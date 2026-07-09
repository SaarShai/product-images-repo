#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage


ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "tasks" / "festive-v1-gingerbread-candidates"
GEOM = TASK / "geometry" / "ab5-cutouts.json"
OUT = TASK / "outputs" / "ab5-cutout-options"
LOCAL = TASK / "Images" / "candidates"
PROD = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/festive/images/Images/candidates"
)

W = 1600
PAPER = (252, 249, 240, 255)


OPTIONS = [
    ("ab5-option-a-peppermint-holly", "A. Peppermint Holly Ribbons", "peppermint_holly"),
    ("ab5-option-b-gumdrop-pearls", "B. Gumdrop Pearls", "gumdrop_pearls"),
    ("ab5-option-c-snow-icing-scrolls", "C. Snow Icing Scrolls", "snow_scrolls"),
    ("ab5-option-d-candy-brick-garlands", "D. Candy Brick Garlands", "brick_garlands"),
]


def font(size: int) -> ImageFont.ImageFont:
    for candidate in ["/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"]:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def cubic(p0, p1, p2, p3, t):
    u = 1.0 - t
    return (
        u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
        u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1],
    )


def load_polys() -> tuple[list[list[tuple[float, float]]], tuple[float, float, float, float], int]:
    data = json.loads(GEOM.read_text())
    bounds = [item["bounds"] for item in data["paths"]]
    left = min(b[0] for b in bounds) - 185
    top = max(b[1] for b in bounds) + 185
    right = max(b[2] for b in bounds) + 185
    bottom = min(b[3] for b in bounds) - 185
    scale = W / (right - left)
    h = int(round((top - bottom) * scale))

    def tx(pt):
        x, y = pt
        return (x - left) * scale, (top - y) * scale

    polys = []
    for item in data["paths"]:
        pts = item["points"]
        poly = []
        for i, cur in enumerate(pts):
            nxt = pts[(i + 1) % len(pts)]
            p0 = tx(cur["anchor"])
            p1 = tx(cur["right"])
            p2 = tx(nxt["left"])
            p3 = tx(nxt["anchor"])
            span = max(abs(p3[0] - p0[0]), abs(p3[1] - p0[1]))
            steps = max(10, min(52, int(span / 8)))
            for s in range(steps):
                poly.append(cubic(p0, p1, p2, p3, s / steps))
        polys.append(poly)
    return polys, (left, top, right, bottom), h


def masks_from_polys(polys: list[list[tuple[float, float]]], h: int) -> tuple[list[np.ndarray], np.ndarray]:
    masks = []
    combined = np.zeros((h, W), dtype=bool)
    for poly in polys:
        m = Image.new("L", (W, h), 0)
        ImageDraw.Draw(m).polygon(poly, fill=255)
        arr = np.array(m) > 128
        masks.append(arr)
        combined |= arr
    return masks, combined


def paper(size: tuple[int, int], seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    arr = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3] = PAPER
    arr[:, :, :3] = np.clip(arr[:, :, :3] + rng.normal(0, 2.8, (size[1], size[0], 1)), 0, 255)
    return Image.fromarray(arr, "RGBA").filter(ImageFilter.GaussianBlur(0.2))


def gingerbread_fill(masks: list[np.ndarray], h: int) -> Image.Image:
    rng = np.random.default_rng(505)
    base = np.zeros((h, W, 4), dtype=np.float32)
    yy, xx = np.mgrid[0:h, 0:W]
    coarse = ndimage.gaussian_filter(rng.normal(0, 1, (h, W)), 18)
    mid = ndimage.gaussian_filter(rng.normal(0, 1, (h, W)), 6)
    fine = ndimage.gaussian_filter(rng.normal(0, 1, (h, W)), 1.4)
    mottling = 0.50 * coarse + 0.32 * mid + 0.18 * fine
    mottling = (mottling - mottling.mean()) / (mottling.std() + 1e-6)
    warm = 0.10 * np.sin(xx / 88.0) + 0.06 * np.cos(yy / 130.0)
    color = np.array([224, 160, 90], dtype=np.float32)
    for c, scale in enumerate([18, 13, 8]):
        base[:, :, c] = color[c] + mottling * scale + warm * (14 if c < 2 else -6)
    combined = np.zeros((h, W), dtype=bool)
    for m in masks:
        combined |= m
        dist = ndimage.distance_transform_edt(m)
        edge_dark = np.clip(1.0 - dist / 18.0, 0, 1) * 20
        base[:, :, 0] -= edge_dark * 0.45
        base[:, :, 1] -= edge_dark * 0.75
        base[:, :, 2] -= edge_dark * 1.05
    base[:, :, :3] = np.clip(base[:, :, :3], 0, 255)
    base[:, :, 3] = np.where(combined, 255, 0)
    return Image.fromarray(base.astype(np.uint8), "RGBA").filter(ImageFilter.GaussianBlur(0.35))


