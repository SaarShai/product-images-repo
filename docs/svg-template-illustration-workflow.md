# SVG Template Illustration Workflow

This repo is for generating product illustrations that are designed for an SVG
template from the start. The goal is not "make a nice picture and clip it." The
goal is "compose the picture inside the product geometry, then use masks only to
verify and export exact edges."

## Source Contract

Each reusable task should have this structure:

```text
tasks/<task>/
  source/                 authoritative SVG template(s)
  refs/                   style and color references
  style-packet/           visual reference crops/sheets for style agents
  prompts/                prompt variants
  outputs/generated/      raw generated or procedural artwork
  outputs/reviews/        overlays, crops, score reports, judge notes
  outputs/final/          curated export candidates
  session-brief.md        source paths, goal, geometry rules, decisions
  template-manifest.json  explicit SVG role map, filled before generation
  svg-geometry-report.md  parser/report output when applicable
```

Use `scripts/scaffold_template_task.py` to create this structure:

```bash
python3 scripts/scaffold_template_task.py my-task \
  --svg /path/to/template.svg \
  --refs /path/to/style-a.png /path/to/palette-b.png
```

The scaffold copies source evidence into the task by default. Use `--no-copy`
only when the files are too large or must remain outside the repo; if you do,
record the original absolute paths in the manifest.

## Step 1: Recover And Pin The Inputs

Start every run by checking the real state:

```bash
git status --short
python3 scripts/asset_report.py
```

Then read the task brief and newest review artifacts. Do not assume a previous
turn did no work just because the UI was interrupted.

Pin the source evidence:

- SVG template path and checksum or repo copy.
- Style/color reference paths.
- Good and bad example paths.
- Any user feedback that changed the production rule.

## Step 2: Parse The SVG Before Prompting

Run the geometry report:

```bash
python3 scripts/svg_geometry_report.py tasks/<task>/source/template.svg \
  --out tasks/<task>/svg-geometry-report.md
```

Identify:

- outer contour or product body;
- internal cutouts, holes, slots, notches, center gaps, and shared seams;
- dashed yellow safe-area contours;
- red/yellow keep-clear rectangles;
- areas where quiet background may cross a cut;
- areas where recognizable motifs must never cross.

If the report misses polygons or relevant SVG elements, inspect the SVG directly
or improve the task-specific parser before generating.

Screenery export caution: some contours are not one closed `<path>`. A panel
edge may be split into an open path plus a sibling `<polyline>` or similar
segment. Do not let geometry tooling close such paths diagonally until you have
checked whether a nearby line/polyline supplies the real bottom or side edge.
The `np01-back-bottom.svg` lesson is the concrete failure mode: ignoring the
bottom/right polyline removed the legitimate lower-right panel area.

Socket/notch caution: edge sockets, bite notches, tabs, and interlocking shapes
are carved-out negative space in the contour. Their SVG paths may extend outside
the larger paintable body bounds, but the production meaning is cutout, not
protrusion. Do not rely only on representative-point containment. Check overlap
with the larger paintable contour, raw SVG order, and the visual debug mask
before classifying these shapes as paintable.

Fill `template-manifest.json` before prompting. The manifest should name outer
contours, paintable regions, internal cutouts, keep-clear zones, visual guides,
safe pockets, quiet background zones, and no-focal-motif zones. If you cannot
classify the geometry, stop and say what evidence is missing.

## Step 3: Plan Safe Pockets

Write the composition plan before generating. A good plan says:

- which pockets contain focal motifs or modules;
- which pockets contain secondary detail;
- which zones must stay white or quiet background;
- how large objects route around cutouts before final masking;
- which style-reference objects are allowed in each pocket.

For example, a control-panel task should place dials, sliders, bolts, pipes,
and highlights in named safe pockets. It should not draw a full rectangular
control panel and erase a diagonal slot later.

## Step 4: Build The Reference Style Packet

When style matters, build a visual packet from the actual reference images
before asking any agent to generate artwork:

```bash
python3 scripts/build_reference_style_packet.py tasks/<task>
```

Inspect:

- `tasks/<task>/style-packet/reference-contact-sheet.png`
- `tasks/<task>/style-packet/style-exemplar-sheet.png`
- `tasks/<task>/style-packet/style-packet.json`

The style packet is the source of style truth. It should contain full-reference
crops, region crops, texture and edge-treatment crops, accent/component crops,
palette swatches, and a style-agent prompt that lists the images to attach.

## Step 5: Split Style Agents From Geometry Agents

For difficult template work, do not ask one agent to solve style and geometry in
one pass.

- Style/image-gen agents use `.codex/skills/svg-template-style-agent/SKILL.md`
  and `prompts/prompt-v2-style-packet-elements-first.md`. They generate
  style-matched element sheets from the packet images.
- Geometry agents use `.codex/skills/svg-template-illustration/SKILL.md`. They
  place accepted elements into safe pockets and verify outer/cutout masks.

This separation makes failures easier to diagnose: a style miss is not hidden
behind a geometry pass, and a geometry miss is not excused by a beautiful style.

## Step 6: Choose Element Placement Or Whole Redraw

Choose the smallest route that attacks the current bottleneck:

- Use element-sheet generation plus geometry placement when the missing piece is
  individual reference-style controls or material fragments.
