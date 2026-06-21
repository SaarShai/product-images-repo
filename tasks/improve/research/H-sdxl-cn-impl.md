# H — SDXL ControlNet exact-geometry generation (implementation)

Goal: upgrade the exact-SVG-contour generation route from the weak SD1.5 ControlNet
inpaint (`scripts/controlnet_inpaint_gen.py`) to **SDXL-inpaint + xinsir canny SDXL
ControlNet**, fed the authoritative SVG geometry (lineart/canny control image +
opening/hole mask) so artwork fills the contour and holes/keep-clear stay empty.

Date: 2026-06-21. Host: Apple M3 Max, MPS, `.venv-gen` (torch 2.12.1, diffusers
0.38.0, PYTORCH_ENABLE_MPS_FALLBACK=1). All geometry numbers are **MEASURED**, not
claimed.

**Status: PASS.** One test image proved the route: region-IoU **1.000**, all 13
in-panel openings clear (worst hole painted-fraction 0.000), 0% paint outside the
contour.

---

## 0. What was built

- **`scripts/controlnet_sdxl_gen.py`** (rewritten — the old file on this path was a
  txt2img `StableDiffusionXLControlNetPipeline` on SDXL-base that did NOT mask holes;
  replaced with the inpaint route). New script:
  - Reuses the authoritative parser `svg_classify` (no duplicate SVG parser).
  - Rebuilds the SAME body/hole-mask construction as `controlnet_inpaint_gen.py`
    (`paint = (outer_contour ∪ paintable_region) − internal_cutout`) and the SAME
    viewBox→pixel mapping as `svg_to_controlmap.py`.
  - Loads `diffusers/stable-diffusion-xl-1.0-inpainting-0.1` + `xinsir/controlnet-
    canny-sdxl-1.0` on MPS via `StableDiffusionXLControlNetInpaintPipeline`.
  - `--bbox L,T,R,B` isolates ONE panel of the multi-panel template; with a bbox it
    applies a **centroid in-crop filter** so side-panel cutouts aren't mis-mapped
    into the crop (they otherwise punch false holes / invite false bleed).
  - **Hard exact-geometry composite** (default on, `--no-composite` to disable):
    after sampling, every KEPT region (holes + outside the paint mask) is forced to
    pure white. Required because on MPS the SDXL-inpaint VAE decode tints the WHOLE
    canvas grey — it does NOT keep masked latents byte-exact (see §3). This is what
    makes region-IoU → 1.0 "by construction"; the model still only invents content
    inside the paint region, bounded by the canny ControlNet contour.
  - Prompt-template style: NO geometry/production strokes in the prompt; geometry
    comes only from the control image + mask.
- **`scripts/measure_sdxl_cn.py`** (new): measurement gate. Reuses `svg_classify` +
  the identical src-rect masks (and the identical centroid in-crop filter) to report
  region-IoU(painted, intended-region), coverage, outside-bleed fraction, and per-
  hole painted fraction; writes an overlay + JSON. Numbers describe exactly what was
  generated (no whole-template-bounds mismatch that `svg_geometry_check.py` would
  inject when only one sub-panel is generated).

The existing `svg_to_controlmap.py`, `svg_geometry_check.py`, `svg_classify.py`, and
`controlnet_inpaint_gen.py` were NOT modified.

---

## 1. Models — already cached, NO download needed

Both required models were present in the HF cache (`~/.cache/huggingface/hub`):
- `diffusers/stable-diffusion-xl-1.0-inpainting-0.1` (~19G; UNet cached **fp16-only**)
- `xinsir/controlnet-canny-sdxl-1.0` (2.3G; **plain weights only**, no fp16 variant)

Variant gotcha (fixed in the loader): the base UNet ships ONLY
`diffusion_pytorch_model.fp16.safetensors` (no plain `.safetensors`), so loading with
`variant=None` triggers a multi-GB fp32 UNet download. The xinsir CN ships ONLY plain
weights, so `variant="fp16"` 404s for it. The script loads with `--variant fp16`
(default) and per-repo falls back to `variant=None` when the fp16 file is missing —
verified to run fully offline (`HF_HUB_OFFLINE=1`) with no network. Compute dtype is
fp32 (`--dtype float32`, MPS-safe; fp16 weights are upcast on load).

Also added `shapely==2.1.2` to `.venv-gen` via `uv pip install` (the geometry scripts
import it and it was absent). No conflict with torch/diffusers/numpy.

---

## 2. Working settings (the proven run)

Test region: the **center "door" panel** of `assets/skyline/city-skyline template.svg`,
`--bbox 1866.5,276.7,4770.9,4490.4` (the `outer_contour`, portrait aspect 0.688).

