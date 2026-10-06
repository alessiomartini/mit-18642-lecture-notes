# Study HTML

A local, generated HTML version of a lecture-notes chapter, for studying with the lecture video:
sticky YouTube player synced with the text, and a private notes/solutions box under every paragraph.
LaTeX (`lecture-notes/`) stays the single source; nothing here edits it.

## Run

```
python study/build.py          # ch04 -> study/out/ch04.html  (python study/build.py ch05 for another chapter)
python study/server.py         # then open http://127.0.0.1:8642/ch04.html   (--port N to change)
```

Needs only Python 3 (stdlib). KaTeX, marked and the YouTube IFrame API come from a CDN (internet
needed for maths and video). TikZ figures are compiled once with `pdflatex` + `pdftocairo` into
`out/fig/*.svg` (cached; if those tools are missing the figure is skipped with a warning).
Open the page through the server, not as a file (YouTube refuses `file://`, notes need the API).
Re-run `build.py` after the `.tex` changes; for correct cross-references and numbers it reads the
`lecture-notes/build/**/*.aux` files of the last full LaTeX build.

## What is in the page

- Boxes with the fixed colours and `TYPE n.m: topic` titles; right-column items of the PDF (examples,
  proofs, course notes, history, asides, `\note`, `\feedback`, answers) sit in a right column next to the
  block they follow, under it on a phone.
- Every `\ts{year}{lecture}{mm:ss}` is a button. Click: the player (sticky, top) loads that lecture and seeks.
  While the video plays the paragraph of the latest timestamp already reached is highlighted
  (and scrolled to when "follow video" is on). Video ids come from the table in `preamble.tex`.
- "+" next to a paragraph: note or question (Markdown + `$math$`, live preview, Ctrl+Enter saves,
  optionally with the current video time). "My solution" under each exercise. Notes are tagged NEW
  until imported into LaTeX (see `IMPORT.md`).

## Files

| file | role |
|---|---|
| `build.py` | LaTeX -> HTML converter (knows the macros of `preamble.tex`) |
| `server.py` | `127.0.0.1` server: serves `out/`, JSON API `GET/POST /api/notes`, `DELETE /api/notes/<id>` |
| `static/` | `page.html` template, `study.css`, `study.js` (copied into `out/` by the build) |
| `notes.db` | sqlite, created on first run, **git-ignored** (private notes) |
| `out/` | generated, **git-ignored** (rebuilt in seconds; avoids noisy diffs) |
| `IMPORT.md` | how Claude imports notes into the LaTeX |

Paragraph ids are `p-<hash of the first 90 characters>`: stable when text is inserted elsewhere,
lost if the first words of a paragraph change (such notes then appear under "no longer in the text").

## Known limits

Why a custom converter: `make4ht` is installed but cannot follow paracol/tcolorbox/queued margin
macros; pandoc is not installed. `\note`, `\answer`, `\feedback` are supported but untested on real
data (ch04 has none). Not built yet (roadmap): Claude importing notes (see `IMPORT.md`, manual for now),
a live assistant via the Gemini free API, a study profile. The API/DB were kept generic
(`chapter`, `paragraph_id`, `kind`, `imported_at`) so these can be added.
