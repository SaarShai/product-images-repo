# M — edit.py hardening (provenance + free eraser + auto-gates)

Three upgrades layered onto `scripts/edit.py` (the one-command element-edit
dispatcher) without breaking the proven `automask -> mask_check -> engine ->
diffmask compose -> pixel gate -> judge` happy path. Only `scripts/edit.py` was
modified; it now also writes a `<out>.json` sidecar.

## 1) PROVENANCE — `<out>.json` sidecar
Every run writes a JSON next to the output capturing everything needed to
reproduce/audit the edit:
`src, op, element, desc, box, free, engine, seed, mask_dilate, ctx_pad,
src_size, crop, mask_bbox, jcrop, out, overlay, pixel_gate_ok, leak_metric{},
text_gate{}, judge{}, result, timestamp(null — harness has no clock),
tool_versions.git_rev`.
`git_rev` is read via `git -C <root> rev-parse --short HEAD` (None if
unavailable). `engine` is one of `fal_bria | lama_local | fal_flux_fill`.

## 2) `--free` flag (op=remove → free local eraser)
With `--free`, op=remove routes to the FREE local LaMa eraser
(`.venv-iopaint/bin/python scripts/lama_erase.py`) instead of paid fal Bria.
Default (no flag) stays Bria (better on watercolor). Degrades gracefully: if
`.venv-iopaint` is missing, prints a warning and falls back to Bria so `--free`
never silently no-ops. `--free` is a no-op for op=redraw (Flux Fill only).

## 3) AUTO-GATES (cross-venv, non-fatal)
After compose, two extra gates run in their own venvs, capture exit code, and
fold into the SUCCESS/NEEDS-REVIEW decision (they only BLOCK when *available and
failing* — an unavailable/skipped gate never flips a pass to a fail):
- **leak_metric** (`.venv-metric`): perceptual outside-mask leak. Needs a
  full-size mask whose white = edited region; `edit.py` synthesizes one from the
  full-coord element bbox (`ex0,ey0,ex1,ey1`). exit 0 = PASS.
- **text_gate** (`.venv-ocr`, op=remove only): deterministic leftover-text OCR
  over the judge crop. exit 0 = no text.
Numbers are printed in the final report and stored in the provenance JSON.

## Decision logic
- remove: `pixel_gate_ok AND judge.leftover_text is False AND NOT leak_blocks AND
  NOT text_blocks`
- redraw: `pixel_gate_ok AND judge.verdict==PASS AND judge.leftover_text is False
  AND NOT leak_blocks`
(For removals the VLM judge verdict is intentionally NOT a pass-condition — it
reports the subject "not visible", which is the goal; correctness is keyed off
leftover-text + the two new gates.)

## Graceful degradation
Each sub-venv is guarded by `VENV_X.exists()`. Missing venv ⇒ warn + skip (gate
marked `available:false`, recorded in provenance, never blocks). `--free`
fallback to Bria likewise warns. Constraint honored: only `scripts/edit.py` was
touched (+ the `.json` it writes).

## TEST — proven NYC-taxi removal (cache reuse, Bria default path)
```
python3 scripts/edit.py --src tasks/nyc-taxi/out/nyc-fixed.png --op remove \
  --element "small yellow taxi car" --box 3200,2950,3760,3320 \
  --out tasks/improve/_edit_hardened.png
```
Outputs (quoted):
```
  [compose] OUTSIDE-MASK changed_pixels=0  outside_max_delta=0  (gate: ~0)
  leak_metric: verdict=PASS leak_score=0.002008 ssim_outside=0.999994 \
               lpips_outside=1.9e-05 dino_outside=0.997992 (exit=0)
  text_gate: no_text=True found=[] (exit=0)
  pixel gate outside-mask delta 0: True
  provenance -> tasks/improve/_edit_hardened.png.json
  RESULT: SUCCESS (op=remove)
```
Process exit code: **0**. Provenance JSON written with `engine: fal_bria`,
`pixel_gate_ok: true`, `leak_metric.pass: true`, `text_gate.no_text: true`,
`tool_versions.git_rev: 59cff27`, `result: SUCCESS`.

## SMOKE TEST — `--free` (local LaMa eraser, no fal cost)
```
python3 scripts/edit.py ... --out tasks/improve/_edit_free.png --free
```
Quoted:
```
  [lama_erase] OK device=mps -> .../regen.png  1040x850  5.5s
  [compose] OUTSIDE-MASK changed_pixels=0  outside_max_delta=0  (gate: ~0)
  leak_metric: verdict=PASS leak_score=0.002077 ... (exit=0)
  text_gate: no_text=True found=[] (exit=0)
  RESULT: SUCCESS (op=remove)
```
Process exit code: **0**. Provenance recorded `engine: lama_local`, `free: true`,
all gates pass — confirming the cost-saving local path is fully wired and gated.
