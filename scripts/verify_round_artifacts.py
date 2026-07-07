#!/usr/bin/env python3
"""verify_round_artifacts.py — asserts the round artifact contract (matrix row 14).

Given a round directory, checks that ALL of the following hold:
  - raws/ exists and is non-empty
  - every raw in raws/ has a corresponding overlay somewhere under gates/
    (filename stem match: <stem>*-overlay.png)
  - <round>-results.json exists, has exactly one row per raw, and every row's
    overlay_path is present, non-null, and points at a file that exists
  - both boards exist: overlay_board (<round>-overlay-board.* or
    OVERLAY-<round>.*) and inputs_board (INPUTS-<round>.*)
  - prompts/ and guides/ directories exist and are non-empty
  - REVIEW/<task>/<round>/ has copies of the two boards that byte-match the
    round-dir originals

Usable as a library (verify(round_dir, task) -> list[str] of missing items,
empty list == PASS) or as a standalone CLI.

CLI:
  python3 scripts/verify_round_artifacts.py <round_dir> [--task NAME]

Exit 0 on PASS; exit 2 with a missing-item list on stdout (JSON) on FAIL.
"""
from __future__ import annotations

import argparse
import filecmp
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BOARD_GLOBS_OVERLAY = ["*-overlay-board.*", "OVERLAY-*.*", "*-board.*"]
BOARD_GLOBS_INPUTS = ["INPUTS-*.*"]


def _abs(path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def _find_first(round_dir: Path, patterns: list) -> Path | None:
    for pat in patterns:
        matches = sorted(round_dir.glob(pat))
        if matches:
            return matches[0]
    return None


def verify(round_dir, task: str | None = None, review_root=None) -> list:
    """Returns a list of missing-item strings. Empty list == round contract satisfied.

    review_root defaults to <repo-root>/REVIEW; overridable (e.g. by tests)."""
    round_dir = _abs(round_dir)
    review_root = Path(review_root) if review_root is not None else (ROOT / "REVIEW")
    missing = []

    raws_dir = round_dir / "raws"
    if not raws_dir.is_dir():
        missing.append(f"raws/ directory missing: {raws_dir}")
        raws = []
    else:
        raws = sorted(p for p in raws_dir.iterdir() if p.is_file())
        if not raws:
            missing.append(f"raws/ is empty: {raws_dir}")

    gates_dir = round_dir / "gates"
    if not gates_dir.is_dir():
        missing.append(f"gates/ directory missing: {gates_dir}")

    for raw in raws:
        stem = raw.stem
        overlay_matches = list(gates_dir.glob(f"{stem}*overlay*.png")) if gates_dir.is_dir() else []
        if not overlay_matches:
            missing.append(f"no overlay found for raw '{raw.name}' under {gates_dir}")

    prompts_dir = round_dir / "prompts"
    if not prompts_dir.is_dir() or not any(prompts_dir.iterdir()):
        missing.append(f"prompts/ missing or empty: {prompts_dir}")

    guides_dir = round_dir / "guides"
    if not guides_dir.is_dir() or not any(guides_dir.iterdir()):
        missing.append(f"guides/ missing or empty: {guides_dir}")

    results_path = round_dir / f"{round_dir.name}-results.json"
    results_rows = []
    if not results_path.exists():
        missing.append(f"results.json missing: {results_path}")
    else:
        try:
            results_rows = json.loads(results_path.read_text())
        except json.JSONDecodeError as exc:
            missing.append(f"results.json is not valid JSON: {results_path} ({exc})")
            results_rows = []

        if isinstance(results_rows, list):
            if len(results_rows) != len(raws):
                missing.append(
                    f"results.json row count ({len(results_rows)}) != raws count ({len(raws)})"
                )
            for i, row in enumerate(results_rows):
                overlay_path = row.get("overlay_path") if isinstance(row, dict) else None
                if not overlay_path:
                    missing.append(f"results.json row {i} has null/missing overlay_path")
                elif not Path(overlay_path).exists():
                    missing.append(f"results.json row {i} overlay_path does not exist: {overlay_path}")
        else:
            missing.append(f"results.json is not a list: {results_path}")

    overlay_board = _find_first(round_dir, BOARD_GLOBS_OVERLAY)
    if overlay_board is None:
        missing.append(f"overlay board missing under {round_dir} (expected *-overlay-board.* / OVERLAY-*.* / *-board.*)")

    inputs_board = _find_first(round_dir, BOARD_GLOBS_INPUTS)
    if inputs_board is None:
        missing.append(f"inputs board missing under {round_dir} (expected INPUTS-*.*)")

    task_name = task or round_dir.parent.name
    review_dir = review_root / task_name / round_dir.name
    if not review_dir.is_dir():
        missing.append(f"REVIEW copy dir missing: {review_dir}")
    else:
        for board, label in [(overlay_board, "overlay board"), (inputs_board, "inputs board")]:
            if board is None:
                continue
            review_copy = review_dir / board.name
            if not review_copy.exists():
                missing.append(f"REVIEW copy of {label} missing: {review_copy}")
            elif not filecmp.cmp(board, review_copy, shallow=False):
                missing.append(f"REVIEW copy of {label} does not byte-match original: {review_copy}")

    return missing


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("round_dir")
    ap.add_argument("--task", default=None, help="task name for REVIEW/<task>/<round> lookup")
    ap.add_argument("--review-root", default=None, help="override REVIEW root (default: <repo-root>/REVIEW)")
    args = ap.parse_args(argv)

    missing = verify(args.round_dir, args.task, args.review_root)
    if missing:
        print(json.dumps({"pass": False, "missing": missing}, indent=2))
        return 2

    print(json.dumps({"pass": True, "missing": []}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
