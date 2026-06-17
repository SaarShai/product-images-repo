#!/usr/bin/env python3
"""Reference-first procedural proof for the top-temp SVG template.

The script uses the SVG paths as geometry, then places a small vocabulary of
watercolor control-panel motifs only in named safe pockets. The final alpha mask
is an export guardrail; focal motifs are checked against the cutout/edge margins
before the guardrail is applied.
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

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "tasks" / "top-temp-workflow-test"
OUT_DIR = TASK / "agents" / "reference-first"
SVG_PATH = TASK / "source" / "template.svg"
MANIFEST_PATH = TASK / "template-manifest.json"
GEOMETRY_REPORT_PATH = TASK / "svg-geometry-report.md"
REF_PATHS = [
    TASK / "refs" / "ChatGPT Image Jun 9, 2026, 11_19_45 PM.png",
    TASK / "refs" / "ChatGPT Image Jun 9, 2026, 11_17_34 PM.png",
]

ARTWORK_OUT = OUT_DIR / "reference-first-artwork.png"
OVERLAY_OUT = OUT_DIR / "reference-first-overlay.png"
MASK_DEBUG_OUT = OUT_DIR / "reference-first-mask-debug.png"
METADATA_OUT = OUT_DIR / "reference-first-metadata.json"

RNG = random.Random(16)


@dataclass(frozen=True)
class SvgPath:
    index: int
    d: str
    points: list[tuple[float, float]]
    mapped_points: list[tuple[float, float]]
    bounds: tuple[float, float, float, float]
    role: str


@dataclass(frozen=True)
class Motif:
    name: str
    pocket: str
    bbox: tuple[int, int, int, int]


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


COMMAND_RE = re.compile(
    r"([MmLlHhVvCcSsQqTtZz])|([-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?)"
)


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


def cubic_point(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    mt = 1.0 - t
    x = (
        (mt**3) * p0[0]
        + 3 * (mt**2) * t * p1[0]
        + 3 * mt * (t**2) * p2[0]
        + (t**3) * p3[0]
    )
    y = (
        (mt**3) * p0[1]
        + 3 * (mt**2) * t * p1[1]
        + 3 * mt * (t**2) * p2[1]
        + (t**3) * p3[1]
    )
    return x, y


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


def read_number(tokens: list[str | float], pos: int) -> tuple[float, int]:
    if pos >= len(tokens) or is_command(tokens[pos]):
        raise ValueError(f"Expected number at token {pos}")
    return float(tokens[pos]), pos + 1


def parse_svg_path_points(d: str, curve_steps: int = 32) -> list[tuple[float, float]]:
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
                    points.append(current)
                    first = False
                else:
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
                if last_cubic_ctrl is None:
                    p1 = current
                else:
                    p1 = (
                        current[0] + (current[0] - last_cubic_ctrl[0]),
                        current[1] + (current[1] - last_cubic_ctrl[1]),
                    )
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
                if last_quad_ctrl is None:
                    p1 = current
                else:
                    p1 = (
                        current[0] + (current[0] - last_quad_ctrl[0]),
                        current[1] + (current[1] - last_quad_ctrl[1]),
                    )
                if relative:
                    p2 = (current[0] + x, current[1] + y)
                else:
                    p2 = (x, y)
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


def load_svg_paths(size: tuple[int, int]) -> list[SvgPath]:
    viewbox = parse_viewbox(SVG_PATH)
    root = ET.parse(SVG_PATH).getroot()
    ns = {"svg": "http://www.w3.org/2000/svg"}
    raw_paths = root.findall(".//svg:path", ns)
    roles = [
        "outer material contour",
        "large diagonal rounded slot keep-clear",
        "lower-right round/bolt-like keep-clear",
    ]
    result: list[SvgPath] = []
    for i, path_el in enumerate(raw_paths):
        d = path_el.attrib["d"]
        points = parse_svg_path_points(d)
        mapped = map_points(points, viewbox, size)
        result.append(
            SvgPath(
                index=i,
                d=d,
                points=points,
                mapped_points=mapped,
                bounds=path_bounds(points),
                role=roles[i] if i < len(roles) else "unclassified path",
            )
        )
    return result


def polygon_mask(size: tuple[int, int], paths: list[SvgPath]) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for path in paths:
        draw.polygon(path.mapped_points, fill=255)
    return mask


def build_masks(size: tuple[int, int], paths: list[SvgPath]) -> dict[str, Image.Image]:
    outer = polygon_mask(size, [paths[0]])
    cutouts = polygon_mask(size, paths[1:])
    allowed = Image.new("L", size, 0)
    allowed_arr = np.array(outer, dtype=np.uint8)
    cut_arr = np.array(cutouts, dtype=np.uint8)
    allowed_arr[cut_arr > 0] = 0
    allowed = Image.fromarray(allowed_arr, mode="L")

    cutout_margin_arr = cv2.dilate(
        cut_arr,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (35, 35)),
        iterations=1,
    )
    outer_arr = np.array(outer, dtype=np.uint8)
    eroded_outer = cv2.erode(
        outer_arr,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (29, 29)),
        iterations=1,
    )
    edge_margin_arr = cv2.subtract(outer_arr, eroded_outer)
    forbidden_arr = np.maximum(cutout_margin_arr, edge_margin_arr)
    forbidden_arr[outer_arr == 0] = 0

    return {
        "outer": outer,
        "cutouts": cutouts,
        "allowed": allowed,
        "cutout_margin": Image.fromarray(cutout_margin_arr, mode="L"),
        "edge_margin": Image.fromarray(edge_margin_arr, mode="L"),
        "forbidden": Image.fromarray(forbidden_arr, mode="L"),
    }


def color_distance(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.linalg.norm(a.astype(np.float32) - b.astype(np.float32), axis=1)


def extract_reference_palette() -> dict[str, object]:
    sampled: list[np.ndarray] = []
    for ref in REF_PATHS:
        image = Image.open(ref).convert("RGB").resize((724, 241), Image.Resampling.LANCZOS)
        arr = np.array(image)
        flat = arr.reshape(-1, 3)
        non_white = flat[np.mean(flat, axis=1) < 244]
        sampled.append(non_white[:: max(1, len(non_white) // 6000)])
    pixels = np.vstack(sampled)

    # Fixed seed k-means, used only to document palette evidence from the refs.
    rng = np.random.default_rng(16)
    centers = pixels[rng.choice(len(pixels), size=8, replace=False)].astype(np.float32)
    for _ in range(16):
        distances = np.stack([color_distance(pixels, c) for c in centers], axis=1)
        labels = np.argmin(distances, axis=1)
        for i in range(len(centers)):
            cluster = pixels[labels == i]
            if len(cluster):
                centers[i] = np.mean(cluster, axis=0)
    counts = np.bincount(labels, minlength=len(centers))
    order = np.argsort(-counts)
    hexes = [
        "#%02x%02x%02x" % tuple(np.clip(np.round(centers[i]), 0, 255).astype(int))
        for i in order
    ]

    return {
        "reference_files": [rel(p) for p in REF_PATHS],
        "observed_vocabulary": [
            "blue watercolor material body",
            "dark navy hand-inked outlines and rims",
            "rounded controls with glossy white highlights",
            "coral, yellow, and mint accent controls",
            "sparse sliders, dials, buttons, screws, and tick marks",
            "simple rounded shapes with soft shadow pooling",
        ],
        "sampled_palette_hex": hexes,
    }


def watercolor_base(size: tuple[int, int], allowed_mask: Image.Image) -> Image.Image:
    width, height = size
    rng = np.random.default_rng(16)
    base = np.zeros((height, width, 4), dtype=np.uint8)
    blue = np.array([101, 160, 218], dtype=np.float32)
    light = np.array([150, 197, 235], dtype=np.float32)
    deep = np.array([38, 93, 164], dtype=np.float32)

    noise_large = rng.normal(0.0, 1.0, (height // 12 + 2, width // 12 + 2))
    noise_large = cv2.resize(noise_large, (width, height), interpolation=cv2.INTER_CUBIC)
    noise_small = rng.normal(0.0, 1.0, (height // 38 + 2, width // 38 + 2))
    noise_small = cv2.resize(noise_small, (width, height), interpolation=cv2.INTER_CUBIC)
    mix = np.clip(0.55 + 0.16 * noise_large + 0.09 * noise_small, 0.18, 0.90)
    colors = light[None, None, :] * mix[:, :, None] + blue[None, None, :] * (
        1 - mix[:, :, None]
    )
    dark_wash = np.clip((noise_large + 1.2) / 2.6, 0, 1)
    colors = colors * (1 - 0.20 * dark_wash[:, :, None]) + deep[None, None, :] * (
        0.20 * dark_wash[:, :, None]
    )
    base[:, :, :3] = np.clip(colors, 0, 255).astype(np.uint8)
    base[:, :, 3] = np.array(allowed_mask)

    image = Image.fromarray(base, mode="RGBA").filter(ImageFilter.GaussianBlur(0.55))
    draw = ImageDraw.Draw(image, "RGBA")
    # Broad translucent washes, clipped to material alpha below.
    for _ in range(42):
        x = RNG.randint(40, width - 80)
        y = RNG.randint(20, height - 80)
        rx = RNG.randint(90, 310)
        ry = RNG.randint(35, 140)
        fill = RNG.choice(
            [
                (174, 211, 241, 28),
                (44, 93, 166, 24),
                (87, 147, 211, 20),
                (211, 232, 248, 22),
            ]
        )
        draw.ellipse((x - rx, y - ry, x + rx, y + ry), fill=fill)
    image.putalpha(allowed_mask)
    return image


def draw_path_stroke(
    layer: Image.Image,
    points: list[tuple[float, float]],
    fill: tuple[int, int, int, int],
    width: int,
    joint: str = "curve",
) -> None:
    draw = ImageDraw.Draw(layer, "RGBA")
    int_points = [(int(round(x)), int(round(y))) for x, y in points]
    if len(int_points) > 1:
        draw.line(int_points, fill=fill, width=width, joint=joint)


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


def draw_glossy_button(
    art: Image.Image,
    motif_mask: Image.Image,
    bbox: tuple[int, int, int, int],
    fill: tuple[int, int, int, int],
    pocket: str,
    name: str,
    motifs: list[Motif],
    radius: int | None = None,
) -> None:
    x0, y0, x1, y1 = bbox
    r = radius if radius is not None else max(8, min(x1 - x0, y1 - y0) // 3)
    shadow = (8, 55, 112, 78)
    navy = (18, 68, 130, 230)
    draw = ImageDraw.Draw(art, "RGBA")
    mdraw = ImageDraw.Draw(motif_mask)
    rounded(draw, (x0 + 5, y0 + 8, x1 + 5, y1 + 8), r, shadow)
    rounded(draw, bbox, r, fill, navy, 6)
    rounded(
        draw,
        (x0 + 13, y0 + 9, x1 - 13, y0 + max(18, (y1 - y0) // 2)),
        max(6, r - 7),
        (255, 255, 255, 62),
    )
    draw.arc((x0 + 10, y0 + 7, x1 - 10, y1 - 8), 205, 310, fill=(255, 255, 255, 115), width=5)
    mark_round_rect(mdraw, (x0 - 1, y0 - 1, x1 + 1, y1 + 1), r + 2)
    motifs.append(Motif(name=name, pocket=pocket, bbox=bbox))


def draw_cylinder(
    art: Image.Image,
    motif_mask: Image.Image,
    center: tuple[int, int],
    size: tuple[int, int],
    fill: tuple[int, int, int, int],
    pocket: str,
    name: str,
    motifs: list[Motif],
) -> None:
    cx, cy = center
    w, h = size
    bbox = (cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2)
    base = (bbox[0] - 15, bbox[3] - 15, bbox[2] + 15, bbox[3] + 32)
    draw = ImageDraw.Draw(art, "RGBA")
    mdraw = ImageDraw.Draw(motif_mask)
    rounded(draw, base, 25, (13, 67, 137, 118), (18, 67, 128, 170), 4)
    rounded(draw, bbox, w // 2, fill, (17, 67, 130, 230), 7)
    draw.ellipse((bbox[0] + 4, bbox[1] - 2, bbox[2] - 4, bbox[1] + 24), fill=(255, 255, 255, 64))
    draw.line((bbox[0] + 16, bbox[1] + 24, bbox[0] + 18, bbox[3] - 18), fill=(255, 255, 255, 85), width=5)
    mark_round_rect(mdraw, (bbox[0] - 2, bbox[1] - 2, bbox[2] + 2, bbox[3] + 34), 26)
    motifs.append(Motif(name=name, pocket=pocket, bbox=(bbox[0], bbox[1], bbox[2], bbox[3] + 34)))


def draw_slider_bank(
    art: Image.Image,
    motif_mask: Image.Image,
    motifs: list[Motif],
) -> None:
    pocket = "middle-left field below/left of the diagonal slot"
    draw = ImageDraw.Draw(art, "RGBA")
    mdraw = ImageDraw.Draw(motif_mask)
    ys = [715, 782, 850, 918]
    knob_specs = [
        [(305, (91, 206, 189, 255)), (505, (250, 195, 66, 255))],
        [(405, (87, 206, 187, 255)), (615, (244, 95, 91, 255))],
        [(270, (245, 93, 90, 255)), (480, (246, 191, 65, 255)), (685, (92, 207, 189, 255))],
        [(382, (250, 195, 64, 255)), (612, (91, 205, 188, 255))],
    ]
    for row, y in enumerate(ys):
        x0, x1 = 238, 720
        rounded(draw, (x0, y - 10, x1, y + 11), 10, (37, 102, 181, 125), (18, 65, 128, 190), 4)
        rounded(draw, (x0 + 18, y - 4, x1 - 18, y + 4), 4, (180, 218, 244, 105))
        mdraw.rounded_rectangle((x0 - 4, y - 14, x1 + 4, y + 15), radius=12, fill=255)
        motifs.append(Motif(name=f"rounded slider track {row + 1}", pocket=pocket, bbox=(x0, y - 12, x1, y + 13)))
        for x, color in knob_specs[row]:
            bbox = (x - 18, y - 20, x + 18, y + 20)
            draw_glossy_button(
                art,
                motif_mask,
                bbox,
                color,
                pocket,
                f"small glossy slider knob {row + 1}",
                motifs,
                radius=8,
            )


def draw_dial(
    art: Image.Image,
    motif_mask: Image.Image,
    center: tuple[int, int],
    radius: int,
    pocket: str,
    name: str,
    motifs: list[Motif],
) -> None:
    cx, cy = center
    draw = ImageDraw.Draw(art, "RGBA")
    mdraw = ImageDraw.Draw(motif_mask)
    bbox_shadow = (cx - radius - 12, cy - radius - 4, cx + radius + 12, cy + radius + 20)
    draw.ellipse(bbox_shadow, fill=(12, 65, 128, 80))
    bbox = (cx - radius, cy - radius, cx + radius, cy + radius)
    draw.ellipse(bbox, fill=(190, 220, 242, 255), outline=(16, 65, 130, 235), width=10)
    draw.ellipse((cx - radius + 18, cy - radius + 18, cx + radius - 18, cy + radius - 18), outline=(35, 92, 166, 170), width=5)
    for deg in range(0, 360, 45):
        a = math.radians(deg - 90)
        r0 = radius - 27
        r1 = radius - 10
        draw.line(
            (
                cx + math.cos(a) * r0,
                cy + math.sin(a) * r0,
                cx + math.cos(a) * r1,
                cy + math.sin(a) * r1,
            ),
            fill=(22, 68, 128, 210),
            width=5,
        )
    needle_a = math.radians(-45)
    draw.line(
        (cx, cy, cx + math.cos(needle_a) * (radius - 36), cy + math.sin(needle_a) * (radius - 36)),
        fill=(16, 65, 128, 235),
        width=10,
    )
    draw.ellipse((cx - 11, cy - 11, cx + 11, cy + 11), fill=(21, 72, 135, 255))
    draw.arc((cx - radius + 20, cy - radius + 18, cx + radius - 16, cy + radius - 14), 205, 292, fill=(255, 255, 255, 145), width=8)
    mdraw.ellipse((cx - radius - 8, cy - radius - 8, cx + radius + 8, cy + radius + 8), fill=255)
    motifs.append(Motif(name=name, pocket=pocket, bbox=(cx - radius, cy - radius, cx + radius, cy + radius)))


def draw_screw(
    art: Image.Image,
    motif_mask: Image.Image,
    center: tuple[int, int],
    radius: int,
    pocket: str,
    name: str,
    motifs: list[Motif],
) -> None:
    cx, cy = center
    draw = ImageDraw.Draw(art, "RGBA")
    mdraw = ImageDraw.Draw(motif_mask)
    draw.ellipse((cx - radius - 6, cy - radius + 3, cx + radius + 6, cy + radius + 15), fill=(10, 63, 125, 72))
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(179, 215, 240, 255), outline=(17, 66, 130, 232), width=6)
    draw.line((cx - radius + 12, cy + radius - 12, cx + radius - 12, cy - radius + 12), fill=(42, 99, 172, 210), width=5)
    draw.arc((cx - radius + 7, cy - radius + 5, cx + radius - 7, cy + radius - 7), 200, 295, fill=(255, 255, 255, 130), width=4)
    mdraw.ellipse((cx - radius - 3, cy - radius - 3, cx + radius + 3, cy + radius + 3), fill=255)
    motifs.append(Motif(name=name, pocket=pocket, bbox=(cx - radius, cy - radius, cx + radius, cy + radius)))


def apply_alpha_guard(art: Image.Image, allowed_mask: Image.Image) -> Image.Image:
    rgba = np.array(art.convert("RGBA"))
    alpha = rgba[:, :, 3].astype(np.uint16)
    allowed = np.array(allowed_mask, dtype=np.uint16)
    rgba[:, :, 3] = ((alpha * allowed) // 255).astype(np.uint8)
    return Image.fromarray(rgba, mode="RGBA")


def draw_reference_first_art(
    size: tuple[int, int], paths: list[SvgPath], masks: dict[str, Image.Image]
) -> tuple[Image.Image, Image.Image, list[Motif]]:
    art = watercolor_base(size, masks["allowed"])
    motif_mask = Image.new("L", size, 0)
    motifs: list[Motif] = []

    # Watercolor navy boundary/rim language from the references.
    draw_path_stroke(art, paths[0].mapped_points, (7, 54, 118, 200), 18)
    draw_path_stroke(art, paths[0].mapped_points, (42, 104, 180, 120), 9)
    for cutout_path in paths[1:]:
        draw_path_stroke(art, cutout_path.mapped_points, (7, 54, 118, 205), 18)
        draw_path_stroke(art, cutout_path.mapped_points, (54, 118, 190, 112), 8)

    draw = ImageDraw.Draw(art, "RGBA")
    # Soft body highlights, still clipped to material at export.
    draw.line((410, 48, 632, 48), fill=(255, 255, 255, 82), width=8)
    draw.arc((35, 1115, 395, 1545), 175, 257, fill=(255, 255, 255, 72), width=10)
    draw.line((712, 993, 878, 993), fill=(255, 255, 255, 68), width=8)
    draw.arc((1460, 865, 1608, 1020), 285, 360, fill=(255, 255, 255, 64), width=7)

    draw_slider_bank(art, motif_mask, motifs)

    top_pocket = "upper-left tall bay above the left shoulder of the slot"
    draw_cylinder(art, motif_mask, (470, 175), (56, 140), (244, 94, 91, 255), top_pocket, "coral upright rounded control", motifs)
    draw_cylinder(art, motif_mask, (575, 206), (56, 128), (249, 194, 65, 255), top_pocket, "yellow upright rounded control", motifs)
    draw_cylinder(art, motif_mask, (660, 194), (56, 126), (88, 205, 188, 255), top_pocket, "mint upright rounded control", motifs)
    draw_glossy_button(
        art,
        motif_mask,
        (415, 285, 650, 356),
        (102, 207, 192, 250),
        top_pocket,
        "mint rounded status capsule",
        motifs,
        radius=31,
    )

    lower_mid = "lower-middle bay between the bottom notch and the right cutouts"
    draw_dial(art, motif_mask, (925, 1242), 105, lower_mid, "large pale-blue dial", motifs)
    draw_glossy_button(
        art,
        motif_mask,
        (1078, 1120, 1325, 1192),
        (248, 99, 91, 252),
        lower_mid,
        "coral horizontal pill button",
        motifs,
        radius=32,
    )
    draw_glossy_button(
        art,
        motif_mask,
        (1088, 1288, 1322, 1360),
        (248, 194, 65, 252),
        lower_mid,
        "yellow horizontal pill button",
        motifs,
        radius=32,
    )
    draw_glossy_button(
        art,
        motif_mask,
        (1118, 1210, 1280, 1274),
        (91, 206, 188, 252),
        lower_mid,
        "mint short middle pill button",
        motifs,
        radius=28,
    )

    base_left = "lower-left base bay above the bottom notch"
    draw_screw(art, motif_mask, (125, 1255), 36, base_left, "lower-left glossy screw", motifs)
    draw_screw(art, motif_mask, (560, 1432), 30, "lower-left base bay above the bottom notch", "bottom-center small screw", motifs)

    right_strip = "right vertical strip between the diagonal slot and outer edge"
    for i, (y, color) in enumerate(
        [
            (1082, (250, 195, 65, 245)),
            (1134, (91, 206, 189, 245)),
            (1354, (244, 96, 91, 245)),
            (1410, (249, 195, 65, 245)),
        ]
    ):
        draw_glossy_button(
            art,
            motif_mask,
            (1496, y, 1562, y + 28),
            color,
            right_strip,
            f"right-edge short accent bar {i + 1}",
            motifs,
            radius=12,
        )

    art = apply_alpha_guard(art, masks["allowed"])
    return art, motif_mask, motifs


def dashed_line(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[float, float]],
    fill: tuple[int, int, int, int],
    width: int,
    dash: int = 22,
    gap: int = 13,
) -> None:
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        dx = x1 - x0
        dy = y1 - y0
        length = math.hypot(dx, dy)
        if length <= 0:
            continue
        ux = dx / length
        uy = dy / length
        pos = 0.0
        while pos < length:
            end = min(length, pos + dash)
            draw.line(
                (x0 + ux * pos, y0 + uy * pos, x0 + ux * end, y0 + uy * end),
                fill=fill,
                width=width,
            )
            pos += dash + gap


def make_overlay(art: Image.Image, paths: list[SvgPath], masks: dict[str, Image.Image]) -> Image.Image:
    overlay = Image.new("RGBA", art.size, (252, 252, 248, 255))
    overlay.alpha_composite(art)
    red = Image.new("RGBA", art.size, (255, 72, 72, 0))
    red_alpha = (np.array(masks["cutouts"]) > 0).astype(np.uint8) * 72
    red.putalpha(Image.fromarray(red_alpha, mode="L"))
    overlay.alpha_composite(red)
    draw = ImageDraw.Draw(overlay, "RGBA")
    for path in paths:
        dashed_line(draw, path.mapped_points, (255, 219, 85, 245), 8)
    return overlay


def make_mask_debug(
    size: tuple[int, int],
    paths: list[SvgPath],
    masks: dict[str, Image.Image],
    motif_mask: Image.Image,
    safe_pockets: list[dict[str, object]],
) -> Image.Image:
    outer = np.array(masks["outer"]) > 0
    allowed = np.array(masks["allowed"]) > 0
    cutouts = np.array(masks["cutouts"]) > 0
    forbidden = np.array(masks["forbidden"]) > 0
    motifs = np.array(motif_mask) > 0

    canvas = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    canvas[:, :] = np.array([35, 38, 44, 255], dtype=np.uint8)
    canvas[outer] = np.array([62, 93, 126, 255], dtype=np.uint8)
    canvas[allowed] = np.array([104, 168, 221, 255], dtype=np.uint8)
    canvas[forbidden & allowed] = np.array([248, 195, 65, 255], dtype=np.uint8)
    canvas[cutouts] = np.array([239, 84, 83, 255], dtype=np.uint8)
    canvas[motifs & allowed] = np.array([91, 207, 189, 255], dtype=np.uint8)
    image = Image.fromarray(canvas, mode="RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    for path in paths:
        draw.line([(int(x), int(y)) for x, y in path.mapped_points], fill=(6, 45, 98, 230), width=5, joint="curve")
    for pocket in safe_pockets:
        x0, y0, x1, y1 = pocket["bbox"]
        draw.rounded_rectangle((x0, y0, x1, y1), radius=18, outline=(255, 255, 255, 165), width=3)
    font = ImageFont.load_default()
    draw.text((18, 18), "mask debug: blue=allowed, red=cutout, yellow=reserved margin, mint=focal motifs", fill=(255, 255, 255, 230), font=font)
    return image


def safe_pocket_plan() -> list[dict[str, object]]:
    return [
        {
            "name": "upper-left tall bay above the left shoulder of the slot",
            "bbox": [405, 102, 712, 372],
            "motifs": ["coral/yellow/mint upright controls", "mint rounded status capsule"],
        },
        {
            "name": "middle-left field below/left of the diagonal slot",
            "bbox": [226, 680, 742, 948],
            "motifs": ["four sparse rounded sliders with small colored knobs"],
        },
        {
            "name": "lower-left base bay above the bottom notch",
            "bbox": [72, 1160, 610, 1462],
            "motifs": ["glossy screw heads only"],
        },
        {
            "name": "lower-middle bay between the bottom notch and the right cutouts",
            "bbox": [820, 1090, 1350, 1388],
            "motifs": ["large dial", "three rounded pill buttons"],
        },
        {
            "name": "right vertical strip between the diagonal slot and outer edge",
            "bbox": [1478, 1050, 1570, 1452],
            "motifs": ["short accent bars only, held away from the round cutout"],
        },
    ]


def measure_outputs(
    art: Image.Image,
    paths: list[SvgPath],
    masks: dict[str, Image.Image],
    motif_mask: Image.Image,
) -> dict[str, object]:
    alpha = np.array(art.getchannel("A"))
    allowed = np.array(masks["allowed"]) > 0
    cutouts = np.array(masks["cutouts"]) > 0
    outer = np.array(masks["outer"]) > 0
    forbidden = np.array(masks["forbidden"]) > 0
    motif = np.array(motif_mask) > 0

    outside_painted = int(np.count_nonzero((alpha > 0) & ~allowed))
    cutout_painted = int(np.count_nonzero((alpha > 0) & cutouts))
    motif_forbidden_overlap = int(np.count_nonzero(motif & forbidden))
    motif_cutout_overlap = int(np.count_nonzero(motif & cutouts))
    motif_outside_outer = int(np.count_nonzero(motif & ~outer))

    path_bounds_out = [
        {
            "path_index": path.index,
            "role": path.role,
            "bounds": [round(v, 2) for v in path.bounds],
        }
        for path in paths
    ]

    return {
        "canvas_size": list(art.size),
        "svg_path_bounds": path_bounds_out,
        "painted_pixel_metrics": {
            "outside_allowed_alpha_pixels": outside_painted,
            "inside_internal_cutout_alpha_pixels": cutout_painted,
            "focal_motif_pixels_inside_cutouts": motif_cutout_overlap,
            "focal_motif_pixels_outside_outer": motif_outside_outer,
            "focal_motif_pixels_in_cutout_or_edge_margin": motif_forbidden_overlap,
        },
        "mechanical_gate": {
            "zero_alpha_outside_allowed": outside_painted == 0,
            "zero_alpha_inside_cutouts": cutout_painted == 0,
            "zero_focal_motifs_inside_cutouts": motif_cutout_overlap == 0,
            "zero_focal_motifs_outside_outer": motif_outside_outer == 0,
            "zero_focal_motifs_in_reserved_margins": motif_forbidden_overlap == 0,
            "pass": all(
                [
                    outside_painted == 0,
                    cutout_painted == 0,
                    motif_cutout_overlap == 0,
                    motif_outside_outer == 0,
                    motif_forbidden_overlap == 0,
                ]
            ),
        },
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    viewbox = parse_viewbox(SVG_PATH)
    size = (round(viewbox[2]), round(viewbox[3]))
    paths = load_svg_paths(size)
    masks = build_masks(size, paths)
    palette = extract_reference_palette()
    safe_pockets = safe_pocket_plan()

    art, motif_mask, motifs = draw_reference_first_art(size, paths, masks)
    overlay = make_overlay(art, paths, masks)
    debug = make_mask_debug(size, paths, masks, motif_mask, safe_pockets)

    metrics = measure_outputs(art, paths, masks, motif_mask)
    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    metadata = {
        "candidate": "reference-first",
        "method": "procedural Pillow proof; reference vocabulary first, SVG geometry hard",
        "source_svg": rel(SVG_PATH),
        "template_manifest": rel(MANIFEST_PATH),
        "geometry_report": rel(GEOMETRY_REPORT_PATH),
        "style_reference_extraction": palette,
        "manifest_geometry_roles_used": manifest.get("geometry_roles", {}),
        "safe_pocket_plan": safe_pockets,
        "motifs": [
            {
                "name": motif.name,
                "pocket": motif.pocket,
                "bbox": list(motif.bbox),
            }
            for motif in motifs
        ],
        "geometry_metrics": metrics,
        "workflow_notes": [
            "Quiet blue watercolor material is allowed across the whole paintable body.",
            "Readable controls were placed only in safe pockets before applying the SVG export guardrail.",
            "The large diagonal slot and lower-right circular cutout were reserved as cutouts from the mask stage onward.",
            "The proof prioritizes reference object vocabulary over dense mechanical fill.",
        ],
        "outputs": {
            "artwork": rel(ARTWORK_OUT),
            "overlay": rel(OVERLAY_OUT),
            "mask_debug": rel(MASK_DEBUG_OUT),
            "metadata": rel(METADATA_OUT),
        },
    }

    art.save(ARTWORK_OUT)
    overlay.save(OVERLAY_OUT)
    debug.save(MASK_DEBUG_OUT)
    with METADATA_OUT.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
        f.write("\n")

    print(json.dumps(metadata["geometry_metrics"]["mechanical_gate"], indent=2))


if __name__ == "__main__":
    main()
