# Prompt A: Crop-Faithful Elements

## Intent

Generate a style-matched element sheet by staying close to the actual packet
crops. This variant is for maximum reference fidelity before any geometry agent
places elements into the SVG template.

## Attach These Packet Crops

Attach these 8 images, not the full 24-crop packet:

- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-left-region.png`
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-center-region.png`
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-right-region.png`
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-body-texture.png`
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-edge-treatment.png`
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-accent-component-01.png`
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-accent-component-02.png`
- `tasks/top-temp-workflow-test/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-center-region.png`

## Generation Prompt

Use the attached packet crops as the visual source of truth. Generate a clean
element sheet of isolated control-panel parts that look like they came from
those exact crops.

Create 12 to 16 separated elements on a white or transparent background:

- 3 rounded capsule buttons based on the red, teal, and yellow packet buttons;
- 3 small horizontal slider rails with square colored nubs;
- 2 round dials with blue rims, pale faces, tick marks, and soft white
  highlights;
- 3 to 4 vertical colored pins with dark blue base washers;
- 2 small bolt or screw heads with simple diagonal slots;
- 1 to 2 blue watercolor material or edge swatches.

Stay crop-faithful. Preserve the packet's simple object vocabulary, blue ink
outline weight, slightly uneven hand-painted edges, watercolor granulation,
shadow pooling under raised controls, and soft upper-left highlights. Make each
element feel lifted from the packet family rather than redesigned from memory.

Do not create a final panel, template contour, diagonal slot, cutout, or full
composition. Do not crop a rectangle into the template. Do not add labels,
arrows, UI text, callouts, or measurement marks inside the image.

## Handoff Note To Return With The Image

After the image, return a short provenance note:

- list each generated element group;
- name the packet crop or crops that influenced it;
- mark the style verdict as `REFERENCE-MATCH`, `PARTIAL`, or `RETRY`.

