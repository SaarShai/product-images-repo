#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi


EDGE = Path("/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/festive/images/edge-v4-watercolor-piped-artwork.png")
V1 = Path("/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/new cutting files/NEW Festive/images/candidates/styled-v1-peppermint-artwork.png")
TASK = Path("/Users/za/Documents/product images repo/tasks/festive-edge-v4-peppermint-overlay")
OUT = TASK / "outputs"
ANALYSIS = TASK / "analysis"
PROD = Path("/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/festive/images/candidates")


def rgba(path: Path) -> np.ndarray:
    return np.array(Image.open(path).convert("RGBA"))


def save(arr: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA").save(path)


def binary_to_alpha(mask: np.ndarray, blur: float = 0.0) -> np.ndarray:
    im = Image.fromarray((mask.astype(np.uint8) * 255), "L")
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return np.array(im).astype(np.float32) / 255.0


def gingerbread_inner_mask(edge: np.ndarray) -> np.ndarray:
    rgb = edge[..., :3].astype(np.int16)
    a = edge[..., 3] > 0
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    ginger = a & (r > 90) & (g > 45) & (b < 190) & ((r - g) > 10) & ((g - b) > 5)
    ginger = ndi.binary_closing(ginger, iterations=2)
    ginger = ndi.binary_fill_holes(ginger)
    ginger = ndi.binary_opening(ginger, iterations=1)
    return ndi.binary_erosion(ginger, iterations=3)


def source_item_alpha(src: np.ndarray) -> np.ndarray:
    rgb = src[..., :3].astype(np.float32)
    src_a = src[..., 3].astype(np.float32) / 255.0
    maxc = rgb.max(axis=2)
    minc = rgb.min(axis=2)
    sat = np.divide(maxc - minc, np.maximum(maxc, 1), out=np.zeros_like(maxc), where=maxc > 0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]

    colored = (src_a > 0.04) & (sat > 0.30) & (maxc > 70)
    red = (src_a > 0.04) & (r > 135) & ((r - g) > 22) & ((r - b) > 22)
    blue = (src_a > 0.04) & (b > 120) & ((b - r) > 8)
    green = (src_a > 0.04) & (g > 115) & ((g - r) > -10) & ((g - b) > 10)
    purple = (src_a > 0.04) & (r > 115) & (b > 115) & (g < 130)
    color_core = colored | red | blue | green | purple

    # Pull in the white icing strokes and their soft shadows only when they are
    # close to coloured candy pixels, so the pale icy V1 panel fill is not used.
    red_core = red | ((r > 150) & ((r - g) > 30) & ((r - b) > 30) & (src_a > 0.04))
    dist_red = ndi.distance_transform_edt(~red_core)
    dist_color = ndi.distance_transform_edt(~color_core)
    near_red = dist_red < 9
    near_color = dist_color < 5
    white_icing = (src_a > 0.08) & near_red & (maxc > 205) & (sat < 0.16)
    candy_shadow = (src_a > 0.08) & near_color & (maxc < 205) & (sat > 0.12)

    item = color_core | white_icing | candy_shadow
    item = ndi.binary_opening(item, iterations=1)
    item = ndi.binary_closing(item, iterations=1)
    alpha = src_a * binary_to_alpha(item, blur=0.9)
    alpha[alpha < 0.02] = 0
    return np.clip(alpha, 0, 1)


def preserve_edge_alpha(arr: np.ndarray, edge: np.ndarray) -> np.ndarray:
    out = arr.astype(np.uint8).copy()
    base_alpha = edge[..., 3]
    outside = base_alpha == 0
    out[outside] = edge[outside]
    out[..., 3] = base_alpha
    return out


def composite_over(base: np.ndarray, top_rgb: np.ndarray, top_alpha: np.ndarray) -> np.ndarray:
    out = base.astype(np.float32).copy()
    a = np.clip(top_alpha[..., None], 0, 1)
    out[..., :3] = top_rgb.astype(np.float32) * a + out[..., :3] * (1 - a)
    out[..., 3] = np.maximum(out[..., 3], (top_alpha * 255))
    return out


def warm_to_edge_style(src_rgb: np.ndarray, strength: float) -> np.ndarray:
    rgb = src_rgb.astype(np.float32)
    warm = rgb.copy()
    warm[..., 0] = np.clip(warm[..., 0] * 1.02 + 4, 0, 255)
    warm[..., 1] = np.clip(warm[..., 1] * 0.97 + 2, 0, 255)
    warm[..., 2] = np.clip(warm[..., 2] * 0.92, 0, 255)
    return rgb * (1 - strength) + warm * strength


def option_a(edge: np.ndarray, src: np.ndarray, inner: np.ndarray, item_alpha: np.ndarray) -> np.ndarray:
    clip = binary_to_alpha(inner, blur=1.2)
    alpha = np.clip(item_alpha * clip * 0.96, 0, 0.96)
    top_rgb = warm_to_edge_style(src[..., :3], 0.35)
    return preserve_edge_alpha(composite_over(edge, top_rgb, alpha), edge)


def option_b(edge: np.ndarray, src: np.ndarray, inner: np.ndarray, item_alpha: np.ndarray) -> np.ndarray:
    labels, n = ndi.label(item_alpha > 0.08)
    keep = np.zeros(labels.shape, dtype=bool)
    h, w = labels.shape
    for i in range(1, n + 1):
        ys, xs = np.where(labels == i)
        if len(xs) < 18:
            continue
        area = len(xs)
        x0, x1 = xs.min(), xs.max()
        y0, y1 = ys.min(), ys.max()
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        tall_strip = y1 > h * 0.42
        roof = y0 < h * 0.42
        small_object = (area < 2200) and ((x1 - x0) < 120) and ((y1 - y0) < 120)
        ribbonish = (y1 - y0) > 95 or (x1 - x0) > 95
        # Sparse but still shaped: retain a contour-following garland on the roof,
        # a single trail per wall strip, and small beads/snowflakes as accents.
        if roof and (ribbonish or small_object) and not (cy > 710 and 420 < cx < 1040 and area > 9000):
            keep[labels == i] = True
        elif tall_strip and (ribbonish or small_object) and ((cx < 230) or (300 < cx < 470) or (1010 < cx < 1180) or (cx > 1240)):
            if area > 5000 or small_object:
                keep[labels == i] = True
        elif small_object and (int(cx + cy) % 3 != 0):
            keep[labels == i] = True

    sparse_alpha = item_alpha * binary_to_alpha(keep, blur=0.8)
    clip = binary_to_alpha(inner, blur=1.2)
    alpha = np.clip(sparse_alpha * clip * 0.86, 0, 0.86)
    top_rgb = warm_to_edge_style(src[..., :3], 0.55)
    out = composite_over(edge, top_rgb, alpha)

    # Add a few very soft sugar pearls on gingerbread only, using colours sampled
    # from the V1 palette, to keep the sparse option from looking accidentally erased.
    pearl_layer = np.zeros_like(edge, dtype=np.float32)
    pearl_alpha = np.zeros(edge.shape[:2], dtype=np.float32)
    circles = [
        (545, 472, 9, (235, 247, 248)), (620, 500, 7, (220, 239, 246)),
        (780, 565, 8, (244, 239, 225)), (890, 604, 7, (231, 246, 248)),
        (132, 1160, 8, (221, 242, 248)), (370, 1288, 7, (240, 236, 221)),
        (1090, 1210, 7, (223, 242, 248)), (1270, 1152, 8, (242, 238, 223)),
    ]
    yy, xx = np.mgrid[0:edge.shape[0], 0:edge.shape[1]]
    for x, y, rad, col in circles:
        m = (xx - x) ** 2 + (yy - y) ** 2 <= rad ** 2
        pearl_layer[m, :3] = col
        pearl_alpha[m] = np.maximum(pearl_alpha[m], 0.62)
    pearl_alpha = np.array(Image.fromarray((pearl_alpha * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(1.0))).astype(np.float32) / 255
    pearl_alpha *= clip * 0.65
    return preserve_edge_alpha(composite_over(out.astype(np.uint8), pearl_layer[..., :3], pearl_alpha), edge)


def write_debug(edge: np.ndarray, src: np.ndarray, inner: np.ndarray, item_alpha: np.ndarray) -> None:
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    edge_dbg = edge.copy()
    edge_dbg[..., :3] = np.where(inner[..., None], np.array([70, 200, 90]), edge_dbg[..., :3])
    edge_dbg[..., 3] = np.maximum(edge_dbg[..., 3], (inner.astype(np.uint8) * 140))
    save(edge_dbg, ANALYSIS / "edge-inner-mask-debug.png")

    item_dbg = np.zeros_like(src)
    item_dbg[..., :3] = src[..., :3]
    item_dbg[..., 3] = (item_alpha * 255).astype(np.uint8)
    save(item_dbg, ANALYSIS / "v1-extracted-decoration-layer-debug.png")


def main() -> None:
    edge = rgba(EDGE)
    src = rgba(V1)
    if edge.shape != src.shape:
        raise SystemExit(f"shape mismatch: edge={edge.shape} source={src.shape}")
    inner = gingerbread_inner_mask(edge)
    item_alpha = source_item_alpha(src)
    write_debug(edge, src, inner, item_alpha)

    a = option_a(edge, src, inner, item_alpha)
    b = option_b(edge, src, inner, item_alpha)
    for name, arr in [
        ("edge-v4-peppermint-option-a-composite.png", a),
        ("edge-v4-peppermint-option-b-composite.png", b),
    ]:
        save(arr, OUT / name)
        save(arr, PROD / name)

    print(f"inner_pixels={int(inner.sum())}")
    print(f"item_alpha_pixels={int((item_alpha > 0).sum())}")
    print(f"wrote={OUT / 'edge-v4-peppermint-option-a-composite.png'}")
    print(f"wrote={OUT / 'edge-v4-peppermint-option-b-composite.png'}")
    print(f"copied={PROD / 'edge-v4-peppermint-option-a-composite.png'}")
    print(f"copied={PROD / 'edge-v4-peppermint-option-b-composite.png'}")


if __name__ == "__main__":
    main()
