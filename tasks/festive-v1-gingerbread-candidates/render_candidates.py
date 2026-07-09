#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import random
import shutil
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "tasks" / "festive-v1-gingerbread-candidates"
GEOM = TASK / "geometry" / "ab2-cutouts.json"
OUT = TASK / "outputs" / "generated"
REV = TASK / "outputs" / "reviews"
PROD = Path("/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/new cutting files/NEW Festive/Images/candidates")

W = 1400

PALE = (251, 248, 238, 255)

VARIANTS = [
    {
        "slug": "v1-cocoa-glaze-village",
        "title": "Cocoa Glaze Village",
        "palette": {
            "body": (143, 83, 45, 210),
            "dark": (83, 45, 28, 180),
            "icing": (255, 250, 233, 230),
            "accent": (193, 55, 61, 210),
            "accent2": (80, 132, 78, 190),
            "cool": (185, 222, 232, 125),
            "glow": (250, 188, 86, 210),
        },
        "mode": "village",
    },
    {
        "slug": "v2-holly-berry-bakery",
        "title": "Holly-Berry Bakery",
        "palette": {
            "body": (133, 78, 43, 205),
            "dark": (32, 94, 64, 190),
            "icing": (255, 252, 235, 235),
            "accent": (210, 38, 46, 230),
            "accent2": (22, 116, 73, 210),
            "cool": (184, 218, 224, 115),
            "glow": (246, 196, 103, 190),
        },
        "mode": "holly",
    },
    {
        "slug": "v3-powdered-sugar-frost",
        "title": "Powdered Sugar Frost",
        "palette": {
            "body": (155, 91, 54, 150),
            "dark": (90, 130, 150, 135),
            "icing": (255, 255, 248, 245),
            "accent": (155, 205, 220, 165),
            "accent2": (204, 69, 74, 120),
            "cool": (164, 216, 235, 150),
            "glow": (244, 212, 141, 145),
        },
        "mode": "frost",
    },
    {
        "slug": "v4-painted-ornament-candy-shop",
        "title": "Painted Ornament Candy Shop",
        "palette": {
            "body": (140, 78, 46, 175),
            "dark": (50, 72, 145, 175),
            "icing": (252, 246, 225, 230),
            "accent": (209, 52, 63, 220),
            "accent2": (41, 148, 134, 210),
            "cool": (102, 120, 193, 150),
            "glow": (237, 171, 215, 175),
        },
        "mode": "ornament",
    },
    {
        "slug": "v5-peppermint-roofline",
        "title": "Peppermint Roofline",
        "palette": {
            "body": (139, 77, 42, 190),
            "dark": (104, 43, 48, 180),
            "icing": (255, 251, 236, 238),
            "accent": (220, 35, 45, 230),
            "accent2": (250, 250, 246, 230),
            "cool": (180, 218, 228, 120),
            "glow": (247, 199, 102, 180),
        },
        "mode": "peppermint",
    },
    {
        "slug": "v6-icing-garland-house",
        "title": "Icing Garland House",
        "palette": {
            "body": (151, 88, 47, 190),
            "dark": (48, 108, 76, 185),
            "icing": (255, 252, 237, 240),
            "accent": (196, 44, 65, 215),
            "accent2": (235, 145, 72, 180),
            "cool": (177, 217, 225, 110),
            "glow": (239, 203, 117, 185),
        },
        "mode": "garland",
    },
]


def load_geometry():
    data = json.loads(GEOM.read_text())
    left, top, right, bottom = data["crop_rect"]
    scale = W / (right - left)
    h = int(round((top - bottom) * scale))
    return data, (left, top, right, bottom), scale, h


def tx(pt, crop, scale):
    x, y = pt
    left, top, _, _ = crop
    return (x - left) * scale, (top - y) * scale


def cubic(p0, p1, p2, p3, t):
    u = 1 - t
    return (
        u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
        u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1],
    )


