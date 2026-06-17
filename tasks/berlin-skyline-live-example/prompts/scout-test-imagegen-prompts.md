# Berlin Skyline Image-Generation Scout Prompts

Date: 2026-06-16

These prompts were used as early scout tests after the user noted that the
scripted A/B/C placement boards looked too similar and might not be useful
wireframes for full image generation.

The generated image outputs were displayed in the chat by the image-generation
tool and were not saved as local files. The local scripted scout board remains
under `outputs/reviews/scout-tests/`.

## Scout A: Three-Route Contact Sheet

Purpose: test whether image generation can produce visibly different composition
routes from the same Berlin skyline constraints.

```text
Create one wide review contact sheet with THREE rough concept thumbnails for a Screenery Berlin skyline/city-scape collection. This is an early scout test, not final art.

Use the user's provided Berlin 4-panel render as the primary art-style reference: delicate watercolor and colored pencil, soft pastel palette, pale paper texture, thin sketch lines, gentle shading, childlike but architectural, white/removable sky background. Use the user's Ritz-Carlton / Beisheim / Potsdamer Platz reference for the right high-rise, including its lower podium/base section.

Each thumbnail shows the SAME 3-panel product template concept: left narrow panel, large central saloon-door panel with two arched lower flaps, right narrow panel. Do not make a generic rectangle crop. Design the city inside these panel shapes. Keep sky/background pure white/paper-white.

Required Berlin elements across the set: Fernsehturm, Brandenburg Gate, Berliner Dom, Kaiser Wilhelm Memorial Church tower/spire, Ritz-Carlton/Beisheim/Potsdamer Platz high-rise with lower base, yellow Berlin U-Bahn train, bridge/viaduct arch over quiet water/stone. Do not include the green traffic-light/clock tower.

Hard composition rules: landmarks and recognizable features must remain whole inside panels; no building/landmark split by panel seams; U-Bahn may run through as infrastructure but train doors/windows should not land on seams; bridge/viaduct arch should support the central saloon-door arch; top contour should trace the skyline silhouette: TV tower, gate dip, Dom dome/cross, church tower, hotel crown. Avoid putting focal details where red dashed safety zones would be: vertical red no-detail strips near panel interiors and wavy horizontal separators between top and bottom sub-panels.

Make the three thumbnails genuinely different:
1. Reference-faithful rhythm: like the source render, TV tower + Brandenburg Gate left, Dom + church central, hotel right, low U-Bahn.
2. Strong saloon arch hero: bridge/viaduct arch dominates the central lower saloon flaps, landmarks arranged above it.
3. Continuous city band: U-Bahn/rail/water/bridge form a strong horizontal spine across all panels while landmarks sit safely within their panels.

Use faint panel outlines and very faint dashed safety guides only as review guides. No labels or text inside the artwork. Keep all sky areas white.
```

## Scout B: Direct Whole-Scene Control

Purpose: test whether a direct prompt can produce a cohesive Berlin skyline
without a placement map.

```text
Create a single rough early scout illustration for a Screenery Berlin skyline/city-scape collection using a 3-panel product template: left narrow panel, one large central saloon-door panel with two arched lower flaps, and right narrow panel. This is a direct whole-scene control test, not final production art.

Art style: match the user's provided Berlin render: delicate watercolor and colored pencil architectural illustration, pale pastel palette, soft paper-white background, thin hand sketch linework, gentle shading, airy white sky. Use the user's Ritz-Carlton / Beisheim / Potsdamer Platz photo for the right high-rise, including the lower podium/base.

Required composition:
- Left narrow panel: Fernsehturm and Brandenburg Gate, both whole and not cut by seams.
- Central large saloon-door panel: Berliner Dom and Kaiser Wilhelm Memorial Church tower/spire, with a bridge/viaduct arch over quiet water or stone that fits the central saloon-door arch area.
- Right narrow panel: Ritz-Carlton / Beisheim / Potsdamer Platz high-rise with its lower podium/base, whole inside the panel.
- A yellow Berlin U-Bahn train runs low across the set as quiet infrastructure; make the train body continuous, but keep doors/windows away from panel seams and red safety zones.
- Keep sky/background completely white or paper-white.
- Top contour should trace the skyline silhouette: TV tower, gate dip, Dom dome/cross, church tower, hotel crown.

Show faint template guides for review: black panel borders, very faint yellow safe margins, faint red vertical no-detail rectangles and wavy horizontal separators, and faint green top contour. Do not place recognizable details on the red guide zones. Do not include the green traffic-light/clock tower. Do not add labels or text.
```

## Scout C: Strict Red-Zone Guard

Purpose: test whether a stricter prompt can make the model keep specific
features clear of red zones and seams.

```text
Create a single rough early scout illustration for the same Screenery Berlin skyline 3-panel product template, but this time the PRIMARY test is red-zone and seam safety. Use delicate watercolor and colored pencil style matching the user's Berlin render reference, with pure white/paper-white sky.

Template structure: left narrow panel, large central saloon-door panel with two arched lower flaps, right narrow panel. Show faint black panel borders, faint yellow safe margins, faint red dashed danger zones, and faint green top contour as review guides.

CRITICAL SAFETY RULES:
- Treat every red dashed vertical rectangle as a blank/quiet lane. No train doors, train windows, building windows, signs, statues, columns, distinctive roof details, birds, text, faces, or iconic details may touch or cross those red vertical lanes.
- Treat the wavy red horizontal separators as quiet transition bands. Only sky, plain wall texture, water, rail, or solid train body may pass through them.
- Panel seams may not split any building, landmark, statue, arch tower, train door, train window, sign, or distinctive feature.
- The U-Bahn may run through all panels, but over seams/red lanes it must be a plain yellow body strip with no visible windows or doors.

Required Berlin content, safely placed:
- Left narrow panel: Fernsehturm high in the safe open area; Brandenburg Gate lower but whole, with Quadriga not touching red lanes.
- Central panel: Berliner Dom and Kaiser Wilhelm Memorial Church tower/spire, each whole and clear of red lanes; a simplified bridge/viaduct arch fits the saloon-door arch area without placing bridge towers on seams.
- Right narrow panel: Ritz-Carlton / Beisheim / Potsdamer Platz high-rise with full lower podium/base, shifted so no distinctive window columns or entrance details fall on red lanes.
- Exclude the green traffic-light/clock tower.
- Top contour traces the actual landmark silhouettes: TV tower, gate dip, Dom dome/cross, church tower, hotel crown.

This is a rough scout, not final art. Make the composition readable and clean rather than overly detailed. No labels or explanatory text.
```
