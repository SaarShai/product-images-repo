# G — Free local object eraser (IOPaint / LaMa) implementation

Goal: a FREE, offline, no-API-key object eraser as a **first-try fallback** to the paid
fal Bria eraser (`scripts/falgen.py --mode eraser`). Verdict up front: **WORKS / TEST PASS
on structure, but quality is below Bria on line-art/watercolor art** — good enough as a
free first pass for photo-ish backgrounds, NOT a drop-in replacement for Bria on
illustrated panels. Use it free-first, escalate to Bria when the smear is visible.

## Install steps that worked

System `python3` is 3.9.6 — too old for current IOPaint/torch wheels. Used **Python
3.12** (`~/.local/bin/python3.12`, 3.12.13) in a dedicated venv. No other scripts touched.

```bash
cd "/Users/za/Documents/product images repo"
python3.12 -m venv .venv-iopaint
.venv-iopaint/bin/pip install --upgrade pip
.venv-iopaint/bin/pip install iopaint torch torchvision
```

Installed cleanly: **iopaint 1.6.0, torch 2.12.1, torchvision 0.27.1** (MPS build —
`torch.backends.mps.is_available() == True`). No `simple-lama-inpainting` / replicate
fallback was needed.

Weights are NOT bundled. LaMa's `big-lama.pt` (~205MB) is pulled on demand into a
repo-local model dir (keeps `~/.cache` clean):

```bash
.venv-iopaint/bin/iopaint download --model lama --model-dir ./.iopaint-models
# -> .iopaint-models/torch/hub/checkpoints/big-lama.pt  (208M on disk)
```

The script also auto-downloads on first run if the weights are missing, so the explicit
`iopaint download` is optional.

Gotcha that cost time: `ModelManager(name="lama")` raises `NotImplementedError: Unsupported
model: lama` unless the env var `XDG_CACHE_HOME` points at the model dir BEFORE importing
iopaint — IOPaint discovers erase models by scanning that dir. The script sets
`XDG_CACHE_HOME` / `U2NET_HOME` to `.iopaint-models` at import time (override with
`IOPAINT_MODEL_DIR`).

## Script

`scripts/lama_erase.py` — CLI matches falgen's eraser I/O shape:

```bash
.venv-iopaint/bin/python scripts/lama_erase.py \
    --image SRC.png --mask MASK.png --out OUT.png \
    [--dilate 12] [--device mps|cpu]
```

- `--mask`: white(255)=REMOVE, black=keep (same convention as falgen eraser).
- Mask is **dilated ~12px** (cv2 ellipse kernel, PIL MaxFilter fallback) before erase to
  cover ink halos / soft outlines just outside the object.
- `PYTORCH_ENABLE_MPS_FALLBACK=1` is set automatically; on any MPS init/run error it retries
  on CPU and prints that it did so.

## Device reality (MPS)

`--device mps` is accepted, BUT IOPaint logs `lama not support mps, switch to cpu` and runs
the LaMa **TorchScript JIT model on CPU internally**. This is an IOPaint limitation (the
big-lama JIT graph isn't MPS-traceable), not a bug in this script. Net effect: LaMa erase is
CPU-bound here regardless of `--device`. It's still fast (see runtime). SD/diffusion erase
models in IOPaint do use MPS, but LaMa specifically does not.

## TEST result — middle taxi

Inputs: `tasks/nyc-taxi/work/M2_ctx.png` (1120x700 watercolor NYC street, yellow taxi) +
`tasks/nyc-taxi/work/mask_Mremove.png` (rounded-rect, 47.6% coverage over the taxi).
Output: `tasks/improve/_lama_mid.png`. Compared vs paid Bria `tasks/nyc-taxi/work/M2_erased.png`.
Hi-DPI crops of the masked region saved as `tasks/improve/_cmp_lama_crop.png` and
`_cmp_bria_crop.png` and inspected by eye.

**PASS (with a quality caveat).** What I saw:
- **Taxi: completely gone** in both LaMa and Bria. No ghost, no leftover wheels/body.
- **Background reconstruction: plausible** in LaMa — the building facades, the blue
  building, window rows on the right, and the ground/sidewalk line all continue across the
  hole sensibly. Structure is correct.
- **Quality gap (the caveat):** LaMa's fill is visibly **soft/smeary with a faint
  fabric-like texture**, and it loses the crisp ink line-art of the watercolor style; a grey
  smudge sits at the lower-left of the masked band. Bria's fill is **clean** — sharp window
  grids, crisp line-art panels, clean sidewalk, fully in the original illustration style.
- Root cause: LaMa is trained on photos. On a clean-line illustration it inpaints structure
  well but cannot reproduce the ink-outline aesthetic, so it reads as a blurry patch.

## Runtime

~**4.3s inference** (4.6s wall incl. model load) for 1120x700, CPU (MPS unsupported for
LaMa). First-ever run adds a one-time ~205MB weight download. No per-call cost, no quota,
fully offline thereafter.

## Is it good enough to be the free-first eraser?

**Yes as a free first pass; no as a Bria replacement on illustrated art.**
- Free, offline, no key, ~4s, taxi removed + structure rebuilt → great default first attempt
  and a real cost saver for photo-ish or low-detail backgrounds.
- But on this watercolor/line-art panel the smear is obvious next to Bria. Recommended
  routing: run `lama_erase.py` first; if the masked region looks smeared/off-style on review
  (or for hero output), escalate to `falgen.py --mode eraser` (Bria). For illustration work
  specifically, Bria stays the quality bar.

## Files

- Script: `scripts/lama_erase.py`
- Venv: `.venv-iopaint/` (Python 3.12) — dedicated, no other scripts modified
- Weights: `.iopaint-models/torch/hub/checkpoints/big-lama.pt` (~205MB)
- Test out: `tasks/improve/_lama_mid.png`
- Comparison crops: `tasks/improve/_cmp_lama_crop.png`, `tasks/improve/_cmp_bria_crop.png`
