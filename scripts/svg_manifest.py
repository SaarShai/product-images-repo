#!/usr/bin/env python3
"""Generalized template-manifest extractor: parse ANY panel SVG into JSON.

Nothing is hardcoded per panel. Every number is DERIVED from the SVG itself,
replacing the per-panel constants that scripts/geo_overlay.py and
scripts/window_enlarge.py bake in (VB_W/VB_H, IMG_W/IMG_H, TX/TY/SC).

The manifest contains, all derived from the SVG:

- ``viewBox`` -> {x, y, w, h}
- ``roles`` -> for each legend color-role (cut_contour, safe, keep_clear,
  fold, top_contour, arch) the geometry found by the legend colors: a list of
  entries with the element tag, a bbox {x0,y0,x1,y1} in viewBox coords, the
  resolved stroke/fill color, and (for paths/polygons) the raw `d`/points so
  downstream can re-flatten if it wants.
- ``fixed_elements`` -> every ``<image>`` with its transform composed to a
  bounding box in viewBox coords {x0,y0,x1,y1}, plus width/height (the image's
  intrinsic pixel size) and scale (sx, sy from the composed CTM).
- ``expected_element_counts`` -> e.g. {"windows": <number of <image> els>}.

Role colors follow the SVG legend:
  magenta / pink = cut contour   yellow = safe        red = keep-clear
  blue           = fold          green  = top-contour orange = arch

CLI:
  python3 scripts/svg_manifest.py --svg PATH [--out PATH]   (default: print JSON)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import svg_geometry as G  # noqa: E402  (shared authoritative SVG parser)

ROOT = Path(__file__).resolve().parents[1]
Point = tuple[float, float]

# --- Legend color -> role ----------------------------------------------------
# Classified by hue/lightness so it generalizes across the exact hex variants
# seen in the repo (yellow #ffdb55 & #fff200; red #ed1c24; pink #ed1f79;
# blue #1c75bc; green #39b54a; orange #f7941d) rather than matching literals.
ROLE_KEYS = ("cut_contour", "safe", "keep_clear", "fold", "top_contour", "arch")


def _hex_to_rgb(value: str | None) -> tuple[int, int, int] | None:
    if not value:
        return None
    m = re.search(r"#([0-9a-fA-F]{6})", value)
    if m:
        h = m.group(1)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    m = re.search(r"#([0-9a-fA-F]{3})\b", value)
    if m:
        h = m.group(1)
        return tuple(int(c * 2, 16) for c in h)  # type: ignore[return-value]
    m = re.search(r"rgb\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)", value)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def color_role(value: str | None) -> str:
    """Map a stroke/fill color to a legend role, or "" if it is not a role color.

    Hue-based so #ed1c24 (red, keep-clear) and #ed1f79 (pink/magenta, cut
    contour) are distinguished by their blue channel even though both are
    red-dominant.
    """
    rgb = _hex_to_rgb(value)
    if rgb is None:
        return ""
    r, g, b = rgb
    mx, mn = max(rgb), min(rgb)
    # near black / white / gray -> not a legend role (registration/labels/etc.)
    if mx - mn < 40:
        return ""

    # yellow: high R and G, low B
    if r > 180 and g > 150 and b < 150:
        return "safe"
    # orange: high R, mid G, low B (between yellow and red)
    if r > 180 and 90 <= g <= 180 and b < 110:
        return "arch"
    # red vs magenta/pink: both red-dominant; magenta has a markedly higher
    # blue channel (pink). Red keep-clear has low B.
    if r > 150 and g < 120 and r - g > 60:
        if b > g + 30:
            return "cut_contour"  # pink / magenta
        return "keep_clear"  # red
    # green: green-dominant
    if g > 120 and g - r > 30 and g - b > 30:
        return "top_contour"
    # blue: blue-dominant
    if b > 120 and b - r > 30 and b - g > 10:
        return "fold"
    return ""


# --- CSS class resolution (mirrors svg_classify, kept self-contained) --------
def parse_css(root: ET.Element) -> dict[str, dict[str, str]]:
    rules: dict[str, dict[str, str]] = {}
    for el in root.iter():
        if G.tag_name(el) == "style" and el.text:
            for sel, body in re.findall(r"\.([\w-]+)\s*\{([^}]*)\}", el.text):
                props: dict[str, str] = {}
                for decl in body.split(";"):
                    if ":" in decl:
                        k, v = decl.split(":", 1)
                        props[k.strip()] = v.strip()
                rules.setdefault(sel, {}).update(props)
    return rules


def element_style(el: ET.Element, css: dict[str, dict[str, str]]) -> dict[str, str]:
    style: dict[str, str] = {}
    for cls in (el.attrib.get("class") or "").split():
        style.update(css.get(cls, {}))
    for key in ("stroke", "fill", "stroke-dasharray", "stroke-width"):
        if key in el.attrib:
            style[key] = el.attrib[key]
    if el.attrib.get("style"):
        for decl in el.attrib["style"].split(";"):
            if ":" in decl:
                k, v = decl.split(":", 1)
                style[k.strip()] = v.strip()
    return style


def role_color(style: dict[str, str]) -> tuple[str, str]:
    """Return (role, color) for an element's stroke (preferred) or fill."""
    for key in ("stroke", "fill"):
        val = style.get(key)
        role = color_role(val)
        if role:
            return role, val
    return "", style.get("stroke") or style.get("fill") or ""


