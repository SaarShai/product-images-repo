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

## Step 4: Prompt From Geometry Plus References

A useful prompt has both halves:

- geometry constraints from the SVG;
- visual vocabulary from the references.

Do not rely on palette words alone. Include object vocabulary, edge treatment,
line weight, density, shape simplicity, material language, and lighting from the
references.

Generate one or a small batch of variants. Save every candidate under
`outputs/generated/` with enough timestamp or variant information to trace it.

## Step 5: Export, Score, And Make Review Artifacts

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

## Step 6: Judge By Looking

A mechanical pass is a rejection gate, not final approval. Use a judge pass that
actually opens the images.

The judge must answer:

- Does the artwork fit the contour without visible rescue cropping?
- Are cutouts and keep-clear zones clean?
- Does the style match the references beyond color?
- Are important motifs safely away from seams and production cuts?
- Is the right next move accept, local patch, prompt restart, or blocked?

## Step 7: Reset Or Patch Deliberately

Restart from the prompt/source when:

- the result is a clipped rectangle;
- the style misses the reference vocabulary;
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

## Step 8: Record The Decision

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
- I ran available geometry/export/scoring commands.
- I inspected actual images or had a judge inspect them.
- I chose accept, local patch, or prompt restart from evidence.
