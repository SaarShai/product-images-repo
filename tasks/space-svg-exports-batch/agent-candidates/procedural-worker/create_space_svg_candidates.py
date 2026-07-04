#!/usr/bin/env python3
"""Procedural checkpoint candidates for the space SVG export batch.

This intentionally stays local to this worker folder. It treats the SVG as the
geometry source of truth, designs simple watercolor control-panel modules inside
the paintable mask, then uses the exact SVG-derived mask only as the final
export guardrail.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


WORKER = Path(__file__).resolve().parent
REPO = WORKER.parents[3]
SOURCE_DIR = Path(
    "<DRIVE_ROOT>/"
    "Wanderland Folder/Files/Products/Screenery/production files/space/svg-exports"
)

COMMAND_RE = re.compile(r"[MmLlHhVvCcSsZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")

Point = tuple[float, float]
IPoint = tuple[int, int]
Box = tuple[int, int, int, int]
Color = tuple[int, int, int, int]

NAVY: Color = (12, 61, 139, 225)
NAVY_DARK: Color = (7, 39, 103, 218)
RIM_BLUE: Color = (42, 105, 188, 190)
PANEL_BLUE: Color = (111, 169, 222, 232)
PALE_BLUE: Color = (196, 225, 243, 225)
GLASS_TEAL: Color = (133, 219, 213, 218)
CORAL: Color = (244, 105, 96, 238)
YELLOW: Color = (247, 198, 72, 238)
TEAL: Color = (91, 205, 181, 238)
WHITE: Color = (255, 255, 255, 255)


@dataclass
class SvgGeometry:
    svg_path: Path
    viewbox: tuple[float, float, float, float]
    paths: list[list[Point]]
    output_size: tuple[int, int]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_command(token: str) -> bool:
    return len(token) == 1 and token.isalpha()


def read_number(tokens: list[str], index: int) -> tuple[float, int]:
    if index >= len(tokens) or is_command(tokens[index]):
        raise ValueError("Expected numeric SVG path token")
    return float(tokens[index]), index + 1


def read_pair(tokens: list[str], index: int) -> tuple[Point, int]:
    x, index = read_number(tokens, index)
    y, index = read_number(tokens, index)
    return (x, y), index


def apply_relative(point: Point, current: Point, relative: bool) -> Point:
    if not relative:
        return point
    return (current[0] + point[0], current[1] + point[1])


def cubic_point(p0: Point, p1: Point, p2: Point, p3: Point, t: float) -> Point:
    inv = 1.0 - t
    return (
        (inv**3 * p0[0]) + (3 * inv * inv * t * p1[0]) + (3 * inv * t * t * p2[0]) + (t**3 * p3[0]),
        (inv**3 * p0[1]) + (3 * inv * inv * t * p1[1]) + (3 * inv * t * t * p2[1]) + (t**3 * p3[1]),
    )


def parse_path_d(data: str, curve_steps: int = 34) -> list[list[Point]]:
    tokens = COMMAND_RE.findall(data.replace(",", " "))
    index = 0
    command: str | None = None
    current: Point = (0.0, 0.0)
    start: Point = (0.0, 0.0)
    last_cubic_control: Point | None = None
    current_poly: list[Point] = []
    subpaths: list[list[Point]] = []

    def finish_poly() -> None:
        nonlocal current_poly
        if len(current_poly) >= 3:
            subpaths.append(current_poly)
        current_poly = []

    while index < len(tokens):
        if is_command(tokens[index]):
            command = tokens[index]
            index += 1
        if command is None:
            raise ValueError(f"SVG path starts without a command: {data[:40]}")

        relative = command.islower()
        upper = command.upper()

        if upper == "M":
            point, index = read_pair(tokens, index)
            current = apply_relative(point, current, relative)
            finish_poly()
            current_poly = [current]
            start = current
            last_cubic_control = None
            command = "l" if relative else "L"
            while index < len(tokens) and not is_command(tokens[index]):
                point, index = read_pair(tokens, index)
                current = apply_relative(point, current, relative)
                current_poly.append(current)
        elif upper == "L":
            while index < len(tokens) and not is_command(tokens[index]):
                point, index = read_pair(tokens, index)
                current = apply_relative(point, current, relative)
                current_poly.append(current)
            last_cubic_control = None
        elif upper == "H":
            while index < len(tokens) and not is_command(tokens[index]):
                x, index = read_number(tokens, index)
                current = (current[0] + x, current[1]) if relative else (x, current[1])
                current_poly.append(current)
            last_cubic_control = None
        elif upper == "V":
            while index < len(tokens) and not is_command(tokens[index]):
                y, index = read_number(tokens, index)
                current = (current[0], current[1] + y) if relative else (current[0], y)
                current_poly.append(current)
            last_cubic_control = None
        elif upper == "C":
            while index < len(tokens) and not is_command(tokens[index]):
                control_1, index = read_pair(tokens, index)
                control_2, index = read_pair(tokens, index)
                end, index = read_pair(tokens, index)
                p0 = current
                p1 = apply_relative(control_1, current, relative)
                p2 = apply_relative(control_2, current, relative)
                p3 = apply_relative(end, current, relative)
                for step in range(1, curve_steps + 1):
                    current_poly.append(cubic_point(p0, p1, p2, p3, step / curve_steps))
                current = p3
                last_cubic_control = p2
        elif upper == "S":
            while index < len(tokens) and not is_command(tokens[index]):
                control_2, index = read_pair(tokens, index)
                end, index = read_pair(tokens, index)
                p0 = current
                if last_cubic_control is None:
                    p1 = current
                else:
                    p1 = ((2 * current[0]) - last_cubic_control[0], (2 * current[1]) - last_cubic_control[1])
                p2 = apply_relative(control_2, current, relative)
                p3 = apply_relative(end, current, relative)
                for step in range(1, curve_steps + 1):
                    current_poly.append(cubic_point(p0, p1, p2, p3, step / curve_steps))
                current = p3
                last_cubic_control = p2
        elif upper == "Z":
            if current_poly and current_poly[-1] != start:
                current_poly.append(start)
            current = start
            finish_poly()
            command = None
            last_cubic_control = None
        else:
            raise ValueError(f"Unsupported SVG path command {command!r}")

    finish_poly()
    return subpaths


def read_svg(svg_path: Path) -> SvgGeometry:
    tree = ET.parse(svg_path)
    root = tree.getroot()
    viewbox_text = root.attrib.get("viewBox")
    if not viewbox_text:
        raise ValueError(f"Missing viewBox in {svg_path}")
    viewbox_parts = [float(item) for item in viewbox_text.replace(",", " ").split()]
    if len(viewbox_parts) != 4:
        raise ValueError(f"Unexpected viewBox in {svg_path}: {viewbox_text}")
    paths: list[list[Point]] = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] == "path" and element.attrib.get("d"):
            paths.extend(parse_path_d(element.attrib["d"]))
    if len(paths) < 2:
        raise ValueError(f"Expected an outer path plus cutout path(s) in {svg_path}")
    viewbox = tuple(viewbox_parts)  # type: ignore[assignment]
    output_size = (round(viewbox[2]), round(viewbox[3]))
    return SvgGeometry(svg_path=svg_path, viewbox=viewbox, paths=paths, output_size=output_size)


def transform_points(points: list[Point], geometry: SvgGeometry, aa: int = 1) -> list[IPoint]:
    min_x, min_y, box_w, box_h = geometry.viewbox
    width, height = geometry.output_size
    scale_x = width / box_w
    scale_y = height / box_h
    return [
        (
            round((x - min_x) * scale_x * aa),
            round((y - min_y) * scale_y * aa),
        )
        for x, y in points
    ]


def path_mask(geometry: SvgGeometry, path_indexes: list[int], aa: int = 4) -> Image.Image:
    width, height = geometry.output_size
    mask_hr = Image.new("L", (width * aa, height * aa), 0)
    draw = ImageDraw.Draw(mask_hr)
    for index in path_indexes:
        draw.polygon(transform_points(geometry.paths[index], geometry, aa), fill=255)
    return mask_hr.resize((width, height), Image.Resampling.LANCZOS)


def hard(mask: Image.Image) -> Image.Image:
    return mask.point(lambda p: 255 if p > 0 else 0)


def build_masks(geometry: SvgGeometry, cutout_margin: int = 14, motif_margin: int = 34) -> tuple[Image.Image, Image.Image, Image.Image, Image.Image]:
    outer = hard(path_mask(geometry, [0]))
    cutouts = Image.new("L", geometry.output_size, 0)
    if len(geometry.paths) > 1:
        cutouts = hard(path_mask(geometry, list(range(1, len(geometry.paths)))))
        cutouts = cutouts.filter(ImageFilter.MaxFilter((cutout_margin * 2) + 1))
    paintable = ImageChops.subtract(outer, cutouts)
    safe = paintable.filter(ImageFilter.MinFilter((motif_margin * 2) + 1))
    return outer, cutouts, paintable, safe


def mask_bbox(mask: Image.Image) -> Box | None:
    arr = np.asarray(mask) > 0
    ys, xs = np.where(arr)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def outside_pixels(mask: Image.Image, allowed: Image.Image) -> int:
    arr = np.asarray(mask) > 0
    allowed_arr = np.asarray(allowed) > 0
    return int((arr & ~allowed_arr).sum())


def nonwhite_mask(image: Image.Image, threshold: int = 24) -> np.ndarray:
    rgb = np.asarray(image.convert("RGB")).astype(np.int16)
    return ((255 - rgb[:, :, 0]) + (255 - rgb[:, :, 1]) + (255 - rgb[:, :, 2])) > threshold


def clipped(layer: Image.Image, mask: Image.Image) -> Image.Image:
    return Image.composite(layer, Image.new("RGBA", layer.size, (0, 0, 0, 0)), mask)


def shifted(mask: Image.Image, dx: int, dy: int) -> Image.Image:
    return mask.transform(mask.size, Image.Transform.AFFINE, (1, 0, -dx, 0, 1, -dy))


def color_shift(color: Color, rng: random.Random, amount: int = 16, alpha_delta: int = 0) -> Color:
    return (
        max(0, min(255, color[0] + rng.randint(-amount, amount))),
        max(0, min(255, color[1] + rng.randint(-amount, amount))),
        max(0, min(255, color[2] + rng.randint(-amount, amount))),
        max(0, min(255, color[3] + alpha_delta + rng.randint(-8, 8))),
    )


def watercolor_fill(size: tuple[int, int], mask: Image.Image, color: Color, rng: random.Random, blotches: int = 50) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    layer.alpha_composite(clipped(Image.new("RGBA", size, color), mask.filter(ImageFilter.GaussianBlur(1.0))))
    wash = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(wash, "RGBA")
    width, height = size
    for _ in range(blotches):
        cx = rng.randint(-80, width + 80)
        cy = rng.randint(-80, height + 80)
        rx = rng.randint(max(24, width // 30), max(72, width // 8))
        ry = rng.randint(max(18, height // 40), max(62, height // 7))
        fill = rng.choice(
            [
                color_shift(color, rng, 13, -120),
                (255, 255, 255, rng.randint(14, 42)),
                (43, 111, 193, rng.randint(10, 30)),
                (174, 219, 242, rng.randint(14, 34)),
            ]
        )
        draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=fill)
    wash = wash.filter(ImageFilter.GaussianBlur(14))
    layer.alpha_composite(clipped(wash, mask))
    return layer


def panel_wash(size: tuple[int, int], paintable: Image.Image, rng: random.Random) -> Image.Image:
    width, height = size
    gen = np.random.default_rng(rng.randint(0, 2**32 - 1))
    base = np.zeros((height, width, 3), dtype=np.float32)
    base[:, :, :] = np.array([105, 163, 218], dtype=np.float32)
    low_noise = gen.normal(0, 13, (height, width, 1))
    grain = gen.normal(0, 3.5, (height, width, 1))
    base += low_noise * np.array([0.35, 0.55, 0.95]) + grain
    image = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA").filter(ImageFilter.GaussianBlur(0.8))
    image.alpha_composite(watercolor_fill(size, paintable, (126, 184, 226, 150), rng, blotches=120))

    sheen = Image.new("RGBA", size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sheen, "RGBA")
    for y in [int(height * 0.25), int(height * 0.57), int(height * 0.84)]:
        sd.rounded_rectangle((int(width * 0.07), y, int(width * 0.93), y + 22), radius=13, fill=(255, 255, 255, 42))
    image.alpha_composite(clipped(sheen.filter(ImageFilter.GaussianBlur(8)), paintable))
    return clipped(image, paintable)


def rounded_mask(size: tuple[int, int], box: Box, radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(box, radius=radius, fill=255)
    return mask


def ellipse_mask(size: tuple[int, int], box: Box) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).ellipse(box, fill=255)
    return mask


def line_mask(size: tuple[int, int], points: list[IPoint], width: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).line(points, fill=255, width=width, joint="curve")
    for x, y in points:
        r = max(2, width // 2)
        ImageDraw.Draw(mask).ellipse((x - r, y - r, x + r, y + r), fill=255)
    return mask


def painted_outline(size: tuple[int, int], shape: str, box: Box, rng: random.Random, radius: int = 0, width: int = 8) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    for offset, alpha in [(-2, 70), (1, 122), (3, 72)]:
        shifted_box = (box[0] + offset, box[1] + rng.randint(-1, 2), box[2] + offset, box[3] + rng.randint(-2, 1))
        color = (NAVY[0], NAVY[1], NAVY[2], alpha)
        if shape == "ellipse":
            draw.ellipse(shifted_box, outline=color, width=width)
        else:
            draw.rounded_rectangle(shifted_box, radius=radius, outline=color, width=width)
    return layer.filter(ImageFilter.GaussianBlur(0.35))


def shape_component(size: tuple[int, int], mask: Image.Image, box: Box, color: Color, rng: random.Random, shape: str, radius: int = 0) -> tuple[Image.Image, Image.Image]:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    layer.alpha_composite(clipped(Image.new("RGBA", size, (4, 29, 84, 58)), shifted(mask, 8, 10).filter(ImageFilter.GaussianBlur(4))))
    layer.alpha_composite(watercolor_fill(size, mask, color, rng, blotches=26))
    layer.alpha_composite(painted_outline(size, shape, box, rng, radius=radius, width=7))
    highlight = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(highlight, "RGBA")
    x0, y0, x1, y1 = box
    if shape == "ellipse":
        draw.ellipse((x0 + 28, y0 + 26, min(x1 - 30, x0 + 112), min(y1 - 28, y0 + 94)), fill=(255, 255, 255, 82))
        draw.arc((x0 + 20, y0 + 18, x1 - 24, y1 - 26), 205, 305, fill=(255, 255, 255, 80), width=8)
    else:
        draw.rounded_rectangle((x0 + 18, y0 + 12, x1 - 22, min(y1 - 12, y0 + 34)), radius=12, fill=(255, 255, 255, 86))
        draw.rounded_rectangle((x0 + 20, y1 - 24, x1 - 28, y1 - 14), radius=7, fill=(255, 255, 255, 34))
    layer.alpha_composite(clipped(highlight.filter(ImageFilter.GaussianBlur(0.9)), mask))
    return layer, mask


def candidate_mask_inside(mask: Image.Image, allowed: Image.Image) -> bool:
    return outside_pixels(mask, allowed) == 0


def commit(
    art: Image.Image,
    element_mask: Image.Image,
    layer: Image.Image,
    mask: Image.Image,
    allowed: Image.Image,
    name: str,
    placements: list[dict[str, object]],
) -> Image.Image:
    outside = outside_pixels(mask, allowed)
    if outside:
        placements.append({"name": name, "status": "skipped", "outside_safe_pocket_pixels": outside})
        return element_mask
    placements.append({"name": name, "status": "drawn", "outside_safe_pocket_pixels": outside})
    art.alpha_composite(layer)
    return ImageChops.lighter(element_mask, mask)


def add_rect_module(
    art: Image.Image,
    element_mask: Image.Image,
    safe: Image.Image,
    placements: list[dict[str, object]],
    name: str,
    box: Box,
    color: Color,
    rng: random.Random,
    radius: int = 32,
) -> Image.Image:
    mask = rounded_mask(art.size, box, radius)
    layer, mask = shape_component(art.size, mask, box, color, rng, "rect", radius=radius)
    return commit(art, element_mask, layer, mask, safe, name, placements)


def add_dial(
    art: Image.Image,
    element_mask: Image.Image,
    safe: Image.Image,
    placements: list[dict[str, object]],
    name: str,
    box: Box,
    rng: random.Random,
) -> Image.Image:
    mask = ellipse_mask(art.size, box)
    layer, mask = shape_component(art.size, mask, box, PALE_BLUE, rng, "ellipse")
    draw = ImageDraw.Draw(layer, "RGBA")
    mask_draw = ImageDraw.Draw(mask)
    cx = (box[0] + box[2]) // 2
    cy = (box[1] + box[3]) // 2
    radius = min(box[2] - box[0], box[3] - box[1]) // 2
    for angle in range(205, 336, 26):
        rad = math.radians(angle)
        x0 = cx + int(math.cos(rad) * radius * 0.58)
        y0 = cy + int(math.sin(rad) * radius * 0.58)
        x1 = cx + int(math.cos(rad) * radius * 0.82)
        y1 = cy + int(math.sin(rad) * radius * 0.82)
        draw.line((x0, y0, x1, y1), fill=(13, 65, 143, 178), width=max(5, radius // 20))
    needle = [(cx, cy), (cx + int(radius * 0.44), cy + int(radius * 0.28))]
    draw.line(needle, fill=(12, 62, 139, 210), width=max(7, radius // 14))
    mask_draw.line(needle, fill=255, width=max(8, radius // 10))
    return commit(art, element_mask, layer, mask, safe, name, placements)


def add_radar_screen(
    art: Image.Image,
    element_mask: Image.Image,
    safe: Image.Image,
    placements: list[dict[str, object]],
    name: str,
    box: Box,
    rng: random.Random,
) -> Image.Image:
    outer = rounded_mask(art.size, box, 34)
    layer, mask = shape_component(art.size, outer, box, GLASS_TEAL, rng, "rect", radius=34)
    draw = ImageDraw.Draw(layer, "RGBA")
    mask_draw = ImageDraw.Draw(mask)
    x0, y0, x1, y1 = box
    cx = x0 + int((x1 - x0) * 0.37)
    cy = y0 + int((y1 - y0) * 0.58)
    r = min(x1 - x0, y1 - y0) // 4
    for frac in [0.35, 0.55, 0.75, 0.95]:
        rr = int(r * frac)
        draw.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=(255, 255, 255, 175), width=4)
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        draw.line((cx, cy, cx + int(math.cos(rad) * r), cy + int(math.sin(rad) * r)), fill=(255, 255, 255, 160), width=4)
    for i in range(4):
        yy = y0 + 58 + i * 48
        draw.rounded_rectangle((x0 + int((x1 - x0) * 0.62), yy, x1 - 40, yy + 18), radius=8, fill=(255, 255, 255, 164))
    mask_draw.rounded_rectangle(box, radius=34, fill=255)
    return commit(art, element_mask, layer, mask, safe, name, placements)


def add_sliders(
    art: Image.Image,
    element_mask: Image.Image,
    safe: Image.Image,
    placements: list[dict[str, object]],
    name: str,
    x0: int,
    y0: int,
    length: int,
    rows: int,
    rng: random.Random,
) -> Image.Image:
    layer = Image.new("RGBA", art.size, (0, 0, 0, 0))
    mask = Image.new("L", art.size, 0)
    draw = ImageDraw.Draw(layer, "RGBA")
    mask_draw = ImageDraw.Draw(mask)
    colors = [CORAL, YELLOW, TEAL]
    for row in range(rows):
        y = y0 + row * 70
        rail = (x0, y, x0 + length, y + 18)
        mask_draw.rounded_rectangle((rail[0] - 8, rail[1] - 6, rail[2] + 8, rail[3] + 6), radius=14, fill=255)
        draw.rounded_rectangle(rail, radius=10, fill=(147, 200, 232, 168), outline=(20, 83, 151, 162), width=4)
        for k in range(2):
            knob_x = x0 + int(length * (0.18 + ((row + k * 2 + 1) % 5) * 0.15))
            knob_box = (knob_x - 25, y - 20, knob_x + 25, y + 30)
            mask_draw.rounded_rectangle(knob_box, radius=11, fill=255)
            draw.rounded_rectangle((knob_box[0] + 4, knob_box[1] + 5, knob_box[2] + 5, knob_box[3] + 7), radius=11, fill=(6, 31, 81, 54))
            draw.rounded_rectangle(knob_box, radius=11, fill=colors[(row + k) % len(colors)], outline=NAVY, width=4)
            draw.rounded_rectangle((knob_box[0] + 8, knob_box[1] + 7, knob_box[2] - 8, knob_box[1] + 17), radius=5, fill=(255, 255, 255, 82))
    mask = mask.filter(ImageFilter.MaxFilter(5))
    return commit(art, element_mask, layer, mask, safe, name, placements)


def add_button_grid(
    art: Image.Image,
    element_mask: Image.Image,
    safe: Image.Image,
    placements: list[dict[str, object]],
    name: str,
    box: Box,
    rng: random.Random,
) -> Image.Image:
    element_mask = add_rect_module(art, element_mask, safe, placements, f"{name} backing plate", box, (184, 219, 238, 226), rng, radius=28)
    layer = Image.new("RGBA", art.size, (0, 0, 0, 0))
    mask = Image.new("L", art.size, 0)
    draw = ImageDraw.Draw(layer, "RGBA")
    mask_draw = ImageDraw.Draw(mask)
    x0, y0, x1, y1 = box
    for row in range(2):
        for col in range(3):
            cx = x0 + int((col + 1) * (x1 - x0) / 4)
            cy = y0 + int((row + 1) * (y1 - y0) / 3)
            r = 24
            mask_draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
            draw.ellipse((cx - r + 5, cy - r + 7, cx + r + 5, cy + r + 7), fill=(5, 29, 84, 54))
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=PALE_BLUE, outline=NAVY, width=4)
            draw.ellipse((cx - r + 8, cy - r + 8, cx - r + 21, cy - r + 21), fill=(255, 255, 255, 118))
    return commit(art, element_mask, layer, mask, safe, f"{name} checked buttons", placements)


def add_levers(
    art: Image.Image,
    element_mask: Image.Image,
    safe: Image.Image,
    placements: list[dict[str, object]],
    name: str,
    points: list[tuple[int, int, Color]],
    rng: random.Random,
) -> Image.Image:
    layer = Image.new("RGBA", art.size, (0, 0, 0, 0))
    mask = Image.new("L", art.size, 0)
    draw = ImageDraw.Draw(layer, "RGBA")
    mask_draw = ImageDraw.Draw(mask)
    for x, y, color in points:
        base = (x - 48, y + 64, x + 48, y + 112)
        stem = (x - 22, y - 8, x + 22, y + 88)
        mask_draw.ellipse(base, fill=255)
        mask_draw.rounded_rectangle(stem, radius=19, fill=255)
        draw.ellipse((base[0] + 6, base[1] + 8, base[2] + 6, base[3] + 8), fill=(4, 29, 84, 62))
        draw.ellipse(base, fill=(42, 105, 188, 170), outline=NAVY, width=5)
        draw.rounded_rectangle(stem, radius=19, fill=color, outline=NAVY, width=5)
        draw.rounded_rectangle((stem[0] + 8, stem[1] + 9, stem[0] + 20, stem[3] - 18), radius=7, fill=(255, 255, 255, 85))
    return commit(art, element_mask, layer, mask.filter(ImageFilter.MaxFilter(3)), safe, name, placements)


def add_soft_stars(
    art: Image.Image,
    element_mask: Image.Image,
    safe: Image.Image,
    placements: list[dict[str, object]],
    rng: random.Random,
) -> Image.Image:
    layer = Image.new("RGBA", art.size, (0, 0, 0, 0))
    mask = Image.new("L", art.size, 0)
    draw = ImageDraw.Draw(layer, "RGBA")
    mask_draw = ImageDraw.Draw(mask)
    safe_arr = np.asarray(safe) > 0
    height, width = safe_arr.shape
    added = 0
    for _ in range(900):
        x = rng.randint(0, width - 1)
        y = rng.randint(0, height - 1)
        if not safe_arr[y, x]:
            continue
        r = rng.randint(2, 5)
        dot = ellipse_mask(art.size, (x - r, y - r, x + r, y + r))
        if outside_pixels(dot, safe):
            continue
        mask_draw.bitmap((0, 0), dot, fill=255)
        fill = rng.choice([(255, 255, 255, 72), (255, 218, 77, 94), (135, 239, 255, 78)])
        draw.ellipse((x - r, y - r, x + r, y + r), fill=fill)
        added += 1
        if added >= 85:
            break
    placements.append({"name": "candidate-checked soft star speckles", "outside_safe_pocket_pixels": outside_pixels(mask, safe), "count": added})
    art.alpha_composite(layer)
    return ImageChops.lighter(element_mask, mask)


def add_template_edge_language(art: Image.Image, geometry: SvgGeometry, paintable: Image.Image, rng: random.Random) -> None:
    layer = Image.new("RGBA", art.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    width, height = geometry.output_size
    stroke = max(5, round(min(width, height) / 165))
    for index, path in enumerate(geometry.paths):
        points = transform_points(path, geometry)
        if not points:
            continue
        closed = points + points[:1]
        color = NAVY_DARK if index == 0 else NAVY
        draw.line([(x + 6, y + 7) for x, y in closed], fill=(5, 30, 84, 58), width=stroke + 5, joint="curve")
        draw.line(closed, fill=color, width=stroke + 5, joint="curve")
        draw.line([(x + rng.randint(-1, 1), y + rng.randint(-1, 1)) for x, y in closed], fill=RIM_BLUE, width=max(3, stroke - 1), joint="curve")
        draw.line([(x + 10, y + 8) for x, y in closed], fill=(229, 244, 251, 72), width=max(2, stroke // 2), joint="curve")
    art.alpha_composite(clipped(layer.filter(ImageFilter.GaussianBlur(0.25)), paintable))


def build_np01_back_top(art: Image.Image, safe: Image.Image, rng: random.Random) -> tuple[Image.Image, list[dict[str, object]]]:
    element_mask = Image.new("L", art.size, 0)
    placements: list[dict[str, object]] = []
    element_mask = add_dial(art, element_mask, safe, placements, "left lower moon dial", (210, 520, 520, 830), rng)
    element_mask = add_sliders(art, element_mask, safe, placements, "left slider bank", 190, 885, 500, 4, rng)
    element_mask = add_levers(art, element_mask, safe, placements, "upper center levers", [(625, 430, CORAL), (775, 420, YELLOW), (925, 442, TEAL)], rng)
    element_mask = add_button_grid(art, element_mask, safe, placements, "right lower button grid", (1050, 975, 1355, 1225), rng)
    element_mask = add_rect_module(art, element_mask, safe, placements, "bottom color rail coral", (245, 1255, 640, 1322), CORAL, rng, radius=34)
    element_mask = add_rect_module(art, element_mask, safe, placements, "bottom color rail teal", (1040, 1300, 1420, 1367), TEAL, rng, radius=34)
    element_mask = add_soft_stars(art, element_mask, safe, placements, rng)
    return element_mask, placements


def build_np02_front_top(art: Image.Image, safe: Image.Image, rng: random.Random) -> tuple[Image.Image, list[dict[str, object]]]:
    element_mask = Image.new("L", art.size, 0)
    placements: list[dict[str, object]] = []
    element_mask = add_radar_screen(art, element_mask, safe, placements, "center teal radar screen", (655, 430, 1088, 760), rng)
    element_mask = add_dial(art, element_mask, safe, placements, "right lower dial", (1055, 700, 1365, 1010), rng)
    element_mask = add_sliders(art, element_mask, safe, placements, "left lower slider stack", 175, 820, 410, 4, rng)
    element_mask = add_levers(art, element_mask, safe, placements, "mid lower levers", [(710, 845, CORAL), (840, 850, YELLOW), (970, 848, TEAL)], rng)
    element_mask = add_rect_module(art, element_mask, safe, placements, "right bottom amber rail", (1070, 1175, 1445, 1245), YELLOW, rng, radius=34)
    element_mask = add_button_grid(art, element_mask, safe, placements, "left bottom small button grid", (185, 1145, 520, 1385), rng)
    element_mask = add_soft_stars(art, element_mask, safe, placements, rng)
    return element_mask, placements


def build_debug(artwork: Image.Image, paintable: Image.Image, cutouts: Image.Image, safe: Image.Image, element_mask: Image.Image, geometry: SvgGeometry) -> Image.Image:
    debug = artwork.convert("RGBA")
    tint = np.zeros((artwork.height, artwork.width, 4), dtype=np.uint8)
    tint[np.asarray(paintable) > 0] = (0, 160, 255, 24)
    tint[np.asarray(safe) > 0] = (0, 255, 140, 22)
    tint[np.asarray(cutouts) > 0] = (255, 0, 170, 100)
    tint[np.asarray(element_mask) > 0] = (255, 220, 0, 44)
    debug.alpha_composite(Image.fromarray(tint))
    lines = Image.new("RGBA", artwork.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(lines, "RGBA")
    for index, path in enumerate(geometry.paths):
        points = transform_points(path, geometry)
        draw.line(points + points[:1], fill=(0, 0, 0, 210) if index == 0 else (255, 0, 160, 225), width=3, joint="curve")
    debug.alpha_composite(lines)
    return debug.convert("RGB")


def build_overlay(artwork: Image.Image, geometry: SvgGeometry) -> Image.Image:
    overlay = artwork.convert("RGBA")
    lines = Image.new("RGBA", artwork.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(lines, "RGBA")
    for index, path in enumerate(geometry.paths):
        points = transform_points(path, geometry)
        draw.line(points + points[:1], fill=(0, 0, 0, 235) if index == 0 else (255, 210, 30, 235), width=4, joint="curve")
    overlay.alpha_composite(lines)
    return overlay.convert("RGB")


def compute_metrics(artwork: Image.Image, paintable: Image.Image, cutouts: Image.Image, element_mask: Image.Image, safe: Image.Image) -> dict[str, object]:
    painted = nonwhite_mask(artwork)
    allowed = np.asarray(paintable) > 0
    cutout = np.asarray(cutouts) > 0
    element = np.asarray(element_mask) > 0
    safe_arr = np.asarray(safe) > 0
    panel_area = int(allowed.sum())
    return {
        "verdict": "PASS" if int((painted & ~allowed & ~cutout).sum()) == 0 and int((painted & cutout).sum()) == 0 and int((element & ~safe_arr).sum()) == 0 else "FAIL",
        "outside_nonwhite_pixels": int((painted & ~allowed & ~cutout).sum()),
        "cutout_nonwhite_pixels": int((painted & cutout).sum()),
        "decorative_element_pixels_outside_safe_pocket": int((element & ~safe_arr).sum()),
        "painted_panel_coverage_pct": round(100.0 * int((painted & allowed).sum()) / panel_area, 2) if panel_area else 0.0,
    }


def save_candidate(svg_name: str, seed: int, builder) -> dict[str, object]:
    geometry = read_svg(SOURCE_DIR / svg_name)
    outer, cutouts, paintable, safe = build_masks(geometry)
    rng = random.Random(seed)
    art = Image.new("RGBA", geometry.output_size, WHITE)
    art.alpha_composite(panel_wash(geometry.output_size, paintable, rng))
    element_mask, placements = builder(art, safe, rng)
    add_template_edge_language(art, geometry, paintable, rng)

    white = Image.new("RGBA", geometry.output_size, WHITE)
    clipped_art = Image.composite(art, white, paintable)
    clipped_art = Image.composite(white, clipped_art, cutouts)
    artwork = clipped_art.convert("RGB")

    stem = svg_name.removesuffix(".svg")
    candidate_path = WORKER / f"{stem}-watercolor-control-panel-candidate.png"
    overlay_path = WORKER / f"{stem}-template-overlay.png"
    debug_path = WORKER / f"{stem}-mask-debug.png"
    metadata_path = WORKER / f"{stem}-metadata.json"

    artwork.save(candidate_path)
    build_overlay(artwork, geometry).save(overlay_path)
    build_debug(artwork, paintable, cutouts, safe, element_mask, geometry).save(debug_path)

    metrics = compute_metrics(artwork, paintable, cutouts, element_mask, safe)
    metadata: dict[str, object] = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": "procedural_pil_svg_native_watercolor_control_panel",
        "seed": seed,
        "source_svg": str(geometry.svg_path),
        "source_svg_sha256": sha256(geometry.svg_path),
        "svg_role_map": {
            "outer_contour": "path[0]",
            "cutouts_or_keep_clear": [f"path[{index}]" for index in range(1, len(geometry.paths))],
        },
        "output_size": f"{artwork.width}x{artwork.height}",
        "candidate_png": str(candidate_path),
        "template_overlay_png": str(overlay_path),
        "mask_debug_png": str(debug_path),
        "geometry_report": str(WORKER / f"{stem}-geometry-report.md"),
        "metrics": metrics,
        "placements": placements,
        "limitations": [
            "Procedural/PIL fallback, not image-generation API output.",
            "Style is an approximation of the blue watercolor control-panel references.",
            "Path curves are polygon-flattened before raster masking.",
        ],
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    metadata["metadata_json"] = str(metadata_path)
    return metadata


def main() -> int:
    outputs = [
        save_candidate("np01-back-top.svg", 2026061607, build_np01_back_top),
        save_candidate("np02-front-top.svg", 2026061608, build_np02_front_top),
    ]
    summary_path = WORKER / "generation-summary.json"
    summary_path.write_text(json.dumps(outputs, indent=2) + "\n", encoding="utf-8")
    for item in outputs:
        print(json.dumps({"candidate_png": item["candidate_png"], "metrics": item["metrics"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
