# Prompt V2: Style Packet Elements First

Use the attached style packet images as the primary style source. Do not rely on
written style adjectives alone.

## Visual Attachments To Use

- `tasks/whole-panel-build/B4-princess-window/style-packet/crops/ref01-princess01-ref-full-panel.png` - ref 1 full panel
- `tasks/whole-panel-build/B4-princess-window/style-packet/crops/ref02-style-ref-full-panel.png` - ref 2 full panel
- `tasks/whole-panel-build/B4-princess-window/style-packet/crops/ref01-princess01-ref-center-region.png` - ref 1 center-region
- `tasks/whole-panel-build/B4-princess-window/style-packet/crops/ref01-princess01-ref-left-region.png` - ref 1 left-region
- `tasks/whole-panel-build/B4-princess-window/style-packet/crops/ref01-princess01-ref-right-region.png` - ref 1 right-region
- `tasks/whole-panel-build/B4-princess-window/style-packet/crops/ref02-style-ref-center-region.png` - ref 2 center-region
- `tasks/whole-panel-build/B4-princess-window/style-packet/crops/ref02-style-ref-left-region.png` - ref 2 left-region
- `tasks/whole-panel-build/B4-princess-window/style-packet/crops/ref02-style-ref-right-region.png` - ref 2 right-region
- `tasks/whole-panel-build/B4-princess-window/style-packet/crops/ref01-princess01-ref-body-texture.png` - ref 1 body-texture
- `tasks/whole-panel-build/B4-princess-window/style-packet/crops/ref01-princess01-ref-edge-treatment.png` - ref 1 edge-treatment
- `tasks/whole-panel-build/B4-princess-window/style-packet/crops/ref02-style-ref-body-texture.png` - ref 2 body-texture
- `tasks/whole-panel-build/B4-princess-window/style-packet/crops/ref02-style-ref-edge-treatment.png` - ref 2 edge-treatment
- `tasks/whole-panel-build/B4-princess-window/style-packet/crops/ref02-style-ref-accent-component-01.png` - ref 2 accent component 01
- `tasks/whole-panel-build/B4-princess-window/style-packet/crops/ref02-style-ref-accent-component-02.png` - ref 2 accent component 02
- `tasks/whole-panel-build/B4-princess-window/style-packet/crops/ref02-style-ref-accent-component-03.png` - ref 2 accent component 03
- `tasks/whole-panel-build/B4-princess-window/style-packet/crops/ref02-style-ref-accent-component-04.png` - ref 2 accent component 04
- `tasks/whole-panel-build/B4-princess-window/style-packet/crops/ref02-style-ref-accent-component-05.png` - ref 2 accent component 05
- `tasks/whole-panel-build/B4-princess-window/style-packet/crops/ref02-style-ref-accent-component-06.png` - ref 2 accent component 06
- `tasks/whole-panel-build/B4-princess-window/style-packet/crops/ref02-style-ref-accent-component-07.png` - ref 2 accent component 07

## Task

Generate a style-matched element sheet first, not a final template composition.
Create separate fairy-tale castle elements that look like they came from the
reference images: delicate towers and turrets, slender spires, terracotta
conical roofs (with small gold finial balls), cream/ivory stone walls,
cascading roses and trailing green vines, small winged fairies, an arched
wooden window/door, plus accent details (pennant flags, butterflies, arched
amber windows, edge/shadow samples).

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
  stone, dark/gloomy fortress mood, or generic gray rectangles.
- Do not crop a full rectangular panel into the template.
- Do not invent a style from memory after reading this prompt. Use the packet
  images directly.

## Handoff

Return an element sheet plus a short note naming which packet crops each element
was based on. The geometry agent will place accepted elements into safe pockets
from `template-manifest.json`.
