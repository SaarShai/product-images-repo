# U — Door-panel taper fix (full-bleed facade + opening-fill gate)

## Problem
`scripts/controlnet_sdxl_gen.py` fit the SVG contour perfectly (region-IoU 1.0) but
the **door facade tapered to a trapezoid**: the outer top/bottom corners painted
white instead of full facade. `region-IoU` did not penalize this because it measures
*painted-inside-the-intended-region*, and the empty corners had been **carved into**
that region (so "not painting them" was scored as correct).

## Root cause (measured, not guessed)
The door/center panel of `assets/skyline/city-skyline template.svg` is a **full-bleed
facade scene**. Its two large saloon-flap polygons + the splay/side pieces are
classified `internal_cutout` by `svg_classify`. The gen pipeline then:
1. **subtracted them from the paint mask** → the mask was a downward-narrowing
   trapezoid (bottom corners black = never painted), and
2. **drew them as bold lines in the canny control map** → splay lines running to the
   bottom corners, which the model traced as the building silhouette → trapezoid.

This is exactly the failure described in repo memory `guide-no-flap-outlines-trapezoid`.
Diagnostic (`_diag_cutouts.png`) confirmed the bottom-corner triangles
(`outer_contour_*` reclassified to `internal_cutout`, height-fraction ~0.62) are the
taper culprits; only the knob circles + central arch are genuine openings.

## Fix (two parts, both shipped)

### 1. Generation — `controlnet_sdxl_gen.py --full-bleed`
A cutout taller than `--flap-hfrac` (default 0.45) of the panel is a **structural
flap**, not an enclosed opening (mirrors `skyline_panel.cmd_guide`'s `hfrac>0.45`
skip). Under `--full-bleed`:
- flaps are **NOT carved** from the paint mask → the facade fills the full
  rectangular contour, bottom corners included (paint-area +134% on this panel);
- flaps are drawn **faint** (grey, stroke/3) in the control map, never bold, so the
  model doesn't trace them as the silhouette;
- small enclosed openings (knobs) stay carved + bold (kept clean).

### 2. Measurement gate — `measure_sdxl_cn.py --full-bleed` + `fit.py`
New measured metrics that region-IoU is blind to:
- **`opening_fill`** = painted fraction of the FULL opening (outer contour minus only
  the small enclosed holes; flaps un-carved).
- **`corner_fill`** + **`worst_corner_fill`** = painted fraction of each outer-contour
  corner box; the gate keys on the worst BOTTOM corner (the dome top legitimately
  curves inward, so top corners are informational).
- Under `--full-bleed` the legacy `region_iou`/`coverage`/`holes_clear` are also made
  flap-aware so a correctly full-painted facade isn't wrongly penalized.

`fit.py` auto-enables full-bleed for the door/center panel, threads `--full-bleed` to
both sub-steps, and **adds the new gate to PASS**:
`PASS = region_iou≥0.90 AND holes_clear AND opening_fill≥0.85 AND worst_corner≥0.75`.
Overridable: `--full-bleed` / `--no-full-bleed`, `--opening-pass`, `--corner-pass`.

## Test — regenerate the center door panel + measure (768px, 24 steps, seed 7)

Full-bleed-aware measurement (`--full-bleed`), same SVG + bbox both rows:

| metric              | BEFORE (tapered) | AFTER (full-bleed) |
|---------------------|------------------|--------------------|
| region_iou          | 0.4289           | **0.9988**         |
| **opening_fill**    | **0.4289**       | **0.9988**         |
| worst_corner_fill   | 0.0022           | **0.9925**         |
| bottom-left corner  | 0.0022           | 0.9925             |
| bottom-right corner | 0.0031           | 1.0000             |
| holes_clear         | true (8/8)       | true (8/8)         |

`opening_fill` rose **0.4289 → 0.9988** and the worst bottom corner **0.0022 → 0.9925**
— corners now have facade, not white. Eyeballed `_taper_before.png` (red bottom-corner
probe boxes over white triangles) vs `_taper_after.png` (all four corner boxes green,
brick edge-to-edge): the trapezoid is gone; the panel is now a clean edge-to-edge
brownstone facade with arched doors + clean knob holes.

### region-IoU sanity (kept ~1.0 as required)
The original tapered output still scores `region_iou 1.0` under the LEGACY (non
full-bleed) path — proving region-IoU alone is blind to the taper, which is exactly why
the new `opening_fill` + `corner_fill` gate is needed. The AFTER output scores
`region_iou 0.9988` under the (correct) full-bleed measurement.

### Regression
Legacy path (no `--full-bleed`) on the old image is byte-for-byte unchanged:
`region_iou 1.0, holes_clear true, n_holes 13`. Narrow/side-panel flow untouched.
All three scripts `py_compile` clean.

## Verdict: PASS
Taper fixed and gated. The facade fills the opening (opening_fill 0.43→0.9988, worst
corner 0.0022→0.9925); region-IoU stays ~1.0; the new coverage/corner gate FAILs a
tapered result and PASSes the full-bleed one. The gen + measure + fit gate now agree on
which cutouts are real openings vs structural flaps.

## Files
- `scripts/controlnet_sdxl_gen.py` — `--full-bleed` / `--flap-hfrac`; flap-aware mask + faint control lines.
- `scripts/measure_sdxl_cn.py` — `--full-bleed` / `--flap-hfrac`; `opening_fill`, `corner_fill`, `worst_corner_fill`; flap-aware region/holes; corner-box overlay.
- `scripts/fit.py` — auto full-bleed for door; `--opening-pass`/`--corner-pass`; new gate in PASS.
- Artifacts: `tasks/improve/_taper_before.png|.json`, `tasks/improve/_taper_after.png|.json`,
  `tasks/improve/_diag_cutouts.png`, `tasks/improve/_fb_mask_preview.png`, `tasks/improve/_fb_control_preview.png`.
