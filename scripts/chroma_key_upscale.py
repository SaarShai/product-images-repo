#!/usr/bin/env python3
"""chroma_key_upscale.py — alpha-safe x4 upscale of a keyed RGBA PNG.

Route B (RGB via Real-ESRGAN x4plus, alpha via Lanczos, recombined) — the
verified pattern from tasks/double-marine-bed-wrapper-batch/alpha_aware_upscale.py
(alpha MAE 0 vs the Lanczos reference). Before upscaling, fully-transparent
pixels have their RGB nearest-neighbor-filled from the closest opaque/AA
pixel so the RGB super-resolution net never sees a hard green-to-art edge
(which would otherwise bleed a thin green fringe back in after the alpha
channel is recombined, since the alpha near the edge is soft, not binary).

Usage:
  .venv-gen/bin/python -B scripts/chroma_key_upscale.py IN.png OUT.png [--scale 4]

  --binary-alpha: after the Lanczos alpha resize, threshold back to a hard
  binary mask (>=128 -> 255 else 0). Required for print-profile inputs whose
  source alpha is already binary (e.g. chroma-key/green-purge outputs) —
  Lanczos resampling reintroduces soft/AA alpha values that fail the print
  profile's D2_soft_alpha_fringe gate (soft_perimeter_ratio_max_print = 0.0).
  Default OFF, preserving existing (soft-alpha-preserving) behavior for
  non-print callers.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

Image.MAX_IMAGE_PIXELS = None


def refill_transparent_rgb(rgba: np.ndarray) -> np.ndarray:
    """Nearest-neighbor-fill RGB under alpha==0 pixels from the closest
    non-fully-transparent pixel (push/pull style), so no raw key-color RGB
    survives to confuse the RGB-only upscaler."""
    rgb = rgba[..., :3].astype(np.uint8).copy()
    alpha = rgba[..., 3]
    transparent = alpha == 0
    if not transparent.any():
        return rgb
    _, indices = distance_transform_edt(transparent, return_indices=True)
    filled = rgb[indices[0], indices[1]]
    rgb[transparent] = filled[transparent]
    return rgb


def esrgan_rgb(rgb: np.ndarray, scale: float, device: str, tile: int) -> np.ndarray:
    import torch
    from realesrgan import RealESRGANer
    from basicsr.archs.rrdbnet_arch import RRDBNet

    from chroma_key import REPO  # noqa: E402

    dst = Path.home() / "models-gen" / "esrgan" / "RealESRGAN_x4plus.pth"
    if not dst.exists():
        import urllib.request
        dst.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(
            "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth", dst
        )

    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
    dev = torch.device(device)
    up = RealESRGANer(scale=4, model_path=str(dst), model=model, tile=tile, tile_pad=10, pre_pad=0, half=False, device=dev)
    bgr = rgb[:, :, ::-1]
    out, _ = up.enhance(bgr, outscale=scale)
    return out[:, :, ::-1]


def resize_alpha(alpha: np.ndarray, out_w: int, out_h: int, binary: bool = False) -> np.ndarray:
    """Lanczos-resize an alpha channel to (out_w, out_h); optionally threshold
    the result back to a hard binary mask (>=128 -> 255 else 0)."""
    alpha_img = Image.fromarray(alpha, mode="L")
    up_alpha = np.array(alpha_img.resize((out_w, out_h), Image.Resampling.LANCZOS))
    if binary:
        up_alpha = np.where(up_alpha >= 128, 255, 0).astype(np.uint8)
    return up_alpha


def upscale_rgba(rgba: np.ndarray, scale: float, device: str, tile: int, binary_alpha: bool = False) -> tuple[np.ndarray, dict]:
    h, w = rgba.shape[:2]
    filled_rgb = refill_transparent_rgb(rgba)
    up_rgb = esrgan_rgb(filled_rgb, scale, device, tile)
    out_h, out_w = up_rgb.shape[:2]

    up_alpha = resize_alpha(rgba[..., 3], out_w, out_h, binary=binary_alpha)

    out = np.dstack([up_rgb, up_alpha])
    metrics = {
        "in_size": [w, h],
        "out_size": [out_w, out_h],
        "scale_x": round(out_w / w, 4),
        "scale_y": round(out_h / h, 4),
        "alpha_method": "lanczos_independent_resize" + ("_binary_threshold" if binary_alpha else ""),
        "rgb_method": "realesrgan_x4plus_on_nn_refilled_rgb",
    }
    return out, metrics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("out")
    ap.add_argument("--scale", type=float, default=4.0)
    ap.add_argument("--device", default="cpu", choices=["cpu", "mps"])
    ap.add_argument("--tile", type=int, default=512)
    ap.add_argument("--binary-alpha", action="store_true", help="threshold resized alpha back to {0,255} (required for print-profile binary-alpha inputs)")
    args = ap.parse_args()

    rgba = np.array(Image.open(args.image).convert("RGBA"))
    out, metrics = upscale_rgba(rgba, args.scale, args.device, args.tile, binary_alpha=args.binary_alpha)
    Image.fromarray(out, mode="RGBA").save(args.out)
    print(f"[chroma_key_upscale] {args.image} -> {args.out}  {metrics}")


if __name__ == "__main__":
    main()