def _bbox(points: list[Point]) -> list[float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)]


def _scale_from_ctm(m: G.Matrix) -> tuple[float, float]:
    """Recover (sx, sy) magnitudes from an affine matrix (a,b,c,d,e,f)."""
    a, b, c, d, _e, _f = m
    sx = (a * a + b * b) ** 0.5
    sy = (c * c + d * d) ** 0.5
    return round(sx, 6), round(sy, 6)


def build_manifest(svg: Path) -> dict:
    root = ET.parse(svg).getroot()
    css = parse_css(root)
    vx, vy, vw, vh = G.read_viewbox(root)

    roles: dict[str, list] = {k: [] for k in ROLE_KEYS}
    fixed_elements: list[dict] = []

    for el, ctm in G.iter_with_ctm(root):
        name = G.tag_name(el)

        if name == "image":
            # intrinsic pixel size (defaults 0 if absent)
            def _num(attr: str) -> float:
                v = el.attrib.get(attr, "0")
                nums = re.findall(G.FLOAT, v)
                return float(nums[0]) if nums else 0.0

            iw = _num("width")
            ih = _num("height")
            ix = _num("x")
            iy = _num("y")
            # image local rect corners -> apply composed CTM
            corners = G.apply_ctm(ctm, [
                (ix, iy), (ix + iw, iy), (ix + iw, iy + ih), (ix, iy + ih),
            ])
            bb = _bbox(corners)
            sx, sy = _scale_from_ctm(ctm)
            href = el.attrib.get("{http://www.w3.org/1999/xlink}href") or el.attrib.get("href") or ""
            href_kind = "data" if href.startswith("data:") else ("ref" if href else "")
            fixed_elements.append({
                "tag": "image",
                "id": el.attrib.get("id", ""),
                "bbox": {"x0": bb[0], "y0": bb[1], "x1": bb[2], "y1": bb[3]},
                "width": round(iw, 4),
                "height": round(ih, 4),
                "scale": {"sx": sx, "sy": sy},
                "transform": el.attrib.get("transform", ""),
                "href_kind": href_kind,
            })
            continue

        # geometry by role color
        style = element_style(el, css)
        role, color = role_color(style)
        if not role:
            continue

        entry: dict = {"tag": name, "id": el.attrib.get("id", ""), "color": (color or "").strip()}
        if name == "path" and el.attrib.get("d"):
            pts: list[Point] = []
            for sub in G.parse_path_d(el.attrib["d"]):
                pts.extend(G.apply_ctm(ctm, sub))
            if not pts:
                continue
            entry["bbox"] = dict(zip(("x0", "y0", "x1", "y1"), _bbox(pts)))
            entry["d"] = el.attrib["d"]
        elif name in ("polygon", "polyline") and el.attrib.get("points"):
            pts = G.apply_ctm(ctm, G.parse_points(el.attrib["points"]))
            if not pts:
                continue
            entry["bbox"] = dict(zip(("x0", "y0", "x1", "y1"), _bbox(pts)))
            entry["points"] = el.attrib["points"]
        elif name == "rect":
            x = float(re.findall(G.FLOAT, el.attrib.get("x", "0"))[0]) if el.attrib.get("x") else 0.0
            y = float(re.findall(G.FLOAT, el.attrib.get("y", "0"))[0]) if el.attrib.get("y") else 0.0
            w = float(re.findall(G.FLOAT, el.attrib.get("width", "0"))[0]) if el.attrib.get("width") else 0.0
            h = float(re.findall(G.FLOAT, el.attrib.get("height", "0"))[0]) if el.attrib.get("height") else 0.0
            corners = G.apply_ctm(ctm, [(x, y), (x + w, y), (x + w, y + h), (x, y + h)])
            entry["bbox"] = dict(zip(("x0", "y0", "x1", "y1"), _bbox(corners)))
        elif name in ("line",):
            pts = G.apply_ctm(ctm, [
                (float(re.findall(G.FLOAT, el.attrib.get("x1", "0"))[0]) if el.attrib.get("x1") else 0.0,
                 float(re.findall(G.FLOAT, el.attrib.get("y1", "0"))[0]) if el.attrib.get("y1") else 0.0),
                (float(re.findall(G.FLOAT, el.attrib.get("x2", "0"))[0]) if el.attrib.get("x2") else 0.0,
                 float(re.findall(G.FLOAT, el.attrib.get("y2", "0"))[0]) if el.attrib.get("y2") else 0.0),
            ])
            entry["bbox"] = dict(zip(("x0", "y0", "x1", "y1"), _bbox(pts)))
        elif name in ("circle", "ellipse"):
            cx = float(re.findall(G.FLOAT, el.attrib.get("cx", "0"))[0]) if el.attrib.get("cx") else 0.0
            cy = float(re.findall(G.FLOAT, el.attrib.get("cy", "0"))[0]) if el.attrib.get("cy") else 0.0
            r = el.attrib.get("r")
            rx = float(re.findall(G.FLOAT, r)[0]) if r else (float(re.findall(G.FLOAT, el.attrib.get("rx", "0"))[0]) if el.attrib.get("rx") else 0.0)
            ry = float(re.findall(G.FLOAT, r)[0]) if r else (float(re.findall(G.FLOAT, el.attrib.get("ry", "0"))[0]) if el.attrib.get("ry") else 0.0)
            corners = G.apply_ctm(ctm, [(cx - rx, cy - ry), (cx + rx, cy - ry), (cx + rx, cy + ry), (cx - rx, cy + ry)])
            entry["bbox"] = dict(zip(("x0", "y0", "x1", "y1"), _bbox(corners)))
        else:
            continue

        roles[role].append(entry)

    manifest = {
        "template_svg": _rel(svg),
        "viewBox": {"x": round(vx, 4), "y": round(vy, 4), "w": round(vw, 4), "h": round(vh, 4)},
        "roles": roles,
        "fixed_elements": fixed_elements,
        "expected_element_counts": {"windows": len(fixed_elements)},
    }
    return manifest


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--svg", required=True, help="panel SVG to parse")
    ap.add_argument("--out", help="write JSON here (default: print to stdout)")
    args = ap.parse_args()

    svg = Path(args.svg)
    if not svg.is_absolute():
        svg = (ROOT / svg)
    if not svg.exists():
        print(f"ERROR: SVG not found: {svg}", file=sys.stderr)
        return 2

    manifest = build_manifest(svg)
    text = json.dumps(manifest, indent=2) + "\n"
    if args.out:
        out = Path(args.out)
        if not out.is_absolute():
            out = ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
        print(f"manifest -> {_rel(out)}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
