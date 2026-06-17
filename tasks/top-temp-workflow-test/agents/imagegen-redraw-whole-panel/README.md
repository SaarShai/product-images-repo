# Method A: Whole-Panel Image-Generation Redraw

Goal: generate a cohesive watercolor repaint of the whole top-temp panel, using
the prior B/C candidates as composition references and the two source reference
panels as style targets.

## Tooling Status

The available chat `image_gen` tool exposes only a prompt field. It does not
expose file attachment parameters, masks, image-to-image controls, or a local
save path. I used it as a prompt-only smoke test, but a production Method A run
should use the full attachment prompt in `prompt-method-a-whole-panel.md` with
an image model that can accept the input images listed below.

## Inputs Packaged Here

- `inputs/template.svg`: copied SVG silhouette and cutout source.
- `inputs/composition-b-style-imagegen-fit-preview-white.png`: B composition
  reference.
- `inputs/composition-c-style-matte-elements-preview-white.png`: C composition
  reference.
- `inputs/style-ref-01-slider-panel.png`: style target with sliders, pills, and
  gauge.
- `inputs/style-ref-02-knob-panel.png`: style target with knobs, bolts, and
  dials.
- `inputs/reference-contact-sheet.png`: existing style-packet contact sheet.
- `inputs/style-exemplar-sheet.png`: existing style-packet exemplar sheet.
- `inputs/input-contact-sheet.png`: local combined attachment sheet for quick
  image-gen handoff.

## Geometry Contract

- ViewBox: `0 0 1592.1 1570.39`.
- `path[0]`: outer material contour.
- `path[1]`: large diagonal rounded slot keep-clear, approximately
  `x 788.38..1508.10`, `y 401.16..1029.35`.
- `path[2]`: lower-right round cutout keep-clear, approximately
  `x 1385.69..1527.53`, `y 1167.47..1309.31`.
- Outside the outer contour, the diagonal slot, the lower-right round cutout,
  and the bottom center void must remain blank negative space.

## Files In This Package

- `prompt-method-a-whole-panel.md`: exact attachment-aware prompt.
- `prompt-only-smoke-prompt.txt`: exact prompt used for the prompt-only smoke
  generation tool.
- `generated/`: generated image output location when tooling can save locally.
- `review.md`: short judge-style review and next-step decision.
