# Checkpoint 1: Source And Composition Plan

Date: 2026-06-16

This checkpoint has no generated candidate yet. It asks for approval of the
source packet, landmark read, composition strategy, and next process before
image generation.

## Evidence Inspected

- Source template: `tasks/berlin-skyline-live-example/source/template.svg`
- Render/style reference:
  `tasks/berlin-skyline-live-example/refs/WhatsApp Image 2026-06-16 at 01.31.54.jpeg`
- Ritz-Carlton/Beisheim/Potsdamer Platz reference:
  `tasks/berlin-skyline-live-example/refs/Beisheim-Center_und_Potsdamer_Platz_in_Berlin_(2013)_(cropped).jpg`
- Style packet:
  `tasks/berlin-skyline-live-example/style-packet/reference-contact-sheet.png`
- Style packet exemplars:
  `tasks/berlin-skyline-live-example/style-packet/style-exemplar-sheet.png`
- Style packet JSON:
  `tasks/berlin-skyline-live-example/style-packet/style-packet.json`
- Visual approval board:
  `tasks/berlin-skyline-live-example/outputs/reviews/checkpoint-1-approval-board.png`
- Skyline workflow:
  `docs/skyline-template-illustration-workflow.md`
- Geometry reporter attempt:
  `perl -e 'alarm shift; exec @ARGV' 10 python3 scripts/svg_geometry_report.py tasks/berlin-skyline-live-example/source/template.svg --out tasks/berlin-skyline-live-example/svg-geometry-report.md`
  exited `142` and did not create `svg-geometry-report.md`; the manifest is
  filled from direct SVG role inspection and skyline workflow rules.

## Landmark Read

High confidence:

- Berlin TV Tower / Fernsehturm.
- Brandenburg Gate with Quadriga.
- Berlin Cathedral / Berliner Dom.
- Yellow Berlin U-Bahn train.
- Ritz-Carlton / Beisheim Center / Potsdamer Platz high-rise family.

Medium confidence:

- Kaiser Wilhelm Memorial Church: the central church tower resembles the old
  tower/spire silhouette, but the render is stylized.
- Red-brick bridge/station infrastructure: likely a stylized Berlin bridge or
  Potsdamer Platz station/bridge hybrid rather than a literal one-to-one
  landmark.
- Green clock/traffic tower: likely the historic Potsdamer Platz traffic-light
  tower; it appears as a separate right-side panel/object in the reference.

## Style Read

- Soft watercolor and pencil illustration.
- Low contrast, friendly product/toy feel.
- Pale removable sky, light cloud texture, and lots of white paper.
- Warm beige stone, muted mint/verdigris domes, grey-green metal, Berlin yellow
  train, terracotta bridge accents.
- Simplified landmark silhouettes first; tiny ornament and windows second.
- Small birds are allowed only as safe secondary accents away from seams and red
  keep-clear zones.

## Recommended Strategy

Start with a whole-set composition plan, then generate/repair panel-aware
details.

Reason: the yellow U-Bahn, base rail/ground band, water/bridge band, and skyline
top contour need to read as one family across all three physical panels. A
panel-by-panel start would likely produce three attractive but disconnected
postcards.

## Proposed Three-Panel Allocation

Left narrow panel:

- Fernsehturm as the tall silhouette.
- Brandenburg Gate as the lower/wider landmark.
- Yellow U-Bahn entering low across the panel.

Central door panel:

- Berliner Dom as the main dome.
- Kaiser Wilhelm Memorial Church style tower/spire as the vertical counterpoint.
- A simplified Berlin bridge/station/water/embankment motif low in the panel.
- The bridge or viaduct arch echoes the orange saloon-door guide.

Right narrow panel:

- Ritz-Carlton / Beisheim Center / Potsdamer Platz high-rise as the main
  vertical landmark.
- Optional simplified Potsdamer Platz traffic-light/clock tower only if it does
  not overcrowd the narrow panel. Otherwise treat it as the ignored extra panel.

## Run-Through Element Plan

- Primary run-through element: yellow U-Bahn, low across the set.
- Let train body, rail, stone base, or embankment cross seams.
- Keep train doors/windows, birds, text, signage, and people away from seams and
  red zones.
- A low water/bridge/ground band may continue through the central panel to bind
  the set, but bridge towers/signs/decorative arch details must stay wholly in
  safe pockets.

## Saloon-Door Arch Plan

Use a simplified Berlin bridge/viaduct arch centered in the central door panel
to echo the orange saloon-door arch. It should fit the arch generally, not
trace it mathematically. If it becomes too busy, simplify to one warm
brick/stone arch over quiet water.

## Top-Contour Plan

- Left narrow panel: rise around the Fernsehturm, dip over Brandenburg Gate.
- Central door panel: trace Berliner Dom, church tower/spire, and selected
  bridge/station roof forms.
- Right narrow panel: follow the Beisheim/Potsdamer high-rise crown and any
  simplified traffic-light tower roof if included.
- Keep fragile antennas and tiny tips short/thick enough to be production-safe.

## No-Focal Zones

Avoid seams, red dashed separators, red rectangles, and door cuts for:

- TV tower sphere/antenna.
- Brandenburg Quadriga.
- Cathedral dome cross.
- Church spire tips.
- Beisheim roof crown.
- Clock faces and traffic-light lenses.
- U-Bahn doors/windows.
- Birds, people, text, signs.
- Bridge towers and decorative arch details.

Allowed through risky zones:

- plain train body;
- rail line;
- quiet stone/water/ground band;
- generic facade texture;
- white sky.

## Prompt Status

`prompt-v2-style-packet-elements-first.md` has been rewritten for Berlin skyline
elements. The original scaffold-generated version used generic control-panel
language and must not be used for this task.

`prompt-pack.md` was rebuilt after the rewrite.

## Checkpoint Questions

1. Source packet:
   - `approve sources` - approved with `1A`
   - `wrong or missing source`
   - `show SVG preview first`

2. Landmark roster:
   - `approve roster` - approved with `2A`; optional green traffic-light/clock
     tower is excluded from the first candidate
   - `include green traffic tower`
   - `change roster`

3. Composition strategy:
   - `whole-set first` - approved with `3A`
   - `panel-by-panel first`
   - `show another plan`

4. Visual premise:
   - `approve run-through/arch/contour/white-sky plan` - approved with `4A`
   - `adjust run-through, arch, contour, or sky`
   - `show visual plan again`

## Next Step After Approval

Use the Berlin-specific style-packet prompt to produce style-matched skyline
elements or a whole-set draft, then review against the SVG template before
attempting final artwork.
