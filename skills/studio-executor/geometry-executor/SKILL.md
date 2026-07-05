---
name: studio-geometry-executor
description: "Produce geometry artifacts (spec, guide, mask, control map) for a die-cut panel and gate candidates deterministically — panel-scoped silhouette-IoU + geom_gate mask mode. Geometry is measured, never eyeballed (LAW 1)."
effort: medium
---

# geometry-executor — spec → control map → deterministic gates

Promoted 2026-07-05 after gpt-5.5 read-critique + execution sim. History: `../DRAFT-geometry-executor.md`.

## Commands (verified — these exact flags)

| step | command |
|---|---|
| spec (single source of geometry truth) | `python3 scripts/skyline_panel.py --svg <svg> --panel <p> --mode spec` |
| guide | `... --mode guide` (bold OUTER contour + faint hints only; NEVER draw saloon-flap/cut-split lines; element openings = WHITE openings) |
| preflight | `... --mode check` (guide aspect MUST equal spec aspect) |
| mask + control map | `python3 -m studio.controlmap --spec <spec.json> [--guide <guide.png>] [--content <edges.json>] --outdir <dir>` |
| shape gate | `python3 -m studio.controlmap --score <cand.png> --mask <panel>-mask.png` |
| full geometry gate | `python3 scripts/geom_gate.py --cand <cand.png> --mask <panel>-mask.png` (no `--svg` = mask-authoritative) |

Notes:
- `--guide` mode is REQUIRED when the SVG has no drawn contour for the panel (city-skyline narrows).
- Content that MUST appear (arch, window) goes in `--content` as edges json (`[{"type":"arch|archwin|rect|line","frac":[x0,y0,x1,y1]}]`) — LAW 0 for the control channel; never place fixed structure by prompt.
- `scripts/svg_geometry.py` is a module, NOT a CLI. `measure_sdxl_cn.py` takes a POSITIONAL candidate (`<cand> --svg <svg>`).
- Single panel of a multi-panel template: use the two panel-scoped gates above. `objective_gate_report.py --cand <png> --svg <full-template.svg>` false-FAILs by construction (aspect mismatch) — reserve it for single-panel-SVG tasks.

## Gates — what each proves

- `--score` silhouette-IoU ≥ `packet.gates.geom_iou_min` (default 0.85): SHAPE only. Resize-normalized (fal snaps sizes to buckets, e.g. 820x2105→576x1536 — expected, not an error).
- `geom_gate --mask`: fill_inside_contour (catches NEAR-EMPTY panels deterministically — proven: a 0.976-IoU empty panel fails here at fill 0.018), cutout voids, keep-clear (advisory unless `--keepclear-fail`).
- Hole-bearing panels additionally: `python3 scripts/punch_holes.py --gen <png> --svg <svg> --out <png> --halo` + hi-DPI hole-crop VLM check. Hole clarity is judged, not IoU'd.
- A number is not a verdict: scrutinize the per-opening overlay before claiming fit ([[region-iou-not-fit-calibration]]).

## Both gates + a VLM content/style check are required before accepting any candidate. IoU alone has passed empty panels; vision alone has ranked wrong geometry #1 ([[geometry-must-be-measured-gate]]).

## Done means

- spec/guide/mask/control files exist at the reported paths (`ls` proof).
- Preflight aspect check passed.
- Every candidate has BOTH gate JSONs; verdicts quoted, not paraphrased.