- Use whole-panel redraw/restyle when the best candidates already prove the
  rough layout/geometry but look procedural, collaged, or sprite-assembled.
  Attach the rough candidates as composition maps, attach the style references
  and style packet, and ask the image model to repaint one coherent watercolor
  object. Then run the SVG exporter/checker only after the redraw is visually
  promising.

The 2026-06-16 top-temp lesson is the model: B/C roughs were poor final art but
excellent image-generation inputs. Three redraw prompts produced much better
watercolor panels because the model solved cohesive style synthesis directly.

Hard routing rule for geometry-approved style fixes: if the user says the
dimensions/location/geometry are good and only the style needs adaptation, do
not style the approved raster by local filters, crop compositing, or
`locked-geometry` scripts. Use the approved raster only as a composition map,
attach the real style references/style packet, produce a raw whole-panel redraw,
and only then run SVG export/checks as the downstream geometry gate. If the image
tool cannot attach those images, prepare the attachment-aware prompt package
instead of doing a prompt-only substitute.

## Step 7: Prompt From Geometry Plus References

A useful prompt has both halves:

- geometry constraints from the SVG;
- visual vocabulary from the packet images made from the references.

Do not rely on palette words alone. Attach style-packet images. Include object
vocabulary, edge treatment, line weight, density, shape simplicity, material
language, and lighting from the packet crops.

For Screenery watercolor control panels, include edge treatment explicitly:
dark blue rim lines, slight raised bevel, soft inner shadow, pale highlights,
and optional subtle rim/lip around the contour and cutout rims. Keep rims
watercolor-native so they do not read as extra cutouts.

Generate one or a small batch of variants. Save every candidate under
`outputs/generated/` with enough timestamp or variant information to trace it.

## Step 8: Export, Score, And Make Review Artifacts

Use task-specific exporters and scorers when available:

```bash
python3 scripts/export_svg_template_fit.py <generated.png> \
  --template-svg tasks/<task>/source/template.svg \
  --out-dir tasks/<task>/outputs/final \
  --prefix <candidate-prefix> \
  --require-pass
```

For castle-panel placement work, use `scripts/score_template_fit.py` and
`scripts/export_composite.py` as recorded in `tasks/castle-panels/CURRENT.md`.

Minimum review artifacts:

- artwork-only export;
- clean-line or template-overlay export;
- debug mask or score JSON;
- cutout crop/contact sheet for small holes or scar-prone areas;
- judge note using `docs/review-judge-checklist.md`.

Package review artifacts so each image tests one candidate against one SVG
geometry. Do not group two versions of the same panel in a single review image
or overlay. Side-by-side sheets are useful for summaries after individual
checks exist, but acceptance review needs one geometry, one overlay, and one
verdict per artifact.

## Step 9: Judge By Looking

A mechanical pass is a rejection gate, not final approval. Use a judge pass that
actually opens the images.

The judge must answer:

- Does the artwork fit the contour without visible rescue cropping?
- Are cutouts and keep-clear zones clean?
- Are side sockets/notches blank where the SVG intends carved-out cutout space,
  including paths whose coordinates extend past the paintable body edge?
- Are bottom/right panel areas complete, or did an open path get closed with a
  diagonal because a sibling polyline was ignored?
- Does the style match the references beyond color?
- Does the contour/cutout edge treatment have the reference bevel/rim quality,
  without looking like a hard crop mask?
- Are important motifs safely away from seams and production cuts?
- Is the right next move accept, local patch, prompt restart, or blocked?

## Step 10: Reset Or Patch Deliberately

Restart from the prompt/source when:

- the result is a clipped rectangle;
- the style misses the reference vocabulary;
- style agents described the references from memory instead of using a visual
  style packet;
- geometry-safe candidates still look like procedural placement or crop
  collage; use whole-redraw from roughs instead of more placement polishing;
- several repairs have accumulated artifacts;
- feedback changes the task rule;
- a patch would require broad inpaint over core composition.

Patch locally when:

- the full artwork is good;
- the defect is bounded;
- donor pixels can be constrained to that bounded region;
- exact SVG cleanup and crop/full-frame review can prove the repair.

The Baci-door accepted repair is the model for bounded local repair:
`docs/baci-door-template-fit.md`.

The space narrow 1+2 reference-first restart is the model for abandoning a
geometry-valid but style-wrong procedural sketch:
`tasks/space-narrow-1-2/session-brief.md`.

## Step 11: Record The Decision

Every handoff or review note should include:

- source SVG and references;
- generated candidate;
- commands run;
- metadata/score paths;
- image artifacts inspected;
- verdict and next move;
- any user feedback promoted into a durable rule.

## Agent Checklist

- I read `AGENTS.md` and this workflow.
- I used the SVG as the geometry source of truth.
- I identified outer contours and every cutout/keep-clear zone.
- I filled `template-manifest.json` or explicitly blocked on ambiguous roles.
- I planned safe pockets before generating.
- I used references for visual vocabulary, not only palette.
- I saved raw candidates and review artifacts in the task folder.
- I packaged each acceptance overlay/review image as one candidate against one
  SVG geometry, not multiple same-panel versions in one image.
- I ran available geometry/export/scoring commands.
- I inspected actual images or had a judge inspect them.
- I chose accept, local patch, or prompt restart from evidence.
