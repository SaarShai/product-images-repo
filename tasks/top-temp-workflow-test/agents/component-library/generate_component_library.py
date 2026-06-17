#!/usr/bin/env python3
"""Component-library proof for the top-temp SVG template.

The test separates style from geometry:
1. Draw reusable watercolor control sprites on a contact sheet.
2. Place only sprite instances whose full bounding boxes fit named pockets.
3. Reject any placed sprite whose mask crosses the eroded paintable SVG mask.
"""

from __future__ import annotations

import json
import math
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


OUT_DIR = Path(__file__).resolve().parent
TASK_DIR = OUT_DIR.parent.parent
ROOT = TASK_DIR.parent.parent
SVG_PATH = TASK_DIR / "source" / "template.svg"
MANIFEST_PATH = TASK_DIR / "template-manifest.json"
GEOMETRY_REPORT_PATH = TASK_DIR / "svg-geometry-report.md"
REF_PATHS = [
    TASK_DIR / "refs" / "ChatGPT Image Jun 9, 2026, 11_19_45 PM.png",
    TASK_DIR / "refs" / "ChatGPT Image Jun 9, 2026, 11_17_34 PM.png",
]

SHEET_PATH = OUT_DIR / "component-library-sheet.png"
ARTWORK_PATH = OUT_DIR / "component-library-artwork.png"
OVERLAY_PATH = OUT_DIR / "component-library-overlay.png"
MASK_DEBUG_PATH = OUT_DIR / "component-library-mask-debug.png"
METADATA_PATH = OUT_DIR / "component-library-metadata.json"

TOKEN_RE = re.compile(
    r"[MmLlHhVvCcSsQqTtZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"
)

RNG = random.Random(44)


@dataclass(frozen=True)
class SvgPath:
    index: int
    role: str
    points: list[tuple[float, float]]
    bounds: tuple[float, float, float, float]


@dataclass(frozen=True)
class Component:
    key: str
    family: str
    display_name: str
    size: tuple[int, int]
    image: Image.Image
    mask: Image.Image
    style_notes: list[str]


@dataclass(frozen=True)
class PlacementPlan:
    name: str
    component_key: str
    pocket: str
    xy: tuple[int, int]


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def is_command(token: str) -> bool:
    return len(token) == 1 and token.isalpha()


def parse_viewbox(svg_text: str) -> tuple[float, float, float, float]:
    match = re.search(r'viewBox="([^"]+)"', svg_text)
    if not match:
        raise ValueError("SVG has no viewBox")
    values = [float(part) for part in re.split(r"[,\s]+", match.group(1).strip())]
    if len(values) != 4:
        raise ValueError(f"Unexpected viewBox: {match.group(1)}")
    return tuple(values)  # type: ignore[return-value]


def extract_path_data(svg_text: str) -> list[str]:
    paths = re.findall(r"<path\b[^>]*\sd=\"([^\"]+)\"", svg_text)
    if len(paths) < 3:
        raise ValueError(f"Expected at least 3 paths, found {len(paths)}")
    return paths


