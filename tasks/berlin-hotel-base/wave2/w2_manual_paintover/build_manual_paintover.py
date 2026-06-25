#!/usr/bin/env python3
"""Manual clone/paintover candidates for the Berlin hotel base wave-2 lane."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps


OUT = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "tasks/berlin-hotel-base/work/src.png"
M3_ZOOM = ROOT / "tasks/berlin-hotel-base/RESULTS/M3_procedural_zoom.png"
M3_FULL = ROOT / "tasks/berlin-hotel-base/RESULTS/M3_procedural_composited.png"
CAHILL2 = ROOT / "tasks/berlin-hotel-base/refs/ritz_cahill2.jpg"
STREET = ROOT / "tasks/berlin-hotel-base/refs/ritz_streetlevel.png"

BOX = (3162, 2582, 4082, 2845)
ZOOM = (3060, 2480, 4120, 2900)
W = BOX[2] - BOX[0]
H = BOX[3] - BOX[1]

STONE = np.array([221, 212, 197], dtype=np.float32)
STONE_SHADOW = np.array([175, 170, 159], dtype=np.float32)
WINDOW = np.array([78, 90, 98], dtype=np.float32)
INK = np.array([56, 66, 74], dtype=np.float32)
WARM_GLOW = np.array([177, 137, 72], dtype=np.float32)


FRONT_BAYS = [
    (34, 89, [(34, 50), (52, 70), (72, 89)]),
    (133, 188, [(133, 150), (151, 169), (171, 188)]),
    (236, 287, [(236, 251), (254, 270), (271, 287)]),
    (325, 376, [(325, 340), (343, 358), (361, 376)]),
    (417, 472, [(417, 433), (438, 453), (458, 472)]),
    (512, 567, [(512, 529), (532, 548), (554, 567)]),
]

RIGHT_RUNS = [
    (640, 650),
    (673, 681),
    (710, 719),
    (722, 733),
    (743, 752),
    (756, 764),
    (827, 849),
]


@dataclass
class Candidate:
    key: str
    label: str
    patch: Image.Image


def rgb_tuple(color: np.ndarray | tuple[int, int, int], alpha: int = 255) -> tuple[int, int, int, int]:
    arr = np.asarray(color).clip(0, 255).astype(int)
    return int(arr[0]), int(arr[1]), int(arr[2]), alpha


def stone_texture(src: np.ndarray, seed: int, warm: float = 0.0) -> Image.Image:
    rng = np.random.default_rng(seed)
    x0, y0, x1, _ = BOX
    strip = src[y0 - 235 : y0 - 8, x0:x1].astype(np.float32)
    lum = 0.299 * strip[:, :, 0] + 0.587 * strip[:, :, 1] + 0.114 * strip[:, :, 2]
    clean = strip.copy()
    clean[lum < 135] = STONE * (0.95 + 0.08 * rng.random(clean[lum < 135].shape))
    blurred = Image.fromarray(np.clip(clean, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(7))
    blurred = blurred.resize((W, H), Image.Resampling.BICUBIC)
    arr = np.asarray(blurred).astype(np.float32)
    arr = 0.55 * arr + 0.45 * (STONE + np.array([warm, warm * 0.35, -warm * 0.2], dtype=np.float32))

    low_noise = rng.normal(0, 1, (24, 84, 3)).astype(np.float32)
    low_noise = Image.fromarray(np.clip((low_noise + 3.0) * 36.0, 0, 255).astype(np.uint8))
    low_noise = low_noise.resize((W, H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(3))
    n = np.asarray(low_noise).astype(np.float32) - 108
    arr += n * np.array([0.06, 0.055, 0.05], dtype=np.float32)

    fine = rng.normal(0, 2.2, arr.shape).astype(np.float32)
    arr += fine
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def aa_layer(base: Image.Image, scale: int = 3) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    layer = base.resize((base.width * scale, base.height * scale), Image.Resampling.BICUBIC).convert("RGBA")
    return layer, ImageDraw.Draw(layer, "RGBA")


def sx(v: float, scale: int = 3) -> int:
    return int(round(v * scale))


def rect(draw: ImageDraw.ImageDraw, xy: tuple[float, float, float, float], fill, scale: int = 3, outline=None, width=1) -> None:
    coords = tuple(sx(v, scale) for v in xy)
    draw.rectangle(coords, fill=fill, outline=outline, width=max(1, sx(width, scale)))


def line(draw: ImageDraw.ImageDraw, xy: tuple[float, float, float, float], fill, scale: int = 3, width=1) -> None:
    coords = tuple(sx(v, scale) for v in xy)
    draw.line(coords, fill=fill, width=max(1, sx(width, scale)))


def draw_window(draw: ImageDraw.ImageDraw, x0: float, x1: float, y0: float, y1: float, alpha: int, seed_jitter: float = 0.0) -> None:
    dark = WINDOW + seed_jitter
    rect(draw, (x0 - 1.1, y0 - 1.2, x1 + 1.1, y1 + 1.1), rgb_tuple(INK, int(alpha * 0.52)))
    rect(draw, (x0, y0, x1, y1), rgb_tuple(dark, alpha))
    rect(draw, (x0 + 1.7, y0 + 2.0, x0 + 3.9, y1 - 2.0), rgb_tuple([185, 196, 190], int(alpha * 0.18)))
    rect(draw, (x1 - 3.0, y0 + 3.0, x1 - 1.5, y1 - 1.5), rgb_tuple([210, 215, 202], int(alpha * 0.12)))


def draw_stone_jointing(draw: ImageDraw.ImageDraw, rng: np.random.Generator, strength: int = 52) -> None:
    joint = rgb_tuple(STONE_SHADOW * 0.82, strength)
    for y in [40, 82, 126, 169, 214, 239]:
        line(draw, (5, y + rng.normal(0, 0.4), W - 3, y + rng.normal(0, 0.4)), joint, width=0.8)
    for x in [2, 91, 129, 191, 233, 290, 321, 379, 414, 475, 509, 571, 604, 628, 667, 704, 738, 772, 809, 858, 907]:
        y_top = 2 if x < 620 else 0
        line(draw, (x + rng.normal(0, 0.25), y_top, x + rng.normal(0, 0.25), H - 6), joint, width=0.7)
    for x in range(20, 610, 58):
        for y in [106, 151, 194, 232]:
            line(draw, (x, y, x + 34 + rng.normal(0, 4), y + rng.normal(0, 0.5)), rgb_tuple(STONE_SHADOW, 22), width=0.55)


def draw_bay_frames(draw: ImageDraw.ImageDraw, rng: np.random.Generator, lower_variant: bool) -> None:
    pier_light = rgb_tuple(STONE + np.array([15, 10, 3]), 95)
    pier_shadow = rgb_tuple(STONE_SHADOW * 0.82, 70)
    ink = rgb_tuple(INK, 56)

    for left, right, runs in FRONT_BAYS:
        rect(draw, (left - 8, 0, left - 3, H - 17), pier_light)
        rect(draw, (right + 3, 0, right + 8, H - 17), pier_light)
        line(draw, (left - 9, 1, left - 9, H - 18), pier_shadow, width=0.8)
        line(draw, (right + 9, 2, right + 9, H - 18), ink, width=0.6)

        row_defs = [(11, 66, 184), (92, 146, 175), (171, 219, 158)]
        if lower_variant:
            row_defs = [(10, 62, 182), (87, 143, 166), (170, 214, 144)]
        for ridx, (yt, yb, alpha) in enumerate(row_defs):
            for wx0, wx1 in runs:
                jitter = rng.normal(0, 4.0)
                x_pad = 0.5 if ridx < 2 else 1.4
                draw_window(draw, wx0 + x_pad, wx1 - x_pad, yt, yb, alpha, jitter)

    for wx0, wx1 in RIGHT_RUNS:
        x_mid = (wx0 + wx1) * 0.5
        for yt, yb, alpha in [(8, 58, 155), (88, 141, 145), (170, 211, 128)]:
            taper = 0.06 * (yt / H) * max(0, x_mid - 610)
            draw_window(draw, wx0 + taper, wx1 + taper, yt, yb, alpha, rng.normal(0, 3.0))
        line(draw, (wx0 - 5, 2, wx0 - 9, H - 22), pier_shadow, width=0.55)

    # A heavier but quiet stone ground floor: smaller punched openings, not a glass hall.
    plinth_top = 222 if lower_variant else 226
    rect(draw, (0, plinth_top, W, H), rgb_tuple(STONE_SHADOW + np.array([24, 21, 14]), 138))
    rect(draw, (0, plinth_top - 5, W, plinth_top + 2), rgb_tuple(STONE + np.array([8, 5, 0]), 150))
    rect(draw, (0, H - 19, W, H), rgb_tuple(STONE_SHADOW + np.array([10, 8, 4]), 150))

    openings = [(142, 181), (252, 292), (346, 386), (443, 486), (538, 577), (670, 705), (742, 772), (835, 867)]
    for i, (a, b) in enumerate(openings):
        y_top = 231 + (i % 2) * 2
        rect(draw, (a, y_top, b, H - 24), rgb_tuple(WINDOW * 0.72, 92))
        rect(draw, (a + 2, y_top + 2, b - 2, H - 26), rgb_tuple(WINDOW * 0.95, 62))
    for x in range(16, W, 54):
        line(draw, (x, plinth_top + 4, x + rng.normal(0, 1.0), H - 5), rgb_tuple(STONE_SHADOW, 36), width=0.45)


def foreground_mask(src: np.ndarray) -> Image.Image:
    x0, y0, x1, y1 = BOX
    crop = src[y0:y1, x0:x1].astype(np.int16)
    r, g, b = crop[:, :, 0], crop[:, :, 1], crop[:, :, 2]
    mx = crop.max(axis=2)
    mn = crop.min(axis=2)
    sat = mx - mn
    yy, xx = np.mgrid[0:H, 0:W]

    vegetation = (xx < 235) & (yy > 36) & (sat > 16) & (g > b - 4) & (r > b + 4) & (r > 105)
    twig = (xx < 220) & (yy > 30) & (sat > 18) & (mx < 178) & (g >= b - 12)
    railing = (yy > 228) & (xx < 190) & (mx < 185) & (sat > 12)
    mask = vegetation | twig | railing
    im = Image.fromarray(mask.astype(np.uint8) * 255)
    im = im.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.1))
    return im


def edge_feather_mask() -> Image.Image:
    mask = Image.new("L", (W, H), 255)
    arr = np.asarray(mask).astype(np.float32)
    feather = 16
    for i in range(feather):
        v = 255 * (i + 1) / feather
        arr[:, i] = np.minimum(arr[:, i], v)
        arr[:, W - 1 - i] = np.minimum(arr[:, W - 1 - i], v)
        arr[i, :] = np.minimum(arr[i, :], v)
        arr[H - 1 - i, :] = np.minimum(arr[H - 1 - i, :], v)
    return Image.fromarray(arr.astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))


def candidate_clone_plinth(src: np.ndarray) -> Image.Image:
    rng = np.random.default_rng(2201)
    patch = stone_texture(src, 2201, warm=2.0)

    x0, y0, x1, _ = BOX
    # Clone the artwork's own upper facade, but only as a softened construction base.
    clone = Image.fromarray(src[y0 - 178 : y0 - 4, x0:x1]).resize((W, 178), Image.Resampling.BICUBIC)
    clone_arr = np.asarray(clone).astype(np.float32)
    col_jitter = rng.normal(0, 1.8, (1, W, 3)).astype(np.float32)
    row_wash = np.linspace(0, -8, 178, dtype=np.float32)[:, None, None]
    clone_arr = clone_arr + col_jitter + row_wash
    clone = Image.fromarray(np.clip(clone_arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.25))

    top_mask = Image.new("L", (W, H), 0)
    mdraw = ImageDraw.Draw(top_mask)
    mdraw.rectangle((0, 0, W, 188), fill=224)
    top_mask = top_mask.filter(ImageFilter.GaussianBlur(4))
    patch.paste(clone.crop((0, 0, W, min(H, 178))), (0, 0), top_mask.crop((0, 0, W, min(H, 178))))

    layer, draw = aa_layer(patch)
    draw_stone_jointing(draw, rng, strength=44)
    draw_bay_frames(draw, rng, lower_variant=False)

    # Break the clone-stamp feel with selective warm/dark watercolor glazes.
    for a, b in [(115, 196), (305, 397), (492, 592), (706, 780)]:
        rect(draw, (a, 78 + rng.normal(0, 1), b, 219 + rng.normal(0, 1)), rgb_tuple([218, 201, 169], 18))
    rect(draw, (0, 0, W, 18), rgb_tuple(STONE + np.array([4, 3, 0]), 92))
    line(draw, (0, 24, W, 22), rgb_tuple(INK, 34), width=0.75)

    out = layer.resize((W, H), Image.Resampling.LANCZOS).convert("RGB").filter(ImageFilter.GaussianBlur(0.18))
    return out


def candidate_ref_piers(src: np.ndarray) -> Image.Image:
    rng = np.random.default_rng(2202)
    patch = stone_texture(src, 2202, warm=5.0)
    layer, draw = aa_layer(patch)

    # Reference-informed base: same pier rhythm, but the lower portion becomes a quiet stone podium.
    rect(draw, (0, 0, W, H), rgb_tuple(STONE + np.array([4, 3, -2]), 35))
    draw_stone_jointing(draw, rng, strength=58)
    draw_bay_frames(draw, rng, lower_variant=True)

    # Subtle cornices and pier caps similar to the real refs, with no lettering.
    for y, alpha in [(72, 72), (153, 62), (220, 116)]:
        rect(draw, (2, y - 3, W - 2, y + 3), rgb_tuple(STONE + np.array([13, 10, 3]), alpha))
        line(draw, (0, y + 4, W, y + 3), rgb_tuple(INK, 28), width=0.55)

    for left, right, _ in FRONT_BAYS:
        cap_y = 154
        rect(draw, (left - 10, cap_y, right + 10, cap_y + 7), rgb_tuple(STONE + np.array([10, 7, 2]), 80))
        line(draw, (left - 9, cap_y + 8, right + 9, cap_y + 8), rgb_tuple(INK, 28), width=0.55)

    # Keep the entrance implication very restrained: shadowed small recesses, not a glass hall.
    for a, b in [(333, 384), (522, 573)]:
        rect(draw, (a, 224, b, 252), rgb_tuple(WINDOW * 0.78, 70))
        rect(draw, (a + 3, 226, b - 3, 248), rgb_tuple(WARM_GLOW * 0.45 + WINDOW * 0.55, 34))

    # Watercolor/ink irregularities.
    for _ in range(115):
        x = rng.uniform(0, W)
        y = rng.uniform(0, H)
        radius = rng.uniform(0.25, 1.2)
        shade = STONE_SHADOW + rng.normal(0, 8, 3)
        rect(draw, (x, y, x + radius, y + radius), rgb_tuple(shade, int(rng.uniform(8, 22))))

    out = layer.resize((W, H), Image.Resampling.LANCZOS).convert("RGB").filter(ImageFilter.GaussianBlur(0.22))
    return out


def candidate_soft_podium(src: np.ndarray) -> Image.Image:
    rng = np.random.default_rng(2203)
    if M3_FULL.exists():
        patch = Image.open(M3_FULL).convert("RGB").crop(BOX)
    else:
        patch = candidate_clone_plinth(src)

    # Work with translucent watercolor passes over the seamless clone baseline.
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")

    podium = stone_texture(src, 2203, warm=3.0).convert("RGBA")
    grad = np.zeros((H, W), dtype=np.uint8)
    for y in range(H):
        if y < 138:
            a = 0
        elif y < 188:
            a = int((y - 138) / 50 * 42)
        elif y < 232:
            a = 58
        else:
            a = 72
        grad[y, :] = a
    alpha = Image.fromarray(grad).filter(ImageFilter.GaussianBlur(3.0))
    overlay.alpha_composite(Image.composite(podium, Image.new("RGBA", (W, H), (0, 0, 0, 0)), alpha))
    draw = ImageDraw.Draw(overlay, "RGBA")

    # Quiet ground-floor hierarchy from the real refs: stone still dominates;
    # only small recessed openings remain at the lowest level.
    for y, alpha_v, width in [(177, 26, 0.75), (207, 24, 0.6), (229, 36, 0.85), (248, 30, 0.65)]:
        line(draw, (0, y + rng.normal(0, 0.5), W, y + rng.normal(0, 0.5)), rgb_tuple(INK, alpha_v), width=width, scale=1)
        line(draw, (0, y - 2, W, y - 2), rgb_tuple(STONE + np.array([12, 8, 0]), int(alpha_v * 0.18)), width=1, scale=1)

    # Break repeated cloned window rows with varied stone washes and slight shadows.
    wash_rects = [(104, 154), (198, 251), (301, 346), (396, 449), (492, 546), (605, 644), (689, 728), (786, 827)]
    for idx, (a, b) in enumerate(wash_rects):
        top = 168 + (idx % 3) * 2
        bottom = 225 + (idx % 2) * 3
        color = STONE + rng.normal(0, 5, 3)
        rect(draw, (a, top, b, bottom), rgb_tuple(color, 22 + (idx % 2) * 6), scale=1)
        line(draw, (a + 1, top, a + 1, bottom), rgb_tuple(INK, 10), width=0.5, scale=1)

    # Low punched openings: narrow and recessed, so they do not read as a tall glass hall.
    openings = [(144, 171), (258, 286), (350, 378), (443, 476), (539, 566), (678, 700), (742, 763), (839, 860)]
    for idx, (a, b) in enumerate(openings):
        y_top = 229 + (idx % 2)
        y_bot = 251 - (idx % 3 == 0)
        rect(draw, (a - 1, y_top - 1, b + 1, y_bot + 1), rgb_tuple(INK, 24), scale=1)
        rect(draw, (a, y_top, b, y_bot), rgb_tuple(WINDOW * 0.78, 54), scale=1)
        if idx in {2, 4}:
            rect(draw, (a + 3, y_top + 2, b - 4, y_bot - 2), rgb_tuple(WARM_GLOW * 0.55 + WINDOW * 0.45, 12), scale=1)

    # Reinforce the facade piers with uneven ink/wash lines rather than computer-flat rectangles.
    for x in [91, 129, 191, 233, 290, 321, 379, 414, 475, 509, 571, 604, 628, 667, 704, 738, 772, 809, 858]:
        line(draw, (x + rng.normal(0, 0.45), 145, x + rng.normal(0, 0.45), H - 15), rgb_tuple(INK, 13), width=0.4, scale=1)
        line(draw, (x + 2 + rng.normal(0, 0.45), 149, x + 2 + rng.normal(0, 0.45), H - 20), rgb_tuple(STONE + np.array([15, 11, 5]), 12), width=0.4, scale=1)

    # Fine watercolor speckle and uneven darkening at the base.
    for _ in range(90):
        x = rng.uniform(5, W - 5)
        y = rng.uniform(156, H - 8)
        r = rng.uniform(0.4, 1.8)
        color = STONE_SHADOW + rng.normal(0, 8, 3)
        rect(draw, (x, y, x + r, y + r), rgb_tuple(color, int(rng.uniform(8, 20))), scale=1)

    overlay = overlay.filter(ImageFilter.GaussianBlur(0.85))
    result = patch.convert("RGBA")
    result.alpha_composite(overlay)
    return result.convert("RGB")


def candidate_stronger_podium(src: np.ndarray) -> Image.Image:
    rng = np.random.default_rng(2204)
    if M3_FULL.exists():
        patch = Image.open(M3_FULL).convert("RGB").crop(BOX)
    else:
        patch = candidate_clone_plinth(src)

    podium = stone_texture(src, 2204, warm=4.0).convert("RGBA")
    alpha_arr = np.zeros((H, W), dtype=np.uint8)
    for y in range(H):
        if y < 130:
            a = 0
        elif y < 178:
            a = int((y - 130) / 48 * 95)
        elif y < 224:
            a = 122
        else:
            a = 142
        alpha_arr[y, :] = a
    stone_alpha = Image.fromarray(alpha_arr).filter(ImageFilter.GaussianBlur(5.0))

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    overlay.alpha_composite(Image.composite(podium, Image.new("RGBA", (W, H), (0, 0, 0, 0)), stone_alpha))
    draw = ImageDraw.Draw(overlay, "RGBA")

    # Preserve tower rhythm with hand-painted piers and smaller punched openings.
    for left, right, runs in FRONT_BAYS:
        rect(draw, (left - 7, 146, left - 2, H - 14), rgb_tuple(STONE + np.array([9, 6, 1]), 26), scale=1)
        rect(draw, (right + 2, 146, right + 7, H - 14), rgb_tuple(STONE + np.array([7, 5, 1]), 24), scale=1)
        line(draw, (left - 8, 149, left - 8, H - 18), rgb_tuple(INK, 16), width=0.45, scale=1)
        for wx0, wx1 in runs:
            draw_window(draw, wx0 + 2.0, wx1 - 1.6, 166 + rng.normal(0, 1.0), 211 + rng.normal(0, 1.0), 72, rng.normal(0, 3.0))

    for wx0, wx1 in RIGHT_RUNS:
        draw_window(draw, wx0 + 0.8, wx1 - 0.4, 164, 206 + rng.normal(0, 1.0), 58, rng.normal(0, 3.0))

    # Low, quiet base openings. These are broken into separate recesses to avoid a glass hall.
    for idx, (a, b) in enumerate([(148, 171), (260, 285), (350, 376), (447, 473), (541, 565), (681, 701), (743, 762), (840, 858)]):
        rect(draw, (a - 1, 232, b + 1, 252), rgb_tuple(INK, 18), scale=1)
        rect(draw, (a, 233, b, 251), rgb_tuple(WINDOW * 0.8, 42), scale=1)
        if idx in (2, 4):
            rect(draw, (a + 3, 236, b - 3, 248), rgb_tuple(WARM_GLOW * 0.5 + WINDOW * 0.5, 10), scale=1)

    for y, alpha_v in [(159, 14), (222, 28), (244, 30)]:
        line(draw, (0, y + rng.normal(0, 0.4), W, y + rng.normal(0, 0.4)), rgb_tuple(INK, alpha_v), width=0.55, scale=1)
    for x in range(24, W, 68):
        line(draw, (x + rng.normal(0, 0.5), 220, x + rng.normal(0, 0.5), H - 10), rgb_tuple(STONE_SHADOW, 16), width=0.35, scale=1)

    for _ in range(130):
        x = rng.uniform(0, W)
        y = rng.uniform(150, H)
        color = STONE_SHADOW + rng.normal(0, 7, 3)
        r = rng.uniform(0.4, 1.4)
        rect(draw, (x, y, x + r, y + r), rgb_tuple(color, int(rng.uniform(5, 16))), scale=1)

    overlay = overlay.filter(ImageFilter.GaussianBlur(0.95))
    result = patch.convert("RGBA")
    result.alpha_composite(overlay)
    return result.convert("RGB")


def candidate_soft_ref_hybrid(src: np.ndarray) -> Image.Image:
    if M3_FULL.exists():
        clone_base = Image.open(M3_FULL).convert("RGB").crop(BOX)
    else:
        clone_base = candidate_clone_plinth(src)
    manual = candidate_ref_piers(src).filter(ImageFilter.GaussianBlur(0.65))

    alpha_arr = np.zeros((H, W), dtype=np.uint8)
    for y in range(H):
        if y < 66:
            a = 0
        elif y < 134:
            a = int((y - 66) / 68 * 185)
        else:
            a = 208
        alpha_arr[y, :] = a
    alpha = Image.fromarray(alpha_arr).filter(ImageFilter.GaussianBlur(4.0))
    hybrid = Image.composite(manual, clone_base, alpha).convert("RGBA")

    # Add a final source-colored wash so the hand geometry sits back in the watercolor.
    rng = np.random.default_rng(2205)
    wash = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(wash, "RGBA")
    for _ in range(150):
        x = rng.uniform(0, W)
        y = rng.uniform(78, H)
        r = rng.uniform(0.5, 2.4)
        color = STONE_SHADOW + rng.normal(0, 9, 3)
        rect(draw, (x, y, x + r, y + r), rgb_tuple(color, int(rng.uniform(4, 14))), scale=1)
    for y, alpha_v in [(136, 12), (217, 20), (244, 22)]:
        line(draw, (0, y, W, y + 0.4), rgb_tuple(INK, alpha_v), width=0.45, scale=1)
    wash = wash.filter(ImageFilter.GaussianBlur(0.8))
    hybrid.alpha_composite(wash)
    return hybrid.convert("RGB")


def composite(src_img: Image.Image, patch: Image.Image, key: str) -> Image.Image:
    x0, y0, x1, y1 = BOX
    base = src_img.copy()
    src_patch = src_img.crop(BOX)

    # Preserve foreground tree/rail details and feather only inside the allowed box.
    src_np = np.asarray(src_img.convert("RGB"))
    fg = foreground_mask(src_np)
    patched = patch.copy()
    patched.paste(src_patch, (0, 0), fg)

    # Edge feather avoids cut lines while all changed pixels remain inside BOX.
    edge = edge_feather_mask()
    mixed = Image.composite(patched, src_patch, edge)
    base.paste(mixed, (x0, y0))

    full_path = OUT / f"{key}_composited.png"
    zoom_path = OUT / f"{key}_zoom.png"
    patch_path = OUT / f"{key}_base_patch.png"
    base.save(full_path)
    base.crop(ZOOM).save(zoom_path)
    patched.save(patch_path)
    return base


def make_contact(candidates: list[Candidate]) -> None:
    thumbs: list[tuple[str, Image.Image]] = []
    src_img = Image.open(SRC).convert("RGB")
    thumbs.append(("source crop", src_img.crop(ZOOM)))
    if M3_ZOOM.exists():
        thumbs.append(("M3 reference", Image.open(M3_ZOOM).convert("RGB").resize((1060, 420))))
    for cand in candidates:
        thumbs.append((cand.label, Image.open(OUT / f"{cand.key}_zoom.png").convert("RGB")))

    tile_w, tile_h = 530, 210
    pad = 18
    header = 26
    sheet = Image.new("RGB", (tile_w * 2 + pad * 3, (tile_h + header + pad) * ((len(thumbs) + 1) // 2) + pad), (244, 241, 232))
    draw = ImageDraw.Draw(sheet)
    for idx, (label, img) in enumerate(thumbs):
        row = idx // 2
        col = idx % 2
        x = pad + col * (tile_w + pad)
        y = pad + row * (tile_h + header + pad)
        draw.text((x, y), label, fill=(42, 45, 48))
        thumb = ImageOps.contain(img, (tile_w, tile_h), Image.Resampling.LANCZOS)
        sheet.paste(thumb, (x, y + header))
    sheet.save(OUT / "w2_manual_paintover_contact.png")

    # Source refs sheet for this lane, cropped/resized only for review context.
    refs: list[tuple[str, Image.Image]] = [
        ("artwork source", src_img.crop(ZOOM)),
        ("ritz_cahill2", Image.open(CAHILL2).convert("RGB")),
        ("ritz_streetlevel", Image.open(STREET).convert("RGB")),
    ]
    ref_sheet = Image.new("RGB", (360 * len(refs), 310), (244, 241, 232))
    rdraw = ImageDraw.Draw(ref_sheet)
    for i, (label, img) in enumerate(refs):
        thumb = ImageOps.contain(img, (340, 270), Image.Resampling.LANCZOS)
        x = 10 + i * 360
        rdraw.text((x, 8), label, fill=(42, 45, 48))
        ref_sheet.paste(thumb, (x, 34))
    ref_sheet.save(OUT / "w2_manual_reference_sheet.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    src_img = Image.open(SRC).convert("RGB")
    src = np.asarray(src_img)

    candidates = [
        Candidate("w2_manual_a_clone_plinth", "A clone plus stone plinth", candidate_clone_plinth(src)),
        Candidate("w2_manual_b_ref_piers", "B reference-informed piers", candidate_ref_piers(src)),
        Candidate("w2_manual_c_soft_podium", "C soft podium over clone", candidate_soft_podium(src)),
        Candidate("w2_manual_d_stronger_podium", "D stronger stone podium", candidate_stronger_podium(src)),
        Candidate("w2_manual_e_soft_ref_hybrid", "E soft ref-pier hybrid", candidate_soft_ref_hybrid(src)),
    ]
    for cand in candidates:
        cand.patch.save(OUT / f"{cand.key}_raw_patch_unfeathered.png")
        composite(src_img, cand.patch, cand.key)
    make_contact(candidates)


if __name__ == "__main__":
    main()
