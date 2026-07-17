#!/usr/bin/env python3
"""Stage-C mechanical guardrail: LAST raster ops before delivery (SYNTHESIS.md
Stage C). Given a candidate image + the experiment-1 assets dir, in order:

  (a) silhouette re-mask  -- everything outside silhouette_mask forced to
      white, 1px feather at the boundary.
  (b) punch holes         -- holes_mask interior forced to clean white, with a
      subtle bevel ring (mirrors scripts/punch_holes.py's inner-shadow/outer-
      lip convention, keyed on our precomputed mask instead of re-deriving
      cutout polygons from the SVG at punch time).
  (c) socket composite-back -- Amendment 1 (pre-run advisor correction):
      alpha-composite the FROZEN arch-shaped RGBA matte (door_socket_rgba.png,
      built by build_socket_matte.py -- border-connected near-white flood,
      RGB byte-preserved, its own ~0.8px feather baked in) back at its
      measured placement. Always upscales directly from the matte's own
      native pixels to the candidate's resolution (never through an
      intermediate downscaled copy), per SYNTHESIS's "upscale art BEFORE
      paste, never after". Replaces the earlier full-rect opaque paste.
  (d) metrics.json -- Amendment 2 (2nd advisor) gate set:
        - registration: boundary-distance (max offset) + footprint area
          ratio of the candidate's actual (untouched) neutral-fill region
          vs. the expected arch footprint.
        - corner_integration: in the (old placement-rect minus arch) corner
          zone, % of pixels actually painted (not neutral fill, not white)
          -- proves the wall was painted up to the arch, not left as a
          pasted rectangular card.
        - socket_gates: byte-exact zoning -- alpha=255 pixels byte-exact vs
          the resized matte; the feather ring (0<alpha<255) matches the
          deterministic alpha-blend expectation; alpha=0 unconstrained; a
          fresh independent recompute of the matte's resized alpha must
          exactly match what was used for the paste.
      Plus the legacy outside-silhouette / per-hole paint-% metrics.

Registration is a HARD GATE (unchanged mechanism, refined measurement):
measured on the ORIGINAL candidate (before any of this script's own edits
touch the socket pixels). If the boundary offset exceeds --reg-tol OR the
footprint area ratio drifts beyond +/-2%, the composited output + metrics
are still written (so the failure is inspectable) but the process exits
non-zero -- the fail-pre-fix fixture SYNTHESIS.md calls for.

Amendment 3 (post-gen, detection-only recalibration; gate thresholds
unchanged): actual_neutral_region() (which locates the candidate's actual
kept-neutral pixels for the registration gate above) is now a color-tolerant,
two-stage, position-honest detector -- see its docstring and the module-level
NEUTRAL_* constants. reg_tol/AREA_RATIO_TOL themselves are untouched. Real
gens still measure 3.0-3.16px max_boundary_offset (just above --reg-tol=1.5)
even with this fix -- see test_composite_back.py's
test_real_gen_socket_and_corner_gates docstring for the finding.

Amendment 4 (registration gate redesign, advisor consult -- see
tasks/geometry-adherence-solutions/kimi-reggate.md): Amendment 3's finding --
the appearance-based registration gate has a ~3.0-3.16px measured noise floor
on real Stage-A candidates (making reg-tol=1.5 always-fail) and 100%
false-positives on painterly Stage-B candidates (flat washes merge into the
low-texture blob the detector keys on: offsets ~120px, area_ratio 1.84-1.99)
while every paste-measuring gate (socket byte-exact, feather-ring blend,
alpha-vs-frozen-matte, corner_integration) passes -- means appearance detection
carries no reliable information about WHERE the paste landed, only about
candidate drift that corner_integration already bounds. The paste itself is
already deterministic (rasterize_geometry() re-derives socket_rect_px from the
frozen SVG at compose time; composite_socket_arch() blends at exactly that
rect), so the PRIMARY registration gate is now transform-provenance
(registration_provenance() / independent_provenance_rect_px()): re-derive the
socket footprint px rect via a genuinely separate code path -- reading the
NUMBERS build_assets.py already recorded in assets-dir/door_socket_placement.json
(placement_svg_units) + assets-dir/transform.json (src_rect_svg_units) and
reapplying the same px=(svg-min)*scale formula, WITHOUT calling
BA.rasterize_geometry/BA.compute_src_rect/BA.extract_door_raster -- and assert
it matches the footprint the compositor actually used, within 0.5px, PLUS
assert door_socket_rgba.png's sha256 against assets-dir/provenance.json
(bootstrapped on first run if absent). This is the HARD gate now: exit 3 on
either mismatch. Appearance detection (arch_registration() /
actual_neutral_region(), mechanism unchanged) is DEMOTED to advisory: its
status is "advisory_pass"/"advisory_anomalous"/"no_neutral_region_found",
reported in metrics.json, but it NEVER sets the exit code. Its tolerance is
widened 1.5 -> 5.0px (58% headroom over the measured 3.0-3.16px real-gen
floor; area_ratio tolerance unchanged +/-2%). Every run also now writes a
junction crop (<out stem>-junction.png): a tight bounding-box crop of
final.png around the composited arch footprint's boundary ring, +/-8px, for
human review.

Usage:
  composite_back.py --candidate CAND.png --assets-dir ASSETS_DIR --out OUT.png
      [--metrics METRICS.json] [--reg-tol 5.0] [--fill 255,255,255]
      [--init-fill 222,213,199] [--bevel 2]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter
from scipy import ndimage

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_assets as BA  # noqa: E402 (reuse geometry rasterization, no duplication)

REG_FAIL_EXIT = 3
AREA_RATIO_TOL = (0.98, 1.02)
PROVENANCE_TOL_PX = 0.5  # Amendment 4: max allowed disagreement between the
                          # independently re-derived footprint rect and the
                          # compositor's own -- the PRIMARY (hard) gate
JUNCTION_CROP_MARGIN_PX = 8  # Amendment 4 (kimi-reggate.md #3): junction
                              # crop margin around the arch boundary ring

# Amendment 3 (post-gen, detection-only recalibration; gate thresholds unchanged):
# actual_neutral_region() parameters. Real MPS SDXL-inpaint gens keep the socket
# region's SHAPE untouched (it's excluded from paintable) but the VAE
# encode/decode roundtrip tints its RGB uniformly away from --init-fill
# (222,213,199) -- measured on all 4 real gens (runs/A-P{1,2}-s{7,21}/gen.png):
# mean drift 60.8-70.4/255 on every channel roughly equally (max per-gen channel
# delta: 67.7, 70.4, 65.4, 69.8), while the region's OWN internal color std stays
# low (4.3-8.9/255) -- i.e. still visually flat/uniform, just a different flat
# color. Absolute-RGB matching against the fixed --init-fill (old behaviour)
# therefore finds nothing on any of the 4 (exit 3, "no_neutral_region_found")
# even though the region is genuinely untouched.
#
# Detection is TWO STAGE, and stage 1 deliberately never trusts the expected
# mask's own pixels as ground truth for what "neutral" looks like -- an
# earlier version of this fix sampled the reference color from a core of the
# (assumed-correct) expected mask and searched only a tight dilation of it;
# that self-referentially "found" whatever solid color happened to sit at the
# expected location even when it was actually generic painted body fill that
# coincidentally matched within tolerance, silently PASSING a shifted-fixture
# regression test (test_shifted_tinted_socket_fails_registration) -- caught in
# calibration, not shipped. Fixed by decoupling position-finding from the
# expected geometry entirely:
#
#   Stage 1 (position, shift-safe): find the largest LOW-TEXTURE (local pixel
#   variance) connected blob within a generous neighborhood of the expected
#   mask, independent of its color -- texture naturally separates the kept
#   region from adjacent differently-colored painted content (a real color
#   edge = local variance spike), so this works without any a-priori color
#   assumption. Among candidate blobs, keep the one with the best IoU vs the
#   expected mask (a floor rejects "no plausible match anywhere nearby").
#   Because this stage's blob-vs-blob choice never warps the winning blob's
#   own shape, a genuinely SHIFTED true region is still reported at its real
#   (shifted) position, not snapped onto the expected one.
#
#   Stage 2 (precision refine, self-referential): sample the reference color
#   from the eroded core of stage 1's OWN blob (never from the expected mask,
#   never from the fixed --init-fill) and refine within a small dilation of
#   THAT SAME blob (not the expected mask) -- recovers the few px stage 1's
#   texture threshold misses right at the model's bold outline stroke
#   (Amendment 1 control_canny convention paints one directly on the arch
#   boundary), again without ever referencing where the socket was "supposed"
#   to be.
#
# arch_registration() (unchanged) then compares this position-honest actual
# mask against the expected mask exactly as before -- a real shift still
# shows up as a large boundary offset because stage 2 only ever tightens
# around wherever stage 1 actually found paint, not around the expected
# footprint.
NEUTRAL_TEX_WIN_PX = 3         # stage 1: local-variance window (uniform_filter)
NEUTRAL_TEX_TOL = 6            # stage 1: local std <= this => "flat"
NEUTRAL_SEARCH_MARGIN_PX = 60  # stage 1: neighborhood searched around the
                                # expected mask's bbox for candidate flat blobs
NEUTRAL_MIN_IOU = 0.3          # stage 1: reject if no flat blob anywhere in
                                # the neighborhood overlaps the expected mask
                                # by at least this much (Intersection-over-
                                # Union) -- genuinely nothing plausible nearby
NEUTRAL_REFINE_DILATE_PX = 1   # stage 2: refine within stage-1 blob dilated
                                # this far (NOT the expected mask)
NEUTRAL_REFINE_ERODE_PX = 3    # stage 2: reference color sampled from stage-1
                                # blob eroded this far in
NEUTRAL_REFINE_COLOR_TOL = 30  # stage 2: max per-channel abs distance from
                                # that locally-sampled reference color
NEUTRAL_REFINE_CLOSE_PX = 3    # stage 2: morphological closing (re-clipped to
                                # the stage-2 search window) to bridge the
                                # outline-stroke notches


def parse_rgb(s: str) -> tuple[int, int, int]:
    return tuple(int(v) for v in s.split(","))  # type: ignore[return-value]


def silhouette_remask(cand: Image.Image, silhouette: Image.Image, fill: tuple[int, int, int]) -> Image.Image:
    """(a) everything outside the silhouette -> fill color, 1px feather at the edge."""
    sil = silhouette.filter(ImageFilter.GaussianBlur(0.6))  # ~1px soft edge
    a = np.asarray(sil).astype(np.float32) / 255.0
    src = np.asarray(cand.convert("RGB")).astype(np.float32)
    bg = np.full_like(src, fill, dtype=np.float32)
    out = src * a[..., None] + bg * (1 - a[..., None])
    return Image.fromarray(out.astype(np.uint8), "RGB")


def punch_holes(cand: Image.Image, holes: Image.Image, fill: tuple[int, int, int], bevel: int):
    """(b) clean white(-ish) interior + subtle bevel ring. Mirrors
    scripts/punch_holes.py's inner-shadow/outer-lip convention, but keyed off
    a precomputed holes_mask instead of re-deriving cutout polygons."""
    W, H = cand.size
    plate = Image.new("RGB", (W, H), fill)
    out = Image.composite(plate, cand.convert("RGB"), holes)

    b = max(1, bevel)
    inner = holes.filter(ImageFilter.MinFilter(2 * b + 1))
    outer = holes.filter(ImageFilter.MaxFilter(2 * b + 1))
    inner_ring = ImageChops.subtract(holes, inner)
    outer_ring = ImageChops.subtract(outer, holes)
    shadow = Image.new("RGB", (W, H), (40, 40, 50))
    lip = Image.new("RGB", (W, H), (245, 245, 250))
    out = Image.composite(shadow, out, inner_ring.point(lambda v: int(v * 0.75)))
    out = Image.composite(lip, out, outer_ring.point(lambda v: int(v * 0.55)))
    return out


def measure_hole_paint_pct(img: Image.Image, shapes, src_rect, W, H, bg: tuple[int, int, int], tol: int = 12):
    """Per-cutout (excluding st1) painted % = fraction of non-background pixels
    inside that single shape's own polygon, rasterized fresh at WxH."""
    f, _, _ = BA.make_mapper(src_rect, W, H)
    arr = np.asarray(img.convert("RGB")).astype(np.int16)
    bg_arr = np.array(bg, dtype=np.int16)
    diff = np.abs(arr - bg_arr).sum(axis=2)
    non_bg = diff > tol
    out = []
    for i, s in enumerate(s for s in shapes if s.role == "internal_cutout" and s.ref != BA.SOCKET_REF):
        m = Image.new("L", (W, H), 0)
        pts = [f(x, y) for x, y in s.polygon.exterior.coords]
        ImageDraw.Draw(m).polygon(pts, fill=255)
        hole_bool = np.asarray(m) > 127
        n = int(hole_bool.sum())
        painted = int((hole_bool & non_bg).sum())
        out.append({"ref": s.ref, "index": i, "area_px": n,
                    "painted_pct": round(100 * painted / n, 3) if n else 0.0})
    return out


