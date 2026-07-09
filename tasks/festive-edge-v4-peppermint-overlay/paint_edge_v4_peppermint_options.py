#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi


EDGE = Path("/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/festive/images/edge-v4-watercolor-piped-artwork.png")
TASK = Path("/Users/za/Documents/product images repo/tasks/festive-edge-v4-peppermint-overlay")
OUT = TASK / "outputs"
PROD = Path("/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/festive/images/candidates")


def base_image() -> np.ndarray:
    return np.array(Image.open(EDGE).convert("RGBA"))


def ginger_inner_mask(edge: np.ndarray) -> np.ndarray:
    rgb = edge[..., :3].astype(np.int16)
    a = edge[..., 3] > 0
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    ginger = a & (r > 90) & (g > 45) & (b < 190) & ((r - g) > 10) & ((g - b) > 5)
    ginger = ndi.binary_closing(ginger, iterations=2)
    ginger = ndi.binary_fill_holes(ginger)
    ginger = ndi.binary_erosion(ginger, iterations=5)
    return ginger


def mask_to_alpha(mask: np.ndarray, blur: float = 0.8) -> np.ndarray:
    im = Image.fromarray((mask.astype(np.uint8) * 255), "L")
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return np.array(im).astype(np.float32) / 255.0


def noise_field(shape: tuple[int, int], seed: int, scale: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    small = rng.normal(0, 1, (max(2, shape[0] // scale), max(2, shape[1] // scale)))
    im = Image.fromarray(((small - small.min()) / (np.ptp(small) + 1e-6) * 255).astype(np.uint8), "L")
    im = im.resize((shape[1], shape[0]), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(1.2))
    arr = np.array(im).astype(np.float32) / 255.0
    return arr - 0.5


def textured_color(alpha: np.ndarray, color: tuple[int, int, int], seed: int, strength: float = 0.13) -> np.ndarray:
    n = noise_field(alpha.shape, seed)
    rgb = np.zeros((*alpha.shape, 3), dtype=np.float32)
    base = np.array(color, dtype=np.float32)
    tint = 1 + n[..., None] * strength
    rgb[:] = np.clip(base * tint, 0, 255)
    return rgb


def composite(base: np.ndarray, rgb: np.ndarray, alpha: np.ndarray, inner: np.ndarray, opacity: float = 1.0) -> np.ndarray:
    out = base.astype(np.float32).copy()
    a = np.clip(alpha * mask_to_alpha(inner, 0.5) * opacity, 0, 1)[..., None]
    out[..., :3] = rgb * a + out[..., :3] * (1 - a)
    out[..., 3] = base[..., 3]
    return np.clip(out, 0, 255).astype(np.uint8)


def add_shape(base: np.ndarray, mask: np.ndarray, color: tuple[int, int, int], inner: np.ndarray, seed: int, opacity: float = 0.9, blur: float = 0.8) -> np.ndarray:
    alpha = mask_to_alpha(mask, blur)
    rgb = textured_color(alpha, color, seed)
    return composite(base, rgb, alpha, inner, opacity)


def stroke_mask(size: tuple[int, int], points: list[tuple[int, int]], width: int) -> np.ndarray:
    im = Image.new("L", size, 0)
    draw = ImageDraw.Draw(im)
    draw.line(points, fill=255, width=width, joint="curve")
    for x, y in points:
        r = width // 2
        draw.ellipse((x - r, y - r, x + r, y + r), fill=255)
    return np.array(im) > 0


def candy_ribbon(base: np.ndarray, inner: np.ndarray, points: list[tuple[int, int]], width: int, seed: int, phase: float = 0) -> np.ndarray:
    h, w = base.shape[:2]
    mask = stroke_mask((w, h), points, width)
    shadow = ndi.binary_dilation(mask, iterations=2) & ~mask
    out = add_shape(base, shadow, (128, 86, 48), inner, seed + 1, opacity=0.12, blur=2.0)
    out = add_shape(out, mask, (252, 247, 231), inner, seed + 2, opacity=0.88, blur=1.0)
    yy, xx = np.mgrid[0:h, 0:w]
    stripes = (((xx * 0.82 + yy * 0.55 + phase) % (width * 1.45)) < width * 0.42) & mask
    out = add_shape(out, stripes, (200, 36, 32), inner, seed + 3, opacity=0.82, blur=0.9)
    highlight = ndi.binary_erosion(mask, iterations=max(1, width // 8))
    out = add_shape(out, highlight & ~stripes, (255, 252, 238), inner, seed + 4, opacity=0.22, blur=2.0)
    return out


def peppermint(base: np.ndarray, inner: np.ndarray, x: int, y: int, r: int, seed: int, opacity: float = 0.92) -> np.ndarray:
    h, w = base.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    circle = (xx - x) ** 2 + (yy - y) ** 2 <= r ** 2
    out = add_shape(base, ndi.binary_dilation(circle, iterations=2) & ~circle, (92, 63, 42), inner, seed, opacity=0.12, blur=2.2)
    out = add_shape(out, circle, (255, 249, 237), inner, seed + 1, opacity=opacity, blur=0.9)
    angle = (np.arctan2(yy - y, xx - x) + np.pi)
    radius = np.sqrt((xx - x) ** 2 + (yy - y) ** 2)
    wedges = (((angle * 6 / np.pi + radius / (r * 0.9)) % 2) < 0.9) & circle & (radius > r * 0.12)
    out = add_shape(out, wedges, (203, 34, 32), inner, seed + 2, opacity=0.82, blur=0.7)
    rim = circle & ~ndi.binary_erosion(circle, iterations=max(1, r // 7))
    out = add_shape(out, rim, (255, 248, 235), inner, seed + 3, opacity=0.45, blur=0.6)
    return out


def gumdrop(base: np.ndarray, inner: np.ndarray, x: int, y: int, r: int, color: tuple[int, int, int], seed: int) -> np.ndarray:
    h, w = base.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    body = ((xx - x) / (r * 1.0)) ** 2 + ((yy - y) / (r * 0.9)) ** 2 <= 1
    out = add_shape(base, ndi.binary_dilation(body, iterations=2) & ~body, (85, 56, 35), inner, seed, opacity=0.13, blur=2.1)
    out = add_shape(out, body, color, inner, seed + 1, opacity=0.82, blur=1.0)
    hi = ((xx - (x - r * 0.28)) / (r * 0.36)) ** 2 + ((yy - (y - r * 0.32)) / (r * 0.24)) ** 2 <= 1
    out = add_shape(out, hi & body, (255, 236, 226), inner, seed + 2, opacity=0.35, blur=1.6)
    rng = np.random.default_rng(seed + 3)
    speck = np.zeros((h, w), dtype=bool)
    ys, xs = np.where(body)
    if len(xs):
        pick = rng.choice(len(xs), size=min(len(xs) // 22 + 8, 70), replace=False)
        for px, py in zip(xs[pick], ys[pick]):
            rr = rng.integers(1, 3)
            speck[(xx - px) ** 2 + (yy - py) ** 2 <= rr ** 2] = True
    return add_shape(out, speck, (255, 246, 232), inner, seed + 4, opacity=0.58, blur=0.5)


def pearl(base: np.ndarray, inner: np.ndarray, x: int, y: int, r: int, seed: int, blue: bool = False) -> np.ndarray:
    color = (223, 244, 248) if blue else (248, 241, 223)
    return gumdrop(base, inner, x, y, r, color, seed)


def snowflake(base: np.ndarray, inner: np.ndarray, x: int, y: int, r: int, seed: int) -> np.ndarray:
    h, w = base.shape[:2]
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    for k in range(6):
        a = np.pi * k / 3
        x1, y1 = x + np.cos(a) * r, y + np.sin(a) * r
        x0, y0 = x - np.cos(a) * r * 0.18, y - np.sin(a) * r * 0.18
        d.line((x0, y0, x1, y1), fill=255, width=max(1, r // 9))
        bx, by = x + np.cos(a) * r * 0.58, y + np.sin(a) * r * 0.58
        for off in (-0.55, 0.55):
            aa = a + off
            d.line((bx, by, bx + np.cos(aa) * r * 0.23, by + np.sin(aa) * r * 0.23), fill=220, width=max(1, r // 12))
    mask = np.array(im) > 0
    return add_shape(base, mask, (104, 181, 213), inner, seed, opacity=0.62, blur=0.65)


def option_one(edge: np.ndarray, inner: np.ndarray) -> np.ndarray:
    out = edge.copy()
    out = candy_ribbon(out, inner, [(98, 960), (105, 1110), (112, 1290), (118, 1480), (112, 1690)], 43, 10, 0)
    out = candy_ribbon(out, inner, [(366, 990), (358, 1160), (366, 1370), (358, 1620), (369, 1840)], 31, 20, 34)
    out = candy_ribbon(out, inner, [(1084, 1025), (1074, 1200), (1082, 1410), (1075, 1630), (1090, 1790)], 31, 30, 12)
    out = candy_ribbon(out, inner, [(1302, 912), (1300, 1120), (1288, 1320), (1304, 1535), (1290, 1765)], 39, 40, 45)
    out = candy_ribbon(out, inner, [(1200, 350), (1200, 520)], 29, 50, 5)
    out = candy_ribbon(out, inner, [(480, 480), (575, 500), (680, 510), (785, 498), (890, 462)], 22, 60, 20)
    for i, (x, y, r) in enumerate([(488, 470, 26), (574, 488, 25), (660, 502, 25), (745, 502, 24), (830, 484, 26), (912, 455, 28), (438, 681, 28), (112, 1826, 20), (1322, 1822, 18)]):
        out = peppermint(out, inner, x, y, r, 100 + i)
    gumdrops = [
        (610, 640, 28, (126, 160, 66)), (690, 612, 24, (55, 148, 206)), (812, 652, 31, (205, 62, 51)),
        (948, 602, 29, (218, 75, 44)), (575, 214, 18, (118, 155, 63)), (1238, 492, 17, (117, 158, 63)),
        (100, 1050, 16, (57, 149, 198)), (145, 1138, 17, (120, 158, 62)), (388, 1348, 20, (63, 151, 205)),
        (1106, 1510, 18, (121, 158, 63)), (1110, 1688, 24, (178, 68, 160)), (1296, 1148, 21, (207, 56, 47)),
        (1314, 1360, 18, (55, 149, 204)), (1320, 1676, 20, (121, 156, 61)), (82, 827, 11, (204, 47, 35)), (1321, 824, 12, (207, 52, 38)),
    ]
    for i, item in enumerate(gumdrops):
        out = gumdrop(out, inner, *item, seed=200 + i)
    for i, (x, y, r) in enumerate([(502, 615, 28), (760, 575, 25), (890, 632, 23), (1238, 955, 20), (382, 1710, 18), (1090, 1110, 16)]):
        out = snowflake(out, inner, x, y, r, 300 + i)
    for i, (x, y, r, blue) in enumerate([(616, 553, 6, True), (710, 682, 7, False), (764, 682, 6, False), (875, 688, 7, True), (128, 1005, 6, True), (1098, 1320, 6, False), (1312, 1010, 6, True)]):
        out = pearl(out, inner, x, y, r, 400 + i, blue)
    return out


def option_two(edge: np.ndarray, inner: np.ndarray) -> np.ndarray:
    out = edge.copy()
    out = candy_ribbon(out, inner, [(520, 542), (635, 520), (780, 536), (930, 520)], 17, 510, 16)
    out = candy_ribbon(out, inner, [(118, 1000), (112, 1240), (122, 1515), (114, 1705)], 24, 520, 20)
    out = candy_ribbon(out, inner, [(366, 1040), (358, 1360), (370, 1745)], 20, 530, 60)
    out = candy_ribbon(out, inner, [(1082, 1080), (1072, 1410), (1084, 1740)], 20, 540, 44)
    out = candy_ribbon(out, inner, [(1305, 950), (1294, 1280), (1304, 1660)], 22, 550, 12)
    out = candy_ribbon(out, inner, [(1200, 372), (1198, 500)], 18, 560, 40)
    for i, (x, y, r) in enumerate([(536, 548, 18), (696, 524, 19), (865, 532, 18), (111, 1830, 17), (1320, 1826, 15)]):
        out = peppermint(out, inner, x, y, r, 600 + i, opacity=0.86)
    for i, item in enumerate([
        (598, 625, 19, (128, 159, 70)), (784, 644, 20, (206, 58, 49)), (928, 620, 18, (52, 149, 203)),
        (578, 250, 13, (123, 158, 67)), (453, 665, 16, (205, 52, 42)), (118, 1120, 13, (53, 148, 202)),
        (150, 1440, 14, (124, 158, 67)), (366, 1235, 16, (187, 68, 159)), (386, 1700, 16, (53, 148, 203)),
        (1092, 1215, 14, (205, 52, 42)), (1110, 1580, 15, (126, 158, 69)), (1298, 1125, 14, (56, 150, 204)),
        (1310, 1500, 16, (205, 53, 43)), (1235, 472, 13, (123, 157, 67)),
    ]):
        out = gumdrop(out, inner, *item, seed=700 + i)
    for i, (x, y, r) in enumerate([(505, 645, 20), (830, 596, 21), (1240, 970, 18), (383, 1625, 16), (1300, 960, 15)]):
        out = snowflake(out, inner, x, y, r, 800 + i)
    for i, (x, y, r, blue) in enumerate([
        (620, 574, 5, False), (685, 582, 5, True), (744, 584, 5, False), (880, 570, 5, True),
        (99, 1000, 5, True), (130, 1290, 5, False), (365, 1475, 5, True), (1082, 1350, 5, False), (1306, 1300, 5, True),
        (80, 828, 9, False), (1320, 824, 9, False),
    ]):
        out = pearl(out, inner, x, y, r, 900 + i, blue)
    return out


def save(arr: np.ndarray, name: str) -> None:
    for root in (OUT, PROD):
        root.mkdir(parents=True, exist_ok=True)
        Image.fromarray(arr, "RGBA").save(root / name)


def main() -> None:
    edge = base_image()
    inner = ginger_inner_mask(edge)
    a = option_one(edge, inner)
    b = option_two(edge, inner)
    a[~inner] = edge[~inner]
    b[~inner] = edge[~inner]
    a[..., 3] = edge[..., 3]
    b[..., 3] = edge[..., 3]
    save(a, "edge-v4-peppermint-option-1-highres.png")
    save(b, "edge-v4-peppermint-option-2-highres.png")
    print("wrote", OUT / "edge-v4-peppermint-option-1-highres.png")
    print("wrote", OUT / "edge-v4-peppermint-option-2-highres.png")
    print("copied", PROD / "edge-v4-peppermint-option-1-highres.png")
    print("copied", PROD / "edge-v4-peppermint-option-2-highres.png")
    print("inner_pixels", int(inner.sum()))


if __name__ == "__main__":
    main()
