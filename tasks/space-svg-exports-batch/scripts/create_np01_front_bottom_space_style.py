#!/usr/bin/env python3
"""Create space-reference style candidates for np01-front-bottom.svg."""

from __future__ import annotations

import json
import math
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "tasks/space-svg-exports-batch"
SVG = TASK / "source/np01-front-bottom.svg"
OUT_PREFIX = "np01-front-bottom-space-style"

sys.path.insert(0, str(TASK / "scripts"))
from create_checkpoint_candidates import (  # noqa: E402
    classify_svg,
    draw_geom_mask,
    draw_records_lines,
    image_size,
    safe_region,
    sha256,
    vb_box,
)


Color = tuple[int, int, int, int]


BLUE_RIM = (18, 83, 157, 255)
BLUE_DARK = (7, 48, 121, 255)
BLUE_BODY = (179, 224, 248, 255)
BLUE_BODY_2 = (126, 190, 232, 255)
TEAL = (93, 203, 203, 255)
TEAL_LIGHT = (184, 246, 238, 255)
WHITE = (255, 255, 255, 255)
YELLOW = (247, 188, 50, 255)
ORANGE = (242, 125, 53, 255)
GREEN = (158, 200, 67, 255)
CYAN = (42, 173, 204, 255)


def rel_box(box: tuple[int, int, int, int], values: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    w = x1 - x0
    h = y1 - y0
    return (
        round(x0 + values[0] * w),
        round(y0 + values[1] * h),
        round(x0 + values[2] * w),
        round(y0 + values[3] * h),
    )


def inset_box(box: tuple[int, int, int, int], px: int) -> tuple[int, int, int, int]:
    return box[0] + px, box[1] + px, box[2] - px, box[3] - px


def fits(mask_np: np.ndarray, box: tuple[int, int, int, int]) -> bool:
    x0, y0, x1, y1 = box
    if x0 < 0 or y0 < 0 or x1 >= mask_np.shape[1] or y1 >= mask_np.shape[0]:
        return False
    region = mask_np[y0:y1, x0:x1]
    return bool(region.size and region.min() > 0)


def watercolor_space_body(mask: Image.Image, seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    width, height = mask.size
    arr = np.zeros((height, width, 4), dtype=np.uint8)
    arr[:, :, 0] = BLUE_BODY[0]
    arr[:, :, 1] = BLUE_BODY[1]
    arr[:, :, 2] = BLUE_BODY[2]
    arr[:, :, 3] = 255

    coarse = rng.normal(0, 24, (max(8, height // 13), max(8, width // 13))).astype(np.float32)
    noise = Image.fromarray(np.clip(coarse + 128, 0, 255).astype(np.uint8), "L")
    noise = noise.resize((width, height), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(2.2))
    noise_np = np.asarray(noise).astype(np.int16) - 128
    arr[:, :, 0] = np.clip(arr[:, :, 0].astype(np.int16) + noise_np * 0.36, 0, 255)
    arr[:, :, 1] = np.clip(arr[:, :, 1].astype(np.int16) + noise_np * 0.28, 0, 255)
    arr[:, :, 2] = np.clip(arr[:, :, 2].astype(np.int16) + noise_np * 0.16, 0, 255)
    body = Image.fromarray(arr, "RGBA")

    wash = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(wash, "RGBA")
    random.seed(seed)
    for _ in range(70):
        x = random.randint(-width // 5, width)
        y = random.randint(-height // 8, height)
        rx = random.randint(max(30, width // 14), max(52, width // 3))
        ry = random.randint(max(24, height // 25), max(48, height // 8))
        draw.ellipse(
            (x, y, x + rx, y + ry),
            fill=random.choice(
                [
                    (244, 252, 255, 34),
                    (91, 176, 231, 18),
                    (31, 120, 211, 12),
                    (206, 241, 255, 28),
                ]
            ),
        )
    body.alpha_composite(wash.filter(ImageFilter.GaussianBlur(18)))
    return Image.composite(body, Image.new("RGBA", (width, height), (255, 255, 255, 255)), mask)


def add_glass_edges(
    image: Image.Image,
    allowed_mask: Image.Image,
    hole_mask: Image.Image,
    records: list[object],
    viewbox: tuple[float, float, float, float],
    size: tuple[int, int],
) -> None:
    edge = ImageChops.subtract(allowed_mask, allowed_mask.filter(ImageFilter.MinFilter(35))).filter(ImageFilter.GaussianBlur(1.0))
    image.alpha_composite(Image.composite(Image.new("RGBA", size, (14, 96, 184, 80)), Image.new("RGBA", size, (0, 0, 0, 0)), edge))
    image.alpha_composite(Image.composite(Image.new("RGBA", size, (6, 52, 133, 78)), Image.new("RGBA", size, (0, 0, 0, 0)), hole_mask.filter(ImageFilter.GaussianBlur(1.5))))
    draw_records_lines(image, records, viewbox, size, 12, (16, 80, 158, 145))
    draw_records_lines(image, records, viewbox, size, 4, BLUE_RIM)

    high = Image.new("RGBA", size, (0, 0, 0, 0))
    hdraw = ImageDraw.Draw(high, "RGBA")
    for record in records:
        if record.role != "paintable":
            continue
        x0, y0, x1, y1 = vb_box(viewbox, size, record.bounds)
        hdraw.line((x0 + 22, y0 + 26, x0 + (x1 - x0) // 2, y0 + 20), fill=(255, 255, 255, 150), width=4)
        hdraw.arc((x0 + 20, y0 + 24, x0 + 90, y0 + 120), 175, 235, fill=(255, 255, 255, 130), width=5)
    image.alpha_composite(Image.composite(high.filter(ImageFilter.GaussianBlur(0.4)), Image.new("RGBA", size, (0, 0, 0, 0)), allowed_mask))


def rounded_panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, fill: Color, outline: Color = BLUE_RIM) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle((x0 + 6, y0 + 8, x1 + 6, y1 + 8), radius=radius, fill=(10, 61, 129, 74))
    draw.rounded_rectangle((x0 - 5, y0 - 5, x1 + 5, y1 + 5), radius=radius + 6, fill=BLUE_DARK)
    draw.rounded_rectangle((x0, y0, x1, y1), radius=radius, fill=fill, outline=outline, width=3)


def draw_radar_screen(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], seed: int) -> None:
    x0, y0, x1, y1 = box
    rounded_panel(draw, box, max(14, (x1 - x0) // 18), (91, 205, 202, 226))
    draw.rounded_rectangle((x0 + 10, y0 + 10, x1 - 10, y1 - 10), radius=12, outline=(244, 255, 255, 215), width=3)
    cx = x0 + round((x1 - x0) * 0.38)
    cy = y0 + round((y1 - y0) * 0.60)
    r = min(x1 - x0, y1 - y0) // 4
    for rr in [r, int(r * 0.72), int(r * 0.46), int(r * 0.22)]:
        draw.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=(248, 255, 255, 230), width=3)
    for angle in range(0, 180, 30):
        a = math.radians(angle)
        draw.line((cx - math.cos(a) * r, cy - math.sin(a) * r, cx + math.cos(a) * r, cy + math.sin(a) * r), fill=(248, 255, 255, 230), width=3)
    draw.line((cx, cy, cx + round(r * 1.45), cy - round(r * 0.70)), fill=(248, 255, 255, 230), width=4)
    random.seed(seed)
    for _ in range(5):
        px = cx + random.randint(-r, r)
        py = cy + random.randint(-r, r)
        draw.ellipse((px - 5, py - 5, px + 5, py + 5), fill=(255, 255, 255, 235))
    for idx in range(4):
        yy = y0 + round((idx + 0.22) * (y1 - y0) / 5)
        draw.rounded_rectangle((x0 + round((x1 - x0) * 0.66), yy, x1 - 18, yy + 9), radius=4, fill=(248, 255, 255, 230))
    draw.polygon([(x0 + 16, y0 + 18), (x0 + 115, y0 + 18), (x0 + 18, y0 + 124)], fill=(235, 255, 255, 58))
    draw.arc((x1 - 75, y1 - 70, x1 - 18, y1 - 16), 30, 88, fill=(255, 255, 255, 175), width=5)


def draw_knob(draw: ImageDraw.ImageDraw, center: tuple[int, int], radius: int, tick_span: tuple[int, int] = (195, 345)) -> None:
    cx, cy = center
    for i in range(11):
        a = math.radians(tick_span[0] + i * (tick_span[1] - tick_span[0]) / 10)
        r0 = radius + 16
        r1 = radius + 31
        draw.line((cx + math.cos(a) * r0, cy + math.sin(a) * r0, cx + math.cos(a) * r1, cy + math.sin(a) * r1), fill=(255, 255, 255, 230), width=max(3, radius // 10))
    draw.ellipse((cx - radius - 10, cy - radius - 10, cx + radius + 10, cy + radius + 10), fill=BLUE_DARK)
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=YELLOW, outline=(180, 104, 12, 210), width=3)
    draw.ellipse((cx - radius + 8, cy - radius + 8, cx + radius - 8, cy + radius - 8), fill=(255, 204, 80, 170))
    draw.arc((cx - radius + 10, cy - radius + 10, cx + radius - 4, cy + radius - 4), 196, 252, fill=(255, 255, 255, 185), width=5)


def draw_planet(draw: ImageDraw.ImageDraw, center: tuple[int, int], radius: int, palette: list[Color], ring: bool = False) -> None:
    cx, cy = center
    if ring:
        ring_box = (cx - radius * 2, cy - radius // 2, cx + radius * 2, cy + radius // 2)
        draw.ellipse(ring_box, outline=(210, 250, 245, 210), width=max(7, radius // 4))
        draw.ellipse((ring_box[0] + 10, ring_box[1] + 5, ring_box[2] - 10, ring_box[3] - 5), outline=(86, 156, 190, 120), width=2)
    draw.ellipse((cx - radius + 8, cy - radius + 12, cx + radius + 8, cy + radius + 12), fill=(34, 95, 160, 52))
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=palette[0], outline=(92, 83, 30, 135), width=2)
    for idx, color in enumerate(palette[1:]):
        y = cy - radius + round((idx + 1) * 2 * radius / (len(palette) + 1))
        amp = radius * (0.60 + 0.12 * math.sin(idx))
        draw.arc((cx - amp, y - radius // 5, cx + amp, y + radius // 3), 5, 175, fill=color, width=max(3, radius // 9))
    draw.arc((cx - radius + 8, cy - radius + 8, cx - radius // 4, cy - radius // 4), 192, 255, fill=(255, 255, 255, 190), width=max(4, radius // 8))
    if not ring:
        for dx, dy, rr in [(-0.35, -0.10, 0.13), (0.22, 0.28, 0.16), (0.08, -0.38, 0.09)]:
            draw.ellipse((cx + dx * radius - rr * radius, cy + dy * radius - rr * radius, cx + dx * radius + rr * radius, cy + dy * radius + rr * radius), fill=palette[-1])


def draw_planet_stack(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], variant: int) -> None:
    x0, y0, x1, y1 = box
    w = x1 - x0
    h = y1 - y0
    centers = [
        (x0 + round(w * 0.34), y0 + round(h * 0.25), min(w, h) // 7),
        (x0 + round(w * 0.63), y0 + round(h * 0.48), min(w, h) // 5),
        (x0 + round(w * 0.38), y0 + round(h * 0.73), min(w, h) // 6),
    ]
    palettes = [
        [(252, 190, 54, 255), (255, 230, 122, 210), (228, 109, 30, 180), (205, 112, 25, 150)],
        [(236, 141, 74, 255), (255, 226, 147, 230), (210, 73, 58, 170), (171, 91, 33, 160)],
        [(190, 218, 70, 255), (235, 234, 92, 220), (123, 171, 52, 185), (112, 152, 49, 165)],
    ]
    if variant == 2:
        palettes[1] = [(39, 175, 200, 255), (98, 232, 220, 220), (23, 107, 188, 180), (27, 119, 116, 160)]
    for idx, (cx, cy, r) in enumerate(centers):
        draw_planet(draw, (cx, cy), r, palettes[idx], ring=(variant == 2 and idx == 1))


def draw_hud_lines(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    for i in range(5):
        yy = y0 + i * (y1 - y0) // 5
        draw.rounded_rectangle((x0, yy, x1 - (i % 2) * 35, yy + 9), radius=4, fill=(255, 255, 255, 220))
    for i in range(3):
        xx = x0 + i * (x1 - x0) // 4
        draw.rectangle((xx, y0 + 70, xx + 32, y0 + 120), outline=(255, 255, 255, 215), width=5)


def draw_space_elements(art: Image.Image, records: list[object], viewbox: tuple[float, float, float, float], allowed_mask: Image.Image, variant: int) -> None:
    safe_np = np.asarray(safe_region(allowed_mask, 28)) > 0
    layer = Image.new("RGBA", art.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    paintables = sorted([record for record in records if record.role == "paintable"], key=lambda record: record.bounds[0])

    for idx, record in enumerate(paintables):
        box = inset_box(vb_box(viewbox, art.size, record.bounds), 42)
        if idx == 0:
            placements = [
                ("screen", rel_box(box, (0.06, 0.07, 0.27, 0.30))),
                ("planet_one", rel_box(box, (0.58, 0.09, 0.90, 0.29))),
                ("knob", rel_box(box, (0.62, 0.36, 0.88, 0.50))),
                ("hud", rel_box(box, (0.58, 0.54, 0.90, 0.65))),
                ("planets", rel_box(box, (0.10, 0.70, 0.82, 0.95))),
            ]
        else:
            placements = [
                ("screen", rel_box(box, (0.08, 0.08, 0.39, 0.32))),
                ("hud", rel_box(box, (0.75, 0.10, 0.95, 0.36))),
                ("knob", rel_box(box, (0.74, 0.56, 0.95, 0.70))),
                ("planets", rel_box(box, (0.08, 0.64, 0.42, 0.94))),
            ]
            if variant == 2:
                placements = [
                    ("planet_one", rel_box(box, (0.08, 0.08, 0.38, 0.30))),
                    ("hud", rel_box(box, (0.76, 0.11, 0.94, 0.36))),
                    ("screen", rel_box(box, (0.08, 0.58, 0.42, 0.82))),
                    ("knob", rel_box(box, (0.74, 0.60, 0.95, 0.75))),
                    ("planets", rel_box(box, (0.12, 0.84, 0.42, 0.97))),
                ]
        for kind, placement in placements:
            if placement[2] <= placement[0] or placement[3] <= placement[1] or not fits(safe_np, placement):
                continue
            x0, y0, x1, y1 = placement
            if kind == "screen":
                draw_radar_screen(draw, placement, 530 + variant + idx)
            elif kind == "planets":
                draw_planet_stack(draw, placement, variant + idx)
            elif kind == "planet_one":
                radius = min(x1 - x0, y1 - y0) // 2
                palette = [(238, 137, 73, 255), (255, 223, 142, 230), (211, 78, 63, 190), (166, 92, 39, 160)]
                if variant == 2:
                    palette = [(40, 174, 201, 255), (115, 234, 224, 220), (30, 106, 188, 180), (24, 118, 119, 160)]
                draw_planet(draw, ((x0 + x1) // 2, (y0 + y1) // 2), radius, palette, ring=(variant == 2 and idx == 1))
            elif kind == "knob":
                r = min(x1 - x0, y1 - y0) // 2
                draw_knob(draw, ((x0 + x1) // 2, (y0 + y1) // 2), r)
            elif kind == "hud":
                draw_hud_lines(draw, placement)

    # Style pass: light bloom like the reference glass panels.
    layer = Image.blend(layer, layer.filter(ImageFilter.GaussianBlur(0.5)), 0.22)
    clipped = Image.composite(layer, Image.new("RGBA", art.size, (0, 0, 0, 0)), allowed_mask)
    art.alpha_composite(clipped)


def make_debug(art: Image.Image, allowed_mask: Image.Image, hole_mask: Image.Image, line_image: Image.Image) -> Image.Image:
    debug = art.convert("RGBA")
    allowed = np.asarray(allowed_mask) > 0
    holes = np.asarray(hole_mask) > 0
    tint = np.zeros((debug.height, debug.width, 4), dtype=np.uint8)
    tint[allowed] = (0, 160, 255, 18)
    tint[holes] = (255, 0, 150, 94)
    debug.alpha_composite(Image.fromarray(tint, "RGBA"))
    debug.alpha_composite(line_image)
    return debug.convert("RGB")


def metrics(art: Image.Image, allowed_mask: Image.Image, hole_mask: Image.Image) -> dict[str, object]:
    rgb = np.asarray(art.convert("RGB")).astype(np.int16)
    painted = ((255 - rgb[:, :, 0]) + (255 - rgb[:, :, 1]) + (255 - rgb[:, :, 2])) > 24
    allowed = np.asarray(allowed_mask) > 0
    holes = np.asarray(hole_mask) > 0
    outside = int((painted & ~allowed & ~holes).sum())
    in_holes = int((painted & holes).sum())
    coverage = round(100 * int((painted & allowed).sum()) / max(1, int(allowed.sum())), 2)
    return {
        "verdict": "PASS" if outside == 0 and in_holes == 0 and coverage > 35 else "REVIEW",
        "outside_nonwhite_pixels": outside,
        "cutout_nonwhite_pixels": in_holes,
        "paintable_coverage_pct": coverage,
    }


def create_candidate(variant: int) -> dict[str, object]:
    geometry, records, allowed_geom, hole_geom = classify_svg(SVG)
    size = image_size(geometry.viewbox, 940)
    allowed_mask = draw_geom_mask(allowed_geom, geometry.viewbox, size)
    hole_mask = draw_geom_mask(hole_geom, geometry.viewbox, size)

    art = watercolor_space_body(allowed_mask, 8300 + variant)
    add_glass_edges(art, allowed_mask, hole_mask, records, geometry.viewbox, size)
    draw_space_elements(art, records, geometry.viewbox, allowed_mask, variant)
    add_glass_edges(art, allowed_mask, hole_mask, records, geometry.viewbox, size)

    white = Image.new("RGBA", size, (255, 255, 255, 255))
    allowed_binary = allowed_mask.point(lambda value: 255 if value > 0 else 0)
    hole_binary = hole_mask.point(lambda value: 255 if value > 0 else 0)
    art = Image.composite(art, white, allowed_binary)
    art = Image.composite(white, art, hole_binary)

    lines = Image.new("RGBA", size, (0, 0, 0, 0))
    draw_records_lines(lines, records, geometry.viewbox, size, 4, (0, 0, 0, 255))
    clean = art.copy()
    clean.alpha_composite(lines)
    debug = make_debug(art, allowed_mask, hole_mask, lines)

    prefix = f"{OUT_PREFIX}-v{variant}"
    generated = TASK / "outputs/generated" / f"{prefix}.png"
    final_art = TASK / "outputs/final" / f"{prefix}-artwork-only.png"
    clean_path = TASK / "outputs/final" / f"{prefix}-clean-black-lines.png"
    debug_path = TASK / "outputs/reviews" / f"{prefix}-debug-mask.png"
    meta_path = TASK / "outputs/reviews" / f"{prefix}-metadata.json"
    for path in [generated, final_art, clean_path, debug_path, meta_path]:
        path.parent.mkdir(parents=True, exist_ok=True)
    art.convert("RGB").save(generated)
    art.convert("RGB").save(final_art)
    clean.convert("RGB").save(clean_path)
    debug.save(debug_path)

    metadata = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "svg": str(SVG.relative_to(ROOT)),
        "svg_sha256": sha256(SVG),
        "variant": variant,
        "candidate": str(generated.relative_to(ROOT)),
        "artwork_only": str(final_art.relative_to(ROOT)),
        "clean_black_lines": str(clean_path.relative_to(ROOT)),
        "debug_mask": str(debug_path.relative_to(ROOT)),
        "source_style_refs": [
            "/Users/za/Downloads/ChatGPT Image Jun 11, 2026, 06_36_44 AM.png",
            "/Users/za/Downloads/ChatGPT Image Jun 9, 2026, 11_23_04 PM.png",
        ],
        "viewbox": list(geometry.viewbox),
        "output_dimensions": f"{size[0]}x{size[1]}",
        "contours": [
            {
                "source_type": record.source_type,
                "index": record.index,
                "role": record.role,
                "area": round(record.area, 2),
                "bounds": [round(value, 2) for value in record.bounds],
            }
            for record in records
        ],
        "metrics": metrics(art, allowed_mask, hole_mask),
        "method_note": "Space/radar/planet style adaptation from user-uploaded references, exact SVG geometry cleanup.",
    }
    meta_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    metadata["metadata"] = str(meta_path.relative_to(ROOT))
    return metadata


def make_sheet(item: dict[str, object]) -> Path:
    art = Image.open(ROOT / str(item["artwork_only"])).convert("RGB")
    debug = Image.open(ROOT / str(item["debug_mask"])).convert("RGB")
    max_h = 920
    scale = min(1.0, max_h / art.height)
    size = (round(art.width * scale), round(art.height * scale))
    art = art.resize(size, Image.Resampling.LANCZOS)
    debug = debug.resize(size, Image.Resampling.LANCZOS)
    pad = 32
    label_h = 42
    cell_w = max(art.width, debug.width)
    width = pad * 2 + cell_w
    height = pad * 3 + label_h * 2 + art.height + debug.height
    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)
    x = pad
    y = pad
    draw.text((x, y), f"np01-front-bottom space v{item['variant']} art", fill=(10, 45, 85))
    sheet.paste(art, (x, y + label_h))
    y = y + label_h + art.height + pad
    draw.text((x, y), f"np01-front-bottom space v{item['variant']} debug", fill=(10, 45, 85))
    sheet.paste(debug, (x, y + label_h))
    path = TASK / "checkpoints" / f"np01-front-bottom-space-style-v{item['variant']}-review-sheet.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    return path


def main() -> int:
    items = [create_candidate(1), create_candidate(2)]
    sheets = [make_sheet(item) for item in items]
    summary = {
        "checkpoints": [str(sheet.relative_to(ROOT)) for sheet in sheets],
        "candidates": items,
    }
    summary_path = TASK / "checkpoints/np01-front-bottom-space-style-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