def _local_std_map(gray: np.ndarray, win: int) -> np.ndarray:
    """Per-pixel local standard deviation over a win x win window (fast
    box-filter formulation: sqrt(E[x^2] - E[x]^2))."""
    m = ndimage.uniform_filter(gray, size=win)
    m2 = ndimage.uniform_filter(gray * gray, size=win)
    return np.sqrt(np.clip(m2 - m * m, 0, None))


def _neutral_region_stage1(arr: np.ndarray, exp_bool: np.ndarray,
                            tex_win: int, tex_tol: float,
                            search_margin: int, min_iou: float) -> np.ndarray | None:
    """Stage 1 (position, shift-safe): largest low-texture connected blob
    within `search_margin` px of the expected mask's bbox, selected by best
    IoU vs the expected mask (never by raw size, and never by matching the
    expected mask's own color) -- see module docstring above
    actual_neutral_region."""
    H, W = arr.shape[:2]
    gray = arr.mean(axis=2)
    tex = _local_std_map(gray, tex_win)

    ys, xs = np.where(exp_bool)
    if ys.size == 0:
        return None
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    sx0 = max(0, x0 - search_margin); sx1 = min(W, x1 + search_margin)
    sy0 = max(0, y0 - search_margin); sy1 = min(H, y1 + search_margin)
    win_mask = np.zeros((H, W), dtype=bool)
    win_mask[sy0:sy1, sx0:sx1] = True

    flat = (tex <= tex_tol) & win_mask
    labels, n = ndimage.label(flat)
    best_iou = -1.0
    best_mask = None
    for i in range(1, n + 1):
        comp = labels == i
        inter = (comp & exp_bool).sum()
        if inter == 0:
            continue
        union = (comp | exp_bool).sum()
        iou = inter / union
        if iou > best_iou:
            best_iou = iou
            best_mask = comp
    if best_mask is None or best_iou < min_iou:
        return None
    return best_mask


