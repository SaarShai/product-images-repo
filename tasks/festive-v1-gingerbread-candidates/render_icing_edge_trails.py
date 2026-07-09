#!/usr/bin/env python3
"""Cookie fill inside cutouts + white icing trails stroked on exact cutout contours."""
from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "tasks" / "festive-v1-gingerbread-candidates"
GEOM = TASK / "geometry" / "ab2-cutouts.json"
MASK_PATH = TASK / "geometry" / "combined-decoration-mask.png"
OPT_A = TASK / "outputs" / "round2-options" / "opt-a-royal-icing-cookie-trim-artwork.png"
OUT = TASK / "outputs" / "icing-edge-trails"
PROD = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/new cutting files/NEW Festive/Images/candidates"
)
LOCAL_IMG = TASK / "Images" / "candidates"
W, H = 1400, 1899
PAPER = (252, 249, 240, 255)
COOKIE_TARGET = np.array([227.0, 168.0, 101.0], dtype=np.float32)

VARIANTS = [
    ("edge-v1-smooth-rope", "V1. Smooth Icing Rope", "rope"),
    ("edge-v2-scallop-edge", "V2. Scalloped Edge Icing", "scallop"),
    ("edge-v3-soft-watercolor", "V3. Soft Watercolor Icing", "wash"),
]


def paper(size: tuple[int, int], seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    arr = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3] = PAPER
    arr[:, :, :3] = np.clip(arr[:, :, :3] + rng.normal(0, 3, (size[1], size[0], 1)), 0, 255)
    return Image.fromarray(arr.astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.2)).convert("RGBA")


def label_font(size: int = 22) -> ImageFont.ImageFont:
    for path in ["/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def load_polygons() -> list[list[tuple[float, float]]]:
    data = json.loads(GEOM.read_text())
    left, top, right, bottom = data["crop_rect"]
    scale = W / (right - left)

    def tx(pt):
        x, y = pt
        return (x - left) * scale, (top - y) * scale

    def cubic(p0, p1, p2, p3, t):
        u = 1 - t
        return (
            u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
            u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1],
        )

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
            steps = max(8, min(48, int(span / 10)))
            for s in range(steps):
                poly.append(cubic(p0, p1, p2, p3, s / steps))
        if len(poly) >= 3:
            polys.append(poly)
    return polys


