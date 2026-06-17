# Skyline Template Illustration Workflow

This document is the human-readable source of truth for default skyline and
city-scape Screenery image-generation rules in this repo. User instructions for
a specific task can override these defaults, but the override must be recorded
in that task's brief or review note.

The shared SVG-template rules still apply:

- Use the SVG as coordinate authority.
- Compose inside the template, rather than drawing a rectangle and cropping it.
- Separate geometry success from style success.
- Treat mechanical passes as rejection gates, not production approval.
- Use visual judges for actual artwork and overlay review.

## Default Evidence

- Default skyline SVG: `assets/skyline/city-skyline template.svg`
- Example and counterexample images: `assets/skyline/*.png`
- Asset map: `assets/skyline/README.md`
- Shared workflow: `docs/svg-template-illustration-workflow.md`
- Shared judge checklist: `docs/review-judge-checklist.md`
- Skyline skill: `.codex/skills/skyline-template-illustration/SKILL.md`

Use a user-uploaded SVG instead of the default only when the user supplies one.

## Default Template Roles

In `assets/skyline/city-skyline template.svg`:

- Black strokes (`#231f20`) are production panel borders, outer contours, door
  flaps, and cut/hinge references.
- Yellow dashed strokes (`#ffdb55`) are margin and safe-area guides.
- Red dashed strokes (`#ed1c24`) are no-crop and no-focal-feature zones, unless
  explicitly repurposed by the user.
- Green dashed strokes (`#39b54a`) are temporary top-contour guides that should
  be adapted to the actual tops of buildings and landmarks.
- Orange dashed strokes (`#f7941d`) mark the central saloon-door arch guide.

The default physical structure is:

- one large central door panel;
- two narrow side panels;
- central door panel: one top sub-panel plus two bottom saloon-style door flap
  sub-panels;
- each narrow panel: one top sub-panel plus one bottom sub-panel.

## Composition Rules

Create a single city-scape family across all three panels. It may feel like one
continuous skyline, but landmark identity is assigned by physical panel.

Each physical panel should contain:

- one iconic building or landmark; or
- a composite of up to three buildings/landmarks.

Do not split buildings, landmarks, or specific recognizable features between
panels. Specific features include characters, faces, birds, vehicles, signs,
text, statues, unique roof tips, named facades, distinctive doors, windows that
read as part of an iconic feature, and any user-named subject.

Quiet, repeating, or infrastructural elements may run through panels when they
are intentionally continuous. Examples:

- bridges;
- trains or rail lines;
- roads;
- rivers;
- cables;
- skyline horizon bands;
- repeated generic facade or wall texture.

Run-through elements must be planned as continuous infrastructure. Do not use
this exception to excuse cropped focal landmarks or chopped characters.

## Flexibility Rule

Use exact rule-following where it protects production geometry or recognizable
features. When strict interpretation is impossible, too slow, or visually worse,
follow the general intent, record the deviation, and ask the user when the
choice changes the visual premise.

## Red Zone Rules

Red dashed separators and rectangles are safety zones. Avoid putting specific
recognizable features there. They can contain white sky, simple wall/facade
texture, generic cloudless background, or other non-specific filler when needed.

The good fairy/castle example shows the desired behavior: characters and birds
are moved away from cut lines, while a plain wall lane can occupy the middle.

The bad fairy/castle example shows the failure: fairies and birds are cropped by
horizontal cuts and red rectangles.

Red-center lanes may contain quiet, non-iconic filler such as plain facade,
wall, rail, water, or train body. They should not contain recognizable features
such as statues, signs, faces, text, distinctive roof tips, or named landmark
details. If a feature only slightly overlaps a red center, prefer a small
realignment over a broad redraw.

## Saloon-Door Arch Rule

The orange dashed arch in the central door panel is a compositional opportunity,
not a pixel-perfect requirement.

Prefer a feature that fits inside or stylistically echoes the arch:

- bridge span;
- doorway or entrance;
- palace gate;
- statue or column;
- archway;
- window bay;
- enlarged building entrance;
- landmark feature whose proportions can be exaggerated.

It is acceptable to modify proportions to make the feature work. The bridge and
exaggerated-door examples are valid precedents: they fit the arch generally,
not mathematically.

When the arch feature is a bridge or similar span, check whether aligning it to
the middle of the saloon door flaps improves symmetry without making the scene
feel forced.

If no natural feature exists, record that decision and keep the arch area quiet
instead of forcing an awkward motif.

## Top-Contour Rule

The green dashed contour is a placeholder. The final top contour should trace
the chosen skyline: rooflines, spires, domes, bridge towers, antennas, or other
major silhouette features.

Do not leave the top as a generic arch when the chosen buildings give a better
production silhouette. Do not add tiny fragile details above the contour unless
they are essential and production-safe.

A landmark may rise above the adapted contour only in a controlled amount.
Door-panel domes and spires are a valid precedent for modest height additions.
If a feature towers far above the contour, reduce it or reposition it so the
silhouette still reads as intentional production geometry.

## Landmark Integrity Rule

