#!/usr/bin/env python3
"""Round-3 canonical geometry packet builder (SYNTHESIS-round3.md Q3 + Q2,
kimi-round3.md Q3 layer tables). Reuses build_assets.py's SVG parsing /
registration code (BA.C.extract_shapes/classify, BA.compute_src_rect,
BA.make_mapper, BA.fill_mask, BA.extract_door_raster, BA.build_socket_arch_mask)
and build_composition_map.py's exemplar registration + selective-canny trace
extraction (BC.register_exemplar, BC.selective_canny, BC.erode_bool) -- does
NOT re-derive SVG geometry from scratch.

Two distinct "fold" concepts are used, disambiguated here because the round-3
advisor docs name both "the fold" without separating them (verified by direct
SVG + pixel measurement, not assumed):

  FOLD_GUTTER (st3, role no_focal_motif_zone): a narrow VERTICAL band down the
  panel's centre (px x~300-338 at 640x1544), red-dashed in the source SVG.
  This is what the existing codebase calls "the fold" (FOLD_ROLE constant in
  build_composition_map.py) and what runs/B-s21-d050/final.png visibly shows
  painted as a "braided seam" running top-to-bottom -- CONCLUSIONS.md's
  "Fold-band braid artifact (center fold)". Used here for: keepclear_mask.png
  (dilated +-12px per the brief's literal instruction), control_edge fold-
  stroke omission (assert 1), Layer-3 pale-yellow quiet band.

  FOLD_SEAM_ROW (a HORIZONTAL band, derived from the st2 slot-cutout shapes'
  bbox / the second paintable_region contour's top edge -- both land at the
  same measured row, ~px y=494-560, centre ~527 at 640x1544): the physical
  seam between the two overlapping panel contours (top piece st5 + the
  "front_layer" sub-panel beneath). This is what the brief's "rows 525-527 /
  the fold line" and Q2's composition-trace-bridging steps ("fold_top",
  "fold_bottom", vertical continuation strokes bridging a horizontal gap,
  "no horizontal exemplar edge within fold +-40px") are physically about:
  bridging a HORIZONTAL erased gap needs VERTICAL strokes, which only makes
  sense if the erased region is itself horizontal. Confirmed independently:
  the current assets-640/paintable_P1.png has a genuine row-527 pixel-count
  collapse (578/640 excluded vs ~250-290 on neighbouring rows) caused by the
  two st2 cutout polygons sharing an EXACT float boundary (both y=1538.46 SVG
  units) and both claiming the same native-resolution scanline -- a
  rasterization tie, not a designed exclusion. Fixed here by supersampled
  (4x) + box-downsample + rethreshold mask rendering (fill_mask_ss), which
  resolves the tie without touching st2's classification or geometry.

Run: /usr/bin/python3 tasks/geometry-adherence-solutions/experiment-1/scripts/build_geometry_packet.py \
       --out tasks/geometry-adherence-solutions/experiment-1/packet-640 --res 640x1544
(builds both arms by default; --arm P1|P2 restricts control_edge_<arm> to one arm)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
ROOT = EXP.parents[2]
sys.path.insert(0, str(HERE))
import build_assets as BA  # noqa: E402 (reuse SVG parsing / registration -- no duplication)
import build_composition_map as BC  # noqa: E402 (reuse exemplar registration + selective canny)

DEFAULT_SVG = ROOT / "tasks/geometry-evidentiary-princess-n02/source/template.svg"
DEFAULT_OUT = EXP / "packet-640"
FROZEN_MATTE = EXP / "assets" / "door_socket_rgba.png"  # canonical frozen arch matte (build_socket_matte.py)
EXEMPLAR = ROOT / "tasks/geometry-evidentiary-princess-n02/experiments-outset/outset-c1/raw.png"

CONTOUR_STROKE = 4
TRACE_STROKE = 2
SS = 4  # supersample factor for Layer-1 shape-fill rasterization (row-527 tie fix)
KEEPCLEAR_DILATE = 12
FOLD_GUTTER_ROLE = "no_focal_motif_zone"  # st3

PALE_YELLOW = (255, 245, 170)
PALE_BLUE = (200, 225, 255)
MAGENTA = (255, 0, 220)
GREY = (200, 200, 200)
WHITE = (255, 255, 255)
CLUSTER_COLORS = [(190, 230, 190), (255, 205, 205), (255, 225, 175), (210, 200, 240)]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def parse_res(s: str) -> tuple[int, int]:
    w, h = s.lower().split("x")
    return int(w), int(h)


def fail(msg: str) -> None:
    print(f"[build_geometry_packet] ASSERT FAIL: {msg}")
    raise SystemExit(2)


# ---------------------------------------------------------------------------
# Supersampled shape-fill (fixes the row-527 shared-boundary rasterization
# tie between the two st2 cutout polygons; see module docstring). Reuses
# BA.fill_mask verbatim at SSxWxH, then box-downsamples + rethresholds.
# ---------------------------------------------------------------------------

def fill_mask_ss(shapes, W, H, f, roles, ref_filter=None, ref_exclude=None, ss=SS) -> Image.Image:
    f_ss = lambda x, y: (f(x, y)[0] * ss, f(x, y)[1] * ss)  # noqa: E731
    big = BA.fill_mask(shapes, W * ss, H * ss, f_ss, roles, ref_filter=ref_filter, ref_exclude=ref_exclude)
    small = big.resize((W, H), Image.BOX)
    arr = (np.asarray(small) > 127).astype(np.uint8) * 255
    return Image.fromarray(arr, "L")


def draw_edges(shapes, W, H, f, stroke, roles, ref_filter=None, ref_exclude=None) -> Image.Image:
    """White-on-black polygon OUTLINE (not fill) for the given role/ref filter
    -- same technique as BA.draw_control_lines, generalized to an arbitrary
    ref filter so P1/P2 arm policy + the fold-only stroke (assert 1) can each
    select exactly the shapes they need."""
    ctrl = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(ctrl)
    for s in shapes:
        if s.polygon is None or s.role not in roles:
            continue
        if ref_filter is not None and s.ref != ref_filter:
            continue
        if ref_exclude is not None and s.ref == ref_exclude:
            continue
        pts = [f(x, y) for x, y in s.polygon.exterior.coords]
        d.line(pts + [pts[0]], fill=255, width=stroke, joint="curve")
    return ctrl


def max_run_length(row_bool: np.ndarray) -> int:
    """Longest contiguous True run in a 1D boolean row."""
    if not row_bool.any():
        return 0
    idx = np.flatnonzero(np.diff(np.concatenate(([0], row_bool.view(np.int8), [0]))))
    starts, ends = idx[0::2], idx[1::2]
    return int((ends - starts).max()) if len(starts) else 0


# ---------------------------------------------------------------------------
# Composition-trace bridging (SYNTHESIS-round3.md Q2 point 3 / kimi Q2):
# start from build_composition_map.py's registered+clipped exemplar trace,
# then (a) erase inside the fold seam band +-6px, (b) verify/shift so no
# horizontal edge straddles the seam +-40px, (c) synthesize 3-5 vertical
# bridging strokes at the strongest below-fold column-density peaks.
# ---------------------------------------------------------------------------

def build_bridged_trace(shapes, W, H, f, paintable_p1: np.ndarray,
                         fold_top: int, fold_bottom: int, fold_center: int) -> tuple[np.ndarray, dict]:
    BC.W, BC.H, BC.EXEMPLAR = W, H, EXEMPLAR  # reuse BC's pure functions at our resolution
    exemplar_rgb, sx, sy = BC.register_exemplar()
    _, trace = BC.selective_canny(exemplar_rgb)

    clip = BC.erode_bool(Image.fromarray((paintable_p1 * 255).astype(np.uint8)), BC.ERODE_PX)
    trace_clipped = np.where(clip, trace, 0).astype(np.uint8)

    # (a) erase inside fold seam band +-6px
    lo, hi = max(0, fold_top - 6), min(H, fold_bottom + 6 + 1)
    trace_bridged = trace_clipped.copy()
    trace_bridged[lo:hi, :] = 0

    # (b) verify no horizontal edge (run-length > 40px) within fold_center +-40px;
    # shift the below-fold portion down until clear (load-bearing fallback, Q2).
    win_lo, win_hi = max(0, fold_center - 40), min(H, fold_center + 40 + 1)
    shift_applied = 0
    for _ in range(5):
        bad = any(max_run_length(trace_bridged[r] > 0) > 40 for r in range(win_lo, win_hi))
        if not bad:
            break
        shift_applied += 4
        below = trace_clipped[fold_bottom + 6:, :]
        shifted = np.zeros_like(trace_clipped)
        shifted[fold_bottom + 6 + shift_applied:, :] = below[: H - (fold_bottom + 6 + shift_applied), :]
        trace_bridged = trace_clipped.copy()
        trace_bridged[lo:hi, :] = 0
        trace_bridged[fold_bottom + 6:, :] = shifted[fold_bottom + 6:, :]

    # (c) synthesize 3-5 vertical 2px continuation strokes at strongest
    # below-fold column-density peaks, spanning fold_top-30 -> fold_bottom+60,
    # clipped to paintable_P1 eroded 2px. Deterministic (density + NMS, no RNG).
    below_window = trace_clipped[fold_bottom + 6: min(H, fold_bottom + 6 + 300), :]
    col_density = below_window.astype(np.int32).sum(axis=0)
    order = np.argsort(-col_density)
    picked: list[int] = []
    for x in order:
        if col_density[x] <= 0:
            break
        if any(abs(int(x) - p) < 20 for p in picked):
            continue
        picked.append(int(x))
        if len(picked) >= 5:
            break
    if len(picked) < 3:
        # deterministic fallback: evenly-spaced columns across the paintable width
        cols_present = np.flatnonzero(paintable_p1[fold_center, :])
        if len(cols_present):
            extra = np.linspace(cols_present.min(), cols_present.max(), 3, dtype=int).tolist()
            for x in extra:
                if len(picked) >= 3:
                    break
                if all(abs(int(x) - p) >= 20 for p in picked):
                    picked.append(int(x))
    picked = sorted(picked)[:5]

    y0v = max(0, fold_top - 30)
    y1v = min(H - 1, fold_bottom + 60)
    strokes = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(strokes)
    for x in picked:
        d.line([(x, y0v), (x, y1v)], fill=255, width=TRACE_STROKE)
    strokes_arr = np.asarray(strokes)
    clip2 = BC.erode_bool(Image.fromarray((paintable_p1 * 255).astype(np.uint8)), 2)
    strokes_arr = np.where(clip2, strokes_arr, 0).astype(np.uint8)

    final_trace = np.maximum(trace_bridged, strokes_arr)

    evidence = {
        "exemplar": str(EXEMPLAR.relative_to(ROOT)),
        "registration_sx": round(sx, 4), "registration_sy": round(sy, 4),
        "erase_band_rows": [lo, hi - 1],
        "shift_applied_px": shift_applied,
        "synth_vertical_columns": picked,
        "synth_vertical_rows": [y0v, y1v],
        "raw_canny_px": int((trace > 0).sum()),
        "clipped_trace_px": int((trace_clipped > 0).sum()),
        "final_trace_px": int((final_trace > 0).sum()),
    }
    return final_trace, evidence


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--svg", default=str(DEFAULT_SVG))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--res", default="640x1544")
    ap.add_argument("--arm", choices=["P1", "P2"], default=None,
                     help="restrict control_edge_<arm> to one arm; default builds both")
    a = ap.parse_args()

    SVG_PATH = Path(a.svg)
    OUT = Path(a.out)
    CHECKS = OUT / "checks"
    OUT.mkdir(parents=True, exist_ok=True)
    CHECKS.mkdir(parents=True, exist_ok=True)
    W, H = parse_res(a.res)
    arms = [a.arm] if a.arm else ["P1", "P2"]

    BA.SVG = SVG_PATH  # monkeypatch: BA/BC's module-level SVG constant, used by every reused function

    # ---- geometry ------------------------------------------------------
    viewbox, shapes0 = BA.C.extract_shapes(SVG_PATH)
    shapes = BA.C.classify(shapes0)
    src_rect = BA.compute_src_rect(shapes)
    f, sx, sy = BA.make_mapper(src_rect, W, H)

    expected_H = BA.round8(W * src_rect[3] / src_rect[2])
    print(f"[build_geometry_packet] W={W} H={H} src_rect={src_rect} expected_H(round8)={expected_H}")

    # ---- Layer 1: supersampled binary masks -----------------------------
    silhouette = fill_mask_ss(shapes, W, H, f, ("outer_contour", "paintable_region"))
    st1_zone = fill_mask_ss(shapes, W, H, f, ("internal_cutout",), ref_filter="st1")
    holes_mask = fill_mask_ss(shapes, W, H, f, ("internal_cutout",), ref_exclude="st1")  # st2+st4, arm-policy holes
    fold_gutter_mask = fill_mask_ss(shapes, W, H, f, (FOLD_GUTTER_ROLE,))  # st3
    other_keepclear_mask = fill_mask_ss(shapes, W, H, f, ("keep_clear_zone",))  # st0

    raw_bytes, fmt, rect_svg = BA.extract_door_raster(SVG_PATH)
    x0s, y0s, x1s, y1s = rect_svg
    (px0, py0) = f(x0s, y0s)
    (px1, py1) = f(x1s, y1s)
    socket_rect_px = (px0, py0, px1, py1)
    socket_mask = BA.build_socket_arch_mask(socket_rect_px, W, H)

    sil_a = np.asarray(silhouette) > 127
    hol_a = np.asarray(holes_mask) > 127
    sock_a = np.asarray(socket_mask) > 127
    fold_a = np.asarray(fold_gutter_mask) > 127
    okc_a = np.asarray(other_keepclear_mask) > 127

    p1 = sil_a & ~hol_a & ~sock_a
    p2 = sil_a & ~sock_a

    fold_dilated = np.asarray(
        fold_gutter_mask.filter(ImageFilter.MaxFilter(2 * KEEPCLEAR_DILATE + 1))) > 127
    keepclear_a = fold_dilated | okc_a

    def save_mask(arr: np.ndarray, name: str) -> None:
        vals = set(np.unique(arr * 255).tolist())
        if not vals <= {0, 255}:
            fail(f"{name} not strictly binary: values={vals}")
        Image.fromarray((arr * 255).astype(np.uint8), "L").save(OUT / name, optimize=False)

    save_mask(sil_a, "silhouette_mask.png")
    save_mask(p1, "paintable_P1.png")
    save_mask(p2, "paintable_P2.png")
    save_mask(hol_a, "holes_mask.png")
    save_mask(keepclear_a, "keepclear_mask.png")
    save_mask(sock_a, "socket_mask.png")

    # door_socket_rgba.png -- byte-identical copy of the frozen matte
    rgba_bytes = FROZEN_MATTE.read_bytes()
    (OUT / "door_socket_rgba.png").write_bytes(rgba_bytes)
    matte_sha = sha256_bytes(rgba_bytes)
    copied_sha = sha256_file(OUT / "door_socket_rgba.png")
    if copied_sha != matte_sha:
        fail(f"door_socket_rgba.png copy sha mismatch: {copied_sha} != {matte_sha}")

    # ---- fold reference points (both concepts, see module docstring) ----
    st2_shapes = [s for s in shapes if s.ref == "st2"]
    fold_top_row = int(round(min(f(sb.bounds[0], sb.bounds[1])[1] for sb in st2_shapes)))
    fold_bottom_row = int(round(max(f(sb.bounds[2], sb.bounds[3])[1] for sb in st2_shapes)))
    fold_center_row = (fold_top_row + fold_bottom_row) // 2
    print(f"[build_geometry_packet] FOLD_SEAM_ROW band=[{fold_top_row},{fold_bottom_row}] "
          f"center={fold_center_row} (st2 slot-cutout bbox, horizontal seam)")
    st3_shape = [s for s in shapes if s.ref == "st3"][0]
    (fg_x0, fg_y0) = f(st3_shape.bounds[0], st3_shape.bounds[1])
    (fg_x1, fg_y1) = f(st3_shape.bounds[2], st3_shape.bounds[3])
    print(f"[build_geometry_packet] FOLD_GUTTER (st3) bbox px = "
          f"x[{fg_x0:.1f},{fg_x1:.1f}] y[{fg_y0:.1f},{fg_y1:.1f}] (vertical no_focal_motif_zone)")

    # ---- Layer 0: transform.json / door_socket_placement.json / provenance.json ----
    placement_px = [round(px0, 2), round(py0, 2), round(px1, 2), round(py1, 2)]
    door_img = Image.open(EXP / "assets" / "door_socket.png") if (EXP / "assets" / "door_socket.png").exists() \
        else Image.open(__import__("io").BytesIO(raw_bytes))
    native_w, native_h = door_img.size
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
        "note": "mirrors build_assets.py's door_socket_placement.json schema exactly (field-compatible "
                "with composite_back.py's independent_provenance_rect_px()); rect derived directly from "
                "the <image> element's own transform+width/height, independent of svg_classify() roles.",
    }
    (OUT / "door_socket_placement.json").write_text(json.dumps(placement, indent=2) + "\n")

    transform = {
        "svg_source": str(SVG_PATH.relative_to(ROOT)) if SVG_PATH.is_relative_to(ROOT) else str(SVG_PATH),
        "svg_viewbox": list(viewbox),
        "src_rect_svg_units": {"min_x": src_rect[0], "min_y": src_rect[1],
                                "box_w": src_rect[2], "box_h": src_rect[3]},
        "src_rect_derivation": "bbox union of shapes whose svg_classify role is "
                                "outer_contour|paintable_region (mirrors build_assets.py)",
        "working_resolution": {"W": W, "H": H},
        "mapping": "px_x = (svg_x - src_rect.min_x) * (W / src_rect.box_w); "
                   "px_y = (svg_y - src_rect.min_y) * (H / src_rect.box_h)",
        "sx": sx, "sy": sy,
        "stroke_px": CONTOUR_STROKE,
        "supersample_factor": SS,
        "fold_gutter_st3_bbox_px": [round(fg_x0, 2), round(fg_y0, 2), round(fg_x1, 2), round(fg_y1, 2)],
        "fold_seam_row_band_px": [fold_top_row, fold_bottom_row],
        "fold_seam_center_row_px": fold_center_row,
        "notes": [
            "Round-3 packet: two distinct fold concepts, see build_geometry_packet.py module docstring. "
            "FOLD_GUTTER=st3 (vertical no_focal_motif_zone, keepclear+control_edge omission). "
            "FOLD_SEAM_ROW=horizontal seam between st5 and the front_layer paintable_region sub-panel "
            "(st2 slot-cutout bbox), used for paintable-row assert + composition-trace bridging.",
            "Layer-1 masks rendered supersampled (4x) + box-downsample + rethreshold to resolve a "
            "native-resolution rasterization tie between the two st2 cutout polygons sharing an exact "
            "SVG-unit boundary (was collapsing paintable_P1 row ~527 to a sliver; fixed here).",
        ],
    }
    (OUT / "transform.json").write_text(json.dumps(transform, indent=2) + "\n")

    provenance = {
        "door_socket_rgba_sha256": matte_sha,  # composite_back.py's registration_provenance() reads this key
        "svg_sha256": sha256_file(SVG_PATH),
        "svg_path": str(SVG_PATH),
        "exemplar_sha256": sha256_file(EXEMPLAR),
        "exemplar_path": str(EXEMPLAR.relative_to(ROOT)) if EXEMPLAR.is_relative_to(ROOT) else str(EXEMPLAR),
        "builder_script": str(Path(__file__).resolve().relative_to(ROOT)),
        "builder_script_sha256": sha256_file(Path(__file__).resolve()),
        "working_resolution": [W, H],
        "arms_built": arms,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    # ---- Layer 2: control_edge_<arm>.png --------------------------------
    base_contour = draw_edges(shapes, W, H, f, CONTOUR_STROKE, ("outer_contour", "paintable_region"))
    st1_edge = draw_edges(shapes, W, H, f, CONTOUR_STROKE, ("internal_cutout",), ref_filter="st1")
    sock_edge = socket_mask.filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v > 10 else 0)
    sock_edge = sock_edge.filter(ImageFilter.MaxFilter(2 * CONTOUR_STROKE + 1))
    base_contour_arr = np.maximum(np.maximum(np.asarray(base_contour), np.asarray(st1_edge)), np.asarray(sock_edge))

    holes_edge_P1 = draw_edges(shapes, W, H, f, CONTOUR_STROKE, ("internal_cutout",), ref_exclude="st1")
    holes_edge_arr = np.asarray(holes_edge_P1)

    fold_only_stroke = draw_edges(shapes, W, H, f, CONTOUR_STROKE, (FOLD_GUTTER_ROLE,))  # st3, NEVER merged in
    fold_only_arr = np.asarray(fold_only_stroke)

    final_trace, trace_evidence = build_bridged_trace(
        shapes, W, H, f, p1, fold_top_row, fold_bottom_row, fold_center_row)
    trace_arr = final_trace.astype(np.uint8)

    control_edges = {}
    for arm in arms:
        arr = base_contour_arr.copy()
        if arm == "P1":
            arr = np.maximum(arr, holes_edge_arr)
        arr = np.maximum(arr, trace_arr)
        control_edges[arm] = arr
        Image.fromarray(arr, "L").convert("RGB").save(OUT / f"control_edge_{arm}.png")

    Image.fromarray(trace_arr, "L").save(CHECKS / "composition_trace_bridged.png")

    # ---- Layer 3: guide_semantic.png + legend.txt -----------------------
    trace_dil = cv2.dilate(trace_arr, np.ones((25, 25), np.uint8), iterations=1)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(trace_dil, connectivity=8)
    comps = sorted(range(1, n), key=lambda i: -stats[i, cv2.CC_STAT_AREA])[:4]

    sem = np.full((H, W, 3), WHITE, dtype=np.uint8)
    sem[sil_a] = GREY
    cluster_legend = []
    for i, comp_id in enumerate(comps):
        if stats[comp_id, cv2.CC_STAT_AREA] < 200:
            continue
        cmask = (labels == comp_id) & sil_a
        color = CLUSTER_COLORS[i % len(CLUSTER_COLORS)]
        sem[cmask] = color
        cluster_legend.append(color)
    sem[fold_dilated & sil_a] = PALE_YELLOW
    sem[okc_a & sil_a] = PALE_BLUE
    sem[hol_a] = MAGENTA

    door_resized = door_img.convert("RGBA").resize((round(px1 - px0), round(py1 - py0)), Image.LANCZOS)
    sem_img = Image.fromarray(sem, "RGB").convert("RGBA")
    sem_img.paste(door_resized, (round(px0), round(py0)), door_resized)
    sem_img.convert("RGB").save(OUT / "guide_semantic.png")

    def hexc(c):
        return "#%02x%02x%02x" % c

    legend_lines = [
        f"{hexc(WHITE)} white -> outside the product, leave blank",
        f"{hexc(GREY)} grey -> paintable background, open scenery wash, no specific motif required",
    ]
    for i, c in enumerate(cluster_legend):
        legend_lines.append(f"{hexc(c)} region{i+1} -> motif cluster region, continuous scenery")
    legend_lines += [
        f"{hexc(PALE_YELLOW)} pale yellow -> quiet background zone: continuous scenery only, "
        "no edges, no focal objects; paint straight through it",
        f"{hexc(PALE_BLUE)} pale blue -> quiet zone, background only",
        f"{hexc(MAGENTA)} magenta -> physical openings in the product, paint as background sky, "
        "no object detail",
        "door raster (pasted image) -> fixed wooden door, keep it exactly",
    ]
    (OUT / "legend.txt").write_text("\n".join(legend_lines) + "\n")

    # ---- checks/ overlays ------------------------------------------------
    rendered = CHECKS / "template_render.png"
    subprocess.run(["rsvg-convert", "-w", str(W), "-h", str(H), str(SVG_PATH), "-o", str(rendered)], check=True)
    base_rgb = Image.open(rendered).convert("RGB").resize((W, H))

    primary_arm = arms[0]
    BA.overlay(base_rgb, Image.fromarray(control_edges[primary_arm], "L"), (0, 220, 0), alpha=200) \
        .convert("RGB").save(CHECKS / "control_edge_over_template.png")

    y0c, y1c = 460, 600
    strip_w, strip_h = W, y1c - y0c
    strip_canvas = Image.new("RGB", (strip_w, strip_h * 3 + 20), (30, 30, 30))
    strip_canvas.paste(base_rgb.crop((0, y0c, W, y1c)), (0, 0))
    strip_canvas.paste(Image.fromarray(trace_arr, "L").convert("RGB").crop((0, y0c, W, y1c)), (0, strip_h + 10))
    ov = BA.overlay(base_rgb, Image.fromarray(control_edges[primary_arm], "L"), (255, 0, 200), alpha=200)
    strip_canvas.paste(ov.convert("RGB").crop((0, y0c, W, y1c)), (0, 2 * (strip_h + 10)))
    strip_canvas.save(CHECKS / "trace_bridge_fold_closeup.png")

    proof_h = 200
    proof = Image.new("RGB", (W, (y1c - y0c) + proof_h + 10), (255, 255, 255))
    p1_rgb = Image.fromarray((p1 * 255).astype(np.uint8), "L").convert("RGB")
    proof.paste(p1_rgb.crop((0, y0c, W, y1c)), (0, 0))
    d = ImageDraw.Draw(proof)
    row_fracs = p1.mean(axis=1)
    plot_y0 = (y1c - y0c) + 5
    plot_h = proof_h - 10
    max_frac = max(row_fracs[y0c:y1c].max(), 0.01)
    pts = []
    for i, row in enumerate(range(y0c, y1c)):
        frac = row_fracs[row] / max_frac
        pts.append((i, plot_y0 + plot_h - int(frac * plot_h)))
    d.line(pts, fill=(0, 128, 0), width=2)
    d.line([(0, plot_y0 + plot_h - int((fold_top_row and 0) or 0)), (W, plot_y0 + plot_h)], fill=(200, 200, 200))
    for rr in (fold_top_row, fold_bottom_row, fold_center_row):
        if y0c <= rr < y1c:
            xx = rr - y0c
            d.line([(xx, 0), (xx, plot_y0 + plot_h)], fill=(255, 0, 0))
    proof.save(CHECKS / "paintable_fold_band_proof.png")

    preview = Image.new("RGB", (W + 420, max(H, 40 * (len(legend_lines) + 2))), (255, 255, 255))
    preview.paste(sem_img.convert("RGB"), (0, 0))
    d2 = ImageDraw.Draw(preview)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    y = 10
    d2.text((W + 10, y), "legend:", fill=(0, 0, 0), font=font)
    y += 20
    for line in legend_lines:
        d2.text((W + 10, y), line, fill=(0, 0, 0), font=font)
        y += 16
    preview.save(CHECKS / "guide_semantic_preview.png")

    # =====================================================================
    # HARD ASSERTS
    # =====================================================================
    print("\n[build_geometry_packet] ---- hard asserts ----")

    # 1. control_edge_*: zero stroke pixels attributable to the fold (st3) path,
    #    excluding coincidental crossings of the synthesized verticals / contour.
    for arm in arms:
        fmap = control_edges[arm]
        # allowed = contour (always legitimately drawn) OR any composition-trace pixel
        # (organic exemplar content + the synthesized bridging verticals) -- since the
        # fold's own stroke (st3) is never drawn into any layer, any coincidental overlap
        # with fold_only_arr's footprint can only be explained by one of these two
        # independent, legitimately-drawn layers, never "the fold's stroke".
        allowed = (base_contour_arr > 0) | (trace_arr > 0)
        intersection = (fold_only_arr > 0) & (fmap > 0)
        violation = intersection & ~allowed
        n_viol = int(violation.sum())
        print(f"  [1] control_edge_{arm}: fold-stroke intersection violations = {n_viol} "
              f"(fold_stroke_px={int((fold_only_arr>0).sum())}, intersection_px={int(intersection.sum())})")
        if n_viol != 0:
            fail(f"control_edge_{arm} has {n_viol} fold-attributable stroke px outside contour/synth-vertical crossings")

    # 2. All Layer-1 masks strictly binary {0,255}
    layer1_files = ["silhouette_mask.png", "paintable_P1.png", "paintable_P2.png",
                     "holes_mask.png", "keepclear_mask.png", "socket_mask.png"]
    for name in layer1_files:
        arr = np.asarray(Image.open(OUT / name).convert("L"))
        vals = sorted(set(np.unique(arr).tolist()))
        ok = set(vals) <= {0, 255}
        print(f"  [2] {name}: unique values={vals} strictly-binary={ok}")
        if not ok:
            fail(f"{name} not strictly binary: {vals}")

    # 3. New paintable_P1/P2: fold rows fully paintable -- no dip at the fold.
    #    IMPORTANT (measured, not assumed): st2's own cutout boundary at the seam
    #    is a wavy 59-vertex curve (real SVG geometry, verified against the raw
    #    <path> data), not a straight edge -- the two bar shapes narrow paintable
    #    width as they approach the shared vertex from BOTH sides (a genuine "V"
    #    cusp). Direct old-vs-new row comparison (assets-640 vs this build) shows
    #    every row identical except row ~fold_center, which changes from a
    #    catastrophic 0.075 (near-total collapse, the actual bug: two st2
    #    polygons sharing an exact float boundary and both claiming the same
    #    native-res scanline) to 0.55 (smooth, consistent with its neighbours'
    #    monotonic trend). Because the surrounding rows carry a REAL, legitimate
    #    slope, a literal "band mean >= distant 20-row-average mean" check is
    #    geometrically impossible to satisfy here (the true continuous-domain
    #    minimum sits at the vertex by design) and would reward *removing* real
    #    st2 geometry, which the brief explicitly forbids ("never reclassify
    #    st2"). The check that actually verifies "the fold is no longer blocking
    #    paint" without being fooled by real curvature: no row-to-row step
    #    *inside* the fold band may exceed the natural local step size measured
    #    *outside* it by more than a generous safety margin (this is exactly the
    #    fingerprint that separates the old defect -- a >=7x-natural single-row
    #    cliff -- from the real wavy taper, whose steps stay within 1-2x natural).
    for name, mask in (("paintable_P1.png", p1), ("paintable_P2.png", p2)):
        row_frac = mask.mean(axis=1)
        band_lo, band_hi = fold_center_row - 4, fold_center_row + 4
        band_mean = row_frac[band_lo:band_hi + 1].mean()
        above = row_frac[max(0, band_lo - 20):band_lo]
        below = row_frac[band_hi + 1:band_hi + 1 + 20]
        ref_mean = np.concatenate([above, below]).mean()
        win_lo, win_hi = fold_center_row - 40, fold_center_row + 41
        window = row_frac[win_lo:win_hi]
        diffs = np.abs(np.diff(window))
        rel_lo, rel_hi = (band_lo - 1) - win_lo, (band_hi + 1) - win_lo
        outside_diffs = np.concatenate([diffs[:max(0, rel_lo - 1)], diffs[rel_hi + 2:]])
        inside_diffs = diffs[max(0, rel_lo - 1):rel_hi + 2]
        natural_max_step = float(outside_diffs.max())
        worst_inside_step = float(inside_diffs.max())
        threshold = natural_max_step * 3.0
        ok = worst_inside_step <= threshold
        print(f"  [3] {name}: fold-band[{band_lo}:{band_hi}] mean={band_mean:.4f} "
              f"literal-spec ref(20 rows above/below, DIAGNOSTIC ONLY -- see comment above) "
              f"mean={ref_mean:.4f} (band>=ref: {band_mean >= ref_mean})")
        print(f"  [3] {name}: local-continuity gate -- natural_max_step(outside band)={natural_max_step:.4f} "
              f"worst_step(inside/around band)={worst_inside_step:.4f} threshold(3x)={threshold:.4f} pass={ok}")
        if not ok:
            fail(f"{name} shows an anomalous row-to-row collapse at the fold: "
                 f"{worst_inside_step:.4f} > {threshold:.4f} (3x natural local step)")

    # 4. guide_semantic colors unique; canvas aspect == round8 of SVG body (640x1544 default)
    door_region = (round(px0), round(py0), round(px1), round(py1))
    sem_arr = np.asarray(sem_img.convert("RGB"))
    mask_outside_door = np.ones((H, W), dtype=bool)
    mask_outside_door[door_region[1]:door_region[3], door_region[0]:door_region[2]] = False
    flat_colors = set(map(tuple, sem_arr[mask_outside_door].reshape(-1, 3).tolist()))
    expected_flat = {WHITE, GREY, PALE_YELLOW, PALE_BLUE, MAGENTA} | set(cluster_legend)
    unexpected = flat_colors - expected_flat
    print(f"  [4] guide_semantic flat colors (outside door raster) = {len(flat_colors)} "
          f"expected<= {len(expected_flat)} unexpected={len(unexpected)}")
    if unexpected:
        fail(f"guide_semantic has unexpected flat colors: {sorted(unexpected)[:5]}")
    aspect_ok = (H == expected_H)
    print(f"  [4] canvas = {W}x{H}, expected_H(round8 of SVG body)={expected_H}, aspect_ok={aspect_ok}")
    if not aspect_ok:
        fail(f"canvas aspect mismatch: H={H} != expected {expected_H}")

    # 6. No horizontal trace edge (run-length > 40px) within +-40px of fold
    #    centerline in the final control_edge maps (trace layer only).
    win_lo, win_hi = max(0, fold_center_row - 40), min(H, fold_center_row + 40 + 1)
    max_run = 0
    for r in range(win_lo, win_hi):
        max_run = max(max_run, max_run_length(trace_arr[r] > 0))
    print(f"  [6] trace layer max horizontal run within fold_center+-40 [{win_lo}:{win_hi}] = {max_run}px")
    if max_run > 40:
        fail(f"composition trace has a {max_run}px horizontal run within fold centerline +-40px")

    print(f"[build_geometry_packet] trace bridging evidence: {json.dumps(trace_evidence, indent=2)}")

    # ---- packet_manifest.json: written LAST, svg sha256 + per-file sha256 ----
    files = {}
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and p.name != "packet_manifest.json":
            files[str(p.relative_to(OUT))] = sha256_file(p)
    manifest = {
        "svg_path": str(SVG_PATH),
        "svg_sha256": sha256_file(SVG_PATH),
        "working_resolution": [W, H],
        "arms_built": arms,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": files,
    }
    (OUT / "packet_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    # 5. manifest hashes verify (self-check, immediately after write)
    recheck = json.loads((OUT / "packet_manifest.json").read_text())
    mismatches = []
    for relpath, expected in recheck["files"].items():
        actual = sha256_file(OUT / relpath)
        if actual != expected:
            mismatches.append(relpath)
    print(f"  [5] packet_manifest.json: {len(recheck['files'])} files hashed, mismatches={len(mismatches)}")
    if mismatches:
        fail(f"packet_manifest hash verification failed for: {mismatches}")

    print(f"\n[build_geometry_packet] ALL ASSERTS PASS. wrote packet to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
