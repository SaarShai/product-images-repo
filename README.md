# Product Images Repo

Workspace for image-generation prompt packs, reference assets, template checks,
and result reviews.

## Current Task

The active task is `tasks/castle-panels`: refining a two-panel children's
watercolor castle illustration constrained by a die-line template.

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
python3 scripts/asset_report.py
python3 scripts/build_prompt_pack.py tasks/castle-panels
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