def sampled_polygon(item, crop, scale):
    pts = item["points"]
    poly = []
    for i, cur in enumerate(pts):
        nxt = pts[(i + 1) % len(pts)]
        p0 = tx(cur["anchor"], crop, scale)
        p1 = tx(cur["right"], crop, scale)
        p2 = tx(nxt["left"], crop, scale)
        p3 = tx(nxt["anchor"], crop, scale)
        span = max(abs(p3[0] - p0[0]), abs(p3[1] - p0[1]))
        steps = max(6, min(30, int(span / 18)))
        for s in range(steps):
            poly.append(cubic(p0, p1, p2, p3, s / steps))
    return poly


def masks(data, crop, scale, h):
    items = []
    for idx, p in enumerate(data["paths"]):
        hi = 3
        mask_hi = Image.new("L", (W * hi, h * hi), 0)
        poly = [(x * hi, y * hi) for x, y in sampled_polygon(p, crop, scale)]
        ImageDraw.Draw(mask_hi).polygon(poly, fill=255)
        mask = mask_hi.resize((W, h), Image.Resampling.LANCZOS)
        bbox = mask.getbbox()
        if not bbox:
            continue
        p = dict(p)
        p["idx"] = idx
        p["mask"] = mask
        p["bbox_px"] = bbox
        items.append(p)
    combined = Image.new("L", (W, h), 0)
    for p in items:
        combined = ImageChops.lighter(combined, p["mask"])
    return items, combined


def paper(size, seed):
    rng = np.random.default_rng(seed)
    arr = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    arr[:, :, 0] = PALE[0]
    arr[:, :, 1] = PALE[1]
    arr[:, :, 2] = PALE[2]
    arr[:, :, 3] = 255
    noise = rng.normal(0, 4, (size[1], size[0], 1))
    arr[:, :, :3] = np.clip(arr[:, :, :3] + noise, 0, 255)
    img = Image.fromarray(arr, "RGBA")
    return img.filter(ImageFilter.GaussianBlur(0.35))


def clipped(layer, mask):
    out = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    alpha = mask.point(lambda v: int(v * 0.92))
    out.alpha_composite(layer)
    out.putalpha(ImageChops.multiply(out.getchannel("A"), alpha))
    return out


def blob_fill(draw, bbox, color, rng, count=80):
    x0, y0, x1, y1 = bbox
    for _ in range(count):
        x = rng.uniform(x0, x1)
        y = rng.uniform(y0, y1)
        r = rng.uniform(10, max(18, (x1 - x0 + y1 - y0) / 18))
        c = tuple(max(0, min(255, int(ch + rng.uniform(-18, 18)))) for ch in color[:3]) + (rng.randint(16, 42),)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=c)


def shrink(b, frac=0.12):
    x0, y0, x1, y1 = b
    dx, dy = (x1 - x0) * frac, (y1 - y0) * frac
    return x0 + dx, y0 + dy, x1 - dx, y1 - dy


