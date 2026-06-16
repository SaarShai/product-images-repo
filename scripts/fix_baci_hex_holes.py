#!/usr/bin/env python3
"""Correct Baci door hex holes from the authoritative SVG polygons.

The image model can place convincing-looking hex holes a little off-template.
This script removes the bitmap hole marks near the SVG targets, inpaints the
local panel texture, then redraws exactly the SVG polygon holes.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from export_svg_template_fit import read_template, transform_points


ROOT = Path(__file__).resolve().parents[1]


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def draw_polygon_mask(size: tuple[int, int], points: list[tuple[int, int]]) -> np.ndarray:
    mask = np.zeros((size[1], size[0]), dtype=np.uint8)
    cv2.fillPoly(mask, [np.asarray(points, dtype=np.int32)], 255)
    return mask


def draw_panel_mask(size: tuple[int, int], polygons: list[list[tuple[int, int]]]) -> np.ndarray:
    mask = np.zeros((size[1], size[0]), dtype=np.uint8)
    for points in polygons:
        cv2.fillPoly(mask, [np.asarray(points, dtype=np.int32)], 255)
    return mask


def erase_existing_hole_marks(image: Image.Image, svg_path: Path, pad: int, dilate: int, inpaint_radius: int) -> Image.Image:
    geometry = read_template(svg_path)
    width, height = image.size
    rgb = np.asarray(image.convert("RGB"))

    panel_points = [transform_points(path, geometry.viewbox, width, height, 1) for path in geometry.paths]
    panel_mask = draw_panel_mask((width, height), panel_points)

    erase_mask = np.zeros((height, width), dtype=np.uint8)
    for polygon in geometry.polygons:
        points = transform_points(polygon, geometry.viewbox, width, height, 1)
        xs = [x for x, _ in points]
        ys = [y for _, y in points]
        x0, x1 = max(0, min(xs) - pad), min(width, max(xs) + pad)
        y0, y1 = max(0, min(ys) - pad), min(height, max(ys) + pad)

        local = rgb[y0:y1, x0:x1]
        local_panel = panel_mask[y0:y1, x0:x1] > 0
        bright = (local[:, :, 0] > 220) & (local[:, :, 1] > 220) & (local[:, :, 2] > 220)
        seed = bright & local_panel
        local_mask = np.zeros((y1 - y0, x1 - x0), dtype=np.uint8)
        local_mask[seed] = 255

        if dilate > 0:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate * 2 + 1, dilate * 2 + 1))
            local_mask = cv2.dilate(local_mask, kernel, iterations=1)
            local_mask = np.where(local_panel, local_mask, 0).astype(np.uint8)

        erase_mask[y0:y1, x0:x1] = np.maximum(erase_mask[y0:y1, x0:x1], local_mask)

    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    corrected = cv2.inpaint(bgr, erase_mask, inpaintRadius=inpaint_radius, flags=cv2.INPAINT_TELEA)
    corrected_rgb = cv2.cvtColor(corrected, cv2.COLOR_BGR2RGB)
    return Image.fromarray(corrected_rgb)


def draw_svg_hexes(image: Image.Image, svg_path: Path, stroke_units: float) -> Image.Image:
    geometry = read_template(svg_path)
    width, height = image.size
    scale = ((width / geometry.viewbox[2]) + (height / geometry.viewbox[3])) / 2.0
    stroke = max(1, round(stroke_units * scale))

    aa = 4
    canvas = image.convert("RGB").resize((width * aa, height * aa), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(canvas)
    for polygon in geometry.polygons:
        points = transform_points(polygon, geometry.viewbox, width, height, aa)
        draw.polygon(points, fill=(255, 255, 255))
        draw.line(points + points[:1], fill=(0, 0, 0), width=stroke * aa)
    return canvas.resize((width, height), Image.Resampling.LANCZOS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--template-svg", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--debug-mask", type=Path)
    parser.add_argument("--pad", type=int, default=38)
    parser.add_argument("--dilate", type=int, default=12)
    parser.add_argument("--inpaint-radius", type=int, default=5)
    parser.add_argument("--stroke-width-units", type=float, default=2.0)
    args = parser.parse_args()

    image_path = resolve(args.image)
    svg_path = resolve(args.template_svg)
    out_path = resolve(args.out)

    source = Image.open(image_path).convert("RGB")
    erased = erase_existing_hole_marks(source, svg_path, args.pad, args.dilate, args.inpaint_radius)
    corrected = draw_svg_hexes(erased, svg_path, args.stroke_width_units)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    corrected.save(out_path)
    print(out_path.relative_to(ROOT) if out_path.is_relative_to(ROOT) else out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
