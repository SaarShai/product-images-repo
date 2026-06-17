# Review Note

## np01-back-top

Verdict: ACCEPT

Evidence inspected:
- `np01-back-top-watercolor-control-panel-candidate.png`
- `np01-back-top-template-overlay.png`
- `np01-back-top-mask-debug.png`
- `np01-back-top-metadata.json`
- `np01-back-top-geometry-report.md`

Passes:
- Mechanical metrics report `PASS` with `outside_nonwhite_pixels: 0`, `cutout_nonwhite_pixels: 0`, and `decorative_element_pixels_outside_safe_pocket: 0`.
- Visual review shows the circular cutout, diagonal cutout, center slot, and outer contour remain clean.
- Decorative controls are routed into the lower-left, upper-center, lower-right, and bottom pockets instead of crossing the production cuts.

Failures or risks:
- Procedural/PIL rendering is only a checkpoint approximation of the watercolor-blue control-panel references.
- The edge and surface language is softer than vector-flat output, but less organic than a full image-generation redraw.

Next move:
- Use as a checkpoint candidate or composition map for a future reference-style whole-panel redraw.

## np02-front-top

Verdict: ACCEPT

Evidence inspected:
- `np02-front-top-watercolor-control-panel-candidate.png`
- `np02-front-top-template-overlay.png`
- `np02-front-top-mask-debug.png`
- `np02-front-top-metadata.json`
- `np02-front-top-geometry-report.md`

Passes:
- Mechanical metrics report `PASS` with `outside_nonwhite_pixels: 0`, `cutout_nonwhite_pixels: 0`, and `decorative_element_pixels_outside_safe_pocket: 0`.
- Visual review shows the diagonal cutout, circular cutout, center slot, and outer contour remain clean.
- Focal controls are placed in safe pockets: left lower sliders/buttons, center radar screen, mid levers, right dial, and bottom rail.

Failures or risks:
- Procedural/PIL rendering is only a checkpoint approximation of the watercolor-blue control-panel references.
- The composition is geometry-safe, but final production style would benefit from image-generation redraw using the candidate as a layout guide.

Next move:
- Use as a checkpoint candidate or composition map for a future reference-style whole-panel redraw.
