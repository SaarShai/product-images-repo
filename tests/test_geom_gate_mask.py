"""geom_gate.py --mask-only (mask-authoritative) mode — no SVG required."""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "scripts" / "geom_gate.py"


def _mask(tmp_path, w=100, h=200):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rectangle([10, 20, 90, 199], fill=255)  # touches bottom edge
    p = tmp_path / "mask.png"
    m.save(p)
    return p


def _run(cand, mask):
    r = subprocess.run([sys.executable, str(GATE), "--cand", str(cand), "--mask", str(mask)],
                       capture_output=True, text=True)
    return r.returncode, json.loads(r.stdout)


def test_mask_only_pass_on_filled_panel(tmp_path):
    mask = _mask(tmp_path)
    cand = Image.new("RGB", (100, 200), "white")
    ImageDraw.Draw(cand).rectangle([10, 20, 90, 199], fill=(140, 80, 60))
    cp = tmp_path / "cand.png"; cand.save(cp)
    code, rep = _run(cp, mask)
    assert code == 0 and rep["verdict"] == "PASS"
    assert rep["svg"] is None
    assert rep["fill_inside_contour"] > 0.95


def test_mask_only_fails_near_empty_panel(tmp_path):
    # the r3_right_s1 lesson: outline-only panel must FAIL on fill
    mask = _mask(tmp_path)
    cand = Image.new("RGB", (100, 200), "white")
    ImageDraw.Draw(cand).rectangle([10, 20, 90, 199], outline=(80, 80, 80), width=3)
    cp = tmp_path / "cand.png"; cand.save(cp)
    code, rep = _run(cp, mask)
    assert code == 1 and rep["verdict"] == "FAIL"
    assert "fill_inside_contour" in rep["fails"][0]


def test_mask_only_handles_bucket_drift_dims(tmp_path):
    # candidate at different dims than mask: mask is resized to candidate
    mask = _mask(tmp_path)
    cand = Image.new("RGB", (57, 153), "white")
    ImageDraw.Draw(cand).rectangle([6, 15, 51, 152], fill=(140, 80, 60))
    cp = tmp_path / "cand.png"; cand.save(cp)
    code, rep = _run(cp, mask)
    assert code == 0 and rep["verdict"] == "PASS"


def test_tight_cropped_mask_not_wrongly_inverted(tmp_path):
    # regression 2026-07-05: body touching left/right/bottom border made the
    # old border-frac heuristic flip the mask -> all metrics zeroed
    m = Image.new("L", (100, 200), 0)
    ImageDraw.Draw(m).rectangle([0, 20, 99, 199], fill=255)  # touches 3 borders
    mp = tmp_path / "mask.png"; m.save(mp)
    cand = Image.new("RGB", (100, 200), "white")
    ImageDraw.Draw(cand).rectangle([0, 20, 99, 199], fill=(140, 80, 60))
    cp = tmp_path / "cand.png"; cand.save(cp)
    code, rep = _run(cp, mp)
    assert code == 0 and rep["fill_inside_contour"] > 0.95


def test_no_svg_no_mask_is_an_error(tmp_path):
    cand = tmp_path / "cand.png"
    Image.new("RGB", (10, 10), "white").save(cand)
    r = subprocess.run([sys.executable, str(GATE), "--cand", str(cand)],
                       capture_output=True, text=True)
    assert r.returncode == 2
    assert "--mask is required" in r.stderr
