#!/usr/bin/env python3
"""verdict_form.py — generate a structured review-verdict form for a gen round.

PROCESS-V3 law 8 / stage H: every review round ships ONE short form instead of
free prose (REVIEW/marriott-hospital/FEEDBACK.md's old style). Axis verdicts +
a retake label + optional forced-choice decisions + optional A/B + must-preserve
/ may-change / free-text. The user edits the answers INLINE in the generated
markdown file; scripts/verdict_apply.py parses the filled form back to JSON.

CLI:
  python3 scripts/verdict_form.py --round r17 --candidates a.png b.png --out REVIEW/task \
      [--gate rough|cleanup|color|prepress] \
      [--decision "door: clean|ornate|noleafcross"] [--decision "stab: lighthouse|pilaster"] \
      [--ab "is the door canopy too dense?"]

Writes <out>/VERDICT-<round>.md and returns its path (also printed).

Deps: stdlib only.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

AXES = [
    ("style_family", "Style family"),
    ("geometry", "Geometry/template"),
    ("motifs", "Motifs/small elements (crop ids)"),
    ("palette_finish", "Palette/finish/texture"),
    ("prepress", "Text/logo/prepress"),
]

RETAKE_LABELS = [
    "RESET_STYLE",
    "ROUGH_RETAKE",
    "CLEANUP_RETAKE",
    "COLOR_RETAKE",
    "PREPRESS_RETAKE",
]

GATES = ["rough", "cleanup", "color", "prepress"]

NEXT_ACTIONS = ["accept", "local repair", "phase retake", "reset"]


def _candidate_link(path: str) -> str:
    """Markdown link with the FILENAME as link text (user rule: link text = filename)."""
    name = os.path.basename(path.rstrip("/"))
    return f"- [{name}]({path})"


def build_form(round_name: str, candidates: list[str], gate: str | None = None,
               decisions: list[str] | None = None, ab: str | None = None) -> str:
    """Render the verdict-form markdown for one review round. Pure string build —
    no I/O — so tests can generate + fill + parse without touching disk twice."""
    decisions = decisions or []
    lines: list[str] = []

    lines.append(f"# Verdict — {round_name}")
    lines.append("")
    lines.append(f"Round: {round_name}")
    lines.append(f"Gate: {gate or '(unspecified)'}")
    lines.append("")
    lines.append("Answer inline — a word per line is enough. Anything not marked is")
    lines.append("treated as \"approve\".")
    lines.append("")
    lines.append("## Candidates")
    for c in candidates:
        lines.append(_candidate_link(c))
    lines.append("")

    lines.append("## Axis verdicts")
    for key, label in AXES:
        lines.append(f"- {label} [{key}]: approve / retake")
        lines.append("  note:")
    lines.append("")

    lines.append("## Retake label (if any axis is retake)")
    lines.append(f"one of: {' / '.join(RETAKE_LABELS)}")
    lines.append("label:")
    lines.append("")

    if decisions:
        lines.append("## Decisions")
        for d in decisions:
            slot, _, opts = d.partition(":")
            slot = slot.strip()
            opts = opts.strip()
            lines.append(f"- {slot} [{opts}]: ")
        lines.append("")

    if ab:
        lines.append("## A/B")
        lines.append(f"question: {ab}")
        lines.append("A / B is closer because:")
        lines.append("")

    lines.append("## Overall next action")
    lines.append(f"one of: {' / '.join(NEXT_ACTIONS)}")
    lines.append("next_action:")
    lines.append("")

    lines.append("## Must preserve")
    lines.append("")
    lines.append("## May change")
    lines.append("")
    lines.append("## Free text (optional)")
    lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--round", required=True, dest="round_name", help="round name, e.g. r17")
    ap.add_argument("--candidates", nargs="+", required=True, help="candidate image paths")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--gate", choices=GATES, default=None)
    ap.add_argument("--decision", action="append", default=[],
                     help='forced-choice slot, e.g. "door: clean|ornate|noleafcross" '
                          "(repeatable)")
    ap.add_argument("--ab", default=None, help="optional A/B forced-choice question")
    a = ap.parse_args()

    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"VERDICT-{a.round_name}.md"

    text = build_form(a.round_name, a.candidates, gate=a.gate,
                       decisions=a.decision, ab=a.ab)
    out_path.write_text(text)
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
