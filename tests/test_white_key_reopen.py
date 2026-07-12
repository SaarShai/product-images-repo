"""white_key.py --reopen-interior: reopen trapped (enclosed) pure-white background
while protecting tinted (cream/blush) art highlights and tiny glints.

Calibrated against the double Marine Bed Wrapper round-1 candidates (M1/M3/M6),
whose keyed RGBAs left enclosed near-white gaps between coral branches opaque.
See REVIEW/transparent-clear-edge-claude/RESULTS.md (round-1 verdict, trapped-bg note).
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
WK = REPO / "scripts" / "white_key.py"


def _subject_with_holes(tmp_path):
    """A colored subject slab enclosing three holes, at production scale so the
    fraction-based size floor behaves as it does on real ~1MP renders:
      A pure-white   -> trapped background (should reopen)
      B cream/blush  -> tinted art highlight (must be protected by purity)
      C tiny pure    -> below the size floor (must be protected by area)
    plus the normal border background (always transparent)."""
    w, h = 1500, 900
    img = np.full((h, w, 3), 255, np.uint8)          # white background
    img[120:780, 270:1230] = [80, 150, 170]          # teal slab -> encloses the holes
    img[330:600, 360:600] = [255, 255, 255]          # A pure-white  (~64800 px)
    img[330:600, 690:930] = [252, 247, 240]          # B cream       (~64800 px)
    img[400:410, 1050:1060] = [255, 255, 255]        # C tiny pure   (~100 px < floor)
    p = tmp_path / "subject.png"
    Image.fromarray(img).save(p)
    return p


def _key(img, out, *extra):
    subprocess.run([sys.executable, str(WK), "--image", str(img), "--out", str(out),
                    "--erode", "1", "--feather", "0.5", *extra],
                   check=True, capture_output=True, text=True)
    return np.asarray(Image.open(out).convert("RGBA"))[:, :, 3]


def _alpha(a, y0, y1, x0, x1):
    return float(a[y0:y1, x0:x1].mean())


def test_flag_off_leaves_trapped_white_opaque(tmp_path):
    """Opt-in: without the flag, an enclosed pure-white hole stays opaque (the
    documented base behavior the flag exists to fix)."""
    img = _subject_with_holes(tmp_path)
    a = _key(img, tmp_path / "off.png")
    assert _alpha(a, 420, 510, 420, 540) > 235      # pure hole A NOT reopened
    assert _alpha(a, 20, 80, 20, 180) < 20          # border bg still transparent


def test_reopen_opens_pure_trapped_white(tmp_path):
    img = _subject_with_holes(tmp_path)
    a = _key(img, tmp_path / "on.png", "--reopen-interior")
    assert _alpha(a, 420, 510, 420, 540) < 20       # pure hole A reopened


def test_reopen_protects_tinted_tiny_and_subject(tmp_path):
    img = _subject_with_holes(tmp_path)
    a = _key(img, tmp_path / "on.png", "--reopen-interior")
    assert _alpha(a, 420, 510, 750, 870) > 235      # B cream/blush protected (purity gate)
    assert _alpha(a, 402, 408, 1052, 1058) > 235    # C tiny pure protected (size gate)
    assert _alpha(a, 150, 250, 900, 1080) > 250     # subject slab stays opaque
    assert _alpha(a, 20, 80, 20, 180) < 20          # border bg still transparent


def test_reopen_selects_only_near_white_pixels(tmp_path):
    """Structural safety: the reopened region is a subset of near-white pixels, so
    no saturated/colored art pixel is ever *selected* as background. (The existing
    --erode step then eats a 1px fringe of the hole edge, same as it does at the
    outer contour; disable it here to isolate the selection.)"""
    img = _subject_with_holes(tmp_path)
    off = _key(img, tmp_path / "off.png", "--erode", "0", "--feather", "0")
    on = _key(img, tmp_path / "on.png", "--reopen-interior", "--erode", "0", "--feather", "0")
    reopened = (off > 127) & (on <= 127)            # pixels the flag turned transparent
    rgb = np.asarray(Image.open(img).convert("RGB")).astype(int)
    spread = rgb.max(2) - rgb.min(2)
    assert reopened.sum() > 0                        # it did something
    assert int((spread[reopened] > 18).sum()) == 0  # every reopened pixel is near-white
