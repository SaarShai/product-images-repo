#!/usr/bin/env python3
"""Micro-pocket style proof for the top-temp SVG template.

This intentionally avoids solving the full panel. It tests whether the
reference watercolor control-panel style becomes easier when only one simple
safe pocket carries focal motifs.
"""

from __future__ import annotations

import json
import math
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


TASK_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = Path(__file__).resolve().parents[4]
OUT_DIR = Path(__file__).resolve().parent

SVG_PATH = TASK_DIR / "source" / "template.svg"
MANIFEST_PATH = TASK_DIR / "template-manifest.json"
GEOMETRY_REPORT_PATH = TASK_DIR / "svg-geometry-report.md"
REF_PATHS = [
    TASK_DIR / "refs" / "ChatGPT Image Jun 9, 2026, 11_19_45 PM.png",
    TASK_DIR / "refs" / "ChatGPT Image Jun 9, 2026, 11_17_34 PM.png",
]

ARTWORK_PATH = OUT_DIR / "micro-pocket-style-artwork.png"
OVERLAY_PATH = OUT_DIR / "micro-pocket-style-overlay.png"
MASK_DEBUG_PATH = OUT_DIR / "micro-pocket-style-mask-debug.png"
METADATA_PATH = OUT_DIR / "micro-pocket-style-metadata.json"

COMMAND_RE = re.compile(
    r"([MmLlHhVvCcSsQqTtZz])|([-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?)"
)
RNG = random.Random(37)


@dataclass(frozen=True)
class SvgPath:
    index: int
    points: list[tuple[float, float]]
    role: str


@dataclass(frozen=True)
class MotifPlan:
    name: str
    pocket: str
    bbox: tuple[int, int, int, int]
    role: str


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


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
        (mt**3) * p0[0]
        + 3 * (mt**2) * t * p1[0]
        + 3 * mt * (t**2) * p2[0]
        + (t**3) * p3[0],
        (mt**3) * p0[1]
        + 3 * (mt**2) * t * p1[1]
        + 3 * mt * (t**2) * p2[1]
        + (t**3) * p3[1],
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


def parse_svg_path_points(d: str, curve_steps: int = 36) -> list[tuple[float, float]]:
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
            command = None
            last_cubic_ctrl = None
            last_quad_ctrl = None
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
                points.append(current)
                if first:
                    start = current
                    first = False
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
                p1 = (x1 + current[0], y1 + current[1]) if relative else (x1, y1)
                p2 = (x2 + current[0], y2 + current[1]) if relative else (x2, y2)
                p3 = (x + current[0], y + current[1]) if relative else (x, y)
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
                p1 = current
                if last_cubic_ctrl is not None:
                    p1 = (
                        current[0] + (current[0] - last_cubic_ctrl[0]),
                        current[1] + (current[1] - last_cubic_ctrl[1]),
                    )
                p2 = (x2 + current[0], y2 + current[1]) if relative else (x2, y2)
                p3 = (x + current[0], y + current[1]) if relative else (x, y)
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
                p1 = (x1 + current[0], y1 + current[1]) if relative else (x1, y1)
                p2 = (x + current[0], y + current[1]) if relative else (x, y)
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
                p1 = current
                if last_quad_ctrl is not None:
                    p1 = (
                        current[0] + (current[0] - last_quad_ctrl[0]),
                        current[1] + (current[1] - last_quad_ctrl[1]),
                    )
                p2 = (x + current[0], y + current[1]) if relative else (x, y)
                p0 = current
                for step in range(1, curve_steps + 1):
                    points.append(quad_point(p0, p1, p2, step / curve_steps))
                current = p2
                last_quad_ctrl = p1
                last_cubic_ctrl = None
            continue

        raise ValueError(f"Unsupported SVG path command: {cmd}")

    if points and points[0] != points[-1]:
        points.append(points[0])
    return points


def parse_viewbox(svg_path: Path) -> tuple[float, float, float, float]:
    root = ET.parse(svg_path).getroot()
    raw = root.attrib.get("viewBox")
    if not raw:
        raise ValueError("SVG has no viewBox")
    parts = [float(v) for v in raw.replace(",", " ").split()]
    if len(parts) != 4:
        raise ValueError(f"Unexpected viewBox: {raw}")
    return tuple(parts)  # type: ignore[return-value]


