#!/usr/bin/env python3
"""Read, check and edit MuseScore 4 .mscz files.

Library:
    pkg    = unpack("score.mscz")          -> Package (tree, style, files)
    slots  = lyric_slots(pkg.staff(1))     -> {verse_no: [Slot, ...]} in tick order
    set_lyric(slot.el, "Fa-", number=3)
    set_breaks(pkg, {4: "line", 8: "page"})
    rescale(pkg, 2.55)                     # bigger staff, lyrics same printed size
    problems = check(pkg)
    pack(pkg, "out.mscz")

CLI:
    mscz.py check  score.mscz
    mscz.py lyrics score.mscz
    mscz.py slots  score.mscz
    mscz.py style  score.mscz [key ...]
"""
from __future__ import annotations

import collections
import os
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from fractions import Fraction as F

NBSP = "\xa0"

BASE_DUR = {"whole": F(1), "half": F(1, 2), "quarter": F(1, 4),
            "eighth": F(1, 8), "16th": F(1, 16), "32nd": F(1, 32)}

# style keys whose values are in spatium units, so they must be divided by the
# same factor the spatium is multiplied by if the printed size is to stay put
SPATIUM_DEPENDENT = (
    "lyricsOddFontSize", "lyricsEvenFontSize", "lyricsMinDistance",
    "staffDistance", "minSystemDistance", "maxSystemDistance",
    "minSystemSpread", "maxSystemSpread", "minStaffSpread", "maxStaffSpread",
    "staffUpperBorder", "staffLowerBorder",
    "lyricsMinTopDistance", "lyricsMinBottomDistance",
)


# --------------------------------------------------------------------- package

class Package:
    def __init__(self, workdir, mscx_name, tree):
        self.workdir = workdir
        self.mscx_name = mscx_name
        self.tree = tree
        self.score = tree.getroot().find("Score")

    def staves(self):
        return self.score.findall("Staff")

    def staff(self, n):
        return self.staves()[n - 1]

    # ---- style ----
    @property
    def _style_path(self):
        return os.path.join(self.workdir, "score_style.mss")

    def style(self, key, value=None):
        """Get a style value, or set it when `value` is given."""
        if not os.path.exists(self._style_path):
            return None
        s = open(self._style_path).read()
        pat = re.compile(r"<%s>(.*?)</%s>" % (key, key), re.S)
        m = pat.search(s)
        if value is None:
            return m.group(1) if m else None
        if not m:
            raise KeyError(key)
        open(self._style_path, "w").write(
            pat.sub("<%s>%s</%s>" % (key, value, key), s))
        return value

    def thumbnail(self):
        """Path to MuseScore's own render of page 1, if the file has one."""
        p = os.path.join(self.workdir, "Thumbnails", "thumbnail.png")
        return p if os.path.exists(p) else None


def unpack(path, workdir=None):
    workdir = workdir or tempfile.mkdtemp(prefix="mscz-")
    with zipfile.ZipFile(path) as z:
        z.extractall(workdir)
    names = [n for n in os.listdir(workdir) if n.endswith(".mscx")]
    if len(names) != 1:
        raise ValueError("expected exactly one .mscx, found %r" % names)
    return Package(workdir, names[0], ET.parse(os.path.join(workdir, names[0])))


def pack(pkg, out, rename=None):
    """Write the package back out. `rename` renames the .mscx and fixes container.xml."""
    name = pkg.mscx_name
    pkg.tree.write(os.path.join(pkg.workdir, name),
                   encoding="UTF-8", xml_declaration=True)
    if rename and rename + ".mscx" != name:
        new = rename + ".mscx"
        os.rename(os.path.join(pkg.workdir, name), os.path.join(pkg.workdir, new))
        c = os.path.join(pkg.workdir, "META-INF", "container.xml")
        open(c, "w").write(open(c).read().replace(name, new))
        name = new
    if os.path.exists(out):
        os.remove(out)
    order = ["META-INF/container.xml", name, "score_style.mss",
             "audiosettings.json", "automation.json", "viewsettings.json",
             "Thumbnails/thumbnail.png"]
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for n in order:
            p = os.path.join(pkg.workdir, n)
            if os.path.exists(p):
                z.write(p, n)
    return out


