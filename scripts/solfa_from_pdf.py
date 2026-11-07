#!/usr/bin/env python3
"""Extract tonic sol-fa from a PDF that has a text layer.

    python3 solfa_from_pdf.py sheet.pdf              # show the rows it found
    python3 solfa_from_pdf.py sheet.pdf --voices 4   # parse into bars per voice

The sol-fa printed above and below the staves is an exact transcription of every
voice, including octave marks — more reliable than reading noteheads. See
references/tonic-solfa.md for the notation and the pitch mapping.

Needs pdfplumber.
"""
from __future__ import annotations

import argparse
import collections
import sys
from fractions import Fraction as F

try:
    import pdfplumber
except ImportError:
    sys.exit("pdfplumber is required:  pip install pdfplumber --break-system-packages")


# --------------------------------------------------------------------- reading

def rows(page, drop_fonts=()):
    """Characters grouped by rounded baseline, each sorted left to right."""
    out = collections.defaultdict(list)
    for c in page.chars:
        if any(c["fontname"].startswith(f) for f in drop_fonts):
            continue
        out[round(c["top"], 1)].append(c)
    return {k: sorted(v, key=lambda z: z["x0"]) for k, v in sorted(out.items())}


def classify(rows_):
    """Split rows into (sol-fa letter rows, barline rows, octave-mark rows).

    Barlines and octave marks are both '|'. They are told apart by font size:
    barlines are set large (~20pt), octave marks small (~5pt).
    """
    solfa, bars, marks = [], [], []
    for top, cs in rows_.items():
        size = cs[0]["size"]
        only_pipes = all(c["text"] in "|" for c in cs)
        if only_pipes and size > 12:
            bars.append(top)
        elif only_pipes and size < 8:
            marks.append(top)
        elif any(c["text"].isalpha() for c in cs) and any(c["text"] == ":" for c in cs):
            solfa.append(top)
    return solfa, bars, marks


def tokenize(chars):
    """-> [[text, x0, x1, marks], ...]; letters may be two chars ('fe', 'se')."""
    toks, i = [], 0
    while i < len(chars):
        ch = chars[i]["text"]
        if ch == " ":
            i += 1
            continue
        if ch in ":-.":
            toks.append([ch, chars[i]["x0"], chars[i]["x1"], 0])
            i += 1
            continue
        j = i + 1
        while (j < len(chars) and chars[j]["text"].isalpha()
               and (chars[j]["x0"] - chars[j - 1]["x1"]) < 1.2):
            j += 1
        toks.append(["".join(c["text"] for c in chars[i:j]),
                     chars[i]["x0"], chars[j - 1]["x1"], 0])
        i = j
    return toks


def attach_marks(toks, mark_chars):
    """Assign each octave mark to the NEAREST letter by x-centre.

    Containment tests miss the second of a stacked pair and turn d₁₁ into d₁ —
    an octave error in the bass. Afterwards the assigned total must equal the
    number of marks in the row; assert it.
    """
    letters = [t for t in toks if t[0] not in ":-."]
    if not letters:
        return toks
    for m in mark_chars:
        mx = (m["x0"] + m["x1"]) / 2
        best = min(letters, key=lambda t: abs((t[1] + t[2]) / 2 - mx))
        best[3] += 1
    assert sum(t[3] for t in letters) == len(mark_chars), "octave marks lost"
    return toks


def split_bars(toks, bar_xs):
    """Split a row's tokens into bars using the barline x positions."""
    groups, cur, bi = [], [], 0
    edges = sorted(bar_xs)[1:]
    for t in toks:
        while bi < len(edges) and t[1] > edges[bi]:
            groups.append(cur)
            cur = []
            bi += 1
        cur.append(t)
    groups.append(cur)
    return groups


# --------------------------------------------------------------------- rhythm

def parse_bar(bar_toks):
    """-> [(beats, solfa, octave_marks), ...] for one bar.

    ':' separates beats, '.' halves a beat, '-' extends the previous note.
    """
    beats, cur = [], []
    for t in bar_toks:
        if t[0] == ":":
            beats.append(cur)
            cur = []
        else:
            cur.append(t)
    beats.append(cur)

    notes = []
    for b in beats:
        syms = [x for x in b if x[0] != "."]
        if not syms:
            continue
        if len(syms) == 1 and syms[0][0] == "-":
            if not notes:
                raise ValueError("bar opens with a continuation")
            notes[-1][0] += 1
        elif len(syms) == 1:
            notes.append([F(1), syms[0][0], syms[0][3]])
        else:                                   # half-beats
            for s in syms:
                if s[0] == "-":
                    notes[-1][0] += F(1, 2)
                else:
                    notes.append([F(1, 2), s[0], s[3]])
    return [tuple(n) for n in notes]


# ---------------------------------------------------------------------- pitch

DEGREE = {"d": (0, "G"), "r": (2, "A"), "m": (4, "B"), "f": (5, "C"),
          "s": (7, "D"), "l": (9, "E"), "t": (11, "F#"),
          "fe": (6, "C#"), "se": (8, "D#"), "ta": (10, "F"), "de": (1, "G#")}


def pitch(solfa, marks, doh_midi=67):
    """MIDI pitch. doh_midi is the pitch of unmarked 'd' (G4 = 67 for 'Doh is G').

    Each octave mark drops an octave: d₁₁ = doh_midi - 24.
    """
    semitones, _ = DEGREE[solfa]
    return doh_midi + semitones - 12 * marks


def check_metre(voices, expected):
    """voices = {name: [bar, ...]}; expected = [beats per bar].

    All voices agreeing bar by bar is the strongest available signal that the
    tokenisation is right — a mis-split shows up in exactly one voice.
    """
    assert all(len(v) == len(expected) for v in voices.values()), \
        {k: len(v) for k, v in voices.items()}
    for name, bars in voices.items():
        for i, (bar, want) in enumerate(zip(bars, expected), 1):
            got = sum(n[0] for n in bar)
            assert got == want, f"{name} bar {i}: {got} beats, expected {want}"
    return True


# ------------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--voices", type=int, default=0,
                    help="sol-fa rows per system (4 for SATB); parses into bars")
    args = ap.parse_args()

    with pdfplumber.open(args.pdf) as pdf:
        page = pdf.pages[args.page]
        r = rows(page, drop_fonts=("AAAAAA",))
        solfa_tops, bar_tops, mark_tops = classify(r)

    print(f"{len(solfa_tops)} sol-fa rows, {len(bar_tops)} barline rows, "
          f"{len(mark_tops)} octave-mark rows\n")

    for top in solfa_tops:
        toks = tokenize(r[top])
        near_marks = [t for t in mark_tops if 0 < t - top < 8]
        if near_marks:
            attach_marks(toks, r[near_marks[0]])
        near_bars = [t for t in bar_tops if -10 < t - top < 0]
        bar_xs = [c["x0"] for c in r[near_bars[-1]]] if near_bars else []

        show = lambda t: t[0] + ("_" * t[3]) if t[0] not in ":-." else t[0]
        if args.voices and bar_xs:
            groups = split_bars(toks, bar_xs)
            print(f"top={top:7.1f}  " +
                  " | ".join(" ".join(show(t) for t in g) for g in groups))
        else:
            print(f"top={top:7.1f}  " + " ".join(show(t) for t in toks))

    print("\nRows appear per system in score order: soprano, alto, tenor, bass.")
    print("Underscores are octave marks — one per octave below the middle range.")


if __name__ == "__main__":
    main()
