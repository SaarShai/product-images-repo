import importlib.util
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
DEPTH_PATH = REPO_ROOT / "scripts" / "make_depth_from_mask.py"


spec = importlib.util.spec_from_file_location("make_depth_from_mask", DEPTH_PATH)
make_depth_from_mask = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(make_depth_from_mask)


def test_depth_from_mask_keeps_size_bright_portal_midgrey_background_and_smooth_transition():
    mask = np.zeros((31, 31), dtype=np.uint8)
    mask[9:22, 9:22] = 255

    depth = make_depth_from_mask.depth_from_mask(mask, blur_radius=2.0)
    arr = np.asarray(depth)

    assert depth.size == (31, 31)
    assert arr[15, 15] > 245
    assert 124 <= arr[0, 0] <= 132
    assert 145 < arr[8, 15] < 235

    inverted = np.asarray(make_depth_from_mask.depth_from_mask(mask, invert=True, blur_radius=2.0))
    assert inverted[15, 15] < 10
    assert 124 <= inverted[0, 0] <= 132
