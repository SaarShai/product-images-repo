"""tests/test_review_pack.py — minimal coverage for scripts/review_pack.py:
build_review_pack() on a small synthetic RGBA produces fullres + 3 composites
+ manifest listing exactly the files on disk, and junction crops are
deterministic across two runs (same file list). Fast: no realesrgan/upscale
involved.
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
from PIL import Image


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "review_pack.py"


def load_module():
    spec = importlib.util.spec_from_file_location("review_pack", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic_rgba(size=64) -> np.ndarray:
    """A small RGBA with an irregular (non-convex) opaque shape so the
    junction/curvature crop-picker has real boundary features to find."""
    rgba = np.zeros((size, size, 4), dtype=np.uint8)
    yy, xx = np.mgrid[0:size, 0:size]
    c = size // 2
    # star-ish blob: union of a disc and an offset disc carves a concave notch
    disc1 = (xx - c) ** 2 + (yy - c) ** 2 <= (size * 0.32) ** 2
    disc2 = (xx - (c + 10)) ** 2 + (yy - (c - 8)) ** 2 <= (size * 0.18) ** 2
    fg = disc1 | disc2
    rgba[..., 0][fg] = 200
    rgba[..., 1][fg] = 60
    rgba[..., 2][fg] = 90
    rgba[..., 3][fg] = 255
    return rgba


def write_png(path: Path, rgba: np.ndarray) -> None:
    Image.fromarray(rgba, "RGBA").save(path)


def test_build_review_pack_produces_fullres_and_three_composites(tmp_path: Path):
    mod = load_module()
    final_path = tmp_path / "final.png"
    write_png(final_path, synthetic_rgba())

    out_dir = tmp_path / "pack"
    manifest = mod.build_review_pack(
        final_path=final_path, raw_path=None, out_dir=out_dir,
    )

    fullres = out_dir / "fullres" / "final.png"
    assert fullres.exists()

    composites_dir = out_dir / "composites"
    composite_files = sorted(p.name for p in composites_dir.glob("*.png"))
    assert composite_files == [
        "composite_dark.png", "composite_magenta.png", "composite_white.png",
    ]

    manifest_path = out_dir / "manifest.json"
    assert manifest_path.exists()
    on_disk_manifest = json.loads(manifest_path.read_text())
    assert on_disk_manifest == manifest


def test_manifest_lists_exactly_the_files_on_disk(tmp_path: Path):
    mod = load_module()
    final_path = tmp_path / "final.png"
    write_png(final_path, synthetic_rgba())

    out_dir = tmp_path / "pack"
    manifest = mod.build_review_pack(
        final_path=final_path, raw_path=None, out_dir=out_dir,
    )

    manifest_paths = {Path(entry["path"]) for entry in manifest["files"]}
    on_disk = {
        p for p in out_dir.rglob("*")
        if p.is_file() and p.name != "manifest.json"
    }
    assert manifest_paths == on_disk


def test_junction_crops_deterministic_across_two_runs(tmp_path: Path):
    mod = load_module()
    final_path = tmp_path / "final.png"
    write_png(final_path, synthetic_rgba())

    out_dir_a = tmp_path / "pack_a"
    out_dir_b = tmp_path / "pack_b"
    manifest_a = mod.build_review_pack(final_path=final_path, raw_path=None, out_dir=out_dir_a)
    manifest_b = mod.build_review_pack(final_path=final_path, raw_path=None, out_dir=out_dir_b)

    assert manifest_a["n_junction_points"] > 0

    def crop_names(manifest, out_dir):
        return sorted(
            Path(entry["path"]).relative_to(out_dir).as_posix()
            for entry in manifest["files"]
            if entry["kind"].startswith("junction_crop")
        )

    names_a = crop_names(manifest_a, out_dir_a)
    names_b = crop_names(manifest_b, out_dir_b)
    assert names_a == names_b
    assert len(names_a) > 0

    # pixel-identical, not just same file names
    for name in names_a:
        px_a = np.asarray(Image.open(out_dir_a / name))
        px_b = np.asarray(Image.open(out_dir_b / name))
        assert np.array_equal(px_a, px_b)