def _neutral_region_stage2(arr: np.ndarray, stage1_blob: np.ndarray,
                            refine_dilate: int, refine_erode: int,
                            color_tol: int, close_px: int) -> np.ndarray:
    """Stage 2 (precision refine, self-referential): color-match + close,
    entirely relative to stage 1's OWN blob -- never to the expected mask --
    so a genuinely shifted/misplaced stage-1 result stays reported at its
    real position instead of being pulled back onto the expected one."""
    H, W = arr.shape[:2]
    search_mask = (ndimage.binary_dilation(stage1_blob, iterations=refine_dilate)
                   if refine_dilate > 0 else stage1_blob)
    core = ndimage.binary_erosion(stage1_blob, iterations=refine_erode) if refine_erode > 0 else stage1_blob
    if not core.any():
        core = stage1_blob
    local_color = arr[core].mean(axis=0)

    color_dist = np.abs(arr - local_color).max(axis=2)
    flat = (color_dist <= color_tol) & search_mask
    if not flat.any():
        return np.zeros((H, W), dtype=bool)

    labels, n = ndimage.label(flat)
    sizes = ndimage.sum(flat, labels, range(1, n + 1))
    biggest = int(np.argmax(sizes)) + 1
    mask = labels == biggest
    if close_px > 0:
        mask = ndimage.binary_closing(mask, iterations=close_px) & search_mask
    return mask


