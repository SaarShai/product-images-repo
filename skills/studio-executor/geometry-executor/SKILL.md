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

## Control maps: SOLID strokes only (2026-07-05, user rule)

Dashed strokes in a control map LEAK into generated art as painted dot marks
(proven: Marriott r12 dome tops + door-anchor dashes). Templates carry dashed
ANNOTATION lines (zone stripes, anchors, guides) and even black dashed guide
strokes that pixel-classify identically to cuts. Rules for any packet/control
builder (see scripts/master_spec.py for the reference implementation):
- Drop small black components (< ~300 px at ~0.55 px/pt) — real cuts are long
  strokes or hole rings; dash segments are tiny blobs.
- Outer contour = smooth boundary of the CLOSED silhouette (close-then-open to
  kill dash scallops), never the raw dash-bridged arc.
- Never trace dashed anchor shapes — draw a SYNTHETIC solid outline from the
  anchor's percentile bbox (arch = straight sides + semicircle top).

## Geometry comes from VECTOR paths, not raster reconstruction (2026-07-05, binding)

The master-template geometry lives in the .ai bezier paths. Extract them once with
scratchpad/master_paths.jsx (read-only; opens the master template explicitly) →
tasks/_templates/master_paths.json, then build the contract with
`python3 scripts/vector_spec.py --outdir <dir>`. It renders CONTINUOUS SOLID
strokes per class and needs NO morphology — dashes are just stroke styling over a
real path, so a continuous stroke has no gaps to bridge. This is the source of
truth; `scripts/master_spec.py` (raster PNG reconstruction) is SUPERSEDED — it
caused the jagged arch, the r16c synthetic wide-anchor, and dash leaks, and its
heuristics were co-tuned to the messy export (broke on clean input).

vector_spec rules baked in (don't re-derive):
- silhouette: the die-cut is ONE continuous strip, so per-panel side/base edges are
  the crop window (seal them), NOT real cuts. Domed panels (left/door/right) flood
  the exterior from the TOP only — the yellow/green envelope arc closes the dome.
  Stab strips seal all four borders (near-rectangular; contour open on one side).
- body vs holes: classify interior regions by AREA (≥3% of panel = paintable body).
  The door face splits into left/centre/right thirds at the slot cuts — all three
  are body; "largest component only" dropped two of them (body_frac 0.34, wrong).
- door anchor: render the orange bezier path directly (smooth), never a synthetic
  bbox+semicircle (r16c: the bbox was ~35% too wide from stray edge dashes).

Verification (mandatory before any gen uses a new contract): the arch/contour must
be SMOOTH — overlay or per-column top-edge check, jumps ≤ a few px/col (see
tests/test_vector_spec.py::test_door_arch_is_smooth and the v2-vs-v3 proof at
scratchpad/arch-smoothness-v2-vs-v3.png). If you ever reconstruct from raster
again, verify pixel-on-pixel against the source and eyeball coincidence — but the
vector path removes the need.
