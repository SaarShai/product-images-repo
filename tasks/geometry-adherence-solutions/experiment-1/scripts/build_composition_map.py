#!/usr/bin/env python3
"""Amendment 4 (round 2, both advisors converged): composition control map.

Round-1 contour-only lineart gave the model no interior scaffold -> content
collapsed to flat washes despite 100% geometry adherence. Round 2: trace
SELECTIVE structural edges (tower silhouettes, roofs, window rows, gate arch
-- NOT texture/foliage/paper-grain/speckle) from the frozen frontier exemplar
outset-c1 raw.png, register per-axis into the 640x1544 body (corner-to-corner
stretch, sx~0.833 sy~1.122 -- NOT aspect-preserving, PARAMS.md is explicit),
clip to paintable_P1 eroded -2px (drops strokes landing in holes/socket/
outside), then re-add the authoritative SVG boundary strokes ON TOP (contour/
cutouts/fold-band/arch -- reuses build_assets.draw_control_lines() for the
first three, extended for the fold band + Amendment-1 arch edge).

Saves assets-640/control_composition.png. Does NOT touch control_canny.png
(round-1 asset, left untouched).

Run: /usr/bin/python3 tasks/geometry-adherence-solutions/experiment-1/scripts/build_composition_map.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
ROOT = EXP.parents[2]
sys.path.insert(0, str(HERE))
import build_assets as BA  # noqa: E402 (reuse SVG parsing / draw_control_lines / overlay -- no duplication)

ASSETS = EXP / "assets-640"
CHECKS = ASSETS / "checks"
EXEMPLAR = ROOT / "tasks/geometry-evidentiary-princess-n02/experiments-outset/outset-c1/raw.png"

W, H = 640, 1544
BOUNDARY_STROKE = 4   # contour/cutouts/fold-band/arch
INTERIOR_STROKE = 2   # traced structural edges from the exemplar
ERODE_PX = 2          # paintable_P1 erosion for the clip
FOLD_ROLE = "no_focal_motif_zone"  # st3 -- the "fold" band the card names


def register_exemplar():
    """Per-axis rescale, corner-to-corner STRETCH (not aspect-preserving --
    Amendment 4 explicit sx~0.833 sy~1.122)."""
    im = Image.open(EXEMPLAR).convert("RGB")
    ow, oh = im.size
    sx, sy = W / ow, H / oh
    resized = im.resize((W, H), Image.LANCZOS)
    return np.asarray(resized), sx, sy


def selective_canny(rgb: np.ndarray):
    """Structural edges only: bilateral+median pre-blur kills stone-texture/
    paper-grain, high thresholds keep silhouettes/rooflines/window
    rows/gate arch; small connected-component filter drops residual
    speckle fragments. Returns (raw_canny, cleaned) both uint8 0/255."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    smoothed = cv2.bilateralFilter(gray, d=9, sigmaColor=60, sigmaSpace=60)
    smoothed = cv2.medianBlur(smoothed, 5)
    canny = cv2.Canny(smoothed, threshold1=80, threshold2=160)

    n, labels, stats, _ = cv2.connectedComponentsWithStats(canny, connectivity=8)
    cleaned = np.zeros_like(canny)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= 8:  # drop 1-7px speckle fragments
            cleaned[labels == i] = 255
    cleaned = cv2.dilate(cleaned, np.ones((2, 2), np.uint8), iterations=1)  # ~INTERIOR_STROKE width
    return canny, cleaned


def erode_bool(mask_img: Image.Image, px: int) -> np.ndarray:
    m8 = (np.asarray(mask_img) > 127).astype(np.uint8) * 255
    if px <= 0:
        return m8 > 127
    eroded = cv2.erode(m8, np.ones((2 * px + 1, 2 * px + 1), np.uint8), iterations=1)
    return eroded > 127


def svg_boundary_layer(shapes, f) -> Image.Image:
    """Reuses build_assets.draw_control_lines() (contour/paintable_region/
    internal_cutout) then adds the fold band (st3) + Amendment-1 arch edge --
    the two additions round 2 asks for that round-1's control_canny didn't
    carry (fold) or carried at rect-vs-arch mismatch (arch, now consistent)."""
    layer = BA.draw_control_lines(shapes, W, H, f, BOUNDARY_STROKE)  # contour/cutouts, 4px
    d = ImageDraw.Draw(layer)
    for s in shapes:
        if s.polygon is None or s.role != FOLD_ROLE:
            continue
        pts = [f(x, y) for x, y in s.polygon.exterior.coords]
        d.line(pts + [pts[0]], fill=255, width=BOUNDARY_STROKE, joint="curve")

    socket_mask = Image.open(ASSETS / "socket_mask.png").convert("L")
    sock_edge = socket_mask.filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v > 10 else 0)
    sock_edge = sock_edge.filter(ImageFilter.MaxFilter(2 * BOUNDARY_STROKE + 1))
    return Image.fromarray(np.maximum(np.asarray(layer), np.asarray(sock_edge)))


