#!/usr/bin/env python3
"""Render a registered overlay of a combined "template + embedded illustration" SVG:
paste every embedded raster at its SVG transform, then draw the template guide lines
(coloured by their .stN stroke colour) ON TOP — so adherence can be judged by eye.

No external SVG renderer needed (none installed); reuses scripts/svg_geometry.py for
robust path flattening and PIL for raster compositing.

Usage:
  python3 scripts/make_anchor_overlay.py <combined.svg> --out overlay.png [--width 1400]
"""
from __future__ import annotations
import argparse, base64, io, re, sys
from pathlib import Path
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import svg_geometry as G  # noqa: E402

NUM = r"[-+]?\d*\.?\d+(?:e[-+]?\d+)?"


def parse_transform(t: str):
    """Return (tx, ty, sx, sy) from translate()/scale()/matrix(); identity default."""
    tx = ty = 0.0
    sx = sy = 1.0
    if not t:
        return tx, ty, sx, sy
    m = re.search(rf"translate\(\s*({NUM})[ ,]+({NUM})", t) or re.search(rf"translate\(\s*({NUM})", t)
    if m:
        tx = float(m.group(1))
        ty = float(m.group(2)) if m.lastindex and m.lastindex >= 2 else 0.0
    m = re.search(rf"scale\(\s*({NUM})[ ,]+({NUM})", t) or re.search(rf"scale\(\s*({NUM})", t)
    if m:
        sx = float(m.group(1))
        sy = float(m.group(2)) if m.lastindex and m.lastindex >= 2 else sx
    mm = re.search(rf"matrix\(\s*({NUM})[ ,]+({NUM})[ ,]+({NUM})[ ,]+({NUM})[ ,]+({NUM})[ ,]+({NUM})", t)
    if mm:
        a, b, c, d, e, f = (float(mm.group(i)) for i in range(1, 7))
        sx, sy, tx, ty = a, d, e, f
    return tx, ty, sx, sy


