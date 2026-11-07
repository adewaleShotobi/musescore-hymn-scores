# The .mscz / .mscx format (MuseScore 4.7)

## Package

A `.mscz` is a zip:

```
<Name>.mscx              the score
score_style.mss          style overrides
META-INF/container.xml   names the .mscx  (update it if you rename)
Thumbnails/thumbnail.png a real MuseScore render of page 1 — read it
audiosettings.json  automation.json  viewsettings.json
```

Renaming the score means renaming the `.mscx` **and** editing `container.xml`.

## Skeleton

```xml
<museScore version="4.70">
  <Score>
    <metaTag .../>
    <Part id="1">
      <Staff>
        <StaffType group="pitched">
          <name>stdNormal</name>
          <noteheadScheme>solfege-movable</noteheadScheme>
        </StaffType>
      </Staff>
      <trackName>Women</trackName>
      <Instrument id="women">…<longName>Soprano/Alto</longName>
                              <shortName>S/A</shortName></Instrument>
    </Part>
    <Part id="2">…</Part>
    <Staff id="1">
      <VBox>…title / subtitle / composer / poet…</VBox>
      <Measure len="1/4">…</Measure>
      …
    </Staff>
    <Staff id="2">…</Staff>
  </Score>
</museScore>
```

`<Part>` carries the instrument and the notehead scheme; `<Staff id=N>` carries
the music. A closed SATB score is two parts, two staves, two voices each.

## Element order — the trap

MuseScore writes `<eid>` first inside a `<Measure>`, then structural elements,
then `<voice>`:

```xml
<Measure>
  <eid>…</eid>
  <LayoutBreak>
    <subtype>line</subtype>
  </LayoutBreak>
  <voice>…</voice>
</Measure>
```

**A `<LayoutBreak>` written *before* `<eid>` is silently discarded when the file
is opened.** The score loads, nothing is reported, and MuseScore re-flows the
systems itself — which quietly destroys any verse numbering that was aligned to
the intended line starts. Insert after `<eid>` (index 1 when an `<eid>` is
present, 0 when it is not).

Breaks live on **staff 1 only**. Writing them on both staves is not how
MuseScore stores them.

Assume the same hazard for other structural elements. The way to be sure an edit
took is to read the file back after the user has opened and saved it.

## Measures

- Default length comes from the time signature. An irregular measure carries
  `len` as a fraction **of a whole note**: a one-beat pickup in 3/4 is
  `len="1/4"`; a two-beat closing bar is `len="1/2"`.
- A phrase-end bar before a mid-piece pickup is often `len="1/2"` too. If one
  such bar is short and a structurally identical bar elsewhere is not, the
  full-length one is usually the bug — it produces an audible pause.
- The first measure of staff 1 holds `<Clef>`, `<KeySig>`, `<TimeSig>` inside
  voice 1.
- `<KeySig><concertKey>N</concertKey></KeySig>`; N is the number of sharps,
  negative for flats. G major = 1, A♭ major = −4.

## Chords, notes, rests

```xml
<Chord>
  <dots>1</dots>                    <!-- before durationType -->
  <durationType>half</durationType>
  <Lyrics>…</Lyrics>                <!-- all Lyrics before the Notes -->
  <Note><pitch>67</pitch><tpc>15</tpc></Note>
</Chord>
```

Write `<dots>` **before** `<durationType>`, as MuseScore does. Written after, a
dotted half can be read as a plain half; MuseScore then pads the measure with a
rest and the bar is quietly wrong.

`<duration>` inside a Chord is an actual-length override. Seeing it alongside a
`<dots>` that disagrees is the signature of a measure MuseScore had to repair.

`pitch` is MIDI. `tpc` is the tonal pitch class, which fixes the spelling:

```
tpc = 13 + "FCGDAEB".index(letter) + 7*alter
letter = "FCGDAEB"[(tpc - 13) % 7]        alter = (tpc - 13) // 7
```

| | F | C | G | D | A | E | B |
|---|---|---|---|---|---|---|---|
| ♭ | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
| ♮ | 13 | 14 | 15 | 16 | 17 | 18 | 19 |
| ♯ | 20 | 21 | 22 | 23 | 24 | 25 | 26 |

So A♭=10, B♭=12, C=14, D♭=9, D=16, E♭=11, F=13, G♭=8, G=15, A=17, E=18, F♯=20,
C♯=21, D♯=23.

## Lyrics

`<Lyrics>` is a child of `<Chord>`, before the `<Note>` elements:

```xml
<Lyrics>
  <no>2</no>                    <!-- 0-indexed; omitted for verse 1 -->
  <syllabic>begin</syllabic>    <!-- begin | middle | end; omitted if a whole word -->
  <text>Fa</text>
</Lyrics>
```

Child order is `no`, `eid`, `syllabic`, `text`. A verse number goes in the
`text` of the syllable it heads, followed by a non-breaking space:
`"3. The"`.

Lyrics sit on the soprano (staff 1, voice 1) in a closed SATB score. A separate
bass word — where the men have their own text at a cadence — is a `<Lyrics>` on
a staff 2 chord.

**Lyrics live across voices, so iterate in tick order.** Walking voice by voice
reports syllables out of sequence and will scramble any edit keyed on ordinal
position. Use `lyric_slots()` in `scripts/mscz.py`.

Two lyrics at the same tick in different voices is normal — the parts have
different rhythms there. It is not a duplicate.

## Slurs

A slur is a `<Spanner type="Slur">` on the chord where it starts, with the
matching `<prev>` half on the chord where it ends:

```xml
<Chord>                                   <Chord>
  <Spanner type="Slur">                     <Spanner type="Slur">
    <Slur/>                                   <prev><location>
    <next><location>                            <fractions>-1/8</fractions>
      <fractions>1/8</fractions>              </location></prev>
    </location></next>                      </Spanner>
  </Spanner>                                …
```

The fraction is the distance between the two chords. Two notes under one
syllable need one.

## Style keys (score_style.mss)

| key | what it does |
|---|---|
| `spatium` | staff size in mm (stock ≈ 1.75). Everything else in sp scales with it |
| `lyricsOddFontSize` / `lyricsEvenFontSize` | lyric text size — spatium-dependent |
| `lyricsMinDistance` | horizontal gap between syllables; 0.8 sp reads well |
| `lyricsLineHeight` / `lyricsOddLineSpacing` | verse row spacing (relative to the font) |
| `staffDistance` | gap between the two staves |
| `minSystemDistance` / `maxSystemDistance` | gap between systems |
| `minSystemSpread` / `minStaffSpread` | **override the two above when `enableVerticalSpread=1`** |
| `staffUpperBorder` / `staffLowerBorder` | page top/bottom padding |
| `pagePrintableWidth`, `pageOdd/EvenLeft/Top/BottomMargin` | page geometry, in inches |

The vertical-spread override is a common surprise: changing `staffDistance` and
seeing nothing happen usually means `minStaffSpread` is what is in charge.