# ------------------------------------------------------------------ traversal

def duration(el, measure_len):
    d = el.findtext("durationType")
    if d == "measure":
        return measure_len
    v = BASE_DUR[d]
    total, add = v, v
    for _ in range(int(el.findtext("dots") or 0)):
        add /= 2
        total += add
    return total


def measure_len(m, default=F(3, 4)):
    if m.get("len"):
        a, b = m.get("len").split("/")
        return F(int(a), int(b))
    return default


@dataclass
class Slot:
    measure: int
    tick: F
    chord: ET.Element
    el: ET.Element          # the <Lyrics> element
    text: str
    syllabic: str | None

    def token(self):
        """'-ship', 'Fa-', '-a-' — hyphens showing how the syllable joins."""
        pre = "-" if self.syllabic in ("end", "middle") else ""
        post = "-" if self.syllabic in ("begin", "middle") else ""
        return pre + self.text + post


def chords_in_tick_order(staff, default_len=F(3, 4)):
    """(measure_no, tick, voice_index, chord) for every chord, correctly ordered.

    Lyrics live across voices; walking voice by voice reports them out of
    sequence. Always come through here.
    """
    out = []
    for bi, m in enumerate(staff.findall("Measure"), 1):
        ml = measure_len(m, default_len)
        events = []
        for vi, v in enumerate(m.findall("voice")):
            t = F(0)
            for e in v:
                if e.tag in ("Chord", "Rest"):
                    if e.tag == "Chord":
                        events.append((t, vi, e))
                    t += duration(e, ml)
        out += [(bi, t, vi, e) for t, vi, e in sorted(events, key=lambda z: (z[0], z[1]))]
    return out


def lyric_slots(staff, default_len=F(3, 4)):
    """{verse_no (0-based): [Slot, ...]} in tick order."""
    rows = collections.defaultdict(list)
    for bi, t, vi, ch in chords_in_tick_order(staff, default_len):
        for l in ch.findall("Lyrics"):
            rows[int(l.findtext("no") or 0)].append(
                Slot(bi, t, ch, l, l.findtext("text") or "", l.findtext("syllabic")))
    return dict(rows)


# --------------------------------------------------------------------- editing

def set_lyric(lyrics_el, token, number=None):
    """Set a <Lyrics> from a token like 'Fa-', '-ther', '-o-' or 'praise.'.

    `number` prefixes the verse number and a non-breaking space.
    """
    begins = token.endswith("-")
    ends = token.startswith("-")
    text = token[1:] if ends else token
    text = text[:-1] if begins else text
    syl = ("middle" if (begins and ends) else
           "begin" if begins else "end" if ends else None)
    for tag in ("syllabic", "text"):
        e = lyrics_el.find(tag)
        if e is not None:
            lyrics_el.remove(e)
    if syl:
        s = ET.SubElement(lyrics_el, "syllabic")
        s.text = syl
    x = ET.SubElement(lyrics_el, "text")
    x.text = (f"{number}.{NBSP}" if number else "") + text


def keep_number(old_text, new_text):
    """Rewrite a syllable without losing a leading '3. ' verse number."""
    m = re.match(r"^\d+\.[\s\xa0]+", old_text or "")
    return (m.group(0) if m else "") + new_text


def set_breaks(pkg, breaks, indent="\n        "):
    """breaks = {measure_number: 'line'|'page'|'section'}. Staff 1 only.

    Inserted after <eid>, which is where MuseScore keeps them; written before
    <eid> they are silently discarded on load.
    """
    staff = pkg.staff(1)
    ms = staff.findall("Measure")
    for m in ms:
        for lb in m.findall("LayoutBreak"):
            m.remove(lb)
    for bar, kind in breaks.items():
        m = ms[bar - 1]
        lb = ET.Element("LayoutBreak")
        sub = ET.SubElement(lb, "subtype")
        sub.text = kind
        kids = list(m)
        m.insert(1 if (kids and kids[0].tag == "eid") else 0, lb)
        lb.text = indent + "  "
        sub.tail = indent
        lb.tail = indent
    return breaks


