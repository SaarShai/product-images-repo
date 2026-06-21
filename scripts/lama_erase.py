#!/usr/bin/env python3
"""lama_erase.py — FREE local object eraser via IOPaint (LaMa model) on Apple MPS.

The free-first fallback to paid fal Bria eraser (scripts/falgen.py --mode eraser).
LaMa is a fast Fourier-convolution inpainting model — no prompt, no API key, no quota.
Runs fully offline once the model weights are cached.

I/O shape matches falgen's eraser:
  --image IMG : source image
  --mask  MASK: white(=255)=REMOVE region, black=keep
  --out   OUT : erased result (background reconstructed under the mask)

The mask is DILATED ~12px (configurable via --dilate) before erasing so ink halos /
soft outlines just outside the painted object are also covered.

Device: MPS by default (export PYTORCH_ENABLE_MPS_FALLBACK=1 is set automatically so
unsupported ops fall back to CPU). If MPS init/run fails, retries on CPU and says so.

Usage:
  python3 scripts/lama_erase.py --image SRC.png --mask MASK.png --out OUT.png
  python3 scripts/lama_erase.py --image SRC.png --mask MASK.png --out OUT.png --dilate 16 --device cpu

Requires the dedicated venv: .venv-iopaint/bin/python scripts/lama_erase.py ...
"""
import argparse
import os
import sys
import time
from pathlib import Path

# MUST be set before torch picks up the env: lets unsupported MPS ops fall back to CPU.
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

# IOPaint discovers downloaded erase-model weights via XDG_CACHE_HOME. Default to a
# repo-local dir so weights live next to the venv (no pollution of ~/.cache).
_MODEL_DIR = os.environ.get(
    "IOPAINT_MODEL_DIR",
    str((Path(__file__).resolve().parent.parent / ".iopaint-models").absolute()),
)
os.environ["XDG_CACHE_HOME"] = _MODEL_DIR
os.environ["U2NET_HOME"] = _MODEL_DIR

import numpy as np
from PIL import Image


def load_image_rgb(path: str) -> np.ndarray:
    """Return HxWx3 uint8 RGB."""
    return np.array(Image.open(path).convert("RGB"))


def load_mask(path: str, size_wh) -> np.ndarray:
    """Return HxW uint8 binary mask (255=remove). Resized to match image (W,H)."""
    m = Image.open(path).convert("L").resize(size_wh, Image.NEAREST)
    arr = np.array(m)
    arr = np.where(arr > 127, 255, 0).astype(np.uint8)
    return arr


def dilate_mask(mask: np.ndarray, px: int) -> np.ndarray:
    """Grow the white (remove) region by ~px pixels to cover ink halos / soft edges."""
    if px <= 0:
        return mask
    try:
        import cv2
        k = 2 * px + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        return cv2.dilate(mask, kernel, iterations=1)
    except Exception:
        # PIL MaxFilter fallback (square kernel) if cv2 unavailable
        from PIL import ImageFilter
        k = 2 * px + 1
        m = Image.fromarray(mask).filter(ImageFilter.MaxFilter(k if k % 2 else k + 1))
        return np.array(m)


def run_lama(image: np.ndarray, mask: np.ndarray, device_str: str):
    """Run IOPaint LaMa. Returns BGR uint8 (IOPaint convention) -> caller converts."""
    import torch
    from iopaint.model_manager import ModelManager
    from iopaint.schema import InpaintRequest, HDStrategy
    from iopaint.download import scan_models

    # weights live under XDG_CACHE_HOME (set above); torch.hub downloads there too.
    torch.hub.set_dir(str(Path(_MODEL_DIR) / "torch" / "hub"))
    if "lama" not in {m.name for m in scan_models()}:
        # first run on a fresh machine: pull the ~205MB big-lama.pt
        from iopaint.download import cli_download_model
        print("[lama_erase] lama weights not found; downloading (~205MB)...", file=sys.stderr)
        cli_download_model("lama")

    device = torch.device(device_str)
    mgr = ModelManager(name="lama", device=device)
    # IOPaint expects RGB image (HWC) and HxW mask; returns BGR result.
    cfg = InpaintRequest(
        image=None, mask=None,
        hd_strategy=HDStrategy.RESIZE,
        hd_strategy_resize_limit=2048,
    )
    res_bgr = mgr(image, mask, cfg)
    return res_bgr  # HxWx3 uint8, BGR


def main():
    ap = argparse.ArgumentParser(description="FREE local LaMa object eraser (IOPaint, MPS).")
    ap.add_argument("--image", required=True, help="source image")
    ap.add_argument("--mask", required=True, help="mask: white(255)=remove")
    ap.add_argument("--out", required=True, help="output path")
    ap.add_argument("--dilate", type=int, default=12, help="dilate mask N px before erase (covers ink halos)")
    ap.add_argument("--device", default="mps", choices=["mps", "cpu"], help="primary device (falls back to cpu on mps error)")
    a = ap.parse_args()

    t0 = time.time()
    image = load_image_rgb(a.image)
    H, W = image.shape[:2]
    mask = load_mask(a.mask, (W, H))
    mask = dilate_mask(mask, a.dilate)
    white_frac = float((mask > 127).mean())
    print(f"[lama_erase] image={W}x{H} mask_white_frac={white_frac:.3f} dilate={a.dilate}px", file=sys.stderr)

    device_used = a.device
    try:
        res_bgr = run_lama(image, mask, a.device)
    except Exception as e:
        if a.device == "mps":
            print(f"[lama_erase] MPS FAILED ({type(e).__name__}: {e}); retrying on CPU", file=sys.stderr)
            device_used = "cpu"
            res_bgr = run_lama(image, mask, "cpu")
        else:
            raise

    # IOPaint returns BGR; convert to RGB for saving.
    res_rgb = res_bgr[:, :, ::-1]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(res_rgb.astype(np.uint8)).save(a.out)
    dt = time.time() - t0
    print(f"[lama_erase] OK device={device_used} -> {a.out}  {W}x{H}  {dt:.1f}s")


if __name__ == "__main__":
    main()