def load_svg_paths(size: tuple[int, int]) -> list[SvgPath]:
    del size
    root = ET.parse(SVG_PATH).getroot()
    ns = {"svg": "http://www.w3.org/2000/svg"}
    raw_paths = root.findall(".//svg:path", ns)
    roles = [
        "outer material contour",
        "large diagonal rounded slot keep-clear",
        "lower-right round/bolt-like keep-clear",
    ]
    return [
        SvgPath(
            index=i,
            points=parse_svg_path_points(path.attrib["d"]),
            role=roles[i] if i < len(roles) else "unclassified path",
        )
        for i, path in enumerate(raw_paths[:3])
    ]


def draw_polygon_mask(size: tuple[int, int], points: Iterable[tuple[float, float]]) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon([(round(x), round(y)) for x, y in points], fill=255)
    return mask


def count_nonzero(mask: Image.Image) -> int:
    return int(np.count_nonzero(np.asarray(mask)))


def erode(mask: Image.Image, pixels: int) -> Image.Image:
    return mask.filter(ImageFilter.MinFilter(pixels * 2 + 1))


def path_bounds(points: list[tuple[float, float]]) -> list[float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)]


def rounded(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    radius: int,
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int] | None = None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def build_masks(size: tuple[int, int], paths: list[SvgPath]) -> dict[str, Image.Image]:
    outer = draw_polygon_mask(size, paths[0].points)
    cutout_a = draw_polygon_mask(size, paths[1].points)
    cutout_b = draw_polygon_mask(size, paths[2].points)
    cutouts = ImageChops.lighter(cutout_a, cutout_b)
    paintable = ImageChops.subtract(outer, cutouts)
    motif_safe = erode(paintable, 28)
    return {
        "outer": outer,
        "cutouts": cutouts,
        "paintable": paintable,
        "motif_safe": motif_safe,
    }


def build_pocket_mask(size: tuple[int, int]) -> Image.Image:
    # Upper-left tall bay, narrowed so motifs sit away from the sloped outer edge
    # and the shoulder above the large diagonal slot.
    pocket = Image.new("L", size, 0)
    d = ImageDraw.Draw(pocket)
    d.rounded_rectangle((386, 92, 644, 380), radius=48, fill=255)
    return pocket


def make_watercolor_background(size: tuple[int, int], paintable_mask: Image.Image) -> Image.Image:
    width, height = size
    rng = np.random.default_rng(37)
    coarse = rng.normal(0, 1, (math.ceil(height / 42), math.ceil(width / 42)))
    fine = rng.normal(0, 1, (math.ceil(height / 16), math.ceil(width / 16)))
    coarse = Image.fromarray(np.uint8(((coarse - coarse.min()) / (np.ptp(coarse))) * 255)).resize(
        size, Image.Resampling.BICUBIC
    )
    fine = Image.fromarray(np.uint8(((fine - fine.min()) / (np.ptp(fine))) * 255)).resize(
        size, Image.Resampling.BICUBIC
    )
    coarse = coarse.filter(ImageFilter.GaussianBlur(13))
    fine = fine.filter(ImageFilter.GaussianBlur(4))
    c = np.asarray(coarse).astype(np.float32) / 255.0
    f = np.asarray(fine).astype(np.float32) / 255.0
    mix = np.clip(0.62 * c + 0.38 * f, 0, 1)

    pale = np.array([180, 220, 247], dtype=np.float32)
    mid = np.array([95, 166, 224], dtype=np.float32)
    deep = np.array([44, 103, 179], dtype=np.float32)
    rgb = pale * (1 - mix[..., None]) + mid * mix[..., None]
    rgb = rgb * 0.88 + deep * (0.12 * np.clip(mix[..., None] * 1.2, 0, 1))
    image = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).convert("RGBA")

    wash = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(wash, "RGBA")
    for _ in range(30):
        cx = RNG.randint(40, width - 60)
        cy = RNG.randint(40, height - 60)
        rx = RNG.randint(90, 260)
        ry = RNG.randint(40, 140)
        color = RNG.choice(
            [
                (218, 240, 255, 20),
                (54, 111, 190, 22),
                (129, 190, 232, 18),
            ]
        )
        d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=color)
    wash = wash.filter(ImageFilter.GaussianBlur(18))
    image = Image.alpha_composite(image, wash)
    image.putalpha(paintable_mask)
    return image


