# Product Images Repo

Workspace for image-generation prompt packs, reference assets, template checks,
and result reviews.

## Current Tasks

The active/recent tasks are:

- `tasks/baci-door`: repairing a Baci door template-fit image where the full
  panel is close but the two SVG hex cutout areas need exact, clean handling.
- `tasks/castle-panels`: refining a two-panel children's watercolor castle
  illustration constrained by a die-line template.

For Baci-door repair learning, start with:

```text
docs/baci-door-template-fit.md
.codex/skills/baci-template-fit-repair/SKILL.md
```

For a new SVG-template illustration task, start with:

```text
docs/svg-template-illustration-workflow.md
docs/review-judge-checklist.md
.codex/skills/svg-template-illustration/SKILL.md
.codex/skills/svg-template-review-judge/SKILL.md
```

The latest accepted Baci checkpoint is:

```text
tasks/baci-door/outputs/final/20260616T071500Z-baci-door-hole-sections-bounded-exact-hex-v1-svg-fit-artwork-only.png
tasks/baci-door/outputs/final/20260616T071500Z-baci-door-hole-sections-bounded-exact-hex-v1-svg-fit-clean-black-lines.png
```

Canonical task status lives at:

```text
tasks/castle-panels/CURRENT.md
```

The current best scored wall-center export is
`20260615T-system-v9b-wall-sx070-sy104-y0`, produced from the revised V9B
template-first artwork with `scale_x=0.70`, `scale_y=1.04`, and `offset_y=0`.
It passes the mechanical template-fit scorer, but still requires semantic visual
review before production handoff.

## Layout

- `assets/reference-images/` - style references and contour examples.
- `assets/templates/` - raster and SVG geometry templates.
- `tasks/<task>/prompts/` - copy-pasteable prompt variants.
- `tasks/<task>/outputs/generated/` - generated images saved from tools.
- `tasks/<task>/outputs/reviews/` - review notes comparing outputs.
- `tasks/<task>/outputs/final/` - curated final/export candidates.
- `scripts/` - local helpers for asset inventory and prompt packaging.
- `wiki/` - repo-local Brainer wiki memory, if initialized.

## Useful Commands

```bash
python3 scripts/verify_setup.py
python3 scripts/validate_svg_template_workflow.py
python3 scripts/scaffold_template_task.py demo-task --svg assets/templates/two-panel-template.svg --refs assets/reference-images/castle-style-reference.png --dry-run
python3 scripts/asset_report.py
python3 scripts/build_prompt_pack.py tasks/castle-panels
python3 scripts/svg_geometry_report.py tasks/baci-door/source/baci-door-updated-20260616.svg --out tasks/baci-door/svg-geometry-report-updated-20260616.md
python3 scripts/export_svg_template_fit.py tasks/baci-door/outputs/generated/20260616T071500Z-baci-door-hole-sections-bounded-exact-hex-v1.png --template-svg tasks/baci-door/source/baci-door-updated-20260616.svg --out-dir tasks/baci-door/outputs/final --prefix 20260616T071500Z-baci-door-hole-sections-bounded-exact-hex-v1-svg-fit --require-pass
python3 scripts/score_template_fit.py --batch-generated --sweep --mode wall --md-out tasks/castle-panels/outputs/reviews/20260615T-system-wall-score-sweep.md --json-out tasks/castle-panels/outputs/reviews/20260615T-system-wall-score-sweep.json
python3 scripts/export_composite.py tasks/castle-panels/outputs/generated/20260615T132212Z-prompt-v6-narrow-center-safe-gutters.png --prefix 20260615T132212Z-v6-scale090-y50 --art-scale 0.90 --art-offset-y 50
```

Current review packet:

```text
tasks/castle-panels/CURRENT.md
tasks/castle-panels/outputs/reviews/20260615T-system-wall-score-sweep.md
tasks/castle-panels/outputs/reviews/20260615T-system-wall-v9b-targeted-sweep.md
tasks/castle-panels/outputs/reviews/2026-06-15-v6-v7-decision-packet.md
tasks/castle-panels/prompts/prompt-v9a-empty-center-split-safe.md
tasks/castle-panels/prompts/prompt-v9b-wall-background-split-safe.md
```

## Brainer Skills

Selected skills from `/Users/za/Documents/Brainer` are linked for both Codex and
Gemini/Antigravity workspace use. See `docs/brainer-skills.md`.

## SVG Status

The authoritative template SVG is now stored at:

```text
assets/templates/two-panel-template.svg
```

Run:

```bash
python3 scripts/asset_report.py
python3 scripts/svg_geometry_report.py
```
