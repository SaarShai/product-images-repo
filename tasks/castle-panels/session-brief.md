# Castle Panels Prompt Test

## Objective

Create and test three image-generation prompts for a new fairytale castle
illustration that matches the uploaded watercolor reference style while fitting
a two-panel die-line template.

Current status: active system workflow. Use `tasks/castle-panels/CURRENT.md` for
the latest candidate, score reports, and promotion gate.

## Assets

- Style reference:
  `assets/reference-images/castle-style-reference.png`
- Raster template:
  `assets/templates/two-panel-template-raster.png`
- Adapted contour examples:
  `assets/reference-images/adapted-contour-example-1.png`
  `assets/reference-images/adapted-contour-example-2.png`
- Expected SVG location:
  `assets/templates/two-panel-template.svg`

## Important Rules

- Artwork must stay inside the safe area.
- The margin between outer cut line and safe area must remain blank.
- Red dashed rectangles are no-feature zones.
- The central vertical slot must remain clear.
- The horizontal panel divide must not cut important elements.
- If the middle is filled, it may contain only quiet background such as plain
  wall, masonry, path, grass, or empty white. It must not contain birds,
  butterflies, fairies, windows, flowers, or other recognizable motifs.
- The top contour should adapt to the castle skyline, not remain a generic arch.
- Final outputs should remove dashed construction guides and show clean final
  cut lines only.

## Prompt Variants

- Prompt A: strict geometry-first.
- Prompt B: balanced geometry and composition.
- Prompt C: contour-first / illustration-led.

## SVG Check

The authoritative SVG is now present at
`assets/templates/two-panel-template.svg`. The first generation pass happened
before the SVG was available, so those outputs should be treated as prompt
behavior tests rather than production-accurate geometry tests.

## Current System Check

Run `python3 scripts/verify_setup.py` for setup. Run
`python3 scripts/score_template_fit.py --help` for the candidate scoring gate.