def draw_house(draw, b, pal, rng, mode, tall=False):
    x0, y0, x1, y1 = shrink(b, 0.16 if tall else 0.11)
    w, h = x1 - x0, y1 - y0
    if w < 35 or h < 35:
        draw_candy(draw, b, pal, rng, mode)
        return
    roof_h = h * (0.26 if tall else 0.31)
    roof = [(x0 + w * 0.08, y0 + roof_h), (x0 + w * 0.5, y0), (x1 - w * 0.08, y0 + roof_h)]
    body = [x0 + w * 0.15, y0 + roof_h * 0.82, x1 - w * 0.15, y1 - h * 0.08]
    draw.polygon(roof, fill=pal["dark"], outline=None)
    draw.rounded_rectangle(body, radius=max(8, int(w * 0.08)), fill=pal["body"])
    # roof icing scallop
    for i in range(6):
        x = x0 + w * (0.12 + i * 0.15)
        y = y0 + roof_h * (0.65 + 0.1 * math.sin(i))
        draw.ellipse([x - w * 0.04, y - h * 0.012, x + w * 0.04, y + h * 0.035], fill=pal["icing"])
    # windows
    n = 2 if not tall and w > 120 else 1
    for i in range(n):
        cx = body[0] + (body[2] - body[0]) * (i + 1) / (n + 1)
        wy = body[1] + h * 0.22
        ww = max(12, w * 0.11)
        wh = max(16, h * 0.08)
        draw.rounded_rectangle([cx - ww, wy - wh, cx + ww, wy + wh], radius=int(ww * 0.5), fill=pal["glow"])
        draw.arc([cx - ww * 1.2, wy - wh * 1.5, cx + ww * 1.2, wy + wh * 1.5], 180, 360, fill=pal["icing"], width=max(2, int(w * 0.012)))
    # candy dots
    for i in range(10 if not tall else 6):
        cx = rng.uniform(body[0], body[2])
        cy = rng.uniform(body[1] + h * 0.05, body[3])
        rr = rng.uniform(max(3, w * 0.015), max(5, w * 0.035))
        color = pal["accent"] if i % 2 == 0 else pal["accent2"]
        draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=color)


def draw_candy(draw, b, pal, rng, mode):
    x0, y0, x1, y1 = shrink(b, 0.18)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = max(5, min(x1 - x0, y1 - y0) * 0.36)
    if mode in ("peppermint", "holly"):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=pal["icing"])
        for a in range(0, 360, 60):
            end = (cx + math.cos(math.radians(a)) * r, cy + math.sin(math.radians(a)) * r)
            draw.line([cx, cy, end[0], end[1]], fill=pal["accent"], width=max(3, int(r * 0.22)))
    elif mode == "frost":
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=pal["cool"])
        draw.arc([cx - r * 0.7, cy - r * 0.7, cx + r * 0.7, cy + r * 0.7], 10, 280, fill=pal["icing"], width=max(2, int(r * 0.15)))
    else:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=pal["accent2"])
        draw.ellipse([cx - r * 0.42, cy - r * 0.55, cx + r * 0.15, cy + r * 0.02], fill=pal["icing"])


def draw_garland(draw, b, pal, rng, mode):
    x0, y0, x1, y1 = shrink(b, 0.12)
    steps = 9
    last = None
    for i in range(steps):
        t = i / (steps - 1)
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * (0.45 + 0.22 * math.sin(t * math.pi * 2))
        if last:
            draw.line([last[0], last[1], x, y], fill=pal["icing"], width=max(3, int((x1-x0+y1-y0)*0.008)))
        rr = max(4, min(x1 - x0, y1 - y0) * 0.035)
        draw.ellipse([x - rr, y - rr, x + rr, y + rr], fill=pal["accent"] if i % 2 else pal["accent2"])
        last = (x, y)


def classify(p):
    path = p["item_path"]
    if "top subpanel" in path:
        if "chimney" in path:
            return "chimney"
        return "top"
    if "bottom left" in path:
        return "left"
    if "bottom right" in path:
        return "right"
    return "misc"


