"""fit_gate.py — creature/element overlap + border no-crop checks (synthetic spec)."""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "scripts" / "fit_gate.py"

W, H = 200, 100
SCALE = 1.0


def _spec(tmp_path):
    # a single "PART" part whose crop box is the whole 200x100 render, in
    # doc-point space identical to render-pixel space (ab_x=[0,W], scale=1).
    spec = {
        "ab_x": [0, W],
        "ab_top": H,
        "render_scale": SCALE,
        "parts": {
            "PART": {
                "cut_ltrb": [0, H, W, 0],
                "fish_floor_y": H / 2,
            }
        },
    }
    p = tmp_path / "geometry_spec.json"
    p.write_text(json.dumps(spec))
    return p


def _render(tmp_path):
    im = Image.new("RGB", (W, H), "white")
    p = tmp_path / "render.png"
    im.save(p)
    return p


def _creature_alpha(tmp_path, box):
    """RGBA image with a solid fg blob at `box` (l,t,r,b) in image pixel coords."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle(box, fill=(200, 50, 50, 255))
    p = tmp_path / "creature.png"
    im.save(p)
    return p


def _candidate(tmp_path, box, size=(100, 60), margin_ok=True, name="cand.png"):
    """Candidate element image (non-white = painted); box in candidate-local coords."""
    cw, ch = size
    im = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle(box, fill=(30, 120, 30, 255))
    p = tmp_path / name
    im.save(p)
    return p


def _run(args):
    r = subprocess.run([sys.executable, str(GATE)] + args, capture_output=True, text=True)
    return r


# --- overlap: candidate overlapping the creature mask -----------------------

def test_check_overlap_fails_at_ceiling(tmp_path):
    spec = _spec(tmp_path)
    render = _render(tmp_path)
    # creature blob covers the bottom band where the candidate is placed
    creature = _creature_alpha(tmp_path, (60, 60, 140, 100))
    cand = _candidate(tmp_path, (5, 5, 95, 55))  # nearly-full painted candidate
    r = _run([
        "check", "PART", str(cand),
        "--panel-spec", str(spec), "--render", str(render), "--creature-alpha", str(creature),
        "--scale", "0.5", "--overlap-max", "0.5",
    ])
    rep = json.loads(r.stdout)
    assert rep["overlap_pct"] > 0
    assert r.returncode == 1
    assert rep["pass"] is False


def test_check_clean_candidate_passes(tmp_path):
    spec = _spec(tmp_path)
    render = _render(tmp_path)
    # creature blob confined to the top-left, far from where the candidate lands
    creature = _creature_alpha(tmp_path, (0, 0, 10, 10))
    cand = _candidate(tmp_path, (5, 5, 95, 55))
    r = _run([
        "check", "PART", str(cand),
        "--panel-spec", str(spec), "--render", str(render), "--creature-alpha", str(creature),
        "--scale", "0.5", "--overlap-max", "0.5",
    ])
    rep = json.loads(r.stdout)
    assert rep["overlap_pct"] == 0
    assert r.returncode == 0
    assert rep["pass"] is True


# --- border no-crop check ----------------------------------------------------

def test_border_fails_on_edge_touching_image(tmp_path):
    im = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([0, 40, 20, 60], fill=(30, 120, 30, 255))  # touches left edge
    p = tmp_path / "edge.png"
    im.save(p)
    r = _run(["border", str(p), "--strip-px", "3", "--max-occupancy", "0.02"])
    rep = json.loads(r.stdout)
    assert rep["border_pass"] is False
    assert r.returncode == 1


def test_border_passes_on_margined_image(tmp_path):
    im = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([20, 20, 80, 80], fill=(30, 120, 30, 255))  # well inside
    p = tmp_path / "margined.png"
    im.save(p)
    r = _run(["border", str(p), "--strip-px", "3", "--max-occupancy", "0.02"])
    rep = json.loads(r.stdout)
    assert rep["border_pass"] is True
    assert r.returncode == 0


# --- search: largest passing scale -------------------------------------------

def test_search_returns_largest_passing_scale(tmp_path):
    spec = _spec(tmp_path)
    render = _render(tmp_path)
    # creature blob sits at the very bottom edge; bigger candidate scale -> more overlap
    creature = _creature_alpha(tmp_path, (0, 95, 200, 100))
    cand = _candidate(tmp_path, (5, 5, 95, 55))
    r = _run([
        "search", "PART", str(cand),
        "--panel-spec", str(spec), "--render", str(render), "--creature-alpha", str(creature),
        "--overlap-max", "10", "--scale-range", "0.3:1.0:0.1",
    ])
    rep = json.loads(r.stdout)
    assert rep["best"] is not None
    passing = [s for s in rep["sweep"] if s["pass"]]
    assert rep["best"]["scale"] == max(s["scale"] for s in passing)
    # never shrink-to-pass: best must be the max of the passing set, not just any pass
    assert all(s["scale"] <= rep["best"]["scale"] for s in passing)
