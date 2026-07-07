"""mask_to_svg.py round-trip fidelity: rasterize the emitted SVG back and IoU it
against the source mask/holes rasters. Binding rule (LANE C brief): reconstructed
geometry must be source-verified, not trusted from the trace alone.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "mask_to_svg.py"

sys.path.insert(0, str(REPO / "scripts"))
import svg_classify as C  # noqa: E402


def _run(mask, out, holes=None, body="nonwhite", pad=0, epsilon=1.0):
    cmd = [sys.executable, str(SCRIPT), "--mask", str(mask), "--out", str(out),
           "--body", body, "--pad", str(pad), "--epsilon", str(epsilon)]
    if holes:
        cmd += ["--holes", str(holes)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r


def _rasterize(svg_path: Path, size):
    """Fill each classified shape's polygon onto an (H, W) boolean canvas, in the
    SVG's own coordinate space (viewBox == mask pixel space at pad=0)."""
    viewbox, shapes = C.extract_shapes(svg_path)
    shapes = C.classify(shapes)
    outer = [s for s in shapes if s.role == "outer_contour"]
    holes = [s for s in shapes if s.role == "internal_cutout"]
    W, H = size
    outer_mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(outer_mask)
    for s in outer:
        d.polygon(list(s.polygon.exterior.coords), fill=255)
    outer_arr = np.asarray(outer_mask) > 127

    hole_masks = []
    for s in holes:
        hm = Image.new("L", (W, H), 0)
        ImageDraw.Draw(hm).polygon(list(s.polygon.exterior.coords), fill=255)
        hole_masks.append(np.asarray(hm) > 127)
    return outer_arr, hole_masks


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    inter = int(np.sum(a & b))
    union = int(np.sum(a | b))
    return inter / union if union else 0.0


def test_roundtrip_iou_synthetic_rect_with_holes(tmp_path):
    W, H = 300, 400
    mask = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(mask)
    d.rectangle([20, 20, 279, 379], fill=(0, 0, 0))
    holes = Image.new("RGB", (W, H), (0, 0, 0))
    dh = ImageDraw.Draw(holes)
    dh.ellipse([60, 80, 110, 130], fill=(255, 255, 255))
    dh.ellipse([180, 220, 240, 280], fill=(255, 255, 255))
    mp = tmp_path / "mask.png"
    hp = tmp_path / "holes.png"
    mask.save(mp)
    holes.save(hp)

    out = tmp_path / "panel.svg"
    _run(mp, out, holes=hp, body="nonwhite", pad=0, epsilon=1.0)

    # viewBox is cropped+translated to the outer contour's own bbox (crop_origin
    # from the sidecar), not necessarily identical to source pixel space -> shift
    # the source rasters by the documented crop origin before comparing.
    sidecar = json.loads(out.with_suffix(out.suffix + ".json").read_text())
    x0, y0 = sidecar["crop_origin_in_source_px"]
    Wv, Hv = sidecar["viewbox"][2], sidecar["viewbox"][3]

    def _shift(arr):
        canvas = np.zeros((Hv, Wv), bool)
        sy0, sy1 = max(0, y0), min(H, y0 + Hv)
        sx0, sx1 = max(0, x0), min(W, x0 + Wv)
        dy0, dx0 = sy0 - y0, sx0 - x0
        canvas[dy0:dy0 + (sy1 - sy0), dx0:dx0 + (sx1 - sx0)] = arr[sy0:sy1, sx0:sx1]
        return canvas

    outer_src = _shift(np.all(np.asarray(mask) == 0, axis=2))
    hole_src_white = _shift(np.all(np.asarray(holes) == 255, axis=2))

    outer_rt, hole_rts = _rasterize(out, (Wv, Hv))
    assert _iou(outer_src, outer_rt) >= 0.99

    # each reconstructed hole must correspond (by max IoU) to a source hole region
    assert len(hole_rts) == 2
    from scipy import ndimage  # type: ignore
    lbl, n = ndimage.label(hole_src_white)
    src_holes = [lbl == i for i in range(1, n + 1)]
    for rt in hole_rts:
        best = max(_iou(rt, sh) for sh in src_holes)
        assert best >= 0.97


def test_roundtrip_iou_real_door_panel():
    geo = REPO / "tasks" / "marriott-hospital" / "geometry" / "v3"
    mask_path = geo / "door-mask.png"
    holes_path = geo / "door-holes.png"
    svg_path = geo / "door-panel.svg"
    assert svg_path.exists(), "door-panel.svg must already be generated in-repo"

    mask = np.asarray(Image.open(mask_path).convert("RGB"))
    holes = np.asarray(Image.open(holes_path).convert("RGB"))
    sidecar = json.loads(svg_path.with_suffix(svg_path.suffix + ".json").read_text())
    assert sidecar["body_mode"] == "nonblack"  # door-mask.png body = white (non-black), see door-spec.json body_frac
    outer_src_full = np.all(mask != 0, axis=2)  # nonblack body
    hole_src_white_full = np.all(holes == 255, axis=2)

    W, H = mask.shape[1], mask.shape[0]
    x0, y0 = sidecar["crop_origin_in_source_px"]
    Wv, Hv = sidecar["viewbox"][2], sidecar["viewbox"][3]

    def _shift(arr):
        canvas = np.zeros((Hv, Wv), bool)
        sy0, sy1 = max(0, y0), min(H, y0 + Hv)
        sx0, sx1 = max(0, x0), min(W, x0 + Wv)
        dy0, dx0 = sy0 - y0, sx0 - x0
        canvas[dy0:dy0 + (sy1 - sy0), dx0:dx0 + (sx1 - sx0)] = arr[sy0:sy1, sx0:sx1]
        return canvas

    outer_src = _shift(outer_src_full)
    hole_src_white = _shift(hole_src_white_full)

    outer_rt, hole_rts = _rasterize(svg_path, (Wv, Hv))
    # the SVG's outer-contour path encodes the silhouette only; holes are separate
    # <path class="hole"> elements meant to be subtracted (same convention consumers
    # use, e.g. svg_geometry_check.py's contour_mask & ~holes_mask). door-mask.png's
    # body raster already has the 6 holes punched out of it, so subtract the
    # reconstructed holes from the filled outer polygon before comparing apples-to-apples.
    holes_union_rt = np.zeros_like(outer_rt)
    for hm in hole_rts:
        holes_union_rt |= hm
    outer_iou = _iou(outer_src, outer_rt & ~holes_union_rt)
    assert outer_iou >= 0.99, f"outer contour round-trip IoU {outer_iou} < 0.99"

    from scipy import ndimage  # type: ignore
    lbl, n = ndimage.label(hole_src_white)
    assert n == 6
    src_holes = [lbl == i for i in range(1, n + 1)]
    assert len(hole_rts) == 6
    per_hole_ious = []
    for rt in hole_rts:
        best = max(_iou(rt, sh) for sh in src_holes)
        per_hole_ious.append(best)
        assert best >= 0.97, f"hole round-trip IoU {best} < 0.97"
    print("door-panel round-trip: outer_iou=%.4f hole_ious=%s" % (
        outer_iou, [round(v, 4) for v in per_hole_ious]))
