#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi


EDGE = Path("/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/festive/images/edge-v4-watercolor-piped-artwork.png")
TASK = Path("/Users/za/Documents/product images repo/tasks/festive-edge-v4-peppermint-overlay")
OUT = TASK / "outputs"
ANALYSIS = TASK / "analysis"
PROD = Path("/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/festive/images/candidates")


def rgba(path: Path) -> np.ndarray:
    return np.array(Image.open(path).convert("RGBA"))


def resize_to_base(path: Path, size: tuple[int, int]) -> np.ndarray:
    im = Image.open(path).convert("RGB").resize(size, Image.Resampling.LANCZOS)
    arr = np.array(im)
    out = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    out[..., :3] = arr
    out[..., 3] = 255
    return out


def ginger_inner_mask(edge: np.ndarray) -> np.ndarray:
    rgb = edge[..., :3].astype(np.int16)
    a = edge[..., 3] > 0
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    ginger = a & (r > 90) & (g > 45) & (b < 190) & ((r - g) > 10) & ((g - b) > 5)
    ginger = ndi.binary_closing(ginger, iterations=2)
    ginger = ndi.binary_fill_holes(ginger)
    return ndi.binary_erosion(ginger, iterations=6)


def alpha_from(mask: np.ndarray, blur: float) -> np.ndarray:
    im = Image.fromarray((mask.astype(np.uint8) * 255), "L")
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return np.array(im).astype(np.float32) / 255.0


def decoration_alpha(edge: np.ndarray, donor: np.ndarray, inner: np.ndarray) -> np.ndarray:
    rgb = donor[..., :3].astype(np.float32)
    base = edge[..., :3].astype(np.float32)
    maxc = rgb.max(axis=2)
    minc = rgb.min(axis=2)
    sat = (maxc - minc) / np.maximum(maxc, 1)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    diff = np.linalg.norm(rgb - base, axis=2)

    red = (r > 135) & ((r - g) > 22) & ((r - b) > 22)
    green = (g > 105) & ((g - r) > -8) & ((g - b) > 8) & (sat > 0.18)
    blue = (b > 120) & ((b - r) > 5) & (sat > 0.18)
    purple = (r > 105) & (b > 105) & (g < 145) & (sat > 0.16)
    colored_candy = inner & (red | green | blue | purple | ((sat > 0.34) & (maxc > 80)))

    # White candy-cane bodies, sugar pearls, and snowflake highlights are low
    # saturation, so keep them only when near coloured candy or when they differ
    # strongly from the warm cookie base inside the gingerbread interior.
    dist_col = ndi.distance_transform_edt(~colored_candy)
    near_col = dist_col < 22
    white = inner & (maxc > 205) & (sat < 0.18) & (diff > 30) & near_col
    pearl = inner & (maxc > 215) & (sat < 0.12) & (diff > 42)
    blue_snow = inner & (b > 135) & (g > 130) & (r < 190) & (diff > 28)
    shadow = inner & near_col & (diff > 35) & (maxc < 210) & (sat > 0.09)

    mask = colored_candy | white | pearl | blue_snow | shadow
    mask = ndi.binary_opening(mask, iterations=1)
    mask = ndi.binary_closing(mask, iterations=1)

    # Remove broad low-detail fills: only keep connected components that look like
    # candy, bead trails, snowflakes, or ribbons rather than entire panel wash.
    labels, n = ndi.label(mask)
    keep = np.zeros(mask.shape, dtype=bool)
    for i in range(1, n + 1):
        ys, xs = np.where(labels == i)
        if len(xs) < 12:
            continue
        x0, x1 = xs.min(), xs.max()
        y0, y1 = ys.min(), ys.max()
        area = len(xs)
        bbox_area = max(1, (x1 - x0 + 1) * (y1 - y0 + 1))
        fill = area / bbox_area
        # Large garlands/ribbons are okay; broad panel haze is not.
        if area < 28000 and fill < 0.82:
            keep[labels == i] = True
        elif (x1 - x0) > 120 and (y1 - y0) < 80:
            keep[labels == i] = True
        elif (y1 - y0) > 180 and (x1 - x0) < 90:
            keep[labels == i] = True
    alpha = alpha_from(keep, 0.8)
    alpha *= alpha_from(inner, 0.7)
    alpha[alpha < 0.025] = 0
    return np.clip(alpha, 0, 0.96)


def composite(edge: np.ndarray, donor: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    out = edge.astype(np.float32).copy()
    rgb = donor[..., :3].astype(np.float32)
    a = alpha[..., None]
    out[..., :3] = rgb * a + out[..., :3] * (1 - a)
    out[..., 3] = edge[..., 3]
    outside = edge[..., 3] == 0
    out[outside] = edge[outside]
    return np.clip(out, 0, 255).astype(np.uint8)


def save(arr: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr, "RGBA").save(path)


def process(raw_name: str, final_name: str) -> None:
    edge = rgba(EDGE)
    donor = resize_to_base(OUT / raw_name, (edge.shape[1], edge.shape[0]))
    inner = ginger_inner_mask(edge)
    alpha = decoration_alpha(edge, donor, inner)
    result = composite(edge, donor, alpha)
    save(result, OUT / final_name)
    save(result, PROD / final_name)
    dbg = np.zeros_like(edge)
    dbg[..., :3] = donor[..., :3]
    dbg[..., 3] = (alpha * 255).astype(np.uint8)
    save(dbg, ANALYSIS / f"{Path(final_name).stem}-donor-decoration-alpha.png")
    print(final_name, "alpha_pixels", int((alpha > 0).sum()), "copied", PROD / final_name)


def main() -> None:
    process("edge-v4-peppermint-option-a-raw-openai.png", "edge-v4-peppermint-option-1-highres.png")
    process("edge-v4-peppermint-option-b-raw-openai.png", "edge-v4-peppermint-option-2-highres.png")


if __name__ == "__main__":
    main()
