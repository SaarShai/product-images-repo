#!/usr/bin/env python3
"""Validate that SVG-template illustration workflow docs stay agent-usable."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    ".codex/skills/reference-style-packet/SKILL.md",
    ".codex/skills/skyline-template-illustration/SKILL.md",
    ".codex/skills/svg-template-style-agent/SKILL.md",
    ".codex/skills/svg-template-style-agent/drift_probes.json",
    ".codex/skills/svg-template-illustration/SKILL.md",
    ".codex/skills/svg-template-review-judge/SKILL.md",
    "assets/skyline/city-skyline template.svg",
    "assets/skyline/example of DO - specific elements (fairies, birds) not cropped.png",
    "assets/skyline/example of DON'T - specific elements (fairies, birds) cropped.png",
    "assets/skyline/door panel example - bridge inside door flaps area.png",
    "assets/skyline/example - bridge runs through panels + top contour tracing buildings shape.png",
    "assets/skyline/README.md",
    "docs/svg-template-illustration-workflow.md",
    "docs/skyline-template-illustration-workflow.md",
    "docs/review-judge-checklist.md",
    "tasks/_template/session-brief.md",
    "tasks/_template/skyline-example-feedback.md",
    "tasks/_template/review-judge.md",
    "tasks/_template/template-manifest.json",
    "tasks/_template/prompts/prompt-v1-contour-first.md",
    "scripts/build_reference_style_packet.py",
    "scripts/scaffold_template_task.py",
]

REQUIRED_SNIPPETS = {
    ".codex/skills/svg-template-illustration/SKILL.md": [
        "Do not make a generic rectangular illustration",
        "visual style packet",
        "Any subagent assigned to adapt approved geometry to style",
        "Reset Vs Patch",
        "visual judge",
        "Done Means",
    ],
    ".codex/skills/reference-style-packet/SKILL.md": [
        "build_reference_style_packet.py",
        "style-agent prompt",
        "Style agents must receive images",
    ],
    ".codex/skills/svg-template-style-agent/SKILL.md": [
        "## Job Boundary",
        "element sheets",
        "Style agents do not",
        "ALWAYS use this rule for geometry-to-style adaptation",
        "prompt-only attempt is not",
        "approved geometry image only as a composition/negative-space map",
        "REFERENCE-MATCH",
    ],
    ".codex/skills/svg-template-style-agent/drift_probes.json": [
        "geometry-approved-style-adaptation-requires-whole-panel-redraw",
        "locked[-_ ]geometry",
        "whole[-_ ]panel redraw",
    ],
    ".codex/skills/skyline-template-illustration/SKILL.md": [
        "assets/skyline/city-skyline template.svg",
        "one large central door panel",
        "orange dashed arch",
        "follow the general",
        "vision-capable judge",
        "proof-before-spend scout gate",
        "faint lookalike placement boards",
        "Template-Lock Rule",
        "generated guide lines are off",
        "never ask the image model to think about",
        "Prompt boundary preflight",
        "Forbidden prompt concepts include",
        "Those constraints belong to the deterministic overlay/export step",
        "sky/background default is white",
        "visual-premise approval",
        "Ask Early",
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
        "Build The Reference Style Packet",
        "Split Style Agents From Geometry Agents",
        "Hard routing rule for geometry-approved style fixes",
        "template-manifest.json",
        "Reset Or Patch Deliberately",
    ],
    "docs/skyline-template-illustration-workflow.md": [
        "human-readable source of truth",
        "Default Template Roles",
        "Composition Rules",
        "Flexibility Rule",
        "Saloon-Door Arch Rule",
        "Top-Contour Rule",
        "Template-Lock Rule",
        "never ask the image model to think about",
        "Prompt boundary preflight",
        "Forbidden prompt concepts include",
        "Those constraints belong to deterministic overlay/export",
        "Proof-Before-Spend Scout Gate",
        "Dimension Repair Gate",
        "Skyline Composition Plan",
        "visual-premise approval",
        "Learning Loop",
    ],
    "assets/skyline/README.md": [
        "Default guide roles",
        "Example Roles",
        "counterexample",
        "top contour adaptation",
        "Keep the default sky",
    ],
    "tasks/_template/skyline-example-feedback.md": [
        "Load-Bearing Choices",
        "Checkpoint Approval Status",
        "Visual premise",
        "Proof-Before-Spend Scout Notes",
        "Dimension Repair Notes",
        "Decision unlocked",
        "User Feedback Log",
        "rule learned",
        "Durable Lessons To Consider Promoting",
    ],
    "tasks/_template/template-manifest.json": [
        "outer_contours",
        "internal_cutouts",
        "keep_clear_zones",
        "safe_pockets",
    ],
    "tasks/_template/session-brief.md": [
        "attachment-aware whole-panel redraw",
        "approved geometry image only as a composition/negative-space map",
        "Do not use locked-geometry local restyle",
    ],
    "tasks/_template/review-judge.md": [
        "Geometry-Approved Style Rule",
        "approved geometry as a composition map only",
        "locked-geometry local restyle",
    ],
    "docs/review-judge-checklist.md": [
        "Geometry Gate",
        "Cutout Gate",
        "Style Gate",
        "Reject local `locked-geometry` restyle outputs",
        "style-packet",
        "Verdicts",
    ],
    "AGENTS.md": [
        ".codex/skills/svg-template-illustration/SKILL.md",
        ".codex/skills/skyline-template-illustration/SKILL.md",
        ".codex/skills/svg-template-review-judge/SKILL.md",
        "Do not substitute locked-geometry scripts",
    ],
}


def check(condition: bool, label: str, failures: list[str]) -> None:
    mark = "OK" if condition else "FAIL"
    print(f"[{mark}] {label}")
    if not condition:
        failures.append(label)


def command_ok(command: list[str], expected_stdout: str | None = None) -> bool:
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
    if expected_stdout is not None:
        return expected_stdout in completed.stdout
    return "would create" in completed.stdout or "would write" in completed.stdout


def space_socket_geometry_regression_ok() -> bool:
    """Catch the Screenery socket/polyline geometry regressions from 2026-06-17."""
    script = """