def style_colors(svg_text: str) -> dict[str, str]:
    """class -> stroke hex, parsed from the <style> block (handles grouped selectors)."""
    m = re.search(r"<style[^>]*>(.*?)</style>", svg_text, re.S)
    colors: dict[str, str] = {}
    if not m:
        return colors
    for rule in re.finditer(r"([^{}]+)\{([^}]*)\}", m.group(1)):
        sel, body = rule.group(1), rule.group(2)
        cm = re.search(r"stroke:\s*(#[0-9a-fA-F]{6})", body)
        if not cm:
            continue
        for cls in re.findall(r"\.([A-Za-z0-9_-]+)", sel):
            colors[cls] = cm.group(1)
    return colors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("svg")
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=1400)
    ap.add_argument("--line-min", type=int, default=3, help="min stroke px on canvas")
    ap.add_argument("--artwork-only", action="store_true",
                    help="emit the registered artwork on the viewBox canvas WITHOUT guide lines "
                         "(a 'registered candidate' for geometry metrics)")
    ap.add_argument("--base", help="use this PNG as the canvas (a generated/perturbed candidate "
                                   "already filling the viewBox panel) instead of the SVG's embedded raster")
    ap.add_argument("--contrast", action="store_true",
                    help="recolor guide lines by CLASSIFIED ROLE (cutout=magenta, contour=lime, "
                         "red-zone=red, fold=blue) instead of the SVG's own stroke colours — readable "
                         "over monochrome/all-black templates where dark-on-dark hides adherence")
    args = ap.parse_args()

    text = Path(args.svg).read_text(encoding="utf-8", errors="replace")

    # 1) collect embedded images with their transforms (before stripping)
    images = []
    for im in re.finditer(r"<image\b([^>]*?)data:image/(?:png|jpeg);base64,([A-Za-z0-9+/=]+)([^>]*)>", text):
        attrs = im.group(1) + im.group(3)
        tr = re.search(r'transform="([^"]*)"', attrs)
        w = re.search(r'width="([^"]*)"', attrs)
        h = re.search(r'height="([^"]*)"', attrs)
        images.append({
            "blob": im.group(2),
            "transform": tr.group(1) if tr else "",
            "w": float(w.group(1)) if w else None,
            "h": float(h.group(1)) if h else None,
        })

    # 2) stripped XML for viewBox + style + shapes
    stripped = re.sub(r"<image\b[^>]*>(\s*</image>)?", "", text)
    colors = style_colors(stripped)
    root = ET.fromstring(stripped)
    vbx, vby, vbw, vbh = G.read_viewbox(root)
    sf = args.width / vbw
    W, H = int(round(vbw * sf)), int(round(vbh * sf))

    def to_screen(x, y):
        return ((x - vbx) * sf, (y - vby) * sf)

    if args.base:
        # use an external candidate image as the canvas (a generated/perturbed candidate that
        # already fills the viewBox panel) and draw the template lines registered on top.
        canvas = Image.open(args.base).convert("RGB").resize((W, H))
    else:
        canvas = Image.new("RGB", (W, H), (255, 255, 255))
        # 3) paste each embedded raster at its transform
        for d in images:
            tx, ty, sx, sy = parse_transform(d["transform"])
            png = Image.open(io.BytesIO(base64.b64decode(d["blob"]))).convert("RGBA")
            iw, ih = png.size
            pw = max(1, int(round(iw * sx * sf)))
            ph = max(1, int(round(ih * sy * sf)))
            png = png.resize((pw, ph))
            canvas.paste(png, (int(round((tx - vbx) * sf)), int(round((ty - vby) * sf))), png)

    if args.artwork_only:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        canvas.save(args.out, quality=92)
        print(f"artwork-only {W}x{H} (sf={sf:.4f}) <- {len(images)} raster(s); wrote {args.out}")
        return 0

    if args.contrast:
        # recolor by classified ROLE so monochrome templates stay readable (dark-on-dark hides
        # adherence). Uses the same svg_classify the judge scores with → lines match the metric.
        import svg_classify as C  # noqa: E402
        ROLE_COL = {"internal_cutout": (237, 31, 121), "outer_contour": (57, 181, 74),
                    "top_contour": (57, 181, 74), "no_focal_motif_zone": (237, 28, 36),
                    "fold_or_subpanel": (28, 117, 188), "saloon_arch": (247, 148, 29)}
        vb, shapes = C.extract_shapes(Path(args.svg))
        cl = C.classify(shapes)
        draw = ImageDraw.Draw(canvas)
        lwid = max(args.line_min, 3)
        for s in sorted(cl, key=lambda s: 0 if s.role in ("outer_contour", "top_contour") else 1):
            col = ROLE_COL.get(s.role)
            if not col:
                continue
            pts = [to_screen(x, y) for x, y in s.polygon.exterior.coords]
            if len(pts) >= 2:
                draw.line(pts, fill=col, width=lwid, joint="curve")
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        canvas.save(args.out, quality=92)
        roles = sorted(set(s.role for s in cl if ROLE_COL.get(s.role)))
        print(f"overlay(contrast) {W}x{H} (sf={sf:.4f}); roles={roles}")
        print(f"wrote {args.out}")
        return 0

    # 4) draw template shapes on top, coloured by class stroke colour
    draw = ImageDraw.Draw(canvas)

    def cls_color(el):
        for c in (el.attrib.get("class", "")).split():
            if c in colors:
                return colors[c]
        return "#444444"

    def lw(el):
        return max(args.line_min, 3)

    def scr(ctm, pts):
        return [to_screen(x, y) for x, y in G.apply_ctm(ctm, pts)]

    for el, ctm in G.iter_with_ctm(root):
        tag = G.tag_name(el)
        col = cls_color(el)
        if tag == "path" and el.attrib.get("d"):
            for sub in G.parse_path_d(el.attrib["d"]):
                pts = scr(ctm, sub)
                if len(pts) >= 2:
                    draw.line(pts, fill=col, width=lw(el), joint="curve")
        elif tag in ("polygon", "polyline") and el.attrib.get("points"):
            pts = scr(ctm, G.parse_points(el.attrib["points"]))
            if len(pts) >= 2:
                if tag == "polygon":
                    pts = pts + [pts[0]]
                draw.line(pts, fill=col, width=lw(el), joint="curve")
        elif tag == "line":
            x1, y1, x2, y2 = (float(el.attrib.get(k, 0)) for k in ("x1", "y1", "x2", "y2"))
            draw.line(scr(ctm, [(x1, y1), (x2, y2)]), fill=col, width=lw(el))
        elif tag == "rect":
            x = float(el.attrib.get("x", 0)); y = float(el.attrib.get("y", 0))
            w = float(el.attrib.get("width", 0)); h = float(el.attrib.get("height", 0))
            corners = scr(ctm, [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)])
            draw.line(corners, fill=col, width=lw(el), joint="curve")
        elif tag in ("circle", "ellipse"):
            cx = float(el.attrib.get("cx", 0)); cy = float(el.attrib.get("cy", 0))
            rx = float(el.attrib.get("r", el.attrib.get("rx", 0)))
            ry = float(el.attrib.get("r", el.attrib.get("ry", 0)))
            (x0, y0), (x1, y1) = scr(ctm, [(cx - rx, cy - ry), (cx + rx, cy + ry)])
            draw.ellipse([min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)], outline=col, width=lw(el))

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.out, quality=92)
    print(f"overlay {W}x{H} (sf={sf:.4f}) <- {len(images)} raster(s); colours={sorted(set(colors.values()))}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
