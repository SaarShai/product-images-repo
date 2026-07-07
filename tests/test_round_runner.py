import json
import sys
from pathlib import Path

import pytest
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts import round_runner
from scripts import verify_round_artifacts


# ---------------------------------------------------------------------------
# 1. preflight refuses a guide without a sibling .approved marker
# ---------------------------------------------------------------------------

def test_preflight_refuses_guide_without_approved_marker(tmp_path, monkeypatch):
    guide = tmp_path / "arm-a.png"
    Image.new("RGB", (20, 20), (255, 0, 0)).save(guide)
    # no arm-a.png.approved marker written

    log = round_runner.RunLog(tmp_path / "runner.log")
    with pytest.raises(round_runner.RoundError) as excinfo:
        round_runner.preflight_guides_approved([str(guide)], log)
    log.close()

    assert excinfo.value.step == "preflight"
    assert "approved" in excinfo.value.message.lower()


def test_preflight_passes_guide_with_approved_marker(tmp_path):
    guide = tmp_path / "arm-a.png"
    Image.new("RGB", (20, 20), (255, 0, 0)).save(guide)
    marker = guide.with_suffix(guide.suffix + ".approved")
    marker.write_text("approved by leader\n")

    log = round_runner.RunLog(tmp_path / "runner.log")
    round_runner.preflight_guides_approved([str(guide)], log)  # should not raise
    log.close()


# ---------------------------------------------------------------------------
# 1b. preflight_callouts_lint routes --geom through to the callouts_lint subcall
# ---------------------------------------------------------------------------

def test_preflight_callouts_lint_passes_geom_through(tmp_path, monkeypatch):
    calls = []

    def fake_run(cmd, log, step, check=True):
        calls.append(cmd)
        class P:
            returncode = 0
        return P()

    monkeypatch.setattr(round_runner, "_run", fake_run)
    monkeypatch.setattr(round_runner, "_require_tool", lambda *a, **k: None)

    log = round_runner.RunLog(tmp_path / "runner.log")
    round_runner.preflight_callouts_lint("callouts.yaml", "geom-dir", log)
    log.close()

    assert len(calls) == 1
    cmd = [str(c) for c in calls[0]]
    assert "--geom" in cmd
    geom_idx = cmd.index("--geom")
    assert cmd[geom_idx + 1].endswith("geom-dir")


# ---------------------------------------------------------------------------
# 2. budget counter refuses call N+1 (mock subgen via an injectable fake script)
# ---------------------------------------------------------------------------

def _fake_subgen_script(tmp_path) -> Path:
    """A stand-in for subgen.py that writes a tiny valid PNG to --out."""
    script = tmp_path / "fake_subgen.py"
    script.write_text(
        "import argparse\n"
        "from PIL import Image\n"
        "ap = argparse.ArgumentParser()\n"
        "ap.add_argument('--provider')\n"
        "ap.add_argument('--out')\n"
        "ap.add_argument('--prompt', default=None)\n"
        "ap.add_argument('--prompt-file', default=None)\n"
        "ap.add_argument('-i', '--image', nargs='*', default=[])\n"
        "a = ap.parse_args()\n"
        "import random\n"
        "random.seed(0)\n"
        "px = [tuple(random.randrange(256) for _ in range(3)) for _ in range(512 * 512)]\n"
        "img = Image.new('RGB', (512, 512))\n"
        "img.putdata(px)\n"
        "img.save(a.out)\n"
    )
    return script


def test_generate_refuses_to_exceed_max_calls(tmp_path, monkeypatch):
    fake_subgen = _fake_subgen_script(tmp_path)
    monkeypatch.setattr(round_runner, "SCRIPTS", tmp_path)
    monkeypatch.setattr(round_runner, "PY", sys.executable)
    # round_runner.run_generate looks up SCRIPTS / "subgen.py"
    (tmp_path / "subgen.py").write_text(fake_subgen.read_text())

    guide = tmp_path / "guide.png"
    Image.new("RGB", (20, 20), (0, 255, 0)).save(guide)

    round_dir = tmp_path / "round1"
    round_dir.mkdir()

    class Args:
        arms = ["arm-a:guide.png:3"]
        handle = None
        extra_refs = []
        max_calls = 2  # budget smaller than the 3 requested samples
        provider = "openai"

    args = Args()
    args.guide_path = guide

    log = round_runner.RunLog(round_dir / "runner.log")
    monkeypatch.chdir(tmp_path)
    # patch guide resolution: arm spec references "guide.png" relative to tmp_path
    monkeypatch.setattr(round_runner, "_abs", lambda p: (tmp_path / p) if not Path(p).is_absolute() else Path(p))

    with pytest.raises(round_runner.RoundError) as excinfo:
        round_runner.run_generate(args, round_dir, log)
    log.close()

    assert excinfo.value.step == "generate"
    assert "max-calls" in excinfo.value.message.lower() or "budget" in excinfo.value.message.lower()


