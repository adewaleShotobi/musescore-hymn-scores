# Reading music out of a PDF

Two situations. A sheet printed with **tonic sol-fa** above the staves usually
has a text layer, and that text is an exact transcription of every voice — read
it. A purely **engraved** PDF has no text for the notes, and you have to work
from glyph coordinates.

---

## 1. Tonic sol-fa from the text layer

### The notation

```
d r m f s l t      the seven degrees, relative to doh
d'  or  d¹         one octave up      (a stroke above the letter)
d₁  or  d|         one octave down    (a stroke below); two strokes = two octaves
fe  se  ta  de     chromatics: raised 4, raised 5, flattened 7, raised 1
:                  beat separator          .    half-beat separator
-                  the previous note continues for another beat
|                  barline                 ‖    phrase or section mark
underline          two notes to one syllable
```

`Doh is G` (or whatever) is printed at the left and fixes the key.

### Pitch

With mark count *n* (strokes below the letter), doh sits in octave `4 − n`:

```
d → G(4−n)   r → A(4−n)   m → B(4−n)
f → C(5−n)   s → D(5−n)   l → E(5−n)   t → F♯(5−n)
```

for *Doh is G*; shift for other keys. So `d₁₁` = G2, `t₁₁` = F♯3, `t₁₁₁` = F♯2.
Alto and tenor typically carry one stroke, bass two, occasionally three.
`fe` is a raised `f`, `se` a raised `s`.

### Extracting it

`scripts/solfa_from_pdf.py` does the work. The mechanics that matter:

- Group `pdfplumber` characters by rounded `top`. Each system produces
  interleaved rows: a large-font row of `|` (barlines), a row of sol-fa letters
  and `:` `.` `-`, and a **small-font row of `|`** just below it — those are the
  octave marks, not barlines. Tell them apart by font size.
- Assign each octave mark to the **nearest letter by x-centre**, not by
  containment. Two marks under one letter sit slightly wider than the glyph, and
  a containment test will find only one, turning `d₁₁` into `d₁` — an octave
  error in the bass.
- Sanity-check by counting: the number of marks assigned must equal the number
  of marks in the row.
- Split the letter row into bars using the barline x positions.
- Rows appear per system in score order: soprano, alto, lyrics, tenor, bass.

### Rhythm

Split a bar on `:` into beat groups, then:

| group | meaning |
|---|---|
| `X` | one beat |
| `-` | extend the previous note by one beat |
| `X . Y` | two half-beats |
| `X . -` | dotted |

`X : -` is a half note, `X : - : -` a dotted half. A one-beat pickup bar has a
single group.

### The check that proves you got it right

Sum each voice's bar durations independently and compare against the expected
metre — 3 beats for a full bar in 3/4, 1 for the pickup, 2 for a closing bar
that completes the anacrusis. **All four voices agreeing, bar by bar, is a
strong signal the tokenisation is correct**, because a mis-split shows up as an
arithmetic error in exactly one voice. Assert it before generating anything.

---

## 2. Noteheads from an engraved PDF

Sibelius exports use the `OpusStd` font, so the noteheads *are* characters:

```
œ  filled notehead      ˙  half note      Œ  quarter rest      ™  dot
b  flat                 n  natural        #  sharp
```

- Staff lines are horizontal `lines` longer than about 200 pt. Five of them make
  a staff; their spacing gives the step size.
- **The anchor: a glyph's pitch-y is its `top` + 17.91.** Then
  `step = (y_bottom_line − pitch_y) / (spacing / 2)`, with step 0 on the bottom
  line — E4 in treble, G2 in bass.
- Calibrate that anchor against the key signature, whose flat positions are
  known: treble B♭=4, E♭=7, A♭=3, D♭=6; bass B♭=2, E♭=5, A♭=1, D♭=4.
- Group glyphs into chords by x with a tolerance around **6 pt**. Too tight
  (1–2 pt) splits two voices sounding the same pitch at the same moment into two
  chords and manufactures false differences.

To line an extracted staff up with an existing score in musical time: prove one
voice identical first (the treble is usually the safe one), pair its PDF
x-positions with that voice's known tick times, then interpolate the other
staves' onsets piecewise-linearly. The mapping is only valid once the reference
voice is proven.

---

## Proof renders

MuseScore 4.7 cannot be rendered from a script. MuseScore 3 (`mscore3`) can, and
is enough to check *notes and words*:

```
QT_QPA_PLATFORM=offscreen mscore3 -r 95 -o proof.png hand_written.musicxml
```

Write the MusicXML yourself from the `.mscx` — two staves with `<backup>`
between voices, `<lyric number="N">` on the first note of each chord. Note that
`-S style.mss` is ignored, and a `<defaults>` block overrides style anyway, so
**the spacing in a proof render means nothing**. Say that when you show one.