def draw_icing(polys: list[list[tuple[float, float]]], combined: np.ndarray, h: int) -> Image.Image:
    hi = 2
    layer = Image.new("RGBA", (W * hi, h * hi), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    for poly in polys:
        pts = [(x * hi, y * hi) for x, y in poly + [poly[0]]]
        draw.line(pts, fill=(116, 89, 64, 80), width=24 * hi, joint="curve")
        draw.line(pts, fill=(255, 252, 242, 255), width=18 * hi, joint="curve")
        draw.line(pts, fill=(245, 232, 210, 225), width=12 * hi, joint="curve")
        draw.line(pts, fill=(255, 255, 250, 190), width=5 * hi, joint="curve")
    layer = layer.filter(ImageFilter.GaussianBlur(0.55 * hi)).resize((W, h), Image.Resampling.LANCZOS)
    arr = np.array(layer).astype(np.float32)

    dist = ndimage.distance_transform_edt(combined)
    outer_shadow = np.clip((30.0 - dist) / 12.0, 0, 1) * combined
    icing_body = np.clip((22.0 - dist) / 10.0, 0, 1) * combined
    icing_core = np.clip((12.0 - dist) / 7.0, 0, 1) * combined
    highlight = np.clip(1.0 - np.abs(dist - 8.0) / 5.5, 0, 1) * combined

    ring = np.zeros((h, W, 4), dtype=np.float32)
    ring[:, :, 0] = 124
    ring[:, :, 1] = 88
    ring[:, :, 2] = 54
    ring[:, :, 3] = outer_shadow * 72

    white = np.zeros((h, W, 4), dtype=np.float32)
    white[:, :, 0] = 255
    white[:, :, 1] = 250
    white[:, :, 2] = 236
    white[:, :, 3] = icing_body * 238

    cream = np.zeros((h, W, 4), dtype=np.float32)
    cream[:, :, 0] = 238
    cream[:, :, 1] = 219
    cream[:, :, 2] = 193
    cream[:, :, 3] = icing_core * 120

    gleam = np.zeros((h, W, 4), dtype=np.float32)
    gleam[:, :, 0] = 255
    gleam[:, :, 1] = 255
    gleam[:, :, 2] = 250
    gleam[:, :, 3] = highlight * 115

    def over(dst: np.ndarray, src: np.ndarray) -> np.ndarray:
        sa = src[:, :, 3:4] / 255.0
        da = dst[:, :, 3:4] / 255.0
        out_a = sa + da * (1 - sa)
        out_rgb = (src[:, :, :3] * sa + dst[:, :, :3] * da * (1 - sa)) / np.maximum(out_a, 1e-6)
        out = np.zeros_like(dst)
        out[:, :, :3] = out_rgb
        out[:, :, 3:4] = out_a * 255
        return out

    for src in (ring, white, cream, gleam, arr):
        ring = over(ring, src) if src is not ring else ring
    ring[:, :, 3] = np.minimum(ring[:, :, 3], np.where(combined, 255, 0).astype(np.float32))
    return Image.fromarray(np.clip(ring, 0, 255).astype(np.uint8), "RGBA")


def bbox(mask: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.where(mask)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def draw_ball(draw: ImageDraw.ImageDraw, x: float, y: float, r: float, color: tuple[int, int, int], seed: int) -> None:
    rng = np.random.default_rng(seed)
    shadow = (78, 53, 38, 45)
    draw.ellipse([x - r + 2, y - r + 3, x + r + 2, y + r + 3], fill=shadow)
    draw.ellipse([x - r, y - r, x + r, y + r], fill=(*color, 235), outline=(120, 75, 52, 90), width=max(1, int(r / 5)))
    draw.ellipse([x - r * 0.45, y - r * 0.58, x + r * 0.10, y - r * 0.12], fill=(255, 255, 255, 120))
    for _ in range(max(6, int(r))):
        px = x + rng.uniform(-0.65, 0.65) * r
        py = y + rng.uniform(-0.65, 0.65) * r
        if (px - x) ** 2 + (py - y) ** 2 < (0.72 * r) ** 2:
            draw.ellipse([px - 1.4, py - 1.4, px + 1.4, py + 1.4], fill=(255, 252, 238, 90))


def draw_holly(draw: ImageDraw.ImageDraw, x: float, y: float, s: float, angle: float = 0.0) -> None:
    for sign in [-1, 1]:
        pts = []
        for i in range(9):
            t = (i / 8.0 - 0.5) * math.pi
            rr = s * (0.75 + 0.20 * math.sin(i * 2.7))
            px = sign * math.cos(t) * rr
            py = math.sin(t) * s * 0.45
            ca, sa = math.cos(angle), math.sin(angle)
            pts.append((x + px * ca - py * sa, y + px * sa + py * ca))
        draw.polygon(pts, fill=(74, 122, 82, 205), outline=(43, 82, 55, 110))
    for dx, dy in [(-0.25, 0.08), (0.18, -0.08), (0.34, 0.18)]:
        draw_ball(draw, x + dx * s, y + dy * s, s * 0.17, (190, 49, 39), int((x + y + s) * 10) % 99999)


def draw_peppermint(draw: ImageDraw.ImageDraw, x: float, y: float, r: float) -> None:
    draw.ellipse([x - r, y - r, x + r, y + r], fill=(248, 246, 236, 245), outline=(163, 56, 43, 120), width=max(2, int(r / 8)))
    for i in range(6):
        a0 = i * 60 - 12
        a1 = i * 60 + 18
        draw.pieslice([x - r * 0.88, y - r * 0.88, x + r * 0.88, y + r * 0.88], a0, a1, fill=(200, 45, 38, 220))
    draw.ellipse([x - r * 0.18, y - r * 0.18, x + r * 0.18, y + r * 0.18], fill=(255, 250, 240, 240))


def draw_icing_line(draw: ImageDraw.ImageDraw, pts: list[tuple[float, float]], width: int = 7, alpha: int = 215) -> None:
    draw.line(pts, fill=(255, 252, 239, alpha), width=width, joint="curve")
    draw.line(pts, fill=(238, 218, 190, min(alpha, 120)), width=max(1, width // 3), joint="curve")


def decorate_option(base: Image.Image, masks: list[np.ndarray], kind: str) -> Image.Image:
    art = base.copy()
    deco = Image.new("RGBA", art.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(deco, "RGBA")
    colors = [(196, 52, 42), (78, 127, 85), (222, 172, 58), (164, 191, 205), (238, 238, 222)]
    for idx, mask in enumerate(masks):
        x0, y0, x1, y1 = bbox(mask)
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        ww = x1 - x0
        hh = y1 - y0
        is_top = idx < 2
        rng = np.random.default_rng(1000 + idx * 31 + len(kind))

        if kind == "peppermint_holly":
            if is_top:
                for k in range(7):
                    t = (k + 1) / 8
                    x = x0 + ww * (0.16 + 0.68 * t)
                    y = y0 + hh * (0.58 - 0.22 * math.sin(t * math.pi))
                    draw_ball(draw, x, y, min(ww, hh) * rng.uniform(0.035, 0.055), colors[k % 4], idx * 77 + k)
                draw_holly(draw, x0 + ww * 0.32, y0 + hh * 0.32, min(ww, hh) * 0.17, -0.5)
                draw_holly(draw, x0 + ww * 0.68, y0 + hh * 0.34, min(ww, hh) * 0.17, 0.55)
                draw_peppermint(draw, cx, y0 + hh * 0.70, min(ww, hh) * 0.055)
            else:
                for k in range(6):
                    y = y0 + hh * (0.12 + k * 0.15)
                    x = cx + math.sin(k * 1.25 + idx) * ww * 0.13
                    draw_holly(draw, x, y, ww * 0.17, 0.25 * (-1) ** k)
                    draw_ball(draw, x + ww * 0.08, y + ww * 0.08, ww * 0.055, colors[k % 4], idx * 100 + k)
                pts = [(cx + math.sin(t * 0.045 + idx) * ww * 0.23, y0 + t) for t in range(20, hh - 20, 22)]
                draw_icing_line(draw, pts, width=max(5, int(ww * 0.035)), alpha=190)

        elif kind == "gumdrop_pearls":
            count = 14 if is_top else 16
            for k in range(count):
                y = y0 + hh * rng.uniform(0.16, 0.84)
                x = x0 + ww * rng.uniform(0.22, 0.78)
                r = min(ww, hh) * (0.032 if is_top else 0.045) * rng.uniform(0.75, 1.25)
                draw_ball(draw, x, y, r, colors[(k + idx) % len(colors)], idx * 88 + k)
            for k in range(18 if is_top else 22):
                y = y0 + hh * (k + 0.5) / (18 if is_top else 22)
                x = cx + math.sin(k * 0.9 + idx) * ww * 0.24
                draw.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(255, 252, 235, 210))

        elif kind == "snow_scrolls":
            for k in range(3 if is_top else 5):
                y = y0 + hh * (0.20 + k * (0.22 if is_top else 0.16))
                pts = []
                for s in range(80):
                    t = s / 79
                    x = x0 + ww * (0.18 + 0.64 * t)
                    pts.append((x, y + math.sin(t * math.pi * 2.0 + k) * min(ww, hh) * 0.055))
                draw_icing_line(draw, pts, width=max(5, int(min(ww, hh) * 0.018)), alpha=215)
            for k in range(9 if is_top else 12):
                x = x0 + ww * rng.uniform(0.22, 0.78)
                y = y0 + hh * rng.uniform(0.14, 0.86)
                r = min(ww, hh) * rng.uniform(0.010, 0.018)
                draw.ellipse([x - r, y - r, x + r, y + r], fill=(191, 216, 225, 160))
                draw.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(255, 255, 252, 220))
            if is_top:
                draw_peppermint(draw, cx, cy, min(ww, hh) * 0.045)

        elif kind == "brick_garlands":
            brick_h = max(18, int(hh * (0.055 if is_top else 0.030)))
            brick_w = max(38, int(ww * (0.18 if is_top else 0.42)))
            for row, y in enumerate(range(y0 + brick_h, y1 - brick_h, brick_h + 8)):
                offset = (brick_w // 2) if row % 2 else 0
                for x in range(x0 - offset, x1, brick_w + 8):
                    draw.rounded_rectangle(
                        [x, y, x + brick_w, y + brick_h],
                        radius=8,
                        fill=(205, 135, 68, 72),
                        outline=(153, 91, 47, 50),
                        width=2,
                    )
            if is_top:
                pts = [(x0 + ww * (0.16 + 0.68 * t / 80), y0 + hh * (0.25 + 0.12 * math.sin(t / 80 * math.pi))) for t in range(81)]
                draw_icing_line(draw, pts, width=8, alpha=210)
                for k in range(6):
                    draw_ball(draw, x0 + ww * (0.18 + k * 0.12), y0 + hh * (0.40 + 0.08 * math.sin(k)), min(ww, hh) * 0.043, colors[k % 4], idx * 55 + k)
            else:
                for k in range(7):
                    y = y0 + hh * (0.10 + k * 0.13)
                    x = cx + math.sin(k * 0.8 + idx) * ww * 0.18
                    draw_ball(draw, x, y, ww * 0.052, colors[(k + 1) % 4], idx * 66 + k)
                pts = [(cx + math.sin(t * 0.037 + idx) * ww * 0.24, y0 + t) for t in range(18, hh - 18, 18)]
                draw_icing_line(draw, pts, width=6, alpha=185)

    combined = np.zeros(art.size[::-1], dtype=bool)
    for m in masks:
        combined |= ndimage.binary_erosion(m, iterations=9)
    alpha_clip = Image.fromarray(np.where(combined, 255, 0).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(0.8))
    deco.putalpha(Image.fromarray(np.minimum(np.array(deco.getchannel("A")), np.array(alpha_clip)).astype(np.uint8), "L"))
    art.alpha_composite(deco)
    return art


def transparent_clip(img: Image.Image, combined: np.ndarray) -> Image.Image:
    arr = np.array(img.convert("RGBA"))
    arr[:, :, 3] = np.where(combined, arr[:, :, 3], 0).astype(np.uint8)
    arr[arr[:, :, 3] == 0, :3] = 0
    return Image.fromarray(arr, "RGBA")


def make_preview(art: Image.Image, seed: int) -> Image.Image:
    bg = paper(art.size, seed)
    bg.alpha_composite(art)
    return bg


def make_board(items: list[dict], h: int) -> Path:
    thumb_w, thumb_h, label_h, gutter = 370, 450, 44, 24
    cols = 2
    rows = math.ceil(len(items) / cols)
    board = Image.new("RGBA", (cols * thumb_w + (cols + 1) * gutter, rows * (thumb_h + label_h) + (rows + 1) * gutter), (250, 247, 239, 255))
    draw = ImageDraw.Draw(board)
    fnt = font(20)
    for idx, item in enumerate(items):
        im = Image.open(item["preview"]).convert("RGBA")
        im.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = gutter + (idx % cols) * (thumb_w + gutter)
        y = gutter + (idx // cols) * (thumb_h + label_h + gutter)
        draw.text((x, y), item["title"], fill=(64, 47, 36, 255), font=fnt)
        board.alpha_composite(im, (x + (thumb_w - im.width) // 2, y + label_h))
    out = OUT / "festive-ab5-cutout-options-board.png"
    board.save(out)
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    LOCAL.mkdir(parents=True, exist_ok=True)
    PROD.mkdir(parents=True, exist_ok=True)
    polys, crop, h = load_polys()
    masks, combined = masks_from_polys(polys, h)
    Image.fromarray(np.where(combined, 255, 0).astype(np.uint8), "L").save(OUT / "ab5-combined-mask.png")

    base = gingerbread_fill(masks, h)
    icing = draw_icing(polys, combined, h)
    base.alpha_composite(icing)
    base = transparent_clip(base, combined)
    base.save(OUT / "ab5-base-gingerbread-icing.png")

    items = []
    metrics = {}
    for i, (slug, title, kind) in enumerate(OPTIONS):
        art = decorate_option(base, masks, kind)
        art = transparent_clip(art, combined)
        art_path = OUT / f"{slug}-artwork.png"
        preview_path = OUT / f"{slug}-preview.png"
        art.save(art_path)
        make_preview(art, 8800 + i).save(preview_path)

        alpha = np.array(art.getchannel("A")) > 0
        outside = int(np.count_nonzero(alpha & ~combined))
        inside = int(np.count_nonzero(alpha & combined))
        metrics[slug] = {"opaque_outside_mask": outside, "opaque_inside_mask": inside}
        for src in (art_path, preview_path):
            shutil.copy2(src, PROD / src.name)
            shutil.copy2(src, LOCAL / src.name)
        items.append({"slug": slug, "title": title, "artwork": str(art_path), "preview": str(preview_path), "metrics": metrics[slug]})

    board = make_board(items, h)
    shutil.copy2(board, PROD / board.name)
    shutil.copy2(board, LOCAL / board.name)
    report = {
        "pass": all(m["opaque_outside_mask"] == 0 for m in metrics.values()),
        "geometry": str(GEOM),
        "crop_rect": list(crop),
        "canvas_size": [W, h],
        "count_cutouts": len(masks),
        "same_base": str(OUT / "ab5-base-gingerbread-icing.png"),
        "candidates": items,
        "board": str(board),
        "metrics": metrics,
    }
    (OUT / "ab5-cutout-options-report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0 if report["pass"] and len(masks) == 6 else 1


if __name__ == "__main__":
    raise SystemExit(main())
