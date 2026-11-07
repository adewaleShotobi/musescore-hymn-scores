# musescore-hymn-scores

An agent skill for Claude that edits and builds **MuseScore 4 hymn scores** by working on the `.mscz` file directly instead of clicking through the MuseScore app.

It was built for choirs that read **tonic sol-fa**. It does bulk jobs like adding six verses, switching every note to a sol-fa notehead or translating the words syllable by syllable in minutes, where the same work by hand takes hours.

## What it can do

- Add sol-fa (movable-do) noteheads to every staff
- Add or replace verses
- Make the staff bigger while keeping the lyrics the same size
- Put a verse number at the start of every line of music, not just the first
- Pin line and page breaks so the layout stays put
- Find and fix wrong rests, unwanted pauses and broken bars
- Translate a hymn's lyrics into another language, checking syllable counts against the notes
- Build a full SATB score from scratch from a tonic sol-fa sheet or a hymnal PDF

## Who it's for

Choir directors, music secretaries and arrangers who prepare hymn scores in MuseScore, especially for choirs that read sol-fa, and anyone with a stack of hymns that need the same treatment.

It assumes the standard hymnal layout: SATB on two staves, with soprano and alto on the treble staff and tenor and bass on the bass staff.

## Requirements

- Claude on any plan, Free included (the Claude app, Claude Code or Cowork). Free plan usage limits are tight, so Pro is best for full or long scores. Claude Code is not available on the Free plan.
- **Code execution must be switched on.** In the Claude app, go to Settings, then Capabilities, and turn on "Code execution and file creation". The skill will not run without it.
- MuseScore 4 to open and check the results
- Python 3, used by the helper scripts. Claude runs these for you.

## Installation

### Claude app (claude.ai / desktop)

1. Download this repository as a ZIP, or zip the `musescore-hymn-scores` folder.
2. Go to **Customize > Skills**, click **+** and upload the ZIP.
3. Make sure the skill is switched on, and that code execution is on under Settings > Capabilities. Start a new chat to use it.

### Claude Code

Copy the folder into your personal skills directory:

```bash
git clone https://github.com/adewaleShotobi/musescore-hymn-scores.git
cp -r musescore-hymn-scores ~/.claude/skills/
```

To use it in a single project only, put it in that project's `.claude/skills/` folder instead.

## How to use it

Attach your `.mscz` file to edit an existing score, or attach a PDF of a hymn or a tonic sol-fa sheet to build a new score from it. Then ask in plain language. Claude picks up the skill on its own.

PDFs work best when the notes are real text you can select and copy. Scanned or photographed pages, and especially handwritten sol-fa, are much less reliable.

Example requests:

- "Add sol-fa noteheads to this hymn and make the staff slightly bigger without changing the lyric size."
- "Here are verses 4 to 6. Add them under the existing verses and number every line."
- "Translate this hymn into Yoruba. Here is the translation; fit it to the notes and flag any lines that don't match."
- "Build a MuseScore file from this tonic sol-fa PDF."
- "Bar 9 is causing a pause when it plays back. Find out why and fix it."

## What's inside

```
musescore-hymn-scores/
├── SKILL.md                  # instructions Claude follows
├── scripts/
│   ├── mscz.py               # check, lyrics, slots, rescale, unpack/pack
│   └── solfa_from_pdf.py     # extract sol-fa text from a PDF
└── references/
    ├── mscz-xml.md           # MuseScore XML structure and element order
    ├── tonic-solfa.md        # reading sol-fa sheets and engraved PDFs
    └── verification.md       # checks and known failure modes
```

You can also run the checker yourself:

```bash
python3 scripts/mscz.py check  score.mscz   # durations, breaks, lyrics, style
python3 scripts/mscz.py lyrics score.mscz   # every verse in order
python3 scripts/mscz.py slots  score.mscz   # where each syllable sits
```

## Limitations (please read)

- **Claude cannot see the rendered score.** Anything it says about page count, line fit or spacing is a prediction. Always open the file in MuseScore and check it.
- **It will not invent hymn text.** You supply the verses, or confirm a published version before it uses them.
- **Save before you ask for an edit.** The skill re-reads the file before every change, but unsaved work in MuseScore can still be overwritten.
- Built and tested on MuseScore 4. Older versions may behave differently.

## Contributing

Issues and pull requests are welcome, especially for other notation conventions, other hymnal layouts and new failure cases you run into.

## Author

Built by Adewale Shotobi with Claude.

## License

MIT. See the LICENSE file for details.

## Disclaimer

This project is independent and is not affiliated with, endorsed by or sponsored by MuseScore. MuseScore is a trademark of its respective owner.

You are responsible for making sure you have the right to edit and share the hymns and translations you use with this skill. Many older hymns are public domain, but many modern hymns and translations are still under copyright.