def build_cookie_fill(mask: np.ndarray) -> Image.Image:
    """Warm golden gingerbread fill from opt-a; scrub candy beads only."""
    art = np.array(Image.open(OPT_A).convert("RGBA"))
    rgb = art[:, :, :3].astype(np.float32)
    alpha = art[:, :, 3] > 200
    lum = rgb.mean(axis=2)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    chroma = rgb.max(axis=2) - rgb.min(axis=2)
    candy_red = (r > 175) & (r - g > 45) & (chroma > 55) & (lum > 90)
    candy_green = (g > r + 18) & (g > b + 10) & (chroma > 40) & (lum < 180)
    warm_cookie = (r > g - 5) & (g > b - 5) & (r > b + 15)
    cookie_px = mask & alpha & (lum < 205) & (lum > 60) & warm_cookie & ~candy_red & ~candy_green
    samples = rgb[cookie_px]
    if len(samples) < 1000:
        raise SystemExit(f"too few cookie samples: {len(samples)}")

    rng = np.random.default_rng(42)
    mean = samples.mean(axis=0)
    if mean[0] < 200 or mean[0] - mean[2] < 60:
        mean = 0.35 * mean + 0.65 * COOKIE_TARGET
    std = np.maximum(samples.std(axis=0) * 0.85, 8.0)

    coarse = ndimage.gaussian_filter(rng.normal(0, 1, (H, W)), sigma=18)
    mid = ndimage.gaussian_filter(rng.normal(0, 1, (H, W)), sigma=6)
    fine = ndimage.gaussian_filter(rng.normal(0, 1, (H, W)), sigma=1.8)
    mottling = 0.55 * coarse + 0.30 * mid + 0.15 * fine
    mottling = (mottling - mottling.mean()) / (mottling.std() + 1e-6)

    yy, xx = np.mgrid[0:H, 0:W]
    warm_shift = 0.08 * np.sin(xx / 90.0) + 0.06 * np.cos(yy / 110.0)
    dist_in = ndimage.distance_transform_edt(mask)
    edge_dark = np.clip(1.0 - dist_in / 14.0, 0, 1) * 14

    ys, xs = np.where(cookie_px)
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    plate = art[y0:y1, x0:x1].copy().astype(np.float32)
    pl = plate[:, :, :3]
    pl_lum = pl.mean(axis=2)
    pl_chroma = pl.max(axis=2) - pl.min(axis=2)
    pl_r, pl_g, pl_b = pl[:, :, 0], pl[:, :, 1], pl[:, :, 2]
    pl_candy_red = (pl_r > 175) & (pl_r - pl_g > 45) & (pl_chroma > 55)
    pl_candy_green = (pl_g > pl_r + 18) & (pl_g > pl_b + 10) & (pl_chroma > 40)
    pl_keep = (
        (plate[:, :, 3] > 200)
        & (pl_lum < 205)
        & (pl_lum > 60)
        & (pl_r > pl_g - 5)
        & (pl_g > pl_b - 5)
        & (pl_r > pl_b + 15)
        & ~pl_candy_red
        & ~pl_candy_green
    )
    for c in range(3):
        ch = pl[:, :, c].copy()
        ch[~pl_keep] = mean[c]
        plate[:, :, c] = ndimage.gaussian_filter(ch, sigma=1.2)
    plate[:, :, 3] = 255
    plate_img = Image.fromarray(np.clip(plate, 0, 255).astype(np.uint8))

    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pw, ph = plate_img.size
    for ty in range(0, H, max(1, ph - 48)):
        for tx in range(0, W, max(1, pw - 48)):
            canvas.alpha_composite(plate_img, (tx, ty))
    tiled = np.array(canvas).astype(np.float32)

    out = np.zeros((H, W, 4), dtype=np.float32)
    for c in range(3):
        synth = mean[c] + mottling * std[c] * 1.05 + warm_shift * (10 if c < 2 else -8) - edge_dark * (
            0.55 if c == 0 else 1.0
        )
        out[:, :, c] = 0.70 * tiled[:, :, c] + 0.30 * synth
    out[:, :, :3] = np.clip(out[:, :, :3], 0, 255)
    out[:, :, 3] = np.where(mask, 255, 0)
    img = Image.fromarray(out.astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.45))
    arr = np.array(img.convert("RGBA"))
    arr[:, :, 3] = np.where(mask, 255, 0).astype(np.uint8)
    return Image.fromarray(arr)


def densify(poly: list[tuple[float, float]], spacing: float = 2.0) -> list[tuple[float, float]]:
    if len(poly) < 2:
        return list(poly)
    out = [poly[0]]
    for i in range(1, len(poly)):
        x0, y0 = out[-1]
        x1, y1 = poly[i]
        dist = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(dist / spacing))
        for s in range(1, n + 1):
            t = s / n
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    return out


