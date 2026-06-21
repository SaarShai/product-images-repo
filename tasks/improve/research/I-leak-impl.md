# I — Perceptual outside-mask leakage metric

**Goal.** `compose_fairy.py --diffmask` already reports the **raw** max pixel delta
OUTSIDE the edit mask (=0 ideal). But a whole-crop-repaint engine (Flux.2 /
Kontext) can subtly **repaint** the background — same palette, shifted
texture/structure — which a byte-pixel gate near a feathered seam can miss. We
need a **perceptual** check that the region OUTSIDE the mask is *perceptually
unchanged*.

Research consensus: **DINOv2 patch-cosine** is the most sensitive local-edit
detector; **LPIPS** (learned perceptual) and **SSIM** (structural) are useful,
cheap complements. The metric combines all three.

---

## Install

Dedicated venv, isolated from the other `.venv-*`. **Python 3.12** is required —
the DINOv2 `torch.hub` code uses PEP-604 `X | None` type unions that fail to
import on the repo's system Python 3.9.

```bash
python3.12 -m venv .venv-metric
.venv-metric/bin/python -m pip install --upgrade pip
.venv-metric/bin/python -m pip install torch torchvision piq lpips torchmetrics numpy pillow scikit-image
# Do NOT add xformers — it needs a CUDA toolchain and fails to build on macOS;
# DINOv2 runs fine without it (falls back to standard attention, harmless warnings).
```

Versions used: torch 2.12.1 (MPS available), torchvision 0.27.1, scikit-image
0.26.0, lpips (AlexNet backbone), DINOv2 ViT-S/14 (`dinov2_vits14`, 84 MB).
First run downloads two weight files into `~/.cache/torch` (AlexNet 233 MB for
LPIPS, DINOv2 84 MB); afterward every run is fast. Apple M3 Max, `mps`,
`PYTORCH_ENABLE_MPS_FALLBACK=1`.

## Script

`scripts/leak_metric.py` (new; no other script modified).

```
PYTORCH_ENABLE_MPS_FALLBACK=1 .venv-metric/bin/python scripts/leak_metric.py \
    --orig A.png --edited B.png --mask M.png \
    [--thresh 0.06] [--lpips-ref 0.15] [--no-dino] [--json out.json]
```

**Mask semantics** (match `compose_fairy.py`): WHITE (>127) = the EDITED region
(taxi / fairy). The metric scores the **complement** (everything outside white).
Mask is auto-resized (nearest) to the orig size.

Computed OUTSIDE the mask only:

- **(a) SSIM** — windowed structural similarity (skimage, gaussian weights). The
  edit region is neutralized to a constant grey in *both* images first, so SSIM
  windows straddling the seam see no difference and can't drag the outside score
  down. 1.0 = identical.
- **(b) LPIPS** — AlexNet learned perceptual distance; edit region neutralized
  identically in both images so the distance is driven by outside-mask change.
  0.0 = identical.
- **(c) DINOv2 patch-cosine** — DINOv2 ViT-S/14 `x_norm_patchtokens`, cosine
  similarity per patch between orig & edited, averaged over patches that fall
  outside the edit mask. 1.0 = identical. **Falls back to LPIPS+SSIM** (`--no-dino`,
  or auto on load failure) if DINOv2 is unavailable; MPS forward errors auto-retry
  on CPU.

**Leakage score** (0 = clean .. 1 = heavy leak) = max of the per-signal leaks:

```
leak = max( 1 - SSIM_out ,  min(1, LPIPS_out / LPIPS_REF) ,  1 - DINO_cos_out )
PASS = leak < thresh        (default thresh 0.06)
```

`max` (not mean) so any one signal detecting leakage trips the gate. Exit code
0 = PASS, 1 = FAIL (usable as a gate).

---

## TEST — two cases from existing files

Masks built into `tasks/nyc-taxi/work/`:
- `clean_mask.png` — full-res 4192x3848, white over the 3 changed taxi bboxes
  `(140,2940,1300,3400) ∪ (1665,2985,2705,3360) ∪ (3235,2980,4035,3355)` (7.6% white).
- `leak_mask.png` — 1200x800 crop, tight taxi-only bbox `(140,300,1180,720)` (45.7% white).

Raw-pixel ground truth (sanity): CLEAN outside-mask max|Δ| = **0** (byte-identical);
LEAK outside-mask mean|Δ| = **57.4**, max 255 (buildings repainted).

### Results

| case  | inputs | outside frac | SSIM_out | LPIPS_out | DINOv2_cos_out (leak) | **leak** | thresh | verdict |
|-------|--------|-------------:|---------:|----------:|----------------------:|---------:|-------:|:-------:|
| CLEAN | nyc-hires.png → nyc-fixed.png | 0.924 | 1.0000 | 0.0000 | 0.9994 (0.0006), 1156 patches | **0.0006** | 0.06 | **PASS** (exit 0) |
| LEAK  | left_ctx.png → L_flux2.png    | 0.543 | 0.3489 | 0.3105 | 0.7470 (0.2530), 479 patches  | **1.0000** | 0.06 | **FAIL** (exit 1) |

**Separation:** the CLEAN case (background untouched) scores leak = 0.0006 and
PASSes; the LEAK case (Flux.2 repainted the buildings outside a taxi-only mask)
saturates to leak = 1.0000 and FAILs. Gap of ~0.0006 vs 1.0 — wide and
unambiguous. **Every signal fires independently**, including DINOv2 patch-cosine
(0.9994 vs 0.7470 → dino_leak 0.0006 vs 0.2530). The metric cleanly distinguishes
a clean local edit from a whole-crop repaint.

LPIPS+SSIM alone already separate them perfectly (leak 0.00 vs 1.00); DINOv2 adds
a third independent confirmation and is the more sensitive detector for *subtle*
repaints than this obvious one (its dino_leak of 0.2530 alone clears the 0.06
gate by 4x).

### JSON artifacts
- `tasks/nyc-taxi/work/clean_full.json`, `tasks/nyc-taxi/work/leak_full.json` (with DINOv2)
- `tasks/nyc-taxi/work/clean_nodino.json`, `tasks/nyc-taxi/work/leak_nodino.json` (LPIPS+SSIM only)

## Threshold guidance
- **0.06** chosen as a conservative default: a clean edit lands ~0.00; the leak
  case is 1.00. Any value in (0.0, ~0.3) separates these two. Tighten toward 0.03
  to catch subtler repaints, loosen toward 0.10 if benign JPEG/compression noise
  outside the mask causes false fails.
- LPIPS normalization ref `--lpips-ref 0.15` maps a "clearly different" LPIPS to
  leak 1.0; tune per engine if needed.
