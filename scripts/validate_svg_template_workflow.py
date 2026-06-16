#!/usr/bin/env python3
"""Validate that SVG-template illustration workflow docs stay agent-usable."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    ".codex/skills/svg-template-illustration/SKILL.md",
    ".codex/skills/svg-template-review-judge/SKILL.md",
    "docs/svg-template-illustration-workflow.md",
    "docs/review-judge-checklist.md",
    "tasks/_template/session-brief.md",
    "tasks/_template/review-judge.md",
    "tasks/_template/template-manifest.json",
    "tasks/_template/prompts/prompt-v1-contour-first.md",
    "scripts/scaffold_template_task.py",
]

REQUIRED_SNIPPETS = {
    ".codex/skills/svg-template-illustration/SKILL.md": [
        "Do not make a generic rectangular illustration",
        "Reset Vs Patch",
        "visual judge",
        "Done Means",
    ],
    ".codex/skills/svg-template-review-judge/SKILL.md": [
        "Inspect the actual images",
        "ACCEPT | LOCAL PATCH | PROMPT RESTART | BLOCKED",
        "metadata",
        "cutout",
    ],
    "docs/svg-template-illustration-workflow.md": [
        "Source Contract",
        "Parse The SVG Before Prompting",
        "Plan Safe Pockets",
        "template-manifest.json",
        "Reset Or Patch Deliberately",
    ],
    "tasks/_template/template-manifest.json": [
        "outer_contours",
        "internal_cutouts",
        "keep_clear_zones",
        "safe_pockets",
    ],
    "docs/review-judge-checklist.md": [
        "Geometry Gate",
        "Cutout Gate",
        "Style Gate",
        "Verdicts",
    ],
    "AGENTS.md": [
        ".codex/skills/svg-template-illustration/SKILL.md",
        ".codex/skills/svg-template-review-judge/SKILL.md",
    ],
}


def check(condition: bool, label: str, failures: list[str]) -> None:
    mark = "OK" if condition else "FAIL"
    print(f"[{mark}] {label}")
    if not condition:
        failures.append(label)


def command_ok(command: list[str]) -> bool:
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        if isinstance(exc, subprocess.CalledProcessError):
            print(exc.stdout)
            print(exc.stderr, file=sys.stderr)
        return False
    return "would create" in completed.stdout or "would write" in completed.stdout


def main() -> int:
    failures: list[str] = []

    for rel in REQUIRED_FILES:
        check((ROOT / rel).is_file(), f"file exists: {rel}", failures)

    for rel, snippets in REQUIRED_SNIPPETS.items():
        path = ROOT / rel
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        for snippet in snippets:
            check(snippet in text, f"{rel} contains {snippet!r}", failures)

    check(
        command_ok(
            [
                "python3",
                "scripts/scaffold_template_task.py",
                "validator-smoke",
                "--svg",
                "assets/templates/two-panel-template.svg",
                "--refs",
                "assets/reference-images/castle-style-reference.png",
                "--dry-run",
            ]
        ),
        "task scaffold dry-run works",
        failures,
    )

    if failures:
        print("\nWorkflow validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nSVG-template workflow validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
