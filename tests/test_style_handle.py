import subprocess
import sys
from pathlib import Path

import yaml
from PIL import Image

from scripts.build_style_handle import ManifestError, load_manifest_rows, validate_manifest


REPO = Path(__file__).resolve().parents[1]
BUILD_STYLE_HANDLE = REPO / "scripts" / "build_style_handle.py"


def _make_image(path: Path, color=(120, 140, 200)) -> Path:
    Image.new("RGB", (40, 30), color).save(path)
    return path


def _write_manifest(tmp_path: Path, rows: list[dict]) -> Path:
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(yaml.safe_dump(rows, sort_keys=False), encoding="utf-8")
    return manifest_path


def test_happy_path_validates(tmp_path):
    medium = _make_image(tmp_path / "medium.png")
    palette = _make_image(tmp_path / "palette.png")
    style1 = _make_image(tmp_path / "style1.png")
    feature1 = _make_image(tmp_path / "feature1.png")
    feature2 = _make_image(tmp_path / "feature2.png")

    rows_raw = [
        {"file": "medium.png", "role": "medium_ref", "provenance": "photo"},
        {"file": "palette.png", "role": "palette_ref", "provenance": "photo"},
        {"file": "style1.png", "role": "style_ref", "provenance": "gen r13", "hold_out": "door"},
        {"file": "feature1.png", "role": "feature_ref", "provenance": "gen r11"},
        {"file": "feature2.png", "role": "feature_ref", "provenance": "gen r12"},
    ]
    manifest_path = _write_manifest(tmp_path, rows_raw)

    rows = validate_manifest(load_manifest_rows(manifest_path), manifest_path.parent)

    assert len(rows) == 5
    resolved = {row.file: row.resolved_path for row in rows}
    assert resolved["medium.png"] == medium.resolve()
    assert resolved["palette.png"] == palette.resolve()
    assert resolved["style1.png"] == style1.resolve()
    assert resolved["feature1.png"] == feature1.resolve()
    assert resolved["feature2.png"] == feature2.resolve()


def test_missing_file_rejected(tmp_path):
    _make_image(tmp_path / "medium.png")
    rows_raw = [
        {"file": "medium.png", "role": "medium_ref"},
        {"file": "does-not-exist.png", "role": "palette_ref"},
    ]
    manifest_path = _write_manifest(tmp_path, rows_raw)

    try:
        validate_manifest(load_manifest_rows(manifest_path), manifest_path.parent)
    except ManifestError as exc:
        assert "does-not-exist.png" in str(exc)
        assert "does not exist" in str(exc)
    else:
        raise AssertionError("validate_manifest accepted a missing file")


def test_bad_role_rejected(tmp_path):
    _make_image(tmp_path / "medium.png")
    rows_raw = [{"file": "medium.png", "role": "backdrop_ref"}]
    manifest_path = _write_manifest(tmp_path, rows_raw)

    try:
        validate_manifest(load_manifest_rows(manifest_path), manifest_path.parent)
    except ManifestError as exc:
        assert "backdrop_ref" in str(exc)
    else:
        raise AssertionError("validate_manifest accepted an invalid role")


def test_one_role_violation_rejected(tmp_path):
    """Same file used under two different roles must be rejected.

    feature_ref is the ONLY role allowed to repeat, and only when it repeats
    with itself (multiple distinct feature refs) — not a file double-booked
    across two different roles.
    """
    _make_image(tmp_path / "shared.png")
    rows_raw = [
        {"file": "shared.png", "role": "style_ref"},
        {"file": "shared.png", "role": "palette_ref"},
    ]
    manifest_path = _write_manifest(tmp_path, rows_raw)

    try:
        validate_manifest(load_manifest_rows(manifest_path), manifest_path.parent)
    except ManifestError as exc:
        message = str(exc)
        assert "shared.png" in message
        assert "style_ref" in message and "palette_ref" in message
    else:
        raise AssertionError("validate_manifest accepted a file reused across two roles")