def stroke_rope(polys: list[list[tuple[float, float]]], width: int = 12) -> Image.Image:
    hi = 2
    layer = Image.new("RGBA", (W * hi, H * hi), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    shadow = Image.new("RGBA", (W * hi, H * hi), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow, "RGBA")
    for poly in polys:
        pts = [(x * hi, y * hi) for x, y in poly + [poly[0]]]
        sdraw.line(pts, fill=(90, 90, 88, 50), width=width * hi + 3)
        draw.line(pts, fill=(255, 252, 242, 245), width=width * hi)
        draw.line(pts, fill=(255, 255, 252, 180), width=max(2, width * hi // 3))
    shadow = shadow.filter(ImageFilter.GaussianBlur(1.4 * hi))
    layer = layer.filter(ImageFilter.GaussianBlur(0.5 * hi))
    out = Image.new("RGBA", (W * hi, H * hi), (0, 0, 0, 0))
    out.alpha_composite(shadow)
    out.alpha_composite(layer)
    return out.resize((W, H), Image.Resampling.LANCZOS)


def stroke_scallop(
    polys: list[list[tuple[float, float]]], bead_r: float = 6.4, spacing: float = 10.5
) -> Image.Image:
    hi = 2
    base = stroke_rope(polys, width=7)
    layer = Image.new("RGBA", (W * hi, H * hi), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    rng = np.random.default_rng(7)
    for poly in polys:
        dense = densify(poly + [poly[0]], spacing=1.5)
        acc = 0.0
        prev = dense[0]
        for pt in dense[1:]:
            acc += math.hypot(pt[0] - prev[0], pt[1] - prev[1])
            if acc >= spacing:
                acc = 0.0
                r = (bead_r + float(rng.uniform(-0.5, 0.8))) * hi
                x, y = pt[0] * hi, pt[1] * hi
                draw.ellipse([x - r, y - r, x + r, y + r], fill=(255, 253, 245, 245))
                draw.ellipse(
                    [x - r * 0.35, y - r * 0.55, x + r * 0.2, y - r * 0.05],
                    fill=(255, 255, 255, 170),
                )
            prev = pt
    layer = layer.filter(ImageFilter.GaussianBlur(0.45 * hi)).resize((W, H), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.alpha_composite(base)
    out.alpha_composite(layer)
    return out


def stroke_wash(polys: list[list[tuple[float, float]]], width: int = 14) -> Image.Image:
    hi = 2
    layer = Image.new("RGBA", (W * hi, H * hi), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    for poly in polys:
        pts = [(x * hi, y * hi) for x, y in poly + [poly[0]]]
        draw.line(pts, fill=(255, 252, 245, 200), width=width * hi)
        draw.line(pts, fill=(255, 255, 250, 160), width=max(4, (width * hi * 2) // 3))
    bloom = layer.filter(ImageFilter.GaussianBlur(1.8 * hi))
    core = layer.filter(ImageFilter.GaussianBlur(0.7 * hi))
    out = Image.new("RGBA", (W * hi, H * hi), (0, 0, 0, 0))
    out.alpha_composite(bloom)
    out.alpha_composite(core)
    arr = np.array(out.resize((W, H), Image.Resampling.LANCZOS)).astype(np.float32)
    rng = np.random.default_rng(11)
    grain = ndimage.gaussian_filter(rng.normal(0, 1, (H, W)), 1.2)
    arr[:, :, 3] = np.clip(arr[:, :, 3] * (0.95 + 0.10 * grain), 0, 240)
    return Image.fromarray(arr.astype(np.uint8))


def make_icing(kind: str, polys: list[list[tuple[float, float]]]) -> Image.Image:
    if kind == "rope":
        return stroke_rope(polys, width=12)
    if kind == "scallop":
        return stroke_scallop(polys, bead_r=6.4, spacing=10.5)
    return stroke_wash(polys, width=14)


def metrics(art: Image.Image, mask: np.ndarray) -> dict:
    arr = np.array(art)
    rgb = arr[:, :, :3].astype(np.float32)
    a = arr[:, :, 3] > 40
    lum = rgb.mean(axis=2)
    icing = a & (lum > 220)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    cookie = a & (lum < 210) & (lum > 50) & (r > g + 8) & (g > b + 8)
    return {
        "icing_inside": int((icing & mask).sum()),
        "icing_outside": int((icing & ~mask).sum()),
        "cookie_outside": int((cookie & ~mask).sum()),
        "cookie_inside": int((cookie & mask).sum()),
    }


def make_board(items: list[dict]) -> Path:
    thumb_w, thumb_h, label_h, gutter = 430, 640, 48, 22
    cols = 3
    board = Image.new(
        "RGBA",
        (cols * thumb_w + (cols + 1) * gutter, thumb_h + label_h + 2 * gutter),
        (250, 248, 240, 255),
    )
    draw = ImageDraw.Draw(board, "RGBA")
    font = label_font(20)
    for idx, item in enumerate(items):
        img = Image.open(item["preview"]).convert("RGBA")
        img.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = gutter + idx * (thumb_w + gutter)
        y = gutter
        draw.text((x, y), item["title"], fill=(62, 48, 38, 255), font=font)
        board.alpha_composite(img, (x + (thumb_w - img.width) // 2, y + label_h))
    path = OUT / "festive-v1-icing-edge-trails-board.png"
    board.save(path)
    return path


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    LOCAL_IMG.mkdir(parents=True, exist_ok=True)
    PROD.mkdir(parents=True, exist_ok=True)

    mask_img = Image.open(MASK_PATH).convert("L").resize((W, H), Image.Resampling.NEAREST)
    mask = np.array(mask_img) > 128
    polys = load_polygons()
    print(f"loaded {len(polys)} cutout polygons")

    cookie = build_cookie_fill(mask)
    cookie_path = OUT / "cookie-fill-base.png"
    cookie.save(cookie_path)
    cookie_rgb = np.array(cookie)[:, :, :3][mask].mean(axis=0)
    print(f"cookie mean RGB {cookie_rgb.tolist()}")
    (OUT / "NOTES-cookie-fill.md").write_text(
        "# Cookie fill\n\nMethod: tiled warm non-candy patches from opt-a "
        "blended with watercolor mottling; masked to cutouts only.\n\n"
        f"Mean RGB inside mask: [{cookie_rgb[0]:.1f}, {cookie_rgb[1]:.1f}, {cookie_rgb[2]:.1f}]\n"
        "Icing trails: stroked on exact ab2-cutouts.json bezier-sampled contours "
        "(width straddles edge inward+outward).\n"
    )

    manifest = []
    all_metrics = {}
    for i, (slug, title, kind) in enumerate(VARIANTS):
        icing = make_icing(kind, polys)
        art = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        art.alpha_composite(cookie)
        art.alpha_composite(icing)
        art_path = OUT / f"{slug}-artwork.png"
        art.save(art_path)

        preview = paper((W, H), 42000 + i)
        preview.alpha_composite(art)
        preview_path = OUT / f"{slug}-preview.png"
        preview.save(preview_path)

        m = metrics(art, mask)
        all_metrics[slug] = m
        for src in (art_path, preview_path):
            shutil.copy2(src, PROD / src.name)
            shutil.copy2(src, LOCAL_IMG / src.name)
        manifest.append(
            {
                "title": title,
                "slug": slug,
                "kind": kind,
                "artwork": str(art_path),
                "preview": str(preview_path),
                "production_preview": str(PROD / preview_path.name),
                "metrics": m,
            }
        )
        print(json.dumps({"slug": slug, **m}))

    board = make_board(manifest)
    shutil.copy2(board, PROD / board.name)
    shutil.copy2(board, LOCAL_IMG / board.name)
    shutil.copy2(cookie_path, PROD / cookie_path.name)

    color_ok = cookie_rgb[0] > 200 and (cookie_rgb[0] - cookie_rgb[2]) > 80
    report = {
        "cookie_fill": str(cookie_path),
        "cookie_mean_rgb": cookie_rgb.tolist(),
        "candidates": manifest,
        "board": str(board),
        "metrics": all_metrics,
        "pass": color_ok
        and all(
            m["cookie_outside"] == 0 and m["icing_inside"] > 0 and m["icing_outside"] > 0
            for m in all_metrics.values()
        ),
    }
    (OUT / "icing-edge-trails-report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"pass": report["pass"], "cookie_mean_rgb": report["cookie_mean_rgb"], "metrics": all_metrics}, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
