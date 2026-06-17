# Prompt B: Style-Transfer Elements

## Intent

Generate a broader element library by transferring the packet style onto a
specified set of isolated control parts. This variant tests whether the style
agent can use actual packet images to make new but compatible elements without
drifting into generic UI art.

## Attach These Packet Crops

Attach these 10 images, not the full 24-crop packet:

- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-left-region.png`
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-center-region.png`
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-right-region.png`
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-body-texture.png`
- `tasks/top-temp-workflow-test/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-edge-treatment.png`
- `tasks/top-temp-workflow-test/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-center-region.png`
- `tasks/top-temp-workflow-test/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-edge-treatment.png`
- `tasks/top-temp-workflow-test/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-accent-component-01.png`
- `tasks/top-temp-workflow-test/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-accent-component-02.png`
- `tasks/top-temp-workflow-test/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-accent-component-03.png`

## Generation Prompt

Study the attached packet crops visually before generating. Treat them as the
style source, not as a loose mood description.

Generate an isolated watercolor control-part library on a white or transparent
background. The parts may be new arrangements, but every rendered decision
should be traceable to the packet crops: line quality, fill texture, color
mixing, bevel softness, highlight shape, shadow placement, and friendly
rounded geometry.

Create these separate, reusable elements:

- 2 large circular dials and 2 small circular dial fragments;
- 4 capsule buttons in red, teal, yellow, and pale orange;
- 5 vertical pins or pegs with dark blue base washers;
- 4 short slider rails with small square colored nubs;
- 4 tiny screws or bolt heads;
- 3 blue edge, corner, or body-texture patches for later geometry placement.

Keep generous spacing between elements so a geometry agent can cut or place
each one independently. Use the same watercolor paper feel and blue panel
language as the packet, but do not make a full panel or template layout.

Negative constraints:

- no flat vector icons;
- no glossy app UI;
- no photoreal metal;
- no dark machine panel;
- no final SVG contour, diagonal slot, yellow safe area, or cutout;
- no labels or explanatory text inside the image.

## Handoff Note To Return With The Image

Return a concise provenance note mapping each element family to the exact packet
crops used. Mark any element that feels invented beyond the packet as `PARTIAL`
or `RETRY`.

