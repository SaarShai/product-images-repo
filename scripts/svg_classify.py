#!/usr/bin/env python3
"""Step 1 gate: classify an SVG template's geometry into roles and gate the manifest.

Turns the user's raw SVG (contours + cutouts + overlay zones) into a filled,
machine-checked ``template-manifest.json`` so no later step can generate from an
un-parsed template. Encodes the hard-won lessons:

- open paths split across a path + a closure polyline are stitched before
  polygonizing (otherwise Shapely closes them with a diagonal and eats panel
  area) -- the socket/polyline lesson;
- a small contour *contained by* or *biting into* a big one is a cutout (hole),
  not paintable -- the socket/notch lesson;
- red dashed rectangles are keep-clear / no-focal-motif bands (the V7 failure:
  a bird/butterfly cropped by the middle rectangles); blue dashed lines are
  sub-panel dividers / visual guides.

Usage:
  svg_classify.py <svg> [--task DIR] [--write-manifest] [--report PATH] [--json]
  svg_classify.py --check tasks/<task>/template-manifest.json   # the gate
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import svg_geometry as G  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
Point = tuple[float, float]


@dataclass
class Shape:
    kind: str  # path | polygon | rect | line | polyline
    ref: str  # element id/class or synthetic index
    polygon: Polygon | None
    area: float
    bounds: tuple[float, float, float, float]
    style: dict[str, str] = field(default_factory=dict)
    role: str = ""
    reason: str = ""


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def parse_css(root: ET.Element) -> dict[str, dict[str, str]]:
    """Resolve ``<style>`` class rules to property dicts (e.g. .cls-3 -> {...})."""
    rules: dict[str, dict[str, str]] = {}
    for el in root.iter():
        if G.tag_name(el) == "style" and el.text:
            for sel, body in re.findall(r"\.([\w-]+)\s*\{([^}]*)\}", el.text):
                props = {}
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


def color_family(value: str | None) -> str:
    if not value:
        return ""
    m = re.search(r"#([0-9a-fA-F]{6})", value)
    if not m:
        return ""
    r, gg, b = (int(m.group(1)[i : i + 2], 16) for i in (0, 2, 4))
    if r > 140 and gg < 110 and b < 110:
        return "red"
    if b > 140 and r < 110 and gg < 150:
        return "blue"
    if gg > 130 and r < 130 and b < 130:
        return "green"
    return "other"


def is_dashed(style: dict[str, str]) -> bool:
    da = style.get("stroke-dasharray", "none")
    return bool(da) and da not in ("none", "0")


def poly_from_points(points: list[Point]) -> Polygon | None:
    pts = points[:]
    if len(pts) < 3:
        return None
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    poly = Polygon(pts)
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty or poly.area <= 1:
        return None
    if isinstance(poly, MultiPolygon):
        poly = max(poly.geoms, key=lambda p: p.area)
    return poly


def close_open_path_with_polyline(points: list[Point], polylines: list[list[Point]]) -> list[Point]:
    """Stitch an open path to a separate closure polyline (socket/polyline lesson)."""
    if len(points) < 3 or points[0] == points[-1]:
        return points
    start, end = points[0], points[-1]
    import math

    for pl in polylines:
        if len(pl) < 2:
            continue
        for cand in (pl, list(reversed(pl))):
            first, last = cand[0], cand[-1]
            start_near_first = math.hypot(start[0] - first[0], start[1] - first[1]) < 8
            start_near_last = math.hypot(start[0] - last[0], start[1] - last[1]) < 8
            end_aligned = abs(end[0] - last[0]) < 8 or abs(end[0] - first[0]) < 8
            if start_near_first and end_aligned:
                return points + list(reversed(cand))
            if start_near_last and end_aligned:
                return points + cand
    return points


def rect_polygon(el: ET.Element, ctm=G.IDENTITY) -> tuple[Polygon | None, tuple[float, float, float, float]]:
    x = float(el.attrib.get("x", 0))
    y = float(el.attrib.get("y", 0))
    w = float(el.attrib.get("width", 0))
    h = float(el.attrib.get("height", 0))
    if w <= 0 or h <= 0:
        return None, (x, y, x, y)
    corners = G.apply_ctm(ctm, [(x, y), (x + w, y), (x + w, y + h), (x, y + h)])
    xs = [p[0] for p in corners]
    ys = [p[1] for p in corners]
    return Polygon(corners), (min(xs), min(ys), max(xs), max(ys))


def extract_shapes(svg: Path, clip_to_viewbox: bool = True) -> tuple[tuple[float, float, float, float], list[Shape]]:
    root = ET.parse(svg).getroot()
    css = parse_css(root)
    viewbox = G.read_viewbox(root)

    polylines: list[list[Point]] = [
        G.apply_ctm(ctm, G.parse_points(el.attrib["points"]))
        for el, ctm in G.iter_with_ctm(root)
        if G.tag_name(el) == "polyline" and el.attrib.get("points")
    ]

    shapes: list[Shape] = []
    pidx = 0
    for el, ctm in G.iter_with_ctm(root):
        name = G.tag_name(el)
        ref = el.attrib.get("id") or el.attrib.get("class") or f"{name}#{pidx}"
        style = element_style(el, css)
        if name == "path" and el.attrib.get("d"):
            for sub in G.parse_path_d(el.attrib["d"]):
                sub = close_open_path_with_polyline(G.apply_ctm(ctm, sub), polylines)
                poly = poly_from_points(sub)
                if poly is None:
                    continue
                shapes.append(Shape("path", ref, poly, poly.area, poly.bounds, style))
                pidx += 1
        elif name == "polygon" and el.attrib.get("points"):
            poly = poly_from_points(G.apply_ctm(ctm, G.parse_points(el.attrib["points"])))
            if poly is not None:
                shapes.append(Shape("polygon", ref, poly, poly.area, poly.bounds, style))
                pidx += 1
        elif name == "rect":
            poly, bounds = rect_polygon(el, ctm)
            if poly is not None:
                shapes.append(Shape("rect", ref, poly, poly.area, bounds, style))
                pidx += 1
        elif name in ("line", "polyline"):
            if name == "line":
                pts = G.apply_ctm(ctm, [
                    (float(el.attrib.get("x1", 0)), float(el.attrib.get("y1", 0))),
                    (float(el.attrib.get("x2", 0)), float(el.attrib.get("y2", 0))),
                ])
            else:
                pts = G.apply_ctm(ctm, G.parse_points(el.attrib.get("points", "")))
            xs = [p[0] for p in pts] or [0]
            ys = [p[1] for p in pts] or [0]
            bounds = (min(xs), min(ys), max(xs), max(ys))
            shapes.append(Shape(name, ref, None, 0.0, bounds, style))
            pidx += 1
        elif name in ("circle", "ellipse"):
            cx = float(el.attrib.get("cx", 0)); cy = float(el.attrib.get("cy", 0))
            rx = float(el.attrib.get("r", el.attrib.get("rx", 0)))
            ry = float(el.attrib.get("r", el.attrib.get("ry", 0)))
            if rx > 0 and ry > 0:
                ring = [(cx + rx * math.cos(math.tau * k / 48), cy + ry * math.sin(math.tau * k / 48))
                        for k in range(48)]
                poly = poly_from_points(G.apply_ctm(ctm, ring))
                if poly is not None:
                    shapes.append(Shape("circle", ref, poly, poly.area, poly.bounds, style))
                    pidx += 1

    if clip_to_viewbox:
        # drop shapes entirely OUTSIDE the visible viewBox (off-canvas other-panel/rogue elements);
        # keep anything that overlaps it. Matches a renderer clipping content to the viewport.
        vx, vy, vw, vh = viewbox
        mx, my = vw * 0.02, vh * 0.02

        def _overlaps(b):
            return not (b[2] < vx - mx or b[0] > vx + vw + mx or b[3] < vy - my or b[1] > vy + vh + my)

        shapes = [s for s in shapes if _overlaps(s.bounds)]
    return viewbox, shapes


def classify(shapes: list[Shape]) -> list[Shape]:
    contours = [s for s in shapes if s.kind in ("path", "polygon", "circle") and s.polygon is not None]
    if contours:
        max_area = max(s.area for s in contours)
        biggest = max(contours, key=lambda s: s.area)
        for s in contours:
            contained = any(
                o is not s and o.area > s.area * 1.8
                and o.polygon.buffer(0.05).contains(s.polygon.representative_point())
                for o in contours
            )
            bitten = any(
                o is not s and s.area < max_area * 0.25 and o.area > s.area * 1.8
                and (s.polygon.intersection(o.polygon).area / max(1.0, s.area)) > 0.10
                for o in contours
            )
            if s is biggest:
                s.role, s.reason = "outer_contour", "largest contour"
            elif contained:
                s.role, s.reason = "internal_cutout", "contained by a larger contour"
            elif bitten:
                s.role, s.reason = "internal_cutout", "edge socket/notch biting a larger contour"
            elif s.area >= max_area * 0.10:
                s.role, s.reason = "paintable_region", "large standalone contour"
            else:
                s.role, s.reason = "internal_cutout", "small contour (<10% of largest)"

    for s in shapes:
        if s.kind in ("path", "polygon", "circle"):
            continue
        fam = color_family(s.style.get("stroke") or s.style.get("fill"))
        dashed = is_dashed(s.style)
        if s.kind == "rect":
            if fam == "red":
                s.role, s.reason = "no_focal_motif_zone", "red dashed/solid rect = keep-clear, no recognizable motif"
            elif dashed:
                s.role, s.reason = "keep_clear_zone", "dashed overlay rect (confirm role)"
            else:
                s.role, s.reason = "keep_clear_zone", "overlay rect (confirm: keep-clear vs paintable sub-panel)"
        else:  # line / polyline
            if fam == "blue":
                s.role, s.reason = "visual_guide", "blue dashed line = sub-panel divider"
            else:
                s.role, s.reason = "visual_guide", "guide line/polyline"
    return shapes


ROLE_KEYS = {
    "outer_contour": "outer_contours",
    "paintable_region": "paintable_regions",
    "internal_cutout": "internal_cutouts",
    "keep_clear_zone": "keep_clear_zones",
    "visual_guide": "visual_guides",
}


def build_manifest_roles(shapes: list[Shape]) -> dict:
    def entry(s: Shape) -> dict:
        return {"ref": s.ref, "kind": s.kind, "bbox": [round(v, 2) for v in s.bounds],
                "area": round(s.area, 2), "reason": s.reason}

    roles = {k: [] for k in ("outer_contours", "paintable_regions", "internal_cutouts", "keep_clear_zones", "visual_guides")}
    no_focal: list[dict] = []
    for s in shapes:
        if s.role == "no_focal_motif_zone":
            no_focal.append(entry(s))
            roles["keep_clear_zones"].append(entry(s))
        elif s.role in ROLE_KEYS:
            roles[ROLE_KEYS[s.role]].append(entry(s))
    return roles, no_focal


def render_report(svg: Path, viewbox, shapes: list[Shape]) -> str:
    lines = [
        "# SVG geometry classification",
        "",
        f"Source: `{rel(svg)}`",
        f"viewBox: `{' '.join(str(round(v, 2)) for v in viewbox)}`",
        "",
        "| role | ref | kind | bbox (x0,y0,x1,y1) | area | reason |",
        "|---|---|---|---|---|---|",
    ]
    order = ["outer_contour", "paintable_region", "internal_cutout", "no_focal_motif_zone", "keep_clear_zone", "visual_guide", ""]
    for role in order:
        for s in [x for x in shapes if x.role == role]:
            bb = ",".join(str(round(v)) for v in s.bounds)
            lines.append(f"| {s.role or '(unclassified)'} | `{s.ref}` | {s.kind} | {bb} | {round(s.area)} | {s.reason} |")
    review = [s for s in shapes if "confirm" in s.reason or not s.role]
    if review:
        lines += ["", "## Confirm before generating", ""]
        for s in review:
            lines.append(f"- `{s.ref}` ({s.kind}) -> {s.role or 'UNCLASSIFIED'}: {s.reason}")
    return "\n".join(lines) + "\n"


def render_preview(viewbox, shapes: list[Shape], out: Path, max_w: int = 460) -> Path:
    """Human-confirmation render: panel body + red holes labelled, so the role
    classification can be eyeballed instead of read as a coordinate table."""
    min_x, min_y, box_w, box_h = viewbox
    scale = max_w / box_w
    W, H = max_w, max(1, round(box_h * scale))
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img, "RGBA")

    def tp(poly: Polygon) -> list[tuple[float, float]]:
        return [((x - min_x) * scale, (y - min_y) * scale) for x, y in poly.exterior.coords]

    # body first (outer contour + paintable), then holes on top, then guides
    for s in shapes:
        if s.polygon is None:
            continue
        if s.role in ("outer_contour", "paintable_region"):
            d.polygon(tp(s.polygon), fill=(133, 183, 235, 255), outline=(20, 30, 60, 255), width=2)
    cut_n = 0
    for s in shapes:
        if s.polygon is None:
            continue
        if s.role == "internal_cutout":
            cut_n += 1
            d.polygon(tp(s.polygon), fill=(226, 75, 74, 235), outline=(120, 20, 20, 255), width=1)
            cx, cy = s.polygon.representative_point().coords[0]
            d.text(((cx - min_x) * scale - 3, (cy - min_y) * scale - 6), str(cut_n), fill=(255, 255, 255, 255))
        elif s.role in ("keep_clear_zone", "no_focal_motif_zone"):
            d.polygon(tp(s.polygon), fill=(245, 158, 39, 90), outline=(133, 79, 11, 255), width=2)
    for s in shapes:
        if s.role == "visual_guide" and s.kind in ("line", "polyline"):
            x0, y0, x1, y1 = s.bounds
            d.line([((x0 - min_x) * scale, (y0 - min_y) * scale), ((x1 - min_x) * scale, (y1 - min_y) * scale)],
                   fill=(40, 110, 200, 200), width=1)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


def render_map(viewbox, shapes: list[Shape], out: Path, max_w: int = 760) -> Path:
    """Negative-space composition map for the image model: flat neutral body,
    white holes, white background. Defines silhouette + openings ONLY; style
    comes from the attached references. No labels, no CAD cues."""
    min_x, min_y, box_w, box_h = viewbox
    scale = max_w / box_w
    W, H = max_w, max(1, round(box_h * scale))
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img, "RGBA")

    def tp(poly: Polygon) -> list[tuple[float, float]]:
        return [((x - min_x) * scale, (y - min_y) * scale) for x, y in poly.exterior.coords]

    for s in shapes:
        if s.polygon is not None and s.role in ("outer_contour", "paintable_region"):
            d.polygon(tp(s.polygon), fill=(208, 210, 214, 255), outline=(40, 45, 55, 255), width=2)
    for s in shapes:
        if s.polygon is not None and s.role == "internal_cutout":
            d.polygon(tp(s.polygon), fill=(255, 255, 255, 255), outline=(40, 45, 55, 255), width=2)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


def write_manifest(task_dir: Path, svg: Path, roles: dict, no_focal: list) -> Path:
    mpath = task_dir / "template-manifest.json"
    manifest = json.loads(mpath.read_text()) if mpath.exists() else json.loads((ROOT / "tasks/_template/template-manifest.json").read_text())
    manifest["template_svg"] = rel(svg)
    manifest["geometry_roles"] = roles
    manifest["no_focal_motif_zones"] = no_focal
    manifest["status"] = "auto-classified-confirm-before-generation"
    manifest.setdefault("notes", [])
    manifest["notes"] = [
        "Auto-classified by scripts/svg_classify.py. Eyeball the geometry report and",
        "confirm cutouts vs paintable and keep-clear roles before generating.",
        "Set status to 'approved' once a human has confirmed roles.",
    ]
    mpath.write_text(json.dumps(manifest, indent=2) + "\n")
    return mpath


REQUIRED_ROLES = ("outer_contours",)


def check_manifest(mpath: Path) -> int:
    if not mpath.exists():
        print(f"FAIL: manifest not found: {rel(mpath)}")
        return 1
    m = json.loads(mpath.read_text())
    status = m.get("status", "")
    roles = m.get("geometry_roles", {})
    problems = []
    if status == "draft-fill-before-generation" or not status:
        problems.append("status is still draft/empty (template never classified)")
    for key in REQUIRED_ROLES:
        if not roles.get(key):
            problems.append(f"geometry_roles.{key} is empty (no outer contour identified)")
    if not any(roles.get(k) for k in roles):
        problems.append("all geometry_roles are empty")
    if problems:
        print(f"FAIL ({rel(mpath)}):")
        for p in problems:
            print(f"  - {p}")
        return 1
    n = {k: len(v) for k, v in roles.items() if v}
    print(f"PASS ({rel(mpath)}): status='{status}', roles={n}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("svg", nargs="?", type=Path, help="SVG template to classify")
    ap.add_argument("--task", type=Path, help="task dir whose template-manifest.json to fill")
    ap.add_argument("--write-manifest", action="store_true", help="write classification into the task manifest")
    ap.add_argument("--report", type=Path, help="write the markdown report here")
    ap.add_argument("--json", action="store_true", help="print classification as JSON")
    ap.add_argument("--check", type=Path, help="gate a template-manifest.json (exit 1 if unfilled)")
    ap.add_argument("--preview", type=Path, help="render a labelled role-preview PNG here")
    ap.add_argument("--map", dest="negmap", type=Path, help="render a negative-space composition map (for the image model) here")
    args = ap.parse_args()

    if args.check:
        return check_manifest(args.check if args.check.is_absolute() else ROOT / args.check)

    if not args.svg:
        ap.error("provide an SVG to classify, or --check a manifest")
    svg = args.svg if args.svg.is_absolute() else ROOT / args.svg
    viewbox, shapes = extract_shapes(svg)
    shapes = classify(shapes)
    roles, no_focal = build_manifest_roles(shapes)

    if args.json:
        print(json.dumps({"viewbox": viewbox, "geometry_roles": roles, "no_focal_motif_zones": no_focal}, indent=2))
    else:
        report = render_report(svg, viewbox, shapes)
        print(report)
        if args.report:
            rp = args.report if args.report.is_absolute() else ROOT / args.report
            rp.parent.mkdir(parents=True, exist_ok=True)
            rp.write_text(report)
            print(f"report -> {rel(rp)}")

    if args.write_manifest:
        task = args.task or svg.parents[1]
        mpath = write_manifest(task, svg, roles, no_focal)
        print(f"manifest -> {rel(mpath)}")

    if args.preview:
        pp = args.preview if args.preview.is_absolute() else ROOT / args.preview
        render_preview(viewbox, shapes, pp)
        print(f"preview -> {rel(pp)}")

    if args.negmap:
        mp = args.negmap if args.negmap.is_absolute() else ROOT / args.negmap
        render_map(viewbox, shapes, mp)
        print(f"map -> {rel(mp)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
