"""tests/test_content_gate.py — scripts/content_gate.py whiteness + flap-content checks.

Synthetic geometry (mask + spec) fixtures; no network.
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "scripts" / "content_gate.py"

W, H = 100, 200


def _make_geom(tmp_path):
    geom = tmp_path / "geom"
    geom.mkdir()
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rectangle([10, 20, 89, 199], fill=255)  # body interior
    mask.save(geom / "door-mask.png")
    spec = {
        "panel": "door",
        "size_px": [W, H],
        "door_anchor_frac": [0.2, 0.5, 0.8, 0.99],
    }
    (geom / "door-spec.json").write_text(json.dumps(spec))
    return geom


def _run(image_path, geom_dir, overlay=None):
    args = [sys.executable, str(GATE), "--image", str(image_path), "--geom", str(geom_dir)]
    if overlay:
        args += ["--overlay", str(overlay)]
    r = subprocess.run(args, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_whiteness_flags_colored_background_outside_body(tmp_path):
    geom = _make_geom(tmp_path)
    img = Image.new("RGB", (W, H), (30, 120, 200))  # saturated blue everywhere, incl. outside
    ImageDraw.Draw(img).rectangle([10, 20, 89, 199], fill=(140, 80, 60))  # body painted too
    p = tmp_path / "cand.png"
    img.save(p)
    ov = tmp_path / "overlay.png"
    rep = _run(p, geom, overlay=ov)
    assert rep["outside_whiteness"]["verdict"] == "FAIL"
    assert rep["outside_whiteness"]["frac_bad_outside"] > 0.05
    assert ov.exists()


def test_whiteness_passes_white_background_outside_body(tmp_path):
    geom = _make_geom(tmp_path)
    img = Image.new("RGB", (W, H), "white")  # near-white everywhere outside body
    ImageDraw.Draw(img).rectangle([10, 20, 89, 199], fill=(140, 80, 60))
    p = tmp_path / "cand.png"
    img.save(p)
    ov = tmp_path / "overlay.png"
    rep = _run(p, geom, overlay=ov)
    assert rep["outside_whiteness"]["verdict"] == "PASS"
    assert rep["outside_whiteness"]["frac_bad_outside"] <= 0.05
    assert ov.exists()


def test_flap_content_reports_when_anchor_present(tmp_path):
    geom = _make_geom(tmp_path)
    img = Image.new("RGB", (W, H), "white")
    ImageDraw.Draw(img).rectangle([10, 20, 89, 199], fill=(140, 80, 60))
    p = tmp_path / "cand.png"
    img.save(p)
    rep = _run(p, geom)
    assert rep["flap_content"]["available"] is True
    assert rep["flap_content"]["verdict"] in ("OK", "WARN")
    assert "band_px" in rep["flap_content"]


def test_overlay_defaults_next_to_image_when_not_given(tmp_path):
    geom = _make_geom(tmp_path)
    img = Image.new("RGB", (W, H), "white")
    ImageDraw.Draw(img).rectangle([10, 20, 89, 199], fill=(140, 80, 60))
    p = tmp_path / "raw.png"
    img.save(p)
    rep = _run(p, geom)
    default_overlay = tmp_path / "raw-content-gate-overlay.png"
    assert Path(rep["overlay"]) == default_overlay
    assert default_overlay.exists()
