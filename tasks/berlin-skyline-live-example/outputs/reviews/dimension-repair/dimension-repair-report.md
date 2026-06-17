# Berlin Skyline Dimension Repair Report

Date: 2026-06-16

## Diagnosis

- Attached/generated content aspect: `1.841`.
- Exact SVG content aspect: `1.463`.
- To match SVG aspect at the same height, the generated frame needs about `0.795x` horizontal scale.
- Generated red separator ratio from top: `0.487`.
- Exact SVG top/bottom separator ratio from top: `0.400`.
- Interpretation: the liked option is visually valuable, but it redrew the physical template too wide/squat and placed the bottom sub-panels too low.

## Test Artifacts

- `outputs/reviews/dimension-repair/diagnostic-best-vs-svg-aspect.png`
- `outputs/reviews/dimension-repair/repair-option-1-global-svg-aspect.png`
- `outputs/reviews/dimension-repair/repair-option-2-panel-remap.png`
- `outputs/reviews/dimension-repair/repair-option-3-svg-locked-composition-map.png`
- `outputs/reviews/dimension-repair/dimension-repair-contact-sheet.png`

## Verdict

- Option 1 is useful as a quick proof that global aspect registration fixes the largest dimensional drift, but it distorts every building.
- Option 2 is useful as a salvage test, but panel seams and local warping are likely too visible for final art.
- Option 3 is the best next method: restart from the liked composition inside the exact SVG proportions, then ask the image model for artwork-only redraw while the SVG overlay remains locked outside the model output.