def test_generate_stops_exactly_at_budget_not_beyond(tmp_path, monkeypatch):
    """Sanity: a plan that exactly matches the budget must be refused up-front
    only when it EXCEEDS the budget; equal-to-budget must succeed."""
    fake_subgen = _fake_subgen_script(tmp_path)
    (tmp_path / "subgen.py").write_text(fake_subgen.read_text())
    monkeypatch.setattr(round_runner, "SCRIPTS", tmp_path)
    monkeypatch.setattr(round_runner, "PY", sys.executable)
    monkeypatch.setattr(round_runner, "_abs", lambda p: (tmp_path / p) if not Path(p).is_absolute() else Path(p))

    guide = tmp_path / "guide.png"
    Image.new("RGB", (20, 20), (0, 255, 0)).save(guide)

    round_dir = tmp_path / "round2"
    round_dir.mkdir()

    class Args:
        arms = ["arm-a:guide.png:2"]
        handle = None
        extra_refs = []
        max_calls = 2
        provider = "openai"

    log = round_runner.RunLog(round_dir / "runner.log")
    raws = round_runner.run_generate(Args(), round_dir, log)
    log.close()

    assert len(raws) == 2
    for raw in raws:
        assert Path(raw["raw_path"]).exists()


# ---------------------------------------------------------------------------
# 3. verify_round_artifacts catches a missing overlay
# ---------------------------------------------------------------------------

def _minimal_round(tmp_path, with_overlay=True, with_results=True):
    round_dir = tmp_path / "roundX"
    (round_dir / "raws").mkdir(parents=True)
    (round_dir / "gates").mkdir(parents=True)
    (round_dir / "prompts").mkdir(parents=True)
    (round_dir / "guides").mkdir(parents=True)

    raw_path = round_dir / "raws" / "arm-a_s1.png"
    Image.new("RGB", (16, 16), (5, 5, 5)).save(raw_path)
    (round_dir / "prompts" / "arm-a_prompt.md").write_text("prompt\n")
    (round_dir / "guides" / "arm-a.png").write_bytes(b"\x89PNG\r\n")

    overlay_path = round_dir / "gates" / "arm-a_s1-overlay.png"
    if with_overlay:
        Image.new("RGB", (16, 16), (9, 9, 9)).save(overlay_path)

    overlay_board = round_dir / f"{round_dir.name}-board.png"
    Image.new("RGB", (8, 8)).save(overlay_board)
    inputs_board = round_dir / f"INPUTS-{round_dir.name}.jpg"
    Image.new("RGB", (8, 8)).save(inputs_board, format="JPEG")

    if with_results:
        rows = [{"arm": "arm-a", "sample": "s1", "raw_path": str(raw_path),
                 "overlay_path": str(overlay_path) if with_overlay else None}]
        (round_dir / f"{round_dir.name}-results.json").write_text(json.dumps(rows))

    review_dir = tmp_path / "REVIEW" / "sometask" / round_dir.name
    review_dir.mkdir(parents=True)
    for board in (overlay_board, inputs_board):
        (review_dir / board.name).write_bytes(board.read_bytes())

    return round_dir


def test_verify_catches_missing_overlay(tmp_path):
    round_dir = _minimal_round(tmp_path, with_overlay=False, with_results=True)
    missing = verify_round_artifacts.verify(round_dir, task="sometask", review_root=tmp_path / "REVIEW")
    assert missing, "expected verify() to report missing items"
    assert any("overlay" in m.lower() for m in missing)


def test_verify_passes_on_complete_round(tmp_path):
    round_dir = _minimal_round(tmp_path, with_overlay=True, with_results=True)
    missing = verify_round_artifacts.verify(round_dir, task="sometask", review_root=tmp_path / "REVIEW")
    assert missing == []


# ---------------------------------------------------------------------------
# 4. results-row schema rejects a null overlay_path
# ---------------------------------------------------------------------------

def test_verify_rejects_null_overlay_path_in_results_row(tmp_path):
    round_dir = _minimal_round(tmp_path, with_overlay=True, with_results=False)
    # write a results.json row with overlay_path explicitly null
    rows = [{
        "arm": "arm-a",
        "sample": "s1",
        "raw_path": str(round_dir / "raws" / "arm-a_s1.png"),
        "overlay_path": None,
    }]
    (round_dir / f"{round_dir.name}-results.json").write_text(json.dumps(rows))

    missing = verify_round_artifacts.verify(round_dir, task="sometask", review_root=tmp_path / "REVIEW")
    assert any("overlay_path" in m for m in missing)


# ---------------------------------------------------------------------------
# 5. run_gates invokes content_gate.py WITHOUT --panel (content_gate.py's CLI
#    is --image/--geom/--overlay only; it has no --panel flag)
# ---------------------------------------------------------------------------

