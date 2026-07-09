#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import random
import shutil
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
PALE = (252, 249, 240, 255)

VARIANTS = [
    ("d1-icing-scallop-garlands", "Icing Scallop Garlands", "scallop", {
        "icing": (255, 252, 235, 245), "cookie": (156, 91, 48, 150), "red": (203, 47, 55, 238),
        "green": (52, 130, 82, 218), "blue": (178, 220, 232, 145), "gold": (245, 185, 85, 220)
    }),
    ("d2-peppermint-candy-ribbons", "Peppermint Candy Ribbons", "peppermint", {
        "icing": (255, 252, 239, 248), "cookie": (145, 81, 43, 145), "red": (221, 38, 47, 245),
        "green": (55, 123, 85, 175), "blue": (188, 223, 232, 125), "gold": (245, 195, 92, 190)
    }),
    ("d3-gumdrop-sugar-beads", "Gumdrop Sugar Beads", "gumdrop", {
        "icing": (255, 251, 235, 242), "cookie": (148, 85, 46, 145), "red": (207, 53, 73, 238),
        "green": (53, 143, 102, 225), "blue": (112, 174, 215, 180), "gold": (236, 172, 81, 230)
    }),
    ("d4-frosted-holly-sprigs", "Frosted Holly Sprigs", "holly", {
        "icing": (255, 254, 242, 242), "cookie": (142, 82, 45, 130), "red": (204, 36, 47, 238),
        "green": (21, 110, 76, 235), "blue": (178, 222, 236, 145), "gold": (240, 190, 105, 190)
    }),
    ("d5-powdered-sugar-crystals", "Powdered Sugar Crystals", "frost", {
        "icing": (255, 255, 247, 248), "cookie": (151, 90, 54, 115), "red": (178, 70, 76, 145),
        "green": (118, 170, 143, 145), "blue": (118, 194, 228, 190), "gold": (235, 202, 134, 145)
    }),
    ("d6-painted-candy-confetti", "Painted Candy Confetti", "confetti", {
        "icing": (252, 246, 226, 240), "cookie": (148, 82, 47, 135), "red": (211, 52, 63, 238),
        "green": (43, 147, 131, 225), "blue": (76, 103, 184, 190), "gold": (237, 175, 101, 218)
    }),
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
        steps = max(6, min(32, int(span / 16)))
        for s in range(steps):
            poly.append(cubic(p0, p1, p2, p3, s / steps))
    return poly


def build_masks(data, crop, scale, h):
    items = []
    for idx, p in enumerate(data["paths"]):
        hi = 3
        poly = sampled_polygon(p, crop, scale)
        mask_hi = Image.new("L", (W * hi, h * hi), 0)
        ImageDraw.Draw(mask_hi).polygon([(x * hi, y * hi) for x, y in poly], fill=255)
        mask = mask_hi.resize((W, h), Image.Resampling.LANCZOS)
        bbox = mask.getbbox()
        if bbox:
            p = dict(p)
            p["idx"] = idx
            p["mask"] = mask
            p["bbox_px"] = bbox
            p["poly"] = poly
            items.append(p)
    combined = Image.new("L", (W, h), 0)
    for item in items:
        combined = ImageChops.lighter(combined, item["mask"])
    return items, combined


def shrink(b, frac):
    x0, y0, x1, y1 = b
    dx, dy = (x1 - x0) * frac, (y1 - y0) * frac
    return x0 + dx, y0 + dy, x1 - dx, y1 - dy


def paper(size, seed):
    rng = np.random.default_rng(seed)
    arr = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3] = PALE
    arr[:, :, :3] = np.clip(arr[:, :, :3] + rng.normal(0, 4, (size[1], size[0], 1)), 0, 255)
    return Image.fromarray(arr, "RGBA").filter(ImageFilter.GaussianBlur(0.25))


def classify(item):
    path = item["item_path"]
    if "top subpanel" in path and "chimney" in path:
        return "chimney"
    if "top subpanel" in path:
        return "top"
    if "bottom left" in path:
        return "left"
    if "bottom right" in path:
        return "right"
    return "misc"