Buildings and landmarks must read whole within their physical panels. Do not
crop or hide a landmark base, entrance, lower section, or other identity-bearing
part at a panel edge. Fix a cropped building base before polishing style.

## Sky Rule

Keep sky and removable background areas white by default. The sky can be added
later. If style references include blue sky or clouds, treat them as style
context, not as permission to paint the final sky, unless the user explicitly
asks for a sky background.

## Template-Lock Rule

The SVG is the coordinate authority. A generated skyline may be beautiful, but
it does not own the physical template. Do not accept model-drawn guide lines,
panel widths, separator heights, red-zone positions, saloon-arch size, or top
contour as production geometry.

When using image generation for whole-scene cohesion, prefer artwork-only output
on a white/paper-white background:

- no black panel borders;
- no yellow dashed margins;
- no red dashed rectangles or separators;
- no green top-contour guide line;
- no orange arch guide;
- no door split, knobs, or production strokes.

Hard boundary: never ask the image model to think about, preserve, adapt, trace,
honor, fix, or improve the SVG contour, panel proportions, guide positions, red
zones, top-contour line, saloon arch, or production geometry during an artwork
patch. Those constraints belong to deterministic overlay/export and review
notes, not the creative prompt. The prompt may say `artwork-only on white
background` and may name the local visual defects to change, but it must not
include contour/panel/guide instructions that invite the model to redraw or
reinterpret the template. If exact geometry context is needed, provide it as a
mask, crop, or external overlay artifact and verify the result afterward.

Prompt boundary preflight: before sending any skyline prompt to image
generation, read the exact prompt text and remove template-geometry language.
Forbidden prompt concepts include `SVG`, `contour`, `panel proportions`,
`red zone`, `green line`, `orange arch`, `saloon-door guide`, `template guide`,
`safe margin`, and `production stroke`, unless the prompt is explicitly for a
non-production diagnostic guide image. Put those requirements in the task brief
or verifier checklist instead, then overlay the real SVG after generation.

Overlay the real SVG after generation and measure against it. If a generated
candidate includes a good adapted top contour but changes the template
dimensions, keep the candidate as visual evidence only. Use deterministic
registration or panel remap only as a diagnostic/composition map, not as final
production art when it visibly warps buildings.

For overlay review, calculate guide dimensions from the source SVG coordinate
system, not from a raster preview crop. A square PNG preview may be used as a
visible stroke layer, but exact overlay aspect, panel widths, separator height,
red-zone positions, and saloon-arch placement must come from the SVG viewBox,
visible coordinate bounds, or a recorded geometry report. If an overlay looks
lower, squished, or close-but-wrong, rebuild the overlay from SVG coordinates
before judging the artwork.

## Setup Checklist

Before generation:

1. Run `git status --short`.
2. Create or recover `tasks/<task>/`.
3. Scaffold with the default skyline SVG unless a user SVG is provided:

   ```bash
   python3 scripts/scaffold_template_task.py <task> \
     --svg "assets/skyline/city-skyline template.svg" \
     --refs <reference-images>
   ```

4. Fill `template-manifest.json` with skyline guide roles.
5. Attempt `python3 scripts/svg_geometry_report.py ...` if useful, but do not
   rely on it blindly. If it stalls or misses the skyline roles, inspect the SVG
   directly and record the limitation.
6. Build and inspect the reference style packet:

   ```bash
   python3 scripts/build_reference_style_packet.py tasks/<task>
   ```

7. Write a skyline composition plan in `session-brief.md` or
   `tasks/<task>/skyline-plan.md`. The task scaffold writes
   `skyline-example-feedback.md` for skyline tasks; use it to capture the live
   example feedback loop.

## Skyline Composition Plan

The plan must answer:

- Which city, cities, or landmark family is being used?
- Which landmark or composite goes in each of the three physical panels?
- Which elements, if any, run through between panels?
- Which feature fits or echoes the central saloon-door arch?
- How should the green top contour adapt to the skyline?
- Which specific features must avoid red zones and seams?
- Is the sky/removable background pure white?
- Which reference images control style, palette, landmarks, and prior rendered
  panels?

Ask the user for approval when any of these choices are ambiguous or when the
choice changes the visual premise.

For live examples, make the approval easy to answer. If native UI buttons are
not available, use compact button-style choices and record the selected codes in
`skyline-example-feedback.md`. Checkpoint 1 should explicitly separate:

- source packet approval;
- landmark roster approval;
- composition strategy approval;
- visual-premise approval: run-through element, saloon-door arch feature,
  top-contour adaptation, and white/removable sky.

## Generation Pattern

When references define style, generate style-matched elements first and place
them later. This is especially important when the user provides art-style or
prior-render references.

Recommended split:

- Style agent: uses `style-packet/` crops to create skyline/landmark element
  candidates or an element sheet.
- Geometry agent: uses the SVG and skyline plan to place only accepted elements
  into safe pockets.
- Judge agent: reviews actual candidates and overlays using vision.

Keep the prompt narrow. Attach 6 to 10 high-signal style-packet crops where the
tool supports it. Do not ask a style agent to infer the look from prose alone.

## Proof-Before-Spend Scout Gate

