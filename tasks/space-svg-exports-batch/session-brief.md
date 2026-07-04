# Space SVG Exports Batch

## Goal

Create template-constrained watercolor control-panel illustrations for every
eligible non-top SVG in:

`<DRIVE_ROOT>/Wanderland Folder/Files/Products/Screenery/production files/space/svg-exports`

Exclude `np01-front-top.svg`, `np01-back-top.svg`, `np02-front-top.svg`, and
`np02-back-top.svg`.

The checkpoint produced two versions for `np01-back-bottom.svg`. After
continuation, the batch produced two versions for each eligible bottom SVG.

## Style Source

Use the successful top-temp watercolor control-panel family as visual evidence,
not prose memory:

- `refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png`
- `refs/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png`
- `style-packet/reference-contact-sheet.png`
- `style-packet/style-exemplar-sheet.png`
- `style-packet/style-packet.json`

Style cues to preserve:

- blue watercolor body texture;
- dark blue rim lines;
- slight bevel and soft inner shadow around outer contour and cutouts;
- pale edge highlights;
- rounded red, yellow, and mint controls;
- simple knobs, switches, monitors, circuitry, sockets, sliders, and dials.

## Geometry Rules

- SVG contour geometry is authoritative.
- Large uncontained contours are paintable panel regions.
- Smaller contours contained inside a paintable panel are cutouts or
  keep-clear holes, even when represented as `<path>` instead of `<polygon>`.
- Decorative controls must be placed inside safe pockets before final masking.
- Final masks are export guardrails, not a substitute for composition planning.

## Checkpoint Plan

Initial checkpoint generated two bottom-piece candidates:

- `np01-back-bottom.svg` v1 and v2: tests multi-contour bottom geometry with
  internal path cutouts and a narrow side contour.

Continuation batch generated two versions for each of the four eligible
non-top SVGs:

- `np01-back-bottom.svg`
- `np01-front-bottom.svg`
- `np02-back-bottom.svg`
- `np02-front-bottom.svg`

Review sheets:

- `checkpoints/batch-bottom-all-versions.png`
- `checkpoints/np01-back-bottom-review-sheet.png`
- `checkpoints/np01-front-bottom-review-sheet.png`
- `checkpoints/np02-back-bottom-review-sheet.png`
- `checkpoints/np02-front-bottom-review-sheet.png`

Correction on 2026-06-17: `np01-back-bottom.svg` originally misclassified the
right-side socket/notch contour as paintable because the cutout bite protrudes
slightly beyond the main panel bounds. The shared classifier now treats smaller
contours that substantially intersect a larger paintable contour as cutouts.
`np01-back-bottom` outputs and review sheets were regenerated; the right-side
socket/notch area is now white cutout space.

Second correction on 2026-06-17: the lower-right area of
`np01-back-bottom.svg` was missing because the right panel is exported as an
open `<path>` plus a separate bottom/right `<polyline>`. The parser ignored the
polyline and closed the path diagonally. The classifier now reads polylines and
uses matching polyline closure segments before falling back to automatic path
closure. `np01-back-bottom` outputs and review sheets were regenerated again;
the lower-right panel area is restored while the socket/notch contour remains a
white cutout.

All regenerated batch candidates report zero painted pixels outside the SVG
contour and zero painted pixels inside cutouts. Visual review: contour, cutout
cleanup, rim, and bevel are consistent; internal elements are varied and
reference-colored, but remain more procedural than a full image-generation
watercolor redraw.

## 2026-06-17 Style Adaptation Correction

`np01-back-top-checkpoint-v1-artwork-only.png` is the approved geometry map for
the revised tabbed SVG. Its dimensions, tab locations, contour, and cutouts are
good enough to preserve as the layout/negative-space map.

Do not continue the failed local restyle experiments in `outputs/style-tests/`
or the helper scripts named `test_locked_geometry_style*.py` as the creative
method. Those outputs mechanically lock the SVG and then repaint/texture/collage
inside it, which repeats the wrong procedural style path.

Next style attempt must use the successful top-temp method:

- attach the approved geometry image as a composition map only;
- attach the two original reference panels plus the style packet/contact sheets;
- ask the image model to redraw the entire object as one coherent watercolor
  panel;
- save the raw redraw and exact prompt;
- run exact SVG export/checks only after the raw redraw is visually promising.