def draw_watercolor_ground(draw, bbox, pal, rng, count=70):
    x0, y0, x1, y1 = bbox
    for _ in range(count):
        x = rng.uniform(x0, x1)
        y = rng.uniform(y0, y1)
        r = rng.uniform(12, max(20, (x1 - x0 + y1 - y0) / 22))
        base = pal["blue"] if rng.random() < 0.65 else pal["cookie"]
        color = tuple(max(0, min(255, int(c + rng.uniform(-12, 12)))) for c in base[:3]) + (rng.randint(18, 42),)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


def sine_path(b, horizontal=True, n=90, amp=0.18, phase=0):
    x0, y0, x1, y1 = b
    pts = []
    for i in range(n):
        t = i / (n - 1)
        if horizontal:
            x = x0 + (x1 - x0) * t
            y = (y0 + y1) / 2 + math.sin(t * math.tau + phase) * (y1 - y0) * amp
        else:
            x = (x0 + x1) / 2 + math.sin(t * math.tau + phase) * (x1 - x0) * amp
            y = y0 + (y1 - y0) * t
        pts.append((x, y))
    return pts


def draw_line(draw, pts, fill, width):
    if len(pts) > 1:
        draw.line(pts, fill=fill, width=max(1, int(width)), joint="curve")


def contour_trim(draw, item, pal, rng, mode):
    poly = item["poly"]
    if len(poly) < 10:
        return
    step = max(12, len(poly) // 34)
    pts = poly[::step]
    if mode in ("scallop", "gumdrop", "confetti"):
        colors = [pal["red"], pal["green"], pal["gold"], pal["icing"]]
        for i, (x, y) in enumerate(pts):
            if i % 2 == 0:
                r = rng.uniform(5, 11)
                draw.ellipse([x - r, y - r, x + r, y + r], fill=colors[i % len(colors)])
    if mode in ("frost", "scallop"):
        for x, y in pts[::2]:
            r = rng.uniform(3, 8)
            draw.ellipse([x - r, y - r, x + r, y + r], fill=pal["icing"])


def beads(draw, pts, pal, rng, every=10, r=9):
    colors = [pal["red"], pal["green"], pal["gold"], pal["icing"]]
    for i, (x, y) in enumerate(pts[::every]):
        rr = max(3, r * rng.uniform(0.65, 1.2))
        c = colors[i % len(colors)]
        draw.ellipse([x - rr, y - rr, x + rr, y + rr], fill=c)
        if rr > 5:
            draw.ellipse([x - rr * .35, y - rr * .45, x, y - rr * .1], fill=(255, 255, 255, 120))


def peppermint_disc(draw, cx, cy, r, pal, spokes=True):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=pal["icing"])
    if spokes:
        for a in range(0, 360, 60):
            ex = cx + math.cos(math.radians(a)) * r
            ey = cy + math.sin(math.radians(a)) * r
            draw.line([cx, cy, ex, ey], fill=pal["red"], width=max(2, int(r * 0.20)))
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=pal["red"], width=max(1, int(r * 0.08)))


def stars(draw, b, pal, rng, count=14):
    x0, y0, x1, y1 = shrink(b, 0.16)
    for _ in range(count):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        r = rng.uniform(4, 12)
        pts = []
        for k in range(10):
            a = -math.pi / 2 + k * math.pi / 5
            rr = r if k % 2 == 0 else r * 0.42
            pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
        draw.polygon(pts, fill=pal["icing"] if rng.random() < .65 else pal["blue"])


