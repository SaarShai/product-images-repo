"""vector_spec.py — native-vector geometry contract from the true .ai bezier paths.

Locks the properties that the raster reconstruction (master_spec.py) got wrong and
that the user flagged: a SMOOTH door arch (not the jagged staircase), full-body
panels (the area-based body/hole split, not largest-component-only), and the true
source-verified door anchor. Requires tasks/_templates/master_paths.json.
"""
import json
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
PATHS = REPO / "tasks" / "_templates" / "master_paths.json"

pytestmark = pytest.mark.skipif(not PATHS.exists(), reason="master_paths.json not present")


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    import scripts.vector_spec as V
    out = tmp_path_factory.mktemp("v3")
    return V.build(str(PATHS), 55.48, str(out)), out


def test_all_five_panels_emitted(report):
    rep, _ = report
    assert set(rep) == {"left", "door", "right", "stab1", "stab2"}
    assert all("error" not in v for v in rep.values()), rep


def test_panels_are_full_body(report):
    """The area-based split must keep every large region as paintable body.
    master_spec's largest-component-only logic dropped 2 of the door's 3 thirds
    (body_frac collapsed to ~0.34); the real body is ~0.9."""
    rep, _ = report
    for p in ("left", "door", "right"):
        assert rep[p]["body_frac"] > 0.85, (p, rep[p]["body_frac"])
    for p in ("stab1", "stab2"):
        assert rep[p]["body_frac"] > 0.90, (p, rep[p]["body_frac"])


def test_door_anchor_matches_source(report):
    """Source-verified anchor, not the r16c synthetic wide arch [0.186..0.815]."""
    rep, _ = report
    a = rep["door"]["door_anchor_frac"]
    assert a[0] == pytest.approx(0.27, abs=0.03), a  # left side, NOT 0.186
    assert a[2] == pytest.approx(0.73, abs=0.03), a  # right side, NOT 0.815
    assert (a[2] - a[0]) == pytest.approx(0.46, abs=0.04), a  # width, NOT ~0.63


def test_door_arch_is_smooth(report):
    """The whole point of the rebuild: the arch must be a smooth curve, not the
    raster staircase. Measure per-column top-edge of the door control map across
    the arch span; a smooth arch changes row by <=~2px/col, a jagged one spikes."""
    from PIL import Image
    _, out = report
    ctrl = np.array(Image.open(out / "door-control.png").convert("L")) > 127
    h, w = ctrl.shape
    tops = []
    for x in range(w):
        ys = np.where(ctrl[: h // 2, x])[0]  # top-edge in the upper half (arch band)
        if len(ys):
            tops.append((x, ys.min()))
    xs = [t[0] for t in tops]
    ytop = [t[1] for t in tops]
    # over the central 60% of the arch span, consecutive-column jumps stay small
    lo, hi = int(len(xs) * 0.2), int(len(xs) * 0.8)
    jumps = np.abs(np.diff(ytop[lo:hi]))
    assert jumps.max() <= 4, f"max column jump {jumps.max()} — arch not smooth"
    assert np.percentile(jumps, 95) <= 2, f"95pct jump {np.percentile(jumps,95)}"


def test_control_map_is_solid_not_dashed(report):
    """Control maps must be solid strokes only (dashes leak into art as dot marks).
    Count connected components after a small dilation that bridges the 1px-diagonal
    4-connectivity gaps but NOT dash gaps: a solid map collapses to a handful of
    large strokes; a dashed one stays a spray of fragments."""
    from PIL import Image
    import scripts.vector_spec as V
    _, out = report
    ctrl = np.array(Image.open(out / "door-control.png").convert("L")) > 127
    bridged = V._dilate1(V._dilate1(ctrl))  # 2px: closes anti-alias/diagonal gaps
    comps = [c for c in V.components(bridged) if c.sum() > 100]
    # solid: the contour + arch + interior cuts merge into few large strokes
    assert len(comps) <= 20, f"{len(comps)} stroke fragments — dashes leaking?"
