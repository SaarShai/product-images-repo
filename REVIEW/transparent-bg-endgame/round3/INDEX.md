# Round 3 — RICH style + THICK outline, native alpha (2026-07-13)

Answers round-1 feedback: keep the O-route "perfect" edge/removal, raise style
detail. Same pipeline as validated: native `background=transparent` gen →
`decontam_binarize.py --erode 1` → `gate_battery.py --profile print`.

All files: `/Users/za/Documents/product images repo/REVIEW/transparent-bg-endgame/round3/`
- `boards/` — 5-panel composites (white/black/#111/navy/magenta) + 400% edge crops
- `fullres/` — raw gens + `-print` processed finals (judge from these)

| Candidate | Model | Gate | Note |
|---|---|---|---|
| H-O1-RICH-AA-print.png | gpt-image-1 | FAIL (D1) | pale ground tuft at base — real defect, gate correct |
| H-O1-RICH-HARD-print.png | gpt-image-1 | FAIL (D1) | same ground tuft |
| H-O15-RICH-AA-print.png | gpt-image-1.5 | REVIEW | rich, clean on dark panels |
| H-O15-RICH-HARD-print.png | gpt-image-1.5 | REVIEW | rich, clean |
| H-O2-RICH-AA-print.png | chatgpt-image-latest (image-2 family) | REVIEW | rich graphic detail, clean |
| H-O2-RICH-HARD-print.png | chatgpt-image-latest | REVIEW | rich, clean |

Model answer to round-1 question: round-1 O1 = gpt-image-1, O2 =
chatgpt-image-latest (the image-2-family model). gpt-image-2 itself rejects
background=transparent (HTTP 400, canary-verified) — chatgpt-image-latest and
gpt-image-1.5 are the high-quality models that DO support native alpha.

## Questions for user
1. Style level: is round-3 richness right, or push further/dial back?
2. Model pick: gpt-image-1.5 vs chatgpt-image-latest (both clean; different flavor)?
3. AA vs HARD prompt made little visible difference post-binarize — default AA?