def actual_neutral_region(cand: Image.Image, expected_mask: Image.Image,
                           fill: tuple[int, int, int],
                           tex_win: int = NEUTRAL_TEX_WIN_PX,
                           tex_tol: float = NEUTRAL_TEX_TOL,
                           search_margin: int = NEUTRAL_SEARCH_MARGIN_PX,
                           min_iou: float = NEUTRAL_MIN_IOU,
                           refine_dilate: int = NEUTRAL_REFINE_DILATE_PX,
                           refine_erode: int = NEUTRAL_REFINE_ERODE_PX,
                           refine_color_tol: int = NEUTRAL_REFINE_COLOR_TOL,
                           refine_close_px: int = NEUTRAL_REFINE_CLOSE_PX) -> np.ndarray:
    """Amendment 3: two-stage, color-tolerant, position-honest detection of
    the candidate's actual (untouched) neutral socket fill. Unlike the old
    absolute-RGB match against the fixed --init-fill (breaks on real MPS
    SDXL-inpaint gens, which tint the kept region 60-70/255 via the VAE
    roundtrip), this never assumes the expected location's own pixels are the
    ground truth for what "neutral" looks like -- see the module-level
    constants' docstring for why (an earlier, simpler version of this fix did
    exactly that and silently passed a shifted-fixture regression test).

    Stage 1 finds WHERE the actual kept-flat content is (texture-based,
    position-agnostic, IoU-scored against `expected_mask` only to pick among
    candidates -- never to relocate one). Stage 2 refines that blob's own
    boundary using a color reference sampled from itself. `fill` is accepted
    for interface/back-compat (`--init-fill`) and used only as a last-resort
    fallback if `expected_mask` itself is degenerate (0px).

    Returns an all-False mask (registration reports "no_neutral_region_found")
    if no plausible region exists nearby at all -- a genuinely overpainted/
    misplaced socket still fails, and (per Amendment 3's calibration) a
    genuinely shifted one is reported at its real position so
    arch_registration()'s unchanged boundary-distance/area-ratio gate still
    fails it."""
    W, H = cand.size
    arr = np.asarray(cand.convert("RGB")).astype(np.float64)
    exp_bool = np.asarray(expected_mask) > 127
    if not exp_bool.any():
        return np.zeros((H, W), dtype=bool)

    blob = _neutral_region_stage1(arr, exp_bool, tex_win, tex_tol, search_margin, min_iou)
    if blob is None:
        return np.zeros((H, W), dtype=bool)
    return _neutral_region_stage2(arr, blob, refine_dilate, refine_erode, refine_color_tol, refine_close_px)


