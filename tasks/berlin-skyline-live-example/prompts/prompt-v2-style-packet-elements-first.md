# Prompt V2: Berlin Skyline Style Packet Elements First

Use the attached style packet images as the primary style source. Do not rely on
written style adjectives alone.

## Visual Attachments To Use

Use this focused crop set first:

- `tasks/berlin-skyline-live-example/style-packet/crops/ref02-whatsapp-image-2026-06-16-at-01-31-54-full-panel.png`
- `tasks/berlin-skyline-live-example/style-packet/crops/ref02-whatsapp-image-2026-06-16-at-01-31-54-left-region.png`
- `tasks/berlin-skyline-live-example/style-packet/crops/ref02-whatsapp-image-2026-06-16-at-01-31-54-center-region.png`
- `tasks/berlin-skyline-live-example/style-packet/crops/ref02-whatsapp-image-2026-06-16-at-01-31-54-right-region.png`
- `tasks/berlin-skyline-live-example/style-packet/crops/ref02-whatsapp-image-2026-06-16-at-01-31-54-body-texture.png`
- `tasks/berlin-skyline-live-example/style-packet/crops/ref02-whatsapp-image-2026-06-16-at-01-31-54-edge-treatment.png`
- `tasks/berlin-skyline-live-example/style-packet/crops/ref02-whatsapp-image-2026-06-16-at-01-31-54-accent-component-03.png`
- `tasks/berlin-skyline-live-example/style-packet/crops/ref02-whatsapp-image-2026-06-16-at-01-31-54-accent-component-06.png`
- `tasks/berlin-skyline-live-example/style-packet/crops/ref01-beisheim-center-und-potsdamer-platz-in-ber-full-panel.png`
- `tasks/berlin-skyline-live-example/style-packet/crops/ref01-beisheim-center-und-potsdamer-platz-in-ber-body-texture.png`

## Task

Generate a style-matched Berlin skyline element sheet first, not a final SVG
template composition.

Create separated, reusable watercolor/pencil elements on a white or transparent
background:

- Berlin TV Tower / Fernsehturm silhouette.
- Brandenburg Gate with simplified Quadriga.
- Berlin Cathedral / Berliner Dom dome and facade.
- Kaiser Wilhelm Memorial Church old tower / Memorial Church style
  tower-spire.
- Ritz-Carlton / Beisheim / Potsdamer Platz hotel facade, including the full
  lower podium/base and lower wing visible in the user's reference photo, not
  only the tall tower shaft.
- Low yellow Berlin U-Bahn run-through material: train body, rail, stone, and
  water/base strips. Keep it useful as seam-safe infrastructure rather than as
  a detailed focal train.
- Simplified Berlin bridge or viaduct arch over quiet water/stone. If using a
  named bridge cue, make it Oberbaum Bridge-inspired: red brick, paired bridge
  towers, arches over water, and U-Bahn/viaduct feeling. Do not include
  readable station signs.
- Optional small birds as secondary accents.
- Exclude the green Potsdamer Platz traffic-light/clock tower entirely in this
  first element sheet.

## Required Style Match

- Match the actual Berlin render crops: soft watercolor wash, pale paper,
  subtle paper texture, warm beige stone, muted mint/verdigris domes,
  grey-green metal, Berlin yellow train, terracotta bridge accents.
- Keep contrast gentle and product-friendly.
- Use simplified landmark silhouettes first and tiny ornament second.
- Make the middle landmarks identifiable as Berliner Dom and Kaiser Wilhelm
  Memorial Church, not generic European buildings.
- Use pencil-like outlines and soft uneven edges rather than crisp vector lines.
- Use the palette in `style-packet/style-packet.json`, but do not treat palette
  as the style. Shape language and rendering must also match.

## Geometry Handoff Rules

- Keep elements separate so a geometry agent can place them inside safe pockets.
- Do not draw the final SVG contour, yellow margins, red zones, orange arch, or
  green contour.
- Do not crop a full rectangular Berlin panorama into the template.
- Do not put recognizable details near panel seams or red keep-clear zones.
- If drawing train pieces, include plain carriage-body sections that can cross
  seams without doors, windows, text, people, or birds.
- Generate clean landmark silhouette tops for later adaptive top-contour
  tracing, but do not draw the green contour itself.

## Negative Rules

- No photorealism.
- No glossy 3D.
- No hard vector postcard style.
- No dramatic blue sky background.
- No blue sky backdrop; use transparent, white, or very pale paper-white
  background only.
- No readable text or signage.
- No crowded collage where landmarks are chopped by panel cuts.

## Handoff

Return an element sheet plus a short note naming which packet crops each element
was based on. The geometry agent will place accepted elements into safe pockets
from `template-manifest.json`.
