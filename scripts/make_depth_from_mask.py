#!/usr/bin/env python3
"""Create a simple synthetic depth map from a portal mask."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def depth_from_mask(mask: Image.Image | np.ndarray, invert: bool = False, blur_radius: float = 4.0) -> Image.Image:
    if isinstance(mask, Image.Image):
        mask_image = mask.convert("L")
    else:
        mask_image = Image.fromarray(np.asarray(mask).astype(np.uint8)).convert("L")
    if blur_radius > 0:
        mask_image = mask_image.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    alpha = np.asarray(mask_image, dtype=np.float32) / 255.0
    background = 128.0
    portal = 0.0 if invert else 255.0
    depth = background + alpha * (portal - background)
    return Image.fromarray(np.clip(depth, 0, 255).astype(np.uint8))


def parse_args(argv: list[str] | None = None):
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path, help="portal-mask PNG; white is portal opening")
    ap.add_argument("output", type=Path, help="output depth-map PNG")
    ap.add_argument("--invert", action="store_true", help="make the portal dark/far instead of bright/near")
    ap.add_argument("--blur-radius", type=float, default=4.0, help="Gaussian blur radius for the transition")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    mask = Image.open(args.input)
    depth = depth_from_mask(mask, invert=args.invert, blur_radius=args.blur_radius)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    depth.save(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
