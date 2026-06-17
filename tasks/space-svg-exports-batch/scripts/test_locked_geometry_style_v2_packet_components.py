#!/usr/bin/env python3
"""Style-adapt the approved geometry using packet pixels, not geometry redraw.

This keeps the approved SVG-derived geometry and uses actual reference style
crops for the body texture and main controls. The SVG mask/rim is restored last.
"""

from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

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
CROPS = TASK / "style-packet/crops"
OUT_DIR = TASK / "outputs/style-tests"


def tile_reference_body(size: tuple[int, int]) -> Image.Image:
    random.seed(1701)
    rng = np.random.default_rng(1701)
    base = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    base[:, :, 0] = 90
    base[:, :, 1] = 156
    base[:, :, 2] = 222
    base[:, :, 3] = 255

    for scale, strength in [(18, 22), (55, 18), (140, 12)]:
        noise = rng.normal(0, strength, (max(4, size[1] // scale), max(4, size[0] // scale))).astype(np.float32)
        noise_img = Image.fromarray(np.clip(noise + 128, 0, 255).astype(np.uint8), "L")
        noise_img = noise_img.resize(size, Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(scale / 18))
        delta = np.asarray(noise_img).astype(np.int16) - 128
        base[:, :, 0] = np.clip(base[:, :, 0].astype(np.int16) + delta * 0.50, 0, 255)
        base[:, :, 1] = np.clip(base[:, :, 1].astype(np.int16) + delta * 0.44, 0, 255)
        base[:, :, 2] = np.clip(base[:, :, 2].astype(np.int16) + delta * 0.30, 0, 255)
    body = Image.fromarray(base, "RGBA")

    blooms = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(blooms, "RGBA")
    for _ in range(120):
        x = random.randint(-size[0] // 5, size[0])
        y = random.randint(-size[1] // 5, size[1])
        rx = random.randint(34, max(72, size[0] // 4))
        ry = random.randint(28, max(70, size[1] // 5))
        draw.ellipse(
            (x, y, x + rx, y + ry),
            fill=random.choice(
                [
                    (16, 86, 181, 20),
                    (9, 66, 149, 14),
                    (176, 219, 247, 36),
                    (245, 253, 255, 28),
                ]
            ),
        )
    body.alpha_composite(blooms.filter(ImageFilter.GaussianBlur(19)))
    return ImageEnhance.Contrast(body).enhance(1.08)


def component_mask(component: Image.Image) -> Image.Image:
    rgb = np.asarray(component.convert("RGB")).astype(np.int16)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    maxc = rgb.max(axis=2)
    minc = rgb.min(axis=2)
    sat = maxc - minc
    # Keep colored controls, dark pooled shadows, and bright highlights, while
    # dropping the blue panel background in packet crops.
    keep = (
        (sat > 32)
        | ((r < 55) & (g < 95) & (b < 150))
        | ((r > 220) & (g > 230) & (b > 225))
    )
    blue_bg = (b > r + 22) & (b > g + 8) & (r > 55) & (g > 95) & (sat < 88)
    keep &= ~blue_bg
    mask = Image.fromarray(keep.astype(np.uint8) * 255, "L")
    mask = mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(0.9))
    return mask.point(lambda value: min(255, round(value * 1.18)))


def crop_component(path: Path, crop: tuple[int, int, int, int] | None = None) -> tuple[Image.Image, Image.Image]:
    img = Image.open(path).convert("RGBA")
    if crop:
        img = img.crop(crop)
    mask = component_mask(img)
    return img, mask


def rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(0.6))


def paste_component(
    canvas: Image.Image,
    path: Path,
    box: tuple[int, int, int, int],
    crop: tuple[int, int, int, int] | None = None,
    opacity: float = 1.0,
    mask_kind: str = "auto",
) -> None:
    img, mask = crop_component(path, crop)
    w, h = box[2] - box[0], box[3] - box[1]
    img = img.resize((w, h), Image.Resampling.LANCZOS)
    if mask_kind == "rounded":
        mask = rounded_mask((w, h), max(8, h // 2))
    else:
        mask = mask.resize((w, h), Image.Resampling.LANCZOS)
    if opacity < 1:
        mask = mask.point(lambda value: round(value * opacity))
    canvas.alpha_composite(Image.composite(img, Image.new("RGBA", (w, h), (0, 0, 0, 0)), mask), (box[0], box[1]))


def draw_screen(canvas: Image.Image, box: tuple[int, int, int, int]) -> None:
    src = Image.open(CROPS / "ref01-chatgpt-image-jun-9-2026-11-17-34-pm-body-texture.png").convert("RGBA")
    src = src.resize((box[2] - box[0], box[3] - box[1]), Image.Resampling.BICUBIC)
    arr = np.asarray(src.convert("RGB")).astype(np.float32)
    target = np.array([166, 224, 226], dtype=np.float32)
    mean = arr.reshape(-1, 3).mean(axis=0)
    arr = (arr - mean) * 0.72 + target
    src = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    layer.alpha_composite(src, (box[0], box[1]))
    draw = ImageDraw.Draw(layer, "RGBA")
    x0, y0, x1, y1 = box
    draw.rounded_rectangle((x0, y0, x1, y1), radius=13, outline=(5, 54, 125, 245), width=5)
    draw.rounded_rectangle((x0 + 8, y0 + 8, x1 - 8, y1 - 8), radius=8, outline=(48, 133, 171, 120), width=2)
    for i in range(1, 4):
        x = x0 + i * (x1 - x0) // 4
        draw.line((x, y0 + 13, x, y1 - 13), fill=(24, 113, 154, 80), width=1)
    for i in range(1, 3):
        y = y0 + i * (y1 - y0) // 3
        draw.line((x0 + 13, y, x1 - 13, y), fill=(24, 113, 154, 75), width=1)
    for dot in [(0.24, 0.72, (237, 82, 77, 255)), (0.30, 0.84, (246, 178, 50, 255)), (0.76, 0.28, (246, 178, 50, 255)), (0.79, 0.52, (246, 178, 50, 255))]:
        cx = round(x0 + dot[0] * (x1 - x0))
        cy = round(y0 + dot[1] * (y1 - y0))
        draw.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=dot[2], outline=(6, 54, 125, 230), width=1)
    canvas.alpha_composite(layer)


def draw_exact_rim(
    canvas: Image.Image,
    size: tuple[int, int],
    allowed_mask: Image.Image,
    hole_mask: Image.Image,
    records: list[object],
    viewbox: tuple[float, float, float, float],
) -> None:
    rim = Image.new("RGBA", size, (0, 0, 0, 0))
    outer_band = ImageChops.subtract(allowed_mask, allowed_mask.filter(ImageFilter.MinFilter(45)))
    rim.alpha_composite(Image.composite(Image.new("RGBA", size, (1, 43, 111, 76)), Image.new("RGBA", size, (0, 0, 0, 0)), outer_band.filter(ImageFilter.GaussianBlur(2.4))))
    rim.alpha_composite(Image.composite(Image.new("RGBA", size, (5, 51, 123, 82)), Image.new("RGBA", size, (0, 0, 0, 0)), hole_mask.filter(ImageFilter.GaussianBlur(1.9))))
    for width, alpha, jitter in [(7, 185, 0), (3, 92, 2), (2, 72, -2)]:
        line = Image.new("RGBA", size, (0, 0, 0, 0))
        draw_records_lines(line, records, viewbox, size, width, (5, 48, 121, alpha))
        if jitter:
            line = ImageChops.offset(line, jitter, -jitter)
        rim.alpha_composite(line)
    high = Image.new("RGBA", size, (0, 0, 0, 0))
    hdraw = ImageDraw.Draw(high, "RGBA")
    # Simple placed highlights, not contour edits.
    for coords in [
        (96, 24, 254, 22),
        (612, 92, 775, 75),
        (72, 1010, 240, 1010),
        (612, 1014, 812, 1014),
    ]:
        hdraw.line(coords, fill=(245, 253, 255, 125), width=4)
    canvas.alpha_composite(rim)
    canvas.alpha_composite(high.filter(ImageFilter.GaussianBlur(0.5)))


def debug_overlay(image: Image.Image, allowed_mask: Image.Image, hole_mask: Image.Image, records: list[object], viewbox: tuple[float, float, float, float]) -> Image.Image:
    debug = image.convert("RGBA")
    tint = np.zeros((debug.height, debug.width, 4), dtype=np.uint8)
    tint[np.asarray(allowed_mask) > 0] = (0, 165, 255, 18)
    tint[np.asarray(hole_mask) > 0] = (255, 0, 160, 92)
    debug.alpha_composite(Image.fromarray(tint, "RGBA"))
    lines = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw_records_lines(lines, records, viewbox, image.size, 3, (0, 0, 0, 255))
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

    body = tile_reference_body(size)
    white = Image.new("RGBA", size, (255, 255, 255, 255))
    allowed_binary = allowed_mask.point(lambda value: 255 if value > 0 else 0)
    hole_binary = hole_mask.point(lambda value: 255 if value > 0 else 0)
    canvas = Image.composite(body, white, allowed_binary)

    # Approved geometry coordinate boxes in the 1120x1119 render.
    draw_screen(canvas, (108, 504, 382, 678))
    paste_component(canvas, CROPS / "ref01-chatgpt-image-jun-9-2026-11-17-34-pm-accent-component-01.png", (94, 744, 362, 806), crop=(24, 20, 374, 128), opacity=0.98, mask_kind="rounded")
    paste_component(canvas, CROPS / "ref01-chatgpt-image-jun-9-2026-11-17-34-pm-accent-component-02.png", (94, 812, 362, 876), crop=(18, 63, 378, 178), opacity=0.98, mask_kind="rounded")
    paste_component(canvas, CROPS / "ref01-chatgpt-image-jun-9-2026-11-17-34-pm-accent-component-03.png", (94, 882, 362, 946), crop=(18, 44, 380, 156), opacity=0.98, mask_kind="rounded")

    paste_component(canvas, CROPS / "ref02-chatgpt-image-jun-9-2026-11-19-45-pm-accent-component-02.png", (437, 272, 511, 382), crop=(28, 16, 198, 224), opacity=0.98)
    paste_component(canvas, CROPS / "ref02-chatgpt-image-jun-9-2026-11-19-45-pm-accent-component-05.png", (491, 272, 568, 382), crop=(30, 16, 198, 224), opacity=0.98)
    paste_component(canvas, CROPS / "ref02-chatgpt-image-jun-9-2026-11-19-45-pm-accent-component-03.png", (553, 272, 631, 382), crop=(32, 16, 198, 224), opacity=0.98)

    # Keep the small circuit geometry, but repaint it softer.
    base = Image.open(BASE).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
    circuit_mask = Image.new("L", size, 0)
    ImageDraw.Draw(circuit_mask).rectangle((92, 354, 510, 444), fill=255)
    circuit = Image.composite(base, Image.new("RGBA", size, (0, 0, 0, 0)), circuit_mask)
    circuit = ImageEnhance.Color(circuit.filter(ImageFilter.GaussianBlur(0.35))).enhance(1.08)
    canvas.alpha_composite(circuit)

    draw_exact_rim(canvas, size, allowed_mask, hole_mask, records, geometry.viewbox)
    canvas = Image.composite(canvas, white, allowed_binary)
    canvas = Image.composite(white, canvas, hole_binary)
    debug = debug_overlay(canvas, allowed_mask, hole_mask, records, geometry.viewbox)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    art_path = OUT_DIR / "np01-back-top-locked-packet-style-v2.png"
    debug_path = OUT_DIR / "np01-back-top-locked-packet-style-v2-debug.png"
    meta_path = OUT_DIR / "np01-back-top-locked-packet-style-v2-metadata.json"
    canvas.convert("RGB").save(art_path)
    debug.save(debug_path)
    m = metrics(canvas, allowed_mask, hole_mask)
    m["verdict"] = "PASS" if m["outside_nonwhite_pixels"] == 0 and m["cutout_nonwhite_pixels"] == 0 else "FAIL"
    meta = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": "approved geometry locked; body and controls styled from actual style-packet crops; SVG mask/rim restored last",
        "svg": str(SVG.relative_to(ROOT)),
        "approved_geometry_base": str(BASE.relative_to(ROOT)),
        "artwork": str(art_path.relative_to(ROOT)),
        "debug": str(debug_path.relative_to(ROOT)),
        "metrics": m,
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
