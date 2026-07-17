#!/usr/bin/env python3
"""Deterministic shape checks for the Water Cube candidate and print master."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageStat


def inspect(path: Path, minimum_width: int) -> tuple[int, int]:
    if not path.is_file():
        raise SystemExit(f"FAIL missing: {path}")
    with Image.open(path) as image:
        width, height = image.size
        if image.format != "PNG":
            raise SystemExit(f"FAIL format {image.format}: {path}")
        if image.mode not in {"RGB", "RGBA"}:
            raise SystemExit(f"FAIL mode {image.mode}: {path}")
        ratio = width / height
        if abs(ratio - 1.5) > 0.02:
            raise SystemExit(f"FAIL ratio {ratio:.4f}: {path}")
        if width < minimum_width:
            raise SystemExit(f"FAIL width {width} < {minimum_width}: {path}")
        if min(ImageStat.Stat(image.convert("RGB")).var) < 80:
            raise SystemExit(f"FAIL near-flat channel variance: {path}")
    print(f"PASS {path} PNG {width}x{height} ratio={ratio:.4f}")
    return width, height


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--final", type=Path, required=True)
    args = parser.parse_args()
    candidate_size = inspect(args.candidate, 1400)
    final_size = inspect(args.final, 6000)
    if final_size != (candidate_size[0] * 4, candidate_size[1] * 4):
        raise SystemExit(
            f"FAIL final size {final_size} is not exactly 4x candidate {candidate_size}"
        )
    print("PASS final_is_exact_4x_candidate")


if __name__ == "__main__":
    main()