def draw_path_outline(
    layer: Image.Image,
    points: list[tuple[float, float]],
    color: tuple[int, int, int, int],
    width: int,
) -> None:
    d = ImageDraw.Draw(layer, "RGBA")
    coords = [(round(x), round(y)) for x, y in points]
    d.line(coords, fill=color, width=width, joint="curve")


def draw_edge_language(art: Image.Image, paths: list[SvgPath], paintable_mask: Image.Image) -> Image.Image:
    edge = Image.new("RGBA", art.size, (0, 0, 0, 0))
    draw_path_outline(edge, paths[0].points, (15, 68, 137, 210), 18)
    draw_path_outline(edge, paths[0].points, (221, 242, 255, 90), 5)
    for cutout in paths[1:]:
        draw_path_outline(edge, cutout.points, (15, 68, 137, 185), 14)
        draw_path_outline(edge, cutout.points, (230, 246, 255, 85), 4)
    edge.putalpha(ImageChops.multiply(edge.getchannel("A"), paintable_mask))
    return Image.alpha_composite(art, edge)


def draw_gauge(layer: Image.Image, mask: Image.Image | None = None) -> MotifPlan:
    pocket = "upper-left tall bay above the left shoulder of the slot"
    bbox = (434, 126, 582, 274)
    if mask is not None:
        d = ImageDraw.Draw(mask)
        d.ellipse((424, 118, 592, 290), fill=255)
        return MotifPlan("single rounded gauge", pocket, bbox, "round gauge/dial")

    d = ImageDraw.Draw(layer, "RGBA")
    cx, cy, r = 508, 200, 70
    d.ellipse((cx - r - 8, cy - r + 10, cx + r + 8, cy + r + 25), fill=(8, 52, 112, 82))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(20, 76, 150, 240))
    d.ellipse((cx - r + 20, cy - r + 20, cx + r - 20, cy + r - 20), fill=(220, 242, 255, 245))
    d.arc((cx - r + 32, cy - r + 32, cx + r - 32, cy + r - 32), 205, 335, fill=(51, 107, 178, 255), width=8)
    for angle in range(-115, 116, 38):
        rad = math.radians(angle)
        x0 = cx + math.cos(rad) * (r - 38)
        y0 = cy + math.sin(rad) * (r - 38)
        x1 = cx + math.cos(rad) * (r - 22)
        y1 = cy + math.sin(rad) * (r - 22)
        d.line((x0, y0, x1, y1), fill=(16, 70, 141, 230), width=5)
    needle = math.radians(32)
    d.line((cx, cy, cx + math.cos(needle) * 50, cy + math.sin(needle) * 50), fill=(18, 67, 132, 255), width=7)
    d.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), fill=(250, 192, 62, 255))
    d.ellipse((cx - 56, cy - 58, cx - 15, cy - 33), fill=(255, 255, 255, 118))
    d.arc((cx - r + 9, cy - r + 8, cx + r - 10, cy + r - 12), 207, 303, fill=(255, 255, 255, 88), width=5)
    return MotifPlan("single rounded gauge", pocket, bbox, "round gauge/dial")


def draw_capsule_stack(layer: Image.Image, mask: Image.Image | None = None) -> MotifPlan:
    pocket = "upper-left tall bay above the left shoulder of the slot"
    bbox = (428, 290, 606, 358)
    rows = [
        ((428, 290, 592, 317), (255, 102, 91, 255)),
        ((444, 328, 606, 356), (92, 204, 183, 255)),
    ]
    if mask is not None:
        d = ImageDraw.Draw(mask)
        for box, _ in rows:
            x0, y0, x1, y1 = box
            d.rounded_rectangle((x0 - 8, y0 - 6, x1 + 8, y1 + 14), radius=15, fill=255)
        return MotifPlan("two capsule buttons", pocket, bbox, "stacked capsule buttons")

    d = ImageDraw.Draw(layer, "RGBA")
    for box, color in rows:
        x0, y0, x1, y1 = box
        rounded(d, (x0 + 4, y0 + 8, x1 + 4, y1 + 13), 14, (8, 52, 112, 78))
        rounded(d, box, 14, (18, 72, 144, 245))
        rounded(d, (x0 + 8, y0 + 5, x1 - 8, y1 - 5), 11, color, (14, 67, 132, 220), 3)
        rounded(d, (x0 + 24, y0 + 8, x1 - 34, y0 + 15), 6, (255, 255, 255, 82))
    return MotifPlan("two capsule buttons", pocket, bbox, "stacked capsule buttons")


