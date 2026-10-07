# Future work, half-done work, things tried

## Piloted on 2026-10-07, to extend after Alessio has looked at the pilot
Requests in `lecture-notes/chapters/ch00-requests.tex` (Chapter 3 / Introduction, all marked done for the pilot).

| Change | Done in | Remaining |
|---|---|---|
| Worked computational examples -> `tryfirst` + `solution` (printed by `\printsolutions` at chapter end) | ch03 (2 examples) | other chapters: only computations on material he already knows; idea-introducing examples stay |
| `keyformulas` -> `keyconcepts` (retrieval questions, then concepts with formula + `\cref`) | ch03 | 24 chapters still have `keyformulas` |
| `casestudy` -> `lab` (question, data in `data/`, Python steps, course results as solution, script in `labs/`) | ch05 high-yield spread | ~30 case studies |
| Course notes inline, numbered where they refer (`coursenote` inside the paragraph) | ch03 | other chapters: boxes already numbered, markers in text missing |
| Exercises: short ones after the *paragraph* they practise, long structured ones in a final `\section*{Exercises}` | ch03 | other chapters (the 2026-10-06 pass placed them per *section*) |

Each chapter needs `\printsolutions` at its end once it has a `tryfirst` or `lab`.

## Study HTML (`study/build.py`)
- New envs are rewritten by `newer_envs()` into known ones; solutions are folded `<details>` right after
  the exercise.
- Known gaps (older than the pilot): itemize inside `answer`, `table` env, `\texorpdfstring`, `\o`;
  two ch03 TikZ figures fail to compile to SVG.

## Tried and reverted / decided against
- Links from a one-chapter PDF to another chapter's PDF (LaTeX Workshop viewer cannot follow them).
- One endless page per chapter (TeX/PDF page height limits).
- Hiding solutions in the PDF with optional-content layers: not attempted, the VS Code viewer support is
  uncertain; solutions go to the chapter end instead.

## Ideas
- More figures like the slides (TikZ/pgfplots).
