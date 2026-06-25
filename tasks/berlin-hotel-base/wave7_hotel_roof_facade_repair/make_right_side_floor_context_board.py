#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageChops

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
RESULTS = ROOT / "results"
BASE = Path("tasks/berlin-hotel-base/wave6_bridge_stairs_openai_donor/results/stair_architecture_under_foliage_masked.png")

FULL_SIZE = (4192, 3848)
CROP_BOX = (3370, 960, 3945, 1780)
FLOOR_GUARD = (3425, 1320, 3920, 1780)
STAIR_PROTECTED = (1720, 2200, 2600, 2940)


def load_full(path: Path) -> Image.Image:
    im = Image.open(path).convert("RGB")
    if im.size != FULL_SIZE:
        im = im.resize(FULL_SIZE, Image.Resampling.LANCZOS)
    return im


def make_diff(base_crop: Image.Image, candidate_crop: Image.Image, out_path: Path) -> None:
    diff = ImageChops.difference(base_crop, candidate_crop).convert("L")
    arr = np.asarray(diff)
    heat = np.zeros((arr.shape[0], arr.shape[1], 3), dtype=np.uint8)
    heat[..., 0] = np.clip(arr * 5, 0, 255)
    heat[..., 1] = np.clip(arr * 2, 0, 120)
    Image.blend(base_crop, Image.fromarray(heat), 0.46).save(out_path)


def board(items: list[tuple[str, Path]], out_path: Path) -> None:
    tile_w, tile_h = 610, 900
    cols = 2
    rows = (len(items) + 1) // cols
    out = Image.new("RGB", (cols * tile_w + 30, rows * tile_h + 20), "white")
    draw = ImageDraw.Draw(out)
    for i, (label, path) in enumerate(items):
        im = load_full(path)
        crop = im.crop(CROP_BOX).resize((575, 820), Image.Resampling.LANCZOS)
        x = 10 + (i % cols) * tile_w
        y = 10 + (i // cols) * tile_h
        draw.text((x, y), label, fill=(140, 0, 0))
        out.paste(crop, (x, y + 30))
    out.save(out_path)


def verify(items: list[tuple[str, Path]]) -> None:
    base = np.asarray(load_full(BASE))
    fx0, fy0, fx1, fy1 = FLOOR_GUARD
    floor = np.zeros(base.shape[:2], dtype=bool)
    floor[fy0:fy1, fx0:fx1] = True
    sx0, sy0, sx1, sy1 = STAIR_PROTECTED
    stair = np.zeros(base.shape[:2], dtype=bool)
    stair[sy0:sy1, sx0:sx1] = True
    lines = []
    base_crop = load_full(BASE).crop(CROP_BOX)
    for label, path in items:
        if label.startswith("base"):
            continue
        im = np.asarray(load_full(path))
        diff = np.abs(im.astype(int) - base.astype(int)).max(axis=2) > 2
        lines.append(
            f"{label}\tfloor_guard_changed_vs_pre_roof={int((diff & floor).sum())}"
            f"\tstair_protected_changed_vs_pre_roof={int((diff & stair).sum())}"
            f"\tpath={path.resolve()}"
        )
        safe_label = "".join(c if c.isalnum() else "_" for c in label.lower()).strip("_")
        make_diff(base_crop, load_full(path).crop(CROP_BOX), RESULTS / f"{safe_label}_large_context_diff_overlay.png")
    (RESULTS / "hotel_roof_facade_right_side_floor_context_verification.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    items = [
        ("base floors to preserve", BASE),
        ("raw precise donor reference only", RAW / "reference_guided_top_precise_raw.png"),
        ("v10 selected before fade fix", RESULTS / "v10_precise_roof_cap_ledge_facade_restored.png"),
        ("v11 larger donor patch", RESULTS / "v11_right_parapet_precise_reinforced.png"),
        ("v15 small donor patch", RESULTS / "v15_right_rear_face_small_precise.png"),
        ("v16 tiny donor patch", RESULTS / "v16_right_rear_face_tiny_precise.png"),
        ("v18 tiny plus edge", RESULTS / "v18_right_face_tiny_plus_edge.png"),
    ]
    board(items, RESULTS / "hotel_roof_facade_right_side_floor_context_board.png")
    verify(items)


if __name__ == "__main__":
    main()
