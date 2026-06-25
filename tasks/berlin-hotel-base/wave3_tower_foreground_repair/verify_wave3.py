#!/usr/bin/env python3
"""Verify wave3 tower/foreground repair candidates against the banked baseline."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parent
BASELINE = (ROOT / "../wave2/BANKED_CURRENT_BEST/berlin_hotel_base_current_best.png").resolve()

# Broad far-left context that contains the user-circled TV tower / foreground defects.
ALLOWED_BOX = (0, 900, 860, 3050)

# The previously banked hotel-base integration must not move during this pass.
HOTEL_BASE_BOX = (3162, 2582, 4082, 2845)


def diff_bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def outside_box_mask(shape: tuple[int, int], box: tuple[int, int, int, int]) -> np.ndarray:
    height, width = shape
    mask = np.ones((height, width), dtype=bool)
    x0, y0, x1, y1 = box
    mask[y0:y1, x0:x1] = False
    return mask


def box_mask(shape: tuple[int, int], box: tuple[int, int, int, int]) -> np.ndarray:
    height, width = shape
    mask = np.zeros((height, width), dtype=bool)
    x0, y0, x1, y1 = box
    mask[y0:y1, x0:x1] = True
    return mask


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--baseline", default=BASELINE, type=Path)
    parser.add_argument("--allowed-box", default=",".join(map(str, ALLOWED_BOX)))
    parser.add_argument("--hotel-base-box", default=",".join(map(str, HOTEL_BASE_BOX)))
    args = parser.parse_args()

    allowed_box = tuple(map(int, str(args.allowed_box).split(",")))
    hotel_base_box = tuple(map(int, str(args.hotel_base_box).split(",")))

    base = Image.open(args.baseline).convert("RGB")
    cand = Image.open(args.candidate).convert("RGB")
    if base.size != cand.size:
        print(f"FAIL size_mismatch baseline={base.size} candidate={cand.size}")
        return 2

    base_arr = np.asarray(base, dtype=np.int16)
    cand_arr = np.asarray(cand, dtype=np.int16)
    delta = np.abs(cand_arr - base_arr)
    changed = np.any(delta > 0, axis=2)
    bbox = diff_bbox(changed)

    outside_allowed = changed & outside_box_mask(changed.shape, allowed_box)
    hotel_region = changed & box_mask(changed.shape, hotel_base_box)
    max_delta = int(delta.max()) if delta.size else 0
    inside_changed = int(np.count_nonzero(changed & ~outside_box_mask(changed.shape, allowed_box)))
    outside_changed = int(np.count_nonzero(outside_allowed))
    hotel_changed = int(np.count_nonzero(hotel_region))

    status = "PASS" if outside_changed == 0 and hotel_changed == 0 and bbox is not None else "FAIL"
    print(
        f"{status} candidate={args.candidate} "
        f"bbox={bbox} max_delta={max_delta} "
        f"inside_allowed_changed={inside_changed} "
        f"outside_allowed_changed={outside_changed} "
        f"hotel_base_changed={hotel_changed} "
        f"allowed_box={allowed_box} hotel_base_box={hotel_base_box}"
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
