#!/usr/bin/env python3
"""Build experiment-1 geometry assets from the frozen princess-n02 template SVG.

Single source of truth: tasks/geometry-evidentiary-princess-n02/source/template.svg
(the SAME frozen file used by the evidentiary run). Reuses scripts/svg_classify.py
for parsing/role-classification (do NOT hand-author geometry) and mirrors
scripts/controlnet_sdxl_gen.py's sizing convention (src_rect = bbox of shapes
whose role is outer_contour|paintable_region, no --bbox given -> whole-body crop).

IMPORTANT geometry note (verified by direct SVG render, see assets/checks/ +
the builder report): svg_classify's heuristic role assignment for THIS
template labels the *inset bleed/safe-area guide* path (class "st5", yellow
#ffdb55) as "outer_contour" and the *true arch/dome silhouette* path (class
"st1", green #39b54a) as "internal_cutout" ("contained by a larger contour").
Mirroring controlnet_sdxl_gen.py's sizing means the render canvas top edge is
st5's top (y=179.08 SVG units), which crops ~74 SVG units (~1.9%) off the true
arch peak (st1's top, y=105.25) -- visible in assets/checks/overlay_silhouette.png.
This is a pre-existing tool limitation (already flagged in
tasks/geometry-evidentiary-princess-n02/DIAGNOSIS-attempt2.md finding B), not
introduced here; flagged, not silently fixed, per the "do not hand-author
geometry" constraint.

Bigger finding: st1 (the "internal_cutout" the brief names as the door-socket)
does NOT spatially overlap the embedded raster <image> element (measured: zero
pixel overlap -- st1 bbox y:105-759 SVG units vs the raster's own placement
rect y:1572-2378 SVG units). st1 is actually the top arch/dome silhouette
edge, not a socket for the door raster. socket_mask.png in this build is
therefore keyed to the RASTER'S OWN measured placement rect (unambiguous,
extracted straight from the <image> transform/width/height), matching how
SYNTHESIS.md/advisor-brief.md describe "the socket" ("an embedded door raster
that must survive untouched"). st1's own polygon is still rasterized
separately as st1_zone_mask.png for traceability/reference. See the builder's
final report for the full discrepancy writeup.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
import svg_classify as C  # noqa: E402
import svg_geometry as G  # noqa: E402

SVG = ROOT / "tasks/geometry-evidentiary-princess-n02/source/template.svg"
EXP = ROOT / "tasks/geometry-adherence-solutions/experiment-1"
ASSETS = EXP / "assets"
CHECKS = ASSETS / "checks"
STYLE_REFS = [
    ROOT / "tasks/geometry-evidentiary-princess-n02/refs/princess style 01.png",
    ROOT / "tasks/geometry-evidentiary-princess-n02/refs/princess style 02.png",
]

WIDTH = 1024          # mirrors controlnet_sdxl_gen.py --width default
STROKE = 4             # mirrors controlnet_sdxl_gen.py --stroke default
SOCKET_REF = "st1"     # class the brief names as the door-socket path id
INIT_FILL = (222, 213, 199)  # neutral light-warm-grey, surround-matched to white paintable
SOCKET_RGBA = ASSETS / "door_socket_rgba.png"  # Amendment 1: frozen arch matte (build_socket_matte.py),
                                                 # ALWAYS the canonical assets/ path (resolution-independent
                                                 # native raster), regardless of --outdir
SOCKET_DILATE_PX = 1  # Amendment 1: arch footprint dilated +1px at working res


def round8(v) -> int:
    v = int(round(v))
    return max(8, v - (v % 8))


def compute_src_rect(shapes):
    body = [s for s in shapes if s.polygon is not None and s.role in ("outer_contour", "paintable_region")]
    x0 = min(s.bounds[0] for s in body)
    y0 = min(s.bounds[1] for s in body)
    x1 = max(s.bounds[2] for s in body)
    y1 = max(s.bounds[3] for s in body)
    return x0, y0, x1 - x0, y1 - y0


def make_mapper(src_rect, W, H):
    min_x, min_y, box_w, box_h = src_rect
    sx = W / box_w
    sy = H / box_h

    def f(x, y):
        return ((x - min_x) * sx, (y - min_y) * sy)

    return f, sx, sy


def load_socket_alpha_native() -> np.ndarray:
    """Amendment 1: the frozen arch matte's native-resolution alpha channel
    (boolean, >127), source of truth for the socket exclusion shape. Run
    build_socket_matte.py first if missing."""
    if not SOCKET_RGBA.exists():
        raise SystemExit(f"missing {SOCKET_RGBA} -- run build_socket_matte.py first (Amendment 1)")
    im = Image.open(SOCKET_RGBA).convert("RGBA")
    a = np.asarray(im.split()[-1])
    return a > 127


def build_socket_arch_mask(rect_px, W, H, dilate=SOCKET_DILATE_PX) -> Image.Image:
    """Amendment 1: project the matte's native alpha footprint (the ARCH
    shape, not the enclosing rect) through the shared placement transform
    onto a WxH canvas, NEAREST-resized (keeps it strictly binary, matching
    the "0px feather / NEAREST binary resize" mask convention) then dilated
    +dilate px. rect_px is the raster's own placement rect (x0,y0,x1,y1),
    used only to size/position the projection -- NOT the mask shape itself."""
    alpha_native = load_socket_alpha_native()
    x0, y0, x1, y1 = rect_px
    tw, th = max(1, round(x1 - x0)), max(1, round(y1 - y0))
    m_native = Image.fromarray((alpha_native * 255).astype(np.uint8), "L")
    m_resized = m_native.resize((tw, th), Image.NEAREST)
    canvas = Image.new("L", (W, H), 0)
    canvas.paste(m_resized, (round(x0), round(y0)))
    if dilate > 0:
        canvas = canvas.filter(ImageFilter.MaxFilter(2 * dilate + 1))
    return canvas


def rasterize_geometry(W, H):
    """Reusable, resolution-agnostic geometry rasterization: re-derives shapes +
    src_rect fresh from SVG (same convention as compute_src_rect/make_mapper)
    and maps everything to the given WxH. Used by build_assets.main() for the
    default working resolution AND by composite_back.py for an arbitrary
    candidate resolution (e.g. after an upscale pass), so masks/placement stay
    exactly registered regardless of pixel size.

    Returns: silhouette, holes_excl_st1, st1_zone (PIL "L" images), socket_rect_px
    (x0,y0,x1,y1 floats, the raster's OWN placement rect -- a sizing/search-window
    reference only, NOT the paint-exclusion shape), socket_arch_mask (PIL "L",
    Amendment 1: the actual arch-shaped exclusion, +1px dilated), shapes
    (classified), src_rect.
    """
    viewbox, shapes0 = C.extract_shapes(SVG)
    shapes = C.classify(shapes0)
    src_rect = compute_src_rect(shapes)
    f, sx, sy = make_mapper(src_rect, W, H)

    silhouette = fill_mask(shapes, W, H, f, ("outer_contour", "paintable_region"))
    st1_zone = fill_mask(shapes, W, H, f, ("internal_cutout",), ref_filter=SOCKET_REF)
    holes_excl_st1 = fill_mask(shapes, W, H, f, ("internal_cutout",), ref_exclude=SOCKET_REF)

    _, _, rect_svg = extract_door_raster(SVG)
    x0s, y0s, x1s, y1s = rect_svg
    (px0, py0) = f(x0s, y0s)
    (px1, py1) = f(x1s, y1s)
    socket_rect_px = (px0, py0, px1, py1)
    socket_arch_mask = build_socket_arch_mask(socket_rect_px, W, H)

    return silhouette, holes_excl_st1, st1_zone, socket_rect_px, socket_arch_mask, shapes, src_rect


def fill_mask(shapes, W, H, f, roles, ref_filter=None, ref_exclude=None) -> Image.Image:
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    for s in shapes:
        if s.polygon is None or s.role not in roles:
            continue
        if ref_filter is not None and s.ref != ref_filter:
            continue
        if ref_exclude is not None and s.ref == ref_exclude:
            continue
        pts = [f(x, y) for x, y in s.polygon.exterior.coords]
        d.polygon(pts, fill=255)
    return m


def draw_control_lines(shapes, W, H, f, stroke) -> Image.Image:
    """white-on-black canny-style lineart: outer contour + paintable region edge
    + every internal_cutout boundary (which includes st1's boundary)."""
    ctrl = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(ctrl)
    for s in shapes:
        if s.polygon is None or s.role not in ("outer_contour", "paintable_region", "internal_cutout"):
            continue
        pts = [f(x, y) for x, y in s.polygon.exterior.coords]
        d.line(pts + [pts[0]], fill=255, width=stroke, joint="curve")
    return ctrl


def extract_door_raster(svg_path: Path):
    """Find the single embedded <image>, decode its base64 payload, and compute
    its placement rect in SVG user units from its own transform + width/height
    (NOT from any classify() role -- this is independent, direct XML parsing)."""
    ns = {"xlink": "http://www.w3.org/1999/xlink"}
    root = ET.parse(svg_path).getroot()
    images = [el for el in root.iter() if G.tag_name(el) == "image"]
    if len(images) != 1:
        raise SystemExit(f"expected exactly 1 <image> element, found {len(images)}")
    el = images[0]
    href = el.attrib.get("{http://www.w3.org/1999/xlink}href") or el.attrib.get("href")
    m = re.match(r"data:image/(?P<fmt>[\w.+-]+);base64,(?P<b64>.+)", href, re.S)
    if not m:
        raise SystemExit("embedded <image> href is not a base64 data URI")
    raw = base64.b64decode(m.group("b64"))
    w = float(el.attrib.get("width", 0))
    h = float(el.attrib.get("height", 0))
    mat = G.parse_transform(el.attrib.get("transform", ""))
    (x0, y0), (x1, y1) = G.apply_ctm(mat, [(0, 0), (w, h)])
    rect_svg = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
    return raw, m.group("fmt"), rect_svg


def overlay(base_rgb: Image.Image, mask: Image.Image, color, alpha=140) -> Image.Image:
    ov = base_rgb.convert("RGBA")
    tint = Image.new("RGBA", ov.size, color + (0,))
    a = mask.point(lambda v: alpha if v > 127 else 0)
    tint.putalpha(a)
    return Image.alpha_composite(ov, tint)


def px_count(mask: Image.Image) -> int:
    return int((np.asarray(mask) > 127).sum())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=WIDTH)
    ap.add_argument("--outdir", default="assets", help="asset output subdir under experiment-1 (default 'assets')")
    a = ap.parse_args()
    W0 = a.width

    ASSETS = EXP / a.outdir  # shadow the module default when --outdir given; door_socket_rgba.png
                               # (the frozen matte) is still always read from the canonical SOCKET_RGBA path
    CHECKS = ASSETS / "checks"
    ASSETS.mkdir(parents=True, exist_ok=True)
    CHECKS.mkdir(parents=True, exist_ok=True)

    viewbox, shapes0 = C.extract_shapes(SVG)
    shapes = C.classify(shapes0)

    src_rect = compute_src_rect(shapes)
    _, _, box_w, box_h = src_rect
    W = round8(W0)
    H = round8(W * box_h / box_w)
    f, sx, sy = make_mapper(src_rect, W, H)

    # ---- core masks -------------------------------------------------
    silhouette = fill_mask(shapes, W, H, f, ("outer_contour", "paintable_region"))
    st1_zone = fill_mask(shapes, W, H, f, ("internal_cutout",), ref_filter=SOCKET_REF)
    holes_excl_st1 = fill_mask(shapes, W, H, f, ("internal_cutout",), ref_exclude=SOCKET_REF)

    # ---- embedded door raster (independent of classify() roles) -----
    raw_bytes, fmt, rect_svg = extract_door_raster(SVG)
    door_path = ASSETS / f"door_socket.{('png' if fmt == 'png' else fmt)}"
    door_path.write_bytes(raw_bytes)
    door_img = Image.open(door_path)
    native_w, native_h = door_img.size

    x0s, y0s, x1s, y1s = rect_svg
    (px0, py0) = f(x0s, y0s)
    (px1, py1) = f(x1s, y1s)
    placement_px = [round(px0, 2), round(py0, 2), round(px1, 2), round(py1, 2)]

    # Amendment 1 (pre-run advisor correction): socket exclusion = the door
    # raster's ARCH-shaped alpha footprint (frozen matte, +1px dilate), NOT
    # the enclosing rect -- rect corners are real wall and must stay paintable.
    socket_mask = build_socket_arch_mask((px0, py0, px1, py1), W, H)
    outdir_rgba = ASSETS / "door_socket_rgba.png"
    if outdir_rgba.resolve() != SOCKET_RGBA.resolve():
        shutil.copyfile(SOCKET_RGBA, outdir_rgba)

    placement = {
        "svg_viewbox": list(viewbox),
        "src_rect_svg_units": list(src_rect),
        "working_resolution": [W, H],
        "transform": {"note": "px = (svg_x - src_rect.min_x) * (W/box_w), (svg_y - src_rect.min_y) * (H/box_h)",
                      "sx": sx, "sy": sy, "min_x": src_rect[0], "min_y": src_rect[1]},
        "placement_svg_units": [round(v, 4) for v in rect_svg],
        "placement_px": placement_px,
        "native_raster_size_px": [native_w, native_h],
        "source_element": {"width": native_w, "height": native_h, "format": fmt},
        "note": "rect derived directly from the <image> element's own transform="
                "translate()+scale() and width/height attributes -- independent of "
                "svg_classify() role assignment. Does NOT match st1's bbox "
                "(103.38,105.25 -> 1747.48,759.27 SVG units, the top arch/dome); "
                "see build_assets.py module docstring / builder report.",
        "amendment_1": "this rect is now a SIZING/SEARCH-WINDOW reference only. The "
                        "actual socket_mask.png / paintable exclusion / init-canvas "
                        "neutral fill is the ARCH-shaped frozen matte alpha footprint "
                        "(door_socket_rgba.png, built by build_socket_matte.py) "
                        "projected through this same rect + dilated +1px, NOT this "
                        "rectangle -- see PARAMS.md Amendment 1.",
    }
    (ASSETS / "door_socket_placement.json").write_text(json.dumps(placement, indent=2) + "\n")

    # ---- paintable masks ---------------------------------------------
    sil_a = np.asarray(silhouette) > 127
    hol_a = np.asarray(holes_excl_st1) > 127
    sock_a = np.asarray(socket_mask) > 127
    st1_a = np.asarray(st1_zone) > 127

    p1 = sil_a & ~hol_a & ~sock_a
    p2 = sil_a & ~sock_a
    Image.fromarray((p1 * 255).astype(np.uint8)).save(ASSETS / "paintable_P1.png")
    Image.fromarray((p2 * 255).astype(np.uint8)).save(ASSETS / "paintable_P2.png")

    silhouette.save(ASSETS / "silhouette_mask.png")
    holes_excl_st1.save(ASSETS / "holes_mask.png")
    socket_mask.save(ASSETS / "socket_mask.png")
    st1_zone.save(ASSETS / "st1_zone_mask.png")

    # ---- control map ---------------------------------------------------
    ctrl = draw_control_lines(shapes, W, H, f, STROKE)
    # Amendment 1: draw the socket ARCH outline (matte alpha edge), not the
    # rect -- an intentional frame around the door art, not an accidental gap.
    sock_edge = socket_mask.filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v > 10 else 0)
    sock_edge = sock_edge.filter(ImageFilter.MaxFilter(2 * STROKE + 1))
    ctrl = ImageChops.lighter(ctrl, sock_edge)
    ctrl.convert("RGB").save(ASSETS / "control_canny.png")

    # ---- init canvas -----------------------------------------------
    # Amendment 1: neutral fill ONLY inside the arch footprint; the rest of
    # the old rect (corners) is now real paintable white canvas.
    init = Image.new("RGB", (W, H), (255, 255, 255))
    init_arr = np.asarray(init).copy()
    init_arr[sock_a] = INIT_FILL
    init = Image.fromarray(init_arr)
    init.save(ASSETS / "init_canvas.png")

    # ---- transform.json --------------------------------------------
    transform = {
        "svg_source": str(SVG.relative_to(ROOT)),
        "svg_viewbox": list(viewbox),
        "src_rect_svg_units": {"min_x": src_rect[0], "min_y": src_rect[1],
                                "box_w": src_rect[2], "box_h": src_rect[3]},
        "src_rect_derivation": "bbox union of shapes whose svg_classify role is "
                                "outer_contour|paintable_region (mirrors "
                                "controlnet_sdxl_gen.py main() with no --bbox given)",
        "working_resolution": {"W": W, "H": H},
        "mapping": "px_x = (svg_x - src_rect.min_x) * (W / src_rect.box_w); "
                   "px_y = (svg_y - src_rect.min_y) * (H / src_rect.box_h)",
        "sx": sx, "sy": sy,
        "stroke_px": STROKE,
        "notes": [
            "st5 (yellow #ffdb55, classify role=outer_contour) is used for the "
            "silhouette top edge per controlnet_sdxl_gen.py convention; the TRUE "
            "physical arch peak is st1 (green #39b54a, classify role=internal_cutout) "
            "which pokes ~74 SVG units (~1.9% of panel height) above st5's top -- "
            "see assets/checks/overlay_silhouette.png for the visible crop.",
            "socket_mask.png / paintable_P1 / paintable_P2 / init_canvas / "
            "control_canny's socket outline are keyed to the embedded raster's "
            "OWN measured placement (door_socket_placement.json) for SIZING, "
            "not to st1's polygon -- but Amendment 1 (see PARAMS.md) supersedes "
            "the earlier full-rect socket shape: the actual exclusion is the "
            "ARCH-shaped frozen matte alpha footprint (door_socket_rgba.png) "
            "projected through that rect + dilated +1px. st1_zone_mask.png is "
            "the literal st1 rasterization, kept for traceability; it does not "
            "overlap the raster placement.",
        ],
    }
    (ASSETS / "transform.json").write_text(json.dumps(transform, indent=2) + "\n")

    # ---- style_ref.png (side-by-side, longest side <= 1568) ----------
    imgs = [Image.open(p).convert("RGB") for p in STYLE_REFS]
    target_h = 1400
    scaled = []
    for im in imgs:
        s = target_h / im.height
        scaled.append(im.resize((round(im.width * s), target_h), Image.LANCZOS))
    gap = 24
    total_w = sum(im.width for im in scaled) + gap
    longest = max(total_w, target_h)
    if longest > 1568:
        scale = 1568 / longest
        target_h = round(target_h * scale)
        scaled = [im.resize((round(im.width * scale), target_h), Image.LANCZOS) for im in scaled]
        total_w = sum(im.width for im in scaled) + gap
    canvas = Image.new("RGB", (total_w, target_h), (255, 255, 255))
    x = 0
    for im in scaled:
        canvas.paste(im, (x, 0))
        x += im.width + gap
    canvas.save(ASSETS / "style_ref.png")

    # ---- rendered template (for overlay checks) ------------------------
    import subprocess
    rendered = CHECKS / "template_render.png"
    subprocess.run(["rsvg-convert", "-w", str(W), "-h", str(H), str(SVG), "-o", str(rendered)], check=True)
    base_rgb = Image.open(rendered).convert("RGB")

    overlay(base_rgb, silhouette, (0, 140, 255)).convert("RGB").save(CHECKS / "overlay_silhouette.png")
    overlay(base_rgb, holes_excl_st1, (255, 40, 40)).convert("RGB").save(CHECKS / "overlay_holes.png")
    overlay(base_rgb, socket_mask, (255, 160, 0)).convert("RGB").save(CHECKS / "overlay_socket.png")
    overlay(base_rgb, st1_zone, (170, 0, 220)).convert("RGB").save(CHECKS / "overlay_st1_zone.png")
    overlay(base_rgb, ctrl, (0, 200, 0), alpha=200).convert("RGB").save(CHECKS / "overlay_control.png")

    # door_socket overlay: paste the raster at its computed placement onto the render
    door_check = base_rgb.copy()
    door_resized = door_img.convert("RGBA").resize((round(px1 - px0), round(py1 - py0)), Image.LANCZOS)
    door_check.paste(door_resized, (round(px0), round(py0)), door_resized)
    door_check.save(CHECKS / "overlay_door_socket.png")

    # ---- pixel-count report -------------------------------------------
    report_lines = [
        "# experiment-1 asset mask pixel-count report",
        "",
        f"SVG: {SVG.relative_to(ROOT)}",
        f"viewBox: {viewbox}",
        f"src_rect (SVG units): {src_rect}",
        f"working resolution: {W}x{H}  (aspect {W/H:.4f})",
        "",
        "| asset | px count | % of canvas |",
        "|---|---|---|",
    ]
    canvas_px = W * H
    for name, m in [("silhouette_mask", silhouette), ("holes_mask (excl st1)", holes_excl_st1),
                     ("socket_mask (arch footprint +1px, Amendment 1)", socket_mask), ("st1_zone_mask", st1_zone),
                     ("paintable_P1", Image.fromarray((p1 * 255).astype(np.uint8))),
                     ("paintable_P2", Image.fromarray((p2 * 255).astype(np.uint8)))]:
        n = px_count(m)
        report_lines.append(f"| {name} | {n} | {100*n/canvas_px:.2f}% |")

    report_lines += [
        "",
        "## per-shape SVG-unit areas (svg_classify, cross-check vs "
        "tasks/geometry-evidentiary-princess-n02/svg-geometry-report.md)",
        "",
        "| role | ref | area (svg units^2) | bbox |",
        "|---|---|---|---|",
    ]
    for s in shapes:
        if s.polygon is None:
            continue
        report_lines.append(f"| {s.role} | {s.ref} | {s.area:.1f} | {tuple(round(v,2) for v in s.bounds)} |")

    report_lines += [
        "",
        "## discrepancy: st1 vs embedded-raster placement",
        f"- st1_zone bbox (SVG units): {[round(v,2) for v in [s.bounds for s in shapes if s.ref=='st1'][0]]}",
        f"- door raster placement (SVG units): {[round(v,2) for v in rect_svg]}",
        f"- overlap area (SVG units^2): "
        f"{max(0, min([s.bounds for s in shapes if s.ref=='st1'][0][2], rect_svg[2]) - max([s.bounds for s in shapes if s.ref=='st1'][0][0], rect_svg[0])) * max(0, min([s.bounds for s in shapes if s.ref=='st1'][0][3], rect_svg[3]) - max([s.bounds for s in shapes if s.ref=='st1'][0][1], rect_svg[1])):.1f}",
        "-> zero/near-zero overlap confirmed; socket_mask.png uses the raster's own "
        "placement, not st1. See build_assets.py module docstring.",
    ]
    (CHECKS / "mask_report.txt").write_text("\n".join(report_lines) + "\n")

    print(f"[build_assets] W={W} H={H} src_rect={src_rect}")
    print(f"[build_assets] door raster native={native_w}x{native_h} placement_svg={rect_svg} placement_px={placement_px}")
    print(f"[build_assets] wrote assets to {ASSETS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
