# Prompt: Method A Whole-Panel Redraw

## Attachments

Attach these files in this order when the image model supports input images:

1. `inputs/template.svg`
2. `inputs/input-contact-sheet.png`
3. `inputs/composition-b-style-imagegen-fit-preview-white.png`
4. `inputs/composition-c-style-matte-elements-preview-white.png`
5. `inputs/style-ref-01-slider-panel.png`
6. `inputs/style-ref-02-knob-panel.png`
7. `inputs/style-exemplar-sheet.png`
8. `inputs/reference-contact-sheet.png`

## Exact Prompt

Redraw the entire attached top-temp SVG panel as one cohesive hand-painted
watercolor control-panel illustration. Use the attached template SVG as the
hard silhouette and cutout geometry. Use Composition B and Composition C only
as composition references, not as pixel sprites or collage sources. Use the two
source reference panels and the style-packet sheets as the visual style targets.

Output a single finished panel image at the template aspect ratio, ideally
`1593 x 1571 px`, with the material body painted only inside the outer contour.
If alpha is supported, make everything outside the outer contour transparent;
otherwise leave it pure white. Keep all internal cutouts as pure blank negative
space: the long diagonal rounded slot, the lower-right round cutout, and the
bottom center outer void must contain no blue paint, no shadows, no hardware,
no texture, and no decorative marks.

Preserve this composition logic while repainting it as one unified image:

- A continuous blue watercolor panel body follows the irregular top-temp
  silhouette, with a dark blue ink outline, rounded edge lip, uneven pigment
  granulation, soft pooled shadows, and small upper-left highlights.
- In the upper-left tall bay, place three vertical colored pins or knobs
  similar to the reference knobs: red, yellow, and mint/teal cylinders on dark
  blue washer bases. Keep them clear of the outer edge and well left of the
  diagonal slot.
- In the middle-left field, paint a compact bank of three or four horizontal
  slider rails with small colored square nubs. The rails must stop before the
  diagonal slot and must not be clipped by it.
- In the lower-left base bay, paint one round gauge/dial with a blue rim, pale
  watercolor face, tick marks, and a dark pointer. It may sit near the lower
  edge but must stay inside the material. Add two or three stacked rounded
  capsule buttons nearby, using red, yellow, and teal accents.
- In the lower-middle bay to the right of the center bottom opening, paint two
  or three rounded capsule controls inspired by the references. Keep them away
  from the lower-right round cutout and the bottom notch.
- In the narrow right vertical strip, paint one or two small screw heads above
  and below the circular cutout if there is room. Do not place a screw or any
  shadow inside the circular cutout.
- Add richer reference-style details: white tick marks, small blue washer
  shadows, soft watercolor blooms, slightly irregular ink edges, pale highlight
  streaks on buttons, subtle paper texture, and blue edge-darkening.

Style requirements:

- Match the actual references in object vocabulary: friendly control-panel
  dials, sliders, rounded buttons, small colored pins, screw heads, washers,
  soft blue panel body.
- Match the references in rendering: watercolor texture, soft highlights,
  irregular blue ink outlines, gentle shadow pooling under raised controls, and
  simple rounded shapes.
- Keep the design playful and clean, not dense machinery. The panel should look
  like it belongs to the same watercolor family as the two attached source
  references.

Hard negative rules:

- Do not create a generic rectangular control panel and crop it into the
  silhouette.
- Do not fill the diagonal slot, lower-right round cutout, or bottom center void
  with blue paint, texture, shadows, outlines, bolts, controls, or any other
  marks.
- Do not let focal motifs cross production cuts, cutout edges, or the outer
  contour.
- Do not use procedural sprite placement, visible collage seams, pasted cutouts,
  hard vector UI, glossy app icons, photoreal metal, dark machinery, labels,
  text, arrows, grid lines, or extra holes.

## Variant Notes

For a small batch, run three variants from the same prompt:

- `balanced-hybrid`: closest to B/C, with moderate control density.
- `reference-rich`: more reference-style tick marks, washer shadows, and edge
  highlights, but still clear of cutouts.
- `quiet-background`: fewer controls, more blue watercolor body texture, useful
  if the model tends to crowd the slot.
