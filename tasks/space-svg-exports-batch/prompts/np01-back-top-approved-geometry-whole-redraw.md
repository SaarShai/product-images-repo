# NP01 Back Top Approved Geometry Whole-Panel Redraw

## Purpose

Use this prompt package when adapting the user-approved `np01-back-top` geometry
to the correct watercolor control-panel style.

This is not a local locked-geometry restyle. It follows the successful
2026-06-16 top-temp method: use the geometry image as a composition map, use the
real references/style packet as style targets, generate a raw whole-panel redraw,
then run SVG verification downstream.

## Attachments

Attach these images/files in this order when the image model supports image
inputs:

1. `tasks/space-svg-exports-batch/outputs/final/np01-back-top-checkpoint-v1-artwork-only.png`
2. `tasks/space-svg-exports-batch/source/np01-back-top.svg`
3. `tasks/space-svg-exports-batch/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png`
4. `tasks/space-svg-exports-batch/refs/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png`
5. `tasks/space-svg-exports-batch/style-packet/style-exemplar-sheet.png`
6. `tasks/space-svg-exports-batch/style-packet/reference-contact-sheet.png`

Optional high-signal crops:

- `tasks/space-svg-exports-batch/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-edge-treatment.png`
- `tasks/space-svg-exports-batch/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-edge-treatment.png`
- `tasks/space-svg-exports-batch/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-body-texture.png`
- `tasks/space-svg-exports-batch/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-body-texture.png`

## Exact Prompt

Use the first attached image only as the approved geometry and composition map.
It shows the correct outer silhouette, two bottom triangular tabs, the top-left
round cutout, the upper-right diagonal rounded slot, the lower-center rectangular
void, and the right-side notch/cut geometry. Do not copy, trace, texture, or
collage its pixels as final art.

Redraw the entire object as one cohesive hand-painted watercolor blue
control-panel illustration in the style of the attached reference panels and
style-packet sheets.

Preserve the visible geometry from the first image:

- keep the same overall part silhouette, including the two bottom tabs;
- keep the top-left circular cutout blank white;
- keep the large diagonal rounded slot blank white;
- keep the lower-center rectangular opening blank white;
- keep all outside background blank white;
- keep all controls and details inside safe blue material areas, not crossing
  cutout edges or the outer contour.

Style target:

- soft cobalt/sky-blue watercolor body;
- dark blue uneven ink rim;
- slight bevel/lip around the outer contour and cutout rims;
- soft inner shadows and pale upper-left highlights;
- watercolor granulation and paper texture;
- friendly rounded red, yellow, and mint/teal controls;
- simple dials, sliders, capsule buttons, knobs, sockets, screw heads, and sparse
  circuit-like traces that look hand-painted.

Composition target:

- Preserve the existing broad layout: dial/gauge and slider bank on the left,
  three colored pins near the upper middle, a small control/screen cluster on the
  lower right, and capsule buttons near the lower material pockets.
- Improve cohesion so the whole plate looks painted by one artist, not assembled
  from separate sprites or crop fragments.
- Add subtle reference-style detail where safe, but keep the design clean and
  readable.

Hard negatives:

- no procedural sprite placement;
- no visible crop seams or pasted reference fragments;
- no local texture fill pretending to be a style transfer;
- no flat vector UI;
- no photoreal metal;
- no labels, numbers, arrows, construction guides, or dashed template marks;
- no new holes or moved holes;
- no paint, shadow, controls, or texture inside any cutout.

Return a single raw high-resolution PNG on white background. The raw redraw does
not have to prove exact SVG fit by itself; it will be passed through the exact
SVG export/checker afterward.

## Acceptance Before Geometry Export

The raw redraw is worth SVG verification only if it looks like one coherent
watercolor object in the same family as the two reference panels. If it still
looks like the approved geometry raster was filtered, recolored, or collaged,
reject it and rerun Whole-Panel Redraw Mode with the attachments.
