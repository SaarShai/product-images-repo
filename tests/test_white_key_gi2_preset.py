"""white_key.py --preset gi2: named regression-proof preset (thresh=246, erode=0)
for gpt-image-2 art, whose thin pure-white (255,255,255) rim highlights get eaten
by the default erode=2 fringe-kill step. See advisor ruling: prose memory alone
did not prevent recurrence; this fixture asserts the failure AND the fix.
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
WK = REPO / "scripts" / "white_key.py"


def test_gi2_preset_maps_to_thresh_246_erode_0():
    out = subprocess.run([sys.executable, str(WK), "--help"], capture_output=True, text=True)
    assert out.returncode == 0
    assert "gi2" in out.stdout


def _rim_tube(tmp_path):
    """A colored tube shape with a thin near-white rim highlight band sitting
    right at its top boundary against the background -- the coral-panel failure
    geometry. The rim color (240,242,239) is near-white but not pure 255: it
    qualifies as background-white at the default thresh=238 (so the border flood
    walks straight through it into the art) but NOT at the tighter thresh=246
    used by --preset gi2 (so it stays foreground)."""
    w, h = 400, 300
    img = np.full((h, w, 3), 255, np.uint8)                # white background
    img[95:100, 60:340] = [240, 242, 239]                  # thin near-white rim band
    img[100:220, 60:340] = [200, 90, 60]                    # colored tube body
    p = tmp_path / "tube.png"
    Image.fromarray(img).save(p)
    return p


def _key(img, out, *extra):
    subprocess.run([sys.executable, str(WK), "--image", str(img), "--out", str(out), *extra],
                   check=True, capture_output=True, text=True)
    return np.asarray(Image.open(out).convert("RGBA"))[:, :, 3]


def test_default_params_remove_rim_highlight(tmp_path):
    """Documents the failure: default thresh=238 erode=2 keys the near-white rim
    transparent (the flood walks through it since it clears the loose threshold)."""
    img = _rim_tube(tmp_path)
    a = _key(img, tmp_path / "default.png")
    rim = a[95:100, 60:340]
    assert float((rim > 200).mean()) < 0.1          # rim pixels wrongly keyed transparent
    bg = a[0:20, 0:20]
    assert float(bg.mean()) < 20                     # background still transparent


def test_gi2_preset_preserves_rim_highlight(tmp_path):
    """The fix: --preset gi2 (thresh=246 erode=0) keeps the rim opaque while the
    background still keys transparent."""
    img = _rim_tube(tmp_path)
    a = _key(img, tmp_path / "gi2.png", "--preset", "gi2")
    # interior of rim: away from feather-softened x-ends and the true-bg/rim
    # y-transition at row 95 (row 96-99 sits solidly inside the fg silhouette)
    rim = a[96:100, 100:300]
    assert float((rim > 200).mean()) > 0.9            # rim preserved
    bg = a[0:20, 0:20]
    assert float(bg.mean()) < 20                       # background still transparent
