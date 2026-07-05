# Prompt V2: Style Packet Elements First

Use the attached style packet images as the primary style source. Do not rely on
written style adjectives alone.

## Visual Attachments To Use

- `tasks/marriott-hospital/style-packet/crops/ref01-birds-nest-full-panel.png` - ref 1 full panel
- `tasks/marriott-hospital/style-packet/crops/ref02-police-station-full-panel.png` - ref 2 full panel
- `tasks/marriott-hospital/style-packet/crops/ref03-updated-fire-station-full-panel.png` - ref 3 full panel
- `tasks/marriott-hospital/style-packet/crops/ref04-updated-hospital-1-full-panel.png` - ref 4 full panel
- `tasks/marriott-hospital/style-packet/crops/ref05-updated-kitchen-3-full-panel.png` - ref 5 full panel
- `tasks/marriott-hospital/style-packet/crops/ref06-water-cube-full-panel.png` - ref 6 full panel
- `tasks/marriott-hospital/style-packet/crops/ref01-birds-nest-center-region.png` - ref 1 center-region
- `tasks/marriott-hospital/style-packet/crops/ref01-birds-nest-left-region.png` - ref 1 left-region
- `tasks/marriott-hospital/style-packet/crops/ref01-birds-nest-right-region.png` - ref 1 right-region
- `tasks/marriott-hospital/style-packet/crops/ref02-police-station-center-region.png` - ref 2 center-region
- `tasks/marriott-hospital/style-packet/crops/ref02-police-station-left-region.png` - ref 2 left-region
- `tasks/marriott-hospital/style-packet/crops/ref02-police-station-right-region.png` - ref 2 right-region
- `tasks/marriott-hospital/style-packet/crops/ref03-updated-fire-station-center-region.png` - ref 3 center-region
- `tasks/marriott-hospital/style-packet/crops/ref03-updated-fire-station-left-region.png` - ref 3 left-region
- `tasks/marriott-hospital/style-packet/crops/ref03-updated-fire-station-right-region.png` - ref 3 right-region
- `tasks/marriott-hospital/style-packet/crops/ref04-updated-hospital-1-center-region.png` - ref 4 center-region
- `tasks/marriott-hospital/style-packet/crops/ref04-updated-hospital-1-left-region.png` - ref 4 left-region
- `tasks/marriott-hospital/style-packet/crops/ref04-updated-hospital-1-right-region.png` - ref 4 right-region
- `tasks/marriott-hospital/style-packet/crops/ref05-updated-kitchen-3-center-region.png` - ref 5 center-region
- `tasks/marriott-hospital/style-packet/crops/ref05-updated-kitchen-3-left-region.png` - ref 5 left-region
- `tasks/marriott-hospital/style-packet/crops/ref05-updated-kitchen-3-right-region.png` - ref 5 right-region
- `tasks/marriott-hospital/style-packet/crops/ref06-water-cube-center-region.png` - ref 6 center-region
- `tasks/marriott-hospital/style-packet/crops/ref06-water-cube-left-region.png` - ref 6 left-region
- `tasks/marriott-hospital/style-packet/crops/ref06-water-cube-right-region.png` - ref 6 right-region

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
