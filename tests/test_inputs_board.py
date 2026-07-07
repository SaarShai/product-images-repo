"""Tests for scripts/inputs_board.py against a synthetic round dir."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import inputs_board  # noqa: E402


def _make_round_dir(tmp_path: Path) -> Path:
    round_dir = tmp_path / "roundx"
    handle_dir = round_dir / "handle"
    guides_dir = round_dir / "guides"
    prompts_dir = round_dir / "prompts"
    for d in (handle_dir, guides_dir, prompts_dir):
        d.mkdir(parents=True)

    # reference images, one per role
    Image.new("RGB", (100, 160), (200, 210, 220)).save(handle_dir / "01-medium_ref.png")
    Image.new("RGB", (100, 160), (240, 220, 200)).save(handle_dir / "02-palette_ref.png")
    Image.new("RGB", (100, 160), (180, 200, 180)).save(handle_dir / "03-style_ref.png")

    manifest = {
        "created_at": "2026-01-01T00:00:00Z",
        "rows": [
            {
                "file": "01-medium_ref.png",
                "role": "medium_ref",
                "provenance": "synthetic medium ref for test",
                "notes": "",
            },
            {
                "file": "02-palette_ref.png",
                "role": "palette_ref",
                "provenance": "synthetic palette ref for test",
                "notes": "",
            },
            {
                "file": "03-style_ref.png",
                "role": "style_ref",
                "provenance": "synthetic style ref for test",
                "notes": "",
            },
        ],
    }
    (handle_dir / "style-handle.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")

    # guide
    Image.new("RGB", (100, 160), (128, 128, 128)).save(guides_dir / "arm-x_geometry-only.png")

    # prompt
    (prompts_dir / "arm-x_prompt.md").write_text(
        "Image 1 = layout/geometry reference only.\n\n"
        "Image 2 = watercolor medium only.\n\n"
        "Paint a synthetic test building.\n",
        encoding="utf-8",
    )

    return round_dir


def test_collect_reference_items(tmp_path):
    round_dir = _make_round_dir(tmp_path)
    items = inputs_board.collect_reference_items(round_dir)
    roles = {item["role"] for item in items}
    assert roles == {"medium_ref", "palette_ref", "style_ref"}
    assert len(items) == 3


def test_collect_guide_items(tmp_path):
    round_dir = _make_round_dir(tmp_path)
    items = inputs_board.collect_guide_items(round_dir)
    assert len(items) == 1
    assert items[0]["filename"] == "arm-x_geometry-only.png"


def test_collect_prompt_items(tmp_path):
    round_dir = _make_round_dir(tmp_path)
    items = inputs_board.collect_prompt_items(round_dir)
    assert len(items) == 1
    assert items[0]["filename"] == "arm-x_prompt.md"


def test_build_board_runs_and_all_roles_present(tmp_path):
    round_dir = _make_round_dir(tmp_path)
    out_path = round_dir / f"INPUTS-{round_dir.name}.jpg"

    result_path = inputs_board.build_board(round_dir, out_path)

    assert result_path == out_path
    assert out_path.exists()
    assert out_path.stat().st_size > 0

    # image opens and is a real, non-trivial-size board
    board = Image.open(out_path)
    assert board.width > 0 and board.height > 0

    # every reference/guide/prompt role made it into the board's item list
    all_items = (
        inputs_board.collect_reference_items(round_dir)
        + inputs_board.collect_guide_items(round_dir)
        + inputs_board.collect_prompt_items(round_dir)
    )
    roles_found = {item["role"] for item in all_items}
    assert {"medium_ref", "palette_ref", "style_ref", "guide", "prompt"} <= roles_found


def test_main_cli(tmp_path):
    round_dir = _make_round_dir(tmp_path)
    rc = inputs_board.main([str(round_dir)])
    assert rc == 0
    out_path = round_dir / f"INPUTS-{round_dir.name}.jpg"
    assert out_path.exists()
    assert out_path.stat().st_size > 0