def main() -> int:
    CHECKS.mkdir(parents=True, exist_ok=True)

    exemplar_rgb, sx, sy = register_exemplar()
    raw_canny, trace = selective_canny(exemplar_rgb)

    paintable_p1 = Image.open(ASSETS / "paintable_P1.png").convert("L")
    clip = erode_bool(paintable_p1, ERODE_PX)
    trace_clipped = np.where(clip, trace, 0).astype(np.uint8)

    viewbox, shapes0 = BA.C.extract_shapes(BA.SVG)
    shapes = BA.C.classify(shapes0)
    src_rect = BA.compute_src_rect(shapes)
    f, _, _ = BA.make_mapper(src_rect, W, H)
    svg_layer = svg_boundary_layer(shapes, f)

    final = Image.fromarray(np.maximum(trace_clipped, np.asarray(svg_layer)))
    final.convert("RGB").save(ASSETS / "control_composition.png")

    # ---- intermediates (evidence) ----
    Image.fromarray(raw_canny).save(CHECKS / "composition_canny_raw.png")
    Image.fromarray(trace).save(CHECKS / "composition_canny_cleaned.png")
    Image.fromarray(trace_clipped).save(CHECKS / "composition_canny_clipped.png")

    # ---- construction-claim check: any clipped-trace px land in fold/keep-clear? ----
    fold_mask = np.zeros((H, W), dtype=bool)
    keepclear_mask = np.zeros((H, W), dtype=bool)
    m_fold = Image.new("L", (W, H), 0)
    d_fold = ImageDraw.Draw(m_fold)
    m_kc = Image.new("L", (W, H), 0)
    d_kc = ImageDraw.Draw(m_kc)
    for s in shapes:
        if s.polygon is None:
            continue
        if s.role == FOLD_ROLE:
            d_fold.polygon([f(x, y) for x, y in s.polygon.exterior.coords], fill=255)
        elif s.role == "keep_clear_zone":
            d_kc.polygon([f(x, y) for x, y in s.polygon.exterior.coords], fill=255)
    fold_mask = np.asarray(m_fold) > 127
    keepclear_mask = np.asarray(m_kc) > 127
    trace_bool = trace_clipped > 0
    fold_stray_px = int((trace_bool & fold_mask).sum())
    keepclear_stray_px = int((trace_bool & keepclear_mask).sum())

    # ---- overlay checks ----
    rendered = CHECKS / "template_render.png"
    if not rendered.exists():
        subprocess.run(["rsvg-convert", "-w", str(W), "-h", str(H), str(BA.SVG), "-o", str(rendered)], check=True)
    base_rgb = Image.open(rendered).convert("RGB").resize((W, H))
    BA.overlay(base_rgb, final, (0, 220, 0), alpha=200).convert("RGB").save(
        CHECKS / "overlay_composition_over_template.png")

    exemplar_img = Image.fromarray(exemplar_rgb)
    BA.overlay(exemplar_img, final, (255, 0, 200), alpha=180).convert("RGB").save(
        CHECKS / "overlay_composition_over_outset_c1.png")

    print(f"[build_composition_map] exemplar={EXEMPLAR.name} native={Image.open(EXEMPLAR).size} "
          f"registered {W}x{H} sx={sx:.4f} sy={sy:.4f}")
    print(f"[build_composition_map] raw_canny_px={int((raw_canny > 0).sum())} "
          f"cleaned_px={int((trace > 0).sum())} clipped_px={int(trace_bool.sum())}")
    print(f"[build_composition_map] construction check: fold_stray_px={fold_stray_px} "
          f"keepclear_stray_px={keepclear_stray_px} (clip mechanism is paintable_P1-eroded, "
          f"which does NOT structurally exclude fold/keep-clear zones -- they are PAINTABLE "
          f"by PARAMS.md's own definition; measured empirically here instead)")
    print(f"[build_composition_map] wrote {ASSETS / 'control_composition.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
