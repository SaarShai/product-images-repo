#!/usr/bin/env python3
"""round_runner.py — THE single mechanical entry point for a generation round.

No agent-improvised rounds after this: every round (per
tasks/workflow-rebuild/ENFORCEMENT-MATRIX.md rows 1, 7, 8, 12, 14, 15, 19, 20)
must go through this script, in this order, every time:

  1. PREFLIGHT (hard-fail on any):
       (a) every --guides path has a sibling <name>.approved marker file
       (b) callouts_lint.py clean on --callouts
       (c) style handle validates (build_style_handle.py --validate-only on --handle)
       (d) every preflight/gate tool this round needs actually exists on disk
  2. GENERATE — scripts/subgen.py ONLY, N images per --arms "name:guide:count"
     arm, refs = [guide, handle role images, any --extra-refs], hard --max-calls
     budget (refuse to exceed), every output PIL-verified before counting.
  3. GATES — per raw, no sampling: gates.py (registered resize first),
     door_fill_gate.py, emblem_gate.py (WARN+skip if no key), content_gate.py;
     one results.json row per raw, overlay_path REQUIRED non-null.
  4. BOARDS — overlay_board.py (clean+overlay pairs) and inputs_board.py; both
     mandatory.
  5. verify_round_artifacts.py — asserts the full round-dir contract; a
     non-zero exit here fails the whole round.
  6. Any --repair step is followed by an AUTOMATIC emblem_gate re-run on the
     repaired outputs (post-restyle rule, matrix row 12).

Every step is logged, in order, to <round>/runner.log.

CLI:
  python3 scripts/round_runner.py \
      --round-dir tasks/<task>/roundN \
      --guides guides/arm-a.png guides/arm-b.png \
      --callouts style-spec/feature-callouts.yaml \
      --handle handle/style-handle.yaml \
      --arms "arm-a:guides/arm-a.png:5" "arm-b:guides/arm-b.png:5" \
      --geom geometry-dir --panel door \
      [--provider openai] [--max-calls 14] [--extra-refs a.png b.png] \
      [--repair path/to/repair_tool.py --repair-args ...]

Exit codes: 0 = round complete and verified; 1 = preflight/gate/verify failure
(see runner.log + stderr for which step and why); 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PY = sys.executable or "python3"


class RoundError(RuntimeError):
    """A hard-fail in the round contract. Carries the step name for logging."""

    def __init__(self, step: str, message: str):
        super().__init__(f"[{step}] {message}")
        self.step = step
        self.message = message


class RunLog:
    """Appends timestamped lines to <round>/runner.log and echoes to stderr."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")

    def log(self, step: str, message: str) -> None:
        line = f"[{step}] {message}"
        self._fh.write(line + "\n")
        self._fh.flush()
        print(line, file=sys.stderr)

    def close(self) -> None:
        self._fh.close()


