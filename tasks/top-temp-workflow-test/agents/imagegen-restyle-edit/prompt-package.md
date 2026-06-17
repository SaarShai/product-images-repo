# Top Temp Method B - Imagegen Restyle/Edit Prompt Package

Date: 2026-06-16

## Experiment Goal

Restyle/edit the existing B/C rough results as image inputs. Preserve the
template silhouette, diagonal slot, lower-right round cutout, lower center
opening, notches, and all white voids. Redraw the whole painted surface into the
actual reference watercolor control-panel style with cohesive lighting, richer
blue panel material, and better reference-style controls.

This is an image-generation edit/restyle experiment, not a procedural placement
experiment.

## Local Inputs Copied Into This Folder

- `input-b-style-imagegen-fit-preview-white.png`
  - Source: `tasks/top-temp-workflow-test/agents/style-imagegen-fit/style-imagegen-fit-preview-white.png`
  - Role: structural input B; preserve silhouette/cutouts/overall control placement.
- `input-c-style-matte-elements-preview-white.png`
  - Source: `tasks/top-temp-workflow-test/agents/style-matte-elements/style-matte-elements-preview-white.png`
  - Role: structural input C; preserve silhouette/cutouts/overall control placement.
- `style-exemplar-sheet.png`
  - Source: `tasks/top-temp-workflow-test/style-packet/style-exemplar-sheet.png`
  - Role: style vocabulary and crop contact sheet.
- `reference-ref01-watercolor-panel.png`
  - Source: `tasks/top-temp-workflow-test/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png`
  - Role: strongest single reference for watercolor texture, blue panel material,
    edge treatment, and control lighting.

## Shared Edit Constraints

- Keep the exact outer template silhouette from the structural input.
- Keep the diagonal rounded slot completely white and open; do not paint into it.
- Keep the lower-right round cutout completely white and open; do not paint into it.
- Keep the lower center rectangular opening and bottom notches white/open.
- Do not move, resize, erase, or invent cutouts.
- Do not add labels, text, arrows, stickers, UI icons, logos, or technical callouts.
- Do not make the surface flat vector art, glossy app UI, dark metal, sci-fi,
  photoreal, or 3D-rendered.
- Redraw the blue panel body as watercolor: richer cobalt/sky-blue wash,
  irregular pigment granulation, dark blue ink perimeter, soft pooled shadows,
  and soft white edge highlights.
- Redraw the controls so they look like they came from the references: rounded
  capsule buttons, dials, pins, slider rails, screw heads, uneven blue outlines,
  translucent watercolor fills, soft highlights, and consistent top-left light.
- Keep the whole panel on a clean white background.
- Output the same square-ish product view as the input, not a new rectangular
  control-panel reference.

## Prompt B Edit - From `style-imagegen-fit`

Use Image #1 as the structural input. Preserve its exact product silhouette,
white background, white diagonal slot, white lower-right round cutout, white
lower center opening, bottom notches, and rough placement of controls.

Use Image #3 and Image #4 only as watercolor style references. Redraw the entire
painted blue surface and all controls in that reference style: richer blue
watercolor panel material, dark uneven blue ink outlines, soft pooled shadows,
granulated paper texture, gentle top-left lighting, rounded toy-like hardware,
capsule buttons with translucent highlights, watercolor dials and pins, and
simple friendly control-panel vocabulary.

The result should look like the existing silhouette was repainted by the same
artist who made the reference control panels. Improve cohesion and material
quality while keeping the template and holes unchanged.

Critical preservation checks: no paint in the diagonal slot, no paint in the
lower-right round cutout, no paint in the lower center opening, no moved or
invented cutouts, no cropped-through controls.

## Prompt C Edit - From `style-matte-elements`

Use Image #2 as the structural input. Preserve its exact product silhouette,
white background, white diagonal slot, white lower-right round cutout, white
lower center opening, bottom notches, and rough placement of controls.

Use Image #3 and Image #4 only as watercolor style references. Redraw the entire
painted blue surface and all controls in that reference style: richer blue
watercolor panel material, dark uneven blue ink outlines, soft pooled shadows,
granulated paper texture, gentle top-left lighting, rounded toy-like hardware,
capsule buttons with translucent highlights, watercolor dials and pins, and
simple friendly control-panel vocabulary.

The result should reduce the pasted-collage feel and make the lighting,
shadows, panel texture, and controls belong to one continuous watercolor
painting while preserving the exact template holes and silhouette.

Critical preservation checks: no paint in the diagonal slot, no paint in the
lower-right round cutout, no paint in the lower center opening, no moved or
invented cutouts, no cropped-through controls.

## Review Criteria

- Geometry/cutouts: silhouette and all white voids match the input closely.
- Style: watercolor material and controls match the style packet beyond palette.
- Cohesion: lighting and shadows look like one painting, not placed sprites.
- Production risk: no model-imagined cutouts, no scars/halos around holes, no
  visible rescue crop through important controls.
