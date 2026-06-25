#!/usr/bin/env python3
"""Build vector-first Berlin hotel base repair candidates.

All outputs stay in this lane directory. The source image is read-only input.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from PIL import ImageFont


ROOT = Path(__file__).resolve().parents[2]
LANE = Path(__file__).resolve().parent
SRC_PATH = ROOT / "work" / "src.png"

BOX = (3162, 2582, 4082, 2845)
ZOOM_BOX = (3050, 2480, 4120, 2900)
W = BOX[2] - BOX[0]
H = BOX[3] - BOX[1]
SCALE = 4


@dataclass(frozen=True)
class WindowGroup:
    x0: float
    x1: float
    cols: int


def srgb_luminance(rgb: np.ndarray) -> np.ndarray:
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def stats_color(arr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    flat = arr.reshape(-1, 3).astype(np.float32)
    return np.median(flat, axis=0), flat.std(axis=0)


def jittered_poly(points: list[tuple[float, float]], jitter: float, rng: np.random.Generator) -> list[tuple[int, int]]:
    out = []
    for x, y in points:
        out.append((round((x + rng.normal(0, jitter)) * SCALE), round((y + rng.normal(0, jitter)) * SCALE)))
    return out


def rect(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float], fill, outline=None, width: float = 1.0) -> None:
    scaled = tuple(round(v * SCALE) for v in box)
    draw.rectangle(scaled, fill=fill, outline=outline, width=max(1, round(width * SCALE)))


def line(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], fill, width: float = 1.0) -> None:
    scaled = [(round(x * SCALE), round(y * SCALE)) for x, y in points]
    draw.line(scaled, fill=fill, width=max(1, round(width * SCALE)), joint="curve")


def poly(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], fill, outline=None) -> None:
    scaled = [(round(x * SCALE), round(y * SCALE)) for x, y in points]
    draw.polygon(scaled, fill=fill, outline=outline)


def draw_stone_noise(base: Image.Image, rng: np.random.Generator, strength: float) -> Image.Image:
    arr = np.asarray(base).astype(np.float32)
    noise = rng.normal(0, strength, (H * SCALE, W * SCALE, 1)).astype(np.float32)
    bands = rng.normal(0, strength * 0.6, (H * SCALE, 1, 1)).astype(np.float32)
    arr += noise + bands
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def draw_window_group(
    draw: ImageDraw.ImageDraw,
    group: WindowGroup,
    y0: float,
    y1: float,
    palette: dict[str, tuple[int, int, int, int]],
    rng: np.random.Generator,
    slant: float = 0.0,
    warm: float = 0.0,
) -> None:
    gx0 = group.x0 + slant * y0 / H
    gx1 = group.x1 + slant * y0 / H
    bay_w = gx1 - gx0
    gap = max(3.4, bay_w * 0.10)
    col_w = (bay_w - gap * (group.cols + 1)) / group.cols
    ytop = y0 + 13
    ybot = y1 - 14
    if ybot <= ytop:
        return

    # Pale recessed stone reveal.
    reveal_fill = palette["stone_shadow"]
    rect(draw, (gx0 - 2, ytop - 3, gx1 + 2, ybot + 3), reveal_fill, None)

    for i in range(group.cols):
        x0 = gx0 + gap + i * (col_w + gap)
        x1 = x0 + col_w
        x0b = x0 + slant * (ytop - y0) / H
        x1b = x1 + slant * (ytop - y0) / H
        x0c = x0 + slant * (ybot - y0) / H
        x1c = x1 + slant * (ybot - y0) / H

        dark = np.array(palette["glass_dark"][:3], dtype=np.float32)
        blue = np.array(palette["glass_blue"][:3], dtype=np.float32)
        glow = np.array(palette["warm_glow"][:3], dtype=np.float32)
        local_warm = warm * rng.uniform(0.45, 1.0)
        fill_rgb = dark * (0.65 - local_warm * 0.12) + blue * 0.35 + glow * local_warm * 0.35
        fill_alpha = int(palette.get("window_alpha", 220))
        fill = tuple(np.clip(fill_rgb, 0, 255).astype(np.uint8).tolist()) + (fill_alpha,)
        poly(draw, [(x0b, ytop), (x1b, ytop), (x1c, ybot), (x0c, ybot)], fill)

        # Soft vertical glass highlight and inner ink.
        mid = (x0 + x1) / 2
        line(draw, [(mid + 0.9, ytop + 2), (mid + slant * (ybot - y0) / H + 0.6, ybot - 2)], palette["glass_highlight"], 0.65)
        line(draw, [(x0b, ytop), (x0c, ybot)], palette["ink_soft"], 0.62 if fill_alpha < 190 else 0.75)
        line(draw, [(x1b, ytop), (x1c, ybot)], palette["ink_soft"], 0.62 if fill_alpha < 190 else 0.75)

    # A few faint mullions/broken wash marks, not text.
    for _ in range(3):
        xx = rng.uniform(gx0, gx1)
        line(draw, [(xx, ytop + rng.uniform(0, 8)), (xx + slant * 0.08, ybot - rng.uniform(0, 8))], palette["watermark"], 0.45)


def make_svg(path: Path) -> None:
    front_bays = [26, 122, 222, 322, 421, 521]
    receding_bays = [642, 690, 737, 785, 832, 878]
    lines_svg = []
    lines_svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    lines_svg.append('<rect x="0" y="0" width="920" height="263" fill="#e9dfc9"/>')
    lines_svg.append('<path d="M0 0 H920 M0 86 H920 M0 174 H920 M0 235 H920 M0 252 H920" fill="none" stroke="#5b6770" stroke-width="1.2" opacity="0.7"/>')
    lines_svg.append('<path d="M598 0 L625 252" fill="none" stroke="#41505a" stroke-width="2.2"/>')
    for x in front_bays:
        lines_svg.append(f'<rect x="{x - 10}" y="0" width="20" height="235" fill="#f5eddc" stroke="#75808a" stroke-width="0.8" opacity="0.95"/>')
    for x in receding_bays:
        lines_svg.append(f'<path d="M{x - 6} 0 L{x + 12} 235" fill="none" stroke="#75808a" stroke-width="1.1" opacity="0.8"/>')
    rows = [(5, 84), (92, 171), (179, 232)]
    for y0, y1 in rows:
        for x in [72, 172, 272, 372, 472, 572]:
            lines_svg.append(f'<rect x="{x - 23}" y="{y0 + 14}" width="46" height="{y1 - y0 - 28}" rx="3" fill="#41525c" opacity="0.82"/>')
        for x in [662, 708, 755, 802, 850, 897]:
            lines_svg.append(f'<rect x="{x - 12}" y="{y0 + 13}" width="24" height="{y1 - y0 - 27}" rx="2" fill="#41525c" opacity="0.72"/>')
    lines_svg.append('<rect x="0" y="235" width="920" height="17" fill="#d8d0bf" stroke="#65707a" stroke-width="1"/>')
    lines_svg.append("</svg>")
    path.write_text("\n".join(lines_svg) + "\n")


def build_candidate(src: Image.Image, variant: str) -> dict[str, Path]:
    rng = np.random.default_rng({"v1": 1729, "v2": 2201, "v3": 4099}[variant])
    src_arr = np.asarray(src.convert("RGB"))
    x0, y0, x1, y1 = BOX
    source_patch = src_arr[y0:y1, x0:x1].astype(np.float32)
    clean_above = src_arr[2395:2578, x0:x1].astype(np.float32)
    stone_median, _ = stats_color(clean_above[srgb_luminance(clean_above) > np.percentile(srgb_luminance(clean_above), 58)])
    glass_sample = clean_above[srgb_luminance(clean_above) < np.percentile(srgb_luminance(clean_above), 25)]
    glass_median, _ = stats_color(glass_sample)
    quay = src_arr[2828:2860, x0:x1].astype(np.float32)
    quay_median, _ = stats_color(quay)

    stone = tuple(np.clip(stone_median * np.array([1.01, 1.005, 0.985]), 0, 255).astype(np.uint8).tolist()) + (255,)
    stone_shadow = tuple(np.clip(stone_median * np.array([0.86, 0.88, 0.90]), 0, 255).astype(np.uint8).tolist()) + (168,)
    glass_dark = tuple(np.clip(glass_median * np.array([0.72, 0.80, 0.90]), 0, 255).astype(np.uint8).tolist()) + (230,)
    glass_blue = (77, 96, 107, 210)
    palette = {
        "stone": stone,
        "stone_shadow": stone_shadow,
        "glass_dark": glass_dark,
        "glass_blue": glass_blue,
        "warm_glow": (196, 144, 73, 180),
        "ink": (39, 54, 61, 160),
        "ink_soft": (44, 62, 70, 108),
        "watermark": (67, 77, 73, 60),
        "highlight": (255, 252, 236, 92),
        "glass_highlight": (214, 224, 220, 84),
        "window_alpha": 168 if variant == "v3" else 220,
    }

    base = Image.new("RGBA", (W * SCALE, H * SCALE), stone)
    noise_strength = 4.2 if variant == "v1" else (5.4 if variant == "v2" else 6.2)
    base = draw_stone_noise(base.convert("RGB"), rng, noise_strength).convert("RGBA")
    draw = ImageDraw.Draw(base, "RGBA")

    # Watercolor stone washes.
    for _ in range(120):
        x = rng.uniform(-30, W)
        y = rng.uniform(-10, H)
        ww = rng.uniform(24, 105)
        hh = rng.uniform(10, 42)
        fill = tuple(np.clip(stone_median + rng.normal(0, 7, 3), 0, 255).astype(np.uint8).tolist()) + (rng.integers(14, 38),)
        rect(draw, (x, y, x + ww, y + hh), fill, None)

    # Main building volumes and receding face wash.
    front_right_top = 598
    front_right_bottom = 625
    poly(draw, [(0, 0), (front_right_top, 0), (front_right_bottom, 252), (0, 252)], (*stone[:3], 210))
    poly(draw, [(front_right_top, 0), (W, 0), (W, 252), (front_right_bottom, 252)], tuple(np.clip(stone_median * [0.96, 0.975, 1.01], 0, 255).astype(np.uint8).tolist()) + (218,))

    rows = [(0, 86), (86, 174), (174, 235)]
    if variant in ("v2", "v3"):
        rows = [(0, 84), (84, 172), (172, 235)]

    # Structural floor lines.
    for y in [0, rows[1][0], rows[2][0], 235, 252]:
        line(draw, [(0, y), (W, y)], palette["ink_soft"], 0.8 if y not in (235, 252) else 1.15)
        line(draw, [(0, y + 2.1), (W, y + 2.1)], palette["highlight"], 0.55)

    # Front piers.
    pier_centers = [22, 122, 222, 322, 421, 521, 594]
    for i, x in enumerate(pier_centers):
        top_w = 22 if i != len(pier_centers) - 1 else 25
        bottom_shift = 0 if i != len(pier_centers) - 1 else front_right_bottom - front_right_top
        points = [(x - top_w / 2, 0), (x + top_w / 2, 0), (x + bottom_shift + top_w / 2, 235), (x + bottom_shift - top_w / 2, 235)]
        poly(draw, jittered_poly(points, 0.18, rng), tuple(np.clip(stone_median * [1.05, 1.04, 1.0], 0, 255).astype(np.uint8).tolist()) + (224,))
        line(draw, [(x - top_w / 2, 2), (x + bottom_shift - top_w / 2, 235)], palette["ink_soft"], 0.65)
        line(draw, [(x + top_w / 2, 2), (x + bottom_shift + top_w / 2, 235)], palette["highlight"], 0.72)

    front_windows = [
        WindowGroup(47, 98, 3),
        WindowGroup(146, 198, 3),
        WindowGroup(247, 298, 3),
        WindowGroup(346, 398, 3),
        WindowGroup(445, 497, 3),
        WindowGroup(543, 587, 2),
    ]
    for y0r, y1r in rows:
        warm = 0.12 if y0r >= 170 else 0.035
        for group in front_windows:
            draw_window_group(draw, group, y0r, y1r, palette, rng, 0.0, warm)

    # Receding right face: tighter bays, lines drift subtly to the right as they descend.
    line(draw, [(front_right_top, 0), (front_right_bottom, 252)], palette["ink"], 1.1)
    face_groups = [
        WindowGroup(648, 671, 2),
        WindowGroup(691, 715, 2),
        WindowGroup(734, 759, 2),
        WindowGroup(778, 803, 2),
        WindowGroup(823, 848, 2),
        WindowGroup(870, 895, 2),
    ]
    for y0r, y1r in rows:
        for group in face_groups:
            draw_window_group(draw, group, y0r, y1r, palette, rng, 18.0, 0.055 if y0r >= 170 else 0.015)
    for x in [636, 683, 728, 774, 819, 866, 910]:
        line(draw, [(x, 2), (x + 18.5, 235)], palette["ink_soft"], 0.65)
        line(draw, [(x + 5, 2), (x + 23.5, 235)], palette["highlight"], 0.45)

    # Modest plinth and waterline transition.
    plinth_rgb = np.clip(quay_median * 0.92 + stone_median * 0.08, 0, 255).astype(np.uint8)
    rect(draw, (0, 235, W, 252), tuple(plinth_rgb.tolist()) + (220,), None)
    line(draw, [(0, 235), (W, 235)], palette["ink"], 1.1)
    line(draw, [(0, 252), (W, 252)], (42, 57, 58, 96), 1.0)
    for x in range(0, W, 38):
        line(draw, [(x + rng.uniform(-2, 2), 238), (x + rng.uniform(-2, 2), 251)], (72, 72, 65, 45), 0.5)

    # Watercolor softening: a blurred wash underneath plus a crisp but translucent ink layer.
    wash = base.filter(ImageFilter.GaussianBlur((1.25 if variant != "v3" else 1.8) * SCALE))
    base = Image.blend(wash, base, 0.78 if variant == "v1" else (0.66 if variant == "v2" else 0.52))
    ink = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ink_draw = ImageDraw.Draw(ink, "RGBA")
    for _ in range(48 if variant == "v3" else (42 if variant == "v2" else 28)):
        y = rng.uniform(0, 235)
        x_start = rng.uniform(0, W * 0.15)
        x_end = rng.uniform(W * 0.72, W)
        line(ink_draw, [(x_start, y), (x_end, y + rng.normal(0, 1.4))], (63, 73, 71, rng.integers(18, 40)), 0.45)
    base = Image.alpha_composite(base, ink)

    patch = base.resize((W, H), Image.Resampling.LANCZOS).convert("RGB")
    if variant == "v3":
        patch = patch.filter(ImageFilter.GaussianBlur(0.32))
    patch_arr = np.asarray(patch).astype(np.float32)

    # Match the existing artwork's average value and retain a little paper/edge texture from the source.
    target = clean_above
    patch_lum = srgb_luminance(patch_arr)
    target_lum = srgb_luminance(target)
    patch_arr *= (np.median(target_lum) / max(np.median(patch_lum), 1.0)) * (0.98 if variant == "v1" else 1.0)

    # Gentle paper carry-over from the original base, but suppress old glass-hall content.
    source_blur = np.asarray(Image.fromarray(source_patch.astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))).astype(np.float32)
    if variant == "v3":
        facade_texture = np.asarray(
            Image.fromarray(clean_above.astype(np.uint8)).resize((W, H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(0.7))
        ).astype(np.float32)
        patch_arr = patch_arr * 0.74 + facade_texture * 0.21 + source_blur * 0.05
    else:
        patch_arr = patch_arr * (0.91 if variant == "v1" else 0.86) + source_blur * (0.09 if variant == "v1" else 0.14)

    # Top/bottom feather so the candidate lives in the existing painting.
    alpha = np.ones((H, W, 1), dtype=np.float32)
    top_feather = 15
    bottom_feather = 16
    for yy in range(top_feather):
        alpha[yy, :, 0] = yy / top_feather
    for yy in range(H - bottom_feather, H):
        alpha[yy, :, 0] = np.minimum(alpha[yy, :, 0], (H - 1 - yy) / bottom_feather)
    if variant in ("v2", "v3"):
        # Softer variants preserve more of the original right edge.
        for xx in range(W - 36, W):
            alpha[:, xx, 0] *= (W - 1 - xx) / 36

    comp_patch = source_patch * (1 - alpha) + patch_arr * alpha
    comp_patch = np.clip(comp_patch, 0, 255).astype(np.uint8)

    full = src_arr.copy()
    full[y0:y1, x0:x1] = comp_patch

    patch_path = LANE / f"w2_vector_linework_{variant}_patch.png"
    full_path = LANE / f"w2_vector_linework_{variant}_composited.png"
    zoom_path = LANE / f"w2_vector_linework_{variant}_zoom.png"
    guide_path = LANE / f"w2_vector_linework_{variant}_guide.png"

    Image.fromarray(comp_patch).save(patch_path)
    Image.fromarray(full).save(full_path)
    Image.fromarray(full[ZOOM_BOX[1] : ZOOM_BOX[3], ZOOM_BOX[0] : ZOOM_BOX[2]]).save(zoom_path)
    patch.save(guide_path)
    return {"patch": patch_path, "full": full_path, "zoom": zoom_path, "guide": guide_path}


def main() -> int:
    LANE.mkdir(parents=True, exist_ok=True)
    src = Image.open(SRC_PATH).convert("RGB")
    make_svg(LANE / "vector_linework_base.svg")
    outputs = {}
    for variant in ("v1", "v2", "v3"):
        outputs[variant] = build_candidate(src, variant)
    font = ImageFont.load_default()
    source_zoom = src.crop(ZOOM_BOX)
    zooms = [("source", source_zoom)] + [(variant, Image.open(outputs[variant]["zoom"]).convert("RGB")) for variant in ("v1", "v2", "v3")]
    label_h = 24
    board = Image.new("RGB", (source_zoom.width, (source_zoom.height + label_h) * len(zooms)), (245, 241, 232))
    bd = ImageDraw.Draw(board)
    for i, (label, img) in enumerate(zooms):
        y = i * (source_zoom.height + label_h)
        bd.rectangle((0, y, source_zoom.width, y + label_h), fill=(236, 231, 218))
        bd.text((8, y + 7), label, fill=(42, 48, 52), font=font)
        board.paste(img, (0, y + label_h))
    board_path = LANE / "w2_vector_linework_zoom_board.png"
    board.save(board_path)
    manifest = LANE / "manifest.txt"
    lines = ["Vector linework lane outputs:"]
    for variant, paths in outputs.items():
        lines.append(f"{variant}:")
        for key, path in paths.items():
            lines.append(f"  {key}: {path}")
    lines.append(f"zoom_board: {board_path}")
    manifest.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
