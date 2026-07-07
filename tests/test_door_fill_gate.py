"""door_fill_gate.py — geometry/rule parsing and fill-measurement tests.

Runs entirely on synthetic fixtures (no network, no repo geometry files
required for the pass/half-fill checks) so the suite is fast and isolated;
one additional test exercises the real tasks/marriott-hospital/geometry/v3
fixture if present, to catch drift against the actual door-control.png.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "scripts" / "door_fill_gate.py"
REAL_GEOM = REPO / "tasks" / "marriott-hospital" / "geometry" / "v3"


def _make_synthetic_geom(tmp_path: Path, w=1200, h=1800):
    """A simple rectangular 'door' portal traced on black, with a spec whose
    door_anchor_frac matches the drawn rectangle exactly. Sized close to the
    real geometry fixture's scale (1692x2400) so the gate's fixed-pixel line
    dilation (needed to bridge real double-line gaps; see trace_portal_mask)
    stays a small fraction of the frame, matching production tolerance math."""
    x0, y0, x1, y1 = 240, 480, 960, h  # bottom edge coincides with image bottom,
    # matching the real control image's "door bottom = panel bottom" pattern.
    control = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(control)
    # closed portal outline: two verticals + a top horizontal (bottom is the
    # image edge itself, deliberately left undrawn, then closed by a border
    # line placed a couple of px below y1 like the real control images do).
    draw.line([(x0, y0), (x0, h - 1)], fill=255, width=2)
    draw.line([(x1, y0), (x1, h - 1)], fill=255, width=2)
    draw.line([(x0, y0), (x1, y0)], fill=255, width=2)
    draw.line([(0, h - 3), (w - 1, h - 3)], fill=255, width=2)  # panel bottom edge
    control_path = tmp_path / "door-control.png"
    control.save(control_path)

    spec = {
        "door_anchor_frac": [x0 / w, y0 / h, x1 / w, (h - 1) / h],
    }
    spec_path = tmp_path / "door-spec.json"
    spec_path.write_text(json.dumps(spec))
    return control_path, spec_path, (x0, y0, x1, y1, w, h)


def _run(image_path, geom_dir, overlay_path, extra=None):
    cmd = [sys.executable, str(GATE), "--image", str(image_path), "--geom", str(geom_dir),
           "--overlay", str(overlay_path)]
    if extra:
        cmd += extra
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def test_full_fill_scores_near_one(tmp_path):
    control_path, spec_path, (x0, y0, x1, y1, w, h) = _make_synthetic_geom(tmp_path)
    cand = Image.new("RGB", (w, h), "white")
    ImageDraw.Draw(cand).rectangle([x0, y0, x1, y1], fill=(30, 100, 200))  # saturated blue
    cand_path = tmp_path / "cand.png"
    cand.save(cand_path)

    overlay_path = tmp_path / "overlay.png"
    code, out, err = _run(cand_path, tmp_path, overlay_path)
    assert code == 0, err
    result = json.loads(out)
    assert result["verdict"] == "PASS"
    assert result["door_fill"] > 0.95
    assert overlay_path.exists()


def test_half_size_rect_scores_near_half(tmp_path):
    control_path, spec_path, (x0, y0, x1, y1, w, h) = _make_synthetic_geom(tmp_path)
    # a door leaf painted at half the portal's height, centered — should
    # measure roughly 0.5 fill (calibration case from the brief).
    portal_h = y1 - y0
    half_y0 = y0 + portal_h // 2
    cand = Image.new("RGB", (w, h), "white")
    ImageDraw.Draw(cand).rectangle([x0, half_y0, x1, y1], fill=(30, 100, 200))
    cand_path = tmp_path / "cand.png"
    cand.save(cand_path)

    overlay_path = tmp_path / "overlay.png"
    code, out, err = _run(cand_path, tmp_path, overlay_path)
    assert code == 0, err
    result = json.loads(out)
    assert 0.4 <= result["door_fill"] <= 0.6
    assert result["verdict"] in ("WARN", "FAIL")


def test_no_door_paint_scores_near_zero(tmp_path):
    control_path, spec_path, (x0, y0, x1, y1, w, h) = _make_synthetic_geom(tmp_path)
    cand = Image.new("RGB", (w, h), "white")  # nothing blue painted at all
    cand_path = tmp_path / "cand.png"
    cand.save(cand_path)

    overlay_path = tmp_path / "overlay.png"
    code, out, err = _run(cand_path, tmp_path, overlay_path)
    assert code == 0, err
    result = json.loads(out)
    assert result["door_fill"] < 0.1
    assert result["verdict"] == "FAIL"


def test_pass_and_warn_thresholds_match_binding_verdict(tmp_path):
    """Per the binding user verdict: PASS >= 0.90, WARN 0.75-0.90, FAIL < 0.75
    (door must fill the ENTIRE flap region — no normal-proportion door)."""
    control_path, spec_path, _ = _make_synthetic_geom(tmp_path)
    r = subprocess.run([sys.executable, str(GATE), "--help"], capture_output=True, text=True)
    assert "--pass-fill" in r.stdout and "--warn-fill" in r.stdout

    # inspect the module's own defaults directly to pin the contract
    src = GATE.read_text()
    assert '"--pass-fill", type=float, default=0.9' in src
    assert '"--warn-fill", type=float, default=0.75' in src


def test_geometry_roundtrip_no_network(tmp_path):
    """trace_portal_mask + clip_to_spec_bbox + verify_portal_bbox roundtrip:
    a portal traced exactly at door_anchor_frac must verify within tolerance
    with no network access and no extra inputs beyond the two fixture files."""
    sys.path.insert(0, str(REPO / "scripts"))
    import door_fill_gate as dfg

    control_path, spec_path, _ = _make_synthetic_geom(tmp_path)
    spec = json.loads(spec_path.read_text())
    control = Image.open(control_path)

    interior = dfg.trace_portal_mask(control, spec["door_anchor_frac"])
    portal = dfg.clip_to_spec_bbox(interior, spec["door_anchor_frac"])
    ok, measured = dfg.verify_portal_bbox(portal, spec["door_anchor_frac"])
    assert ok, f"measured {measured} vs spec {spec['door_anchor_frac']}"
    assert portal.sum() > 0


def test_real_geometry_fixture_if_present():
    """Non-fatal cross-check against the actual repo geometry fixture, if
    it exists in this checkout (skips cleanly otherwise — no network)."""
    control_path = REAL_GEOM / "door-control.png"
    spec_path = REAL_GEOM / "door-spec.json"
    if not (control_path.exists() and spec_path.exists()):
        return
    sys.path.insert(0, str(REPO / "scripts"))
    import door_fill_gate as dfg

    spec = json.loads(spec_path.read_text())
    control = Image.open(control_path)
    interior = dfg.trace_portal_mask(control, spec["door_anchor_frac"])
    portal = dfg.clip_to_spec_bbox(interior, spec["door_anchor_frac"])
    ok, measured = dfg.verify_portal_bbox(portal, spec["door_anchor_frac"])
    assert ok, f"real geometry drifted: measured {measured} vs spec {spec['door_anchor_frac']}"
    assert portal.sum() > 100000  # sanity: a real door portal is a large region


# ---------------------------------------------------------------------------
# Recalibration: PORTAL-OCCUPANCY metric (hue-agnostic), replacing the old
# blue-only color heuristic.
# ---------------------------------------------------------------------------

def test_segment_painted_is_hue_agnostic_unit():
    """segment_painted must flag ANY non-background paint (teal/pale/green,
    not just blue) — this is the core recalibration from FIX 3."""
    sys.path.insert(0, str(REPO / "scripts"))
    import door_fill_gate as dfg

    rgb = np.zeros((4, 4, 3), dtype=np.uint8)
    rgb[:, :] = (255, 255, 255)          # background: near-white
    rgb[0, 0] = (0, 128, 128)            # teal
    rgb[0, 1] = (200, 230, 200)          # pale green
    rgb[0, 2] = (60, 160, 90)            # saturated green
    rgb[0, 3] = (250, 250, 248)          # near-white, should stay background

    mask = dfg.segment_painted(rgb)
    assert mask[0, 0] and mask[0, 1] and mask[0, 2], "teal/pale/green must count as painted"
    assert not mask[0, 3], "near-white/near-empty must stay background"
    assert not mask[1, 0], "flat white background must not be flagged as painted"


def test_portal_fully_painted_nonwhite_scores_near_one(tmp_path):
    """Portal fully painted with a NON-BLUE color (teal) must score ~1.0 under
    the recalibrated hue-agnostic occupancy metric — this is exactly the case
    the old blue-only heuristic false-negatived."""
    control_path, spec_path, (x0, y0, x1, y1, w, h) = _make_synthetic_geom(tmp_path)
    cand = Image.new("RGB", (w, h), "white")
    ImageDraw.Draw(cand).rectangle([x0, y0, x1, y1], fill=(0, 150, 140))  # teal, not blue
    cand_path = tmp_path / "cand.png"
    cand.save(cand_path)

    overlay_path = tmp_path / "overlay.png"
    code, out, err = _run(cand_path, tmp_path, overlay_path)
    assert code == 0, err
    result = json.loads(out)
    assert result["verdict"] == "PASS"
    assert result["door_fill"] > 0.95


def test_portal_half_painted_scores_near_half(tmp_path):
    control_path, spec_path, (x0, y0, x1, y1, w, h) = _make_synthetic_geom(tmp_path)
    portal_h = y1 - y0
    half_y0 = y0 + portal_h // 2
    cand = Image.new("RGB", (w, h), "white")
    ImageDraw.Draw(cand).rectangle([x0, half_y0, x1, y1], fill=(0, 150, 140))
    cand_path = tmp_path / "cand.png"
    cand.save(cand_path)

    overlay_path = tmp_path / "overlay.png"
    code, out, err = _run(cand_path, tmp_path, overlay_path)
    assert code == 0, err
    result = json.loads(out)
    assert 0.4 <= result["door_fill"] <= 0.6


def test_portal_empty_white_scores_near_zero(tmp_path):
    control_path, spec_path, (x0, y0, x1, y1, w, h) = _make_synthetic_geom(tmp_path)
    cand = Image.new("RGB", (w, h), "white")  # nothing painted at all
    cand_path = tmp_path / "cand.png"
    cand.save(cand_path)

    overlay_path = tmp_path / "overlay.png"
    code, out, err = _run(cand_path, tmp_path, overlay_path)
    assert code == 0, err
    result = json.loads(out)
    assert result["door_fill"] < 0.1
    assert result["verdict"] == "FAIL"