def cubic(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    mt = 1.0 - t
    return (
        mt * mt * mt * p0[0]
        + 3 * mt * mt * t * p1[0]
        + 3 * mt * t * t * p2[0]
        + t * t * t * p3[0],
        mt * mt * mt * p0[1]
        + 3 * mt * mt * t * p1[1]
        + 3 * mt * t * t * p2[1]
        + t * t * t * p3[1],
    )


def sample_svg_path(d: str, curve_steps: int = 32) -> list[tuple[float, float]]:
    tokens = TOKEN_RE.findall(d)
    points: list[tuple[float, float]] = []
    i = 0
    command = ""
    current = (0.0, 0.0)
    start = (0.0, 0.0)
    last_cubic_ctrl: tuple[float, float] | None = None
    previous_command = ""

    def read_float() -> float:
        nonlocal i
        value = float(tokens[i])
        i += 1
        return value

    def has_number() -> bool:
        return i < len(tokens) and not is_command(tokens[i])

    while i < len(tokens):
        if is_command(tokens[i]):
            command = tokens[i]
            i += 1
        absolute = command.isupper()
        op = command.upper()

        if op == "M":
            first = True
            while has_number():
                x = read_float()
                y = read_float()
                if not absolute:
                    x += current[0]
                    y += current[1]
                current = (x, y)
                if first:
                    start = current
                    first = False
                points.append(current)
                command = "L" if absolute else "l"
            last_cubic_ctrl = None
            previous_command = "M"
            continue

        if op == "L":
            while has_number():
                x = read_float()
                y = read_float()
                if not absolute:
                    x += current[0]
                    y += current[1]
                current = (x, y)
                points.append(current)
            last_cubic_ctrl = None
            previous_command = "L"
            continue

        if op == "H":
            while has_number():
                x = read_float()
                if not absolute:
                    x += current[0]
                current = (x, current[1])
                points.append(current)
            last_cubic_ctrl = None
            previous_command = "H"
            continue

        if op == "V":
            while has_number():
                y = read_float()
                if not absolute:
                    y += current[1]
                current = (current[0], y)
                points.append(current)
            last_cubic_ctrl = None
            previous_command = "V"
            continue

        if op == "C":
            while has_number():
                x1, y1 = read_float(), read_float()
                x2, y2 = read_float(), read_float()
                x, y = read_float(), read_float()
                if not absolute:
                    x1 += current[0]
                    y1 += current[1]
                    x2 += current[0]
                    y2 += current[1]
                    x += current[0]
                    y += current[1]
                p0 = current
                p1 = (x1, y1)
                p2 = (x2, y2)
                p3 = (x, y)
                for step in range(1, curve_steps + 1):
                    points.append(cubic(p0, p1, p2, p3, step / curve_steps))
                current = p3
                last_cubic_ctrl = p2
            previous_command = "C"
            continue

        if op == "S":
            while has_number():
                x2, y2 = read_float(), read_float()
                x, y = read_float(), read_float()
                if previous_command in {"C", "S"} and last_cubic_ctrl is not None:
                    x1 = 2 * current[0] - last_cubic_ctrl[0]
                    y1 = 2 * current[1] - last_cubic_ctrl[1]
                else:
                    x1, y1 = current
                if not absolute:
                    x2 += current[0]
                    y2 += current[1]
                    x += current[0]
                    y += current[1]
                p0 = current
                p1 = (x1, y1)
                p2 = (x2, y2)
                p3 = (x, y)
                for step in range(1, curve_steps + 1):
                    points.append(cubic(p0, p1, p2, p3, step / curve_steps))
                current = p3
                last_cubic_ctrl = p2
            previous_command = "S"
            continue

        if op == "Q":
            while has_number():
                x1, y1 = read_float(), read_float()
                x, y = read_float(), read_float()
                if not absolute:
                    x1 += current[0]
                    y1 += current[1]
                    x += current[0]
                    y += current[1]
                p0 = current
                p1 = (x1, y1)
                p2 = (x, y)
                for step in range(1, curve_steps + 1):
                    t = step / curve_steps
                    mt = 1.0 - t
                    points.append(
                        (
                            mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0],
                            mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1],
                        )
                    )
                current = p2
                last_cubic_ctrl = None
            previous_command = "Q"
            continue

        if op == "Z":
            current = start
            points.append(start)
            command = ""
            last_cubic_ctrl = None
            previous_command = "Z"
            continue

        raise ValueError(f"Unsupported SVG path command: {command}")

    if points and points[0] != points[-1]:
        points.append(points[0])
    return points


