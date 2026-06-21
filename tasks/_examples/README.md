# Curated pass/fail examples — element-edit workflow

Reference exemplars for the "edit ONE element of a finished illustration, change nothing else, match style, fix anatomy/geometry" workflow. Raw/intermediate gen images were dumped to `~/Documents/temp/` (recoverable); these are the teaching keepers. Lessons live in `.claude` memory: `element-edit-diffmask-composite`, `image-edit-engine-routing`, `reference-lock-for-consistency`, `element-reshape-stretch-then-refine`.

## pass/
- **window-widen-PASS-n02-v6.png** — final: wooden arched "window" widened + bottom straightened. Recipe = no-redo stretch (anchored) → Flux Kontext cleanup → arched-mask composite + reattach RGBA alpha.
- **window-widen-AFTER-zoom.png** — zoom of the accepted widened door.
- **fairy-redraw-PASS-X3-zoom.png** — bottom-left fairy redrawn cute children's-book + modest, fal Flux.2-pro, diff-mask composite (gate=0).
- **fairy-reflock-PASS-ML-zoom.png** — a 2nd fairy reference-locked to X3 (cross-instance consistency holds).

## fail/
- **window-BEFORE-narrow-archedbottom.png** — the starting door (narrow, slightly-arched bottom) = the problem to fix.
- **window-FAIL-Fill-blob-didnt-widen.png** — Flux Fill into a blob mask: did NOT widen (model keeps its own door/frame split; a region mask can't enforce the opening geometry).
- **window-FAIL-stretch-only-rough-distort.png** — pure no-redo stretch: exact geometry but distorted handles/soft (needs the Kontext cleanup pass).
- **fairy-FAIL-TL-faded-merged-tower.png** — crop included the tower → fairy faded/merged (per-instance crop framing matters).
- **fairy-FAIL-BR-realistic-drift.png** — style drifted realistic/doll (reference-lock alone didn't hold; needs explicit "flat cute cartoon, not realistic" push).
- **fairy-FAIL-K3-glossy-style-mismatch.png** — high guidance → glossy/anime face that mismatches the loose watercolor surroundings.