import sys
from pathlib import Path
sys.path.insert(0, 'tasks/space-svg-exports-batch/scripts')
from create_checkpoint_candidates import classify_svg
_, records, _, _ = classify_svg(Path('tasks/space-svg-exports-batch/source/np01-back-bottom.svg'))
by_index = {record.index: record for record in records if record.source_type == 'path'}
socket = by_index[0]
right_panel = by_index[3]
if socket.role != 'cutout':
    raise SystemExit(f'right socket/notch path role is {socket.role}, expected cutout')
if right_panel.role != 'paintable':
    raise SystemExit(f'right panel path role is {right_panel.role}, expected paintable')
if right_panel.area < 1_700_000:
    raise SystemExit(f'right panel area {right_panel.area:.0f} too small; likely ignored polyline closure')
if right_panel.bounds[3] < 2580:
    raise SystemExit(f'right panel bottom {right_panel.bounds[3]:.1f} too high; likely diagonal auto-close')
print('space socket/polyline geometry regression passed')
"""
    try:
        subprocess.run(
            ["python3", "-c", script],
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
    return True


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
    check(
        command_ok(
            [
                "python3",
                "scripts/scaffold_template_task.py",
                "skyline-validator-smoke",
                "--svg",
                "assets/skyline/city-skyline template.svg",
                "--refs",
                "assets/skyline/example of DO - specific elements (fairies, birds) not cropped.png",
                "--dry-run",
            ],
            "would write tasks/skyline-validator-smoke/skyline-example-feedback.md",
        ),
        "skyline task scaffold dry-run works",
        failures,
    )
    check(
        command_ok(
            [
                "python3",
                "scripts/scaffold_template_task.py",
                "city-scape-validator-smoke",
                "--title",
                "City Scape Validator Smoke",
                "--svg",
                "assets/templates/two-panel-template.svg",
                "--refs",
                "assets/reference-images/castle-style-reference.png",
                "--dry-run",
            ],
            "would write tasks/city-scape-validator-smoke/skyline-example-feedback.md",
        ),
        "city-scape title scaffold dry-run writes skyline feedback",
        failures,
    )
    check(
        space_socket_geometry_regression_ok(),
        "space socket/polyline geometry regression works",
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