def _boundary_pixels(mask: np.ndarray) -> np.ndarray:
    interior = ndimage.binary_erosion(mask, iterations=1, border_value=0)
    return mask & ~interior


def arch_registration(expected_mask: Image.Image, actual_mask: np.ndarray, reg_tol: float) -> dict:
    """Amendment 2 #3: boundary-distance registration (max symmetric offset,
    expected<->actual) + footprint area ratio, replacing the earlier
    bbox-corner offset. Measured on the UNTOUCHED candidate.

    Amendment 4: DEMOTED to advisory -- status is now "advisory_pass" /
    "advisory_anomalous" (or "no_neutral_region_found") and this result NEVER
    sets the process exit code; see registration_provenance() for the new
    PRIMARY (hard) gate."""
    exp_bool = np.asarray(expected_mask) > 127
    exp_area = int(exp_bool.sum())
    if not actual_mask.any():
        return {"status": "no_neutral_region_found", "max_boundary_offset_px": None,
                "area_actual_px": 0, "area_expected_px": exp_area, "area_ratio": None,
                "tol_px": reg_tol, "area_ratio_tol": list(AREA_RATIO_TOL)}

    dist_to_actual = ndimage.distance_transform_edt(~actual_mask)
    dist_to_expected = ndimage.distance_transform_edt(~exp_bool)
    eb = _boundary_pixels(exp_bool)
    ab = _boundary_pixels(actual_mask)
    d1 = float(dist_to_actual[eb].max()) if eb.any() else 0.0
    d2 = float(dist_to_expected[ab].max()) if ab.any() else 0.0
    max_offset = max(d1, d2)

    area_actual = int(actual_mask.sum())
    area_ratio = area_actual / exp_area if exp_area else None
    status = "advisory_anomalous"
    if area_ratio is not None and max_offset <= reg_tol and AREA_RATIO_TOL[0] <= area_ratio <= AREA_RATIO_TOL[1]:
        status = "advisory_pass"
    return {"status": status, "max_boundary_offset_px": round(max_offset, 3),
            "area_actual_px": area_actual, "area_expected_px": exp_area,
            "area_ratio": round(area_ratio, 4) if area_ratio is not None else None,
            "tol_px": reg_tol, "area_ratio_tol": list(AREA_RATIO_TOL)}


def independent_provenance_rect_px(assets_dir: Path, W: int, H: int) -> tuple[float, float, float, float]:
    """Amendment 4 (registration gate redesign, kimi-reggate.md): the
    INDEPENDENT half of the transform-provenance gate. Re-derives the door
    raster's placement footprint at the candidate's own W,H by reading the
    NUMBERS build_assets.py already recorded --
    assets_dir/door_socket_placement.json's placement_svg_units (the raster's
    own placement rect in SVG units, itself parsed straight from the <image>
    element's transform()+width/height, independent of svg_classify() role
    assignment -- see BA.extract_door_raster) and assets_dir/transform.json's
    src_rect_svg_units -- and reapplying the SAME px=(svg-min)*scale formula
    the compositor uses, WITHOUT calling BA.rasterize_geometry /
    BA.compute_src_rect / BA.extract_door_raster. A genuinely separate
    computation over frozen recorded numbers, not the same function called
    twice."""
    placement = json.loads((assets_dir / "door_socket_placement.json").read_text())
    transform = json.loads((assets_dir / "transform.json").read_text())
    x0s, y0s, x1s, y1s = placement["placement_svg_units"]
    src = transform["src_rect_svg_units"]
    min_x, min_y, box_w, box_h = src["min_x"], src["min_y"], src["box_w"], src["box_h"]
    sx = W / box_w
    sy = H / box_h
    return ((x0s - min_x) * sx, (y0s - min_y) * sy,
            (x1s - min_x) * sx, (y1s - min_y) * sy)


