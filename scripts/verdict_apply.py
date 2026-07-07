#!/usr/bin/env python3
"""verdict_apply.py — parse a filled VERDICT-*.md into JSON, optionally patch the bible.

Companion to scripts/verdict_form.py (PROCESS-V3 law 8 / stage H). Reads a
verdict form the user has edited INLINE and turns it into a machine-readable
verdict record: axis verdicts, retake label, decisions, A/B pick, overall next
action, must-preserve / may-change / free-text. Parsing is TOLERANT — a
missing axis answer defaults to "approve" (nothing marked = fine), a missing
decision is simply absent from the output (never guessed).

CLI:
  python3 scripts/verdict_apply.py REVIEW/task/VERDICT-r17.md [--bible bible.yaml]

Prints the verdict JSON to stdout. Exit 2 if next_action cannot be determined
(garbage next_action text and no axis data to infer accept/retake from).

If --bible is given and any axis verdict is "retake" with a non-empty note, a
single comment line is APPENDED to the end of the bible yaml:
  # VERDICT-PATCH (<round>, <axis>): <note>
This is purely additive — existing bible lines are never touched; the style
lane owns real field edits.

Deps: stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verdict_form import AXES, NEXT_ACTIONS, RETAKE_LABELS  # noqa: E402

AXIS_KEYS = [key for key, _ in AXES]

_AXIS_LINE_RE = re.compile(r"^-\s*.*\[(?P<key>[a-z_]+)\]\s*:\s*(?P<val>.*)$")
_NOTE_LINE_RE = re.compile(r"^\s*note:\s*(?P<val>.*)$")
_DECISION_LINE_RE = re.compile(r"^-\s*(?P<slot>[^\[]+?)\s*\[(?P<opts>[^\]]*)\]\s*:\s*(?P<val>.*)$")
_LABEL_LINE_RE = re.compile(r"^label:\s*(?P<val>.*)$")
_NEXT_ACTION_LINE_RE = re.compile(r"^next_action:\s*(?P<val>.*)$")
_AB_QUESTION_RE = re.compile(r"^question:\s*(?P<val>.*)$")
_AB_ANSWER_RE = re.compile(r"^A\s*/\s*B is closer because:\s*(?P<val>.*)$")
_ROUND_LINE_RE = re.compile(r"^Round:\s*(?P<val>.*)$")
_GATE_LINE_RE = re.compile(r"^Gate:\s*(?P<val>.*)$")
_CANDIDATE_LINE_RE = re.compile(r"^-\s*\[(?P<name>[^\]]+)\]\((?P<path>[^)]+)\)\s*$")


def _clean(val: str) -> str:
    return val.strip()


def _section_header(line: str) -> str | None:
    if line.startswith("## "):
        return line[3:].strip()
    return None


def parse_form(text: str) -> dict:
    """Tolerant parse of a filled (or unfilled) verdict form -> verdict dict."""
    lines = text.splitlines()

    round_name = None
    gate = None
    candidates: list[str] = []
    axes: dict[str, dict] = {key: {"verdict": "approve", "note": ""} for key in AXIS_KEYS}
    retake_label = None
    decisions: dict[str, str] = {}
    ab: dict | None = None
    next_action_raw = None
    must_preserve: list[str] = []
    may_change: list[str] = []
    free_text: list[str] = []

    section = None
    pending_axis_key = None
    ab_question = None

    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()

        hdr = _section_header(line)
        if hdr is not None:
            section = hdr
            pending_axis_key = None
            continue

        if line.startswith("Round:"):
            m = _ROUND_LINE_RE.match(line)
            if m:
                round_name = _clean(m.group("val")) or None
            continue
        if line.startswith("Gate:"):
            m = _GATE_LINE_RE.match(line)
            if m:
                g = _clean(m.group("val"))
                gate = g if g and g != "(unspecified)" else None
            continue

        if section == "Candidates":
            m = _CANDIDATE_LINE_RE.match(stripped)
            if m:
                candidates.append(m.group("path"))
            continue

        if section == "Axis verdicts":
            m = _AXIS_LINE_RE.match(stripped)
            if m:
                key = m.group("key")
                val = _clean(m.group("val"))
                if key in axes:
                    verdict = _axis_verdict_from_value(val)
                    axes[key]["verdict"] = verdict
                    pending_axis_key = key
                continue
            m = _NOTE_LINE_RE.match(line)
            if m and pending_axis_key:
                axes[pending_axis_key]["note"] = _clean(m.group("val"))
                continue
            continue

        if section and section.startswith("Retake label"):
            m = _LABEL_LINE_RE.match(stripped)
            if m:
                val = _clean(m.group("val"))
                retake_label = val if val in RETAKE_LABELS else (val or None)
            continue

        if section == "Decisions":
            m = _DECISION_LINE_RE.match(stripped)
            if m:
                slot = _clean(m.group("slot"))
                val = _clean(m.group("val"))
                if val:
                    decisions[slot] = val
            continue

        if section == "A/B":
            m = _AB_QUESTION_RE.match(stripped)
            if m:
                ab_question = _clean(m.group("val"))
                continue
            m = _AB_ANSWER_RE.match(stripped)
            if m:
                answer_raw = _clean(m.group("val"))
                pick = _ab_pick_from_value(answer_raw)
                ab = {"question": ab_question, "pick": pick, "reason": answer_raw}
            continue

        if section == "Overall next action":
            m = _NEXT_ACTION_LINE_RE.match(stripped)
            if m:
                next_action_raw = _clean(m.group("val"))
            continue

        if section == "Must preserve":
            if stripped:
                must_preserve.append(stripped)
            continue

        if section == "May change":
            if stripped:
                may_change.append(stripped)
            continue

        if section and section.startswith("Free text"):
            if stripped:
                free_text.append(stripped)
            continue

    next_action = _resolve_next_action(next_action_raw, axes, retake_label)
    if next_action is None:
        raise ValueError(
            f"next_action cannot be determined (raw={next_action_raw!r})"
        )

    return {
        "round": round_name,
        "gate": gate,
        "candidates": candidates,
        "axes": axes,
        "retake_label": retake_label,
        "decisions": decisions,
        "ab": ab,
        "next_action": next_action,
        "must_preserve": must_preserve,
        "may_change": may_change,
        "free_text": "\n".join(free_text),
    }


def _axis_verdict_from_value(val: str) -> str:
    """Missing/unedited ('approve / retake') or blank -> approve (tolerant default)."""
    v = val.lower()
    if "retake" in v and "approve" not in v:
        return "retake"
    if v.strip() == "retake":
        return "retake"
    return "approve"


def _ab_pick_from_value(val: str) -> str | None:
    v = val.strip()
    if not v:
        return None
    # accept "A", "A, ...", "A because ..." etc — first token's leading letter
    first = v[0].upper()
    if first in ("A", "B"):
        return first
    return None


def _resolve_next_action(raw: str | None, axes: dict, retake_label: str | None) -> str | None:
    raw = (raw or "").strip()
    if raw:
        for action in NEXT_ACTIONS:
            if raw.lower() == action.lower():
                return action
        # not a recognized action string -> unresolved
        return None
    # blank: infer from axis verdicts / retake label
    if retake_label == "RESET_STYLE":
        return "reset"
    any_retake = any(a["verdict"] == "retake" for a in axes.values())
    if any_retake:
        return "phase retake"
    return "accept"


def apply_bible_patch(bible_path: Path, verdict: dict) -> bool:
    """Append additive VERDICT-PATCH comment lines for every retake axis with a
    note. Never touches existing lines. Returns True if the file was written."""
    retake_notes = [
        (key, a["note"]) for key, a in verdict["axes"].items()
        if a["verdict"] == "retake" and a["note"]
    ]
    if not retake_notes:
        return False

    original = bible_path.read_text() if bible_path.exists() else ""
    round_name = verdict.get("round") or "unknown-round"
    patch_lines = [
        f"# VERDICT-PATCH ({round_name}, {key}): {note}"
        for key, note in retake_notes
    ]
    suffix = "\n".join(patch_lines) + "\n"
    if original and not original.endswith("\n"):
        original += "\n"
    bible_path.write_text(original + suffix)
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("form", help="path to a filled VERDICT-*.md")
    ap.add_argument("--bible", default=None, help="style-bible yaml to additively patch")
    a = ap.parse_args()

    form_path = Path(a.form)
    text = form_path.read_text()

    try:
        verdict = parse_form(text)
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2

    if a.bible:
        apply_bible_patch(Path(a.bible), verdict)

    print(json.dumps(verdict, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