def draw_bolt_pair(layer: Image.Image, mask: Image.Image | None = None) -> MotifPlan:
    pocket = "upper-left tall bay above the left shoulder of the slot"
    bbox = (425, 122, 606, 174)
    centers = [(442, 148), (588, 150)]
    if mask is not None:
        d = ImageDraw.Draw(mask)
        for cx, cy in centers:
            d.ellipse((cx - 23, cy - 22, cx + 23, cy + 25), fill=255)
        return MotifPlan("small bolt pair", pocket, bbox, "corner screw heads")

    d = ImageDraw.Draw(layer, "RGBA")
    for cx, cy in centers:
        d.ellipse((cx - 20, cy - 16, cx + 20, cy + 24), fill=(8, 51, 110, 75))
        d.ellipse((cx - 18, cy - 18, cx + 18, cy + 18), fill=(22, 76, 150, 238))
        d.ellipse((cx - 12, cy - 12, cx + 12, cy + 12), fill=(219, 242, 255, 250))
        d.line((cx - 8, cy + 6, cx + 8, cy - 6), fill=(67, 127, 196, 255), width=4)
        d.ellipse((cx - 9, cy - 10, cx - 2, cy - 4), fill=(255, 255, 255, 130))
    return MotifPlan("small bolt pair", pocket, bbox, "corner screw heads")


def evaluate_motif(mask: Image.Image, masks: dict[str, Image.Image]) -> dict[str, int | list[int] | None]:
    outside_outer = ImageChops.subtract(mask, masks["outer"])
    inside_cutouts = ImageChops.multiply(mask, masks["cutouts"])
    outside_motif_safe = ImageChops.subtract(mask, masks["motif_safe"])
    return {
        "mask_pixels": count_nonzero(mask),
        "outside_outer_pixels": count_nonzero(outside_outer),
        "inside_cutout_pixels": count_nonzero(inside_cutouts),
        "outside_eroded_paintable_pixels": count_nonzero(outside_motif_safe),
        "bbox": list(mask.getbbox()) if mask.getbbox() else None,
    }


def apply_layer_if_safe(
    art: Image.Image,
    masks: dict[str, Image.Image],
    draw_fn,
    motif_records: list[dict[str, object]],
    combined_motif_mask: Image.Image,
) -> Image.Image:
    motif_mask = Image.new("L", art.size, 0)
    plan = draw_fn(Image.new("RGBA", art.size, (0, 0, 0, 0)), motif_mask)
    metrics = evaluate_motif(motif_mask, masks)
    accepted = (
        metrics["mask_pixels"] > 0
        and metrics["outside_outer_pixels"] == 0
        and metrics["inside_cutout_pixels"] == 0
        and metrics["outside_eroded_paintable_pixels"] == 0
    )
    motif_records.append(
        {
            "name": plan.name,
            "pocket": plan.pocket,
            "role": plan.role,
            "bbox": list(plan.bbox),
            "accepted": accepted,
            **metrics,
        }
    )
    if not accepted:
        return art
    layer = Image.new("RGBA", art.size, (0, 0, 0, 0))
    draw_fn(layer, None)
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), masks["paintable"]))
    combined_motif_mask.paste(ImageChops.lighter(combined_motif_mask, motif_mask))
    return Image.alpha_composite(art, layer.filter(ImageFilter.GaussianBlur(0.18)))


def make_overlay(
    size: tuple[int, int],
    art: Image.Image,
    paths: list[SvgPath],
    pocket_mask: Image.Image,
) -> Image.Image:
    overlay = Image.new("RGBA", size, (255, 255, 255, 255))
    overlay = Image.alpha_composite(overlay, art)
    green_alpha = pocket_mask.point(lambda p: 46 if p else 0)
    overlay.alpha_composite(
        Image.merge(
            "RGBA",
            (
                Image.new("L", size, 65),
                Image.new("L", size, 217),
                Image.new("L", size, 122),
                green_alpha,
            ),
        )
    )
    draw_path_outline(overlay, paths[0].points, (255, 219, 85, 255), 7)
    for cutout in paths[1:]:
        draw_path_outline(overlay, cutout.points, (255, 70, 70, 235), 7)
    d = ImageDraw.Draw(overlay, "RGBA")
    d.rounded_rectangle((386, 92, 644, 380), 48, outline=(35, 167, 92, 230), width=5)
    d.text((34, 28), "micro pocket proof: upper-left tall bay only", fill=(0, 0, 0, 220))
    d.text((34, 58), "yellow=outer contour, red=cutouts, green=selected pocket", fill=(0, 0, 0, 190))
    return overlay


