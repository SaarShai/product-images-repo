from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image


MODULE_PATH = Path(__file__).resolve().parents[1] / "batch_triage.py"
SPEC = importlib.util.spec_from_file_location("batch_triage", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
triage = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = triage
SPEC.loader.exec_module(triage)


def config(**changes):
    return triage.TriageConfig(**changes) if changes else triage.TriageConfig()


def disk(xx, yy, x, y, radius):
    return (xx - x) ** 2 + (yy - y) ** 2 <= radius**2


def build_synthetic(width=64, height=64):
    """Same construction family as bg-benchmark/build_negative_fixtures.py."""
    yy, xx = np.ogrid[:height, :width]
    core = disk(xx, yy, 30, 32, 13)
    soft_ring = disk(xx, yy, 30, 32, 16) & ~core
    enclosed_hole = disk(xx, yy, 30, 32, 5)
    appendage = (xx >= 43) & (xx <= 57) & (yy >= 28) & (yy <= 36)

    alpha = np.zeros((height, width), dtype=np.uint8)
    alpha[core] = 255
    alpha[soft_ring] = 128
    alpha[appendage] = 180
    alpha[enclosed_hole] = 0

    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    rgb[:, :] = (70, 115, 180)
    rgb[appendage] = (230, 150, 120)
    paper = np.array([255, 255, 255], dtype=np.uint8)
    alpha32 = alpha.astype(np.uint32)[:, :, None]
    source = (
        (rgb.astype(np.uint32) * alpha32 + paper.astype(np.uint32)[None, None, :] * (255 - alpha32) + 127)
        // 255
    ).astype(np.uint8)

    good_rgba = np.dstack([rgb, alpha]).astype(np.uint8)
    return source, good_rgba, dict(xx=xx, yy=yy, core=core, soft_ring=soft_ring, enclosed_hole=enclosed_hole, appendage=appendage)


def test_paper_field_recovers_uniform_white():
    source = np.full((40, 40, 3), 255, dtype=np.uint8)
    field = triage.fit_paper_field(source.astype(np.float32) / 255.0, config())
    predicted = field.evaluate()
    assert np.allclose(predicted, 1.0, atol=0.02)
    assert field.patch_pixels > 0


def test_paper_field_low_confidence_when_border_fragments():
    # A hard-alternating checkerboard border has no coherent paper patch:
    # every border pixel differs sharply from the seed median, so the
    # border-connected flood fills almost nothing and the fallback fires.
    rng = np.random.default_rng(0)
    source = rng.integers(0, 256, size=(40, 40, 3), dtype=np.uint8)
    field = triage.fit_paper_field(source.astype(np.float32) / 255.0, config())
    assert field.low_confidence is True


def test_matte_rim_flags_white_fringe_not_clean_candidate():
    source, good_rgba, shapes = build_synthetic()
    xx, yy = shapes["xx"], shapes["yy"]
    appendage = shapes["appendage"]

    fringe = disk(xx, yy, 30, 32, 18) & ~disk(xx, yy, 30, 32, 16) & ~appendage
    white_fringe_rgba = good_rgba.copy()
    white_fringe_rgba[fringe, :3] = 255
    white_fringe_rgba[fringe, 3] = 255

    cfg = config()
    clean_report = triage.run_triage_arrays(source, good_rgba, cfg)
    bad_report = triage.run_triage_arrays(source, white_fringe_rgba, cfg)

    assert len(bad_report.matte_rim_suspects) > len(clean_report.matte_rim_suspects)
    assert len(bad_report.matte_rim_suspects) > 0


def test_matte_rim_alpha_sweep_distinguishes_persistent_rim_from_soft_wash():
    source, good_rgba, shapes = build_synthetic()
    xx, yy = shapes["xx"], shapes["yy"]
    appendage = shapes["appendage"]
    fringe = disk(xx, yy, 30, 32, 18) & ~disk(xx, yy, 30, 32, 16) & ~appendage
    white_fringe_rgba = good_rgba.copy()
    white_fringe_rgba[fringe, :3] = 255
    white_fringe_rgba[fringe, 3] = 255  # opaque -> persists even at alpha>224

    cfg = config()
    report = triage.run_triage_arrays(source, white_fringe_rgba, cfg)
    sweep = report.matte_rim_alpha_sweep
    assert sweep["224"] > 0  # persistent matte rim, not just a soft edge


def test_vanished_component_flags_deleted_paint():
    source, good_rgba, shapes = build_synthetic()
    # radius 5 (area ~78px) clears the 64px minimum-area filter; centered at
    # (20, 32), 10px away from the core's own (30, 32) enclosed paper hole so
    # this carves into real paint, not the fixture's legitimate paper gap.
    disk_mask = disk(shapes["xx"], shapes["yy"], 20, 32, 5)
    deleted_rgba = good_rgba.copy()
    deleted_rgba[disk_mask, 3] = 0

    cfg = config()
    clean_report = triage.run_triage_arrays(source, good_rgba, cfg)
    bad_report = triage.run_triage_arrays(source, deleted_rgba, cfg)

    assert len(bad_report.vanished_component_suspects) > len(clean_report.vanished_component_suspects)
    assert any(s.area >= 1 for s in bad_report.vanished_component_suspects)


def test_vanished_component_ignores_pure_paper_gap():
    # A gap in alpha over pixels that are genuinely paper-colored in the
    # source must not be flagged as vanished paint.
    source, good_rgba, shapes = build_synthetic()
    enclosed_hole = shapes["enclosed_hole"]
    report = triage.run_triage_arrays(source, good_rgba, config())
    hole_ys, hole_xs = np.nonzero(enclosed_hole)
    flagged_pixels = set()
    for suspect in report.vanished_component_suspects:
        x0, y0, x1, y1 = suspect.bbox
        for y in range(y0, y1):
            for x in range(x0, x1):
                flagged_pixels.add((x, y))
    for y, x in zip(hole_ys, hole_xs):
        assert (x, y) not in flagged_pixels


def test_hole_census_flags_retained_enclosed_paper():
    source, good_rgba, shapes = build_synthetic()
    enclosed_hole = shapes["enclosed_hole"]
    retained_rgba = good_rgba.copy()
    retained_rgba[enclosed_hole, :3] = 255
    retained_rgba[enclosed_hole, 3] = 255

    cfg = config()
    clean_report = triage.run_triage_arrays(source, good_rgba, cfg)
    bad_report = triage.run_triage_arrays(source, retained_rgba, cfg)

    clean_kinds = [s.kind for s in clean_report.hole_census_suspects]
    bad_kinds = [s.kind for s in bad_report.hole_census_suspects]
    assert "hole_census_retained_paper" in bad_kinds
    assert bad_kinds.count("hole_census_retained_paper") >= clean_kinds.count(
        "hole_census_retained_paper"
    )


def test_hole_census_flags_deleted_enclosed_foreground():
    source, good_rgba, shapes = build_synthetic()
    xx, yy = shapes["xx"], shapes["yy"]
    # (19, 32), radius 2: the core ring between the fixture's own enclosed
    # paper hole (radius 5) and the core boundary (radius 13) is only 8px
    # wide, so this is placed and dilation-checked to stay clear of both.
    interior_hole = disk(xx, yy, 19, 32, 2)
    assert interior_hole.sum() >= 8  # sanity: still a real, non-trivial patch

    deleted_interior_rgba = good_rgba.copy()
    deleted_interior_rgba[interior_hole, 3] = 0

    report = triage.run_triage_arrays(
        source, deleted_interior_rgba, config(hole_census_min_area_px=8)
    )
    kinds = [s.kind for s in report.hole_census_suspects]
    assert "hole_census_deleted_foreground" in kinds


def test_run_triage_arrays_rejects_mismatched_shapes():
    source = np.zeros((10, 10, 3), dtype=np.uint8)
    candidate = np.zeros((12, 12, 4), dtype=np.uint8)
    with pytest.raises(ValueError, match="same size"):
        triage.run_triage_arrays(source, candidate, config())


def test_resample_candidate_to_source_integer_scale():
    small_source_hw = (8, 8)
    big_candidate = np.zeros((16, 16, 4), dtype=np.uint8)
    big_candidate[:, :, 3] = 200
    resized, info = triage.resample_candidate_to_source(big_candidate, small_source_hw)
    assert resized.shape[:2] == small_source_hw
    assert info["resampled"] is True
    assert info["scale"] == 2


def test_resample_candidate_to_source_noninteger_scale_rejected():
    with pytest.raises(ValueError, match="integer multiple"):
        triage.resample_candidate_to_source(np.zeros((15, 15, 4), dtype=np.uint8), (8, 8))


def test_process_files_writes_report_and_review_sheet_and_exits_clean(tmp_path):
    source, good_rgba, _ = build_synthetic()
    source_path = tmp_path / "source.png"
    candidate_path = tmp_path / "candidate.png"
    Image.fromarray(source).save(source_path)
    Image.fromarray(good_rgba).save(candidate_path)

    report_path = tmp_path / "report.json"
    review_path = tmp_path / "review.png"
    exit_code = triage.main(
        [
            "--source",
            str(source_path),
            "--candidate",
            str(candidate_path),
            "--report",
            str(report_path),
            "--review-sheet",
            str(review_path),
        ]
    )
    assert exit_code == 0
    assert report_path.exists()
    assert review_path.exists()


def test_process_files_exit_code_nonzero_on_missing_source(tmp_path):
    exit_code = triage.main(
        [
            "--source",
            str(tmp_path / "missing.png"),
            "--candidate",
            str(tmp_path / "also-missing.png"),
            "--report",
            str(tmp_path / "report.json"),
        ]
    )
    assert exit_code == 2