def scallops(draw, b, pal, rng, horizontal=True):
    x0, y0, x1, y1 = shrink(b, 0.14)
    span = (x1 - x0) if horizontal else (y1 - y0)
    n = max(6, int(span / 48))
    for i in range(n):
        t = (i + 0.5) / n
        if horizontal:
            cx = x0 + (x1 - x0) * t
            cy = y0 + (y1 - y0) * (0.26 + 0.09 * math.sin(i))
        else:
            cx = x0 + (x1 - x0) * (0.35 + 0.11 * math.sin(i))
            cy = y0 + (y1 - y0) * t
        r = max(10, min(x1 - x0, y1 - y0) * 0.052)
        draw.ellipse([cx - r * 1.25, cy - r * .55, cx + r * 1.25, cy + r * 1.05], fill=pal["icing"])


def holly(draw, pts, pal, rng):
    for i, (x, y) in enumerate(pts[::16]):
        if i % 2:
            leaf = [(x, y), (x + 20, y - 9), (x + 35, y), (x + 20, y + 9)]
        else:
            leaf = [(x, y), (x - 20, y - 9), (x - 35, y), (x - 20, y + 9)]
        draw.polygon(leaf, fill=pal["green"])
        if i % 3 == 0:
            draw.ellipse([x - 7, y - 7, x + 7, y + 7], fill=pal["red"])


def decorate_item(draw, item, pal, mode, rng):
    b = item["bbox_px"]
    x0, y0, x1, y1 = b
    bw, bh = x1 - x0, y1 - y0
    kind = classify(item)
    draw_watercolor_ground(draw, b, pal, rng, count=95 if bw * bh > 80000 else 24)
    contour_trim(draw, item, pal, rng, mode)
    small = min(bw, bh) < 125
    if small:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        r = min(bw, bh) * 0.28
        if mode in ("peppermint", "confetti"):
            peppermint_disc(draw, cx, cy, r, pal)
        elif mode == "frost":
            stars(draw, b, pal, rng, count=1)
        else:
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=pal["red" if mode == "holly" else "green"])
            draw.ellipse([cx - r * .35, cy - r * .45, cx + r * .05, cy - r * .05], fill=(255, 255, 255, 115))
        return
    horizontal = (bw >= bh * 0.9 and kind == "top")
    pts = sine_path(shrink(b, 0.18), horizontal=horizontal, amp=0.19 if mode != "peppermint" else 0.08, phase=rng.random() * math.tau)
    if mode == "scallop":
        scallops(draw, b, pal, rng, horizontal=horizontal)
        draw_line(draw, pts, pal["icing"], width=min(bw, bh) * 0.044)
        beads(draw, pts, pal, rng, every=10, r=min(bw, bh) * 0.033)
    elif mode == "peppermint":
        draw_line(draw, pts, pal["red"], width=min(bw, bh) * 0.058)
        pts2 = [(x, y + (8 if horizontal else 0)) for x, y in pts]
        draw_line(draw, pts2, pal["icing"], width=min(bw, bh) * 0.030)
        for x, y in pts[::18]:
            peppermint_disc(draw, x, y, min(bw, bh) * 0.035, pal, spokes=True)
    elif mode == "gumdrop":
        draw_line(draw, pts, pal["icing"], width=min(bw, bh) * 0.024)
        beads(draw, pts, pal, rng, every=7, r=min(bw, bh) * 0.039)
    elif mode == "holly":
        draw_line(draw, pts, pal["icing"], width=min(bw, bh) * 0.018)
        holly(draw, pts, pal, rng)
        beads(draw, pts, pal, rng, every=18, r=min(bw, bh) * 0.022)
    elif mode == "frost":
        scallops(draw, b, pal, rng, horizontal=horizontal)
        stars(draw, b, pal, rng, count=22 if kind == "top" else 12)
        draw_line(draw, pts, pal["blue"], width=min(bw, bh) * 0.034)
    elif mode == "confetti":
        draw_line(draw, pts, pal["icing"], width=min(bw, bh) * 0.022)
        beads(draw, pts, pal, rng, every=8, r=min(bw, bh) * 0.030)
        stars(draw, b, pal, rng, count=12)
    # Icing drips follow gravity inside vertical shapes and upper contour in roof-like shape.
    drip_count = 7 if kind == "top" else 4
    for i in range(drip_count):
        x = x0 + bw * (0.18 + 0.64 * (i + rng.random() * .35) / drip_count)
        y = y0 + bh * (0.16 + rng.random() * .1)
        length = bh * rng.uniform(0.05, 0.16)
        draw.line([x, y, x + rng.uniform(-5, 5), y + length], fill=pal["icing"], width=max(2, int(min(bw, bh) * 0.014)))
        rr = max(3, min(bw, bh) * 0.014)
        draw.ellipse([x - rr, y + length - rr, x + rr, y + length + rr], fill=pal["icing"])