def test_duplicate_non_feature_role_rejected(tmp_path):
    """Two different files both claiming style_ref is fine for feature_ref only."""
    _make_image(tmp_path / "style1.png")
    _make_image(tmp_path / "style2.png")
    rows_raw = [
        {"file": "style1.png", "role": "style_ref"},
        {"file": "style2.png", "role": "style_ref"},
    ]
    manifest_path = _write_manifest(tmp_path, rows_raw)

    try:
        validate_manifest(load_manifest_rows(manifest_path), manifest_path.parent)
    except ManifestError as exc:
        assert "style_ref" in str(exc)
    else:
        raise AssertionError("validate_manifest accepted duplicate style_ref files")


def test_cli_builds_handle_dir(tmp_path):
    medium = _make_image(tmp_path / "medium.png", (200, 200, 200))
    palette = _make_image(tmp_path / "palette.png", (10, 120, 60))
    style1 = _make_image(tmp_path / "style1.png", (240, 120, 20))
    feature1 = _make_image(tmp_path / "feature1.png", (30, 30, 30))
    feature2 = _make_image(tmp_path / "feature2.png", (250, 250, 250))
    geometry = _make_image(tmp_path / "geometry.png", (0, 0, 0))
    layout = _make_image(tmp_path / "layout.png", (255, 255, 255))

    rows_raw = [
        {"file": "medium.png", "role": "medium_ref"},
        {"file": "palette.png", "role": "palette_ref"},
        {"file": "style1.png", "role": "style_ref", "hold_out": "door"},
        {"file": "feature1.png", "role": "feature_ref"},
        {"file": "feature2.png", "role": "feature_ref"},
        {"file": "geometry.png", "role": "geometry_ref"},
        {"file": "layout.png", "role": "layout_ref"},
    ]
    manifest_path = _write_manifest(tmp_path, rows_raw)
    handle_dir = tmp_path / "handle-out"

    result = subprocess.run(
        [
            sys.executable,
            str(BUILD_STYLE_HANDLE),
            "--handle-dir",
            str(handle_dir),
            "--manifest",
            str(manifest_path),
            "--timestamp",
            "2026-07-06T00:00:00Z",
            "--skip-vlm-lint",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert (handle_dir / "style-handle.yaml").exists()
    assert (handle_dir / "contact-sheet.jpg").exists()

    manifest_doc = yaml.safe_load((handle_dir / "style-handle.yaml").read_text(encoding="utf-8"))
    assert manifest_doc["created_at"] == "2026-07-06T00:00:00Z"
    assert len(manifest_doc["rows"]) == 7

    role_files = {row["role"]: row["file"] for row in manifest_doc["rows"] if row["role"] != "feature_ref"}
    for role, filename in role_files.items():
        assert role in filename
        assert (handle_dir / filename).exists()

    feature_rows = [row for row in manifest_doc["rows"] if row["role"] == "feature_ref"]
    assert len(feature_rows) == 2
    assert feature_rows[0]["file"] != feature_rows[1]["file"]
    for row in feature_rows:
        assert (handle_dir / row["file"]).exists()

    hold_out_rows = [row for row in manifest_doc["rows"] if row.get("hold_out")]
    assert len(hold_out_rows) == 1
    assert hold_out_rows[0]["hold_out"] == "door"


def test_cli_rejects_invalid_manifest_exit_code(tmp_path):
    _make_image(tmp_path / "shared.png")
    rows_raw = [
        {"file": "shared.png", "role": "style_ref"},
        {"file": "shared.png", "role": "geometry_ref"},
    ]
    manifest_path = _write_manifest(tmp_path, rows_raw)
    handle_dir = tmp_path / "handle-out"

    result = subprocess.run(
        [
            sys.executable,
            str(BUILD_STYLE_HANDLE),
            "--handle-dir",
            str(handle_dir),
            "--manifest",
            str(manifest_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "shared.png" in result.stderr
    assert not handle_dir.exists()


def test_build_fails_on_hold_out_violation(tmp_path):
    """A manifest row whose provenance is a generated output for its own hold_out panel
    must fail the build (ref_lint hold-out check), without any network call."""
    _make_image(tmp_path / "style1.png")
    rows_raw = [
        {
            "file": "style1.png",
            "role": "style_ref",
            "provenance": "round3/door/raws/s2.png",
            "hold_out": "door",
        },
    ]
    manifest_path = _write_manifest(tmp_path, rows_raw)
    handle_dir = tmp_path / "handle-out"

    result = subprocess.run(
        [
            sys.executable,
            str(BUILD_STYLE_HANDLE),
            "--handle-dir",
            str(handle_dir),
            "--manifest",
            str(manifest_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2, result.stdout + result.stderr
    assert "style1.png" in result.stderr
    assert "hold-out" in result.stderr.lower()
    assert not handle_dir.exists()


def test_build_skip_vlm_lint_prints_warning_and_still_checks_hold_out(tmp_path):
    """--skip-vlm-lint skips the text/open-door VLM checks (no network) but must still
    print a loud WARNING and still enforce the hold-out check."""
    _make_image(tmp_path / "style1.png")
    rows_raw = [
        {
            "file": "style1.png",
            "role": "style_ref",
            "provenance": "round3/door/raws/s2.png",
            "hold_out": "door",
        },
    ]
    manifest_path = _write_manifest(tmp_path, rows_raw)
    handle_dir = tmp_path / "handle-out"

    result = subprocess.run(
        [
            sys.executable,
            str(BUILD_STYLE_HANDLE),
            "--handle-dir",
            str(handle_dir),
            "--manifest",
            str(manifest_path),
            "--skip-vlm-lint",
        ],
        capture_output=True,
        text=True,
    )

    assert "WARNING" in result.stderr
    assert "skip" in result.stderr.lower()
    # hold-out check still runs even with VLM checks skipped
    assert result.returncode == 2
    assert "hold-out" in result.stderr.lower()
    assert not handle_dir.exists()


def test_load_manifest_rows_bare_list(tmp_path):
    """load_manifest_rows accepts bare list shape (input manifests)."""
    _make_image(tmp_path / "medium.png")
    rows_raw = [
        {"file": "medium.png", "role": "medium_ref"},
    ]
    manifest_path = _write_manifest(tmp_path, rows_raw)

    rows = load_manifest_rows(manifest_path)

    assert isinstance(rows, list)
    assert len(rows) == 1
    assert rows[0]["file"] == "medium.png"
    assert rows[0]["role"] == "medium_ref"


def test_load_manifest_rows_handle_mapping(tmp_path):
    """load_manifest_rows accepts mapping shape with 'rows' key (emitted handles)."""
    _make_image(tmp_path / "palette.png")
    handle_doc = {
        "created_at": "2026-07-06T00:00:00Z",
        "rows": [
            {"file": "palette.png", "role": "palette_ref", "source_file": "palette.png"},
        ],
    }
    manifest_path = tmp_path / "style-handle.yaml"
    manifest_path.write_text(yaml.safe_dump(handle_doc, sort_keys=False), encoding="utf-8")

    rows = load_manifest_rows(manifest_path)

    assert isinstance(rows, list)
    assert len(rows) == 1
    assert rows[0]["file"] == "palette.png"
    assert rows[0]["role"] == "palette_ref"


def test_load_manifest_rows_rejects_invalid_shape(tmp_path):
    """load_manifest_rows rejects mappings without 'rows' key and non-list/non-dict root."""
    manifest_path = tmp_path / "bad.yaml"

    # Test: dict without 'rows' key
    manifest_path.write_text(yaml.safe_dump({"created_at": "2026-07-06T00:00:00Z"}), encoding="utf-8")
    try:
        load_manifest_rows(manifest_path)
    except ManifestError as exc:
        assert "rows" in str(exc) or "list" in str(exc)
    else:
        raise AssertionError("load_manifest_rows accepted a dict without 'rows' key")

    # Test: dict with non-list 'rows' value
    manifest_path.write_text(yaml.safe_dump({"rows": "not-a-list"}), encoding="utf-8")
    try:
        load_manifest_rows(manifest_path)
    except ManifestError as exc:
        assert "rows" in str(exc) and "list" in str(exc)
    else:
        raise AssertionError("load_manifest_rows accepted a dict with non-list 'rows' value")

    # Test: scalar root
    manifest_path.write_text(yaml.safe_dump("not-a-list"), encoding="utf-8")
    try:
        load_manifest_rows(manifest_path)
    except ManifestError as exc:
        assert "list" in str(exc) or "rows" in str(exc)
    else:
        raise AssertionError("load_manifest_rows accepted a scalar root")
