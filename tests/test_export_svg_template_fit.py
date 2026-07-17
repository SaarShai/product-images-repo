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

# A closed, non-degenerate S-curve path (real area, not a near-straight sliver
# along the diagonal like SMOOTH_CUBIC_PATH_D above) — needed for the
# read_template() end-to-end test below since read_template() now builds real
# Shapely polygons (Finding B) and rejects zero/near-zero-area geometry, unlike
# the pre-Finding-B point-list-only reader SMOOTH_CUBIC_PATH_D was written for.
SMOOTH_CUBIC_PANEL_PATH_D = "M10,10 L90,10 C95,10 95,20 90,30 S85,90 10,90 Z"


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
        f'<path d="{SMOOTH_CUBIC_PANEL_PATH_D}"/>'
        "</svg>"
    )
    geometry = E.read_template(svg)
    assert geometry.viewbox == (0.0, 0.0, 100.0, 100.0)
    assert len(geometry.paths) == 1


# --- Finding B: read_template() ignored <rect> elements entirely (a) and
# unioned internal-cutout <path>/<rect> elements into the paintable panel
# mask (b), so --require-pass could never detect a candidate painting
# straight over a cutout (this template has 4 <rect> cutouts + <path>
# cutouts st1/st2/st4; the export gate reported 0 violations where
# svg_geometry_check.py correctly measured 71.5-98.5% painted holes). -------

CUTOUT_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
    '<path d="M0,0 L100,0 L100,100 L0,100 Z"/>'
    '<rect x="10" y="10" width="20" height="20"/>'
    '<path d="M60,60 L80,60 L80,80 L60,80 Z"/>'
    "</svg>"
)


def _solid_image(path: Path, size: tuple[int, int] = (100, 100), color=(20, 20, 20)) -> None:
    from PIL import Image

    Image.new("RGB", size, color).save(path)


def _clean_candidate_image(path: Path, size: tuple[int, int] = (100, 100)) -> None:
    """Paint the whole panel EXCEPT the two cutout squares (plus a safety
    margin covering the default hex-clearance dilation and mask antialiasing
    at the crisp cutout edge), which stay white."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", size, (20, 20, 20))
    draw = ImageDraw.Draw(img)
    draw.rectangle([2, 2, 38, 38], fill=(255, 255, 255))  # covers the 10,10-30,30 rect cutout + clearance
    draw.rectangle([52, 52, 88, 88], fill=(255, 255, 255))  # covers the 60,60-80,80 path cutout + clearance
    img.save(path)


def test_read_template_excludes_rect_and_path_cutouts_from_paintable_paths(tmp_path):
    """read_template() must classify the <rect> AND the internal <path>
    cutout as holes (geometry.polygons), not paintable panel (geometry.paths).
    Pre-fix: the <rect> was dropped entirely and the cutout <path> was unioned
    into geometry.paths (paintable) instead of geometry.polygons (hole)."""
    svg = tmp_path / "template.svg"
    svg.write_text(CUTOUT_SVG)
    geometry = E.read_template(svg)
    assert len(geometry.paths) == 1  # only the outer 100x100 panel
    assert E.bbox(geometry.paths[0]) == pytest.approx((0.0, 0.0, 100.0, 100.0))
    cutout_bboxes = {tuple(round(v) for v in E.bbox(poly)) for poly in geometry.polygons}
    assert (10, 10, 30, 30) in cutout_bboxes  # the <rect> cutout
    assert (60, 60, 80, 80) in cutout_bboxes  # the internal <path> cutout


def test_candidate_painted_over_cutouts_fails_require_pass(tmp_path):
    """A candidate that paints solidly over BOTH cutouts must FAIL (nonzero
    violations) post-fix. Pre-fix, read_template() never registered the
    cutouts as holes at all, so this candidate falsely PASSED with 0
    violations (geometry-evidentiary-princess-n02 Finding B)."""
    svg = tmp_path / "template.svg"
    svg.write_text(CUTOUT_SVG)
    candidate = tmp_path / "solid.png"
    _solid_image(candidate)

    metadata = E.export_svg_template_fit(
        image_path=candidate, svg_path=svg, out_dir=tmp_path / "out", prefix="solid",
        output_width=None, output_height=None,
        art_scale_x=1.0, art_scale_y=1.0, art_offset_x=0, art_offset_y=0,
        hex_clearance_units=0.0, stroke_width_units=2.0,
    )
    metrics = metadata["metrics"]
    assert metrics["verdict"] == "FAIL"
    assert metrics["hex_clear_nonwhite_pixels"] > 0


def test_clean_candidate_leaving_cutouts_white_still_passes(tmp_path):
    """A candidate that paints the panel but leaves both cutout squares clean
    white must still PASS post-fix — the fix must not introduce false
    failures on a properly-painted candidate."""
    svg = tmp_path / "template.svg"
    svg.write_text(CUTOUT_SVG)
    candidate = tmp_path / "clean.png"
    _clean_candidate_image(candidate)

    metadata = E.export_svg_template_fit(
        image_path=candidate, svg_path=svg, out_dir=tmp_path / "out", prefix="clean",
        output_width=None, output_height=None,
        art_scale_x=1.0, art_scale_y=1.0, art_offset_x=0, art_offset_y=0,
        hex_clearance_units=5.0, stroke_width_units=2.0,
    )
    metrics = metadata["metrics"]
    assert metrics["verdict"] == "PASS"
    assert metrics["hex_clear_nonwhite_pixels"] == 0
    assert metrics["outside_nonwhite_pixels"] == 0
