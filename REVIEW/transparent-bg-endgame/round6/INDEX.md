# Round 6 — no-filament structure + no-green-art palette (R24/R25)

Response to round-5 feedback: artifacts at thin-branch intersections; a few
stray pixels on other edges.

Root-cause fixes, both at the SOURCE:
1. `[STRUCTURE - NO LOOSE FILAMENTS]` prompt block — no feather-duster fans /
   hair-thin strand sprays; branches solid with painted joints.
2. `[PALETTE CONSTRAINT - NO PURE GREEN]` prompt block — seaweed in
   olive/sage only, so `green_purge.py --no-green-art` removes ALL key-hue
   green unconditionally (no protection shielding = no survivors).

## Results

| Cell | Battery | Purge |
|---|---|---|
| H-G2-CLEAN-GREEN-r1 | all gates PASS (D5 advisory only) | converged, final sweep 0 residual |
| H-G2-CLEAN-GREEN-r2 | all gates PASS (D5 advisory only) | converged, final sweep 0 residual |

Visual check: solid branch junctions, no trapped green, olive seaweed intact.

## Files
- `board-round6-dark.png` — both on dark
- `fullres/` — final RGBA + on-dark/on-white composites
- `zoom-*.png` — branch-junction closeups

## Questions
1. Junction artifacts gone to your eye? (zooms)
2. r1 (purple/teal cluster) vs r2 (red coral + barnacles) pick?
3. If clean: lock this as the standard non-alpha-model route
   (green key + medium outline + no-filament + no-green-art + green_purge)?
