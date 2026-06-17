# Agent Simulation Report

Date: 2026-06-16

Four parallel read-only agents stress-tested this repo setup from different
angles: prior-session learning, tooling audit, visual judge evidence, and future
agent usability. Their findings were folded into the workflow, skills, task
templates, and validation script.

## Findings Incorporated

- Cross-task rules now live in `docs/svg-template-illustration-workflow.md`
  instead of being scattered across castle, Baci, and space task notes.
- Future agents now have end-to-end and specialist skill entrypoints:
  `.codex/skills/svg-geometry-style-illustration/SKILL.md`,
  `.codex/skills/svg-template-illustration/SKILL.md`, and
  `.codex/skills/svg-template-review-judge/SKILL.md`.
- New task scaffolds include a `template-manifest.json` so agents must name
  outer contours, cutouts, keep-clear zones, visual guides, safe pockets, and
  no-focal-motif zones before generating.
- The judge checklist now requires actual image inspection and a concrete
  `ACCEPT`, `LOCAL PATCH`, `PROMPT RESTART`, or `BLOCKED` verdict.
- Baci-door docs now name positive and negative visual fixtures so judges learn
  why a metric `PASS` can still fail.
- `scripts/export_svg_template_fit.py` now warns that `PASS` is mechanical only
  and points to the visual artifacts that still need review.
- `scripts/validate_svg_template_workflow.py` acts as a lightweight simulation
  gate for the docs, skills, and scaffold.

## Simulated Agent Failure Modes

- Guessing SVG roles from element order instead of writing a manifest.
- Treating `outputs/final/*metadata.json` as approval without opening images.
- Cropping a rectangular illustration into the contour and calling it done.
- Palette-shifting a style-wrong result instead of restarting reference-first.
- Treating an approved geometry rough as a pixel source instead of a
  composition map for attachment-aware whole-panel redraw.
- Broadly inpainting scarred holes when a bounded local donor repair is safer.
- Rerunning writer scripts in a dirty repo without checking state first.

## Regression Prompts

Use these prompts to test future agents:

- "Classify this arbitrary SVG into outer contour, cutouts, keep-clear zones,
  and visual guides. Do not generate until the manifest is filled."
- "This candidate passes metrics but the cutout crop has scars. Decide local
  patch vs prompt restart and justify with image evidence."
- "Geometry passes but style vocabulary misses the references. Produce a
  reference-first restart plan."
- "Recover from a dirty worktree with generated outputs. Summarize state without
  cleaning or rerunning writer commands."
- "Two valid modes exist: empty center and quiet background center. Choose the
  mode before scoring."

## Remaining Improvements

- Generalize SVG scoring beyond the castle-specific raster-guide scorer.
- Add shared safe-pocket geometry helpers so task-local scripts do not rely on
  fragile path indices.
- Split `scripts/verify_setup.py` into a pure read-only smoke check and an
  artifact-refresh command.
