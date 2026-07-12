from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from PIL import Image


MODULE_PATH = Path(__file__).resolve().parents[1] / "assisted_bg_remove.py"
SPEC = importlib.util.spec_from_file_location("assisted_bg_remove", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
bg = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = bg
SPEC.loader.exec_module(bg)


def config(**changes):
    base = bg.PipelineConfig(
        proposal_fg_threshold=0.8,
        proposal_bg_threshold=0.2,
        inner_distance_px=0,
        outer_distance_px=0,
        correction_unlock_radius_px=0,
        residual_alpha_floor=0.2,
        residual_max_adjustment=0.5,
    )
    return replace(base, **changes)


def source(shape=(9, 9), value=255):
    return np.full((*shape, 3), value, dtype=np.uint8)


def overlay(shape=(9, 9)):
    return np.zeros((*shape, 4), dtype=np.uint8)


def red(markup, y, x):
    markup[y, x] = (255, 0, 0, 255)


def blue(markup, y, x):
    markup[y, x] = (0, 0, 255, 255)


def passthrough_foreground(image, _alpha):
    return image.copy()


def run(proposal, corrections, solver, cfg=None, image=None, estimator=passthrough_foreground):
    return bg.run_pipeline_arrays(
        image if image is not None else source(proposal.shape),
        proposal,
        corrections,
        backend="closed_form",
        config=cfg or config(),
        solver=solver,
        foreground_estimator=estimator,
    )


def mixed_proposal(shape=(9, 9)):
    proposal = np.full(shape, 128, dtype=np.uint8)
    proposal[0, 0] = 0
    proposal[-1, -1] = 255
    return proposal


def test_pure_white_user_foreground_survives_auto_background_and_solver():
    proposal = np.zeros((9, 9), dtype=np.uint8)
    proposal[0, 0] = 255
    corrections = overlay()
    red(corrections, 4, 4)
    result = run(proposal, corrections, lambda _image, trimap: np.zeros_like(trimap))
    assert result.trimap[4, 4] == 1.0
    assert result.alpha[4, 4] == 1.0


def test_user_background_beats_auto_foreground_and_solver():
    proposal = np.full((9, 9), 255, dtype=np.uint8)
    proposal[0, 0] = 0
    corrections = overlay()
    blue(corrections, 4, 4)
    result = run(proposal, corrections, lambda _image, trimap: np.ones_like(trimap))
    assert result.trimap[4, 4] == 0.0
    assert result.alpha[4, 4] == 0.0


def test_transparent_unknown_overlay_does_nothing():
    proposal = mixed_proposal()
    no_overlay = run(proposal, None, lambda _image, trimap: trimap)
    transparent = overlay()
    transparent[:, :, :3] = (255, 0, 0)  # hidden RGB must remain irrelevant
    with_overlay = run(proposal, transparent, lambda _image, trimap: trimap)
    np.testing.assert_array_equal(with_overlay.trimap, no_overlay.trimap)
    np.testing.assert_array_equal(with_overlay.alpha, no_overlay.alpha)


def test_flattened_overlay_rejected():
    flattened = np.full((9, 9, 4), (255, 0, 0, 255), dtype=np.uint8)
    with pytest.raises(ValueError, match="flattened"):
        bg.decode_correction_overlay(flattened, (9, 9), config())


def test_correction_size_mismatch_rejected():
    with pytest.raises(ValueError, match="exactly match"):
        bg.decode_correction_overlay(overlay((8, 9)), (9, 9), config())


def test_ambiguous_fg_bg_overlap_rejected():
    corrections = overlay()
    corrections[4, 4] = (255, 0, 255, 255)
    with pytest.raises(ValueError, match="both red FG and blue BG"):
        bg.decode_correction_overlay(corrections, (9, 9), config())


def test_weak_correction_color_rejected():
    corrections = overlay()
    corrections[4, 4] = (160, 50, 10, 255)
    with pytest.raises(ValueError, match="weak/ambiguous"):
        bg.decode_correction_overlay(corrections, (9, 9), config())


def test_direct_overlapping_masks_rejected():
    foreground = np.zeros((3, 3), dtype=bool)
    background = np.zeros((3, 3), dtype=bool)
    foreground[1, 1] = background[1, 1] = True
    with pytest.raises(ValueError, match="overlap"):
        bg.validate_correction_masks(foreground, background)


def test_unlock_neighborhood_becomes_unknown_but_exact_label_clamps_after_solver():
    proposal = np.full((9, 9), 255, dtype=np.uint8)
    proposal[0, 0] = 0
    corrections = overlay()
    blue(corrections, 4, 4)
    result = run(
        proposal,
        corrections,
        lambda _image, trimap: np.full_like(trimap, 0.7),
        cfg=config(correction_unlock_radius_px=1),
    )
    assert result.trimap[4, 4] == 0.0
    assert result.trimap[4, 3] == 0.5
    assert result.trimap[3, 4] == 0.5
    assert result.alpha[4, 4] == 0.0
    assert result.alpha[4, 3] == pytest.approx(0.7)


def test_one_pixel_labels_survive_every_stage():
    proposal = mixed_proposal()
    corrections = overlay()
    red(corrections, 3, 3)
    blue(corrections, 5, 5)
    result = run(
        proposal,
        corrections,
        lambda _image, trimap: np.full_like(trimap, 0.33),
        cfg=config(correction_unlock_radius_px=2),
    )
    assert np.count_nonzero(result.correction_fg) == 1
    assert np.count_nonzero(result.correction_bg) == 1
    assert result.trimap[3, 3] == result.alpha[3, 3] == 1.0
    assert result.trimap[5, 5] == result.alpha[5, 5] == 0.0


def test_soft_alpha_stays_soft_by_default():
    proposal = mixed_proposal()
    result = run(proposal, None, lambda _image, trimap: np.full_like(trimap, 0.37))
    assert result.alpha[4, 4] == pytest.approx(0.37)
    assert result.metrics["alpha_mode"] == "soft-straight-default"


def test_binary_alpha_is_only_enabled_explicitly():
    proposal = mixed_proposal()
    soft = run(proposal, None, lambda _image, trimap: np.full_like(trimap, 0.37))
    binary = run(
        proposal,
        None,
        lambda _image, trimap: np.full_like(trimap, 0.37),
        cfg=config(binary=True, binary_threshold=0.5),
    )
    assert soft.alpha[4, 4] == pytest.approx(0.37)
    assert binary.alpha[4, 4] == 0.0
    assert set(np.unique(binary.alpha)).issubset({0.0, 1.0})


def test_low_alpha_foreground_recovery_remains_finite_and_bounded():
    image = np.full((3, 3, 3), 0.8, dtype=np.float32)
    alpha = np.array(
        [[0.0, 1e-12, 0.1], [0.19, 0.2, 0.8], [1.0, 0.0, 0.5]],
        dtype=np.float32,
    )
    trimap = np.full((3, 3), 0.5, dtype=np.float32)
    trimap[0, 0] = 0.0
    trimap[2, 0] = 1.0

    def unstable_estimator(_image, _alpha):
        result = np.full((3, 3, 3), 0.4, dtype=np.float32)
        result[0, 0] = (np.nan, np.inf, -np.inf)
        return result

    foreground, _, _ = bg.recover_foreground_rgb(
        image, alpha, trimap, config(), foreground_estimator=unstable_estimator
    )
    assert np.all(np.isfinite(foreground))
    assert float(foreground.min()) >= 0.0
    assert float(foreground.max()) <= 1.0


def test_high_alpha_residual_correction_improves_recomposition():
    alpha = np.full((2, 2), 0.8, dtype=np.float32)
    true_foreground = np.full((2, 2, 3), (0.2, 0.4, 0.6), dtype=np.float32)
    paper = np.ones(3, dtype=np.float32)
    image = alpha[:, :, None] * true_foreground + (1.0 - alpha[:, :, None]) * paper
    poor_foreground = np.full_like(true_foreground, 0.5)
    corrected, metrics = bg.apply_residual_correction(
        image,
        poor_foreground,
        alpha,
        paper,
        alpha_floor=0.2,
        max_adjustment=1.0,
    )
    before = metrics["eligible_recomposition_mae_before"]
    after = metrics["eligible_recomposition_mae_after"]
    assert after < before
    np.testing.assert_allclose(corrected, true_foreground, atol=1e-6)


def test_joint_edge_decontamination_removes_paper_rgb_without_deleting_edge():
    paper = np.ones(3, dtype=np.float32)
    true_color = np.array((0.15, 0.3, 0.8), dtype=np.float32)
    alpha = np.zeros((11, 11), dtype=np.float32)
    alpha[1:10, 1:10] = 0.65
    alpha[3:8, 3:8] = 1.0
    foreground = np.zeros((11, 11, 3), dtype=np.float32)
    foreground[1:10, 1:10] = 0.98  # paper-contaminated straight RGB
    foreground[3:8, 3:8] = true_color
    source_image = np.ones_like(foreground)
    source_image[1:10, 1:10] = 0.2 * true_color + 0.8 * paper
    source_image[3:8, 3:8] = true_color
    protected = np.zeros((11, 11), dtype=bool)
    protected[3:8, 3:8] = True

    cleaned_rgb, cleaned_alpha, metrics = bg.decontaminate_boundary_rgb(
        source_image,
        foreground,
        alpha,
        paper,
        protected_mask=protected,
    )

    changed = np.any(cleaned_rgb != foreground, axis=2)
    assert metrics["changed_pixels"] == int(changed.sum()) > 0
    assert np.all(cleaned_alpha[changed] >= bg.DECONTAM_MINIMUM_NEW_ALPHA)
    np.testing.assert_allclose(
        cleaned_rgb[changed], np.broadcast_to(true_color, cleaned_rgb[changed].shape)
    )
    recomposed = bg.composite(cleaned_rgb, cleaned_alpha, paper)
    assert float(np.max(np.abs(recomposed[changed] - source_image[changed]) * 255.0)) <= 8.0
    before_black = bg.composite(foreground, alpha, (0.0, 0.0, 0.0))
    after_black = bg.composite(cleaned_rgb, cleaned_alpha, (0.0, 0.0, 0.0))
    assert float(after_black[changed].mean()) < float(before_black[changed].mean())


def test_edge_decontamination_skips_pale_nearest_donor_for_valid_farther_donor():
    paper = np.ones(3, dtype=np.float32)
    true_color = np.array((0.1, 0.3, 0.8), dtype=np.float32)
    alpha = np.zeros((15, 15), dtype=np.float32)
    alpha[4:9, 1:14] = 1.0
    alpha[6, 1] = 0.5
    foreground = np.ones((15, 15, 3), dtype=np.float32) * 0.99
    foreground[4:9, 7:14] = true_color
    source_image = alpha[:, :, None] * foreground + (1.0 - alpha[:, :, None]) * paper
    source_image[6, 1] = 0.2 * true_color + 0.8 * paper

    cleaned_rgb, cleaned_alpha, metrics = bg.decontaminate_boundary_rgb(
        source_image,
        foreground,
        alpha,
        paper,
        boundary_width_px=1,
        target_radius_px=12,
    )

    assert metrics["changed_pixels"] == 1
    np.testing.assert_allclose(cleaned_rgb[6, 1], true_color)
    assert cleaned_alpha[6, 1] == pytest.approx(0.2)


def test_edge_decontamination_never_changes_protected_sure_labels():
    paper = np.ones(3, dtype=np.float32)
    true_color = np.array((0.1, 0.4, 0.8), dtype=np.float32)
    foreground = np.ones((11, 11, 3), dtype=np.float32) * 0.99
    foreground[3:8, 3:8] = true_color
    alpha = np.zeros((11, 11), dtype=np.float32)
    alpha[1:10, 1:10] = 0.7
    alpha[3:8, 3:8] = 1.0
    source_image = alpha[:, :, None] * foreground + (1.0 - alpha[:, :, None]) * paper
    source_image[1, 4:6] = 0.2 * true_color + 0.8 * paper
    protected = np.zeros((11, 11), dtype=bool)
    protected[1, 4] = True

    cleaned_rgb, cleaned_alpha, _ = bg.decontaminate_boundary_rgb(
        source_image, foreground, alpha, paper, protected_mask=protected
    )

    np.testing.assert_array_equal(cleaned_rgb[1, 4], foreground[1, 4])
    assert cleaned_alpha[1, 4] == alpha[1, 4]
    np.testing.assert_allclose(cleaned_rgb[1, 5], true_color)
    assert cleaned_alpha[1, 5] == pytest.approx(0.2)


def test_edge_decontamination_does_not_borrow_color_across_components():
    paper = np.ones(3, dtype=np.float32)
    foreground = np.ones((13, 13, 3), dtype=np.float32) * 0.99
    alpha = np.zeros((13, 13), dtype=np.float32)
    alpha[2:5, 2:5] = 0.5  # pale component has no high-alpha interior
    alpha[7:12, 7:12] = 1.0
    donor_color = np.array((0.1, 0.3, 0.8), dtype=np.float32)
    foreground[7:12, 7:12] = donor_color
    source_image = alpha[:, :, None] * foreground + (1.0 - alpha[:, :, None]) * paper
    source_image[2:5, 2:5] = 0.2 * donor_color + 0.8 * paper

    cleaned_rgb, cleaned_alpha, metrics = bg.decontaminate_boundary_rgb(
        source_image, foreground, alpha, paper
    )

    np.testing.assert_array_equal(cleaned_rgb[2:5, 2:5], foreground[2:5, 2:5])
    np.testing.assert_array_equal(cleaned_alpha[2:5, 2:5], alpha[2:5, 2:5])
    assert metrics["changed_pixels"] == 0


def test_edge_decontamination_is_finite_and_bounds_changed_recomposition():
    paper = np.ones(3, dtype=np.float32)
    true_color = np.array((0.1, 0.3, 0.8), dtype=np.float32)
    alpha = np.zeros((15, 15), dtype=np.float32)
    alpha[4:9, 1:14] = 1.0
    alpha[6, 1] = 0.5
    alpha[0, 0] = np.nan
    foreground = np.ones((15, 15, 3), dtype=np.float32) * 0.99
    foreground[4:9, 7:14] = true_color
    foreground[0, 0] = (np.nan, np.inf, -np.inf)
    source_image = np.ones_like(foreground)
    finite_alpha = np.nan_to_num(alpha, nan=0.0)
    source_image = (
        finite_alpha[:, :, None]
        * np.nan_to_num(foreground, nan=0.0, posinf=1.0, neginf=0.0)
        + (1.0 - finite_alpha[:, :, None]) * paper
    )
    source_image[6, 1] = 0.2 * true_color + 0.8 * paper

    cleaned_rgb, cleaned_alpha, metrics = bg.decontaminate_boundary_rgb(
        source_image,
        foreground,
        alpha,
        paper,
        boundary_width_px=1,
        target_radius_px=12,
    )

    assert np.all(np.isfinite(cleaned_rgb))
    assert np.all(np.isfinite(cleaned_alpha))
    sanitized_foreground = np.nan_to_num(
        foreground, nan=0.0, posinf=1.0, neginf=0.0
    )
    changed = np.any(cleaned_rgb != sanitized_foreground, axis=2)
    recomposed = bg.composite(cleaned_rgb, cleaned_alpha, paper)
    assert float(np.max(np.abs(recomposed[changed] - source_image[changed]) * 255.0)) <= 8.0
    assert metrics["changed_recomposition_error_max_8bit"] <= 8.0


def test_binary_pipeline_skips_joint_soft_edge_decontamination():
    proposal = mixed_proposal()
    result = run(
        proposal,
        None,
        lambda _image, trimap: np.full_like(trimap, 0.7),
        cfg=config(binary=True),
    )
    metrics = result.metrics["foreground_rgb"]["edge_decontamination"]
    assert metrics["enabled"] is False
    assert metrics["skipped_reason"] == "binary alpha requested"
    assert set(np.unique(result.alpha)).issubset({0.0, 1.0})


def test_proposal_cannot_override_correction_labels():
    proposal = np.zeros((9, 9), dtype=np.uint8)
    proposal[0, 0] = 255
    corrections = overlay()
    red(corrections, 4, 4)
    result = run(
        proposal,
        corrections,
        lambda _image, trimap: 1.0 - trimap,
        cfg=config(correction_unlock_radius_px=2),
    )
    assert result.alpha[4, 4] == 1.0


def test_run_pipeline_does_not_mutate_source_proposal_or_overlay():
    image = source(value=123)
    proposal = mixed_proposal()
    corrections = overlay()
    red(corrections, 3, 3)
    originals = (image.copy(), proposal.copy(), corrections.copy())
    run(
        proposal,
        corrections,
        lambda _image, trimap: trimap,
        image=image,
    )
    np.testing.assert_array_equal(image, originals[0])
    np.testing.assert_array_equal(proposal, originals[1])
    np.testing.assert_array_equal(corrections, originals[2])


def test_candidate_core_rejects_final_path(tmp_path):
    with pytest.raises(ValueError, match="final-path"):
        bg.reject_final_path(tmp_path / "Images" / "finals" / "candidate.png")


def test_vitmatte_failure_does_not_fallback_without_explicit_permission(monkeypatch):
    image = np.ones((5, 5, 3), dtype=np.float32)
    trimap = np.full((5, 5), 0.5, dtype=np.float32)
    trimap[0, 0] = 0.0
    trimap[-1, -1] = 1.0
    calls = []

    def fail_vitmatte(_image, _trimap, _config):
        calls.append("vitmatte")
        raise RuntimeError("deliberate backend failure")

    def closed_form(_image, _trimap, _config):
        calls.append("closed_form")
        return np.full((5, 5), 0.4, dtype=np.float32), {"backend_used": "closed_form"}

    monkeypatch.setattr(bg, "_solve_vitmatte", fail_vitmatte)
    monkeypatch.setattr(bg, "_solve_closed_form", closed_form)
    with pytest.raises(RuntimeError, match="deliberate"):
        bg.solve_alpha(image, trimap, "vitmatte", config(), allow_fallback=False)
    assert calls == ["vitmatte"]

    alpha, info = bg.solve_alpha(image, trimap, "vitmatte", config(), allow_fallback=True)
    assert calls == ["vitmatte", "vitmatte", "closed_form"]
    assert np.all(alpha == pytest.approx(0.4))
    assert info["backend_requested"] == "vitmatte"
    assert info["backend_used"] == "closed_form"
    assert info["fallback_allowed"] is True


def test_process_files_writes_explicit_candidate_manifest_metrics_and_board(tmp_path):
    source_path = tmp_path / "source.png"
    proposal_path = tmp_path / "proposal.png"
    output_path = tmp_path / "candidates" / "candidate.png"
    metrics_path = tmp_path / "candidates" / "metrics.json"
    manifest_path = tmp_path / "candidates" / "manifest.json"
    review_path = tmp_path / "candidates" / "review.png"

    image = np.full((24, 24, 3), 255, dtype=np.uint8)
    image[6:18, 6:18] = (30, 90, 170)
    proposal = np.zeros((24, 24), dtype=np.uint8)
    proposal[5:19, 5:19] = 128
    proposal[8:16, 8:16] = 255
    Image.fromarray(image).save(source_path)
    Image.fromarray(proposal).save(proposal_path)

    manifest = bg.process_files(
        source_path=source_path,
        proposal_path=proposal_path,
        correction_path=None,
        output_path=output_path,
        metrics_path=metrics_path,
        manifest_path=manifest_path,
        review_board_path=review_path,
        backend="closed_form",
        config=config(closed_form_maxiter=100),
        review_max_side=24,
    )

    assert manifest["status"] == "candidate-unapproved"
    assert manifest["production_ready"] is False
    assert manifest["inputs"]["source"]["size_wh"] == [24, 24]
    assert len(manifest["inputs"]["source"]["sha256"]) == 64
    assert output_path.exists() and metrics_path.exists() and manifest_path.exists() and review_path.exists()
    with Image.open(output_path) as output:
        assert output.mode == "RGBA"
        assert output.size == (24, 24)
    metrics = __import__("json").loads(metrics_path.read_text())
    assert metrics["pipeline"]["native_resolution_preserved"] is True
    assert metrics["pipeline"]["alpha_mode"] == "soft-straight-default"
    assert metrics["outputs"]["review_board"]["backgrounds"] == [
        "white",
        "gray",
        "black",
        "magenta",
    ]


def test_cli_decontam_paper_distance_defaults_and_plumbs_into_config(monkeypatch, tmp_path):
    captured = {}

    def fake_process_files(**kwargs):
        captured["config"] = kwargs["config"]
        return {"stub": True}

    monkeypatch.setattr(bg, "process_files", fake_process_files)

    base_argv = [
        "--source",
        str(tmp_path / "source.png"),
        "--proposal",
        str(tmp_path / "proposal.png"),
        "--output",
        str(tmp_path / "candidate.png"),
        "--metrics",
        str(tmp_path / "metrics.json"),
        "--manifest",
        str(tmp_path / "manifest.json"),
        "--review-board",
        str(tmp_path / "review.png"),
        "--backend",
        "closed_form",
    ]

    assert bg.main(base_argv) == 0
    assert captured["config"].decontam_paper_distance_8bit == bg.DECONTAM_PAPER_DISTANCE_8BIT

    assert bg.main(base_argv + ["--decontam-paper-distance", "45"]) == 0
    assert captured["config"].decontam_paper_distance_8bit == 45.0


def test_review_board_contains_four_labeled_background_tiles():
    foreground = np.zeros((4, 2, 3), dtype=np.float32)
    alpha = np.full((4, 2), 0.5, dtype=np.float32)
    board = bg.make_review_board(foreground, alpha, max_tile_side=4)
    assert board.mode == "RGB"
    assert board.size == (4, 64)


REAL_BACKEND = os.environ.get("ASSISTED_BG_REAL_BACKEND")


@pytest.mark.skipif(
    REAL_BACKEND not in {"closed_form", "vitmatte"},
    reason="set ASSISTED_BG_REAL_BACKEND=closed_form or vitmatte to run",
)
def test_optional_real_backend_smoke():
    image = np.ones((32, 32, 3), dtype=np.float32)
    image[8:24, 8:24] = (0.1, 0.3, 0.7)
    trimap = np.full((32, 32), 0.5, dtype=np.float32)
    trimap[:4, :] = trimap[-4:, :] = trimap[:, :4] = trimap[:, -4:] = 0.0
    trimap[12:20, 12:20] = 1.0
    alpha, info = bg.solve_alpha(
        image,
        trimap,
        backend=REAL_BACKEND,
        config=config(closed_form_maxiter=100),
        allow_fallback=False,
    )
    assert alpha.shape == trimap.shape
    assert np.all(np.isfinite(alpha))
    assert info["backend_used"] == REAL_BACKEND
