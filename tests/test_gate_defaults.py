"""L4-gate-defaults-rubric: every candidate gets dual geometry metrics + overlay
by default, and the judge rubric carries the two new axes.

Covers:
  (a) one gates.py run -> {geom_iou region metric, svg white-IoU metric, overlay
      PNG always written, one JSON bundle}; disagreement between the two
      metrics > 0.15 is FLAGGED in the JSON.
  (b) judge_panel.py's rubric text contains the two new axes: COMPLETE-BUILDING
      and GEOMETRY-EMBRACE.
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
GATES = REPO / "scripts" / "gates.py"
JUDGE_PANEL = REPO / "scripts" / "judge_panel.py"


# ---------------------------------------------------------------------------
# shared fixture: a panel's mask/control/forbidden/holes/spec + a matching SVG
# with one outer_contour + one internal_cutout, positioned so an SVG viewBox
# (200x300) maps 1:1 (x2) onto a 400x600 candidate.
# ---------------------------------------------------------------------------
SVG_TEXT = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 300">
<polygon points="0,0 200,0 200,300 0,300" style="fill:none;stroke:#000;stroke-width:2"/>
<polygon points="70,120 130,120 130,180 70,180" style="fill:none;stroke:#000;stroke-width:2"/>
</svg>
"""


def _write_geometry(tmp_path):
    geom = tmp_path / "geom"
    geom.mkdir()
    panel = "toy"
    w, h = 400, 600

    # hole rect matches the SVG's internal_cutout (70,120)-(130,180) scaled x2
    hole_box = [140, 240, 260, 360]

    holes = Image.new("L", (w, h), 0)
    ImageDraw.Draw(holes).rectangle(hole_box, fill=255)

    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    d.rectangle([0, 0, w - 1, h - 1], fill=255)
    d.rectangle(hole_box, fill=0)

    control = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(control)
    d.rectangle([0, 0, w - 1, h - 1], outline=255, width=2)
    d.rectangle(hole_box, outline=255, width=2)

    forbidden = Image.new("L", (w, h), 0)

    mask.save(geom / f"{panel}-mask.png")
    control.convert("RGB").save(geom / f"{panel}-control.png")
    forbidden.save(geom / f"{panel}-forbidden.png")
    holes.save(geom / f"{panel}-holes.png")
    (geom / f"{panel}-spec.json").write_text(
        json.dumps(
            {
                "panel": panel,
                "source": "test",
                "size_px": [w, h],
                "aspect": round(w / h, 4),
                "body_frac": 0.9,
                "holes_n": 1,
                "forbidden_bands_frac": [],
            },
            indent=2,
        )
        + "\n"
    )
    svg = geom / f"{panel}.svg"
    svg.write_text(SVG_TEXT)
    return geom, panel, hole_box


def _candidate_clean_hole(path, w=400, h=600, hole_box=(140, 240, 260, 360)):
    """Fully painted panel with the cutout left WHITE (paper) -> both metrics agree, high."""
    img = Image.new("RGB", (w, h), (120, 80, 40))
    ImageDraw.Draw(img).rectangle(hole_box, fill=(255, 255, 255))
    img.save(path)
    return path


def _candidate_disagreeing_hole(path, w=400, h=600, hole_box=(140, 240, 260, 360)):
    """The cutout is drawn as a painted rim/frame around a CLEAN but non-white void
    (a legitimate geometry-embrace treatment): region-IoU (fill-agnostic, bounded by
    the drawn rim edge) scores high, white-IoU (strict-white) scores near zero ->
    a real disagreement between the two metrics."""
    img = Image.new("RGB", (w, h), (120, 80, 40))
    d = ImageDraw.Draw(img)
    d.rectangle(hole_box, fill=(225, 210, 190), outline=(10, 10, 10), width=4)
    img.save(path)
    return path