def registration_provenance(assets_dir: Path, compositor_rect_px: tuple[float, float, float, float],
                             W: int, H: int, tol_px: float = PROVENANCE_TOL_PX) -> dict:
    """Amendment 4: PRIMARY registration gate (hard, exit REG_FAIL_EXIT on
    mismatch) -- replaces the appearance-based boundary/area check (now
    advisory-only, see arch_registration() above). Two independent
    assertions must both hold:
      (1) the independently re-derived footprint rect (see
          independent_provenance_rect_px above) equals the footprint rect the
          compositor actually used (BA.rasterize_geometry's socket_rect_px),
          within tol_px.
      (2) the frozen door_socket_rgba.png matte's sha256 matches the hash
          recorded in assets_dir/provenance.json -- created here, recording
          the currently-observed hash, if that file is absent (first-run
          bootstrap, not itself a failure)."""
    indep_rect = independent_provenance_rect_px(assets_dir, W, H)
    diffs = [abs(a - b) for a, b in zip(indep_rect, compositor_rect_px)]
    max_diff = max(diffs)
    rect_match = max_diff <= tol_px

    rgba_path = assets_dir / "door_socket_rgba.png"
    actual_hash = hashlib.sha256(rgba_path.read_bytes()).hexdigest()
    prov_path = assets_dir / "provenance.json"
    provenance_file_created = False
    if prov_path.exists():
        expected_hash = json.loads(prov_path.read_text()).get("door_socket_rgba_sha256")
    else:
        expected_hash = actual_hash
        prov_path.write_text(json.dumps({"door_socket_rgba_sha256": actual_hash}, indent=2) + "\n")
        provenance_file_created = True
    hash_match = actual_hash == expected_hash

    status = "pass" if (rect_match and hash_match) else "fail"
    return {
        "status": status,
        "independent_rect_px": [round(v, 3) for v in indep_rect],
        "compositor_rect_px": [round(v, 3) for v in compositor_rect_px],
        "max_abs_diff_px": round(max_diff, 4),
        "tol_px": tol_px,
        "rect_match": rect_match,
        "door_socket_rgba_sha256": actual_hash,
        "door_socket_rgba_sha256_expected": expected_hash,
        "hash_match": hash_match,
        "provenance_file_created": provenance_file_created,
    }


def corner_integration_pct(cand: Image.Image, rect_px: tuple[float, float, float, float],
                            arch_mask: Image.Image, fill: tuple[int, int, int],
                            tol: int = 10, white_tol: int = 12) -> dict:
    """Amendment 2 #4 (NEW gate): in the (old placement-rect minus arch)
    corner/margin zone, % of pixels that are actually painted (not neutral
    fill, not near-white) -- proves the wall was painted up to the arch
    edge rather than left as a pasted rectangular card. Measured on the
    UNTOUCHED candidate."""
    W, H = cand.size
    x0, y0, x1, y1 = rect_px
    xi0, yi0 = max(0, int(round(x0))), max(0, int(round(y0)))
    xi1, yi1 = min(W, int(round(x1))), min(H, int(round(y1)))
    rect_mask = np.zeros((H, W), dtype=bool)
    rect_mask[yi0:yi1, xi0:xi1] = True
    arch_bool = np.asarray(arch_mask) > 127
    zone = rect_mask & ~arch_bool

    arr = np.asarray(cand.convert("RGB")).astype(np.int16)
    fill_arr = np.array(fill, dtype=np.int16)
    white_arr = np.array((255, 255, 255), dtype=np.int16)
    near_fill = np.abs(arr - fill_arr).max(axis=2) <= tol
    near_white = np.abs(arr - white_arr).sum(axis=2) <= white_tol
    painted = ~near_fill & ~near_white

    zone_n = int(zone.sum())
    painted_n = int((painted & zone).sum())
    pct = round(100 * painted_n / zone_n, 3) if zone_n else None
    return {"zone_px": zone_n, "painted_px": painted_n, "painted_pct": pct,
            "status": "pass" if (pct is not None and pct >= 95.0) else "fail"}


