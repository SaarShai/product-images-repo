"""Regression test for geom_adherence_test.py's missing --refs precondition
(geometry-evidentiary-princess-n02 Finding 6).

Root cause: the script had no ref-count guard; with --refs omitted (or
empty) it proceeded straight into a real, paid generation call. Contract
requires refusal with the exact message ``style.ref_images must contain at
least one path`` BEFORE any generation is attempted.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "geom_adherence_test.py"
EXPECTED_MESSAGE = "style.ref_images must contain at least one path"


def load_module():
    spec = importlib.util.spec_from_file_location("geom_adherence_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_cli_refuses_with_zero_refs_before_any_generation(tmp_path):
    """End-to-end subprocess check: exact message, nonzero exit, and no
    experiment artifacts (raw.png / metrics.json) are ever written — proof
    the refusal happens before the generation step, not just before scoring."""
    outdir = tmp_path / "experiments"
    map_png = tmp_path / "map.png"
    map_png.write_bytes(b"not a real png, refusal must happen first")
    prompt_md = tmp_path / "prompt.md"
    prompt_md.write_text("a prompt")
    svg = tmp_path / "template.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"/>')

    proc = subprocess.run(
        [
            sys.executable, str(SCRIPT),
            "--id", "safe-stop-probe-zero-refs", "--model", "openai",
            "--map", str(map_png), "--prompt", str(prompt_md),
            "--svg", str(svg), "--outdir", str(outdir),
        ],
        capture_output=True, text=True,
    )
    assert proc.returncode != 0
    assert EXPECTED_MESSAGE in proc.stderr
    # No experiment dir/artifacts must exist — proves the refusal happened
    # before exp.mkdir()/generation, not after a failed generation attempt.
    assert not outdir.exists()


def test_main_never_reaches_gen_entry_point_with_zero_refs(tmp_path, monkeypatch):
    """Mock the subgen generation entry point so any call raises; prove it
    is never invoked when --refs is empty."""

    def _boom(*args, **kwargs):
        raise AssertionError("generation entry point must not be reached with zero refs")

    fake_subgen = type(sys)("subgen")
    fake_subgen.gen_openai = _boom
    fake_subgen.gen_nano = _boom
    monkeypatch.setitem(sys.modules, "subgen", fake_subgen)

    module = load_module()

    outdir = tmp_path / "experiments"
    map_png = tmp_path / "map.png"
    map_png.write_bytes(b"not a real png")
    prompt_md = tmp_path / "prompt.md"
    prompt_md.write_text("a prompt")
    svg = tmp_path / "template.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"/>')

    argv = [
        "geom_adherence_test.py",
        "--id", "safe-stop-probe-zero-refs", "--model", "openai",
        "--map", str(map_png), "--prompt", str(prompt_md),
        "--svg", str(svg), "--outdir", str(outdir),
    ]
    monkeypatch.setattr(sys, "argv", argv)

    with pytest.raises(SystemExit) as excinfo:
        module.main()
    assert str(excinfo.value) == EXPECTED_MESSAGE
    assert not outdir.exists()
