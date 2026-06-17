#!/usr/bin/env python3
"""Strict pocket-planned procedural SVG-template proof.

The SVG path roles are taken from the task manifest:
- path[0]: outer material contour
- path[1]: large diagonal rounded slot cutout
- path[2]: lower-right round cutout

Decorative controls are drawn only if their local mask fits inside the eroded
paintable mask. The final SVG clip is kept as an export guardrail.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


OUT_DIR = Path(__file__).resolve().parent
TASK_DIR = OUT_DIR.parent.parent
SVG_PATH = TASK_DIR / "source" / "template.svg"
MANIFEST_PATH = TASK_DIR / "template-manifest.json"
REF_PATHS = [
    TASK_DIR / "refs" / "ChatGPT Image Jun 9, 2026, 11_19_45 PM.png",
    TASK_DIR / "refs" / "ChatGPT Image Jun 9, 2026, 11_17_34 PM.png",
]

ARTWORK_PATH = OUT_DIR / "strict-pocket-artwork.png"
OVERLAY_PATH = OUT_DIR / "strict-pocket-overlay.png"
MASK_DEBUG_PATH = OUT_DIR / "strict-pocket-mask-debug.png"
METADATA_PATH = OUT_DIR / "strict-pocket-metadata.json"


TOKEN_RE = re.compile(
    r"[MmLlHhVvCcSsQqTtZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"
)


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
    x = (
        mt * mt * mt * p0[0]
        + 3 * mt * mt * t * p1[0]
        + 3 * mt * t * t * p2[0]
        + t * t * t * p3[0]
    )
    y = (
        mt * mt * mt * p0[1]
        + 3 * mt * mt * t * p1[1]
        + 3 * mt * t * t * p2[1]
        + t * t * t * p3[1]
    )
    return x, y


def sample_svg_path(d: str, curve_steps: int = 28) -> list[tuple[float, float]]:
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

        cmd = command
        absolute = cmd.isupper()
        op = cmd.upper()

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
            # Convert quadratic curves to a cubic-compatible sample.
            while has_number():
                x1, y1 = read_float(), read_float()
                x, y = read_float(), read_float()
                if not absolute:
                    x1 += current[0]
                    y1 += current[1]
                    x += current[0]
                    y += current[1]
                p0 = current
                q = (x1, y1)
                p3 = (x, y)
                for step in range(1, curve_steps + 1):
                    t = step / curve_steps
                    mt = 1 - t
                    points.append(
                        (
                            mt * mt * p0[0] + 2 * mt * t * q[0] + t * t * p3[0],
                            mt * mt * p0[1] + 2 * mt * t * q[1] + t * t * p3[1],
                        )
                    )
                current = p3
                last_cubic_ctrl = None
            previous_command = "Q"
            continue

        if op == "Z":
            current = start
            points.append(start)
            last_cubic_ctrl = None
            previous_command = "Z"
            command = ""
            continue

        raise ValueError(f"Unsupported SVG path command: {cmd}")

    if points and points[0] != points[-1]:
        points.append(points[0])
    return points


def draw_polygon_mask(size: tuple[int, int], points: Iterable[tuple[float, float]]) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon([(round(x), round(y)) for x, y in points], fill=255)
    return mask


def count_nonzero(mask: Image.Image) -> int:
    return int(np.count_nonzero(np.asarray(mask)))


def erode(mask: Image.Image, pixels: int) -> Image.Image:
    size = pixels * 2 + 1
    return mask.filter(ImageFilter.MinFilter(size))


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def build_watercolor_background(size: tuple[int, int], paintable: Image.Image) -> Image.Image:
    width, height = size
    rng = np.random.default_rng(63)
    small = rng.normal(0, 1, (math.ceil(height / 34), math.ceil(width / 34)))
    small = (small - small.min()) / (small.max() - small.min())
    noise = Image.fromarray(np.uint8(small * 255)).resize(size, Image.Resampling.BICUBIC)
    noise = noise.filter(ImageFilter.GaussianBlur(7))
    n = np.asarray(noise).astype(np.float32) / 255.0
    light = np.array([151, 207, 247], dtype=np.float32)
    mid = np.array([83, 158, 221], dtype=np.float32)
    dark = np.array([35, 95, 164], dtype=np.float32)
    rgb = (light * (1 - n[..., None]) + mid * n[..., None]).astype(np.uint8)
    rgb = np.minimum(255, rgb + rng.normal(0, 5, rgb.shape)).clip(0, 255).astype(np.uint8)
    image = Image.fromarray(rgb).convert("RGBA")

    wash = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(wash, "RGBA")
    for _ in range(90):
        cx = int(rng.integers(30, width - 30))
        cy = int(rng.integers(30, height - 30))
        rx = int(rng.integers(80, 260))
        ry = int(rng.integers(35, 160))
        color = tuple((dark if rng.random() < 0.35 else light).astype(int)) + (int(rng.integers(10, 35)),)
        d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=color)
    wash = wash.filter(ImageFilter.GaussianBlur(18))
    image = Image.alpha_composite(image, wash)
    image.putalpha(paintable)
    return image


@dataclass
class Control:
    name: str
    pocket: str
    draw_fn: Callable[[Image.Image, bool], None]
    role: str


def make_controls(size: tuple[int, int]) -> list[Control]:
    del size

    def slider_bank(layer: Image.Image, mask_mode: bool) -> None:
        d = ImageDraw.Draw(layer, "RGBA" if layer.mode == "RGBA" else None)
        fill = 255 if mask_mode else None
        rail_colors = [(218, 239, 255, 150), (50, 107, 181, 210), (21, 75, 146, 235)]
        knob_colors = [(255, 105, 91, 255), (252, 194, 58, 255), (91, 204, 180, 255)]
        x0, x1 = 250, 725
        y_values = [720, 792, 864, 936]
        knob_xs = [310, 465, 590, 690]
        for idx, y in enumerate(y_values):
            if mask_mode:
                d.line((x0, y, x1, y), fill=fill, width=18)
                d.rounded_rectangle((knob_xs[idx] - 20, y - 20, knob_xs[idx] + 20, y + 20), 8, fill=fill)
                continue
            d.line((x0, y + 6, x1, y + 6), fill=(18, 58, 117, 110), width=16)
            d.line((x0, y, x1, y), fill=rail_colors[1], width=12)
            d.line((x0 + 10, y - 4, x1 - 10, y - 4), fill=rail_colors[0], width=4)
            k = knob_xs[idx]
            c = knob_colors[idx % len(knob_colors)]
            rounded(d, (k - 21, y - 21, k + 21, y + 21), 8, (19, 67, 135, 230))
            rounded(d, (k - 17, y - 19, k + 17, y + 16), 7, c, (11, 70, 132, 230), 3)
            d.rounded_rectangle((k - 10, y - 16, k + 10, y - 8), 5, fill=(255, 255, 255, 90))

    def upper_lamps(layer: Image.Image, mask_mode: bool) -> None:
        d = ImageDraw.Draw(layer, "RGBA" if layer.mode == "RGBA" else None)
        fill = 255 if mask_mode else None
        for x, y, color in [
            (505, 160, (255, 99, 88, 255)),
            (585, 230, (250, 192, 63, 255)),
            (462, 270, (91, 204, 180, 255)),
        ]:
            if mask_mode:
                d.ellipse((x - 31, y - 31, x + 31, y + 31), fill=fill)
                continue
            d.ellipse((x - 31, y - 25, x + 31, y + 37), fill=(14, 64, 130, 120))
            d.ellipse((x - 28, y - 28, x + 28, y + 28), fill=(19, 72, 146, 235))
            d.ellipse((x - 21, y - 24, x + 21, y + 20), fill=color)
            d.ellipse((x - 13, y - 21, x + 4, y - 7), fill=(255, 255, 255, 125))

    def lower_left_gauge(layer: Image.Image, mask_mode: bool) -> None:
        d = ImageDraw.Draw(layer, "RGBA" if layer.mode == "RGBA" else None)
        cx, cy, r = 470, 1278, 116
        if mask_mode:
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
            for angle in range(-120, 121, 40):
                rad = math.radians(angle)
                x0 = cx + math.cos(rad) * (r + 16)
                y0 = cy + math.sin(rad) * (r + 16)
                x1 = cx + math.cos(rad) * (r + 50)
                y1 = cy + math.sin(rad) * (r + 50)
                d.line((x0, y0, x1, y1), fill=255, width=12)
            return
        d.ellipse((cx - r - 8, cy - r + 8, cx + r + 8, cy + r + 24), fill=(12, 49, 108, 90))
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(24, 79, 151, 245))
        d.ellipse((cx - r + 22, cy - r + 22, cx + r - 22, cy + r - 22), fill=(222, 242, 255, 245))
        d.arc((cx - r + 38, cy - r + 38, cx + r - 38, cy + r - 38), 205, 335, fill=(49, 105, 176, 255), width=9)
        for angle in range(-120, 121, 40):
            rad = math.radians(angle)
            x0 = cx + math.cos(rad) * (r - 40)
            y0 = cy + math.sin(rad) * (r - 40)
            x1 = cx + math.cos(rad) * (r - 22)
            y1 = cy + math.sin(rad) * (r - 22)
            d.line((x0, y0, x1, y1), fill=(15, 71, 142, 230), width=5)
        needle = math.radians(38)
        d.line((cx, cy, cx + math.cos(needle) * 64, cy + math.sin(needle) * 64), fill=(20, 63, 128, 255), width=8)
        d.ellipse((cx - 11, cy - 11, cx + 11, cy + 11), fill=(255, 191, 58, 255))
        d.ellipse((cx - 76, cy - 85, cx - 22, cy - 57), fill=(255, 255, 255, 110))

    def lower_middle_buttons(layer: Image.Image, mask_mode: bool) -> None:
        d = ImageDraw.Draw(layer, "RGBA" if layer.mode == "RGBA" else None)
        fill = 255 if mask_mode else None
        rows = [
            ((760, 1120, 1080, 1188), (255, 106, 91, 255)),
            ((786, 1230, 1145, 1303), (91, 204, 180, 255)),
            ((740, 1362, 1095, 1434), (250, 192, 63, 255)),
        ]
        for box, color in rows:
            if mask_mode:
                d.rounded_rectangle(box, 28, fill=fill)
                continue
            x0, y0, x1, y1 = box
            d.rounded_rectangle((x0, y0 + 13, x1, y1 + 17), 28, fill=(13, 57, 122, 115))
            d.rounded_rectangle(box, 28, fill=(20, 73, 146, 245))
            d.rounded_rectangle((x0 + 12, y0 + 10, x1 - 12, y1 - 12), 24, fill=color)
            d.rounded_rectangle((x0 + 28, y0 + 17, x1 - 40, y0 + 33), 14, fill=(255, 255, 255, 85))

    def right_strip_bolts(layer: Image.Image, mask_mode: bool) -> None:
        d = ImageDraw.Draw(layer, "RGBA" if layer.mode == "RGBA" else None)
        fill = 255 if mask_mode else None
        for cx, cy in [(1544, 1105), (1546, 1402)]:
            if mask_mode:
                d.ellipse((cx - 24, cy - 24, cx + 24, cy + 24), fill=fill)
                continue
            d.ellipse((cx - 24, cy - 20, cx + 24, cy + 28), fill=(9, 45, 101, 95))
            d.ellipse((cx - 22, cy - 22, cx + 22, cy + 22), fill=(31, 86, 158, 245))
            d.ellipse((cx - 15, cy - 15, cx + 15, cy + 15), fill=(223, 242, 255, 250))
            d.line((cx - 11, cy + 8, cx + 11, cy - 8), fill=(69, 125, 194, 255), width=5)
            d.ellipse((cx - 11, cy - 12, cx - 2, cy - 5), fill=(255, 255, 255, 125))

    def lower_left_pills(layer: Image.Image, mask_mode: bool) -> None:
        d = ImageDraw.Draw(layer, "RGBA" if layer.mode == "RGBA" else None)
        fill = 255 if mask_mode else None
        for idx, (x0, y0, x1, y1) in enumerate(
            [(108, 1180, 290, 1224), (116, 1260, 336, 1306), (122, 1342, 310, 1388)]
        ):
            if mask_mode:
                d.rounded_rectangle((x0, y0, x1, y1), 18, fill=fill)
                continue
            color = [(255, 106, 91, 255), (250, 192, 63, 255), (91, 204, 180, 255)][idx]
            d.rounded_rectangle((x0, y0 + 8, x1, y1 + 12), 18, fill=(13, 57, 122, 100))
            d.rounded_rectangle((x0, y0, x1, y1), 18, fill=(22, 76, 149, 245))
            d.rounded_rectangle((x0 + 8, y0 + 8, x1 - 8, y1 - 10), 14, fill=color)
            d.rounded_rectangle((x0 + 22, y0 + 12, x1 - 34, y0 + 22), 8, fill=(255, 255, 255, 90))

    return [
        Control(
            "upper-left lamp cluster",
            "upper-left tall bay above the left shoulder of the slot",
            upper_lamps,
            "small colored indicator bulbs from reference control panels",
        ),
        Control(
            "middle-left slider bank",
            "middle-left field below/left of the diagonal slot",
            slider_bank,
            "horizontal sliders and square knobs from style reference 11_17_34",
        ),
        Control(
            "lower-left gauge",
            "lower-left base bay above the bottom notch",
            lower_left_gauge,
            "round blue-white gauge from both references",
        ),
        Control(
            "lower-left pill bars",
            "lower-left base bay above the bottom notch",
            lower_left_pills,
            "stacked colored pill bars echoing the reference panels",
        ),
        Control(
            "lower-middle pill buttons",
            "lower-middle bay between the bottom notch and the right cutouts",
            lower_middle_buttons,
            "large rounded buttons from reference 11_17_34",
        ),
        Control(
            "right-strip bolts",
            "right vertical strip between the diagonal slot and outer edge",
            right_strip_bolts,
            "small screw-head details kept away from the lower-right round cutout",
        ),
    ]


def evaluate_control(mask: Image.Image, outer: Image.Image, cutouts: Image.Image, paintable_safe: Image.Image) -> dict:
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


def draw_path_outline(layer: Image.Image, points: list[tuple[float, float]], color, width: int) -> None:
    d = ImageDraw.Draw(layer, "RGBA")
    coords = [(round(x), round(y)) for x, y in points]
    d.line(coords, fill=color, width=width, joint="curve")


def make_outputs() -> dict:
    svg_text = SVG_PATH.read_text()
    manifest = json.loads(MANIFEST_PATH.read_text())
    viewbox = parse_viewbox(svg_text)
    _, _, vb_width, vb_height = viewbox
    size = (math.ceil(vb_width), math.ceil(vb_height))
    path_data = extract_path_data(svg_text)
    sampled_paths = [sample_svg_path(d) for d in path_data[:3]]

    outer_mask = draw_polygon_mask(size, sampled_paths[0])
    cutout_masks = [draw_polygon_mask(size, points) for points in sampled_paths[1:3]]
    cutouts_mask = ImageChops.lighter(cutout_masks[0], cutout_masks[1])
    paintable_mask = ImageChops.subtract(outer_mask, cutouts_mask)
    control_margin_px = 16
    paintable_safe = erode(paintable_mask, control_margin_px)

    art = build_watercolor_background(size, paintable_mask)

    line_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw_path_outline(line_layer, sampled_paths[0], (16, 71, 142, 230), 17)
    draw_path_outline(line_layer, sampled_paths[0], (178, 220, 255, 100), 5)
    for hole_points in sampled_paths[1:3]:
        draw_path_outline(line_layer, hole_points, (16, 65, 130, 235), 14)
        draw_path_outline(line_layer, hole_points, (216, 239, 255, 110), 4)
    line_layer.putalpha(ImageChops.multiply(line_layer.getchannel("A"), paintable_mask))
    art = Image.alpha_composite(art, line_layer)

    control_defs = make_controls(size)
    controls_meta = []
    for control in control_defs:
        control_mask = Image.new("L", size, 0)
        control.draw_fn(control_mask, True)
        metrics = evaluate_control(control_mask, outer_mask, cutouts_mask, paintable_safe)
        accepted = metrics["outside_eroded_paintable_pixels"] == 0 and metrics["mask_pixels"] > 0
        record = {
            "name": control.name,
            "pocket": control.pocket,
            "role": control.role,
            "accepted": accepted,
            **metrics,
        }
        controls_meta.append(record)
        if not accepted:
            continue
        control_layer = Image.new("RGBA", size, (0, 0, 0, 0))
        control.draw_fn(control_layer, False)
        control_layer.putalpha(ImageChops.multiply(control_layer.getchannel("A"), paintable_mask))
        control_layer = control_layer.filter(ImageFilter.GaussianBlur(0.15))
        art = Image.alpha_composite(art, control_layer)

    # Final guardrail: no paint outside the authoritative paintable region.
    final_alpha = ImageChops.multiply(art.getchannel("A"), paintable_mask)
    art.putalpha(final_alpha)

    overlay = Image.new("RGBA", size, (255, 255, 255, 255))
    overlay = Image.alpha_composite(overlay, art)
    od = ImageDraw.Draw(overlay, "RGBA")
    draw_path_outline(overlay, sampled_paths[0], (255, 219, 85, 255), 7)
    draw_path_outline(overlay, sampled_paths[1], (255, 78, 78, 235), 7)
    draw_path_outline(overlay, sampled_paths[2], (255, 78, 78, 235), 7)
    od.rectangle((0, 0, size[0] - 1, size[1] - 1), outline=(50, 50, 50, 70), width=2)

    debug = Image.new("RGBA", size, (248, 248, 248, 255))
    debug.alpha_composite(Image.merge("RGBA", (Image.new("L", size, 92), Image.new("L", size, 174), Image.new("L", size, 235), paintable_mask)))
    debug.alpha_composite(Image.merge("RGBA", (Image.new("L", size, 255), Image.new("L", size, 77), Image.new("L", size, 77), cutouts_mask)))
    safe_alpha = paintable_safe.point(lambda p: 80 if p else 0)
    debug.alpha_composite(Image.merge("RGBA", (Image.new("L", size, 50), Image.new("L", size, 220), Image.new("L", size, 120), safe_alpha)))
    for control, meta in zip(control_defs, controls_meta):
        cm = Image.new("L", size, 0)
        control.draw_fn(cm, True)
        color = (0, 0, 0, 155) if meta["accepted"] else (150, 50, 50, 120)
        debug.alpha_composite(Image.merge("RGBA", (Image.new("L", size, color[0]), Image.new("L", size, color[1]), Image.new("L", size, color[2]), cm.point(lambda p: 145 if p else 0))))
    dd = ImageDraw.Draw(debug, "RGBA")
    dd.text((24, 22), "blue=paintable, red=cutouts, green=eroded safe mask, black=drawn controls, brown=rejected plan", fill=(0, 0, 0, 210))

    outside_final = ImageChops.subtract(art.getchannel("A"), paintable_mask)
    final_cutout_alpha = ImageChops.multiply(art.getchannel("A"), cutouts_mask)
    accepted_controls = [c for c in controls_meta if c["accepted"]]
    rejected_controls = [c for c in controls_meta if not c["accepted"]]

    metadata = {
        "workflow": "strict-pocket-procedural-proof",
        "source_svg": str(SVG_PATH.relative_to(TASK_DIR.parent.parent)),
        "template_manifest": str(MANIFEST_PATH.relative_to(TASK_DIR.parent.parent)),
        "style_refs": [str(p.relative_to(TASK_DIR.parent.parent)) for p in REF_PATHS],
        "manifest_status": manifest.get("status"),
        "viewbox": list(viewbox),
        "canvas_size_px": list(size),
        "path_roles": {
            "path[0]": "outer material contour",
            "path[1]": "large diagonal rounded slot keep-clear",
            "path[2]": "lower-right round/bolt-like keep-clear",
        },
        "paintable_mask": {
            "outer_pixels": count_nonzero(outer_mask),
            "cutout_pixels": count_nonzero(cutouts_mask),
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
            "accepted_control_escape_pixels": sum(c["outside_eroded_paintable_pixels"] for c in accepted_controls),
            "accepted_control_cutout_pixels": sum(c["inside_cutout_pixels"] for c in accepted_controls),
            "final_outside_paintable_alpha_pixels": count_nonzero(outside_final),
            "final_cutout_alpha_pixels": count_nonzero(final_cutout_alpha),
        },
        "outputs": {
            "artwork": str(ARTWORK_PATH.name),
            "overlay": str(OVERLAY_PATH.name),
            "mask_debug": str(MASK_DEBUG_PATH.name),
            "metadata": str(METADATA_PATH.name),
        },
        "method_notes": [
            "All decorative controls were first drawn to a local mask and checked against an eroded paintable mask.",
            "The broad blue watercolor background is the only quiet fill allowed to cover the whole paintable body.",
            "The final alpha clip is applied after drawing only as an exact-edge export guardrail.",
        ],
    }

    ARTWORK_PATH.parent.mkdir(parents=True, exist_ok=True)
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
