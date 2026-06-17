#!/usr/bin/env python3
"""Sparse full-panel proof for the top-temp SVG template.

This candidate tests whether the complex top-temp panel works better when the
whole body is quiet watercolor and only a few large control motifs are placed in
named manifest pockets. The SVG roles are taken from template-manifest.json:

- path[0]: outer material contour
- path[1]: large diagonal rounded slot keep-clear
- path[2]: lower-right round/bolt-like keep-clear

The final alpha mask is an export guardrail. Motif masks are checked before that
guardrail is applied, so a passing candidate is not a rectangular crop rescue.
"""

from __future__ import annotations

import json
import math
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable
from xml.etree import ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "tasks" / "top-temp-workflow-test"
OUT_DIR = TASK / "agents" / "simple-full-panel"
SVG_PATH = TASK / "source" / "template.svg"
MANIFEST_PATH = TASK / "template-manifest.json"
GEOMETRY_REPORT_PATH = TASK / "svg-geometry-report.md"
REF_PATHS = [
    TASK / "refs" / "ChatGPT Image Jun 9, 2026, 11_19_45 PM.png",
    TASK / "refs" / "ChatGPT Image Jun 9, 2026, 11_17_34 PM.png",
]

ARTWORK_OUT = OUT_DIR / "simple-full-panel-artwork.png"
OVERLAY_OUT = OUT_DIR / "simple-full-panel-overlay.png"
MASK_DEBUG_OUT = OUT_DIR / "simple-full-panel-mask-debug.png"
METADATA_OUT = OUT_DIR / "simple-full-panel-metadata.json"

RNG = random.Random(42)
EDGE_MARGIN_PX = 16
CUTOUT_MARGIN_PX = 48


@dataclass(frozen=True)
class SvgPath:
    index: int
    points: list[tuple[float, float]]
    mapped_points: list[tuple[float, float]]
    bounds: tuple[float, float, float, float]
    role: str


@dataclass
class MotifGroup:
    name: str
    pocket: str
    bbox: tuple[int, int, int, int]
    metrics: dict[str, int]


COMMAND_RE = re.compile(
    r"([MmLlHhVvCcSsQqTtZz])|([-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?)"
)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def parse_viewbox(svg_path: Path) -> tuple[float, float, float, float]:
    root = ET.parse(svg_path).getroot()
    raw = root.attrib.get("viewBox")
    if not raw:
        raise ValueError("SVG has no viewBox")
    parts = [float(v) for v in raw.replace(",", " ").split()]
    if len(parts) != 4:
        raise ValueError(f"Unexpected viewBox: {raw}")
    return tuple(parts)  # type: ignore[return-value]


def tokenize_path(d: str) -> list[str | float]:
    tokens: list[str | float] = []
    for command, number in COMMAND_RE.findall(d):
        if command:
            tokens.append(command)
        elif number:
            tokens.append(float(number))
    return tokens


def is_command(token: str | float) -> bool:
    return isinstance(token, str)


def read_number(tokens: list[str | float], pos: int) -> tuple[float, int]:
    if pos >= len(tokens) or is_command(tokens[pos]):
        raise ValueError(f"Expected number at token {pos}")
    return float(tokens[pos]), pos + 1