def bounds(points: Iterable[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def load_svg_paths() -> tuple[tuple[int, int], list[SvgPath]]:
    svg_text = SVG_PATH.read_text()
    _, _, width, height = parse_viewbox(svg_text)
    size = (math.ceil(width), math.ceil(height))
    roles = [
        "outer material contour",
        "large diagonal rounded slot keep-clear",
        "lower-right round/bolt-like keep-clear",
    ]
    paths = []
    for index, path_d in enumerate(extract_path_data(svg_text)[:3]):
        points = sample_svg_path(path_d)
        paths.append(
            SvgPath(
                index=index,
                role=roles[index],
                points=points,
                bounds=bounds(points),
            )
        )
    return size, paths


def polygon_mask(size: tuple[int, int], paths: Iterable[SvgPath]) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for path in paths:
        draw.polygon([(round(x), round(y)) for x, y in path.points], fill=255)
    return mask


def count(mask: Image.Image) -> int:
    return int(np.count_nonzero(np.asarray(mask)))


def erode(mask: Image.Image, pixels: int) -> Image.Image:
    return mask.filter(ImageFilter.MinFilter(pixels * 2 + 1))


def compose_alpha(color: tuple[int, int, int], alpha: Image.Image) -> Image.Image:
    size = alpha.size
    return Image.merge(
        "RGBA",
        (
            Image.new("L", size, color[0]),
            Image.new("L", size, color[1]),
            Image.new("L", size, color[2]),
            alpha,
        ),
    )


def rough_ellipse_points(
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    seed: int,
    amp: float = 1.8,
    steps: int = 72,
) -> list[tuple[float, float]]:
    rng = random.Random(seed)
    pts = []
    for step in range(steps):
        angle = math.tau * step / steps
        wobble = rng.uniform(-amp, amp)
        pts.append((cx + math.cos(angle) * (rx + wobble), cy + math.sin(angle) * (ry + wobble)))
    pts.append(pts[0])
    return pts


def rough_rounded_rectangle(
    draw: ImageDraw.ImageDraw,
    bbox: tuple[int, int, int, int],
    radius: int,
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int] | None = None,
    width: int = 1,
    seed: int = 0,
) -> None:
    draw.rounded_rectangle(bbox, radius=radius, fill=fill)
    if outline:
        rng = random.Random(seed)
        for _ in range(4):
            dx = rng.randint(-2, 2)
            dy = rng.randint(-2, 2)
            grow = rng.randint(0, 2)
            obox = (bbox[0] - grow + dx, bbox[1] - grow + dy, bbox[2] + grow + dx, bbox[3] + grow + dy)
            draw.rounded_rectangle(obox, radius=radius + grow, outline=outline, width=width)


def add_texture(image: Image.Image, mask: Image.Image, seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    arr = np.array(image.convert("RGBA"), dtype=np.int16)
    h, w = arr.shape[:2]
    coarse = rng.normal(0, 1, (max(2, h // 9), max(2, w // 9)))
    coarse = Image.fromarray(np.uint8((coarse - coarse.min()) / (coarse.max() - coarse.min()) * 255))
    coarse = coarse.resize((w, h), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(1.2))
    n = np.array(coarse, dtype=np.int16) - 127
    arr[:, :, :3] = np.clip(arr[:, :, :3] + n[:, :, None] // 9, 0, 255)
    alpha = np.array(mask, dtype=np.uint8)
    arr[:, :, 3] = np.minimum(arr[:, :, 3], alpha)
    return Image.fromarray(arr.astype(np.uint8))


def make_mask(size: tuple[int, int]) -> Image.Image:
    return Image.new("L", size, 0)


def component_from_layers(
    key: str,
    family: str,
    display_name: str,
    image: Image.Image,
    mask: Image.Image,
    style_notes: list[str],
) -> Component:
    stable_seed = sum((index + 1) * ord(char) for index, char in enumerate(key))
    image = add_texture(image, mask, seed=stable_seed)
    return Component(key, family, display_name, image.size, image, mask, style_notes)


def make_dial() -> Component:
    size = (206, 206)
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    mask = make_mask(size)
    draw = ImageDraw.Draw(image, "RGBA")
    mdraw = ImageDraw.Draw(mask)
    cx, cy, r = 103, 104, 82
    draw.ellipse((cx - r - 9, cy - r + 8, cx + r + 11, cy + r + 22), fill=(8, 50, 111, 70))
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(188, 221, 243, 248))
    for width, alpha, seed in [(8, 235, 100), (4, 180, 101), (2, 130, 102)]:
        pts = rough_ellipse_points(cx, cy, r, r, seed, amp=2.1)
        draw.line(pts, fill=(12, 61, 126, alpha), width=width, joint="curve")
    draw.ellipse((cx - 56, cy - 56, cx + 56, cy + 56), outline=(47, 105, 178, 150), width=4)
    for deg in range(0, 360, 45):
        angle = math.radians(deg - 90)
        draw.line(
            (
                cx + math.cos(angle) * 51,
                cy + math.sin(angle) * 51,
                cx + math.cos(angle) * 67,
                cy + math.sin(angle) * 67,
            ),
            fill=(18, 65, 126, 210),
            width=5,
        )
    needle = math.radians(-42)
    draw.line(
        (cx, cy, cx + math.cos(needle) * 56, cy + math.sin(needle) * 56),
        fill=(15, 61, 123, 232),
        width=9,
    )
    draw.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), fill=(24, 75, 143, 255))
    draw.arc((36, 30, 165, 162), 205, 295, fill=(255, 255, 255, 135), width=8)
    mdraw.ellipse((cx - r - 10, cy - r - 10, cx + r + 10, cy + r + 10), fill=255)
    return component_from_layers(
        "dial",
        "dial",
        "pale-blue dial",
        image,
        mask,
        ["round gauge face", "navy irregular ring", "white watercolor highlight", "simple needle/ticks"],
    )


def make_slider() -> Component:
    size = (360, 84)
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    mask = make_mask(size)
    draw = ImageDraw.Draw(image, "RGBA")
    mdraw = ImageDraw.Draw(mask)
    rough_rounded_rectangle(draw, (18, 35, 340, 56), 11, (40, 105, 184, 132), (13, 61, 125, 205), 4, 210)
    rough_rounded_rectangle(draw, (34, 40, 326, 49), 5, (184, 221, 246, 110), None)
    for x, color, seed in [
        (112, (244, 95, 91, 255), 221),
        (238, (91, 206, 188, 255), 222),
    ]:
        rough_rounded_rectangle(draw, (x - 21, 20, x + 21, 63), 10, (16, 65, 130, 230), None)
        rough_rounded_rectangle(draw, (x - 16, 17, x + 16, 57), 9, color, (12, 67, 127, 210), 3, seed)
        draw.rounded_rectangle((x - 9, 23, x + 7, 32), 5, fill=(255, 255, 255, 90))
    mdraw.rounded_rectangle((14, 16, 344, 66), radius=13, fill=255)
    return component_from_layers(
        "slider",
        "slider",
        "two-knob slider",
        image,
        mask,
        ["long soft rail", "tiny rounded knobs", "mint/coral accent colors", "pooled navy shadows"],
    )


def make_capsule(key: str, display: str, color: tuple[int, int, int, int]) -> Component:
    size = (260, 92)
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    mask = make_mask(size)
    draw = ImageDraw.Draw(image, "RGBA")
    mdraw = ImageDraw.Draw(mask)
    rough_rounded_rectangle(draw, (14, 24, 246, 80), 27, (8, 50, 111, 78), None)
    rough_rounded_rectangle(draw, (10, 13, 250, 72), 29, (16, 66, 132, 245), None)
    rough_rounded_rectangle(draw, (22, 21, 238, 62), 22, color, (12, 61, 124, 205), 4, 310)
    draw.rounded_rectangle((44, 27, 214, 39), 8, fill=(255, 255, 255, 82))
    draw.arc((28, 21, 236, 65), 200, 315, fill=(255, 255, 255, 94), width=5)
    mdraw.rounded_rectangle((8, 12, 252, 76), radius=31, fill=255)
    family = "capsule button"
    return component_from_layers(
        key,
        family,
        display,
        image,
        mask,
        ["rounded pill button", "glossy top wash", "thick hand-inked navy rim"],
    )


def make_bolt() -> Component:
    size = (72, 72)
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    mask = make_mask(size)
    draw = ImageDraw.Draw(image, "RGBA")
    mdraw = ImageDraw.Draw(mask)
    cx, cy, r = 36, 36, 27
    draw.ellipse((cx - r - 5, cy - r + 5, cx + r + 5, cy + r + 12), fill=(8, 50, 111, 72))
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(199, 227, 246, 250))
    draw.line(rough_ellipse_points(cx, cy, r, r, 410, amp=1.2), fill=(12, 61, 126, 230), width=5)
    draw.line((18, 49, 54, 23), fill=(46, 103, 174, 220), width=6)
    draw.arc((13, 10, 59, 55), 205, 296, fill=(255, 255, 255, 130), width=4)
    mdraw.ellipse((cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4), fill=255)
    return component_from_layers(
        "bolt",
        "bolt",
        "slotted bolt",
        image,
        mask,
        ["small screw head", "navy slotted mark", "pale glossy metal fill"],
    )


def make_pin(key: str, display: str, color: tuple[int, int, int, int]) -> Component:
    size = (92, 150)
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    mask = make_mask(size)
    draw = ImageDraw.Draw(image, "RGBA")
    mdraw = ImageDraw.Draw(mask)
    rough_rounded_rectangle(draw, (15, 102, 77, 139), 20, (8, 50, 111, 76), None)
    rough_rounded_rectangle(draw, (19, 92, 73, 133), 21, (18, 67, 134, 236), (10, 56, 118, 210), 3, 510)
    rough_rounded_rectangle(draw, (29, 13, 64, 116), 18, color, (11, 61, 125, 230), 5, 511)
    draw.ellipse((34, 17, 61, 39), fill=(255, 255, 255, 82))
    draw.line((39, 45, 39, 99), fill=(255, 255, 255, 82), width=5)
    mdraw.rounded_rectangle((15, 12, 77, 139), radius=22, fill=255)
    return component_from_layers(
        key,
        "colored pin",
        display,
        image,
        mask,
        ["upright rounded control pin", "navy base shadow", "candy-color watercolor body"],
    )


def make_components() -> dict[str, Component]:
    components = [
        make_dial(),
        make_slider(),
        make_capsule("capsule_coral", "coral capsule button", (245, 96, 91, 255)),
        make_capsule("capsule_mint", "mint capsule button", (91, 206, 188, 255)),
        make_bolt(),
        make_pin("pin_coral", "coral colored pin", (244, 94, 91, 255)),
        make_pin("pin_yellow", "yellow colored pin", (249, 194, 65, 255)),
        make_pin("pin_mint", "mint colored pin", (91, 206, 188, 255)),
    ]
    return {component.key: component for component in components}


def watercolor_background(size: tuple[int, int], allowed_mask: Image.Image) -> Image.Image:
    width, height = size
    rng = np.random.default_rng(44)
    coarse = rng.normal(0, 1, (height // 24 + 3, width // 24 + 3))
    coarse = Image.fromarray(np.uint8((coarse - coarse.min()) / (coarse.max() - coarse.min()) * 255))
    coarse = coarse.resize(size, Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(5))
    n = np.asarray(coarse, dtype=np.float32) / 255.0
    light = np.array([154, 205, 240], dtype=np.float32)
    mid = np.array([86, 154, 218], dtype=np.float32)
    deep = np.array([35, 91, 164], dtype=np.float32)
    rgb = light[None, None, :] * (1 - n[:, :, None]) + mid[None, None, :] * n[:, :, None]
    rgb = rgb * 0.86 + deep[None, None, :] * (0.14 * n[:, :, None])
    arr = np.zeros((height, width, 4), dtype=np.uint8)
    arr[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    arr[:, :, 3] = np.asarray(allowed_mask)
    image = Image.fromarray(arr)
    wash = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(wash, "RGBA")
    for _ in range(70):
        x = RNG.randint(40, width - 40)
        y = RNG.randint(40, height - 40)
        rx = RNG.randint(70, 240)
        ry = RNG.randint(35, 150)
        color = RNG.choice([(204, 228, 248, 26), (38, 92, 164, 22), (112, 170, 225, 24)])
        draw.ellipse((x - rx, y - ry, x + rx, y + ry), fill=color)
    wash = wash.filter(ImageFilter.GaussianBlur(18))
    image = Image.alpha_composite(image, wash)
    image.putalpha(allowed_mask)
    return image


def draw_path_stroke(layer: Image.Image, path: SvgPath, fill: tuple[int, int, int, int], width: int) -> None:
    draw = ImageDraw.Draw(layer, "RGBA")
    coords = [(round(x), round(y)) for x, y in path.points]
    draw.line(coords, fill=fill, width=width, joint="curve")


def paste_component(
    art: Image.Image,
    motif_mask: Image.Image,
    component: Component,
    xy: tuple[int, int],
) -> Image.Image:
    x, y = xy
    layer = Image.new("RGBA", art.size, (0, 0, 0, 0))
    layer.alpha_composite(component.image, dest=xy)
    art = Image.alpha_composite(art, layer)
    placed_mask = Image.new("L", art.size, 0)
    placed_mask.paste(component.mask, xy)
    motif_mask.paste(ImageChops.lighter(motif_mask.crop((x, y, x + component.size[0], y + component.size[1])), component.mask), xy)
    return art


def placed_mask(size: tuple[int, int], component: Component, xy: tuple[int, int]) -> Image.Image:
    mask = Image.new("L", size, 0)
    mask.paste(component.mask, xy)
    return mask


def bbox_for(component: Component, xy: tuple[int, int]) -> tuple[int, int, int, int]:
    x, y = xy
    return (x, y, x + component.size[0], y + component.size[1])


def bbox_inside(inner: tuple[int, int, int, int], outer: tuple[int, int, int, int]) -> bool:
    return inner[0] >= outer[0] and inner[1] >= outer[1] and inner[2] <= outer[2] and inner[3] <= outer[3]


def plans() -> list[PlacementPlan]:
    return [
        PlacementPlan("upper coral pin", "pin_coral", "upper-left tall bay above the left shoulder of the slot", (420, 145)),
        PlacementPlan("upper yellow pin", "pin_yellow", "upper-left tall bay above the left shoulder of the slot", (542, 160)),
        PlacementPlan("middle-left slider", "slider", "middle-left field below/left of the diagonal slot", (255, 745)),
        PlacementPlan("lower-left dial", "dial", "lower-left base bay above the bottom notch", (365, 1170)),
        PlacementPlan("lower-middle mint capsule", "capsule_mint", "lower-middle bay between the bottom notch and the right cutouts", (1015, 1138)),
        PlacementPlan("lower-middle coral capsule", "capsule_coral", "lower-middle bay between the bottom notch and the right cutouts", (1000, 1290)),
        PlacementPlan("lower-left bolt", "bolt", "lower-left base bay above the bottom notch", (112, 1234)),
    ]


def pocket_boxes() -> dict[str, tuple[int, int, int, int]]:
    return {
        "upper-left tall bay above the left shoulder of the slot": (398, 118, 650, 314),
        "middle-left field below/left of the diagonal slot": (226, 696, 742, 960),
        "lower-left base bay above the bottom notch": (74, 1138, 632, 1452),
        "lower-middle bay between the bottom notch and the right cutouts": (890, 1092, 1328, 1396),
        "right vertical strip between the diagonal slot and outer edge": (1490, 1068, 1576, 1450),
    }


def measure_placement(
    size: tuple[int, int],
    plan: PlacementPlan,
    component: Component,
    pocket_bbox: tuple[int, int, int, int],
    outer: Image.Image,
    cutouts: Image.Image,
    safe_mask: Image.Image,
) -> dict[str, object]:
    pmask = placed_mask(size, component, plan.xy)
    bbox = bbox_for(component, plan.xy)
    outside_outer = ImageChops.subtract(pmask, outer)
    inside_cutouts = ImageChops.multiply(pmask, cutouts)
    outside_safe = ImageChops.subtract(pmask, safe_mask)
    bbox_fits_pocket = bbox_inside(bbox, pocket_bbox)
    return {
        "name": plan.name,
        "component_key": component.key,
        "component_family": component.family,
        "pocket": plan.pocket,
        "bbox": list(bbox),
        "pocket_bbox": list(pocket_bbox),
        "bbox_fits_named_pocket": bbox_fits_pocket,
        "mask_pixels": count(pmask),
        "outside_outer_pixels": count(outside_outer),
        "inside_cutout_pixels": count(inside_cutouts),
        "outside_eroded_paintable_pixels": count(outside_safe),
    }


def dashed_line(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[float, float]],
    fill: tuple[int, int, int, int],
    width: int,
    dash: int = 22,
    gap: int = 14,
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


def make_component_sheet(components: dict[str, Component]) -> None:
    order = ["dial", "slider", "capsule_coral", "bolt", "pin_coral", "pin_yellow", "pin_mint"]
    sheet = Image.new("RGBA", (1180, 520), (250, 250, 247, 255))
    draw = ImageDraw.Draw(sheet, "RGBA")
    font = ImageFont.load_default()
    draw.text((32, 26), "component library: reusable watercolor control sprites", fill=(14, 61, 126, 240), font=font)
    draw.text((32, 46), "sprites are rendered before template composition", fill=(50, 80, 110, 210), font=font)
    boxes = [
        (36, 86, 286, 350),
        (316, 86, 760, 230),
        (316, 270, 650, 404),
        (706, 270, 846, 404),
        (846, 82, 968, 270),
        (980, 82, 1102, 270),
        (980, 286, 1102, 474),
    ]
    for key, box in zip(order, boxes):
        component = components[key]
        x0, y0, x1, y1 = box
        draw.rounded_rectangle(box, radius=8, fill=(232, 241, 248, 255), outline=(35, 91, 164, 120), width=2)
        px = x0 + (x1 - x0 - component.size[0]) // 2
        py = y0 + (y1 - y0 - component.size[1]) // 2 - 8
        sheet.alpha_composite(component.image, (px, py))
        draw.text((x0 + 12, y1 - 26), component.display_name, fill=(13, 61, 126, 235), font=font)
    SHEET_PATH.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(SHEET_PATH)


def make_overlay(art: Image.Image, paths: list[SvgPath], cutouts: Image.Image) -> Image.Image:
    overlay = Image.new("RGBA", art.size, (252, 252, 248, 255))
    overlay.alpha_composite(art)
    red = compose_alpha((255, 72, 72), cutouts.point(lambda p: 70 if p else 0))
    overlay.alpha_composite(red)
    draw = ImageDraw.Draw(overlay, "RGBA")
    dashed_line(draw, paths[0].points, (255, 219, 85, 255), 8)
    for path in paths[1:]:
        dashed_line(draw, path.points, (255, 70, 70, 245), 8)
    return overlay.convert("RGB")


def make_mask_debug(
    size: tuple[int, int],
    outer: Image.Image,
    allowed: Image.Image,
    cutouts: Image.Image,
    safe: Image.Image,
    motif_mask: Image.Image,
    placement_records: list[dict[str, object]],
    pockets: dict[str, tuple[int, int, int, int]],
) -> Image.Image:
    outer_arr = np.asarray(outer) > 0
    allowed_arr = np.asarray(allowed) > 0
    cutout_arr = np.asarray(cutouts) > 0
    safe_arr = np.asarray(safe) > 0
    motif_arr = np.asarray(motif_mask) > 0
    canvas = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    canvas[:, :] = np.array([36, 38, 44, 255], dtype=np.uint8)
    canvas[outer_arr] = np.array([58, 92, 126, 255], dtype=np.uint8)
    canvas[allowed_arr] = np.array([94, 158, 218, 255], dtype=np.uint8)
    canvas[safe_arr] = np.array([101, 184, 176, 255], dtype=np.uint8)
    canvas[cutout_arr] = np.array([240, 78, 78, 255], dtype=np.uint8)
    canvas[motif_arr & safe_arr] = np.array([16, 54, 96, 255], dtype=np.uint8)
    image = Image.fromarray(canvas)
    draw = ImageDraw.Draw(image, "RGBA")
    font = ImageFont.load_default()
    for bbox in pockets.values():
        draw.rounded_rectangle(bbox, radius=14, outline=(255, 255, 255, 155), width=3)
    for record in placement_records:
        bbox = tuple(record["bbox"])  # type: ignore[arg-type]
        accepted = bool(record["accepted"])
        color = (255, 255, 255, 225) if accepted else (250, 196, 65, 230)
        draw.rectangle(bbox, outline=color, width=3)
    draw.text(
        (18, 18),
        "debug: teal=eroded safe paintable, red=cutouts, navy=accepted sprite masks, white boxes=named pockets",
        fill=(255, 255, 255, 235),
        font=font,
    )
    return image.convert("RGB")


def build_artwork() -> dict[str, object]:
    manifest = json.loads(MANIFEST_PATH.read_text())
    size, paths = load_svg_paths()
    components = make_components()
    make_component_sheet(components)

    outer = polygon_mask(size, [paths[0]])
    cutouts = polygon_mask(size, paths[1:])
    allowed_arr = np.asarray(outer).copy()
    allowed_arr[np.asarray(cutouts) > 0] = 0
    allowed = Image.fromarray(allowed_arr.astype(np.uint8))
    margin_px = 24
    safe = erode(allowed, margin_px)

    art = watercolor_background(size, allowed)
    line_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw_path_stroke(line_layer, paths[0], (8, 54, 118, 205), 18)
    draw_path_stroke(line_layer, paths[0], (181, 222, 250, 90), 5)
    for path in paths[1:]:
        draw_path_stroke(line_layer, path, (8, 54, 118, 215), 15)
        draw_path_stroke(line_layer, path, (218, 238, 252, 92), 4)
    line_layer.putalpha(ImageChops.multiply(line_layer.getchannel("A"), allowed))
    art = Image.alpha_composite(art, line_layer)

    motif_mask = Image.new("L", size, 0)
    placement_records: list[dict[str, object]] = []
    pockets = pocket_boxes()
    for plan in plans():
        component = components[plan.component_key]
        record = measure_placement(size, plan, component, pockets[plan.pocket], outer, cutouts, safe)
        accepted = (
            record["bbox_fits_named_pocket"]
            and record["outside_eroded_paintable_pixels"] == 0
            and record["inside_cutout_pixels"] == 0
            and record["outside_outer_pixels"] == 0
        )
        record["accepted"] = bool(accepted)
        if accepted:
            art = paste_component(art, motif_mask, component, plan.xy)
        placement_records.append(record)

    final_alpha = ImageChops.multiply(art.getchannel("A"), allowed)
    art.putalpha(final_alpha)
    overlay = make_overlay(art, paths, cutouts)
    debug = make_mask_debug(size, outer, allowed, cutouts, safe, motif_mask, placement_records, pockets)

    outside_allowed = ImageChops.subtract(art.getchannel("A"), allowed)
    inside_cutouts = ImageChops.multiply(art.getchannel("A"), cutouts)
    motif_outside_safe = ImageChops.subtract(motif_mask, safe)
    motif_inside_cutouts = ImageChops.multiply(motif_mask, cutouts)
    accepted_records = [r for r in placement_records if r["accepted"]]
    rejected_records = [r for r in placement_records if not r["accepted"]]
    family_set = sorted({components[r["component_key"]].family for r in accepted_records})
    required_families = ["bolt", "capsule button", "colored pin", "dial", "slider"]
    missing_families = [family for family in required_families if family not in family_set]

    metadata = {
        "workflow": "component-library-pocket-fit-test",
        "source_svg": rel(SVG_PATH),
        "template_manifest": rel(MANIFEST_PATH),
        "geometry_report": rel(GEOMETRY_REPORT_PATH),
        "style_refs": [rel(p) for p in REF_PATHS],
        "manifest_status": manifest.get("status"),
        "canvas_size_px": list(size),
        "path_roles": {
            "path[0]": paths[0].role,
            "path[1]": paths[1].role,
            "path[2]": paths[2].role,
        },
        "svg_path_bounds": [
            {"path_index": path.index, "role": path.role, "bounds": [round(v, 2) for v in path.bounds]}
            for path in paths
        ],
        "component_library": [
            {
                "key": component.key,
                "family": component.family,
                "display_name": component.display_name,
                "size": list(component.size),
                "style_notes": component.style_notes,
            }
            for component in components.values()
        ],
        "safe_pockets_from_manifest": manifest.get("safe_pockets", []),
        "pocket_bboxes_used_for_bbox_fit": {key: list(value) for key, value in pockets.items()},
        "placement_records": placement_records,
        "summary": {
            "planned_instances": len(placement_records),
            "accepted_instances": len(accepted_records),
            "rejected_instances": len(rejected_records),
            "accepted_families": family_set,
            "missing_required_families": missing_families,
            "outer_pixels": count(outer),
            "cutout_pixels": count(cutouts),
            "paintable_pixels": count(allowed),
            "component_margin_px": margin_px,
            "eroded_safe_pixels": count(safe),
            "accepted_component_outside_eroded_paintable_pixels": sum(
                int(r["outside_eroded_paintable_pixels"]) for r in accepted_records
            ),
            "accepted_component_cutout_pixels": sum(int(r["inside_cutout_pixels"]) for r in accepted_records),
            "focal_motif_pixels_outside_eroded_paintable": count(motif_outside_safe),
            "focal_motif_pixels_inside_cutouts": count(motif_inside_cutouts),
            "final_outside_paintable_alpha_pixels": count(outside_allowed),
            "final_cutout_alpha_pixels": count(inside_cutouts),
            "mechanical_gate_pass": (
                len(missing_families) == 0
                and len(accepted_records) > 0
                and sum(int(r["outside_eroded_paintable_pixels"]) for r in accepted_records) == 0
                and sum(int(r["inside_cutout_pixels"]) for r in accepted_records) == 0
                and count(motif_outside_safe) == 0
                and count(motif_inside_cutouts) == 0
                and count(outside_allowed) == 0
                and count(inside_cutouts) == 0
            ),
        },
        "outputs": {
            "component_sheet": SHEET_PATH.name,
            "artwork": ARTWORK_PATH.name,
            "overlay": OVERLAY_PATH.name,
            "mask_debug": MASK_DEBUG_PATH.name,
            "metadata": METADATA_PATH.name,
        },
        "method_notes": [
            "The contact sheet is rendered before any template composition.",
            "Each planned instance is checked for bbox containment inside a named pocket.",
            "Accepted sprite masks must have zero pixels outside the eroded paintable mask.",
            "The blue watercolor body is quiet background clipped to paintable material; focal controls are sprite instances only.",
        ],
    }

    art.convert("RGBA").save(ARTWORK_PATH)
    overlay.save(OVERLAY_PATH)
    debug.save(MASK_DEBUG_PATH)
    METADATA_PATH.write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def main() -> None:
    metadata = build_artwork()
    print(json.dumps(metadata["summary"], indent=2))


if __name__ == "__main__":
    main()
