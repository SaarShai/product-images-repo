# Product Images Repo

Workspace for image-generation prompt packs, reference assets, template checks,
and result reviews.

## Setup

Create one local environment and use it consistently; do not rely on whichever
`python3` is first on `PATH`.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/verify_setup.py
python scripts/validate_svg_template_workflow.py
```

The default gate uses clone-visible two-panel assets. Use `--legacy-skyline`
only when the optional historical fixtures are supplied.

## Current Work

- **CLOSED NEGATIVE:** `tasks/geometry-evidentiary-princess-n02/VERDICT.md` rejects the July prompt-plus-outset route on geometry.
- **Experiment scope:** `tasks/geometry-adherence-solutions/experiment-1/CONCLUSIONS.md` validates the hard-mask/composite-back architecture on one held-out panel only.

`tasks/baci-door` and `tasks/castle-panels` are historical June examples. New SVG-template work starts with `docs/svg-template-illustration-workflow.md` and `docs/review-judge-checklist.md`.

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
python scripts/scaffold_template_task.py demo-task \
  --svg assets/templates/two-panel-template.svg \
  --refs assets/templates/two-panel-template-raster.png --dry-run
```

## Brainer Skills

Run `./install.sh`, then `python scripts/check_carrier_sync.py`; see `docs/brainer-skills.md`.

## SVG Status

The authoritative template SVG is now stored at:

```text
assets/templates/two-panel-template.svg
```

Run:

```bash
python scripts/asset_report.py
python scripts/svg_geometry_report.py
```
