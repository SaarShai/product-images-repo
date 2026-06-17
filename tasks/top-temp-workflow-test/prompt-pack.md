# Prompt Pack: top-temp-workflow-test

Use the same reference assets for every prompt variant.

## prompt-v1-contour-first

# Prompt V1: Contour-First

Create an illustration for the attached SVG template. The SVG contour and its
internal cutouts are hard geometry constraints.

Design the composition inside the shape from the start:

- place focal motifs only in safe pockets inside the contour;
- route all modules, figures, pipes, vines, buildings, or details around
  internal cutouts and keep-clear zones;
- keep production seams and slots free of recognizable motifs;
- allow only quiet background texture to cross seams when the task brief says it
  is acceptable;
- do not create a full rectangular scene and crop or erase it into the shape.

Match the attached style references in object vocabulary, palette, line weight,
lighting, density, shape simplicity, and material rendering.

The final artwork should already respect the template before any export mask is
applied.

## prompt-v2-style-packet-elements-first

# Prompt V2: Style Packet Elements First

Use the attached style packet images as the primary style source. Do not rely on
written style adjectives alone.

## Visual Attachments To Use

- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-full-panel.png` - ref 1 full panel
- `tasks/top-temp-workflow-test/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-full-panel.png` - ref 2 full panel
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-center-region.png` - ref 1 center-region
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-left-region.png` - ref 1 left-region
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-right-region.png` - ref 1 right-region
- `tasks/top-temp-workflow-test/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-center-region.png` - ref 2 center-region
- `tasks/top-temp-workflow-test/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-left-region.png` - ref 2 left-region
- `tasks/top-temp-workflow-test/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-right-region.png` - ref 2 right-region
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-body-texture.png` - ref 1 body-texture
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-edge-treatment.png` - ref 1 edge-treatment
- `tasks/top-temp-workflow-test/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-body-texture.png` - ref 2 body-texture
- `tasks/top-temp-workflow-test/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-edge-treatment.png` - ref 2 edge-treatment
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-accent-component-01.png` - ref 1 accent component 01
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-accent-component-02.png` - ref 1 accent component 02
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-accent-component-03.png` - ref 1 accent component 03
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-accent-component-04.png` - ref 1 accent component 04
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-accent-component-05.png` - ref 1 accent component 05
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-accent-component-06.png` - ref 1 accent component 06
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-accent-component-07.png` - ref 1 accent component 07
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-accent-component-08.png` - ref 1 accent component 08
- `tasks/top-temp-workflow-test/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-accent-component-01.png` - ref 2 accent component 01
- `tasks/top-temp-workflow-test/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-accent-component-02.png` - ref 2 accent component 02
- `tasks/top-temp-workflow-test/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-accent-component-03.png` - ref 2 accent component 03
- `tasks/top-temp-workflow-test/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-accent-component-04.png` - ref 2 accent component 04

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
