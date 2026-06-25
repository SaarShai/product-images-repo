#!/usr/bin/env python3
"""Verify a Berlin hotel-base candidate is byte-stable outside an edit box."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def parse_box(raw: str) -> tuple[int, int, int, int]:
    parts = [int(p) for p in raw.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("box must be x0,y0,x1,y1")
    x0, y0, x1, y1 = parts
    if x0 >= x1 or y0 >= y1:
        raise argparse.ArgumentTypeError("box must satisfy x0<x1 and y0<y1")
    return x0, y0, x1, y1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default="tasks/berlin-hotel-base/work/src.png")
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--box", type=parse_box, default=parse_box("3162,2582,4082,2845"))
    args = parser.parse_args()

    src_path = Path(args.src)
    cand_path = Path(args.candidate)
    src = np.asarray(Image.open(src_path).convert("RGB"))
    cand = np.asarray(Image.open(cand_path).convert("RGB"))

    if src.shape != cand.shape:
        print(f"FAIL shape src={src.shape} candidate={cand.shape}")
        return 2

    x0, y0, x1, y1 = args.box
    diff = np.abs(cand.astype(np.int16) - src.astype(np.int16))
    outside = diff.copy()
    outside[y0:y1, x0:x1, :] = 0
    outside_max = int(outside.max())
    outside_nonzero = int(np.count_nonzero(outside))
    inside_nonzero = int(np.count_nonzero(diff[y0:y1, x0:x1, :]))

    status = "PASS" if outside_max == 0 and outside_nonzero == 0 and inside_nonzero > 0 else "FAIL"
    print(
        f"{status} candidate={cand_path} box={x0},{y0},{x1},{y1} "
        f"outside_max={outside_max} outside_nonzero={outside_nonzero} "
        f"inside_nonzero={inside_nonzero}"
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

