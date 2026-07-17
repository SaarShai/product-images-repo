"""D5 protected-art preservation contract tests.

All fixtures are generated in code (no binary PNG fixtures committed). Two
kinds of evidence:

1. Synthetic scenes exercising `d5_preservation.py`'s public functions
   directly (policy_exclusion_mask / build_d5_reference / score_no_green_art
   / score_preservation), covering every PASS/REVIEW/FAIL mutation the D5
   blocking-contract spec lists.
2. One nominal fixture pushed through the REAL `chroma_key.py` ->
   `decontam_binarize.py` -> `green_purge.py` CLIs (never mocked, per the
   constraint that those two scripts are out of scope and must be exercised
   for real), plus the tracked round-7 1x/x4 accepted corpus, which an
   accepted artifact must never be used to loosen a negative fixture --
   these are read-only regression checks against files already on disk.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

REPO = Path(__file__).resolve().parents[1]
D5_PATH = REPO / "scripts" / "gates" / "d5_preservation.py"
PY = "/usr/bin/python3"
KEY_RGB = (0, 255, 0)


def load_d5():
    spec = importlib.util.spec_from_file_location("d5_preservation", D5_PATH)
    module = importlib.util.module_from_spec(spec)
    # register before exec: dataclasses + `from __future__ import annotations`
    # need cls.__module__ to resolve via sys.modules during class creation.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


d5 = load_d5()


def disk_mask(h: int, w: int, cx: int, cy: int, r: int) -> np.ndarray:
    yy, xx = np.ogrid[:h, :w]
    return (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r


def make_geometry_scene(h: int = 260, w: int = 300) -> dict:
    """Robust multi-anchor scene: warm coral disk, pale cream disk, a navy
    ink 'bridge' (two blobs joined by a solid connecting strip), and a
    donut-with-hole -- every shape big enough to survive a 2px erosion
    budget untouched. Used for the erosion/PASS and per-shape FAIL
    mutations."""
    coral = disk_mask(h, w, 60, 70, 32)
    cream = disk_mask(h, w, 150, 70, 26)
    navy_a = disk_mask(h, w, 230, 55, 16)
    navy_b = disk_mask(h, w, 280, 55, 16)
    bridge_strip = np.zeros((h, w), dtype=bool)
    bridge_strip[55 - 5 : 55 + 5, 230:280] = True
    navy = navy_a | navy_b | bridge_strip
    ring_outer = disk_mask(h, w, 150, 175, 30)
    ring_inner = disk_mask(h, w, 150, 175, 13)
    ring = ring_outer & ~ring_inner

    alpha = np.zeros((h, w), dtype=np.uint8)
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    src = np.full((h, w, 3), KEY_RGB, dtype=np.uint8)
    for mask, color in (
        (coral, (225, 120, 80)),
        (cream, (238, 228, 208)),
        (navy, (20, 25, 60)),
        (ring, (60, 110, 100)),
    ):
        alpha[mask] = 255
        rgb[mask] = color
        src[mask] = color
    baseline = np.dstack([rgb, alpha])
    return {
        "source_rgb": src,
        "baseline_rgba": baseline,
        "coral": coral,
        "cream": cream,
        "bridge_strip": bridge_strip,
        "ring_inner": ring_inner,
    }


def make_fine_and_green_scene(h: int = 180, w: int = 220) -> dict:
    """One robust anchor + one small ('fine') olive/sage speck (5x5=25px,
    below the anchor-radius threshold) + one interior pure-green
    mistaken-subject-paint blob (NO_GREEN_ART violation)."""
    anchor = disk_mask(h, w, 60, 90, 30)
    fine = np.zeros((h, w), dtype=bool)
    fine[40:45, 150:155] = True
    green = np.zeros((h, w), dtype=bool)
    green[100:130, 150:190] = True  # 30x40, far from any edge band

    alpha = np.zeros((h, w), dtype=np.uint8)
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    src = np.full((h, w, 3), KEY_RGB, dtype=np.uint8)
    for mask, color in (
        (anchor, (225, 120, 80)),
        (fine, (120, 110, 60)),
        (green, (10, 240, 15)),
    ):
        alpha[mask] = 255
        rgb[mask] = color
        src[mask] = color
    baseline = np.dstack([rgb, alpha])
    return {"source_rgb": src, "baseline_rgba": baseline, "fine": fine, "green": green, "anchor": anchor}


def erode_alpha(rgba: np.ndarray, iterations: int) -> np.ndarray:
    fg = rgba[..., 3] > 127
    eroded = ndi.binary_erosion(fg, iterations=iterations, border_value=0)
    out = rgba.copy()
    out[..., 3] = np.where(eroded, 255, 0).astype(np.uint8)
    return out


def delete_region(rgba: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = rgba.copy()
    out[..., 3][mask] = 0
    return out


BASE_CFG_1X = d5.D5Thresholds(analysis_scale=1.0, boundary_budget_px=2.0, palette_policy="no-green-art")


# ---------------------------------------------------------------------------
# policy_exclusion_mask
# ---------------------------------------------------------------------------


def test_policy_exclusion_mask_no_green_art_excludes_key_and_green_hue():
    rgb = np.array(
        [[list(KEY_RGB), [10, 240, 15], [225, 120, 80]]],
        dtype=np.uint8,
    )
    mask = d5.policy_exclusion_mask(rgb, KEY_RGB, "no-green-art")
    assert mask[0, 0] == True  # noqa: E712 -- literal key color
    assert mask[0, 1] == True  # noqa: E712 -- pure green art hue
    assert mask[0, 2] == False  # noqa: E712 -- warm coral is real art


def test_policy_exclusion_mask_preserve_all_only_excludes_literal_key():
    # seaweed-green art color (far enough from the literal key in Lab, ΔE00
    # ~31, that only the no-green-art hue rule -- not the near-key rule --
    # would exclude it).
    rgb = np.array([[[1, 137, 0]]], dtype=np.uint8)
    mask_preserve_all = d5.policy_exclusion_mask(rgb, KEY_RGB, "preserve-all")
    mask_no_green_art = d5.policy_exclusion_mask(rgb, KEY_RGB, "no-green-art")
    assert mask_preserve_all[0, 0] == False  # noqa: E712 -- preserve-all keeps green art protected
    assert mask_no_green_art[0, 0] == True  # noqa: E712 -- no-green-art excludes any green hue


# ---------------------------------------------------------------------------
# build_d5_reference / classification
# ---------------------------------------------------------------------------


def test_build_reference_classifies_anchors_and_excludes_green_and_hole():
    scene = make_fine_and_green_scene()
    ref = d5.build_d5_reference(
        scene["source_rgb"], scene["baseline_rgba"], truth_rgba=None, key_rgb=KEY_RGB, cfg=BASE_CFG_1X
    )
    kinds = sorted(c.kind for c in ref.components)
    assert kinds == ["anchor", "fine"]
    assert not (ref.support & scene["green"]).any(), "pure-green mistaken paint must never enter the protected core"


def test_build_reference_donut_hole_is_not_protected_core():
    scene = make_geometry_scene()
    ref = d5.build_d5_reference(
        scene["source_rgb"], scene["baseline_rgba"], truth_rgba=None, key_rgb=KEY_RGB, cfg=BASE_CFG_1X
    )
    assert not (ref.support & scene["ring_inner"]).any()


# ---------------------------------------------------------------------------
# score_no_green_art (pre-purge palette stop)
# ---------------------------------------------------------------------------


def test_score_no_green_art_fails_on_interior_pure_green_blob():
    scene = make_fine_and_green_scene()
    result = d5.score_no_green_art(scene["baseline_rgba"], cfg=BASE_CFG_1X)
    assert result.verdict == "FAIL"
    assert result.metric["max_component_area_px"] >= 64
    assert result.metric["max_component_radius_px"] >= 3.0


def test_score_no_green_art_passes_clean_baseline():
    scene = make_geometry_scene()
    result = d5.score_no_green_art(scene["baseline_rgba"], cfg=BASE_CFG_1X)
    assert result.verdict == "PASS"


# ---------------------------------------------------------------------------
# score_preservation -- calibration-required mutations
# ---------------------------------------------------------------------------


def test_expected_two_pixel_erosion_only_passes():
    scene = make_geometry_scene()
    ref = d5.build_d5_reference(
        scene["source_rgb"], scene["baseline_rgba"], truth_rgba=None, key_rgb=KEY_RGB, cfg=BASE_CFG_1X
    )
    final = erode_alpha(scene["baseline_rgba"], iterations=2)
    result = d5.score_preservation(final, ref, cfg=BASE_CFG_1X)
    assert result.verdict == "PASS"
    assert result.metric["aggregate_core_recall"] >= 0.9995


def test_removing_8x8_center_from_protected_disk_fails():
    scene = make_geometry_scene()
    ref = d5.build_d5_reference(
        scene["source_rgb"], scene["baseline_rgba"], truth_rgba=None, key_rgb=KEY_RGB, cfg=BASE_CFG_1X
    )
    hole = np.zeros_like(scene["coral"])
    hole[70 - 4 : 70 + 4, 60 - 4 : 60 + 4] = True
    final = delete_region(scene["baseline_rgba"], hole)
    result = d5.score_preservation(final, ref, cfg=BASE_CFG_1X)
    assert result.verdict == "FAIL"
    assert result.metric["deleted_core_max_island_area_px"] >= 16
    assert result.metric["deleted_core_max_island_radius_px"] >= 2.0


def test_deleting_pale_component_fails():
    scene = make_geometry_scene()
    ref = d5.build_d5_reference(
        scene["source_rgb"], scene["baseline_rgba"], truth_rgba=None, key_rgb=KEY_RGB, cfg=BASE_CFG_1X
    )
    cream_full = disk_mask(*scene["baseline_rgba"].shape[:2], 150, 70, 28)
    final = delete_region(scene["baseline_rgba"], cream_full)
    result = d5.score_preservation(final, ref, cfg=BASE_CFG_1X)
    assert result.verdict == "FAIL"
    assert result.metric["any_anchor_component_entirely_lost"] is True


def test_severing_protected_bridge_fails_via_skeleton_or_component_rule():
    scene = make_geometry_scene()
    ref = d5.build_d5_reference(
        scene["source_rgb"], scene["baseline_rgba"], truth_rgba=None, key_rgb=KEY_RGB, cfg=BASE_CFG_1X
    )
    final = delete_region(scene["baseline_rgba"], scene["bridge_strip"])
    result = d5.score_preservation(final, ref, cfg=BASE_CFG_1X)
    assert result.verdict == "FAIL"
    assert result.metric["missing_skeleton_run_px"] >= 3.0


def test_deleting_only_fine_component_is_review_not_fail():
    scene = make_fine_and_green_scene()
    ref = d5.build_d5_reference(
        scene["source_rgb"], scene["baseline_rgba"], truth_rgba=None, key_rgb=KEY_RGB, cfg=BASE_CFG_1X
    )
    final = delete_region(scene["baseline_rgba"], scene["fine"])
    result = d5.score_preservation(final, ref, cfg=BASE_CFG_1X)
    assert result.verdict == "REVIEW"
    assert result.metric["fine_components_lossy"]


def test_purging_pure_green_blob_is_not_penalized_by_d5():
    """D5 excludes green-hue deletion from its recall denominator; a
    separate NO_GREEN_ART palette precheck is the mechanism that blocks it
    (tested above), not D5 preservation recall."""
    scene = make_fine_and_green_scene()
    ref = d5.build_d5_reference(
        scene["source_rgb"], scene["baseline_rgba"], truth_rgba=None, key_rgb=KEY_RGB, cfg=BASE_CFG_1X
    )
    final = delete_region(scene["baseline_rgba"], scene["green"])
    result = d5.score_preservation(final, ref, cfg=BASE_CFG_1X)
    assert result.verdict == "PASS"
    assert result.metric["aggregate_core_recall"] == 1.0


# ---------------------------------------------------------------------------
# Nominal fixture through the REAL chroma_key -> decontam_binarize ->
# green_purge CLIs (never mocked)
# ---------------------------------------------------------------------------


def _make_raw_disc(path: Path, size: int = 240) -> None:
    from PIL import ImageDraw

    scale = 4
    big = Image.new("RGB", (size * scale, size * scale), KEY_RGB)
    draw = ImageDraw.Draw(big)
    cx = cy = size * scale // 2
    r = int(size * scale * 0.29)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(225, 120, 80))
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(25, 20, 15), width=6 * scale)
    big.resize((size, size), Image.LANCZOS).save(path)


def test_nominal_fixture_through_real_pipeline_passes(tmp_path):
    raw_path = tmp_path / "raw.png"
    keyed_path = tmp_path / "keyed.png"
    decontam_path = tmp_path / "decontam.png"
    purged_path = tmp_path / "purged.png"
    _make_raw_disc(raw_path)

    r = subprocess.run(
        [PY, str(REPO / "scripts" / "chroma_key.py"), "key", str(raw_path), str(keyed_path)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr

    r = subprocess.run(
        [
            PY, str(REPO / "scripts" / "decontam_binarize.py"),
            "--rgba", str(keyed_path), "--out", str(decontam_path), "--bg-color", "#00FF00",
        ],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr

    r = subprocess.run(
        [
            PY, str(REPO / "scripts" / "green_purge.py"), str(decontam_path), str(purged_path),
            "--no-green-art", "--erode", "2", "--band", "6",
        ],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr

    source_rgb = np.asarray(Image.open(raw_path).convert("RGB"))
    baseline_rgba = np.asarray(Image.open(decontam_path).convert("RGBA"))
    final_rgba = np.asarray(Image.open(purged_path).convert("RGBA"))

    cfg = d5.D5Thresholds(analysis_scale=1.0, boundary_budget_px=2.0, palette_policy="no-green-art")
    ref = d5.build_d5_reference(source_rgb, baseline_rgba, truth_rgba=None, key_rgb=(0, 255, 0), cfg=cfg)
    result = d5.score_preservation(final_rgba, ref, cfg=cfg)
    assert result.verdict == "PASS", result.metric

    palette = d5.score_no_green_art(baseline_rgba, cfg=cfg)
    assert palette.verdict in {"PASS", "REVIEW"}, palette.metric


# ---------------------------------------------------------------------------
# Round-7 accepted corpus regression -- 1x and x4, r1 and r2. An accepted
# artifact must never be used to loosen a negative fixture; these are
# read-only checks against files already tracked in the repo.
# ---------------------------------------------------------------------------

ROUND7 = REPO / "tasks" / "transparent-bg-endgame" / "round7_outline"

ROUND7_CASES = [
    (
        "r1-1x",
        ROUND7 / "raws" / "H-G2-OUT-GREEN-r1.png",
        ROUND7 / "processed" / "H-G2-OUT-GREEN-r1.png",
        ROUND7 / "processed" / "H-G2-OUT-GREEN-r1-purged.png",
        1.0, 2.0,
    ),
    (
        "r2-1x",
        ROUND7 / "raws" / "H-G2-OUT-GREEN-r2.png",
        ROUND7 / "processed" / "H-G2-OUT-GREEN-r2.png",
        ROUND7 / "processed" / "H-G2-OUT-GREEN-r2-purged.png",
        1.0, 2.0,
    ),
    (
        "r1-x4",
        ROUND7 / "x4" / "H-G2-OUT-GREEN-r1-raw-x4-for-gate.png",
        None,
        ROUND7 / "x4" / "H-G2-OUT-GREEN-r1-x4.png",
        4.0, 8.0,
    ),
    (
        "r2-x4",
        ROUND7 / "x4" / "H-G2-OUT-GREEN-r2-raw-x4-for-gate.png",
        None,
        ROUND7 / "x4" / "H-G2-OUT-GREEN-r2-x4.png",
        4.0, 8.0,
    ),
]


def _round7_case_ids():
    return [c[0] for c in ROUND7_CASES]


import pytest  # noqa: E402


@pytest.mark.parametrize(
    "name,source_path,baseline_path,final_path,scale,budget",
    ROUND7_CASES,
    ids=_round7_case_ids(),
)
def test_round7_accepted_corpus_passes(name, source_path, baseline_path, final_path, scale, budget):
    if not (source_path.exists() and final_path.exists() and (baseline_path is None or baseline_path.exists())):
        pytest.skip(f"round-7 corpus file missing for {name}")
    source_rgb = np.asarray(Image.open(source_path).convert("RGB"))
    baseline_rgba = np.asarray(Image.open(baseline_path).convert("RGBA")) if baseline_path else None
    final_rgba = np.asarray(Image.open(final_path).convert("RGBA"))

    cfg = d5.D5Thresholds(analysis_scale=scale, boundary_budget_px=budget, palette_policy="no-green-art")
    ref = d5.build_d5_reference(source_rgb, baseline_rgba, truth_rgba=None, key_rgb=(0, 255, 0), cfg=cfg)
    result = d5.score_preservation(final_rgba, ref, cfg=cfg)
    assert result.verdict == "PASS", (name, result.metric)
    assert result.metric["aggregate_core_recall"] >= 0.9995, (name, result.metric)
