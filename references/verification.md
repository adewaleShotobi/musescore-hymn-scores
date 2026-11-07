# Verifying, and the ways this goes wrong

## Run these after every edit

1. **Measure arithmetic.** Every voice in every measure sums to the measure's
   length. Catches dropped rests, wrong `len`, dots misread, an overfull bar.
2. **`len` attributes unchanged** unless you meant to change them. Losing a
   `len="1/2"` on a phrase-end bar reintroduces a pause the user already asked
   you to remove.
3. **Syllable counts per verse**, in tick order, against the note slots.
4. **Verse numbers** at identical `(measure, tick)` positions in every verse.
5. **Notehead scheme** still on every part.
6. **Slur count** unchanged.
7. **Short-voice list identical to the file you started from.** Hymn scores
   legitimately contain voices that do not fill their bar (a part resting under
   a held note elsewhere). Do not try to "fix" them — record the list before
   your edit and confirm it after. A *new* entry is a regression; an unchanged
   list is proof you broke nothing.

`scripts/mscz.py check` covers 1, 2, 5, 6, 7.

## Failure modes seen in practice

**Building from a stale copy.** The single most damaging one, and it happens
twice as easily as it sounds. The user opens the score between your turns; you
build from the copy you fetched earlier; their edits vanish and your file looks
fine. Re-fetch in the same turn you edit. Where the platform offers a
modification-time guard on write-back, use it.

**A structural element silently dropped.** See *Element order* in
`references/mscz-xml.md`. Symptom: you make a layout change, the user reports it
had no effect, and you assume they undid it.

**A pinned system that does not fit.** MuseScore splits it, and the invented
line carries no verse number. Symptom: "the number is not complete". Measure the
real capacity from a thumbnail render before pinning.

**Verse numbers in two columns.** Caused by nudging each verse's number to its
own next whole word. Symptom: "the numbering is not done well". Use one anchor
set for all verses.

**A number swallowing its own text.** Replacing a syllable's text drops the
`N. ` prefix. Preserve a leading `^\d+\.[\s\xa0]+` when rewriting.

**Lyrics read out of order.** Iterating voice by voice instead of by tick. Any
edit keyed on ordinal syllable position is then applied to the wrong syllables.

**Mixed-content damage.** A naive re-indent that descends into `<text>` corrupts
the words. Never reformat inside `<text>`.

**Claiming two scores match by eye.** They do not match until you have compared
them by extracted coordinates. If asked "are you sure?", the honest answer is to
redo it rigorously and then state exactly which findings were verified to that
standard and which were not.

## Reporting

Say what you verified and what you only predicted. Page counts, line fits and
spacing are always predictions — there is no MuseScore 4.7 renderer available.
Note counts, durations, syllable counts and element presence are facts you can
check, so check them and say so.

When a source document has an error — a wrong attribution, a garbled word, a
line that will not scan — flag it and ask, rather than silently correcting or
silently reproducing it.