def rescale(pkg, new_spatium, keep_lyric_size=True):
    """Grow (or shrink) the staff. With keep_lyric_size, the words print the
    same size as before and the vertical gaps stay put: every spatium-dependent
    value is divided by the same factor the spatium is multiplied by.

    Costs width — content width in spatium units is fixed, so a 6% bigger staff
    is a 6% shorter line. Watch for a pinned system overflowing.
    """
    old = float(pkg.style("spatium"))
    k = old / float(new_spatium)
    pkg.style("spatium", new_spatium)
    if keep_lyric_size:
        for key in SPATIUM_DEPENDENT:
            cur = pkg.style(key)
            if cur is not None:
                pkg.style(key, round(float(cur) * k, 4))
    return k


# ---------------------------------------------------------------- verification

def short_voices(pkg, default_len=F(3, 4)):
    """Voices that do not fill their measure.

    Hymn scores legitimately contain these. Compare the list before and after an
    edit: unchanged is proof you broke nothing, a new entry is a regression.
    """
    out = []
    for si, st in enumerate(pkg.staves(), 1):
        for bi, m in enumerate(st.findall("Measure"), 1):
            ml = measure_len(m, default_len)
            for vi, v in enumerate(m.findall("voice"), 1):
                t = sum((duration(e, ml) for e in v
                         if e.tag in ("Chord", "Rest")), F(0))
                if t != ml:
                    out.append((si, bi, vi, str(t), str(ml)))
    return out


def check(pkg, default_len=F(3, 4)):
    """Everything cheap and worth knowing. Returns a dict; print it."""
    staves = pkg.staves()
    breaks = {i + 1: m.findtext("LayoutBreak/subtype")
              for i, m in enumerate(staves[0].findall("Measure"))
              if m.find("LayoutBreak") is not None}
    rows = lyric_slots(staves[0], default_len)
    src = ET.tostring(pkg.score, encoding="unicode")
    return {
        "measures": [len(s.findall("Measure")) for s in staves],
        "irregular": {i + 1: m.get("len")
                      for i, m in enumerate(staves[0].findall("Measure"))
                      if m.get("len")},
        "breaks": breaks,
        "notehead_scheme": [p.findtext("Staff/StaffType/noteheadScheme")
                            for p in pkg.score.findall("Part")],
        "slurs": src.count("<Slur"),
        "verses": {n + 1: len(v) for n, v in sorted(rows.items())},
        "verse_numbers": {
            n + 1: [(s.measure, str(s.tick)) for s in v
                    if re.match(r"^\d+\.", s.text)]
            for n, v in sorted(rows.items())},
        "short_voices": short_voices(pkg, default_len),
        "spatium": pkg.style("spatium"),
        "has_thumbnail": pkg.thumbnail() is not None,
    }


# --------------------------------------------------------------------- the CLI

def _main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, path = argv[1], argv[2]
    pkg = unpack(path)
    try:
        if cmd == "check":
            for k, v in check(pkg).items():
                print(f"{k:18s} {v}")
        elif cmd == "lyrics":
            for n, slots in sorted(lyric_slots(pkg.staff(1)).items()):
                print(f"v{n+1} ({len(slots)}): " + " ".join(s.token() for s in slots))
            for n, slots in sorted(lyric_slots(pkg.staff(2)).items()):
                print(f"[staff 2] v{n+1} ({len(slots)}): "
                      + " ".join(s.token() for s in slots))
        elif cmd == "slots":
            for n, slots in sorted(lyric_slots(pkg.staff(1)).items()):
                print(f"--- verse {n+1} ---")
                for i, s in enumerate(slots, 1):
                    print(f"{i:3d}  bar {s.measure:3d}  tick {str(s.tick):>5}  {s.token()}")
        elif cmd == "style":
            keys = argv[3:] or ["spatium", "lyricsOddFontSize", "lyricsMinDistance",
                                "lyricsLineHeight", "staffDistance",
                                "minSystemDistance", "minSystemSpread",
                                "minStaffSpread", "pagePrintableWidth",
                                "pageOddLeftMargin", "enableVerticalSpread"]
            for k in keys:
                print(f"{k:22s} {pkg.style(k)}")
        else:
            print(__doc__)
            return 1
    finally:
        shutil.rmtree(pkg.workdir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
