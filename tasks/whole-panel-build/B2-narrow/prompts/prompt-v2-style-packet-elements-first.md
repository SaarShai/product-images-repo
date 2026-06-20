# Prompt V2: Style Packet Elements First

Use the attached style packet images as the primary style source. Do not rely on
written style adjectives alone.

## Visual Attachments To Use

- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref01-illustration-10-full-panel.png` - ref 1 full panel
- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref02-gauge-pills-full-panel.png` - ref 2 full panel
- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref03-toggles-sliders-full-panel.png` - ref 3 full panel
- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref01-illustration-10-center-region.png` - ref 1 center-region
- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref01-illustration-10-left-region.png` - ref 1 left-region
- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref01-illustration-10-right-region.png` - ref 1 right-region
- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref02-gauge-pills-center-region.png` - ref 2 center-region
- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref02-gauge-pills-left-region.png` - ref 2 left-region
- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref02-gauge-pills-right-region.png` - ref 2 right-region
- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref03-toggles-sliders-center-region.png` - ref 3 center-region
- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref03-toggles-sliders-left-region.png` - ref 3 left-region
- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref03-toggles-sliders-right-region.png` - ref 3 right-region
- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref01-illustration-10-body-texture.png` - ref 1 body-texture
- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref01-illustration-10-edge-treatment.png` - ref 1 edge-treatment
- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref02-gauge-pills-body-texture.png` - ref 2 body-texture
- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref02-gauge-pills-edge-treatment.png` - ref 2 edge-treatment
- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref03-toggles-sliders-body-texture.png` - ref 3 body-texture
- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref03-toggles-sliders-edge-treatment.png` - ref 3 edge-treatment
- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref01-illustration-10-accent-component-01.png` - ref 1 accent component 01
- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref01-illustration-10-accent-component-02.png` - ref 1 accent component 02
- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref01-illustration-10-accent-component-03.png` - ref 1 accent component 03
- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref01-illustration-10-accent-component-04.png` - ref 1 accent component 04
- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref01-illustration-10-accent-component-05.png` - ref 1 accent component 05
- `tasks/whole-panel-build/B2-narrow/style-packet/crops/ref01-illustration-10-accent-component-06.png` - ref 1 accent component 06

## Task

Generate a style-matched element sheet first, not a final template composition.
Create separate control-panel elements that look like they came from the
reference images: dials, sliders, capsule buttons, small bolts, colored pins,
edge/shadow samples, and blue watercolor panel fragments.

## Required Style Match

- Match the actual crops in shape language, line irregularity, watercolor
  bleed, soft highlight placement, outline thickness, shadow pooling, and
  simple friendly object vocabulary.
- Use the palette in `style-packet/style-packet.json`, but do not treat palette
  as the style. The shapes and rendering must also match.
- Keep elements separate on a white or transparent background so geometry agents
  can place them later.
- Do not draw the final SVG contour, diagonal slot, or cutouts. Geometry agents
  handle placement and masks after the style elements are generated.

## Negative Rules

- Do not produce flat vector icons, glossy app UI, hard 3D plastic, photoreal
  metal, dark machinery, or generic blue rectangles.
- Do not crop a full rectangular panel into the template.
- Do not invent a style from memory after reading this prompt. Use the packet
  images directly.

## Handoff

Return an element sheet plus a short note naming which packet crops each element
was based on. The geometry agent will place accepted elements into safe pockets
from `template-manifest.json`.
