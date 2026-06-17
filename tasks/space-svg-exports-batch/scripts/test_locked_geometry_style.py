#!/usr/bin/env python3
"""Test style adaptation with SVG geometry locked.

The experiment deliberately prevents the style pass from owning the silhouette:
the revised SVG mask, cutouts, tabs, and rim are rebuilt after styling.
"""

from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "tasks/space-svg-exports-batch"
sys.path.insert(0, str(TASK / "scripts"))

from create_checkpoint_candidates import (  # noqa: E402
    classify_svg,
    draw_geom_mask,
    draw_records_lines,
    image_size,
)


SVG = TASK / "source/np01-back-top.svg"
BASE = TASK / "outputs/final/np01-back-top-checkpoint-v1-artwork-only.png"
OUT_DIR = TASK / "outputs/style-tests"
CROPS = TASK / "style-packet/crops"


def tile_crop(path: Path, size: tuple[int, int], seed: int) -> Image.Image:
    random.seed(seed)
    crop = Image.open(path).convert("RGB")
    scale = max(size[0] / crop.width, size[1] / crop.height) * random.uniform(1.05, 1.35)
    crop = crop.resize((round(crop.width * scale), round(crop.height * scale)), Image.Resampling.BICUBIC)
    if crop.width < size[0] or crop.height < size[1]:
        tiled = Image.new("RGB", (max(size[0], crop.width * 2), max(size[1], crop.height * 2)), "white")
        for y in range(0, tiled.height, crop.height):
            for x in range(0, tiled.width, crop.width):
                tiled.paste(crop, (x, y))
        crop = tiled
    x = random.randint(0, max(0, crop.width - size[0]))
    y = random.randint(0, max(0, crop.height - size[1]))
    return crop.crop((x, y, x + size[0], y + size[1]))