def cubic_point(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    mt = 1.0 - t
    return (
        (mt**3) * p0[0] + 3 * (mt**2) * t * p1[0] + 3 * mt * (t**2) * p2[0] + (t**3) * p3[0],
        (mt**3) * p0[1] + 3 * (mt**2) * t * p1[1] + 3 * mt * (t**2) * p2[1] + (t**3) * p3[1],
    )


def quad_point(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    mt = 1.0 - t
    return (
        (mt**2) * p0[0] + 2 * mt * t * p1[0] + (t**2) * p2[0],
        (mt**2) * p0[1] + 2 * mt * t * p1[1] + (t**2) * p2[1],
    )


def parse_svg_path_points(d: str, curve_steps: int = 34) -> list[tuple[float, float]]:
    tokens = tokenize_path(d)
    points: list[tuple[float, float]] = []
    pos = 0
    command: str | None = None
    current = (0.0, 0.0)
    start = (0.0, 0.0)
    last_cubic_ctrl: tuple[float, float] | None = None
    last_quad_ctrl: tuple[float, float] | None = None

    def add_line(pt: tuple[float, float]) -> None:
        nonlocal current
        if not points:
            points.append(current)
        points.append(pt)
        current = pt

    while pos < len(tokens):
        if is_command(tokens[pos]):
            command = str(tokens[pos])
            pos += 1
        if command is None:
            raise ValueError("SVG path starts without a command")

        cmd = command
        upper = cmd.upper()
        relative = cmd.islower()

        if upper == "Z":
            points.append(start)
            current = start
            last_cubic_ctrl = None
            last_quad_ctrl = None
            command = None
            continue

        if upper == "M":
            first = True
            while pos < len(tokens) and not is_command(tokens[pos]):
                x, pos = read_number(tokens, pos)
                y, pos = read_number(tokens, pos)
                if relative:
                    x += current[0]
                    y += current[1]
                current = (x, y)
                if first:
                    start = current
                    first = False
                points.append(current)
                last_cubic_ctrl = None
                last_quad_ctrl = None
            command = "l" if relative else "L"
            continue

        if upper == "L":
            while pos < len(tokens) and not is_command(tokens[pos]):
                x, pos = read_number(tokens, pos)
                y, pos = read_number(tokens, pos)
                if relative:
                    x += current[0]
                    y += current[1]
                add_line((x, y))
                last_cubic_ctrl = None
                last_quad_ctrl = None
            continue

        if upper == "H":
            while pos < len(tokens) and not is_command(tokens[pos]):
                x, pos = read_number(tokens, pos)
                if relative:
                    x += current[0]
                add_line((x, current[1]))
                last_cubic_ctrl = None
                last_quad_ctrl = None
            continue

        if upper == "V":
            while pos < len(tokens) and not is_command(tokens[pos]):
                y, pos = read_number(tokens, pos)
                if relative:
                    y += current[1]
                add_line((current[0], y))
                last_cubic_ctrl = None
                last_quad_ctrl = None
            continue

        if upper == "C":
            while pos < len(tokens) and not is_command(tokens[pos]):
                x1, pos = read_number(tokens, pos)
                y1, pos = read_number(tokens, pos)
                x2, pos = read_number(tokens, pos)
                y2, pos = read_number(tokens, pos)
                x, pos = read_number(tokens, pos)
                y, pos = read_number(tokens, pos)
                if relative:
                    p1 = (current[0] + x1, current[1] + y1)
                    p2 = (current[0] + x2, current[1] + y2)
                    p3 = (current[0] + x, current[1] + y)
                else:
                    p1, p2, p3 = (x1, y1), (x2, y2), (x, y)
                p0 = current
                for step in range(1, curve_steps + 1):
                    points.append(cubic_point(p0, p1, p2, p3, step / curve_steps))
                current = p3
                last_cubic_ctrl = p2
                last_quad_ctrl = None
            continue

        if upper == "S":
            while pos < len(tokens) and not is_command(tokens[pos]):
                x2, pos = read_number(tokens, pos)
                y2, pos = read_number(tokens, pos)
                x, pos = read_number(tokens, pos)
                y, pos = read_number(tokens, pos)
                p1 = (
                    current[0] + (current[0] - last_cubic_ctrl[0]),
                    current[1] + (current[1] - last_cubic_ctrl[1]),
                ) if last_cubic_ctrl else current
                if relative:
                    p2 = (current[0] + x2, current[1] + y2)
                    p3 = (current[0] + x, current[1] + y)
                else:
                    p2, p3 = (x2, y2), (x, y)
                p0 = current
                for step in range(1, curve_steps + 1):
                    points.append(cubic_point(p0, p1, p2, p3, step / curve_steps))
                current = p3
                last_cubic_ctrl = p2
                last_quad_ctrl = None
            continue

        if upper == "Q":
            while pos < len(tokens) and not is_command(tokens[pos]):
                x1, pos = read_number(tokens, pos)
                y1, pos = read_number(tokens, pos)
                x, pos = read_number(tokens, pos)
                y, pos = read_number(tokens, pos)
                if relative:
                    p1 = (current[0] + x1, current[1] + y1)
                    p2 = (current[0] + x, current[1] + y)
                else:
                    p1, p2 = (x1, y1), (x, y)
                p0 = current
                for step in range(1, curve_steps + 1):
                    points.append(quad_point(p0, p1, p2, step / curve_steps))
                current = p2
                last_quad_ctrl = p1
                last_cubic_ctrl = None
            continue

        if upper == "T":
            while pos < len(tokens) and not is_command(tokens[pos]):
                x, pos = read_number(tokens, pos)
                y, pos = read_number(tokens, pos)
                p1 = (
                    current[0] + (current[0] - last_quad_ctrl[0]),
                    current[1] + (current[1] - last_quad_ctrl[1]),
                ) if last_quad_ctrl else current
                p2 = (current[0] + x, current[1] + y) if relative else (x, y)
                p0 = current
                for step in range(1, curve_steps + 1):
                    points.append(quad_point(p0, p1, p2, step / curve_steps))
                current = p2
                last_quad_ctrl = p1
                last_cubic_ctrl = None
            continue

        raise ValueError(f"Unsupported SVG path command: {cmd}")

    return points


def map_points(
    points: Iterable[tuple[float, float]],
    viewbox: tuple[float, float, float, float],
    size: tuple[int, int],
) -> list[tuple[float, float]]:
    vx, vy, vw, vh = viewbox
    sx = size[0] / vw
    sy = size[1] / vh
    return [((x - vx) * sx, (y - vy) * sy) for x, y in points]


def path_bounds(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def load_svg_paths(size: tuple[int, int]) -> tuple[list[SvgPath], tuple[float, float, float, float]]:
    viewbox = parse_viewbox(SVG_PATH)
    root = ET.parse(SVG_PATH).getroot()
    ns = {"svg": "http://www.w3.org/2000/svg"}
    raw_paths = root.findall(".//svg:path", ns)
    roles = [
        "outer material contour",
        "large diagonal rounded slot keep-clear",
        "lower-right round/bolt-like keep-clear",
    ]
    paths: list[SvgPath] = []
    for index, path_el in enumerate(raw_paths):
        points = parse_svg_path_points(path_el.attrib["d"])
        paths.append(
            SvgPath(
                index=index,
                points=points,
                mapped_points=map_points(points, viewbox, size),
                bounds=path_bounds(points),
                role=roles[index] if index < len(roles) else "unclassified path",
            )
        )
    return paths, viewbox


def polygon_mask(size: tuple[int, int], paths: list[SvgPath]) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for path in paths:
        draw.polygon(path.mapped_points, fill=255)
    return mask


def max_images(a: Image.Image, b: Image.Image) -> Image.Image:
    return Image.fromarray(np.maximum(np.array(a), np.array(b)).astype(np.uint8))


def build_masks(size: tuple[int, int], paths: list[SvgPath]) -> dict[str, Image.Image]:
    outer = polygon_mask(size, [paths[0]])
    cutouts = polygon_mask(size, paths[1:])
    outer_arr = np.array(outer, dtype=np.uint8)
    cut_arr = np.array(cutouts, dtype=np.uint8)
    allowed_arr = outer_arr.copy()
    allowed_arr[cut_arr > 0] = 0
    allowed = Image.fromarray(allowed_arr)

    edge_eroded = outer.filter(ImageFilter.MinFilter(EDGE_MARGIN_PX * 2 + 1))
    cutout_margin = cutouts.filter(ImageFilter.MaxFilter(CUTOUT_MARGIN_PX * 2 + 1))
    motif_safe_arr = np.array(edge_eroded, dtype=np.uint8)
    motif_safe_arr[np.array(cutout_margin) > 0] = 0
    motif_safe_arr[outer_arr == 0] = 0
    motif_safe = Image.fromarray(motif_safe_arr)

    reserved_arr = outer_arr.copy()
    reserved_arr[np.array(motif_safe) > 0] = 0
    reserved_arr[outer_arr == 0] = 0

    return {
        "outer": outer,
        "cutouts": cutouts,
        "allowed": allowed,
        "edge_eroded": edge_eroded,
        "cutout_margin": cutout_margin,
        "motif_safe": motif_safe,
        "reserved": Image.fromarray(reserved_arr),
    }


def watercolor_base(size: tuple[int, int], allowed_mask: Image.Image) -> Image.Image:
    width, height = size
    rng = np.random.default_rng(42)
    blue = np.array([103, 166, 222], dtype=np.float32)
    pale = np.array([168, 209, 239], dtype=np.float32)
    medium = np.array([72, 134, 205], dtype=np.float32)

    noise = rng.normal(0.0, 1.0, (height // 52 + 2, width // 52 + 2))
    noise = np.array(Image.fromarray(noise).resize(size, Image.Resampling.BICUBIC))
    wash = np.clip(0.54 + 0.18 * noise, 0.18, 0.86)
    colors = pale[None, None, :] * wash[:, :, None] + blue[None, None, :] * (1 - wash[:, :, None])
    colors = colors * 0.88 + medium[None, None, :] * 0.12

    arr = np.zeros((height, width, 4), dtype=np.uint8)
    arr[:, :, :3] = np.clip(colors, 0, 255).astype(np.uint8)
    arr[:, :, 3] = np.array(allowed_mask)
    image = Image.fromarray(arr).filter(ImageFilter.GaussianBlur(0.7))

    wash_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(wash_layer, "RGBA")
    for _ in range(14):
        x = RNG.randint(170, width - 170)
        y = RNG.randint(130, height - 130)
        rx = RNG.randint(150, 360)
        ry = RNG.randint(70, 170)
        fill = RNG.choice(
            [
                (220, 239, 250, 24),
                (45, 103, 183, 18),
                (141, 190, 231, 22),
            ]
        )
        draw.ellipse((x - rx, y - ry, x + rx, y + ry), fill=fill)
    wash_layer.putalpha(Image.fromarray(np.minimum(np.array(wash_layer.getchannel("A")), np.array(allowed_mask))))
    image.alpha_composite(wash_layer)
    image.putalpha(allowed_mask)
    return image


def draw_polyline(
    image: Image.Image,
    points: list[tuple[float, float]],
    fill: tuple[int, int, int, int],
    width: int,
) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    int_points = [(int(round(x)), int(round(y))) for x, y in points]
    if len(int_points) > 1:
        draw.line(int_points, fill=fill, width=width)


def draw_jittered_outline(image: Image.Image, path: SvgPath) -> None:
    for width, alpha, offset in [(13, 92, (0, 0)), (7, 150, (1, -1)), (4, 205, (-1, 1))]:
        shifted = [(x + offset[0], y + offset[1]) for x, y in path.mapped_points]
        draw_polyline(image, shifted, (8, 55, 124, alpha), width)


def rounded(
    draw: ImageDraw.ImageDraw,
    bbox: tuple[int, int, int, int],
    radius: int,
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int] | None = None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline, width=width)


def mark_round_rect(mask_draw: ImageDraw.ImageDraw, bbox: tuple[int, int, int, int], radius: int) -> None:
    mask_draw.rounded_rectangle(bbox, radius=radius, fill=255)


def mark_ellipse(mask_draw: ImageDraw.ImageDraw, bbox: tuple[int, int, int, int]) -> None:
    mask_draw.ellipse(bbox, fill=255)


def motif_metrics(mask: Image.Image, masks: dict[str, Image.Image]) -> dict[str, int]:
    motif = np.array(mask) > 0
    outer = np.array(masks["outer"]) > 0
    cutouts = np.array(masks["cutouts"]) > 0
    safe = np.array(masks["motif_safe"]) > 0
    cutout_margin = np.array(masks["cutout_margin"]) > 0
    return {
        "mask_pixels": int(motif.sum()),
        "outside_outer_pixels": int(np.logical_and(motif, ~outer).sum()),
        "inside_cutout_pixels": int(np.logical_and(motif, cutouts).sum()),
        "inside_cutout_margin_pixels": int(np.logical_and(motif, cutout_margin).sum()),
        "outside_motif_safe_pixels": int(np.logical_and(motif, ~safe).sum()),
    }


def compose_group(
    art: Image.Image,
    motif_mask: Image.Image,
    masks: dict[str, Image.Image],
    size: tuple[int, int],
    name: str,
    pocket: str,
    bbox: tuple[int, int, int, int],
    draw_fn: Callable[[Image.Image, Image.Image], None],
) -> MotifGroup:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    local_mask = Image.new("L", size, 0)
    draw_fn(layer, local_mask)
    metrics = motif_metrics(local_mask, masks)
    if (
        metrics["outside_outer_pixels"]
        or metrics["inside_cutout_pixels"]
        or metrics["inside_cutout_margin_pixels"]
        or metrics["outside_motif_safe_pixels"]
    ):
        raise ValueError(f"Motif group {name!r} violates reserved geometry: {metrics}")
    art.alpha_composite(layer)
    motif_mask.paste(max_images(motif_mask, local_mask))
    return MotifGroup(name=name, pocket=pocket, bbox=bbox, metrics=metrics)


def draw_post_cluster(layer: Image.Image, mask: Image.Image) -> None:
    pocket = "upper-left tall bay above the left shoulder of the slot"
    del pocket
    draw = ImageDraw.Draw(layer, "RGBA")
    mdraw = ImageDraw.Draw(mask)
    navy = (13, 60, 124, 230)
    shadow = (8, 48, 105, 72)
    colors = [(241, 91, 88, 255), (247, 194, 61, 255), (88, 202, 185, 255)]
    xs = [462, 530, 584]
    heights = [116, 126, 106]
    for x, color, h in zip(xs, colors, heights):
        bbox = (x - 23, 148, x + 23, 148 + h)
        base = (x - 42, bbox[3] - 22, x + 42, bbox[3] + 38)
        rounded(draw, (base[0] + 4, base[1] + 7, base[2] + 4, base[3] + 7), 30, shadow)
        rounded(draw, base, 30, (19, 75, 146, 148), navy, 5)
        rounded(draw, bbox, 27, color, navy, 7)
        draw.ellipse((bbox[0] + 7, bbox[1] - 3, bbox[2] - 7, bbox[1] + 27), fill=(255, 255, 255, 76))
        draw.line((bbox[0] + 14, bbox[1] + 32, bbox[0] + 17, bbox[3] - 19), fill=(255, 255, 255, 70), width=5)
        mark_round_rect(mdraw, (base[0] - 2, base[1] - 2, base[2] + 2, base[3] + 9), 32)
        mark_round_rect(mdraw, (bbox[0] - 2, bbox[1] - 4, bbox[2] + 2, bbox[3] + 2), 29)
    rail = (438, 282, 604, 326)
    rounded(draw, (rail[0] + 5, rail[1] + 8, rail[2] + 5, rail[3] + 8), 24, shadow)
    rounded(draw, rail, 24, (121, 219, 205, 250), navy, 6)
    rounded(draw, (rail[0] + 15, rail[1] + 8, rail[2] - 16, rail[1] + 26), 12, (255, 255, 255, 70))
    mark_round_rect(mdraw, (rail[0] - 2, rail[1] - 2, rail[2] + 2, rail[3] + 8), 26)


def draw_slider_pair(layer: Image.Image, mask: Image.Image) -> None:
    draw = ImageDraw.Draw(layer, "RGBA")
    mdraw = ImageDraw.Draw(mask)
    navy = (13, 60, 124, 228)
    shadow = (8, 48, 105, 62)
    specs = [
        (715, [(360, (89, 202, 186, 255)), (575, (247, 194, 61, 255))]),
        (850, [(305, (241, 91, 88, 255)), (500, (92, 203, 187, 255)), (682, (247, 194, 61, 255))]),
    ]
    for y, knobs in specs:
        track = (250, y - 18, 735, y + 18)
        rounded(draw, (track[0] + 4, track[1] + 7, track[2] + 4, track[3] + 7), 17, shadow)
        rounded(draw, track, 17, (43, 105, 183, 138), navy, 5)
        rounded(draw, (track[0] + 22, y - 5, track[2] - 22, y + 5), 5, (204, 231, 249, 100))
        mark_round_rect(mdraw, (track[0] - 2, track[1] - 2, track[2] + 2, track[3] + 8), 19)
        for x, color in knobs:
            knob = (x - 26, y - 29, x + 26, y + 29)
            rounded(draw, (knob[0] + 4, knob[1] + 6, knob[2] + 4, knob[3] + 6), 14, shadow)
            rounded(draw, knob, 14, color, navy, 5)
            rounded(draw, (knob[0] + 8, knob[1] + 6, knob[2] - 8, knob[1] + 23), 8, (255, 255, 255, 70))
            mark_round_rect(mdraw, (knob[0] - 2, knob[1] - 2, knob[2] + 2, knob[3] + 6), 16)


def draw_lower_left_gauge(layer: Image.Image, mask: Image.Image) -> None:
    draw = ImageDraw.Draw(layer, "RGBA")
    mdraw = ImageDraw.Draw(mask)
    cx, cy, r = 468, 1276, 112
    navy = (12, 59, 124, 235)
    shadow = (8, 48, 105, 70)
    draw.ellipse((cx - r + 9, cy - r + 13, cx + r + 9, cy + r + 13), fill=shadow)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(34, 102, 181, 230), outline=navy, width=8)
    draw.ellipse((cx - r + 22, cy - r + 22, cx + r - 22, cy + r - 22), fill=(192, 226, 247, 255), outline=(19, 76, 145, 220), width=5)
    draw.arc((cx - r + 35, cy - r + 35, cx + r - 35, cy + r - 35), 205, 322, fill=(255, 255, 255, 120), width=7)
    for angle in [-128, -92, -56, -20, 18, 56]:
        rad = math.radians(angle)
        x0 = cx + int(math.cos(rad) * (r - 45))
        y0 = cy + int(math.sin(rad) * (r - 45))
        x1 = cx + int(math.cos(rad) * (r - 25))
        y1 = cy + int(math.sin(rad) * (r - 25))
        draw.line((x0, y0, x1, y1), fill=navy, width=5)
    needle = math.radians(32)
    draw.line((cx, cy, cx + int(math.cos(needle) * 62), cy + int(math.sin(needle) * 62)), fill=navy, width=7)
    draw.ellipse((cx - 12, cy - 12, cx + 12, cy + 12), fill=navy)
    mark_ellipse(mdraw, (cx - r - 2, cy - r - 2, cx + r + 11, cy + r + 15))


def draw_lower_middle_capsules(layer: Image.Image, mask: Image.Image) -> None:
    draw = ImageDraw.Draw(layer, "RGBA")
    mdraw = ImageDraw.Draw(mask)
    navy = (13, 60, 124, 230)
    shadow = (8, 48, 105, 70)
    capsules = [
        ((1018, 1156, 1290, 1242), (240, 91, 87, 255), "coral"),
        ((1055, 1290, 1282, 1366), (247, 194, 61, 255), "yellow"),
    ]
    for bbox, color, _name in capsules:
        radius = 34
        rounded(draw, (bbox[0] + 6, bbox[1] + 9, bbox[2] + 6, bbox[3] + 9), radius, shadow)
        rounded(draw, bbox, radius, color, navy, 7)
        rounded(draw, (bbox[0] + 22, bbox[1] + 12, bbox[2] - 22, bbox[1] + 38), 18, (255, 255, 255, 75))
        mark_round_rect(mdraw, (bbox[0] - 3, bbox[1] - 3, bbox[2] + 7, bbox[3] + 10), radius + 3)
    small = (1088, 1249, 1254, 1284)
    rounded(draw, small, 16, (114, 218, 204, 230), navy, 5)
    rounded(draw, (small[0] + 12, small[1] + 6, small[2] - 12, small[1] + 17), 8, (255, 255, 255, 65))
    mark_round_rect(mdraw, (small[0] - 2, small[1] - 2, small[2] + 2, small[3] + 3), 18)


def draw_dashed_polyline(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[float, float]],
    fill: tuple[int, int, int, int],
    width: int,
    dash: int = 26,
    gap: int = 15,
) -> None:
    carry = 0.0
    drawing = True
    for p0, p1 in zip(points, points[1:]):
        x0, y0 = p0
        x1, y1 = p1
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        if length == 0:
            continue
        unit_x, unit_y = dx / length, dy / length
        distance = 0.0
        while distance < length:
            segment_len = (dash if drawing else gap) - carry
            step = min(segment_len, length - distance)
            if drawing:
                a = (x0 + unit_x * distance, y0 + unit_y * distance)
                b = (x0 + unit_x * (distance + step), y0 + unit_y * (distance + step))
                draw.line((a, b), fill=fill, width=width)
            distance += step
            carry += step
            if (drawing and carry >= dash) or ((not drawing) and carry >= gap):
                drawing = not drawing
                carry = 0.0


def make_overlay(art: Image.Image, paths: list[SvgPath], size: tuple[int, int]) -> Image.Image:
    overlay = Image.new("RGBA", size, (255, 255, 255, 255))
    overlay.alpha_composite(art)
    draw = ImageDraw.Draw(overlay, "RGBA")
    draw_dashed_polyline(draw, paths[0].mapped_points, (255, 209, 35, 235), 6)
    for path in paths[1:]:
        draw_dashed_polyline(draw, path.mapped_points, (230, 23, 75, 235), 5)
    return overlay


def make_mask_debug(
    masks: dict[str, Image.Image],
    motif_mask: Image.Image,
    paths: list[SvgPath],
    groups: list[MotifGroup],
    size: tuple[int, int],
) -> Image.Image:
    debug = Image.new("RGBA", size, (255, 255, 255, 255))

    allowed_layer = Image.new("RGBA", size, (123, 181, 226, 0))
    allowed_layer.putalpha(Image.fromarray((np.array(masks["allowed"]) > 0).astype(np.uint8) * 95))
    debug.alpha_composite(allowed_layer)

    reserved_layer = Image.new("RGBA", size, (255, 187, 40, 0))
    reserved_layer.putalpha(Image.fromarray((np.array(masks["reserved"]) > 0).astype(np.uint8) * 115))
    debug.alpha_composite(reserved_layer)

    cutout_layer = Image.new("RGBA", size, (255, 80, 130, 0))
    cutout_layer.putalpha(Image.fromarray((np.array(masks["cutouts"]) > 0).astype(np.uint8) * 190))
    debug.alpha_composite(cutout_layer)

    motif_layer = Image.new("RGBA", size, (10, 54, 119, 0))
    motif_layer.putalpha(Image.fromarray((np.array(motif_mask) > 0).astype(np.uint8) * 185))
    debug.alpha_composite(motif_layer)

    draw = ImageDraw.Draw(debug, "RGBA")
    draw_dashed_polyline(draw, paths[0].mapped_points, (255, 209, 35, 245), 5)
    for path in paths[1:]:
        draw_dashed_polyline(draw, path.mapped_points, (230, 23, 75, 245), 5)
    for group in groups:
        draw.rectangle(group.bbox, outline=(6, 36, 92, 210), width=3)

    font = ImageFont.load_default()
    labels = [
        "blue: paintable body",
        "amber: reserved edge/cutout margin",
        "pink: internal SVG cutouts",
        "navy: accepted motif masks",
    ]
    y = 16
    for label in labels:
        draw.text((18, y), label, fill=(22, 38, 66, 230), font=font)
        y += 18
    return debug


def final_metrics(art: Image.Image, motif_mask: Image.Image, masks: dict[str, Image.Image]) -> dict[str, object]:
    alpha = np.array(art.getchannel("A")) > 0
    allowed = np.array(masks["allowed"]) > 0
    cutouts = np.array(masks["cutouts"]) > 0
    motif = np.array(motif_mask) > 0
    motif_safe = np.array(masks["motif_safe"]) > 0
    cutout_margin = np.array(masks["cutout_margin"]) > 0
    metrics = {
        "painted_pixel_metrics": {
            "outside_allowed_alpha_pixels": int(np.logical_and(alpha, ~allowed).sum()),
            "inside_internal_cutout_alpha_pixels": int(np.logical_and(alpha, cutouts).sum()),
            "focal_motif_pixels_inside_cutouts": int(np.logical_and(motif, cutouts).sum()),
            "focal_motif_pixels_in_cutout_margin": int(np.logical_and(motif, cutout_margin).sum()),
            "focal_motif_pixels_outside_motif_safe": int(np.logical_and(motif, ~motif_safe).sum()),
        }
    }
    gate = {
        "zero_alpha_outside_allowed": metrics["painted_pixel_metrics"]["outside_allowed_alpha_pixels"] == 0,
        "zero_alpha_inside_cutouts": metrics["painted_pixel_metrics"]["inside_internal_cutout_alpha_pixels"] == 0,
        "zero_focal_motifs_inside_cutouts": metrics["painted_pixel_metrics"]["focal_motif_pixels_inside_cutouts"] == 0,
        "zero_focal_motifs_in_cutout_margin": metrics["painted_pixel_metrics"]["focal_motif_pixels_in_cutout_margin"] == 0,
        "zero_focal_motifs_outside_motif_safe": metrics["painted_pixel_metrics"]["focal_motif_pixels_outside_motif_safe"] == 0,
    }
    gate["pass"] = all(gate.values())
    metrics["mechanical_gate"] = gate
    return metrics


def extract_reference_palette() -> dict[str, object]:
    sampled: list[np.ndarray] = []
    for ref in REF_PATHS:
        image = Image.open(ref).convert("RGB").resize((724, 241), Image.Resampling.LANCZOS)
        arr = np.array(image).reshape(-1, 3)
        non_white = arr[np.mean(arr, axis=1) < 244]
        sampled.append(non_white[:: max(1, len(non_white) // 4500)])
    pixels = np.vstack(sampled)
    rng = np.random.default_rng(42)
    centers = pixels[rng.choice(len(pixels), size=7, replace=False)].astype(np.float32)
    for _ in range(12):
        distances = np.stack([np.linalg.norm(pixels.astype(np.float32) - c, axis=1) for c in centers], axis=1)
        labels = np.argmin(distances, axis=1)
        for i in range(len(centers)):
            cluster = pixels[labels == i]
            if len(cluster):
                centers[i] = np.mean(cluster, axis=0)
    counts = np.bincount(labels, minlength=len(centers))
    order = np.argsort(-counts)
    return {
        "reference_files": [rel(p) for p in REF_PATHS],
        "observed_vocabulary": [
            "pale and medium blue watercolor panel body",
            "uneven dark navy hand-inked outline",
            "large rounded controls rather than dense tiny machinery",
            "coral, yellow, and mint accent controls",
            "glossy highlights and soft shadow pooling",
        ],
        "sampled_palette_hex": [
            "#%02x%02x%02x" % tuple(np.clip(np.round(centers[i]), 0, 255).astype(int))
            for i in order
        ],
    }


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text())
    viewbox = parse_viewbox(SVG_PATH)
    size = (int(round(viewbox[2])), int(round(viewbox[3])))
    paths, loaded_viewbox = load_svg_paths(size)
    masks = build_masks(size, paths)

    art = watercolor_base(size, masks["allowed"])
    draw_jittered_outline(art, paths[0])

    motif_mask = Image.new("L", size, 0)
    groups: list[MotifGroup] = []
    groups.append(
        compose_group(
            art,
            motif_mask,
            masks,
            size,
            "upper-left three-post control cluster",
            "upper-left tall bay above the left shoulder of the slot",
            (418, 126, 610, 336),
            draw_post_cluster,
        )
    )
    groups.append(
        compose_group(
            art,
            motif_mask,
            masks,
            size,
            "middle-left oversized two-row slider bank",
            "middle-left field below/left of the diagonal slot",
            (236, 666, 752, 895),
            draw_slider_pair,
        )
    )
    groups.append(
        compose_group(
            art,
            motif_mask,
            masks,
            size,
            "lower-left large friendly gauge",
            "lower-left base bay above the bottom notch",
            (336, 1148, 592, 1403),
            draw_lower_left_gauge,
        )
    )
    groups.append(
        compose_group(
            art,
            motif_mask,
            masks,
            size,
            "lower-middle two-capsule status module",
            "lower-middle bay between the bottom notch and the right cutouts",
            (1005, 1138, 1305, 1380),
            draw_lower_middle_capsules,
        )
    )

    art.putalpha(masks["allowed"])
    overlay = make_overlay(art, paths, size)
    debug = make_mask_debug(masks, motif_mask, paths, groups, size)

    ARTWORK_OUT.parent.mkdir(parents=True, exist_ok=True)
    art.save(ARTWORK_OUT)
    overlay.save(OVERLAY_OUT)
    debug.save(MASK_DEBUG_OUT)

    geometry_metrics = final_metrics(art, motif_mask, masks)
    metadata = {
        "candidate": "simple-full-panel",
        "hypothesis": "A full-panel attempt may work better with a quiet watercolor body and only 2-4 large friendly control motifs.",
        "method": "procedural contour-first proof; full paintable body watercolor, four motif groups checked against SVG-derived safe masks before final alpha guardrail",
        "source_svg": rel(SVG_PATH),
        "template_manifest": rel(MANIFEST_PATH),
        "geometry_report": rel(GEOMETRY_REPORT_PATH),
        "style_reference_extraction": extract_reference_palette(),
        "manifest_geometry_roles_used": manifest["geometry_roles"],
        "safe_pocket_plan": [
            {
                "name": "upper-left tall bay above the left shoulder of the slot",
                "used_for": "large three-post control cluster",
            },
            {
                "name": "middle-left field below/left of the diagonal slot",
                "used_for": "oversized two-row slider bank",
            },
            {
                "name": "lower-left base bay above the bottom notch",
                "used_for": "large friendly gauge",
            },
            {
                "name": "lower-middle bay between the bottom notch and the right cutouts",
                "used_for": "two-capsule status module with generous cutout clearance",
            },
            {
                "name": "right vertical strip between the diagonal slot and outer edge",
                "used_for": "not used; left quiet to avoid crowding the lower-right round cutout",
            },
        ],
        "no_focal_motif_zones": manifest["no_focal_motif_zones"],
        "motif_margin_policy": {
            "outer_edge_margin_px": EDGE_MARGIN_PX,
            "internal_cutout_margin_px": CUTOUT_MARGIN_PX,
            "path_1_path_2_paintable": False,
        },
        "motif_groups": [
            {
                "name": group.name,
                "pocket": group.pocket,
                "bbox": list(group.bbox),
                "metrics": group.metrics,
            }
            for group in groups
        ],
        "geometry_metrics": {
            "canvas_size": list(size),
            "viewbox": list(loaded_viewbox),
            "svg_path_bounds": [
                {"path_index": p.index, "role": p.role, "bounds": [round(v, 2) for v in p.bounds]}
                for p in paths
            ],
            "paintable_mask": {
                "outer_pixels": int((np.array(masks["outer"]) > 0).sum()),
                "cutout_pixels": int((np.array(masks["cutouts"]) > 0).sum()),
                "paintable_pixels": int((np.array(masks["allowed"]) > 0).sum()),
                "motif_safe_pixels": int((np.array(masks["motif_safe"]) > 0).sum()),
            },
            **geometry_metrics,
        },
        "outputs": {
            "artwork": rel(ARTWORK_OUT),
            "overlay": rel(OVERLAY_OUT),
            "mask_debug": rel(MASK_DEBUG_OUT),
            "metadata": rel(METADATA_OUT),
        },
        "workflow_notes": [
            "The base watercolor spans the full paintable material body only.",
            "Four large motif groups were composed inside named manifest pockets before final masking.",
            "The diagonal slot and lower-right round cutout were never treated as paintable regions.",
            "The right vertical strip was intentionally left quiet because the simplified test values clearance over coverage.",
        ],
    }
    METADATA_OUT.write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata["geometry_metrics"]["painted_pixel_metrics"], indent=2))
    print(json.dumps(metadata["geometry_metrics"]["mechanical_gate"], indent=2))


if __name__ == "__main__":
    main()