def make_debug(
    size: tuple[int, int],
    masks: dict[str, Image.Image],
    pocket_mask: Image.Image,
    combined_motif_mask: Image.Image,
) -> Image.Image:
    debug = Image.new("RGBA", size, (248, 248, 248, 255))
    debug.alpha_composite(
        Image.merge(
            "RGBA",
            (
                Image.new("L", size, 92),
                Image.new("L", size, 174),
                Image.new("L", size, 235),
                masks["paintable"].point(lambda p: 150 if p else 0),
            ),
        )
    )
    debug.alpha_composite(
        Image.merge(
            "RGBA",
            (
                Image.new("L", size, 255),
                Image.new("L", size, 70),
                Image.new("L", size, 70),
                masks["cutouts"].point(lambda p: 180 if p else 0),
            ),
        )
    )
    debug.alpha_composite(
        Image.merge(
            "RGBA",
            (
                Image.new("L", size, 50),
                Image.new("L", size, 220),
                Image.new("L", size, 120),
                pocket_mask.point(lambda p: 112 if p else 0),
            ),
        )
    )
    debug.alpha_composite(
        Image.merge(
            "RGBA",
            (
                Image.new("L", size, 0),
                Image.new("L", size, 0),
                Image.new("L", size, 0),
                combined_motif_mask.point(lambda p: 185 if p else 0),
            ),
        )
    )
    d = ImageDraw.Draw(debug, "RGBA")
    d.text(
        (34, 28),
        "blue=paintable, red=cutouts, green=selected pocket, black=accepted motif masks",
        fill=(0, 0, 0, 220),
    )
    return debug


