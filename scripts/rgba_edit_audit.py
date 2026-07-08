#!/usr/bin/env python3
"""Audit local edits to finished RGBA artwork.

Checks that a candidate keeps the source alpha channel identical, reports RGB
changes inside named target boxes, optionally gates all RGB changes to allowed
boxes, and writes an original/candidate/diff review sheet.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw


def parse_box(value: str) -> tuple[str, tuple[int, int, int, int]]:
    if ":" not in value:
        raise argparse.ArgumentTypeError("box must be name:x0,y0,x1,y1")
    name, raw_box = value.split(":", 1)
    parts = raw_box.split(",")
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("box must be name:x0,y0,x1,y1")
    try:
        box = tuple(int(v) for v in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("box coordinates must be integers") from exc
    x0, y0, x1, y1 = box
    if not name or x1 <= x0 or y1 <= y0:
        raise argparse.ArgumentTypeError("box needs a name and positive area")
    return name, box


def load_rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def alpha_counts(image: Image.Image) -> str:
    values, counts = np.unique(np.asarray(image.getchannel("A")), return_counts=True)
    return ",".join(f"{int(v)}:{int(c)}" for v, c in zip(values, counts))


def changed_pixels(a: Image.Image, b: Image.Image, threshold: int) -> tuple[int, tuple[int, int, int, int] | None]:
    diff = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
    arr = np.asarray(diff)
    changed = np.any(arr > threshold, axis=2)
    return int(changed.sum()), diff.getbbox()


def union_mask(size: tuple[int, int], boxes: list[tuple[str, tuple[int, int, int, int]]]) -> np.ndarray:
    mask = np.zeros((size[1], size[0]), dtype=bool)
    for _, (x0, y0, x1, y1) in boxes:
        mask[y0:y1, x0:x1] = True
    return mask


def flatten_on_white(image: Image.Image) -> Image.Image:
    bg = Image.new("RGBA", image.size, (255, 255, 255, 255))
    return Image.alpha_composite(bg, image).convert("RGB")


def make_review(
    source: Image.Image,
    candidate: Image.Image,
    targets: list[tuple[str, tuple[int, int, int, int]]],
    review_path: Path,
    diff_scale: int,
    max_panel_width: int,
) -> None:
    rows = []
    for name, box in targets:
        panels = []
        for label, img in (("source", source), ("candidate", candidate)):
            crop = flatten_on_white(img.crop(box))
            scale = min(4.0, max_panel_width / crop.width)
            crop = crop.resize(
                (round(crop.width * scale), round(crop.height * scale)),
                Image.Resampling.LANCZOS,
            )
            panels.append((label, crop))

        diff = ImageChops.difference(source.crop(box).convert("RGB"), candidate.crop(box).convert("RGB"))
        diff = diff.point(lambda p: min(255, p * diff_scale))
        scale = min(4.0, max_panel_width / diff.width)
        diff = diff.resize(
            (round(diff.width * scale), round(diff.height * scale)),
            Image.Resampling.LANCZOS,
        )
        panels.append((f"diff_x{diff_scale}", diff))

        width = sum(panel.width for _, panel in panels) + 18 * (len(panels) + 1)
        height = max(panel.height for _, panel in panels) + 46
        row = Image.new("RGB", (width, height), (242, 242, 242))
        draw = ImageDraw.Draw(row)
        x = 10
        for label, panel in panels:
            draw.text((x, 8), f"{name} {label}", fill=(0, 0, 0))
            row.paste(panel, (x, 32))
            x += panel.width + 18
        rows.append(row)

    sheet = Image.new(
        "RGB",
        (max(row.width for row in rows), sum(row.height + 12 for row in rows) + 8),
        (228, 228, 228),
    )
    y = 8
    for row in rows:
        sheet.paste(row, (0, y))
        y += row.height + 12
    review_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(review_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--target", action="append", type=parse_box, required=True, help="name:x0,y0,x1,y1")
    parser.add_argument("--allowed-box", action="append", type=parse_box, default=[], help="name:x0,y0,x1,y1")
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--diff-threshold", type=int, default=0)
    parser.add_argument("--diff-scale", type=int, default=6)
    parser.add_argument("--max-panel-width", type=int, default=650)
    parser.add_argument("--require-target-change", action="store_true")
    parser.add_argument("--max-outside-changed", type=int, default=None)
    args = parser.parse_args()

    source = load_rgba(args.source)
    candidate = load_rgba(args.candidate)
    if source.size != candidate.size:
        print(f"FAIL size mismatch source={source.size} candidate={candidate.size}")
        return 2

    print(f"source={args.source}")
    print(f"candidate={args.candidate}")
    print(f"size_mode={candidate.size} {candidate.mode}")

    alpha_diff = ImageChops.difference(source.getchannel("A"), candidate.getchannel("A"))
    alpha_bbox = alpha_diff.getbbox()
    print(f"alpha_diff_extrema={alpha_diff.getextrema()} alpha_diff_bbox={alpha_bbox}")
    print(f"alpha_counts_source={alpha_counts(source)}")
    print(f"alpha_counts_candidate={alpha_counts(candidate)}")

    failed = alpha_bbox is not None
    for name, box in args.target:
        count, bbox = changed_pixels(source.crop(box), candidate.crop(box), args.diff_threshold)
        print(f"target={name} changed_pixels={count} diff_bbox={bbox}")
        if args.require_target_change and count == 0:
            failed = True

    allowed_boxes = args.allowed_box or args.target
    if args.max_outside_changed is not None:
        source_arr = np.asarray(source.convert("RGB"))
        candidate_arr = np.asarray(candidate.convert("RGB"))
        changed = np.any(np.abs(source_arr.astype(np.int16) - candidate_arr.astype(np.int16)) > args.diff_threshold, axis=2)
        outside = np.logical_and(changed, ~union_mask(source.size, allowed_boxes))
        outside_count = int(outside.sum())
        print(f"outside_allowed_changed_pixels={outside_count} max_allowed={args.max_outside_changed}")
        if outside_count > args.max_outside_changed:
            failed = True

    make_review(source, candidate, args.target, args.review, args.diff_scale, args.max_panel_width)
    print(f"review={args.review}")
    print(f"verdict={'FAIL' if failed else 'PASS'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