Before spending on a polished full illustration, prove that the composition
route is likely to work. This gate is required when the skyline has run-through
elements, saloon-door arch decisions, dense red safety zones, multiple landmark
composites, or when user feedback questions whether the wireframe is useful.

Faint lookalike placement boards do not pass this gate. They may document
inventory, but they are weak generation inputs unless the hierarchy and route
differences are visible within a few seconds.

Use two or three low-cost scout tests with distinct prompt strategies:

- direct whole-scene control from template, roster, and references;
- rough composition map used only as a whole-redraw guide, not as pixels to
  collage;
- strict red-zone and seam-safety scout that stresses no-crop behavior.

Proceed only when a scout shows:

- visibly distinct hierarchy, not just different labels;
- landmarks whole within their physical panels;
- red zones containing only blank sky, quiet texture, water, rail, or solid
  train body;
- run-through elements reading as infrastructure rather than cropped focal
  subjects;
- saloon-door arch either clearly useful or intentionally quiet;
- top contour plausibly tracing the selected skyline;
- white/removable sky preserved.

If all scouts fail in the same way, restart the method instead of polishing the
wireframe. Common outcomes:

- Direct whole-scene scouts look cohesive but violate red zones: use whole-scene
  redraw for style/cohesion, then enforce SVG and red-zone safety downstream.
- Composition-map scouts still look like pasted elements: restart with a more
  abstract composition map or direct whole-scene route.
- Red-zone scouts cannot keep details clear: reduce detail, move/simplify the
  affected landmarks, or plan a bounded cleanup/mask after redraw.
- A scout has the best composition/top contour but wrong dimensions: keep the
  visual direction, reject the geometry, and rebuild a locked-SVG composition
  map before redraw.

Record the scout prompts, artifacts, reviewer verdicts, and decision unlocked in
`skyline-example-feedback.md` before moving to a polished candidate.

## Dimension Repair Gate

Before a generated skyline option can drive final production, compare it to the
real SVG:

- active content aspect;
- panel-edge x positions;
- top/bottom separator y position;
- red vertical keep-clear rectangles;
- saloon arch width and split;
- bottom-subpanel start and available height;
- adapted top contour relative to the locked panel widths.

If the best visual option is too wide, too short, has bottom sub-panels too low,
or widens the central door/saloon arch, do not reuse the generation method that
created the drift. Test these repair routes in order:

- global SVG-aspect registration as a cheap diagnostic;
- panel-by-panel remap as a seam-risk diagnostic;
- SVG-locked composition map followed by artwork-only whole-scene redraw.

Prefer the SVG-locked map route when registration visibly distorts buildings or
breaks continuous elements.

## Checkpoints

Checkpoint 1: Source and plan

- Template SVG and references are recorded.
- Skyline guide roles are understood.
- Three-panel landmark allocation is written.
- User has approved load-bearing ambiguous choices, including the visual
  premise: run-through element, saloon-door arch feature, top-contour
  adaptation, and white/removable sky.

Checkpoint 2: Proof-before-spend scouts

- Multiple visual scout routes were created when composition was uncertain.
- Options are visually distinct enough to judge within a few seconds.
- A visual/style reviewer and geometry/risk reviewer inspected actual scout
  images.
- The task records whether to proceed, restart the method, or ask the user for
  a direction.

Checkpoint 3: First candidate

- Candidate is composed for the template, not cropped from a rectangle.
- Candidate does not use model-drawn template guides as production geometry.
- Active frame, panel widths, separator height, red zones, and saloon arch were
  checked against the SVG when the candidate contains any visible guide
  structure.
- Landmarks are whole within panels.
- Red/yellow/orange/green guide intent is respected.
- Sky is white unless overridden.
- Vision judge inspects the candidate and overlay.

Checkpoint 4: Repair or restart decision

- If style vocabulary is wrong, restart from the prompt/source references.
- If geometry is wrong because the composition ignored the template, restart.
- If only a bounded local defect exists, patch locally and verify with overlay
  and visual crop/full-frame review.

Checkpoint 5: Final handoff

- Record final candidate, overlay/debug artifacts, commands run, judge verdict,
  accepted risks, and any user feedback promoted into future rules.
- Check `skyline-example-feedback.md` for durable lessons before changing the
  skill or this workflow.

## Review Gate

Use this verdict form:

```text
Verdict: ACCEPT | LOCAL PATCH | PROMPT RESTART | BLOCKED

Evidence inspected:
- <source SVG>
- <candidate artwork>
- <overlay/debug image>
- <style references or packet sheets>

Passes:
- <specific pass>

Failures or risks:
- <specific failure or risk>

Next move:
- <one concrete action>
```

Reviewers must inspect actual images. Prompt text, metadata, or a mechanical
`PASS` cannot approve production readiness by itself.

## Learning Loop

After a meaningful skyline session, harvest only durable project-specific
lessons:

- a user correction that changes a production rule;
- a placement rule that clearly prevents future failures;
- a failed assumption and its prevention rule;
- an accepted method that should guide the next skyline task.

Record session-specific feedback in the task packet first. Update this workflow
or the skyline skill only when the lesson is stable enough to help future
skyline/city-scape tasks.
