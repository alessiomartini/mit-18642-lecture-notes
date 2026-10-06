# Importing study notes into the LaTeX (procedure for Claude)

Alessio writes notes, questions and exercise solutions in the study HTML. They live in
`study/notes.db` (sqlite, git-ignored). When he says "importa le note dallo study" (or similar),
do the following. Work on `main` in the main checkout (lecture-notes workflow), commit + push.

## 1. Read the unimported rows

```
python - <<'EOF'
import sqlite3; c = sqlite3.connect("study/notes.db"); c.row_factory = sqlite3.Row
for r in c.execute("SELECT * FROM notes WHERE imported_at IS NULL ORDER BY chapter, id"): print(dict(r))
EOF
```

Columns: `id, chapter ('ch04'), paragraph_id, kind (note|question|solution), text (Markdown with $math$),
video_time (seconds, may be null), video_id (YouTube id, may be null), created_at, imported_at`.

## 2. Find the place

`paragraph_id` is `p-<7 hex>`: sha1 of the first 90 characters of the paragraph's source after
whitespace collapsing (`study/build.py`, function `uid`; a `-2`, `-3` suffix marks duplicates in
document order). Boxes use their `\label` (e.g. `ch04:ex-machine`) or `bx-<hash>`. Easiest: run
`python study/build.py <chapter>`, open `study/out/<chapter>.html`, search the id, and read the
paragraph/box text next to it; then find that text in `lecture-notes/chapters/<chapter>-*.tex`.
If the id is not in the HTML any more (the paragraph was edited) place the note by its text and
`video_time`, or ask.

## 3. Insert

- `note` / `question`: put `\note{...}` right after the matching paragraph's text (inside the paragraph,
  before its blank line), as defined in `preamble.tex`: a new `\note{` is "NEW, unread". Convert
  Markdown to LaTeX (`**x**` -> `\textbf{x}`, lists -> itemize), keep `$math$`. If `video_id`/`video_time`
  is set, map the id back to `\ts{year}{lecture}{m:ss}` (table in `preamble.tex`) and append it.
  Follow the "Lecture notes (LaTeX)" rules in `~/.claude/rules/alessio-preferences.md`
  (never delete a note; answers are done later when he says "leggi le note").
- `solution`: `\begin{mysolution}...\end{mysolution}` directly below the matching exercise box
  (`paragraph_id` is the exercise's id). Never edit an existing `mysolution`.

## 4. Mark as imported

```
python - <<'EOF'
import sqlite3, datetime; c = sqlite3.connect("study/notes.db")
ids = [...]   # the ids you inserted
c.executemany("UPDATE notes SET imported_at=? WHERE id=?", [(datetime.datetime.now().isoformat(timespec='seconds'), i) for i in ids]); c.commit()
EOF
```

Imported rows stay in the DB (they show as IMPORTED and cannot be deleted from the UI).
Build the chapter (`lecture-notes/.vscode/build.py`) to check it compiles, then commit + push.
Do not commit `notes.db`.
