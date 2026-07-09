# Prompt V2: Style Packet Elements First

Use the attached style packet images as the primary style source. Do not rely on
written style adjectives alone.

## Visual Attachments To Use

- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref01-christmas-elements-watercolor-full-panel.png` - ref 1 full panel
- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref02-watercolor-gingerbread-cookies-full-panel.png` - ref 2 full panel
- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref03-watercolor-ornaments-full-panel.png` - ref 3 full panel
- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref04-watercolor-snowflake-full-panel.png` - ref 4 full panel
- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref01-christmas-elements-watercolor-center-region.png` - ref 1 center-region
- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref01-christmas-elements-watercolor-left-region.png` - ref 1 left-region
- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref01-christmas-elements-watercolor-right-region.png` - ref 1 right-region
- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref02-watercolor-gingerbread-cookies-center-region.png` - ref 2 center-region
- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref02-watercolor-gingerbread-cookies-left-region.png` - ref 2 left-region
- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref02-watercolor-gingerbread-cookies-right-region.png` - ref 2 right-region
- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref03-watercolor-ornaments-center-region.png` - ref 3 center-region
- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref03-watercolor-ornaments-left-region.png` - ref 3 left-region
- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref03-watercolor-ornaments-right-region.png` - ref 3 right-region
- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref04-watercolor-snowflake-center-region.png` - ref 4 center-region
- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref04-watercolor-snowflake-left-region.png` - ref 4 left-region
- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref04-watercolor-snowflake-right-region.png` - ref 4 right-region
- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref01-christmas-elements-watercolor-body-texture.png` - ref 1 body-texture
- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref01-christmas-elements-watercolor-edge-treatment.png` - ref 1 edge-treatment
- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref02-watercolor-gingerbread-cookies-body-texture.png` - ref 2 body-texture
- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref02-watercolor-gingerbread-cookies-edge-treatment.png` - ref 2 edge-treatment
- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref03-watercolor-ornaments-body-texture.png` - ref 3 body-texture
- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref03-watercolor-ornaments-edge-treatment.png` - ref 3 edge-treatment
- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref04-watercolor-snowflake-body-texture.png` - ref 4 body-texture
- `tasks/festive-v1-gingerbread-candidates/style-packet/crops/ref04-watercolor-snowflake-edge-treatment.png` - ref 4 edge-treatment

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
