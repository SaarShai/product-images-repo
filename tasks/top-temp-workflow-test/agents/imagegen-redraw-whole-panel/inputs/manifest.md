# Input Manifest

These files were copied into this agent folder so the prompt package can be run
without mutating shared task-level assets.

## Composition References

- `composition-b-style-imagegen-fit-preview-white.png`: prior style-imagegen-fit
  candidate. Stronger vivid controls; less cohesive as a whole-panel redraw.
- `composition-c-style-matte-elements-preview-white.png`: prior
  style-matte-elements candidate. Softer reference crop texture and richer
  slider density; still visibly assembled from elements.

## Style References

- `style-ref-01-slider-panel.png`: long rounded blue panel with slider bank,
  stacked capsule buttons, gauge, right-side bars, blue edge lip, and watercolor
  texture.
- `style-ref-02-knob-panel.png`: long rounded blue panel with colored pins on
  dark blue washers, corner screws, two large dials, white tick marks, and
  watercolor texture.
- `reference-contact-sheet.png`: existing style-packet contact sheet.
- `style-exemplar-sheet.png`: existing style-packet exemplar sheet.

## Geometry

- `template.svg`: source SVG copied from
  `tasks/top-temp-workflow-test/source/template.svg`.
- `input-contact-sheet.png`: combined contact sheet made from the two
  composition references and the two style references for image tools that
  accept a single visual board.