| setting | value |
|---|---|
| resolution | **768 × 1112** (`--width 768`, height derived from src aspect, ×8) |
| steps | **30** |
| controlnet_conditioning_scale | **0.85** |
| guidance_scale | **6.5** |
| strength | **1.0** |
| seed | 7 |
| dtype / variant | float32 / fp16 (base), auto-fallback to none (CN) |
| device | mps |

Timing/memory (M3 Max): pipeline load ~9–13 s, sampling ~2.0–2.2 s/step (~65 s for
30 steps), ~73–85 s total. Peak RSS ~5.4 GB. **No OOM.** Smoke test (384 px, 2 steps)
ran in 24 s total and confirmed memory fit before the full run, so no resolution/step
reduction was needed at 768 px. (If a larger panel OOMs, drop `--width` to 640/512 or
steps to 20 — the smoke path at 384 px is the floor that is known to fit.)

Command:
```
PYTORCH_ENABLE_MPS_FALLBACK=1 HF_HUB_OFFLINE=1 .venv-gen/bin/python \
  scripts/controlnet_sdxl_gen.py \
  --svg "assets/skyline/city-skyline template.svg" \
  --bbox 1866.5,276.7,4770.9,4490.4 \
  --out tasks/improve/_sdxl_cn_center.png \
  --width 768 --steps 30 --cond-scale 0.85 --guidance 6.5 --save-debug \
  --prompt "a clean flat-color cityscape illustration, simple stylized buildings and rooftops, soft pastel colors, children's book style, white background"
```

---

## 3. The key finding (why the composite is mandatory)

The SDXL ControlNet **inpaint** pipeline on MPS does NOT keep masked regions clear by
itself. With the raw pipeline output (`--no-composite`):
- painted-inside-holes = **99.95%** (the VAE decode tints the entire canvas grey,
  ~RGB [186,171,168], including the central doorway AND outside the contour),
- IoU(painted, full door silhouette) = 0.945 but IoU(painted, intended frame region)
  = **0.32**, holes NOT clear.

So the SD1.5 script's "region-IoU → 1.0 by construction" does NOT transfer to SDXL on
this host purely via the pipeline mask. The fix is a deterministic post-composite that
whites out every kept pixel (holes + outside). After compositing the openings are
provably empty and the contract holds. The model's invented content is unaffected —
it only ever painted the body region, bounded by the canny ControlNet contour.

A second fix that mattered: when isolating one panel via `--bbox`, the SVG's 25
cutouts span all three panels. Without the centroid in-crop filter, side-panel cutouts
map onto the center body and (a) wrongly punch holes in generation and (b) read as
"painted holes" in measurement. The filter restricts geometry to the 13 cutouts whose
centroid lies inside the crop. Generation and measurement apply the IDENTICAL filter.

---

## 4. MEASURED result (the gate)

`scripts/measure_sdxl_cn.py tasks/improve/_sdxl_cn_center.png --bbox 1866.5,276.7,4770.9,4490.4`:

| metric | value |
|---|---|
| **region-IoU (painted vs intended region)** | **1.0000** |
| coverage (painted fraction of region) | 1.0000 |
| outside-contour bleed fraction | 0.0000 |
| **holes clear** | **True — 13 / 13** |
| worst hole painted-fraction | 0.0000 |

Verified visually too (per repo rule: never score from the metric alone):
- `tasks/improve/_sdxl_cn_center.png` — pink brick archway painted in the frame; the
  central arched doorway and the area outside the door silhouette are pure white.
- `tasks/improve/_sdxl_cn_center_overlay.png` — every SVG contour/cutout line is GREEN
  (all PASS); paint sits inside the frame, openings empty.

Artifacts: `tasks/improve/_sdxl_cn_center.png`, `_sdxl_cn_center_overlay.png`,
`_sdxl_cn_center_control.png`, `_sdxl_cn_center_mask.png`,
`_sdxl_cn_center.metrics.json`, plus the smoke set `_sdxl_cn_smoke*.png`.

---

## 5. PASS/FAIL

**PASS.** SDXL-inpaint + xinsir canny SDXL ControlNet generates artwork that fills the
exact SVG contour with all openings kept empty: measured region-IoU 1.000, holes clear
13/13, 0% outside bleed, on MPS with no OOM and no model download. The route is a drop-
in richer-prior upgrade of the SD1.5 inpaint script, with two implementation
requirements made explicit: fp16-variant loading (cache has no fp32 UNet) and the
hard white-out composite (the SDXL inpaint VAE leaks grey into kept regions on MPS).

Open follow-ups (not blocking): the `internal_cutout` classification treats the door-
leaf paths as keep-clear holes for this door panel — for a panel where those are meant
to be painted detail, a panel-typed role override would be needed; and style quality
(vs the watercolor target) is a separate aesthetic pass, not part of this geometry gate.
