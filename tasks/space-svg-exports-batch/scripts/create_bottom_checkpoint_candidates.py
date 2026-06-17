#!/usr/bin/env python3
"""Create bottom-panel illustrations for all eligible non-top space SVGs.

This reuses the repo's SVG parser/mask code and draws only inside eroded safe
pockets, so each result tests contour fit before exact SVG cleanup. The output
is still procedural, but uses the style-packet palette/edge language and a
painterly pass to keep the results closer to the watercolor references.
"""

from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "tasks/space-svg-exports-batch"
sys.path.insert(0, str(TASK / "scripts"))

from create_checkpoint_candidates import (  # noqa: E402
    PALETTE,
    add_beveled_edges,
    classify_svg,
    draw_circuit,
    draw_dial,
    draw_geom_mask,
    draw_records_lines,
    draw_screen,
    draw_slider,
    draw_socket,
    draw_toggle,
    fits,
    image_size,
    rounded_button,
    safe_region,
    sha256,
    tx,
    vb_box,
    watercolor_body,
)


SVG_NAMES = [
    "np01-back-bottom.svg",
    "np01-front-bottom.svg",
    "np02-back-bottom.svg",
    "np02-front-bottom.svg",
]


def rgba_tuple(color: tuple[int, int, int, int], lift: int = 42) -> tuple[int, int, int, int]:
    return tuple(min(255, channel + lift) for channel in color[:3]) + (255,)


def part_bounds_px(record: object, viewbox: tuple[float, float, float, float], size: tuple[int, int]) -> tuple[int, int, int, int]:
    return vb_box(viewbox, size, record.bounds)


def inset_box(box: tuple[int, int, int, int], px: int) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    return x0 + px, y0 + px, x1 - px, y1 - px


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


