#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi


BASE = Path("/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/festive/images/edge-v4-watercolor-piped-artwork.png")
PROD = Path("/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/festive/images/candidates")
ANALYSIS = Path("tasks/festive-edge-v4-peppermint-overlay/analysis")
OUTPUTS = [
    PROD / "edge-v4-peppermint-option-1-highres.png",
    PROD / "edge-v4-peppermint-option-2-highres.png",
]

# Alpha connected-component ids from the approved edge-v4 base.
LEFT_A = 6
LEFT_B = 8
RIGHT_A = 7
RIGHT_B = 5


def rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def component_maps(base: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    arr = np.array(base)
    alpha = arr[..., 3] > 0
    labels, _ = ndi.label(alpha)
    rgb = arr[..., :3].astype(np.int16)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    ginger = alpha & (r > 90) & (g > 45) & (b < 190) & ((r - g) > 10) & ((g - b) > 5)
    ginger = ndi.binary_closing(ginger, iterations=2)
    ginger = ndi.binary_fill_holes(ginger)
    inner = ndi.binary_erosion(ginger, iterations=7)
    return labels, inner


def bbox(mask: np.ndarray, pad: int = 0) -> tuple[int, int, int, int]:
    ys, xs = np.where(mask)
    if not len(xs):
        raise ValueError("empty mask")
    h, w = mask.shape
    return (
        max(0, int(xs.min()) - pad),
        max(0, int(ys.min()) - pad),
        min(w, int(xs.max()) + 1 + pad),
        min(h, int(ys.max()) + 1 + pad),
    )


def extract_decoration_layer(base_arr: np.ndarray, src_arr: np.ndarray, src_mask: np.ndarray) -> np.ndarray:
    diff = np.abs(src_arr[..., :3].astype(np.int16) - base_arr[..., :3].astype(np.int16)).max(axis=2)
    rgb = src_arr[..., :3].astype(np.int16)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    maxc = rgb.max(axis=2)
    minc = rgb.min(axis=2)
    sat = (maxc - minc) / np.maximum(maxc, 1)

    colorful = (
        ((r > 130) & (r - g > 22) & (r - b > 18))
        | ((g > 105) & (g - b > 8) & (sat > 0.15))
        | ((b > 120) & (b - r > 2) & (sat > 0.13))
        | ((r > 105) & (b > 105) & (g < 150) & (sat > 0.12))
    )
    white_icing = (maxc > 178) & (sat < 0.28) & (diff > 16)
    candy_shadow = (diff > 24) & (sat > 0.05)
    alpha = src_mask & (colorful | white_icing | candy_shadow)
    alpha = ndi.binary_opening(alpha, iterations=1)
    alpha = ndi.binary_dilation(alpha, iterations=2)
    alpha = ndi.binary_fill_holes(alpha)
    return alpha


def paste_transferred_layer(
    out: Image.Image,
    base: Image.Image,
    labels: np.ndarray,
    inner: np.ndarray,
    src_component: int,
    dst_component: int,
    *,
    flip: bool,
    y_scale: float = 0.98,
    x_scale: float = 0.92,
) -> np.ndarray:
    base_arr = np.array(base)
    out_arr = np.array(out)
    src_mask = (labels == src_component) & inner
    dst_mask = (labels == dst_component) & inner
    sx0, sy0, sx1, sy1 = bbox(src_mask, pad=4)
    dx0, dy0, dx1, dy1 = bbox(dst_mask, pad=2)

    src_alpha_full = extract_decoration_layer(base_arr, out_arr, src_mask)
    layer = out.crop((sx0, sy0, sx1, sy1)).convert("RGBA")
    alpha_crop = Image.fromarray((src_alpha_full[sy0:sy1, sx0:sx1] * 255).astype(np.uint8), "L")
    if flip:
        layer = layer.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        alpha_crop = alpha_crop.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    dst_w = dx1 - dx0
    dst_h = dy1 - dy0
    new_w = max(1, int(dst_w * x_scale))
    new_h = max(1, int(dst_h * y_scale))
    layer = layer.resize((new_w, new_h), Image.Resampling.LANCZOS)
    alpha_crop = alpha_crop.resize((new_w, new_h), Image.Resampling.LANCZOS)
    alpha_crop = alpha_crop.filter(ImageFilter.GaussianBlur(0.55))

    px = dx0 + (dst_w - new_w) // 2
    py = dy0 + (dst_h - new_h) // 2
    canvas = Image.new("RGBA", out.size, (0, 0, 0, 0))
    mask_canvas = Image.new("L", out.size, 0)
    canvas.alpha_composite(layer, (px, py))
    mask_canvas.paste(alpha_crop, (px, py))

    dst_clip = Image.fromarray((dst_mask * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(0.25))
    clipped = np.minimum(np.array(mask_canvas), np.array(dst_clip)).astype(np.uint8)
    out.paste(canvas, (0, 0), Image.fromarray(clipped, "L"))
    return clipped > 0


def main() -> int:
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    base = rgba(BASE)
    labels, inner = component_maps(base)
    for index, path in enumerate(OUTPUTS, start=1):
        out = rgba(path)
        left_mask_a = paste_transferred_layer(
            out,
            base,
            labels,
            inner,
            RIGHT_A,
            LEFT_A,
            flip=True,
            y_scale=0.98,
            x_scale=0.94,
        )
        left_mask_b = paste_transferred_layer(
            out,
            base,
            labels,
            inner,
            RIGHT_B,
            LEFT_B,
            flip=False,
            y_scale=0.98,
            x_scale=0.94,
        )
        arr = np.array(out)
        arr[..., 3] = np.array(base.getchannel("A"))
        final = Image.fromarray(arr, "RGBA")
        final.save(path)
        final.save(Path("tasks/festive-edge-v4-peppermint-overlay/outputs") / path.name)
        debug = Image.fromarray(((left_mask_a | left_mask_b) * 255).astype(np.uint8), "L")
        debug.save(ANALYSIS / f"left-strip-decoration-transfer-mask-option-{index}.png")
        print(f"updated {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
