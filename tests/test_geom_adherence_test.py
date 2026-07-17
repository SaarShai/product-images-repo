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


# --- Finding A: bare "python3" + unchecked returncode on the svg_geometry_check.py
# subprocess call. Pre-fix, a failing child process's stderr (the real guard
# message) was swallowed by capture_output and execution fell through to
# json.loads(metrics.json) — which was never written — raising an opaque
# FileNotFoundError instead of surfacing the actual failure. -----------------

from PIL import Image  # noqa: E402


def _write_min_png(path: Path, size: tuple[int, int] = (12, 12), color=(255, 255, 255)) -> None:
    Image.new("RGB", size, color).save(path)


def _install_fake_subgen(monkeypatch) -> None:
    """Stand in for scripts/subgen.py: writes a tiny real PNG so the rest of
    main() (auto_bbox, the svg_geometry_check.py subprocess call) can run
    without a real (paid) generation call."""
    fake_subgen = type(sys)("subgen")

    def _gen(prompt, images, out, timeout, retries=3):
        _write_min_png(Path(out))
        return str(out)

    fake_subgen.gen_openai = _gen
    fake_subgen.gen_nano = _gen
    monkeypatch.setitem(sys.modules, "subgen", fake_subgen)


def _argv_for_svg_check_probe(tmp_path: Path, outdir: Path) -> list[str]:
    map_png = tmp_path / "map.png"
    _write_min_png(map_png)
    prompt_md = tmp_path / "prompt.md"
    prompt_md.write_text("a prompt")
    ref_png = tmp_path / "ref.png"
    _write_min_png(ref_png)
    svg = tmp_path / "template.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"/>')
    return [
        "geom_adherence_test.py",
        "--id", "svg-check-probe", "--model", "openai",
        "--map", str(map_png), "--prompt", str(prompt_md), "--refs", str(ref_png),
        "--svg", str(svg), "--outdir", str(outdir),
    ]


def test_failed_svg_geometry_check_raises_systemexit_with_stderr_not_filenotfounderror(tmp_path, monkeypatch):
    """Simulate svg_geometry_check.py crashing (nonzero returncode, guard
    message on stderr, metrics.json never written). Post-fix: main() must
    raise SystemExit with the child's stderr visible BEFORE attempting to
    read metrics.json — never a FileNotFoundError that hides the real cause."""
    outdir = tmp_path / "experiments"
    _install_fake_subgen(monkeypatch)
    module = load_module()

    def _fake_run(cmd, cwd=None, capture_output=None, text=None):
        assert cmd[1] == "scripts/svg_geometry_check.py"
        return subprocess.CompletedProcess(cmd, returncode=2, stdout="", stderr="SIMULATED GUARD MESSAGE: bad --svg")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    monkeypatch.setattr(module.sys, "argv", _argv_for_svg_check_probe(tmp_path, outdir))

    with pytest.raises(SystemExit) as excinfo:
        module.main()
    assert "SIMULATED GUARD MESSAGE: bad --svg" in str(excinfo.value)
    exp = outdir / "svg-check-probe"
    assert not (exp / "metrics.json").exists()


def test_svg_geometry_check_invoked_via_sys_executable_not_bare_python3(tmp_path, monkeypatch):
    """The subprocess call must invoke sys.executable (documented invocation
    is /usr/bin/python3, so sys.executable inherits it) rather than a bare
    "python3" that resolves via PATH lookup."""
    outdir = tmp_path / "experiments"
    _install_fake_subgen(monkeypatch)
    module = load_module()
    seen: dict = {}

    def _fake_run(cmd, cwd=None, capture_output=None, text=None):
        seen["cmd"] = cmd
        json_out = Path(cmd[cmd.index("--json-out") + 1])
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text('{"overall": "PASS", "mean_iou": 1.0, "outside_frac": 0.0, "holes": []}')
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    monkeypatch.setattr(module.sys, "argv", _argv_for_svg_check_probe(tmp_path, outdir))

    rc = module.main()
    assert rc == 0
    assert seen["cmd"][0] == sys.executable
    assert seen["cmd"][0] != "python3"