def test_run_gates_calls_content_gate_without_panel(tmp_path, monkeypatch):
    calls = []

    def fake_run(cmd, log, step, check=True):
        cmd_s = [str(c) for c in cmd]
        calls.append(cmd_s)
        if "gates.py" in cmd_s[1] and "--outdir" in cmd_s and "--output-stem" in cmd_s:
            outdir = Path(cmd_s[cmd_s.index("--outdir") + 1])
            output_stem = cmd_s[cmd_s.index("--output-stem") + 1]
            outdir.mkdir(parents=True, exist_ok=True)
            bundle_path = outdir / f"{output_stem}-bundle.json"
            overlay_path = outdir / f"{output_stem}-overlay.png"
            Image.new("RGB", (4, 4)).save(overlay_path)
            bundle = {
                "overall_verdict": "PASS",
                "bundle_path": str(bundle_path),
                "overlay_path": str(overlay_path),
            }
            bundle_path.write_text(json.dumps(bundle))
            class P:
                returncode = 0
                stdout = json.dumps(bundle)
                stderr = ""
            return P()
        if "door_fill_gate.py" in cmd_s[1] and "--overlay" in cmd_s:
            overlay_out = Path(cmd_s[cmd_s.index("--overlay") + 1])
            Image.new("RGB", (4, 4)).save(overlay_out)
        class P:
            returncode = 0
            stdout = "{}"
            stderr = ""
        return P()

    monkeypatch.setattr(round_runner, "_run", fake_run)
    monkeypatch.setattr(round_runner, "_require_tool", lambda *a, **k: None)
    monkeypatch.setattr(round_runner, "_abs", lambda p: Path(p))

    round_dir = tmp_path / "round1"
    raw_path = round_dir / "raws" / "arm-a_s1.png"
    raw_path.parent.mkdir(parents=True)
    Image.new("RGB", (16, 16), (5, 5, 5)).save(raw_path)

    class Args:
        geom = "geom-dir"
        panel = "door"
        callouts = None

    log = round_runner.RunLog(round_dir / "runner.log")
    raws = [{"arm": "arm-a", "sample": "s1", "raw_path": str(raw_path)}]
    round_runner.run_gates(Args(), round_dir, raws, log)
    log.close()

    content_calls = [c for c in calls if "content_gate.py" in c[1]]
    assert len(content_calls) == 1, f"expected exactly one content_gate.py call, got {content_calls}"
    assert "--panel" not in content_calls[0], f"content_gate.py has no --panel flag: {content_calls[0]}"
    assert "--image" in content_calls[0]
    assert "--geom" in content_calls[0]
    assert "--overlay" in content_calls[0]
    overlay_idx = content_calls[0].index("--overlay")
    assert str(round_dir / "gates") in content_calls[0][overlay_idx + 1]

    gates_calls = [c for c in calls if "gates.py" in c[1]]
    assert len(gates_calls) == 1, f"expected exactly one gates.py call, got {gates_calls}"
    assert "--output-stem" in gates_calls[0]
    stem_idx = gates_calls[0].index("--output-stem")
    assert gates_calls[0][stem_idx + 1] == "arm-a_s1-door-finish"


# ---------------------------------------------------------------------------
# 6. run_boards invokes overlay_board.py with --raws/--geom/--out (not
#    positionally), and inputs_board.py with the round_dir positional arg
# ---------------------------------------------------------------------------

def test_run_boards_calls_overlay_board_with_flags(tmp_path, monkeypatch):
    calls = []

    def fake_run(cmd, log, step, check=True):
        calls.append([str(c) for c in cmd])
        class P:
            returncode = 0
            stdout = ""
            stderr = ""
        return P()

    monkeypatch.setattr(round_runner, "_run", fake_run)
    monkeypatch.setattr(round_runner, "_require_tool", lambda *a, **k: None)
    monkeypatch.setattr(round_runner, "_abs", lambda p: Path(p))

    round_dir = tmp_path / "round1"
    round_dir.mkdir()

    class Args:
        geom = "geom-dir"

    log = round_runner.RunLog(round_dir / "runner.log")
    round_runner.run_boards(Args(), round_dir, log)
    log.close()

    overlay_calls = [c for c in calls if "overlay_board.py" in c[1]]
    inputs_calls = [c for c in calls if "inputs_board.py" in c[1]]
    assert len(overlay_calls) == 1, f"expected exactly one overlay_board.py call, got {overlay_calls}"
    cmd = overlay_calls[0]
    assert "--raws" in cmd, cmd
    assert "--geom" in cmd, cmd
    assert "--out" in cmd, cmd
    raws_idx = cmd.index("--raws")
    assert "raws" in cmd[raws_idx + 1] and "*.png" in cmd[raws_idx + 1]
    geom_idx = cmd.index("--geom")
    assert cmd[geom_idx + 1].endswith("geom-dir")
    out_idx = cmd.index("--out")
    assert cmd[out_idx + 1].endswith("-overlay-board.jpg")

    assert len(inputs_calls) == 1, f"expected exactly one inputs_board.py call, got {inputs_calls}"
    assert str(round_dir) in inputs_calls[0]