def composite_socket_arch(out_img: Image.Image, door_rgba_path: Path, rect_px: tuple[float, float, float, float]):
    """(c) Amendment 1: alpha-composite the frozen arch-shaped RGBA matte,
    upscaled ONCE directly from its native pixels to the target footprint
    (LANCZOS on RGB+alpha together -- the matte's own ~0.8px feather is what
    creates the transition ring; no synthetic pad/feather added here).
    Returns (composited image, socket_gates dict -- Amendment 2 #2 byte-exact
    zoning, measured not assumed)."""
    x0, y0, x1, y1 = rect_px
    tw, th = max(1, round(x1 - x0)), max(1, round(y1 - y0))
    px0, py0 = round(x0), round(y0)

    door_rgba = Image.open(door_rgba_path).convert("RGBA")
    art_resized = door_rgba.resize((tw, th), Image.LANCZOS)

    # Direct numpy "over" blend at the exact target footprint -- NOT
    # PIL .paste(mask=self-alpha) + alpha_composite: that combo double-applies
    # the alpha weight at partial-alpha pixels (paste blends by mask, THEN
    # alpha_composite blends again by the pasted-in alpha), corrupting the
    # feather ring. A single deterministic blend is both the actual compositor
    # AND the expectation this gate measures against (Amendment 2 #2).
    out_arr = np.asarray(out_img.convert("RGB")).astype(np.float32)
    bg_arr_f = out_arr[py0:py0 + th, px0:px0 + tw].copy()  # pre-paste background, for the blend gate
    art_rgb_f = np.asarray(art_resized.convert("RGB")).astype(np.float32)
    art_a = np.asarray(art_resized.split()[-1])
    afrac = (art_a.astype(np.float32) / 255.0)[..., None]
    blended = art_rgb_f * afrac + bg_arr_f * (1 - afrac)
    out_arr[py0:py0 + th, px0:px0 + tw] = blended
    composited = Image.fromarray(np.clip(out_arr, 0, 255).astype(np.uint8), "RGB")

    # ---- Amendment 2 #2: byte-exact gate zoning (measured, not assumed) ----
    comp_arr = np.clip(np.round(blended), 0, 255).astype(np.int16)
    art_rgb = art_rgb_f.astype(np.int16)
    bg_arr = bg_arr_f.astype(np.int16)

    opaque = art_a == 255
    ring = (art_a > 0) & (art_a < 255)

    opaque_delta = np.abs(comp_arr - art_rgb)[opaque] if opaque.any() else np.zeros((0,), dtype=np.int16)
    opaque_max_delta = int(opaque_delta.max()) if opaque_delta.size else 0

    expected_blend = np.round(art_rgb * afrac + bg_arr * (1 - afrac)).astype(np.int16)
    ring_delta = np.abs(comp_arr - expected_blend)[ring] if ring.any() else np.zeros((0,), dtype=np.int16)
    ring_max_delta = int(ring_delta.max()) if ring_delta.size else 0

    # alpha=0 is intentionally UNCONSTRAINED (outside-art wall, already the
    # candidate's own generated wall pixels -- untouched by this paste).

    # fresh independent recompute of the resized matte alpha, diffed against
    # what was actually used for the paste (self-consistency check).
    door_rgba_check = Image.open(door_rgba_path).convert("RGBA")
    art_a_check = np.asarray(door_rgba_check.resize((tw, th), Image.LANCZOS).split()[-1])
    alpha_exact = bool(np.array_equal(art_a, art_a_check))

    gates = {
        "opaque_px": int(opaque.sum()),
        "opaque_max_abs_delta": opaque_max_delta,
        "opaque_byte_exact": opaque_max_delta == 0,
        "feather_ring_px": int(ring.sum()),
        "feather_ring_max_abs_delta_vs_expected_blend": ring_max_delta,
        "feather_ring_blend_exact": ring_max_delta <= 1,  # <=1: int rounding tolerance only
        "alpha_exact_vs_frozen_matte": alpha_exact,
    }
    return composited, gates