def render_variant(var, items, combined, h, seed):
    rng = random.Random(seed)
    art = Image.new("RGBA", (W, h), (0, 0, 0, 0))
    pal = var["palette"]
    mode = var["mode"]
    for item in items:
        bbox = item["bbox_px"]
        layer = Image.new("RGBA", (W, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer, "RGBA")
        blob_fill(draw, bbox, pal["cool"], rng, count=45)
        kind = classify(item)
        bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if bw < 105 and bh < 105:
            draw_candy(draw, bbox, pal, rng, mode)
        elif kind == "chimney":
            draw_house(draw, bbox, pal, rng, mode, tall=True)
            x0, y0, x1, y1 = shrink(bbox, 0.22)
            for i in range(3):
                x = (x0 + x1) / 2 + (i - 1) * (x1 - x0) * 0.11
                draw.arc([x - 28, y0 + i * 30, x + 38, y0 + 82 + i * 20], 95, 270, fill=pal["icing"], width=4)
        elif kind == "top":
            draw_house(draw, bbox, pal, rng, mode, tall=False)
            if mode in ("garland", "holly"):
                draw_garland(draw, bbox, pal, rng, mode)
        elif max(bw, bh) / max(1, min(bw, bh)) > 3.1:
            draw_house(draw, bbox, pal, rng, mode, tall=True)
            draw_garland(draw, bbox, pal, rng, mode)
        else:
            draw_house(draw, bbox, pal, rng, mode, tall=False)
        clipped_layer = clipped(layer.filter(ImageFilter.GaussianBlur(0.25)), item["mask"])
        art.alpha_composite(clipped_layer)
    art.putalpha(ImageChops.multiply(art.getchannel("A"), combined))
    return art


def outline_image(base, items):
    draw = ImageDraw.Draw(base, "RGBA")
    for item in items:
        edge = item["mask"].filter(ImageFilter.FIND_EDGES)
        overlay = Image.new("RGBA", base.size, (95, 74, 50, 0))
        overlay.putalpha(edge.point(lambda v: 120 if v > 12 else 0))
        base.alpha_composite(overlay)
    return base


def label_font(size=28):
    for path in ["/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    REV.mkdir(parents=True, exist_ok=True)
    PROD.mkdir(parents=True, exist_ok=True)
    data, crop, scale, h = load_geometry()
    items, combined = masks(data, crop, scale, h)
    (TASK / "geometry" / "mask-size.txt").write_text(f"{W}x{h}\\npaths={len(items)}\\n")
    combined.save(TASK / "geometry" / "combined-mask.png")
    previews = []
    for i, var in enumerate(VARIANTS, 1):
        art = render_variant(var, items, combined, h, 7500 + i)
        art_path = OUT / f"{var['slug']}-artwork.png"
        preview_path = REV / f"{var['slug']}-preview.png"
        prod_art = PROD / art_path.name
        prod_preview = PROD / preview_path.name
        art.save(art_path)
        bg = paper((W, h), 1000 + i)
        bg.alpha_composite(art)
        outline_image(bg, items).save(preview_path)
        shutil.copy2(art_path, prod_art)
        shutil.copy2(preview_path, prod_preview)
        previews.append((var["title"], preview_path, prod_preview))
    make_board(previews)
    manifest = {
        "task": "festive-v1-gingerbread-candidates",
        "geometry": str(GEOM),
        "mask": str(TASK / "geometry" / "combined-mask.png"),
        "candidates": [
            {
                "title": title,
                "preview": str(preview),
                "production_preview": str(prod),
            }
            for title, preview, prod in previews
        ],
    }
    (REV / "candidate-manifest.json").write_text(json.dumps(manifest, indent=2))
    shutil.copy2(REV / "candidate-manifest.json", PROD / "candidate-manifest.json")


def make_board(previews):
    font = label_font(28)
    label_h = 48
    thumb_w = 430
    thumb_h = 640
    gutter = 22
    cols = 3
    rows = math.ceil(len(previews) / cols)
    board = Image.new("RGBA", (cols * thumb_w + (cols + 1) * gutter, rows * (thumb_h + label_h) + (rows + 1) * gutter), (250, 248, 240, 255))
    draw = ImageDraw.Draw(board, "RGBA")
    for idx, (title, path, _prod) in enumerate(previews):
        img = Image.open(path).convert("RGBA")
        img.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = gutter + (idx % cols) * (thumb_w + gutter)
        y = gutter + (idx // cols) * (thumb_h + label_h + gutter)
        draw.text((x, y), f"{idx+1}. {title}", fill=(62, 48, 38, 255), font=font)
        board.alpha_composite(img, (x + (thumb_w - img.width) // 2, y + label_h))
    board_path = REV / "festive-v1-gingerbread-candidate-board.png"
    board.save(board_path)
    shutil.copy2(board_path, PROD / board_path.name)


if __name__ == "__main__":
    main()
