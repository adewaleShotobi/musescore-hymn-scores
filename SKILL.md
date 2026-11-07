---
name: musescore-hymn-scores
description: Edit and build MuseScore 4 hymn scores by working on the .mscz XML directly, rather than driving the GUI. Use when asked to add or replace verses, apply solfège (tonic sol-fa) noteheads, enlarge the staff while keeping lyrics the same size, number verses on every line of music, pin line and page breaks, fix pauses or wrong rests, translate a hymn's underlay into another language, or build a score from scratch out of a tonic sol-fa sheet or a hymnal PDF.
---

# MuseScore hymn scores

A `.mscz` is a zip. Editing the XML inside it is faster, more exact and more
verifiable than clicking through the GUI, and it is the only way to do bulk work
— six verses of underlay, a syllable-by-syllable retranslation, a global size
change — without hours of mousework.

This skill assumes SATB hymns on two staves (soprano+alto on the treble,
tenor+bass on the bass), which is how nearly all hymnals are set.

## The five rules that matter most

1. **Re-read the file immediately before every edit.** If the score lives on
   someone's machine, copy it across again in the same turn you edit it. People
   open scores between your turns. Building from a stale copy silently reverts
   their work, and it will not be obvious in the diff — you will simply hand back
   an older file. This has to be a reflex, not a check you remember to do.

2. **Verify that MuseScore kept what you wrote.** MuseScore silently drops
   elements it does not expect in the position you put them. It does not warn,
   and the file still opens. The known case is `<LayoutBreak>` — see
   *Element order* in `references/mscz-xml.md` — but treat every structural
   element the same way: after the user next saves, read the file back and
   confirm your element survived.

3. **Check the arithmetic after every edit.** Sum the durations of every voice in
   every measure and compare against the measure's length. This one check catches
   most real damage: dropped rests, wrong `len` attributes, a dotted note read as
   undotted. `scripts/mscz.py check` does it.

4. **You cannot see the result.** There is no way to render MuseScore 4.7 from a
   script. Every claim about page count, line fit or spacing is a prediction —
   say so. The one real render available is the thumbnail embedded in a file the
   user has saved: `Thumbnails/thumbnail.png` is a genuine MuseScore render of
   page 1. Read it. For everything else, hand-write MusicXML and render with
   `mscore3` for a rough proof of *notes and words only*, never of spacing.

5. **Never invent hymn text.** Ask for the verses, or find a published version
   and have the user confirm it before underlaying. Count the syllables against
   the note slots before you write anything.

## Working on the file

```
python3 scripts/mscz.py check   score.mscz          # durations, breaks, lyrics, style
python3 scripts/mscz.py lyrics  score.mscz          # every verse in tick order
python3 scripts/mscz.py slots   score.mscz          # (measure, tick) of each syllable
```

`scripts/mscz.py` is also importable — `unpack`, `pack`, `lyric_slots`,
`set_lyric`, `set_breaks`, `rescale`, `check` — and that is the normal way to use
it. Write a small build script per job, run the check, then hand the file over.

Read `references/mscz-xml.md` before touching the XML. It has the element order,
the pitch/TPC tables, irregular measures, slurs, and the solfège notehead switch
(including the variant where the `<StaffType>` element is empty).

## The house treatment

Choral groups reading sol-fa want the same four things almost every time:

- **Solfège noteheads on every staff** — `<noteheadScheme>solfege-movable</noteheadScheme>`
- **A bigger staff, with the words unchanged.** Lyric size and vertical
  distances are in spatium units, so raising `spatium` scales everything.
  To grow the notes alone, multiply `spatium` by *k* and divide every
  spatium-dependent value by *k*: `lyricsOddFontSize`, `lyricsEvenFontSize`,
  `lyricsMinDistance`, `staffDistance`, `min`/`maxSystemDistance`,
  `min`/`maxSystemSpread`, `min`/`maxStaffSpread`, `staffUpper`/`LowerBorder`,
  `lyricsMinTop`/`BottomDistance`. `scripts/mscz.py rescale` does exactly this.
  A step of about 6–7% per round is what people mean by "slightly bigger".
- **Wider syllable spacing** — `lyricsMinDistance` around 0.8 sp; the stock 0 or
  0.25 crowds the words.
- **A verse number on every line of music**, not just the first.

Raising the staff costs width: content width in spatium units is fixed, so a
6% bigger staff is a 6% shorter line. Buy some back with margins
(`pageOddLeftMargin`, `pagePrintableWidth`), and watch for a pinned system
overflowing and splitting in two — which strands the verse numbers.

## Verse numbering — the part that goes wrong

The goal is a straight vertical column of numbers at the head of every line.
Two facts make it awkward:

- A system can only begin where a measure begins, and hymn lines are usually
  anacrustic — the text line starts on the *last beat* of the previous bar.
- Word boundaries differ between verses. The syllable that opens a line is
  mid-word in some verses and not others, and no re-syllabification fixes it:
  when a poetic line's last word is polysyllabic, its final syllable lands on
  the next system for every verse that has one there.

So you cannot have both a straight column and every number on a whole word.
**Choose the column.** Anchor the numbers to a set of `(measure, tick)`
positions, apply the same set to all verses, and accept that some read
`1. bove;` after a hyphen at the end of the previous line. That is how hymnals
do it and it is what singers scan for.

Anchor on the first note of each system unless there is a reason not to. If the
poetic lines happen to begin one note in, anchoring there instead is tidier —
but the same anchor must serve every verse.

Pin the line breaks so the layout cannot reflow underneath the numbering, and
then check the breaks survived (rule 2).

## Building a score from scratch

From a **tonic sol-fa sheet**: read `references/tonic-solfa.md`. If the PDF has a
text layer, the sol-fa is an exact transcription of all four voices, including
octave marks — better than reading noteheads. `scripts/solfa_from_pdf.py`
extracts it. The metre check (every voice summing to the right beat count in
every bar independently) is a strong signal you parsed it correctly.

From an **engraved PDF**: `references/tonic-solfa.md` also covers pulling
noteheads out of a Sibelius-style PDF by glyph coordinates, which is the only
reliable way to compare an existing score against a hymnal scan.

Build the package by copying an existing score's `.mscx` prologue (its `<Part>`
blocks already carry the solfège scheme and the instrument definitions) and
generating the `<Staff>` bodies. Keep `score_style.mss` from a score already
tuned to the group's taste.

## Underlaying a translation

Count first, write second. Get the note-slot structure with
`scripts/mscz.py slots`, work out the syllables per line, and check every stanza
against it before touching the file. A line that is one short is normal — the
honest options are to flag it and ask, or to let one syllable take two notes.
Do not pad the text.

Preserve the user's spelling and diacritics exactly. Where an elision has to be
read one way in one line and another way elsewhere to make the counts work, say
so explicitly rather than quietly choosing.

## When something is wrong in the score

Users report symptoms, not causes: "it's causing a pause", "the number is not
complete", "the notes are the same?". Find the mechanism before changing
anything, and compare against a structurally identical bar elsewhere in the same
score — hymn tunes repeat, so the correct version of a broken bar is usually
already in the file. `references/verification.md` has the checks and the failure
modes seen in practice.