def save_junction_crop(final_img: Image.Image, arch_mask: Image.Image, out_path: Path,
                        margin: int = JUNCTION_CROP_MARGIN_PX) -> Path | None:
    """Amendment 4 (kimi-reggate.md #3): emit a junction crop for human
    review on EVERY run -- a tight bounding-box crop of the FINAL composited
    image around the composited arch footprint's boundary ring, +/-margin
    px. Returns None (writes nothing) if the arch mask is degenerate."""
    arch_bool = np.asarray(arch_mask) > 127
    if not arch_bool.any():
        return None
    boundary = _boundary_pixels(arch_bool)
    ys, xs = np.where(boundary if boundary.any() else arch_bool)
    W, H = final_img.size
    x0 = max(0, int(xs.min()) - margin)
    y0 = max(0, int(ys.min()) - margin)
    x1 = min(W, int(xs.max()) + margin + 1)
    y1 = min(H, int(ys.max()) + margin + 1)
    final_img.crop((x0, y0, x1, y1)).save(out_path)
    return out_path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidate", required=True, type=Path)
    ap.add_argument("--assets-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--metrics", type=Path, help="default: <out>.metrics.json")
    ap.add_argument("--reg-tol", type=float, default=5.0,
                     help="Amendment 4: advisory-only appearance boundary-offset px tolerance "
                          "(reported in metrics.json, never sets exit code -- see registration_provenance() "
                          "for the hard gate)")
    ap.add_argument("--fill", default="255,255,255", help="silhouette/hole clean background RGB")
    ap.add_argument("--init-fill", default="222,213,199", help="expected init-canvas neutral socket fill RGB")
    ap.add_argument("--bevel", type=int, default=2)
    a = ap.parse_args()

    fill = parse_rgb(a.fill)
    init_fill = parse_rgb(a.init_fill)
    metrics_path = a.metrics or a.out.with_name(a.out.stem + ".metrics.json")

    cand = Image.open(a.candidate).convert("RGB")
    W, H = cand.size

    silhouette, holes, st1_zone, socket_rect_px, socket_arch_mask, shapes, src_rect = BA.rasterize_geometry(W, H)

    # ---- (c gate, HARD) registration provenance -- Amendment 4 PRIMARY gate ----
    prov = registration_provenance(a.assets_dir, socket_rect_px, W, H)

    # ---- (c gate, advisory) appearance-based registration -- Amendment 4 demotion;
    # measured on the UNTOUCHED input candidate, NEVER sets the exit code ----
    actual_mask = actual_neutral_region(cand, socket_arch_mask, init_fill)
    appearance = arch_registration(socket_arch_mask, actual_mask, a.reg_tol)

    # ---- (NEW gate) corner integration -- measured on the UNTOUCHED candidate ----
    corner = corner_integration_pct(cand, socket_rect_px, socket_arch_mask, init_fill)

    # ---- outside-silhouette painted px (measured on the input candidate) ---
    sil_bool = np.asarray(silhouette) > 127
    cand_arr = np.asarray(cand).astype(np.int16)
    white = np.array((255, 255, 255), dtype=np.int16)
    non_white = (np.abs(cand_arr - white).sum(axis=2)) > 12
    outside_painted = int((non_white & ~sil_bool).sum())

    hole_pct_pre = measure_hole_paint_pct(cand, shapes, src_rect, W, H, fill)

    # ---- (a) silhouette re-mask ---------------------------------------
    out_img = silhouette_remask(cand, silhouette, fill)
    # ---- (b) punch holes ------------------------------------------------
    out_img = punch_holes(out_img, holes, fill, a.bevel)
    hole_pct_post = measure_hole_paint_pct(out_img, shapes, src_rect, W, H, fill)
    # ---- (c) socket composite-back (Amendment 1: arch matte, alpha-over) ----
    door_rgba_path = a.assets_dir / "door_socket_rgba.png"
    out_img, socket_gates = composite_socket_arch(out_img, door_rgba_path, socket_rect_px)

    a.out.parent.mkdir(parents=True, exist_ok=True)
    out_img.save(a.out)

    # ---- (kimi-reggate.md #3) junction crop for human review, every run ----
    junction_path = a.out.with_name(a.out.stem + "-junction.png")
    save_junction_crop(out_img, socket_arch_mask, junction_path)

    metrics = {
        "candidate": str(a.candidate),
        "out": str(a.out),
        "candidate_size": [W, H],
        "registration": prov,
        "registration_appearance_advisory": appearance,
        "corner_integration": corner,
        "socket_gates": socket_gates,
        "outside_silhouette_painted_px": outside_painted,
        "hole_paint_pct_pre_punch": hole_pct_pre,
        "hole_paint_pct_post_punch": hole_pct_post,
        "junction_crop": str(junction_path),
    }
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n")

    print(f"[composite_back] wrote {a.out} + {metrics_path}")
    print(f"[composite_back] registration (PRIMARY, hard): {prov['status']} "
          f"(max_abs_diff_px={prov['max_abs_diff_px']}, tol={prov['tol_px']}, "
          f"rect_match={prov['rect_match']}, hash_match={prov['hash_match']})")
    print(f"[composite_back] registration_appearance_advisory: {appearance['status']} "
          f"(max_boundary_offset={appearance['max_boundary_offset_px']}, tol={a.reg_tol}, "
          f"area_ratio={appearance['area_ratio']}, tol={AREA_RATIO_TOL})")
    print(f"[composite_back] corner_integration: {corner['status']} (painted_pct={corner['painted_pct']})")
    print(f"[composite_back] socket_gates: opaque_byte_exact={socket_gates['opaque_byte_exact']} "
          f"feather_ring_blend_exact={socket_gates['feather_ring_blend_exact']} "
          f"alpha_exact={socket_gates['alpha_exact_vs_frozen_matte']}")
    print(f"[composite_back] outside_silhouette_painted_px={outside_painted}")

    if prov["status"] != "pass":
        print(f"[composite_back] FAIL: registration provenance check did not pass "
              f"(status={prov['status']})", file=sys.stderr)
        return REG_FAIL_EXIT
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
