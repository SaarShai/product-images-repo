# `scripts/fit.py` — one-command SVG die-cut FIT wrapper

Thin wrapper that makes the verified SDXL-CN geometry route usable in one command,
without remembering the multi-step `controlnet_sdxl_gen.py` + `measure_sdxl_cn.py`
invocation (matching `--bbox`, overlay, JSON parse, threshold).

It does NOT reimplement generation or measurement — it shells out to the two
existing scripts and prints a single PASS/FAIL verdict.

## What it does

1. Resolves `--panel center|left|right|auto` to a `--bbox L,T,R,B` (SVG user units)
   via `skyline_panel.panel_bbox` — the canonical skyline 3-panel convention
   (`center` → the `door`/center `outer_contour`; `left`/`right` → narrow side
   paintable panels; `auto` → largest body). Reusing this keeps the crop identical
   to the rest of the skyline tooling.
2. Runs `scripts/controlnet_sdxl_gen.py` (SDXL-inpaint + xinsir canny ControlNet on
   the SVG lineart; openings masked out + composited to white).
3. Runs `scripts/measure_sdxl_cn.py` with the SAME bbox → writes an overlay +
   metrics JSON, then prints PASS/FAIL on `region_iou >= --iou-pass` (default 0.90)
   AND `holes_clear`.
4. Exit 0 on PASS, 1 on FAIL (or on any sub-step error).

## Usage

```bash
.venv-gen/bin/python scripts/fit.py \
  --svg "assets/skyline/city-skyline template.svg" \
  --panel center \
  --prompt "a watercolor-and-ink city brownstone facade" \
  [--out tasks/improve/_fit_center.png] [--width 1024] [--steps 30] [--seed 7] \
  [--iou-pass 0.90] [--negative-prompt "..."] [--smoke]
```

Outputs (next to `--out`): `<out>.png`, `<out>_overlay.png`, `<out>_metrics.json`.
Run with the project `.venv-gen` interpreter (needs the diffusers stack; MPS).
Models load from the local HF cache — no network. `--smoke` = tiny-res 2-step
wiring check only (not a real fit).

## TEST (required command, full run)

Command:
```
.venv-gen/bin/python scripts/fit.py --svg "assets/skyline/city-skyline template.svg" \
    --panel center --prompt "a watercolor-and-ink city brownstone facade" \
    --out tasks/improve/_fit_center.png
```

Result (30 steps @ 1024px, ~202s on MPS):

| metric | value |
|---|---|
| verdict | **PASS** |
| region-IoU | **1.0000** |
| holes-clear | **True** (13/13 cutouts clear) |
| coverage | 1.0000 |
| outside_frac | 0.0000 |
| exit code | 0 |

Artifacts:
- `tasks/improve/_fit_center.png` (828 KB)
- `tasks/improve/_fit_center_overlay.png`
- `tasks/improve/_fit_center_metrics.json`

Smoke pre-check (separate, fast): PASS, region-IoU 0.9765, 13/13 holes clear, exit 0.

## Visual finding (overlay-reviewed, not metric-only)

The overlay confirms the geometry gate is honest at the pixel level: every contour /
cutout outline is green (none red), holes are empty white. BUT the painted artwork is
a **tapered trapezoid** — the model traced the door-flap diagonal cut edges as the
silhouette, leaving the door's outer corners white (the known skyline "taper /
trapezoid" failure mode). The `measure_sdxl_cn` `region_iou` (= painted ∩ body-minus-
holes) does not penalize this taper, so PASS on region-IoU/holes-clear is necessary
but NOT sufficient for visual fill quality. This is a generation-quality issue
(prompt/guide), not a wrapper defect — the wrapper ran the route and reported its
metrics faithfully. To address the taper, drive gen with the `skyline_panel` grey-body
guide (bold OUTER contour, faint interior hints) per the skyline-template skill, and
add a side-fill/taper gate to the PASS criteria.
