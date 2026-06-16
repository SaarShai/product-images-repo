#!/usr/bin/env python3
"""Crop a rendered template preview to its non-white content bounds."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageChops


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pad", type=int, default=48)
    args = parser.parse_args()

    image = Image.open(args.input).convert("RGBA")
    white = Image.new("RGBA", image.size, (255, 255, 255, 255))
    diff = ImageChops.difference(image, white).convert("L")
    bbox = diff.point(lambda p: 255 if p > 8 else 0).getbbox()
    if bbox is None:
        raise SystemExit("No non-white content found")

    left = max(0, bbox[0] - args.pad)
    top = max(0, bbox[1] - args.pad)
    right = min(image.width, bbox[2] + args.pad)
    bottom = min(image.height, bbox[3] + args.pad)
    cropped = image.crop((left, top, right, bottom))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
