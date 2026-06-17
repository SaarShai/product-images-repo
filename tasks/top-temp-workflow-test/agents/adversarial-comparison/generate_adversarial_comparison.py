#!/usr/bin/env python3
"""Adversarial comparison for the top-temp SVG template workflow.

The test intentionally contrasts a naive "clip a full rectangle to the outer
panel" approach with a manifest-aware method that subtracts internal cutouts
before placing focal control-panel motifs.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "tasks" / "top-temp-workflow-test"
OUT = TASK / "agents" / "adversarial-comparison"
SVG = TASK / "source" / "template.svg"
MANIFEST = TASK / "template-manifest.json"
GEOMETRY_REPORT = TASK / "svg-geometry-report.md"
REFS = [
    TASK / "refs" / "ChatGPT Image Jun 9, 2026, 11_19_45 PM.png",
    TASK / "refs" / "ChatGPT Image Jun 9, 2026, 11_17_34 PM.png",
]

WIDTH = 1200
HEIGHT = 1184
AA = 4

COMMAND_RE = re.compile(r"[MmLlHhVvCcSsZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")

Point = tuple[float, float]


@dataclass(frozen=True)
class Geometry:
    viewbox: tuple[float, float, float, float]
    paths: list[list[Point]]
    path_data: list[str]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


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
        raise ValueError("Expected SVG path number")
    return float(tokens[index]), index + 1


def read_pair(tokens: list[str], index: int) -> tuple[Point, int]:
    x, index = read_number(tokens, index)
    y, index = read_number(tokens, index)
    return (x, y), index


def cubic_point(p0: Point, p1: Point, p2: Point, p3: Point, t: float) -> Point:
    inv = 1.0 - t
    x = (inv**3 * p0[0]) + (3 * inv * inv * t * p1[0]) + (3 * inv * t * t * p2[0]) + (t**3 * p3[0])
    y = (inv**3 * p0[1]) + (3 * inv * inv * t * p1[1]) + (3 * inv * t * t * p2[1]) + (t**3 * p3[1])
    return (x, y)


def apply_relative(point: Point, current: Point, relative: bool) -> Point:
    if relative:
        return (current[0] + point[0], current[1] + point[1])
    return point


def parse_path_d(data: str, curve_steps: int = 42) -> list[Point]:
    tokens = COMMAND_RE.findall(data.replace(",", " "))
    index = 0
    command: str | None = None
    current: Point = (0.0, 0.0)
    start: Point = (0.0, 0.0)
    last_cubic_control: Point | None = None
    points: list[Point] = []

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
            start = current
            points.append(current)
            last_cubic_control = None
            command = "l" if relative else "L"
            while index < len(tokens) and not is_command(tokens[index]):
                point, index = read_pair(tokens, index)
                current = apply_relative(point, current, relative)
                points.append(current)
        elif upper == "L":
            while index < len(tokens) and not is_command(tokens[index]):
                point, index = read_pair(tokens, index)
                current = apply_relative(point, current, relative)
                points.append(current)
            last_cubic_control = None
        elif upper == "H":
            while index < len(tokens) and not is_command(tokens[index]):
                x, index = read_number(tokens, index)
                current = (current[0] + x, current[1]) if relative else (x, current[1])
                points.append(current)
            last_cubic_control = None
        elif upper == "V":
            while index < len(tokens) and not is_command(tokens[index]):
                y, index = read_number(tokens, index)
                current = (current[0], current[1] + y) if relative else (current[0], y)
                points.append(current)
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
                    points.append(cubic_point(p0, p1, p2, p3, step / curve_steps))
                current = p3
                last_cubic_control = p2
        elif upper == "S":
            while index < len(tokens) and not is_command(tokens[index]):
                control_2, index = read_pair(tokens, index)
                end, index = read_pair(tokens, index)
                if last_cubic_control is None:
                    p1 = current
                else:
                    p1 = ((2 * current[0]) - last_cubic_control[0], (2 * current[1]) - last_cubic_control[1])
                p0 = current
                p2 = apply_relative(control_2, current, relative)
                p3 = apply_relative(end, current, relative)
                for step in range(1, curve_steps + 1):
                    points.append(cubic_point(p0, p1, p2, p3, step / curve_steps))
                current = p3
                last_cubic_control = p2
        elif upper == "Z":
            if points and points[-1] != start:
                points.append(start)
            current = start
            last_cubic_control = None
            command = None
        else:
            raise ValueError(f"Unsupported SVG command {command!r}")

    return points


def read_geometry(svg_path: Path) -> Geometry:
    tree = ET.parse(svg_path)
    root = tree.getroot()
    viewbox_text = root.attrib["viewBox"]
    viewbox = tuple(float(item) for item in viewbox_text.replace(",", " ").split())
    if len(viewbox) != 4:
        raise ValueError(f"Unexpected viewBox: {viewbox_text}")

    paths: list[list[Point]] = []
    path_data: list[str] = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "path":
            continue
        data = element.attrib.get("d")
        if not data:
            continue
        path_data.append(data)
        paths.append(parse_path_d(data))

    if len(paths) < 3:
        raise ValueError(f"Expected at least 3 paths in {svg_path}, found {len(paths)}")
    return Geometry(viewbox=viewbox, paths=paths, path_data=path_data)


def transform(point: Point, viewbox: tuple[float, float, float, float], width: int, height: int, aa: int = 1) -> tuple[int, int]:
    min_x, min_y, box_w, box_h = viewbox
    return (
        round((point[0] - min_x) * width / box_w * aa),
        round((point[1] - min_y) * height / box_h * aa),
    )


def path_to_pixels(path: list[Point], geometry: Geometry, width: int, height: int, aa: int = 1) -> list[tuple[int, int]]:
    return [transform(point, geometry.viewbox, width, height, aa) for point in path]


def bbox(points: list[Point]) -> list[float]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)]


def build_path_mask(geometry: Geometry, indices: list[int], width: int = WIDTH, height: int = HEIGHT, aa: int = AA) -> Image.Image:
    mask = Image.new("L", (width * aa, height * aa), 0)
    draw = ImageDraw.Draw(mask)
    for index in indices:
        draw.polygon(path_to_pixels(geometry.paths[index], geometry, width, height, aa), fill=255)
    return mask.resize((width, height), Image.Resampling.LANCZOS)


def hard_mask(mask: Image.Image, threshold: int = 8) -> Image.Image:
    return mask.point(lambda value: 255 if value > threshold else 0)


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_dashed_line(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], fill: tuple[int, int, int, int], width: int, dash: int = 14, gap: int = 10) -> None:
    for start, end in zip(points, points[1:]):
        x0, y0 = start
        x1, y1 = end
        length = math.hypot(x1 - x0, y1 - y0)
        if length == 0:
            continue
        dx = (x1 - x0) / length
        dy = (y1 - y0) / length
        distance = 0.0
        while distance < length:
            segment_end = min(length, distance + dash)
            draw.line(
                [
                    (round(x0 + dx * distance), round(y0 + dy * distance)),
                    (round(x0 + dx * segment_end), round(y0 + dy * segment_end)),
                ],
                fill=fill,
                width=width,
            )
            distance += dash + gap


def draw_template_lines(base: Image.Image, geometry: Geometry, outer_indices: list[int], cutout_indices: list[int]) -> Image.Image:
    overlay = base.convert("RGBA")
    line_layer = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(line_layer)
    for index in outer_indices:
        points = path_to_pixels(geometry.paths[index], geometry, overlay.width, overlay.height)
        draw_dashed_line(draw, points, fill=(18, 76, 142, 235), width=4, dash=18, gap=12)
        draw_dashed_line(draw, points, fill=(255, 219, 85, 210), width=2, dash=18, gap=12)
    for index in cutout_indices:
        points = path_to_pixels(geometry.paths[index], geometry, overlay.width, overlay.height)
        draw_dashed_line(draw, points, fill=(168, 22, 72, 245), width=5, dash=14, gap=8)
        draw_dashed_line(draw, points, fill=(255, 255, 255, 215), width=2, dash=14, gap=8)
    overlay.alpha_composite(line_layer)
    return overlay


def make_watercolor_background(width: int, height: int) -> Image.Image:
    base = Image.new("RGBA", (width, height), (142, 181, 225, 255))
    draw = ImageDraw.Draw(base, "RGBA")

    for y in range(height):
        t = y / max(1, height - 1)
        r = int(166 - (42 * t))
        g = int(202 - (52 * t))
        b = int(238 - (26 * t))
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    palette = [
        (56, 115, 183, 34),
        (255, 255, 255, 46),
        (42, 91, 162, 30),
        (96, 164, 218, 36),
        (24, 76, 143, 22),
    ]
    for i in range(180):
        x = (i * 197 + 41) % width
        y = (i * 113 + 73) % height
        rx = 60 + ((i * 23) % 180)
        ry = 20 + ((i * 17) % 90)
        color = palette[i % len(palette)]
        draw.ellipse((x - rx, y - ry, x + rx, y + ry), fill=color)

    paper = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    paper_draw = ImageDraw.Draw(paper, "RGBA")
    for x in range(0, width, 18):
        alpha = 7 if (x // 18) % 2 else 4
        paper_draw.line([(x, 0), (x + 35, height)], fill=(255, 255, 255, alpha), width=1)
    return Image.alpha_composite(base, paper)


def draw_shadowed_round_rect(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, fill: tuple[int, int, int, int], outline: tuple[int, int, int, int], width: int = 5) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle((x0 + 8, y0 + 8, x1 + 8, y1 + 8), radius=radius, fill=(20, 62, 126, 58))
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    draw.rounded_rectangle((x0 + 12, y0 + 10, x1 - 12, y0 + max(14, (y1 - y0) // 2)), radius=max(4, radius - 8), fill=(255, 255, 255, 54))


def draw_dial(draw: ImageDraw.ImageDraw, center: tuple[int, int], radius: int, pointer_angle: float = -0.7) -> None:
    cx, cy = center
    draw.ellipse((cx - radius + 10, cy - radius + 14, cx + radius + 10, cy + radius + 14), fill=(17, 58, 118, 72))
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(37, 99, 177, 255), outline=(13, 62, 130, 255), width=8)
    draw.ellipse((cx - radius + 24, cy - radius + 24, cx + radius - 24, cy + radius - 24), fill=(210, 235, 251, 255), outline=(29, 83, 157, 255), width=5)
    for i in range(9):
        angle = math.radians(205 + i * 16)
        x0 = cx + math.cos(angle) * (radius - 36)
        y0 = cy + math.sin(angle) * (radius - 36)
        x1 = cx + math.cos(angle) * (radius - 18)
        y1 = cy + math.sin(angle) * (radius - 18)
        draw.line([(x0, y0), (x1, y1)], fill=(34, 83, 150, 255), width=4)
    px = cx + math.cos(pointer_angle) * (radius - 42)
    py = cy + math.sin(pointer_angle) * (radius - 42)
    draw.line([(cx, cy), (px, py)], fill=(28, 70, 138, 255), width=8)
    draw.ellipse((cx - 12, cy - 12, cx + 12, cy + 12), fill=(19, 66, 135, 255))
    draw.arc((cx - radius + 38, cy - radius + 24, cx + radius - 30, cy + radius - 58), 202, 284, fill=(255, 255, 255, 142), width=8)


def draw_slider(draw: ImageDraw.ImageDraw, y: int, x0: int, x1: int, knob_x: int, color: tuple[int, int, int, int]) -> None:
    draw.rounded_rectangle((x0, y - 7, x1, y + 7), radius=7, fill=(86, 151, 215, 180), outline=(24, 81, 157, 220), width=2)
    draw.line((x0 + 14, y - 2, x1 - 14, y - 2), fill=(226, 242, 255, 124), width=3)
    draw.rounded_rectangle((knob_x - 15, y - 15, knob_x + 15, y + 15), radius=7, fill=color, outline=(34, 78, 148, 245), width=3)
    draw.rounded_rectangle((knob_x - 9, y - 11, knob_x + 9, y - 3), radius=4, fill=(255, 255, 255, 84))


def object_mask(size: tuple[int, int], draw_fn) -> Image.Image:
    mask = Image.new("L", size, 0)
    mask_draw = ImageDraw.Draw(mask)
    draw_fn(mask_draw)
    return mask


def can_place(mask: Image.Image, allowed_hard: Image.Image, forbidden_hard: Image.Image) -> bool:
    outside = ImageChops.subtract(mask, allowed_hard)
    forbidden_overlap = ImageChops.multiply(mask, forbidden_hard)
    return outside.getbbox() is None and forbidden_overlap.getbbox() is None


def draw_if_safe(image: Image.Image, allowed_hard: Image.Image, forbidden_hard: Image.Image, mask_fn, draw_fn, label: str, placements: list[dict[str, str]]) -> bool:
    mask = object_mask(image.size, mask_fn)
    ok = can_place(mask, allowed_hard, forbidden_hard)
    placements.append({"label": label, "status": "drawn" if ok else "skipped-overlaps-cutout-or-edge"})
    if ok:
        draw_fn(ImageDraw.Draw(image, "RGBA"))
    return ok


def draw_naive_rectangular_art() -> Image.Image:
    image = make_watercolor_background(WIDTH, HEIGHT)
    draw = ImageDraw.Draw(image, "RGBA")

    # This is intentionally wrong: it behaves like a normal rectangular control
    # panel, so objects march straight through the diagonal slot and bolt hole.
    for y, knob, color in [
        (355, 810, (241, 91, 86, 255)),
        (425, 940, (255, 193, 68, 255)),
        (495, 1075, (91, 205, 174, 255)),
        (565, 1210, (250, 111, 74, 255)),
        (635, 1335, (241, 87, 97, 255)),
    ]:
        draw_slider(draw, y, 460, 1370, knob, color)

    draw_dial(draw, (1120, 930), 124, pointer_angle=-2.25)
    for x, color in [
        (500, (239, 91, 87, 255)),
        (610, (250, 191, 65, 255)),
        (720, (91, 202, 174, 255)),
    ]:
        draw_shadowed_round_rect(draw, (x, 720, x + 70, 860), 34, color, (25, 78, 151, 255), width=5)
    draw_shadowed_round_rect(draw, (250, 210, 390, 330), 32, (236, 244, 251, 255), (24, 80, 155, 255), width=7)
    return image


def draw_corrected_art(allowed_mask: Image.Image, cutout_mask: Image.Image) -> tuple[Image.Image, list[dict[str, str]]]:
    background = make_watercolor_background(WIDTH, HEIGHT)
    white = Image.new("RGBA", (WIDTH, HEIGHT), (255, 255, 255, 255))
    allowed_smooth = ImageChops.subtract(allowed_mask, cutout_mask.point(lambda value: min(255, value + 50)))
    image = Image.composite(background, white, allowed_smooth)
    draw = ImageDraw.Draw(image, "RGBA")
    placements: list[dict[str, str]] = []

    allowed_hard = hard_mask(allowed_mask, threshold=16)
    forbidden_hard = hard_mask(cutout_mask.filter(ImageFilter.MaxFilter(35)), threshold=8)

    draw_if_safe(
        image,
        allowed_hard,
        forbidden_hard,
        lambda d: d.ellipse((250, 455, 480, 685), fill=255),
        lambda d: draw_dial(d, (365, 570), 108, pointer_angle=0.45),
        "large dial in middle-left safe pocket",
        placements,
    )

    for y, knob, color, label in [
        (760, 245, (96, 205, 174, 255), "lower-left slider A"),
        (820, 345, (245, 92, 84, 255), "lower-left slider B"),
        (880, 445, (255, 194, 69, 255), "lower-left slider C"),
    ]:
        draw_if_safe(
            image,
            allowed_hard,
            forbidden_hard,
            lambda d, y=y: d.rounded_rectangle((100, y - 20, 510, y + 20), radius=14, fill=255),
            lambda d, y=y, knob=knob, color=color: draw_slider(d, y, 105, 505, knob, color),
            label,
            placements,
        )

    for x, color, label in [
        (740, (241, 91, 86, 255), "lower-middle red post"),
        (850, (255, 193, 68, 255), "lower-middle amber post"),
        (960, (92, 204, 174, 255), "lower-middle teal post"),
    ]:
        draw_if_safe(
            image,
            allowed_hard,
            forbidden_hard,
            lambda d, x=x: d.rounded_rectangle((x - 38, 980, x + 38, 1130), radius=32, fill=255),
            lambda d, x=x, color=color: draw_shadowed_round_rect(d, (x - 32, 990, x + 32, 1120), 30, color, (23, 74, 148, 255), width=5),
            label,
            placements,
        )

    for y, color, label in [
        (230, (255, 193, 68, 255), "upper-left pill red-line"),
        (295, (94, 205, 174, 255), "upper-left pill teal-line"),
        (360, (241, 91, 86, 255), "upper-left pill amber-line"),
    ]:
        draw_if_safe(
            image,
            allowed_hard,
            forbidden_hard,
            lambda d, y=y: d.rounded_rectangle((530, y - 22, 730, y + 22), radius=18, fill=255),
            lambda d, y=y, color=color: draw_shadowed_round_rect(d, (540, y - 18, 720, y + 18), 17, color, (24, 77, 151, 255), width=4),
            label,
            placements,
        )

    for y, color, label in [
        (1010, (255, 193, 68, 255), "right-strip short indicator A"),
        (1080, (92, 204, 174, 255), "right-strip short indicator B"),
    ]:
        draw_if_safe(
            image,
            allowed_hard,
            forbidden_hard,
            lambda d, y=y: d.rounded_rectangle((960, y - 18, 1120, y + 18), radius=16, fill=255),
            lambda d, y=y, color=color: draw_shadowed_round_rect(d, (970, y - 15, 1110, y + 15), 15, color, (24, 77, 151, 255), width=4),
            label,
            placements,
        )

    # A subtle border wash is background-like and constrained to the allowed mask.
    draw.line([(150, 1025), (495, 1025)], fill=(23, 76, 149, 92), width=7)
    draw.arc((90, 200, 545, 655), 185, 255, fill=(255, 255, 255, 120), width=9)

    image = Image.composite(image, white, allowed_mask)
    image = Image.composite(white, image, hard_mask(cutout_mask, threshold=2))
    return image.convert("RGB"), placements


def paintable_nonwhite_pixels(image: Image.Image, mask: Image.Image, threshold: int = 30) -> int:
    rgb = image.convert("RGB")
    pixels = rgb.load()
    mask_pixels = hard_mask(mask, threshold=8).load()
    count = 0
    for y in range(rgb.height):
        for x in range(rgb.width):
            if mask_pixels[x, y] == 0:
                continue
            r, g, b = pixels[x, y]
            if (255 - r) + (255 - g) + (255 - b) > threshold:
                count += 1
    return count


def coverage_pct(image: Image.Image, mask: Image.Image) -> float:
    mask_hard = hard_mask(mask, threshold=8)
    mask_pixels = mask_hard.load()
    rgb = image.convert("RGB")
    pixels = rgb.load()
    total = 0
    painted = 0
    for y in range(rgb.height):
        for x in range(rgb.width):
            if mask_pixels[x, y] == 0:
                continue
            total += 1
            r, g, b = pixels[x, y]
            if (255 - r) + (255 - g) + (255 - b) > 30:
                painted += 1
    return round((painted / total) * 100.0, 2) if total else 0.0


def make_naive_failure_overlay(naive: Image.Image, geometry: Geometry, outer_indices: list[int], cutout_indices: list[int], cutout_mask: Image.Image) -> Image.Image:
    overlay = naive.convert("RGBA")
    violation = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    violation_pixels = hard_mask(cutout_mask, threshold=8)
    violation_draw = ImageDraw.Draw(violation, "RGBA")
    violation_draw.bitmap((0, 0), violation_pixels, fill=(255, 0, 88, 92))
    overlay.alpha_composite(violation)
    overlay = draw_template_lines(overlay, geometry, outer_indices, cutout_indices)

    draw = ImageDraw.Draw(overlay, "RGBA")
    title_font = load_font(34, bold=True)
    body_font = load_font(23)
    draw.rounded_rectangle((22, 22, 790, 150), radius=12, fill=(255, 255, 255, 220), outline=(172, 26, 76, 255), width=3)
    draw.text((42, 38), "NAIVE FAILURE: internal SVG paths treated as paintable", font=title_font, fill=(112, 14, 48, 255))
    draw.text((44, 90), "Red tint marks path[1]/path[2] keep-clear zones filled with background and motifs.", font=body_font, fill=(46, 60, 82, 255))
    draw.line([(755, 142), (1018, 642)], fill=(172, 26, 76, 255), width=4)
    draw.line([(742, 142), (1055, 934)], fill=(172, 26, 76, 255), width=4)
    return overlay.convert("RGB")


def make_mask_debug(allowed_mask: Image.Image, cutout_mask: Image.Image, corrected: Image.Image, corrected_cutout_pixels: int, corrected_outside_pixels: int) -> Image.Image:
    debug = Image.new("RGBA", (WIDTH, HEIGHT), (42, 48, 58, 255))
    allowed_tint = Image.new("RGBA", (WIDTH, HEIGHT), (55, 178, 222, 122))
    cutout_tint = Image.new("RGBA", (WIDTH, HEIGHT), (255, 0, 116, 172))
    white = Image.new("RGBA", (WIDTH, HEIGHT), (255, 255, 255, 255))
    debug = Image.composite(allowed_tint, debug, hard_mask(allowed_mask, threshold=8))
    debug = Image.composite(cutout_tint, debug, hard_mask(cutout_mask, threshold=8))
    corrected_ghost = corrected.convert("RGBA")
    corrected_ghost.putalpha(92)
    debug.alpha_composite(corrected_ghost)

    draw = ImageDraw.Draw(debug, "RGBA")
    title_font = load_font(34, bold=True)
    body_font = load_font(24)
    draw.rounded_rectangle((24, 22, 675, 152), radius=12, fill=(255, 255, 255, 228), outline=(26, 80, 148, 255), width=3)
    draw.text((45, 38), "CORRECTED MASK DEBUG", font=title_font, fill=(15, 60, 124, 255))
    draw.text((45, 90), f"cyan=paintable, magenta=cutout; cutout pixels={corrected_cutout_pixels}, outside={corrected_outside_pixels}", font=body_font, fill=(42, 56, 75, 255))
    return Image.composite(debug, white, Image.new("L", (WIDTH, HEIGHT), 255)).convert("RGB")


def outside_nonwhite_pixels(image: Image.Image, outer_mask: Image.Image, cutout_mask: Image.Image) -> int:
    outside = ImageChops.invert(hard_mask(outer_mask, threshold=8))
    outside = ImageChops.subtract(outside, hard_mask(cutout_mask, threshold=8))
    return paintable_nonwhite_pixels(image, outside)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    geometry = read_geometry(SVG)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    outer_indices = [int(item["element"].removeprefix("path[").removesuffix("]")) for item in manifest["geometry_roles"]["outer_contours"]]
    cutout_indices = [int(item["element"].removeprefix("path[").removesuffix("]")) for item in manifest["geometry_roles"]["internal_cutouts"]]
    all_indices = list(range(len(geometry.paths)))

    outer_mask = build_path_mask(geometry, outer_indices)
    role_blind_all_paths_mask = build_path_mask(geometry, all_indices)
    cutout_mask = build_path_mask(geometry, cutout_indices)
    allowed_mask = ImageChops.subtract(outer_mask, hard_mask(cutout_mask, threshold=2))

    naive_rectangular = draw_naive_rectangular_art()
    white = Image.new("RGBA", (WIDTH, HEIGHT), (255, 255, 255, 255))
    naive_outer_clipped = Image.composite(naive_rectangular, white, role_blind_all_paths_mask).convert("RGB")
    naive_overlay = make_naive_failure_overlay(naive_outer_clipped, geometry, outer_indices, cutout_indices, cutout_mask)

    corrected, placements = draw_corrected_art(allowed_mask, cutout_mask)
    corrected_overlay = draw_template_lines(corrected.convert("RGBA"), geometry, outer_indices, cutout_indices).convert("RGB")

    naive_cutout_pixels = paintable_nonwhite_pixels(naive_outer_clipped, cutout_mask)
    corrected_cutout_pixels = paintable_nonwhite_pixels(corrected, cutout_mask)
    naive_outside_pixels = outside_nonwhite_pixels(naive_outer_clipped, outer_mask, cutout_mask)
    corrected_outside_pixels = outside_nonwhite_pixels(corrected, outer_mask, cutout_mask)
    debug = make_mask_debug(allowed_mask, cutout_mask, corrected, corrected_cutout_pixels, corrected_outside_pixels)

    naive_path = OUT / "naive-failure-overlay.png"
    corrected_path = OUT / "corrected-artwork.png"
    corrected_overlay_path = OUT / "corrected-overlay.png"
    debug_path = OUT / "corrected-mask-debug.png"
    metadata_path = OUT / "comparison-metadata.json"

    naive_overlay.save(naive_path)
    corrected.save(corrected_path)
    corrected_overlay.save(corrected_overlay_path)
    debug.save(debug_path)

    metadata = {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "purpose": "adversarial naive-vs-corrected comparison for top-temp SVG-template workflow",
        "source_svg": rel(SVG),
        "source_svg_sha256": sha256(SVG),
        "template_manifest": rel(MANIFEST),
        "geometry_report": rel(GEOMETRY_REPORT),
        "style_refs": [{"path": rel(path), "sha256": sha256(path)} for path in REFS],
        "output_dimensions": [WIDTH, HEIGHT],
        "path_bboxes_from_parser": {f"path[{index}]": bbox(path) for index, path in enumerate(geometry.paths)},
        "manifest_roles_used": {
            "outer_indices": outer_indices,
            "cutout_indices": cutout_indices,
            "safe_pockets": manifest.get("safe_pockets", []),
            "no_focal_motif_zones": manifest.get("no_focal_motif_zones", []),
        },
        "naive_method": {
            "description": "full rectangular control-panel art clipped to all SVG paths/outer body without subtracting manifest internal_cutouts",
            "failure": "path[1] diagonal slot and path[2] round cutout retain painted background/motifs",
            "cutout_nonwhite_pixels": naive_cutout_pixels,
            "outside_nonwhite_pixels": naive_outside_pixels,
            "panel_coverage_pct": coverage_pct(naive_outer_clipped, allowed_mask),
        },
        "corrected_method": {
            "description": "manifest-aware outer contour minus path[1]/path[2], with focal motifs placed only after mask-intersection checks",
            "cutout_nonwhite_pixels": corrected_cutout_pixels,
            "outside_nonwhite_pixels": corrected_outside_pixels,
            "panel_coverage_pct": coverage_pct(corrected, allowed_mask),
            "placements": placements,
            "verdict": "PASS" if corrected_cutout_pixels == 0 and corrected_outside_pixels == 0 else "FAIL",
        },
        "artifacts": {
            "naive_failure_overlay": rel(naive_path),
            "corrected_artwork": rel(corrected_path),
            "corrected_overlay": rel(corrected_overlay_path),
            "corrected_mask_debug": rel(debug_path),
            "metadata": rel(metadata_path),
        },
        "workflow_signal": [
            "A role-blind parser can draw or permit paint through path[1] and path[2].",
            "The manifest is the missing semantic layer: path order alone is insufficient.",
            "Correctness requires checking internal_cutouts before drawing focal motifs, not only after clipping.",
        ],
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "naive_cutout_nonwhite_pixels": naive_cutout_pixels,
        "corrected_cutout_nonwhite_pixels": corrected_cutout_pixels,
        "corrected_outside_nonwhite_pixels": corrected_outside_pixels,
        "metadata": rel(metadata_path),
    }, indent=2))
    return 0 if corrected_cutout_pixels == 0 and corrected_outside_pixels == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
