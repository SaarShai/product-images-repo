# Prompt C: Edit From Packet Crops

## Intent

Use this variant with an image-editing model that can accept multiple source
crops. The goal is to transform actual packet crop pixels into isolated
elements, rather than asking the model to redraw the style from memory.

## Attach These Packet Crops

Attach these 8 images, prioritizing already-isolated component crops:

- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-accent-component-01.png`
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-accent-component-02.png`
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-accent-component-05.png`
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-body-texture.png`
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-edge-treatment.png`
- `tasks/top-temp-workflow-test/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-accent-component-01.png`
- `tasks/top-temp-workflow-test/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-accent-component-02.png`
- `tasks/top-temp-workflow-test/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-accent-component-03.png`

## Image-Edit Prompt

Use the attached crop images as direct source material. Build a new element
sheet by isolating and lightly completing the controls visible in those crops.

Edit behavior:

- lift the capsule buttons, vertical pins, small bars, edge patches, and blue
  texture samples from the attached crops;
- remove surrounding panel fragments where they are not part of the reusable
  element;
- complete clipped or partially hidden edges only where needed, using the same
  watercolor edge, outline, shadow, and highlight logic from the source crop;
- keep each element separate with clean margins;
- preserve the packet's irregular ink outline and watercolor granulation.

Output a transparent PNG if possible. If transparency is not available, output
a white-background sheet with enough spacing that each element can be extracted
later.

Do not generate a final contour composition. Do not invent a new panel. Do not
include the SVG diagonal slot, yellow safe area, or any template cutout. Do not
turn the parts into crisp vector icons or glossy 3D controls.

## Handoff Note To Return With The Image

Return a source map:

- `element id`;
- `source crop path`;
- `edit performed` such as isolated, edge completed, shadow cleaned, or
  color variant;
- style verdict: `REFERENCE-MATCH`, `PARTIAL`, or `RETRY`.

