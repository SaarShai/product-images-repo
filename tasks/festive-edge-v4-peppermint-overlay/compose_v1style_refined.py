#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

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


def alpha(mask: np.ndarray, blur: float = 0.7) -> np.ndarray:
    im = Image.fromarray((mask.astype(np.uint8) * 255), "L")
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return np.array(im).astype(np.float32) / 255.0


def ginger_inner(edge: np.ndarray) -> np.ndarray:
    rgb = edge[..., :3].astype(np.int16)
    a = edge[..., 3] > 0
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    ginger = a & (r > 90) & (g > 45) & (b < 190) & ((r - g) > 10) & ((g - b) > 5)
    ginger = ndi.binary_closing(ginger, iterations=2)
    ginger = ndi.binary_fill_holes(ginger)
    return ndi.binary_erosion(ginger, iterations=5)


def v1_object_mask(v1: np.ndarray, inner: np.ndarray, sparse: bool = False) -> np.ndarray:
    rgb = v1[..., :3].astype(np.float32)
    src_a = v1[..., 3].astype(np.float32) / 255.0
    maxc = rgb.max(axis=2)
    minc = rgb.min(axis=2)
    sat = (maxc - minc) / np.maximum(maxc, 1)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]

    red = (src_a > 0.04) & (r > 132) & ((r - g) > 20) & ((r - b) > 20)
    blue = (src_a > 0.04) & (b > 118) & ((b - r) > 2) & (sat > 0.14)
    green = (src_a > 0.04) & (g > 105) & ((g - b) > 5) & (sat > 0.15)
    purple = (src_a > 0.04) & (r > 105) & (b > 105) & (g < 145) & (sat > 0.14)
    candy_color = (red | blue | green | purple | ((src_a > 0.04) & (sat > 0.34) & (maxc > 75))) & inner

    # White portions of peppermint disks/candy canes: grow outward from high-
    # colour candy cores. This keeps the V1-style shaded icing bodies while
    # preventing the pale icy V1 panel wash from merging into one huge component.
    near_color = ndi.distance_transform_edt(~candy_color) < 18
    near_red = ndi.distance_transform_edt(~red) < 18
    white_near_candy = (src_a > 0.04) & (maxc > 178) & (sat < 0.24) & (near_red | near_color) & inner
    candy_shadow = (src_a > 0.04) & (maxc < 218) & (sat > 0.08) & near_color & inner

    # Sugar pearls are small low-saturation bright components not necessarily
    # touching red; component-size filter removes broad washed panel fill.
    bright = (src_a > 0.08) & (maxc > 205) & (sat < 0.18) & inner
    labels, n = ndi.label(bright)
    pearls = np.zeros(bright.shape, dtype=bool)
    for i in range(1, n + 1):
        ys, xs = np.where(labels == i)
        if len(xs) < 8:
            continue
        x0, x1 = xs.min(), xs.max()
        y0, y1 = ys.min(), ys.max()
        if len(xs) <= 2600 and (x1 - x0) <= 90 and (y1 - y0) <= 90:
            pearls[labels == i] = True

    mask = (candy_color | white_near_candy | candy_shadow | pearls) & inner

    labels, n = ndi.label(mask)
    keep = np.zeros(mask.shape, dtype=bool)
    for i in range(1, n + 1):
        ys, xs = np.where(labels == i)
        area = len(xs)
        if area < 10:
            continue
        x0, x1 = xs.min(), xs.max()
        y0, y1 = ys.min(), ys.max()
        width = x1 - x0 + 1
        height = y1 - y0 + 1
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        bbox_area = max(1, width * height)
        fill = area / bbox_area
        long_ribbon = (width > 90 and height < 150) or (height > 120 and width < 145)
        small_candy = area < 20000
        broad_fill = area > 42000 and fill > 0.35
        if not sparse:
            if (small_candy or long_ribbon) and not broad_fill:
                keep[labels == i] = True
        else:
            # Keep the airier route: roof garland, one trail per wall, and
            # selected candy clusters with enough empty gingerbread showing.
            roof = cy < 790
            far_left = cx < 230
            left_mid = 300 < cx < 470
            right_mid = 980 < cx < 1180
            far_right = cx > 1230
            if broad_fill:
                continue
            if (roof and (long_ribbon or area < 9000)) or (long_ribbon and (far_left or left_mid or right_mid or far_right)):
                keep[labels == i] = True
            elif area < 2800 and (int(cx + cy) % 4 != 0):
                keep[labels == i] = True
    return keep


def composite(edge: np.ndarray, v1: np.ndarray, mask: np.ndarray, inner: np.ndarray, opacity: float) -> np.ndarray:
    a = alpha(mask, 0.7) * alpha(inner, 0.35) * opacity
    out = edge.astype(np.float32).copy()
    rgb = v1[..., :3].astype(np.float32)
    out[..., :3] = rgb * a[..., None] + out[..., :3] * (1 - a[..., None])
    out[~inner] = edge[~inner]
    out[..., 3] = edge[..., 3]
    return np.clip(out, 0, 255).astype(np.uint8)


def main() -> None:
    edge = rgba(EDGE)
    v1 = rgba(V1)
    inner = ginger_inner(edge)
    full = v1_object_mask(v1, inner, sparse=False)
    sparse = v1_object_mask(v1, inner, sparse=True)

    opt1 = composite(edge, v1, full, inner, 0.96)
    opt2 = composite(edge, v1, sparse, inner, 0.92)

    for name, arr in [
        ("edge-v4-peppermint-option-1-highres.png", opt1),
        ("edge-v4-peppermint-option-2-highres.png", opt2),
    ]:
        save(arr, OUT / name)
        save(arr, PROD / name)
        print("copied", PROD / name)

    dbg = np.zeros_like(edge)
    dbg[..., :3] = v1[..., :3]
    dbg[..., 3] = (alpha(full, 0) * 255).astype(np.uint8)
    save(dbg, ANALYSIS / "v1-refined-object-mask-full.png")
    dbg2 = np.zeros_like(edge)
    dbg2[..., :3] = v1[..., :3]
    dbg2[..., 3] = (alpha(sparse, 0) * 255).astype(np.uint8)
    save(dbg2, ANALYSIS / "v1-refined-object-mask-sparse.png")
    print("full_pixels", int(full.sum()))
    print("sparse_pixels", int(sparse.sum()))


if __name__ == "__main__":
    main()