def draw_button_stack(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    colors: list[tuple[tuple[int, int, int, int], tuple[int, int, int, int]]],
) -> None:
    x0, y0, x1, y1 = box
    gap = max(8, (y1 - y0) // 20)
    h = max(18, (y1 - y0 - gap * (len(colors) - 1)) // len(colors))
    for idx, (fill, light) in enumerate(colors):
        yy = y0 + idx * (h + gap)
        rounded_button(draw, (x0, yy, x1, yy + h), fill, light, radius=max(8, h // 3))


def draw_monitor_bank(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], seed: int) -> None:
    x0, y0, x1, y1 = box
    gap = max(9, (x1 - x0) // 28)
    col_w = (x1 - x0 - gap) // 2
    draw_screen(draw, (x0, y0, x0 + col_w, y1), seed)
    draw_screen(draw, (x0 + col_w + gap, y0 + 14, x1, y1 - 12), seed + 9)


def draw_socket_column(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    count = 4
    radius = max(13, min((x1 - x0) // 3, (y1 - y0) // 9))
    for idx in range(count):
        cy = y0 + round((idx + 0.5) * (y1 - y0) / count)
        cx = x0 + (x1 - x0) // 2 + (idx % 2) * radius // 2 - radius // 4
        draw_socket(draw, (cx, cy), radius)


def draw_switch_grid(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], variant: int) -> None:
    x0, y0, x1, y1 = box
    cols = 2
    rows = 2
    colors = [
        (PALETTE["red"], PALETTE["red_light"]),
        (PALETTE["yellow"], PALETTE["yellow_light"]),
        (PALETTE["mint"], PALETTE["mint_light"]),
        (PALETTE["red"], PALETTE["red_light"]),
    ]
    for row in range(rows):
        for col in range(cols):
            cx = x0 + round((col + 0.5) * (x1 - x0) / cols)
            cy = y0 + round((row + 0.74) * (y1 - y0) / rows)
            fill, light = colors[(row * cols + col + variant) % len(colors)]
            draw_toggle(draw, (cx, cy), 0.58, fill, light)


def draw_circuit_ladder(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], seed: int) -> None:
    random.seed(seed)
    x0, y0, x1, y1 = box
    xs = [x0 + round((x1 - x0) * frac) for frac in [0.15, 0.45, 0.72, 0.88]]
    ys = [y0 + round((y1 - y0) * frac) for frac in [0.10, 0.28, 0.47, 0.66, 0.86]]
    points: list[tuple[int, int]] = []
    for idx, y in enumerate(ys):
        points.append((xs[idx % len(xs)], y))
        if idx < len(ys) - 1:
            points.append((xs[(idx + 1) % len(xs)], y))
    draw_circuit(draw, points, [PALETTE["mint"], PALETTE["yellow"], PALETTE["red"]])


def soften_element_layer(layer: Image.Image, seed: int) -> Image.Image:
    """Soften procedural elements without moving them outside their mask."""
    rng = np.random.default_rng(seed)
    width, height = layer.size
    blurred = layer.filter(ImageFilter.GaussianBlur(0.55))
    layer = Image.blend(layer, blurred, 0.28)

    wash = Image.new("RGBA", layer.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(wash, "RGBA")
    for _ in range(34):
        x = int(rng.integers(-width // 10, width))
        y = int(rng.integers(-height // 10, height))
        rx = int(rng.integers(max(18, width // 28), max(24, width // 9)))
        ry = int(rng.integers(max(18, height // 48), max(24, height // 18)))
        draw.ellipse(
            (x, y, x + rx, y + ry),
            fill=random.choice(
                [
                    (255, 255, 255, 16),
                    (4, 56, 126, 10),
                    (109, 169, 225, 12),
                ]
            ),
        )
    wash = wash.filter(ImageFilter.GaussianBlur(8))
    layer.alpha_composite(wash)
    return layer


def draw_variant_elements(
    art: Image.Image,
    records: list[object],
    viewbox: tuple[float, float, float, float],
    allowed_mask: Image.Image,
    variant: int,
) -> None:
    safe_np = np.asarray(safe_region(allowed_mask, 24)) > 0
    layer = Image.new("RGBA", art.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    paintables = [record for record in records if record.role == "paintable"]
    paintables.sort(key=lambda record: record.bounds[0])

    for idx, record in enumerate(paintables):
        box = inset_box(part_bounds_px(record, viewbox, art.size), 36)
        if box[2] <= box[0] or box[3] <= box[1]:
            continue
        contour_w = box[2] - box[0]
        contour_h = box[3] - box[1]
        narrow = contour_w < art.size[0] * 0.22
        is_left = idx == 0
        if narrow:
            if variant == 1:
                plan = [
                    ("switches", rel_box(box, (0.18, 0.10, 0.82, 0.28))),
                    ("sockets", rel_box(box, (0.18, 0.38, 0.82, 0.70))),
                    ("buttons", rel_box(box, (0.16, 0.78, 0.84, 0.94))),
                ]
            else:
                plan = [
                    ("buttons", rel_box(box, (0.16, 0.08, 0.84, 0.24))),
                    ("sockets", rel_box(box, (0.18, 0.34, 0.82, 0.66))),
                    ("switches", rel_box(box, (0.18, 0.74, 0.82, 0.92))),
                ]
        elif variant == 1:
            plan = [
                ("monitor", rel_box(box, (0.14, 0.07, 0.82, 0.20))),
                ("circuit", rel_box(box, (0.18, 0.25, 0.76, 0.42))),
                ("dial", rel_box(box, (0.22, 0.48, 0.66, 0.62))),
                ("buttons", rel_box(box, (0.19, 0.70, 0.78, 0.88))),
                ("sockets", rel_box(box, (0.68, 0.47, 0.90, 0.67))),
            ]
            if not is_left:
                plan = [
                    ("switches", rel_box(box, (0.20, 0.07, 0.78, 0.22))),
                    ("buttons", rel_box(box, (0.20, 0.30, 0.78, 0.46))),
                    ("monitor", rel_box(box, (0.15, 0.56, 0.84, 0.70))),
                    ("circuit", rel_box(box, (0.18, 0.77, 0.78, 0.91))),
                    ("sockets", rel_box(box, (0.70, 0.18, 0.92, 0.37))),
                ]
        else:
            plan = [
                ("buttons", rel_box(box, (0.19, 0.08, 0.78, 0.23))),
                ("slider", rel_box(box, (0.14, 0.32, 0.82, 0.39))),
                ("monitor", rel_box(box, (0.17, 0.48, 0.84, 0.62))),
                ("switches", rel_box(box, (0.18, 0.73, 0.80, 0.89))),
                ("sockets", rel_box(box, (0.68, 0.26, 0.91, 0.44))),
            ]
            if not is_left:
                plan = [
                    ("monitor", rel_box(box, (0.16, 0.08, 0.84, 0.22))),
                    ("circuit", rel_box(box, (0.18, 0.29, 0.80, 0.45))),
                    ("dial", rel_box(box, (0.27, 0.54, 0.72, 0.69))),
                    ("buttons", rel_box(box, (0.22, 0.78, 0.80, 0.92))),
                    ("sockets", rel_box(box, (0.10, 0.52, 0.31, 0.72))),
                ]

        for kind, shape_box in plan:
            if shape_box[2] <= shape_box[0] or shape_box[3] <= shape_box[1]:
                continue
            if not fits(safe_np, shape_box):
                continue
            x0, y0, x1, y1 = shape_box
            if kind == "monitor":
                draw_monitor_bank(draw, shape_box, 100 + variant * 10 + idx)
            elif kind == "circuit":
                draw_circuit_ladder(draw, shape_box, 200 + variant * 10 + idx)
            elif kind == "dial":
                radius = min(x1 - x0, y1 - y0) // 2
                draw_dial(draw, ((x0 + x1) // 2, (y0 + y1) // 2), radius, angle=-0.85 + idx * 0.45)
            elif kind == "buttons":
                scheme = [
                    (PALETTE["red"], PALETTE["red_light"]),
                    (PALETTE["mint"], PALETTE["mint_light"]),
                    (PALETTE["yellow"], PALETTE["yellow_light"]),
                ]
                if (idx + variant) % 2:
                    scheme = [
                        (PALETTE["yellow"], PALETTE["yellow_light"]),
                        (PALETTE["red"], PALETTE["red_light"]),
                        (PALETTE["mint"], PALETTE["mint_light"]),
                    ]
                draw_button_stack(draw, shape_box, scheme)
            elif kind == "sockets":
                draw_socket_column(draw, shape_box)
            elif kind == "switches":
                draw_switch_grid(draw, shape_box, variant + idx)
            elif kind == "slider":
                draw_slider(
                    draw,
                    shape_box,
                    [
                        (0.24, PALETTE["mint"], PALETTE["mint_light"]),
                        (0.62, PALETTE["yellow"], PALETTE["yellow_light"]),
                    ],
                )

    layer = soften_element_layer(layer, 9100 + variant)
    clipped = Image.composite(layer, Image.new("RGBA", art.size, (255, 255, 255, 0)), allowed_mask)
    art.alpha_composite(clipped)


def make_debug(art: Image.Image, allowed_mask: Image.Image, hole_mask: Image.Image, line_image: Image.Image) -> Image.Image:
    debug = art.convert("RGBA")
    allowed = np.asarray(allowed_mask) > 0
    holes = np.asarray(hole_mask) > 0
    tint = np.zeros((debug.height, debug.width, 4), dtype=np.uint8)
    tint[allowed] = (0, 160, 255, 22)
    tint[holes] = (255, 0, 150, 95)
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


def create_candidate(svg_name: str, variant: int, target_width: int = 900) -> dict[str, object]:
    svg = TASK / "source" / svg_name
    geometry, records, allowed_geom, hole_geom = classify_svg(svg)
    size = image_size(geometry.viewbox, target_width)
    allowed_mask = draw_geom_mask(allowed_geom, geometry.viewbox, size)
    hole_mask = draw_geom_mask(hole_geom, geometry.viewbox, size)

    seed_base = 7200 + (sum(ord(char) for char in svg_name) * 7) + variant
    art = watercolor_body(allowed_mask, seed=seed_base)
    add_beveled_edges(art, allowed_mask, hole_mask, records, geometry.viewbox, size)
    draw_variant_elements(art, records, geometry.viewbox, allowed_mask, variant)
    add_beveled_edges(art, allowed_mask, hole_mask, records, geometry.viewbox, size)

    white = Image.new("RGBA", size, (255, 255, 255, 255))
    allowed_binary = allowed_mask.point(lambda value: 255 if value > 0 else 0)
    hole_binary = hole_mask.point(lambda value: 255 if value > 0 else 0)
    art = Image.composite(art, white, allowed_binary)
    art = Image.composite(white, art, hole_binary)

    lines = Image.new("RGBA", size, (255, 255, 255, 0))
    draw_records_lines(lines, records, geometry.viewbox, size, 4, (0, 0, 0, 255))
    clean = art.copy()
    clean.alpha_composite(lines)
    debug = make_debug(art, allowed_mask, hole_mask, lines)

    prefix = f"{svg.stem}-batch-bottom-v{variant}"
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
        "svg": str(svg.relative_to(ROOT)),
        "svg_sha256": sha256(svg),
        "variant": variant,
        "candidate": str(generated.relative_to(ROOT)),
        "artwork_only": str(final_art.relative_to(ROOT)),
        "clean_black_lines": str(clean_path.relative_to(ROOT)),
        "debug_mask": str(debug_path.relative_to(ROOT)),
        "style_packet": str((TASK / "style-packet/style-packet.json").relative_to(ROOT)),
        "source_style_refs": [str(path.relative_to(ROOT)) for path in sorted((TASK / "refs").glob("*.png"))],
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
        "method_note": "Bottom-panel batch candidate. Elements are drawn only in eroded safe pockets, then exact SVG masks clear the outer contour and cutouts.",
    }
    meta_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    metadata["metadata"] = str(meta_path.relative_to(ROOT))
    return metadata


def make_contact_sheet(metadata: list[dict[str, object]], filename: str = "batch-bottom-all-versions.png") -> Path:
    images = [Image.open(ROOT / str(item["artwork_only"])).convert("RGB") for item in metadata]
    max_h = 760
    thumbs = []
    for image in images:
        scale = min(1.0, max_h / image.height)
        thumbs.append(image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS))
    pad = 34
    label_h = 44
    width = sum(image.width for image in thumbs) + pad * (len(thumbs) + 1)
    height = max(image.height for image in thumbs) + pad * 2 + label_h
    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)
    x = pad
    for image, item in zip(thumbs, metadata):
        sheet.paste(image, (x, pad + label_h))
        draw.text((x, pad), f"{Path(str(item['svg'])).name} v{item['variant']}", fill=(10, 45, 85))
        x += image.width + pad
    path = TASK / "checkpoints" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    return path


def main() -> int:
    candidates = [
        create_candidate(svg_name, variant)
        for svg_name in SVG_NAMES
        for variant in [1, 2]
    ]
    sheet = make_contact_sheet(candidates)
    summary = {
        "checkpoint": str(sheet.relative_to(ROOT)),
        "candidates": candidates,
    }
    summary_path = TASK / "checkpoints/batch-bottom-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