def watercolor_body(size: tuple[int, int], allowed_mask: Image.Image) -> Image.Image:
    refs = [
        CROPS / "ref01-chatgpt-image-jun-9-2026-11-17-34-pm-body-texture.png",
        CROPS / "ref02-chatgpt-image-jun-9-2026-11-19-45-pm-body-texture.png",
        CROPS / "ref01-chatgpt-image-jun-9-2026-11-17-34-pm-left-region.png",
        CROPS / "ref02-chatgpt-image-jun-9-2026-11-19-45-pm-center-region.png",
    ]
    layers = [tile_crop(path, size, 820 + index).convert("RGBA") for index, path in enumerate(refs)]
    body = layers[0]
    for layer in layers[1:]:
        body = Image.blend(body, layer, 0.34)

    body = ImageEnhance.Color(body).enhance(1.28)
    body = ImageEnhance.Contrast(body).enhance(1.18)

    # Pull the reference crop toward the target blue while preserving pigment variation.
    arr = np.asarray(body.convert("RGB")).astype(np.float32)
    target = np.array([86, 153, 221], dtype=np.float32)
    mean = arr.reshape(-1, 3).mean(axis=0)
    arr = (arr - mean) * 1.08 + (target * 0.88 + mean * 0.12)
    arr[:, :, 0] = np.minimum(arr[:, :, 0], arr[:, :, 2] * 0.76)
    arr[:, :, 1] = np.maximum(arr[:, :, 1], arr[:, :, 0] * 1.28)
    body = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

    wash = Image.new("RGBA", size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(wash, "RGBA")
    random.seed(913)
    for _ in range(82):
        x = random.randint(-size[0] // 5, size[0])
        y = random.randint(-size[1] // 5, size[1])
        rx = random.randint(34, max(70, size[0] // 4))
        ry = random.randint(28, max(64, size[1] // 5))
        color = random.choice(
            [
                (28, 94, 180, 18),
                (2, 55, 130, 13),
                (185, 222, 246, 34),
                (255, 255, 255, 24),
            ]
        )
        draw.ellipse((x, y, x + rx, y + ry), fill=color)
    wash = wash.filter(ImageFilter.GaussianBlur(18))
    body.alpha_composite(wash)
    return Image.composite(body, Image.new("RGBA", size, (255, 255, 255, 255)), allowed_mask)


def source_control_mask(source: Image.Image, allowed_mask: Image.Image) -> Image.Image:
    rgb = np.asarray(source.convert("RGB")).astype(np.int16)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    maxc = rgb.max(axis=2)
    minc = rgb.min(axis=2)
    sat = maxc - minc

    # Keep colored controls and light control faces, but exclude the broad blue body.
    red_yellow_mint = ((r > g + 20) | (r > b + 28) | ((g > 145) & (b > 105) & (r < 190))) & (sat > 28)
    pale_screen = (g > 170) & (b > 175) & (r < 210) & (sat > 10)
    dark_small = (b < 150) & (r < 70) & (g < 110)
    mask = (red_yellow_mint | pale_screen | dark_small) & (np.asarray(allowed_mask) > 0)

    # Avoid capturing the exact SVG rim as a "control"; it is rebuilt later.
    inner = allowed_mask.filter(ImageFilter.MinFilter(43))
    mask &= np.asarray(inner) > 0

    image = Image.fromarray(mask.astype(np.uint8) * 255, "L")
    image = image.filter(ImageFilter.MaxFilter(23)).filter(ImageFilter.GaussianBlur(1.2))
    return image.point(lambda value: 255 if value > 18 else 0)


def soften_controls(source: Image.Image, control_mask: Image.Image, body_texture: Image.Image) -> Image.Image:
    controls = Image.composite(source.convert("RGBA"), Image.new("RGBA", source.size, (0, 0, 0, 0)), control_mask)
    soft = controls.filter(ImageFilter.GaussianBlur(0.45))
    soft = ImageEnhance.Color(soft).enhance(1.10)
    soft = ImageEnhance.Contrast(soft).enhance(1.08)

    texture = body_texture.convert("RGBA").filter(ImageFilter.GaussianBlur(1.0))
    tint_mask = control_mask.filter(ImageFilter.GaussianBlur(1.6)).point(lambda value: round(value * 0.18))
    textured = Image.composite(texture, Image.new("RGBA", source.size, (0, 0, 0, 0)), tint_mask)
    soft.alpha_composite(textured)
    return soft


def edge_rim(
    size: tuple[int, int],
    allowed_mask: Image.Image,
    hole_mask: Image.Image,
    records: list[object],
    viewbox: tuple[float, float, float, float],
) -> Image.Image:
    rim = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(rim, "RGBA")

    outer_band = ImageChops.subtract(allowed_mask, allowed_mask.filter(ImageFilter.MinFilter(37)))
    inner_shadow = Image.new("RGBA", size, (3, 43, 111, 80))
    rim.alpha_composite(Image.composite(inner_shadow, Image.new("RGBA", size, (0, 0, 0, 0)), outer_band.filter(ImageFilter.GaussianBlur(2.2))))

    hole_band = hole_mask.filter(ImageFilter.GaussianBlur(2.0))
    rim.alpha_composite(Image.composite(Image.new("RGBA", size, (2, 44, 120, 84)), Image.new("RGBA", size, (0, 0, 0, 0)), hole_band))

    for jitter, alpha, width in [(0, 205, 5), (2, 95, 3), (-2, 72, 2)]:
        scratch = Image.new("RGBA", size, (0, 0, 0, 0))
        draw_records_lines(scratch, records, viewbox, size, width, (5, 45, 116, alpha))
        if jitter:
            scratch = ImageChops.offset(scratch, jitter, -jitter)
        rim.alpha_composite(scratch)

    highlight = Image.new("RGBA", size, (0, 0, 0, 0))
    hdraw = ImageDraw.Draw(highlight, "RGBA")
    for record in records:
        x0, y0, x1, y1 = record.bounds
        # Short, exact-geometry highlights: style only, no geometry ownership.
        px0 = round((x0 + 26) * size[0] / viewbox[2])
        py0 = round((y0 + 30) * size[1] / viewbox[3])
        px1 = round((x0 + (x1 - x0) * 0.32) * size[0] / viewbox[2])
        py1 = round((y0 + 22) * size[1] / viewbox[3])
        hdraw.line((px0, py0, px1, py1), fill=(245, 253, 255, 145), width=4)
    rim.alpha_composite(highlight.filter(ImageFilter.GaussianBlur(0.4)))
    return rim


def debug_overlay(image: Image.Image, allowed_mask: Image.Image, hole_mask: Image.Image, lines: Image.Image) -> Image.Image:
    debug = image.convert("RGBA")
    allowed = np.asarray(allowed_mask) > 0
    holes = np.asarray(hole_mask) > 0
    tint = np.zeros((debug.height, debug.width, 4), dtype=np.uint8)
    tint[allowed] = (0, 165, 255, 20)
    tint[holes] = (255, 0, 160, 92)
    debug.alpha_composite(Image.fromarray(tint, "RGBA"))
    debug.alpha_composite(lines)
    return debug.convert("RGB")


def metrics(image: Image.Image, allowed_mask: Image.Image, hole_mask: Image.Image) -> dict[str, object]:
    rgb = np.asarray(image.convert("RGB")).astype(np.int16)
    painted = ((255 - rgb[:, :, 0]) + (255 - rgb[:, :, 1]) + (255 - rgb[:, :, 2])) > 24
    allowed = np.asarray(allowed_mask) > 0
    holes = np.asarray(hole_mask) > 0
    return {
        "outside_nonwhite_pixels": int((painted & ~allowed & ~holes).sum()),
        "cutout_nonwhite_pixels": int((painted & holes).sum()),
        "coverage_pct": round(100 * int((painted & allowed).sum()) / max(1, int(allowed.sum())), 2),
    }


def main() -> int:
    geometry, records, allowed_geom, hole_geom = classify_svg(SVG)
    size = image_size(geometry.viewbox, 1120)
    allowed_mask = draw_geom_mask(allowed_geom, geometry.viewbox, size)
    hole_mask = draw_geom_mask(hole_geom, geometry.viewbox, size)
    source = Image.open(BASE).convert("RGBA").resize(size, Image.Resampling.LANCZOS)

    body = watercolor_body(size, allowed_mask)
    control_mask = source_control_mask(source, allowed_mask)
    controls = soften_controls(source, control_mask, body)

    final = body.copy()
    final.alpha_composite(controls)
    final.alpha_composite(edge_rim(size, allowed_mask, hole_mask, records, geometry.viewbox))

    white = Image.new("RGBA", size, (255, 255, 255, 255))
    allowed_binary = allowed_mask.point(lambda value: 255 if value > 0 else 0)
    hole_binary = hole_mask.point(lambda value: 255 if value > 0 else 0)
    final = Image.composite(final, white, allowed_binary)
    final = Image.composite(white, final, hole_binary)

    lines = Image.new("RGBA", size, (255, 255, 255, 0))
    draw_records_lines(lines, records, geometry.viewbox, size, 3, (0, 0, 0, 255))
    debug = debug_overlay(final, allowed_mask, hole_mask, lines)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    art_path = OUT_DIR / "np01-back-top-locked-geometry-style-v1.png"
    debug_path = OUT_DIR / "np01-back-top-locked-geometry-style-v1-debug.png"
    meta_path = OUT_DIR / "np01-back-top-locked-geometry-style-v1-metadata.json"
    final.convert("RGB").save(art_path)
    debug.save(debug_path)

    meta = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": "locked SVG geometry: style rebuilt under exact mask, then exact rim/cutout geometry restored",
        "svg": str(SVG.relative_to(ROOT)),
        "base_composition": str(BASE.relative_to(ROOT)),
        "artwork": str(art_path.relative_to(ROOT)),
        "debug": str(debug_path.relative_to(ROOT)),
        "viewbox": list(geometry.viewbox),
        "output_dimensions": f"{size[0]}x{size[1]}",
        "style_sources": [
            str((CROPS / "ref01-chatgpt-image-jun-9-2026-11-17-34-pm-body-texture.png").relative_to(ROOT)),
            str((CROPS / "ref02-chatgpt-image-jun-9-2026-11-19-45-pm-body-texture.png").relative_to(ROOT)),
            str((CROPS / "ref01-chatgpt-image-jun-9-2026-11-17-34-pm-left-region.png").relative_to(ROOT)),
            str((CROPS / "ref02-chatgpt-image-jun-9-2026-11-19-45-pm-center-region.png").relative_to(ROOT)),
        ],
        "metrics": metrics(final, allowed_mask, hole_mask),
    }
    meta["metrics"]["verdict"] = "PASS" if meta["metrics"]["outside_nonwhite_pixels"] == 0 and meta["metrics"]["cutout_nonwhite_pixels"] == 0 else "FAIL"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