def render_variant(slug, title, mode, pal, items, combined, h, seed):
    rng = random.Random(seed)
    art = Image.new("RGBA", (W, h), (0, 0, 0, 0))
    for item in items:
        layer = Image.new("RGBA", (W, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer, "RGBA")
        decorate_item(draw, item, pal, mode, rng)
        layer = layer.filter(ImageFilter.GaussianBlur(0.22))
        layer.putalpha(ImageChops.multiply(layer.getchannel("A"), item["mask"].point(lambda v: int(v * .94))))
        art.alpha_composite(layer)
    art.putalpha(ImageChops.multiply(art.getchannel("A"), combined))
    return art


def outline(base, items):
    for item in items:
        edge = item["mask"].filter(ImageFilter.FIND_EDGES)
        ov = Image.new("RGBA", base.size, (90, 72, 50, 0))
        ov.putalpha(edge.point(lambda v: 125 if v > 12 else 0))
        base.alpha_composite(ov)
    return base


def label_font(size=28):
    for path in ["/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def make_board(previews):
    font = label_font(27)
    label_h, thumb_w, thumb_h, gutter = 48, 430, 640, 22
    cols = 3
    rows = math.ceil(len(previews) / cols)
    board = Image.new("RGBA", (cols * thumb_w + (cols + 1) * gutter, rows * (thumb_h + label_h) + (rows + 1) * gutter), (250, 248, 240, 255))
    draw = ImageDraw.Draw(board, "RGBA")
    for idx, (title, path) in enumerate(previews):
        img = Image.open(path).convert("RGBA")
        img.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = gutter + (idx % cols) * (thumb_w + gutter)
        y = gutter + (idx // cols) * (thumb_h + label_h + gutter)
        draw.text((x, y), f"{idx + 1}. {title}", fill=(62, 48, 38, 255), font=font)
        board.alpha_composite(img, (x + (thumb_w - img.width) // 2, y + label_h))
    p = REV / "festive-v1-decoration-candidate-board.png"
    board.save(p)
    shutil.copy2(p, PROD / p.name)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    REV.mkdir(parents=True, exist_ok=True)
    PROD.mkdir(parents=True, exist_ok=True)
    data, crop, scale, h = load_geometry()
    items, combined = build_masks(data, crop, scale, h)
    combined.save(TASK / "geometry" / "combined-decoration-mask.png")
    previews = []
    manifest = []
    for i, (slug, title, mode, pal) in enumerate(VARIANTS, 1):
        art = render_variant(slug, title, mode, pal, items, combined, h, 18000 + i)
        art_path = OUT / f"{slug}-artwork.png"
        preview_path = REV / f"{slug}-preview.png"
        art.save(art_path)
        bg = paper((W, h), 19000 + i)
        bg.alpha_composite(art)
        outline(bg, items).save(preview_path)
        shutil.copy2(art_path, PROD / art_path.name)
        shutil.copy2(preview_path, PROD / preview_path.name)
        previews.append((title, preview_path))
        manifest.append({"title": title, "artwork": str(art_path), "preview": str(preview_path), "production_preview": str(PROD / preview_path.name)})
    make_board(previews)
    (REV / "decoration-candidate-manifest.json").write_text(json.dumps({"candidates": manifest}, indent=2))
    shutil.copy2(REV / "decoration-candidate-manifest.json", PROD / "decoration-candidate-manifest.json")


if __name__ == "__main__":
    main()
