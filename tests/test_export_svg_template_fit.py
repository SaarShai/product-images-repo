"""Regression test for export_svg_template_fit.py's hand-rolled SVG path
tokenizer (geometry-evidentiary-princess-n02 Finding 5).

Root cause: the tokenizer's command character class only recognised
M/L/H/V/C/Z. An SVG path using the "S" (smooth cubic curveto) command —
present in the frozen princess narrow panel 02 template — was silently
dropped by the regex, desynchronising the number-token stream and raising
``ValueError: Expected numeric SVG path token`` deep inside read_number().
"""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "export_svg_template_fit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("export_svg_template_fit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    # register before exec: dataclasses + `from __future__ import annotations`
    # need cls.__module__ to resolve via sys.modules during class creation.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


E = load_module()

# Minimal reproduction: a path that starts with a normal cubic curve (C) and
# then continues with a smooth cubic curve (S) — the construct that broke
# the pre-fix tokenizer. This mirrors path[7]/path[8] in the real princess
# narrow panel 02 template ("...c...S..." / "...s...").
SMOOTH_CUBIC_PATH_D = "M0,0 C10,10 20,20 30,30 S40,40 50,50 Z"


def test_parse_path_d_handles_smooth_cubic_command():
    """Pre-fix: raises ValueError('Expected numeric SVG path token').

    Post-fix: parses cleanly and the S-segment's reflected curve lands at
    the explicit smooth-curveto endpoint (50, 50), with the subpath closed
    back to the start point (0, 0).
    """
    subpaths = E.parse_path_d(SMOOTH_CUBIC_PATH_D)
    assert len(subpaths) == 1
    poly = subpaths[0]
    # first point is the M start
    assert poly[0] == (0.0, 0.0)
    # the S segment's endpoint (50, 50) must appear before the Z-closure
    # back to (0, 0)
    assert poly[-2] == pytest.approx((50.0, 50.0))
    assert poly[-1] == (0.0, 0.0)


def test_parse_path_d_smooth_cubic_without_prior_curve_uses_current_as_control():
    """S with no preceding C/S: first control point = current point (per
    SVG spec), i.e. degenerates gracefully instead of crashing."""
    d = "M0,0 S10,0 10,10 Z"
    subpaths = E.parse_path_d(d)
    assert len(subpaths) == 1
    assert subpaths[0][0] == (0.0, 0.0)
    assert subpaths[0][-2] == pytest.approx((10.0, 10.0))


def test_read_template_parses_princess_style_smooth_cubic_svg(tmp_path):
    """End-to-end: a template SVG containing an S path command (as found in
    the frozen princess narrow panel 02 template) must be readable via
    read_template(), not raise ValueError."""
    svg = tmp_path / "template.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        f'<path d="{SMOOTH_CUBIC_PATH_D}"/>'
        "</svg>"
    )
    geometry = E.read_template(svg)
    assert geometry.viewbox == (0.0, 0.0, 100.0, 100.0)
    assert len(geometry.paths) == 1