def sample_reference_palette() -> list[str]:
    samples: list[np.ndarray] = []
    for path in REF_PATHS:
        image = Image.open(path).convert("RGB").resize((640, 213), Image.Resampling.LANCZOS)
        flat = np.asarray(image).reshape(-1, 3)
        nonwhite = flat[np.mean(flat, axis=1) < 244]
        if len(nonwhite):
            samples.append(nonwhite[:: max(1, len(nonwhite) // 3000)])
    pixels = np.vstack(samples)
    rng = np.random.default_rng(37)
    centers = pixels[rng.choice(len(pixels), size=7, replace=False)].astype(np.float32)
    for _ in range(14):
        distances = np.stack(
            [np.linalg.norm(pixels.astype(np.float32) - center, axis=1) for center in centers],
            axis=1,
        )
        labels = np.argmin(distances, axis=1)
        for idx in range(len(centers)):
            cluster = pixels[labels == idx]
            if len(cluster):
                centers[idx] = cluster.mean(axis=0)
    counts = np.bincount(labels, minlength=len(centers))
    return [
        "#%02x%02x%02x" % tuple(np.clip(np.round(centers[i]), 0, 255).astype(int))
        for i in np.argsort(-counts)
    ]


def make_outputs() -> dict[str, object]:
    manifest = json.loads(MANIFEST_PATH.read_text())
    viewbox = parse_viewbox(SVG_PATH)
    _, _, vb_width, vb_height = viewbox
    size = (math.ceil(vb_width), math.ceil(vb_height))
    paths = load_svg_paths(size)
    masks = build_masks(size, paths)
    pocket_mask = build_pocket_mask(size)
    pocket_safe_mask = ImageChops.multiply(pocket_mask, masks["motif_safe"])

    art = make_watercolor_background(size, masks["paintable"])
    art = draw_edge_language(art, paths, masks["paintable"])

    motif_records: list[dict[str, object]] = []
    combined_motif_mask = Image.new("L", size, 0)
    for draw_fn in (draw_bolt_pair, draw_gauge, draw_capsule_stack):
        art = apply_layer_if_safe(art, masks, draw_fn, motif_records, combined_motif_mask)

    final_alpha = ImageChops.multiply(art.getchannel("A"), masks["paintable"])
    art.putalpha(final_alpha)

    outside_final = ImageChops.subtract(art.getchannel("A"), masks["paintable"])
    cutout_final = ImageChops.multiply(art.getchannel("A"), masks["cutouts"])
    motif_outside_outer = ImageChops.subtract(combined_motif_mask, masks["outer"])
    motif_in_cutouts = ImageChops.multiply(combined_motif_mask, masks["cutouts"])
    motif_outside_pocket = ImageChops.subtract(combined_motif_mask, pocket_mask)

    metadata = {
        "workflow": "micro-pocket-style-proof",
        "hypothesis": "Reference style may be easier to learn when only one simple SVG-safe pocket carries focal motifs.",
        "source_svg": rel(SVG_PATH),
        "template_manifest": rel(MANIFEST_PATH),
        "geometry_report": rel(GEOMETRY_REPORT_PATH),
        "style_refs": [rel(path) for path in REF_PATHS],
        "manifest_status": manifest.get("status"),
        "canvas_size_px": list(size),
        "viewbox": list(viewbox),
        "path_roles": {f"path[{p.index}]": p.role for p in paths},
        "path_bounds": {f"path[{p.index}]": path_bounds(p.points) for p in paths},
        "selected_pocket": {
            "name": "upper-left tall bay above the left shoulder of the slot",
            "pocket_mask_bbox": list(pocket_mask.getbbox()),
            "reason": "It is a tall, relatively simple pocket far from path[1] diagonal slot and path[2] round cutout.",
            "full_panel_treatment": "quiet pale blue watercolor wash outside the selected pocket",
        },
        "style_vocabulary_tested": [
            "round blue-white gauge with navy rim, ticks, needle, and white highlight",
            "small screw/bolt heads with diagonal slot highlights",
            "rounded coral and mint capsule buttons with navy edging and glossy highlight",
            "pale blue watercolor paper texture with soft navy edge pooling",
        ],
        "sampled_reference_palette_hex": sample_reference_palette(),
        "motif_margin_px": 28,
        "mask_pixels": {
            "outer": count_nonzero(masks["outer"]),
            "cutouts": count_nonzero(masks["cutouts"]),
            "paintable": count_nonzero(masks["paintable"]),
            "motif_safe": count_nonzero(masks["motif_safe"]),
            "selected_pocket": count_nonzero(pocket_mask),
            "selected_pocket_inside_motif_safe": count_nonzero(pocket_safe_mask),
            "combined_motifs": count_nonzero(combined_motif_mask),
        },
        "decorative_motifs": motif_records,
        "summary": {
            "planned_motifs": len(motif_records),
            "accepted_motifs": sum(1 for item in motif_records if item["accepted"]),
            "rejected_motifs": sum(1 for item in motif_records if not item["accepted"]),
            "final_outside_paintable_alpha_pixels": count_nonzero(outside_final),
            "final_cutout_alpha_pixels": count_nonzero(cutout_final),
            "decorative_motif_pixels_outside_outer": count_nonzero(motif_outside_outer),
            "decorative_motif_pixels_inside_cutouts": count_nonzero(motif_in_cutouts),
            "decorative_motif_pixels_outside_selected_pocket_mask": count_nonzero(motif_outside_pocket),
            "mechanical_gate_pass": all(item["accepted"] for item in motif_records)
            and count_nonzero(outside_final) == 0
            and count_nonzero(cutout_final) == 0
            and count_nonzero(motif_outside_outer) == 0
            and count_nonzero(motif_in_cutouts) == 0
            and count_nonzero(motif_outside_pocket) == 0,
        },
        "outputs": {
            "artwork": ARTWORK_PATH.name,
            "overlay": OVERLAY_PATH.name,
            "mask_debug": MASK_DEBUG_PATH.name,
            "metadata": METADATA_PATH.name,
        },
        "method_notes": [
            "Only the selected pocket receives focal control motifs.",
            "All motifs were checked against the SVG-derived outer contour, cutout mask, and eroded paintable mask before drawing.",
            "The final alpha mask is used only as the export guardrail after pre-checked motif placement.",
        ],
    }

    ARTWORK_PATH.parent.mkdir(parents=True, exist_ok=True)
    art.save(ARTWORK_PATH)
    make_overlay(size, art, paths, pocket_mask).save(OVERLAY_PATH)
    make_debug(size, masks, pocket_mask, combined_motif_mask).save(MASK_DEBUG_PATH)
    METADATA_PATH.write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def main() -> None:
    metadata = make_outputs()
    print(json.dumps(metadata["summary"], indent=2))


if __name__ == "__main__":
    main()
