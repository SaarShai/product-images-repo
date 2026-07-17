"""Regression test for scaffold_template_task.py's hard collision error
(geometry-evidentiary-princess-n02 Finding 1).

Root cause: an unconditional `if task_dir.exists(): raise SystemExit(...)`
made it impossible to scaffold a task dir that was pre-seeded with a
hand-authored contract file (e.g. an evidentiary-run brief placed there
before scaffolding runs). Fix adds --allow-existing: scaffold the MISSING
pieces into an existing dir without ever touching files already there.
"""

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "scaffold_template_task.py"
REAL_TEMPLATE_DIR = REPO / "tasks" / "_template"


def load_module():
    spec = importlib.util.spec_from_file_location("scaffold_template_task", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def fake_repo(tmp_path, monkeypatch):
    """A throwaway ROOT with a real copy of tasks/_template, so rendering
    works exactly like it does against the real repo."""
    root = tmp_path / "repo"
    (root / "tasks").mkdir(parents=True)
    shutil.copytree(REAL_TEMPLATE_DIR, root / "tasks" / "_template")

    module = load_module()
    monkeypatch.setattr(module, "ROOT", root)
    monkeypatch.setattr(module, "TEMPLATE_DIR", root / "tasks" / "_template")
    return module, root


def _svg_and_ref(tmp_path):
    svg = tmp_path / "input.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        '<path d="M0,0 L10,0 L10,10 L0,10 Z"/></svg>'
    )
    ref = tmp_path / "ref1.png"
    Image.new("RGB", (4, 4), "red").save(ref)
    return svg, ref


def test_without_allow_existing_still_hard_errors_on_pre_existing_dir(fake_repo, tmp_path):
    """Regression guard: the original collision behavior must be unchanged
    when --allow-existing is NOT passed."""
    module, root = fake_repo
    task_dir = root / "tasks" / "evidentiary-probe"
    task_dir.mkdir(parents=True)
    (task_dir / "EVIDENTIARY-RUN.md").write_text("frozen contract\n")

    svg, ref = _svg_and_ref(tmp_path)
    argv = [
        "scaffold_template_task.py", "evidentiary-probe",
        "--svg", str(svg), "--refs", str(ref),
    ]
    import sys as _sys
    old_argv = _sys.argv
    _sys.argv = argv
    try:
        with pytest.raises(SystemExit) as excinfo:
            module.main()
    finally:
        _sys.argv = old_argv
    assert "Task already exists" in str(excinfo.value)


def test_allow_existing_scaffolds_missing_pieces_without_touching_existing_file(fake_repo, tmp_path):
    module, root = fake_repo
    task_dir = root / "tasks" / "evidentiary-probe"
    task_dir.mkdir(parents=True)
    contract = task_dir / "EVIDENTIARY-RUN.md"
    contract_text = "frozen contract — do not touch\n"
    contract.write_text(contract_text)
    contract_mtime_before = contract.stat().st_mtime_ns

    svg, ref = _svg_and_ref(tmp_path)
    argv = [
        "scaffold_template_task.py", "evidentiary-probe",
        "--svg", str(svg), "--refs", str(ref),
        "--allow-existing",
    ]
    import sys as _sys
    old_argv = _sys.argv
    _sys.argv = argv
    try:
        rc = module.main()
    finally:
        _sys.argv = old_argv
    assert rc == 0

    # the pre-existing contract file must be byte-identical and untouched
    assert contract.read_text() == contract_text
    assert contract.stat().st_mtime_ns == contract_mtime_before

    # the missing scaffold structure must now exist
    assert (task_dir / "source" / "template.svg").is_file()
    assert (task_dir / "refs").is_dir()
    assert any((task_dir / "refs").iterdir())
    assert (task_dir / "style-packet").is_dir()
    assert (task_dir / "prompts" / "prompt-v1-contour-first.md").is_file()
    assert (task_dir / "outputs" / "generated").is_dir()
    assert (task_dir / "outputs" / "reviews").is_dir()
    assert (task_dir / "outputs" / "final").is_dir()
    assert (task_dir / "asset-manifest.json").is_file()
    assert (task_dir / "template-manifest.json").is_file()
    assert (task_dir / "session-brief.md").is_file()
    assert (task_dir / "review-judge.md").is_file()


def test_allow_existing_does_not_overwrite_an_already_scaffolded_file(fake_repo, tmp_path):
    """A second --allow-existing run must not clobber a piece that a PRIOR
    scaffold run (or a hand-edit) already wrote."""
    module, root = fake_repo
    task_dir = root / "tasks" / "evidentiary-probe"
    task_dir.mkdir(parents=True)
    session_brief = task_dir / "session-brief.md"
    session_brief.parent.mkdir(parents=True, exist_ok=True)
    custom_text = "HAND-EDITED session brief — must survive rescaffold\n"
    session_brief.write_text(custom_text)

    svg, ref = _svg_and_ref(tmp_path)
    argv = [
        "scaffold_template_task.py", "evidentiary-probe",
        "--svg", str(svg), "--refs", str(ref),
        "--allow-existing",
    ]
    import sys as _sys
    old_argv = _sys.argv
    _sys.argv = argv
    try:
        rc = module.main()
    finally:
        _sys.argv = old_argv
    assert rc == 0
    assert session_brief.read_text() == custom_text
    # everything else still got scaffolded
    assert (task_dir / "review-judge.md").is_file()