def _abs(path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def _require_tool(tool_path: Path, name: str) -> None:
    """Hard-fail, naming the missing preflight tool, if it doesn't exist yet."""
    if not tool_path.exists():
        raise RoundError(
            "preflight",
            f"required tool '{name}' does not exist at {tool_path} — "
            f"preflight tool missing = HARD FAIL",
        )


def _run(cmd: list, log: RunLog, step: str, check: bool = True) -> subprocess.CompletedProcess:
    log.log(step, "running: " + " ".join(str(c) for c in cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.stdout:
        log.log(step, "stdout: " + proc.stdout.strip()[:4000])
    if proc.stderr:
        log.log(step, "stderr: " + proc.stderr.strip()[:4000])
    if check and proc.returncode != 0:
        raise RoundError(step, f"command failed (exit {proc.returncode}): {' '.join(str(c) for c in cmd)}")
    return proc


# ---------------------------------------------------------------------------
# 1. PREFLIGHT
# ---------------------------------------------------------------------------

def preflight_guides_approved(guides: list, log: RunLog) -> None:
    """(a) every guide passed via --guides has a sibling <name>.approved marker."""
    for guide in guides:
        gpath = _abs(guide)
        marker = gpath.with_suffix(gpath.suffix + ".approved")
        if not marker.exists():
            raise RoundError(
                "preflight",
                f"guide '{gpath}' has no sibling approval marker '{marker.name}' — "
                f"guide vision-gate (matrix row 7) requires a leader-written .approved "
                f"marker before this guide may enter a round",
            )
        log.log("preflight", f"guide approved: {gpath} (marker {marker.name})")


def preflight_callouts_lint(callouts, geom, log: RunLog) -> None:
    """(b) callouts_lint.py clean on --callouts (routed against --geom)."""
    if callouts is None:
        log.log("preflight", "no --callouts passed — skipping callouts_lint")
        return
    tool = SCRIPTS / "callouts_lint.py"
    _require_tool(tool, "callouts_lint.py")
    proc = _run(
        [PY, str(tool), "--callouts", str(_abs(callouts)), "--geom", str(_abs(geom))],
        log, "preflight", check=False,
    )
    if proc.returncode != 0:
        raise RoundError(
            "preflight",
            f"callouts_lint.py FAILED on {callouts} (exit {proc.returncode}) — "
            f"callout zones must be clear of stripes/anchors before generation (matrix row 8)",
        )


def preflight_style_handle(handle, log: RunLog) -> None:
    """(c) style handle validates (re-run build_style_handle validation)."""
    if handle is None:
        log.log("preflight", "no --handle passed — skipping style-handle validation")
        return
    tool = SCRIPTS / "build_style_handle.py"
    _require_tool(tool, "build_style_handle.py")
    manifest_path = _abs(handle)
    sys.path.insert(0, str(ROOT))
    try:
        from scripts.build_style_handle import ManifestError, load_manifest_rows, validate_manifest
    except Exception as exc:  # pragma: no cover - import failure is itself a hard fail
        raise RoundError("preflight", f"could not import build_style_handle.py: {exc}")
    try:
        rows_raw = load_manifest_rows(manifest_path)
        validate_manifest(rows_raw, manifest_path.parent)
    except ManifestError as exc:
        raise RoundError("preflight", f"style handle '{manifest_path}' failed validation: {exc}")
    except Exception as exc:
        raise RoundError("preflight", f"style handle '{manifest_path}' could not be validated: {exc}")
    log.log("preflight", f"style handle validated: {manifest_path}")


REQUIRED_PIPELINE_TOOLS = [
    ("subgen.py", "subgen.py"),
    ("gates.py", "gates.py"),
    ("door_fill_gate.py", "door_fill_gate.py"),
    ("emblem_gate.py", "emblem_gate.py"),
    ("content_gate.py", "content_gate.py"),
    ("inputs_board.py", "inputs_board.py"),
    ("overlay_board.py", "overlay_board.py"),
    ("verify_round_artifacts.py", "verify_round_artifacts.py"),
]


def preflight_tools_exist(log: RunLog) -> None:
    """(d) all preflight/pipeline tools this round depends on exist."""
    for filename, name in REQUIRED_PIPELINE_TOOLS:
        _require_tool(SCRIPTS / filename, name)
        log.log("preflight", f"tool present: {name}")


def run_preflight(args, log: RunLog) -> None:
    preflight_tools_exist(log)
    preflight_guides_approved(args.guides or [], log)
    preflight_callouts_lint(args.callouts, args.geom, log)
    preflight_style_handle(args.handle, log)
    log.log("preflight", "PREFLIGHT PASS")


# ---------------------------------------------------------------------------
# 2. GENERATE
# ---------------------------------------------------------------------------

def parse_arm_spec(spec: str) -> dict:
    parts = spec.split(":")
    if len(parts) != 3:
        raise RoundError("generate", f"malformed --arms entry '{spec}' — expected name:guide:count")
    name, guide, count_s = parts
    try:
        count = int(count_s)
    except ValueError:
        raise RoundError("generate", f"malformed --arms entry '{spec}' — count '{count_s}' is not an int")
    if count < 1:
        raise RoundError("generate", f"malformed --arms entry '{spec}' — count must be >= 1")
    return {"name": name, "guide": guide, "count": count}


def _handle_role_images(handle, log: RunLog) -> list:
    """Resolve the reference image paths (any role) listed in a style handle."""
    if handle is None:
        return []
    manifest_path = _abs(handle)
    sys.path.insert(0, str(ROOT))
    from scripts.build_style_handle import load_manifest_rows
    rows = load_manifest_rows(manifest_path)
    imgs = []
    for row in rows:
        fname = row.get("file")
        if not fname:
            continue
        p = manifest_path.parent / fname
        imgs.append(str(p))
    return imgs


def _valid_image(path: Path) -> bool:
    try:
        from PIL import Image
        if not path.exists() or path.stat().st_size < 8000:
            return False
        Image.open(path).verify()
        return True
    except Exception:
        return False


def run_generate(args, round_dir: Path, log: RunLog) -> list:
    """Generate every arm's samples via subgen.py ONLY. Returns list of raw dicts."""
    subgen = SCRIPTS / "subgen.py"
    _require_tool(subgen, "subgen.py")

    arms = [parse_arm_spec(s) for s in args.arms]
    handle_refs = _handle_role_images(args.handle, log)
    extra_refs = [str(_abs(p)) for p in (args.extra_refs or [])]

    raws_dir = round_dir / "raws"
    raws_dir.mkdir(parents=True, exist_ok=True)
    prompts_dir = round_dir / "prompts"

    total_planned = sum(a["count"] for a in arms)
    if total_planned > args.max_calls:
        raise RoundError(
            "generate",
            f"planned {total_planned} generation calls exceeds --max-calls budget "
            f"({args.max_calls}) — refusing to exceed the hard budget counter (matrix row 15)",
        )

    calls_made = 0
    raws = []
    for arm in arms:
        guide_path = _abs(arm["guide"])
        prompt_file = prompts_dir / f"{arm['name']}_prompt.md"
        refs = [str(guide_path)] + handle_refs + extra_refs
        for i in range(1, arm["count"] + 1):
            if calls_made + 1 > args.max_calls:
                raise RoundError(
                    "generate",
                    f"generation call #{calls_made + 1} would exceed --max-calls budget "
                    f"({args.max_calls}) — refusing to exceed (matrix row 15)",
                )
            out_path = raws_dir / f"{arm['name']}_s{i}.png"
            cmd = [PY, str(subgen), "--provider", args.provider, "--out", str(out_path)]
            if prompt_file.exists():
                cmd += ["--prompt-file", str(prompt_file)]
            else:
                cmd += ["--prompt", f"round {round_dir.name} arm {arm['name']} sample {i}"]
            cmd += ["-i", *refs]
            _run(cmd, log, "generate")
            calls_made += 1
            if not _valid_image(out_path):
                raise RoundError(
                    "generate",
                    f"subgen output for {arm['name']} sample {i} is not a valid image: {out_path}",
                )
            log.log("generate", f"verified raw #{calls_made}: {out_path}")
            raws.append({"arm": arm["name"], "sample": f"s{i}", "raw_path": str(out_path)})

    log.log("generate", f"GENERATE DONE — {calls_made} calls made (budget {args.max_calls})")
    return raws


# ---------------------------------------------------------------------------
# 3. GATES
# ---------------------------------------------------------------------------

def _resolve_panel_svg(geom_dir: Path, panel: str) -> Path | None:
    """gates.py defaults --svg to <geom>/<panel>.svg, but some geometry dirs
    (e.g. tasks/marriott-hospital/geometry/v3) name the traced panel file
    <panel>-panel.svg instead. Prefer <panel>.svg; fall back to <panel>-panel.svg
    so dual_geometry isn't silently skipped. Returns None if neither exists
    (gates.py itself will report dual_geometry.available=False)."""
    direct = geom_dir / f"{panel}.svg"
    if direct.exists():
        return direct
    fallback = geom_dir / f"{panel}-panel.svg"
    if fallback.exists():
        return fallback
    return None


def run_gates(args, round_dir: Path, raws: list, log: RunLog) -> list:
    gates_dir = round_dir / "gates"
    gates_dir.mkdir(parents=True, exist_ok=True)

    gates_py = SCRIPTS / "gates.py"
    door_fill_gate = SCRIPTS / "door_fill_gate.py"
    emblem_gate = SCRIPTS / "emblem_gate.py"
    content_gate = SCRIPTS / "content_gate.py"
    for tool, name in [(gates_py, "gates.py"), (door_fill_gate, "door_fill_gate.py"),
                        (emblem_gate, "emblem_gate.py"), (content_gate, "content_gate.py")]:
        _require_tool(tool, name)

    geom_dir = _abs(args.geom)
    panel_svg = _resolve_panel_svg(geom_dir, args.panel)

    results = []
    for raw in raws:
        raw_path = Path(raw["raw_path"])
        stem = f"{raw['arm']}_{raw['sample']}"
        row = dict(raw)

        # gates.py: registered resize + dual geometry bundle (matrix row 1).
        # Use a per-raw output stem so bundles, overlays, and dual-metric JSON
        # files cannot be overwritten by the next raw in the same gates_dir.
        gates_output_stem = f"{stem}-{args.panel}-finish"
        gates_cmd = [PY, str(gates_py), "--cand", str(raw_path), "--geom", str(geom_dir),
                     "--panel", args.panel, "--outdir", str(gates_dir), "--stage", "finish",
                     "--output-stem", gates_output_stem]
        if panel_svg is not None:
            gates_cmd += ["--svg", str(panel_svg)]
        proc = _run(gates_cmd, log, "gates", check=False)
        try:
            bundle = json.loads(proc.stdout) if proc.stdout.strip() else {}
        except json.JSONDecodeError:
            bundle = {}
        row["gates_overall_verdict"] = bundle.get("overall_verdict")

        row["gates_bundle_path"] = bundle.get("bundle_path")
        overlay_path = bundle.get("overlay_path")

        # door_fill_gate.py — overlay is the required non-null field for the row
        door_overlay = gates_dir / f"{stem}-door-overlay.png"
        proc = _run(
            [PY, str(door_fill_gate), "--image", str(raw_path), "--geom", str(_abs(args.geom)),
             "--panel", args.panel, "--overlay", str(door_overlay)],
            log, "gates", check=False,
        )
        try:
            door_result = json.loads(proc.stdout) if proc.stdout.strip() else {}
        except json.JSONDecodeError:
            door_result = {}
        row["door_fill_verdict"] = door_result.get("verdict")
        row["door_fill"] = door_result.get("door_fill")

        if not overlay_path:
            overlay_path = str(door_overlay) if door_overlay.exists() else None
        row["overlay_path"] = overlay_path
        if not row["overlay_path"]:
            raise RoundError(
                "gates",
                f"no overlay produced for {stem} — overlay_path is a REQUIRED non-null "
                f"field for every results.json row (matrix row 1)",
            )

        # emblem_gate.py — WARN + skip if no API key available
        if args.callouts:
            emblem_json = gates_dir / f"{stem}-emblem.json"
            proc = _run(
                [PY, str(emblem_gate), "--image", str(raw_path), "--callouts", str(_abs(args.callouts))],
                log, "gates", check=False,
            )
            stderr_l = (proc.stderr or "").lower()
            if "key" in stderr_l and proc.returncode != 0:
                log.log("gates", f"emblem_gate WARN (no key) for {stem}: {proc.stderr.strip()[:200]}")
                row["emblem_pass"] = None
            else:
                try:
                    emblem_out = json.loads(proc.stdout) if proc.stdout.strip() else {}
                except json.JSONDecodeError:
                    emblem_out = {}
                emblem_json.write_text(json.dumps(emblem_out, indent=2))
                row["emblem_pass"] = emblem_out.get("pass")
                row["emblem_json_path"] = str(emblem_json)
        else:
            row["emblem_pass"] = None

        # content_gate.py — flap/void content checks (matrix rows 10, 11).
        # Explicit --overlay so it lands in gates_dir, not beside the raw
        # (content_gate.py defaults --overlay to raws/<stem>-content-gate-overlay.png).
        content_overlay = gates_dir / f"{stem}-content-gate-overlay.png"
        proc = _run(
            [PY, str(content_gate), "--image", str(raw_path), "--geom", str(_abs(args.geom)),
             "--overlay", str(content_overlay)],
            log, "gates", check=False,
        )
        try:
            content_out = json.loads(proc.stdout) if proc.stdout.strip() else {}
        except json.JSONDecodeError:
            content_out = {}
        row["content_verdict"] = content_out.get("verdict")

        results.append(row)

    results_path = round_dir / f"{round_dir.name}-results.json"
    results_path.write_text(json.dumps(results, indent=2) + "\n")
    log.log("gates", f"GATES DONE — results.json written: {results_path} ({len(results)} rows)")
    return results


# ---------------------------------------------------------------------------
# 4. BOARDS
# ---------------------------------------------------------------------------

def run_boards(args, round_dir: Path, log: RunLog) -> None:
    overlay_board = SCRIPTS / "overlay_board.py"
    inputs_board = SCRIPTS / "inputs_board.py"
    _require_tool(overlay_board, "overlay_board.py")
    _require_tool(inputs_board, "inputs_board.py")

    raws_glob = str(round_dir / "raws" / "*.png")
    board_out = round_dir / f"{round_dir.name}-overlay-board.jpg"
    _run(
        [PY, str(overlay_board), "--raws", raws_glob, "--geom", str(_abs(args.geom)),
         "--out", str(board_out)],
        log, "boards",
    )
    log.log("boards", "overlay_board.py complete")

    _run([PY, str(inputs_board), str(round_dir)], log, "boards")
    log.log("boards", "inputs_board.py complete")


# ---------------------------------------------------------------------------
# 5. VERIFY
# ---------------------------------------------------------------------------

def run_verify(round_dir: Path, task_name: str, log: RunLog) -> None:
    verify_tool = SCRIPTS / "verify_round_artifacts.py"
    _require_tool(verify_tool, "verify_round_artifacts.py")
    proc = _run(
        [PY, str(verify_tool), str(round_dir), "--task", task_name],
        log, "verify", check=False,
    )
    if proc.returncode != 0:
        raise RoundError(
            "verify",
            f"verify_round_artifacts.py FAILED (exit {proc.returncode}) — round artifact "
            f"contract not satisfied (matrix row 14): {proc.stdout.strip()[:2000]}",
        )
    log.log("verify", "VERIFY PASS")


# ---------------------------------------------------------------------------
# 6. REPAIR (optional)
# ---------------------------------------------------------------------------

def run_repair(args, round_dir: Path, log: RunLog) -> None:
    if not args.repair:
        return
    repair_tool = _abs(args.repair)
    _require_tool(repair_tool, str(args.repair))
    cmd = [PY, str(repair_tool)] + (args.repair_args or [])
    _run(cmd, log, "repair")
    log.log("repair", "repair step complete — running AUTOMATIC post-restyle emblem_gate re-run")

    emblem_gate = SCRIPTS / "emblem_gate.py"
    _require_tool(emblem_gate, "emblem_gate.py")
    if not args.callouts:
        log.log("repair", "no --callouts configured — cannot re-run emblem_gate; matrix row 12 unmet")
        raise RoundError("repair", "post-restyle emblem_gate re-run requires --callouts")

    raws_dir = round_dir / "raws"
    gates_dir = round_dir / "gates"
    for raw_path in sorted(raws_dir.glob("*.png")):
        stem = raw_path.stem
        proc = _run(
            [PY, str(emblem_gate), "--image", str(raw_path), "--callouts", str(_abs(args.callouts))],
            log, "repair", check=False,
        )
        try:
            emblem_out = json.loads(proc.stdout) if proc.stdout.strip() else {}
        except json.JSONDecodeError:
            emblem_out = {}
        (gates_dir / f"{stem}-emblem-postrepair.json").write_text(json.dumps(emblem_out, indent=2))
    log.log("repair", "post-restyle emblem_gate re-run complete for all raws")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--round-dir", required=True, help="round directory, e.g. tasks/<task>/round3")
    ap.add_argument("--guides", nargs="*", default=[], help="guide image paths needing .approved markers")
    ap.add_argument("--callouts", default=None, help="feature-callouts YAML for callouts_lint + emblem_gate")
    ap.add_argument("--handle", default=None, help="style-handle.yaml to validate + pull refs from")
    ap.add_argument("--arms", nargs="+", required=True, help='arm spec(s) "name:guide:count"')
    ap.add_argument("--geom", required=True, help="geometry dir for gates.py/door_fill_gate.py/content_gate.py")
    ap.add_argument("--panel", required=True, help="panel name inside --geom")
    ap.add_argument("--provider", default="openai", choices=["openai", "nano"])
    ap.add_argument("--max-calls", type=int, default=14, help="hard budget cap on subgen calls")
    ap.add_argument("--extra-refs", nargs="*", default=[], help="additional reference images for every arm")
    ap.add_argument("--repair", default=None, help="optional repair tool to run after gates+boards+verify")
    ap.add_argument("--repair-args", nargs="*", default=[], help="args passed through to --repair tool")
    ap.add_argument("--task", default=None, help="task name for REVIEW/<task>/<round> copy (default: round-dir's parent name)")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    round_dir = _abs(args.round_dir)
    round_dir.mkdir(parents=True, exist_ok=True)
    task_name = args.task or round_dir.parent.name

    log = RunLog(round_dir / "runner.log")
    log.log("start", f"round_runner.py starting for {round_dir}")
    try:
        run_preflight(args, log)
        raws = run_generate(args, round_dir, log)
        run_gates(args, round_dir, raws, log)
        run_boards(args, round_dir, log)
        run_verify(round_dir, task_name, log)
        run_repair(args, round_dir, log)
    except RoundError as exc:
        log.log(exc.step, f"HARD FAIL: {exc.message}")
        print(f"ROUND FAILED at step '{exc.step}': {exc.message}", file=sys.stderr)
        log.close()
        return 1
    except Exception as exc:  # pragma: no cover - unexpected errors still logged
        log.log("error", f"unexpected error: {exc}")
        print(f"ROUND FAILED (unexpected): {exc}", file=sys.stderr)
        log.close()
        return 1

    log.log("done", "ROUND COMPLETE")
    log.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
