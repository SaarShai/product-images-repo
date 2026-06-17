# Top Temp Method C: Imagegen Art Director

## Intent

Generate a fresh model-painted candidate for the top-temp control panel. Use
the two accepted B/C method images only as rough control maps for silhouette,
negative-space placement, and broad module distribution. Do not composite,
trace, crop, or preserve their pixels as final art.

## Evidence Used

- Template SVG: `tasks/top-temp-workflow-test/source/template.svg`
- Geometry report: `tasks/top-temp-workflow-test/svg-geometry-report.md`
- Template manifest: `tasks/top-temp-workflow-test/template-manifest.json`
- Rough control map B: `tasks/top-temp-workflow-test/agents/style-imagegen-fit/style-imagegen-fit-preview-white.png`
- Rough control map C: `tasks/top-temp-workflow-test/agents/style-matte-elements/style-matte-elements-preview-white.png`
- Style packet sheets:
  - `tasks/top-temp-workflow-test/style-packet/reference-contact-sheet.png`
  - `tasks/top-temp-workflow-test/style-packet/style-exemplar-sheet.png`

## Meta-Prompt Reasoning

The previous B/C candidates prove a usable layout, but their method is still
too placement-driven: the controls read as sprites or mattes placed onto a blue
body. Method C should ask the image model to reinterpret that evidence into a
single coherent watercolor object.

The prompt therefore separates three inputs:

- Geometry authority: the SVG/template manifest says the diagonal slot and
  lower-right round cutout are empty keep-clear regions. The lower center
  rectangular void is outside the material contour and must also stay white.
- Composition hint: B/C show useful control distribution: upper-left colored
  pins, middle-left slider rows, lower-left dial and pill buttons, lower-middle
  pill controls, and small right-edge hardware.
- Style authority: the style packet controls object vocabulary, blue ink
  outline, watercolor granulation, soft highlights, rounded shapes, and shadow
  pooling.

The final generation prompt asks for one repainted panel, not a cropped
rectangle and not a collage. It also invites believable extra detail only in
safe pockets: small screws, tick marks, fine rails, subtle seams, and tiny
indicator nubs. The empty slot/cutouts are named repeatedly because model
generations often fill negative shapes unless the prompt frames them as
physical holes in the product.

## Done Criteria For This Agent

- `final-prompt.md` records the exact generation prompt.
- At least one generated candidate PNG is saved in this folder.
- Review notes inspect the generated image visually and compare it against the
  SVG cutout intent and style packet.
- Any safety checking is documented as optional post-generation analysis, not
  as procedural compositing.