def _run_gates(cand, geom, panel, outdir, stage="finish", extra=()):
    return subprocess.run(
        [
            sys.executable,
            str(GATES),
            "--cand",
            str(cand),
            "--geom",
            str(geom),
            "--panel",
            panel,
            "--outdir",
            str(outdir),
            "--stage",
            stage,
            *extra,
        ],
        capture_output=True,
        text=True,
    )


def test_dual_geometry_metrics_and_overlay_written_by_default(tmp_path):
    geom, panel, hole_box = _write_geometry(tmp_path)
    cand = _candidate_clean_hole(tmp_path / "clean.png", hole_box=tuple(hole_box))
    outdir = tmp_path / "out"

    result = _run_gates(cand, geom, panel, outdir)

    assert result.returncode == 0, result.stdout + result.stderr
    bundle = json.loads(result.stdout)

    dual = bundle["dual_geometry"]
    assert dual["available"] is True
    assert dual["region_iou"]["value"] is not None
    assert dual["white_iou"]["value"] is not None
    assert dual["region_iou"]["value"] > 0.9
    assert dual["white_iou"]["value"] > 0.9
    assert dual["flagged"] is False

    # overlay PNG always written
    assert Path(bundle["overlay_path"]).exists()
    # one JSON bundle on disk, matching stdout
    assert (outdir / f"{panel}-finish-bundle.json").exists()


def test_dual_geometry_disagreement_is_flagged(tmp_path):
    geom, panel, hole_box = _write_geometry(tmp_path)
    cand = _candidate_disagreeing_hole(tmp_path / "disagree.png", hole_box=tuple(hole_box))
    outdir = tmp_path / "out"

    result = _run_gates(cand, geom, panel, outdir)

    bundle = json.loads(result.stdout)
    dual = bundle["dual_geometry"]

    region_iou = dual["region_iou"]["value"]
    white_iou = dual["white_iou"]["value"]
    assert region_iou is not None and white_iou is not None
    assert abs(region_iou - white_iou) > 0.15

    assert dual["flagged"] is True
    assert dual["disagreement"] == round(abs(region_iou - white_iou), 4)
    assert "disagree" in dual["flag_reason"].lower()

    # a flagged disagreement WARN-downgrades an otherwise-clean bundle rather than
    # silently passing through unnoticed.
    assert bundle["overall_verdict"] in ("WARN", "FAIL")


def test_dual_geometry_skipped_gracefully_without_svg(tmp_path):
    geom, panel, hole_box = _write_geometry(tmp_path)
    (geom / f"{panel}.svg").unlink()
    cand = _candidate_clean_hole(tmp_path / "clean.png", hole_box=tuple(hole_box))
    outdir = tmp_path / "out"

    result = _run_gates(cand, geom, panel, outdir)

    assert result.returncode == 0, result.stdout + result.stderr
    bundle = json.loads(result.stdout)
    assert bundle["dual_geometry"]["available"] is False
    # overlay is still always written even without an SVG
    assert Path(bundle["overlay_path"]).exists()


def test_dual_geometry_defaults_to_panel_svg_fallback(tmp_path):
    geom, panel, hole_box = _write_geometry(tmp_path)
    (geom / f"{panel}.svg").rename(geom / f"{panel}-panel.svg")
    cand = _candidate_clean_hole(tmp_path / "clean.png", hole_box=tuple(hole_box))
    outdir = tmp_path / "out"

    result = _run_gates(cand, geom, panel, outdir)

    assert result.returncode == 0, result.stdout + result.stderr
    bundle = json.loads(result.stdout)
    dual = bundle["dual_geometry"]
    assert dual["available"] is True
    assert dual["svg"].endswith(f"{panel}-panel.svg")
    assert dual["region_iou"]["value"] is not None
    assert dual["white_iou"]["value"] is not None


def test_judge_panel_rubric_has_complete_building_axis():
    text = JUDGE_PANEL.read_text()
    assert "COMPLETE-BUILDING" in text


def test_judge_panel_rubric_has_geometry_embrace_axis():
    text = JUDGE_PANEL.read_text()
    assert "GEOMETRY-EMBRACE" in text
