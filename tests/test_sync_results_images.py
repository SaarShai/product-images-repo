"""Regression test for sync_results_images.py's hardcoded task glob
(geometry-evidentiary-princess-n02 Finding 7).

Root cause: the script only globbed `tasks/space-*/experiments*/`, so any
other task's results were a silent no-op that still printed "OK". Fix adds a
--task selector (default = the original space-* behavior, unchanged) and an
explicit warning + nonzero exit when --task matches no directory.
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "sync_results_images.py"


def run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, cwd=REPO,
    )


def _make_task_with_result(tmp_root: Path, task_name: str, exp_dir_name: str, cell: str):
    """Build a minimal tasks/<task_name>/<exp_dir_name>/<cell>/raw.png fixture
    under a throwaway ROOT-shaped tree, then monkeypatch the script's ROOT."""
    tdir = tmp_root / "tasks" / task_name
    cell_dir = tdir / exp_dir_name / cell
    cell_dir.mkdir(parents=True)
    (cell_dir / "raw.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    return tdir


def test_backward_compat_default_task_matches_original_hardcoded_behavior():
    """Default (--task omitted) must reproduce the exact original message
    against the real repo state — the space-np01 central library."""
    proc = run("--check")
    assert proc.returncode == 0
    assert "OK — every result image has a copy in tasks/space-np01-front-bottom-02/RESULTS/Images" in proc.stdout


def test_no_task_match_prints_explicit_warning_not_silent_ok():
    proc = run("--task", "this-task-name-does-not-exist-xyz", "--check")
    assert proc.returncode != 0
    assert "WARNING" in proc.stderr
    assert "this-task-name-does-not-exist-xyz" in proc.stderr
    # must NOT fall through to the misleading "OK" message
    assert "OK —" not in proc.stdout


def test_task_flag_targets_a_real_non_space_task(tmp_path, monkeypatch):
    """--task <name> on a real (non-space-*) task dir must find its own
    results and route them to that task's own RESULTS/Images — not the
    space-np01 central library, and not silently report nothing to sync."""
    import importlib.util

    tmp_root = tmp_path / "repo"
    (tmp_root / "tasks").mkdir(parents=True)
    _make_task_with_result(tmp_root, "some-other-task", "experiments", "probe-01")

    spec = importlib.util.spec_from_file_location("sync_results_images", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    monkeypatch.setattr(module, "ROOT", tmp_root)
    monkeypatch.setattr(module, "IMG", tmp_root / "tasks/space-np01-front-bottom-02/RESULTS/Images")

    dirs = module.task_dirs("some-other-task")
    assert len(dirs) == 1

    img_dir = module.images_dir_for("some-other-task")
    assert img_dir == tmp_root / "tasks" / "some-other-task" / "RESULTS" / "Images"

    found = list(module.sources("some-other-task", img_dir))
    assert len(found) == 1
    src, dest = found[0]
    assert src.name == "raw.png"
    assert dest.name == "some-other-task__probe-01__raw.png"
