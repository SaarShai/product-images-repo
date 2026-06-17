#!/usr/bin/env python3
"""Watercolor/style polish for the strict-pocket SVG-template candidate.

The geometry contract intentionally reuses the prior strict-pocket parser and
mask gate:
- path[0] is the outer material contour.
- path[1] is the large diagonal rounded slot cutout.
- path[2] is the lower-right circular cutout.

The rendering is a fresh reference-style pass, not a palette shift of the old
flat artwork. Decorative controls are drawn only after their local masks fit
inside an eroded paintable mask. The final alpha clip remains an exact export
guardrail.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


OUT_DIR = Path(__file__).resolve().parent
TASK_DIR = OUT_DIR.parent.parent
SVG_PATH = TASK_DIR / "source" / "template.svg"
MANIFEST_PATH = TASK_DIR / "template-manifest.json"
GEOMETRY_REPORT_PATH = TASK_DIR / "svg-geometry-report.md"
STRICT_POCKET_SCRIPT = OUT_DIR.parent / "strict-pocket" / "generate_strict_pocket.py"
REF_PATHS = [
    TASK_DIR / "refs" / "ChatGPT Image Jun 9, 2026, 11_19_45 PM.png",
    TASK_DIR / "refs" / "ChatGPT Image Jun 9, 2026, 11_17_34 PM.png",
]

ARTWORK_PATH = OUT_DIR / "strict-style-polish-artwork.png"
OVERLAY_PATH = OUT_DIR / "strict-style-polish-overlay.png"
MASK_DEBUG_PATH = OUT_DIR / "strict-style-polish-mask-debug.png"
METADATA_PATH = OUT_DIR / "strict-style-polish-metadata.json"


def load_strict_geometry_module():
    spec = importlib.util.spec_from_file_location("strict_pocket_geometry", STRICT_POCKET_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {STRICT_POCKET_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


strict = load_strict_geometry_module()


def count_nonzero(mask: Image.Image) -> int:
    return int(np.count_nonzero(np.asarray(mask)))


def draw_masked_polygon(size: tuple[int, int], points: Iterable[tuple[float, float]]) -> Image.Image:
    return strict.draw_polygon_mask(size, points)


def erode(mask: Image.Image, pixels: int) -> Image.Image:
    return strict.erode(mask, pixels)


def rounded(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    radius: int,
    fill,
    outline=None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def relative(path: Path) -> str:
    return str(path.relative_to(TASK_DIR.parent.parent))


def normalized_noise(
    size: tuple[int, int],
    rng: np.random.Generator,
    cell: int,
    blur: float,
) -> np.ndarray:
    width, height = size
    small = rng.normal(0, 1, (math.ceil(height / cell), math.ceil(width / cell)))
    small = (small - small.min()) / max(float(small.max() - small.min()), 1e-6)
    image = Image.fromarray(np.uint8(small * 255)).resize(size, Image.Resampling.BICUBIC)
    if blur:
        image = image.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(image).astype(np.float32) / 255.0


def alpha_color(size: tuple[int, int], rgba: tuple[int, int, int, int], alpha: Image.Image) -> Image.Image:
    layer = Image.new("RGBA", size, rgba)
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), alpha))
    return layer


def clear_transparent_rgb(image: Image.Image) -> Image.Image:
    arr = np.array(image.convert("RGBA"), copy=True)
    arr[arr[..., 3] == 0] = (0, 0, 0, 0)
    return Image.fromarray(arr)


def draw_polyline(
    layer: Image.Image,
    points: list[tuple[float, float]],
    color: tuple[int, int, int, int],
    width: int,
    jitter: float,
    seed: int,
) -> None:
    rng = np.random.default_rng(seed)
    coords = []
    for idx, (x, y) in enumerate(points):
        # Keep closure points stable enough that outlines do not visibly gap.
        amp = jitter * (0.4 if idx in (0, len(points) - 1) else 1.0)
        coords.append((round(x + rng.normal(0, amp)), round(y + rng.normal(0, amp))))
    ImageDraw.Draw(layer, "RGBA").line(coords, fill=color, width=width, joint="curve")


def add_shadow(
    layer: Image.Image,
    draw_shape: Callable[[ImageDraw.ImageDraw], None],
    blur: float = 6.0,
) -> None:
    shadow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    draw_shape(ImageDraw.Draw(shadow, "RGBA"))
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    layer.alpha_composite(shadow)


def build_watercolor_panel(size: tuple[int, int], paintable_mask: Image.Image) -> Image.Image:
    width, height = size
    rng = np.random.default_rng(20260616)

    coarse = normalized_noise(size, rng, 38, 7.0)
    bloom = normalized_noise(size, rng, 118, 18.0)
    grain = rng.normal(0, 1, (height, width, 1)).astype(np.float32)

    paper = np.array([219, 237, 246], dtype=np.float32)
    pale_blue = np.array([144, 205, 244], dtype=np.float32)
    wash_blue = np.array([76, 150, 216], dtype=np.float32)
    deep_blue = np.array([29, 88, 164], dtype=np.float32)

    mix = 0.18 + 0.50 * coarse[..., None] + 0.30 * bloom[..., None]
    rgb = paper * (1.0 - mix) + pale_blue * mix
    rgb = rgb * 0.86 + wash_blue * (0.14 + 0.18 * bloom[..., None])
    rgb += grain * 4.5
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)

    panel = Image.fromarray(rgb).convert("RGBA")

    washes = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(washes, "RGBA")
    for _ in range(145):
        cx = int(rng.integers(30, width - 30))
        cy = int(rng.integers(30, height - 30))
        rx = int(rng.integers(55, 310))
        ry = int(rng.integers(35, 190))
        if rng.random() < 0.35:
            color = tuple(deep_blue.astype(int)) + (int(rng.integers(8, 27)),)
        else:
            color = (183, 223, 252, int(rng.integers(10, 36)))
        d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=color)
    washes = washes.filter(ImageFilter.GaussianBlur(14))
    washes.putalpha(ImageChops.multiply(washes.getchannel("A"), paintable_mask))
    panel = Image.alpha_composite(panel, washes)

    fiber = Image.new("RGBA", size, (0, 0, 0, 0))
    fd = ImageDraw.Draw(fiber, "RGBA")
    for y in range(0, height, 17):
        alpha = int(rng.integers(5, 15))
        fd.line((0, y + int(rng.integers(-2, 3)), width, y + int(rng.integers(-2, 3))), fill=(255, 255, 255, alpha), width=1)
    for x in range(0, width, 23):
        alpha = int(rng.integers(3, 10))
        fd.line((x + int(rng.integers(-2, 3)), 0, x + int(rng.integers(-2, 3)), height), fill=(30, 85, 145, alpha), width=1)
    fiber.putalpha(ImageChops.multiply(fiber.getchannel("A"), paintable_mask))
    panel = Image.alpha_composite(panel, fiber)

    edge = ImageChops.subtract(paintable_mask, erode(paintable_mask, 28))
    edge_blur = edge.filter(ImageFilter.GaussianBlur(9))
    panel = Image.alpha_composite(panel, alpha_color(size, (20, 76, 150, 80), edge_blur))

    inner_bloom = ImageChops.subtract(erode(paintable_mask, 9), erode(paintable_mask, 45))
    inner_bloom = inner_bloom.filter(ImageFilter.GaussianBlur(5))
    panel = Image.alpha_composite(panel, alpha_color(size, (222, 241, 255, 52), inner_bloom))

    panel.putalpha(paintable_mask)
    return panel


def draw_template_ink(
    size: tuple[int, int],
    sampled_paths: list[list[tuple[float, float]]],
    paintable_mask: Image.Image,
) -> Image.Image:
    ink = Image.new("RGBA", size, (0, 0, 0, 0))
    outer = sampled_paths[0]
    holes = sampled_paths[1:3]

    for offset, seed, alpha, width in [(0, 11, 165, 15), (1, 12, 100, 10), (-1, 13, 90, 7)]:
        shifted = [(x + offset, y + offset) for x, y in outer]
        draw_polyline(ink, shifted, (12, 57, 126, alpha), width, 1.6, seed)
    draw_polyline(ink, outer, (220, 242, 255, 92), 4, 0.8, 14)

    for idx, hole in enumerate(holes):
        draw_polyline(ink, hole, (9, 53, 119, 180), 13, 1.3, 30 + idx)
        draw_polyline(ink, hole, (29, 91, 169, 140), 7, 0.8, 40 + idx)
        draw_polyline(ink, hole, (231, 247, 255, 80), 3, 0.5, 50 + idx)

    ink.putalpha(ImageChops.multiply(ink.getchannel("A"), paintable_mask))
    return ink


@dataclass
class Control:
    name: str
    pocket: str
    role: str
    draw_fn: Callable[[Image.Image, bool], None]


def pill_mask(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, fill) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def make_controls(size: tuple[int, int]) -> list[Control]:
    width, height = size

    def upper_lamps(layer: Image.Image, mask_mode: bool) -> None:
        d = ImageDraw.Draw(layer, "RGBA" if layer.mode == "RGBA" else None)
        lamps = [
            (506, 158, 31, (250, 96, 89, 255)),
            (585, 230, 30, (247, 188, 58, 255)),
            (462, 270, 29, (93, 201, 181, 255)),
        ]
        if mask_mode:
            for x, y, r, _ in lamps:
                d.ellipse((x - r - 17, y - r - 10, x + r + 17, y + r + 22), fill=255)
            return

        for idx, (x, y, r, color) in enumerate(lamps):
            add_shadow(
                layer,
                lambda sd, x=x, y=y, r=r: sd.ellipse((x - r - 11, y - r + 8, x + r + 13, y + r + 24), fill=(7, 40, 95, 95)),
                5.0,
            )
            d.ellipse((x - r - 8, y - r - 8, x + r + 8, y + r + 8), fill=(13, 60, 132, 238))
            d.ellipse((x - r - 2, y - r + 1, x + r + 4, y + r + 7), fill=(37, 102, 178, 155))
            for j in range(4):
                inset = 4 + j * 2
                alpha = 210 - j * 22
                d.ellipse((x - r + inset, y - r + inset - 2, x + r - inset, y + r - inset + 4), fill=color[:3] + (alpha,))
            d.arc((x - r - 5, y - r - 5, x + r + 5, y + r + 5), 185, 530, fill=(8, 49, 112, 190), width=3)
            d.ellipse((x - r + 7, y - r + 5, x - r + 23, y - r + 19), fill=(255, 255, 255, 125))
            if idx == 1:
                d.ellipse((x - r + 14, y - r + 3, x - r + 28, y - r + 15), fill=(255, 255, 255, 85))

    def slider_bank(layer: Image.Image, mask_mode: bool) -> None:
        d = ImageDraw.Draw(layer, "RGBA" if layer.mode == "RGBA" else None)
        y_values = [704, 776, 852, 928]
        x0, x1 = 245, 735
        knob_sets = [
            [(309, (255, 99, 88, 255)), (526, (250, 190, 58, 255))],
            [(414, (93, 201, 181, 255)), (607, (255, 99, 88, 255))],
            [(248, (255, 99, 88, 255)), (466, (250, 190, 58, 255)), (640, (93, 201, 181, 255))],
            [(389, (250, 190, 58, 255)), (693, (255, 99, 88, 255))],
        ]
        if mask_mode:
            for y, knobs in zip(y_values, knob_sets):
                d.rounded_rectangle((x0 - 3, y - 14, x1 + 3, y + 17), 10, fill=255)
                for k, _ in knobs:
                    d.rounded_rectangle((k - 23, y - 23, k + 24, y + 24), 10, fill=255)
            return

        for row, (y, knobs) in enumerate(zip(y_values, knob_sets)):
            add_shadow(
                layer,
                lambda sd, y=y: sd.rounded_rectangle((x0 - 2, y + 7, x1 + 6, y + 24), 9, fill=(7, 38, 91, 72)),
                4.5,
            )
            d.rounded_rectangle((x0, y - 8, x1, y + 12), 9, fill=(54, 120, 194, 138))
            d.rounded_rectangle((x0 + 4, y - 4, x1 - 5, y + 6), 7, fill=(176, 219, 249, 118))
            d.line((x0 + 10, y - 8, x1 - 12, y - 8), fill=(240, 252, 255, 90), width=3)
            d.line((x0 + 6, y + 12, x1 - 8, y + 12), fill=(18, 63, 133, 100), width=4)
            for col, (k, color) in enumerate(knobs):
                add_shadow(
                    layer,
                    lambda sd, k=k, y=y: sd.rounded_rectangle((k - 20, y - 16, k + 27, y + 29), 9, fill=(6, 37, 94, 84)),
                    3.5,
                )
                d.rounded_rectangle((k - 21, y - 21, k + 21, y + 21), 9, fill=(13, 58, 128, 245))
                d.rounded_rectangle((k - 16, y - 17, k + 17, y + 15), 8, fill=color)
                d.rounded_rectangle((k - 10, y - 14, k + 7, y - 7), 5, fill=(255, 255, 255, 105))
                if (row + col) % 2 == 0:
                    d.arc((k - 17, y - 17, k + 17, y + 17), 185, 440, fill=(255, 255, 255, 64), width=2)

    def lower_left_pills(layer: Image.Image, mask_mode: bool) -> None:
        d = ImageDraw.Draw(layer, "RGBA" if layer.mode == "RGBA" else None)
        bars = [
            ((108, 1178, 291, 1226), (255, 101, 88, 255)),
            ((116, 1260, 338, 1309), (249, 190, 55, 255)),
            ((123, 1342, 313, 1390), (91, 201, 181, 255)),
        ]
        if mask_mode:
            for box, _ in bars:
                x0, y0, x1, y1 = box
                d.rounded_rectangle((x0 - 5, y0 - 4, x1 + 7, y1 + 12), 22, fill=255)
            return
        for box, color in bars:
            x0, y0, x1, y1 = box
            add_shadow(
                layer,
                lambda sd, x0=x0, y0=y0, x1=x1, y1=y1: sd.rounded_rectangle((x0 + 1, y0 + 10, x1 + 7, y1 + 18), 22, fill=(7, 36, 92, 95)),
                4.0,
            )
            d.rounded_rectangle((x0, y0, x1, y1), 21, fill=(12, 58, 130, 245))
            d.rounded_rectangle((x0 + 9, y0 + 9, x1 - 8, y1 - 10), 17, fill=color)
            d.rounded_rectangle((x0 + 22, y0 + 13, x1 - 36, y0 + 24), 8, fill=(255, 255, 255, 106))
            d.arc((x0 + 4, y0 + 4, x1 - 4, y1 - 4), 180, 350, fill=(255, 255, 255, 46), width=3)

    def lower_left_gauge(layer: Image.Image, mask_mode: bool) -> None:
        d = ImageDraw.Draw(layer, "RGBA" if layer.mode == "RGBA" else None)
        cx, cy, r = 471, 1278, 116
        if mask_mode:
            d.ellipse((cx - r - 20, cy - r - 9, cx + r + 25, cy + r + 29), fill=255)
            for angle in range(-130, 140, 30):
                rad = math.radians(angle)
                x0 = cx + math.cos(rad) * (r - 8)
                y0 = cy + math.sin(rad) * (r - 8)
                x1 = cx + math.cos(rad) * (r + 24)
                y1 = cy + math.sin(rad) * (r + 24)
                d.line((x0, y0, x1, y1), fill=255, width=12)
            return

        add_shadow(
            layer,
            lambda sd: sd.ellipse((cx - r - 10, cy - r + 15, cx + r + 20, cy + r + 32), fill=(6, 37, 91, 95)),
            8.0,
        )
        d.ellipse((cx - r - 3, cy - r - 4, cx + r + 3, cy + r + 5), fill=(15, 65, 139, 250))
        d.ellipse((cx - r + 13, cy - r + 13, cx + r - 13, cy + r - 13), fill=(44, 108, 183, 210))
        d.ellipse((cx - r + 24, cy - r + 23, cx + r - 24, cy + r - 25), fill=(222, 241, 251, 245))

        face_wash = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        fd = ImageDraw.Draw(face_wash, "RGBA")
        fd.ellipse((cx - r + 28, cy - r + 27, cx + r - 28, cy + r - 29), fill=(192, 224, 243, 105))
        for offset, alpha in [(-22, 35), (16, 25), (45, 18)]:
            fd.ellipse((cx - 90 + offset, cy - 65, cx + 94 + offset, cy + 76), fill=(127, 190, 230, alpha))
        face_wash = face_wash.filter(ImageFilter.GaussianBlur(6))
        layer.alpha_composite(face_wash)

        d.arc((cx - r + 35, cy - r + 35, cx + r - 35, cy + r - 35), 202, 338, fill=(28, 89, 164, 230), width=9)
        for angle in range(-125, 136, 32):
            rad = math.radians(angle)
            x0 = cx + math.cos(rad) * (r - 39)
            y0 = cy + math.sin(rad) * (r - 39)
            x1 = cx + math.cos(rad) * (r - 20)
            y1 = cy + math.sin(rad) * (r - 20)
            d.line((x0, y0, x1, y1), fill=(12, 63, 137, 230), width=5)
        needle = math.radians(39)
        d.line((cx + 2, cy + 1, cx + math.cos(needle) * 70, cy + math.sin(needle) * 70), fill=(9, 49, 112, 255), width=7)
        d.line((cx + 2, cy + 1, cx + math.cos(needle) * 57, cy + math.sin(needle) * 57), fill=(55, 126, 197, 220), width=3)
        d.ellipse((cx - 13, cy - 13, cx + 13, cy + 13), fill=(250, 188, 53, 255))
        d.ellipse((cx - 78, cy - 82, cx - 18, cy - 55), fill=(255, 255, 255, 128))
        d.arc((cx - r + 24, cy - r + 20, cx + r - 24, cy + r - 21), 180, 346, fill=(255, 255, 255, 70), width=4)

    def lower_middle_buttons(layer: Image.Image, mask_mode: bool) -> None:
        d = ImageDraw.Draw(layer, "RGBA" if layer.mode == "RGBA" else None)
        rows = [
            ((936, 1094, 1188, 1162), (255, 103, 90, 255)),
            ((925, 1217, 1179, 1288), (91, 201, 181, 255)),
            ((945, 1342, 1196, 1413), (249, 190, 55, 255)),
        ]
        if mask_mode:
            for box, _ in rows:
                x0, y0, x1, y1 = box
                d.rounded_rectangle((x0 - 8, y0 - 8, x1 + 10, y1 + 15), 31, fill=255)
            return

        for box, color in rows:
            x0, y0, x1, y1 = box
            add_shadow(
                layer,
                lambda sd, x0=x0, y0=y0, x1=x1, y1=y1: sd.rounded_rectangle((x0 + 1, y0 + 13, x1 + 12, y1 + 19), 31, fill=(5, 35, 88, 88)),
                6.0,
            )
            d.rounded_rectangle((x0, y0, x1, y1), 30, fill=(13, 61, 134, 248))
            d.rounded_rectangle((x0 + 12, y0 + 10, x1 - 11, y1 - 13), 24, fill=color)
            d.rounded_rectangle((x0 + 28, y0 + 17, x1 - 42, y0 + 35), 12, fill=(255, 255, 255, 100))
            d.arc((x0 + 10, y0 + 7, x1 - 10, y1 - 7), 185, 355, fill=(255, 255, 255, 48), width=3)

    def right_strip_bolts(layer: Image.Image, mask_mode: bool) -> None:
        d = ImageDraw.Draw(layer, "RGBA" if layer.mode == "RGBA" else None)
        bolts = [(1536, 1106), (1538, 1402)]
        if mask_mode:
            for cx, cy in bolts:
                d.ellipse((cx - 29, cy - 25, cx + 29, cy + 33), fill=255)
            return
        for cx, cy in bolts:
            add_shadow(
                layer,
                lambda sd, cx=cx, cy=cy: sd.ellipse((cx - 23, cy - 16, cx + 27, cy + 34), fill=(4, 30, 82, 80)),
                4.0,
            )
            d.ellipse((cx - 24, cy - 24, cx + 24, cy + 24), fill=(24, 79, 151, 248))
            d.ellipse((cx - 16, cy - 16, cx + 16, cy + 16), fill=(224, 242, 252, 246))
            d.line((cx - 12, cy + 9, cx + 12, cy - 9), fill=(55, 116, 190, 255), width=5)
            d.ellipse((cx - 11, cy - 12, cx - 1, cy - 4), fill=(255, 255, 255, 132))

    def upper_pin_cluster(layer: Image.Image, mask_mode: bool) -> None:
        d = ImageDraw.Draw(layer, "RGBA" if layer.mode == "RGBA" else None)
        pins = [
            ((416, 386, 448, 496), (255, 99, 88, 255)),
            ((497, 366, 530, 480), (250, 190, 58, 255)),
            ((576, 390, 608, 506), (91, 201, 181, 255)),
        ]
        if mask_mode:
            for box, _ in pins:
                x0, y0, x1, y1 = box
                d.rounded_rectangle((x0 - 12, y0 - 10, x1 + 12, y1 + 18), 20, fill=255)
                d.ellipse((x0 - 14, y1 - 26, x1 + 14, y1 + 21), fill=255)
            return
        for idx, (box, color) in enumerate(pins):
            x0, y0, x1, y1 = box
            add_shadow(
                layer,
                lambda sd, x0=x0, y0=y0, x1=x1, y1=y1: sd.ellipse((x0 - 18, y1 - 20, x1 + 19, y1 + 25), fill=(6, 37, 91, 78)),
                4.5,
            )
            d.ellipse((x0 - 15, y1 - 28, x1 + 15, y1 + 17), fill=(14, 59, 132, 236))
            d.rounded_rectangle((x0 - 3, y0 + 11, x1 + 4, y1 - 2), 14, fill=(15, 63, 136, 245))
            d.rounded_rectangle((x0 + 2, y0, x1 - 2, y1 - 9), 15, fill=color)
            d.ellipse((x0 + 1, y0 - 2, x1 - 2, y0 + 30), fill=tuple(min(255, c + 24) for c in color[:3]) + (215,))
            d.rounded_rectangle((x0 + 8, y0 + 13, x0 + 18, y0 + 55), 7, fill=(255, 255, 255, 72))
            if idx == 2:
                d.line((x1 - 8, y0 + 46, x1 + 1, y0 + 72), fill=(255, 255, 255, 95), width=5)

    return [
        Control(
            "upper-left watercolor indicator lamps",
            "upper-left tall bay above the left shoulder of the slot",
            "domed red/yellow/teal lamps with dark raised bases",
            upper_lamps,
        ),
        Control(
            "upper-left raised pin cluster",
            "upper-left tall bay above the left shoulder of the slot",
            "small vertical control pins copied from the reference vocabulary",
            upper_pin_cluster,
        ),
        Control(
            "middle-left multi-knob slider bank",
            "middle-left field below/left of the diagonal slot",
            "watery rails with several rounded colored knobs",
            slider_bank,
        ),
        Control(
            "lower-left watercolor gauge",
            "lower-left base bay above the bottom notch",
            "raised blue ring, pale face, ticks, needle, and soft highlights",
            lower_left_gauge,
        ),
        Control(
            "lower-left stacked pill buttons",
            "lower-left base bay above the bottom notch",
            "rounded red/yellow/teal pill bars with glossy watercolor highlights",
            lower_left_pills,
        ),
        Control(
            "lower-middle shifted pill buttons",
            "lower-middle bay between the bottom notch and the right cutouts",
            "reference-like large rounded controls shifted clear of the bottom void",
            lower_middle_buttons,
        ),
        Control(
            "right-strip screw heads",
            "right vertical strip between the diagonal slot and outer edge",
            "small friendly screw details kept away from the lower-right cutout",
            right_strip_bolts,
        ),
    ]


def evaluate_control(
    mask: Image.Image,
    outer: Image.Image,
    cutouts: Image.Image,
    paintable_safe: Image.Image,
) -> dict:
    outside_outer = ImageChops.subtract(mask, outer)
    inside_cutouts = ImageChops.multiply(mask, cutouts)
    outside_safe = ImageChops.subtract(mask, paintable_safe)
    return {
        "mask_pixels": count_nonzero(mask),
        "outside_outer_pixels": count_nonzero(outside_outer),
        "inside_cutout_pixels": count_nonzero(inside_cutouts),
        "outside_eroded_paintable_pixels": count_nonzero(outside_safe),
        "bbox": list(mask.getbbox()) if mask.getbbox() else None,
    }


def build_debug(
    size: tuple[int, int],
    paintable_mask: Image.Image,
    cutouts_mask: Image.Image,
    paintable_safe: Image.Image,
    controls: list[Control],
    controls_meta: list[dict],
) -> Image.Image:
    debug = Image.new("RGBA", size, (248, 248, 248, 255))
    debug.alpha_composite(alpha_color(size, (92, 174, 235, 118), paintable_mask))
    debug.alpha_composite(alpha_color(size, (255, 77, 77, 150), cutouts_mask))
    safe_alpha = paintable_safe.point(lambda p: 74 if p else 0)
    debug.alpha_composite(alpha_color(size, (56, 221, 126, 255), safe_alpha))

    for control, meta in zip(controls, controls_meta):
        control_mask = Image.new("L", size, 0)
        control.draw_fn(control_mask, True)
        alpha = control_mask.point(lambda p: 155 if p else 0)
        color = (0, 0, 0, 255) if meta["accepted"] else (136, 55, 30, 255)
        debug.alpha_composite(alpha_color(size, color, alpha))

    d = ImageDraw.Draw(debug, "RGBA")
    d.rectangle((16, 14, 940, 56), fill=(255, 255, 255, 205))
    d.text(
        (24, 24),
        "blue=paintable, red=cutouts, green=eroded safe mask, black=accepted controls, brown=rejected controls",
        fill=(0, 0, 0, 215),
    )
    return debug


def draw_overlay(
    size: tuple[int, int],
    art: Image.Image,
    sampled_paths: list[list[tuple[float, float]]],
) -> Image.Image:
    overlay = Image.new("RGBA", size, (255, 255, 255, 255))
    overlay = Image.alpha_composite(overlay, art)
    strict.draw_path_outline(overlay, sampled_paths[0], (255, 219, 85, 255), 7)
    strict.draw_path_outline(overlay, sampled_paths[1], (255, 78, 78, 235), 7)
    strict.draw_path_outline(overlay, sampled_paths[2], (255, 78, 78, 235), 7)
    ImageDraw.Draw(overlay, "RGBA").rectangle((0, 0, size[0] - 1, size[1] - 1), outline=(50, 50, 50, 70), width=2)
    return overlay


def make_outputs() -> dict:
    svg_text = SVG_PATH.read_text()
    manifest = json.loads(MANIFEST_PATH.read_text())
    viewbox = strict.parse_viewbox(svg_text)
    _, _, vb_width, vb_height = viewbox
    size = (math.ceil(vb_width), math.ceil(vb_height))
    path_data = strict.extract_path_data(svg_text)
    sampled_paths = [strict.sample_svg_path(d, curve_steps=36) for d in path_data[:3]]

    outer_mask = draw_masked_polygon(size, sampled_paths[0])
    path1_mask = draw_masked_polygon(size, sampled_paths[1])
    path2_mask = draw_masked_polygon(size, sampled_paths[2])
    cutouts_mask = ImageChops.lighter(path1_mask, path2_mask)
    paintable_mask = ImageChops.subtract(outer_mask, cutouts_mask)
    control_margin_px = 18
    paintable_safe = erode(paintable_mask, control_margin_px)

    art = build_watercolor_panel(size, paintable_mask)
    art = Image.alpha_composite(art, draw_template_ink(size, sampled_paths, paintable_mask))

    controls = make_controls(size)
    controls_meta = []
    for control in controls:
        control_mask = Image.new("L", size, 0)
        control.draw_fn(control_mask, True)
        metrics = evaluate_control(control_mask, outer_mask, cutouts_mask, paintable_safe)
        accepted = metrics["outside_eroded_paintable_pixels"] == 0 and metrics["mask_pixels"] > 0
        controls_meta.append(
            {
                "name": control.name,
                "pocket": control.pocket,
                "role": control.role,
                "accepted": accepted,
                **metrics,
            }
        )
        if not accepted:
            continue
        control_layer = Image.new("RGBA", size, (0, 0, 0, 0))
        control.draw_fn(control_layer, False)
        control_layer.putalpha(ImageChops.multiply(control_layer.getchannel("A"), paintable_mask))
        art = Image.alpha_composite(art, control_layer)

    # Exact export guardrail after pocket-planned drawing.
    final_alpha = ImageChops.multiply(art.getchannel("A"), paintable_mask)
    art.putalpha(final_alpha)
    art = clear_transparent_rgb(art)

    overlay = draw_overlay(size, art, sampled_paths)
    debug = build_debug(size, paintable_mask, cutouts_mask, paintable_safe, controls, controls_meta)

    final_alpha = art.getchannel("A")
    final_outside_outer = ImageChops.subtract(final_alpha, outer_mask)
    final_path1 = ImageChops.multiply(final_alpha, path1_mask)
    final_path2 = ImageChops.multiply(final_alpha, path2_mask)
    final_cutouts = ImageChops.multiply(final_alpha, cutouts_mask)
    final_outside_paintable = ImageChops.subtract(final_alpha, paintable_mask)

    accepted_controls = [record for record in controls_meta if record["accepted"]]
    rejected_controls = [record for record in controls_meta if not record["accepted"]]

    metadata = {
        "workflow": "strict-style-polish-reference-watercolor",
        "source_svg": relative(SVG_PATH),
        "template_manifest": relative(MANIFEST_PATH),
        "geometry_report": relative(GEOMETRY_REPORT_PATH),
        "previous_geometry_candidate": relative(OUT_DIR.parent / "strict-pocket" / "strict-pocket-artwork.png"),
        "previous_geometry_overlay": relative(OUT_DIR.parent / "strict-pocket" / "strict-pocket-overlay.png"),
        "style_refs": [relative(path) for path in REF_PATHS],
        "manifest_status": manifest.get("status"),
        "viewbox": list(viewbox),
        "canvas_size_px": list(size),
        "path_roles": {
            "path[0]": "outer material contour",
            "path[1]": "large diagonal rounded slot keep-clear",
            "path[2]": "lower-right round/bolt-like keep-clear",
        },
        "rendering_strategy": [
            "Fresh reference-style redraw rather than palette shifting the strict-pocket output.",
            "Watercolor paper grain, translucent blue washes, dark uneven contour ink, and inner edge bloom.",
            "Rounded raised hardware with dark bases, soft shadows, white highlights, and red/yellow/teal accents.",
            "Lower-middle large buttons are shifted right into the paintable bay that the previous proof avoided.",
        ],
        "paintable_mask": {
            "outer_pixels": count_nonzero(outer_mask),
            "path1_cutout_pixels": count_nonzero(path1_mask),
            "path2_cutout_pixels": count_nonzero(path2_mask),
            "combined_cutout_pixels": count_nonzero(cutouts_mask),
            "paintable_pixels": count_nonzero(paintable_mask),
            "control_margin_px": control_margin_px,
            "eroded_control_safe_pixels": count_nonzero(paintable_safe),
        },
        "safe_pocket_plan": manifest.get("safe_pockets", []),
        "no_focal_motif_zones": manifest.get("no_focal_motif_zones", []),
        "decorative_controls": controls_meta,
        "summary": {
            "planned_controls": len(controls_meta),
            "accepted_controls": len(accepted_controls),
            "rejected_controls": len(rejected_controls),
            "accepted_control_escape_pixels": sum(record["outside_eroded_paintable_pixels"] for record in accepted_controls),
            "accepted_control_cutout_pixels": sum(record["inside_cutout_pixels"] for record in accepted_controls),
            "final_outside_outer_alpha_pixels": count_nonzero(final_outside_outer),
            "final_path1_cutout_alpha_pixels": count_nonzero(final_path1),
            "final_path2_cutout_alpha_pixels": count_nonzero(final_path2),
            "final_cutout_alpha_pixels": count_nonzero(final_cutouts),
            "final_outside_paintable_alpha_pixels": count_nonzero(final_outside_paintable),
        },
        "outputs": {
            "artwork": ARTWORK_PATH.name,
            "overlay": OVERLAY_PATH.name,
            "mask_debug": MASK_DEBUG_PATH.name,
            "metadata": METADATA_PATH.name,
        },
        "method_notes": [
            "Decorative controls are mask-tested against the eroded paintable mask before painting.",
            "The panel wash is quiet background texture and is clipped only as an export guardrail.",
            "Visible motifs and hardware are placed in named manifest pockets, away from path[1] and path[2].",
        ],
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    art.save(ARTWORK_PATH)
    overlay.save(OVERLAY_PATH)
    debug.save(MASK_DEBUG_PATH)
    METADATA_PATH.write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def main() -> None:
    metadata = make_outputs()
    print(json.dumps(metadata["summary"], indent=2))


if __name__ == "__main__":
    main()
