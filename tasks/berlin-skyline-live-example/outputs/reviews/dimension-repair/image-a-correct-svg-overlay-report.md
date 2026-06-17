# Image A Correct SVG Overlay Report

- Artwork: `tasks/berlin-skyline-live-example/refs/user-feedback/20260616-image-a-artwork-only.png`
- Template SVG: `tasks/berlin-skyline-live-example/source/template.svg`
- Template preview used only for guide pixels: `tasks/berlin-skyline-live-example/outputs/reviews/checkpoint-1-template-preview/template.svg.png`
- Template preview active bbox: `(219, 230, 886, 691)`
- Template preview active aspect: `1.447`
- Exact SVG coordinate bounds: `(1137.68, 2350.15)` to `(7527.32, 6717.08)`
- Exact SVG content aspect: `1.463`
- Detected artwork bbox: `(0, 60, 1048, 900)`
- Correct overlay box: `(0, 122, 1048, 838)`

## Outputs

- Clean overlay: `tasks/berlin-skyline-live-example/outputs/reviews/dimension-repair/image-a-correct-svg-overlay-clean.png`
- Diagnostic overlay: `tasks/berlin-skyline-live-example/outputs/reviews/dimension-repair/image-a-correct-svg-overlay-diagnostic.png`

## Interpretation

This overlay preserves the real SVG proportions. The square PNG preview is used only as a source for visible guide strokes.
If the user wants this same overlay on a newer generated artwork, that candidate must be available as a local image file first.
