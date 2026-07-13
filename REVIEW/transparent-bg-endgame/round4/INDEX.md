# Round 4 — gpt-image-2 on flat key background (R21)

Goal: use the LATEST model (gpt-image-2, which rejects `background=transparent`)
by generating on a flat solid key color with the validated rich style + thick
closed non-AA contours, then removing the background pixels.

Pipeline per candidate: gpt-image-2 (via /v1/responses) → chroma_key.py →
decontam_binarize.py → green-speck decontam → gate_battery (print profile).

## Results

| Cell | Key bg | Battery | Notes |
|---|---|---|---|
| H-G2-GREEN-r1 | #00FF00 | REVIEW (no FAILs) | despill 0 px; residual specks removed; D1/D5 = advisory tri-state |
| H-G2-GREEN-r2 | #00FF00 | REVIEW (no FAILs) | same |
| H-G2-MAGENTA-r1 | #FF00FF | FAIL | visible magenta rim halo (D1 4× green), bg not flat |
| H-G2-MAGENTA-r2 | #FF00FF | FAIL | worse: heavy halo + unstable bg |

Verdict candidate: **GREEN key + thick dark closed outlines makes gpt-image-2
usable**. Round-1's green leak was the thin-edge prompt; with bold contours the
key separates cleanly (0-5 px despill before cleanup vs 1800+ for magenta).

## Files

- `board-round4-dark.png` — all 4 on dark
- `fullres/H-G2-GREEN-r1.png` / `-r2.png` — final RGBA (print candidates)
- `fullres/*-on-dark.png`, `*-on-white.png` — composites
- `zoom-GREEN-r1-edge.png` — pre-cleanup edge zoom (specks since removed)
- Gate evidence: `tasks/transparent-bg-endgame/round4_key/gates/`

## Questions for you

1. gpt-image-2's detail level vs round-3 (gpt-image-1.5 / chatgpt-image-latest) — better?
2. GREEN-r1 vs GREEN-r2 — pick either as the round-4 exemplar?
3. OK to lock "green key + thick outline + speck decontam" as the standard route for non-alpha models?
