# Adversarial Naive-Vs-Corrected Comparison

Verdict: ACCEPT

Evidence inspected:
- `tasks/top-temp-workflow-test/source/template.svg`
- `tasks/top-temp-workflow-test/template-manifest.json`
- `tasks/top-temp-workflow-test/svg-geometry-report.md`
- `tasks/top-temp-workflow-test/agents/adversarial-comparison/naive-failure-overlay.png`
- `tasks/top-temp-workflow-test/agents/adversarial-comparison/corrected-artwork.png`
- `tasks/top-temp-workflow-test/agents/adversarial-comparison/corrected-overlay.png`
- `tasks/top-temp-workflow-test/agents/adversarial-comparison/corrected-mask-debug.png`
- `tasks/top-temp-workflow-test/agents/adversarial-comparison/comparison-metadata.json`

Passes:
- The naive failure is visible: `path[1]` and `path[2]` are tinted red because the naive method allowed painted background and focal controls inside the internal cutouts.
- The corrected proof uses the manifest roles: `path[0]` is the outer contour, while `path[1]` and `path[2]` are subtracted as keep-clear cutouts before motifs are placed.
- The corrected proof reports `0` nonwhite cutout pixels and `0` nonwhite outside pixels.

Failures or risks:
- The naive method made the exact workflow mistake this task is meant to expose: it treated SVG paths as paintable geometry, then clipped a rectangular control-panel composition to the outside shape. That makes the image look superficially fitted while the diagonal slot and round lower-right cutout are still filled with artwork.
- The corrected proof is intentionally rough. It demonstrates contour-first routing and cutout cleanliness, but it is not a finished production illustration.
- This test caught a parser risk while being built: the SVG uses smooth cubic `s/S` path commands. A role-aware workflow can still fail if its path parser silently mishandles valid SVG commands.

Next move:
- Add a repo-level manifest-aware mask/export helper that reads `template-manifest.json`, subtracts `internal_cutouts` whether they are paths or polygons, supports `C/S` curves, and includes this top-temp file as a regression case. The current diagnostic shows why path order alone is not enough.

## What The Naive Method Did Wrong

The naive method created a rectangular watercolor control-panel composition and used the SVG only as a late crop/outer mask. It never asked what each SVG path meant. Because `path[1]` and `path[2]` were not subtracted, the diagonal rounded slot and the lower-right round cutout retained painted pixels. Metadata measured `59618` nonwhite pixels in cutout zones for the naive output.

## How The Workflow Prevented It

The corrected method read `template-manifest.json` first, classified `path[0]` as material and `path[1]`/`path[2]` as internal cutouts, built `allowed = outer - cutouts`, and checked focal motif masks against an inflated forbidden mask before drawing. Final masking was still used as an export guardrail, but the visible controls were placed only in safe pockets.

## Remaining Workflow Weaknesses

- The repo needs one canonical parser/mask builder. Agents should not be reimplementing SVG path interpretation in every task folder.
- Export/scoring code should fail loudly when a manifest declares path cutouts but the exporter is only subtracting polygons.
- Review metadata should distinguish "all paths parsed" from "all paths semantically classified"; both are required.
