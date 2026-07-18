#!/usr/bin/env python3
"""Validate that SVG-template illustration workflow docs stay agent-usable."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "skills/reference-style-packet/SKILL.md",
    "skills/skyline-template-illustration/SKILL.md",
    "skills/svg-geometry-style-illustration/SKILL.md",
    "skills/svg-geometry-style-illustration/drift_probes.json",
    "skills/svg-template-style-agent/SKILL.md",
    "skills/svg-template-style-agent/drift_probes.json",
    "skills/svg-template-illustration/SKILL.md",
    "skills/svg-template-review-judge/SKILL.md",
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
    "skills/svg-template-illustration/SKILL.md": [
        "Do not make a generic rectangular illustration",
        "svg-geometry-style-illustration",
        "visual style packet",
        "Any subagent assigned to adapt approved geometry to style",
        "Reset Vs Patch",
        "visual judge",
        "Done Means",
    ],
    "skills/svg-geometry-style-illustration/SKILL.md": [
        "SVG geometry -> OUTSET cutouts -> outset contract base -> visual style packet",
        "ELEMENTS-FIRST",
        "WHOLE-PANEL-REDRAW",
        "Use the approved geometry image only as a composition/negative-space map",
        "Prompt-only substitute",
        "A mechanical pass is not approval",
        "visual judge",
    ],
    "skills/svg-geometry-style-illustration/drift_probes.json": [
        "svg-geometry-style-requires-visual-style-packet",
        "svg-geometry-style-no-prompt-only-substitute",
        "svg-geometry-style-pass-is-not-approval",
        "svg-geometry-style-geometry-approved-route",
    ],
    "skills/reference-style-packet/SKILL.md": [
        "build_reference_style_packet.py",
        "style-agent prompt",
        "Style agents must receive images",
    ],
    "skills/svg-template-style-agent/SKILL.md": [
        "## Job Boundary",
        "element sheets",
        "Style agents do not",
        "ALWAYS use this rule for geometry-to-style adaptation",
        "prompt-only attempt is not",
        "approved geometry image only as a composition/negative-space map",
        "REFERENCE-MATCH",
    ],
    "skills/svg-template-style-agent/drift_probes.json": [
        "geometry-approved-style-adaptation-requires-whole-panel-redraw",
        "locked[-_ ]geometry",
        "whole[-_ ]panel redraw",
    ],
    "skills/skyline-template-illustration/SKILL.md": [
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
    "skills/svg-template-review-judge/SKILL.md": [
        "Inspect the actual images",
        "ACCEPT | LOCAL PATCH | PROMPT RESTART | BLOCKED",
        "metadata",
        "cutout",
    ],
    "docs/svg-template-illustration-workflow.md": [
        "svg-geometry-style-illustration",
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
        "svg-geometry-style-illustration",
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
        ".codex/skills/svg-geometry-style-illustration/SKILL.md",
        ".codex/skills/svg-template-illustration/SKILL.md",
        ".codex/skills/skyline-template-illustration/SKILL.md",
        ".codex/skills/svg-template-review-judge/SKILL.md",
        "Do not substitute locked-geometry scripts",
    ],
}

LEGACY_SKYLINE_ASSETS = [
    "assets/skyline/city-skyline template.svg",
    "assets/skyline/example of DO - specific elements (fairies, birds) not cropped.png",
    "assets/skyline/example of DON'T - specific elements (fairies, birds) cropped.png",
    "assets/skyline/door panel example - bridge inside door flaps area.png",
    "assets/skyline/example - bridge runs through panels + top contour tracing buildings shape.png",
]


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
panels = [record for record in records if record.role == 'paintable']
right_socket = next((record for record in records if record.role == 'cutout' and record.bounds[2] > 1600), None)
if right_socket is None:
    raise SystemExit('right socket/notch is not classified as a cutout')
if len(panels) != 2:
    raise SystemExit(f'expected two paintable panels, found {len(panels)}')
if min(panel.area for panel in panels) < 1_700_000:
    raise SystemExit('paintable panel too small; likely ignored polyline closure')
if min(panel.bounds[3] for panel in panels) < 2580:
    raise SystemExit('a paintable panel bottom is too high; likely diagonal auto-close')
print('space socket/polyline geometry regression passed')
"""
    try:
        subprocess.run(
            [sys.executable, "-c", script],
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--legacy-skyline",
        action="store_true",
        help="validate optional historical skyline fixtures, which are not clone-visible",
    )
    args = parser.parse_args()
    failures: list[str] = []

    for rel in REQUIRED_FILES:
        check((ROOT / rel).is_file(), f"file exists: {rel}", failures)

    for rel, snippets in REQUIRED_SNIPPETS.items():
        path = ROOT / rel
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        for snippet in snippets:
            check(snippet in text, f"{rel} contains {snippet!r}", failures)

    if args.legacy_skyline:
        for rel in LEGACY_SKYLINE_ASSETS:
            check((ROOT / rel).is_file(), f"legacy skyline asset exists: {rel}", failures)
    else:
        print("[SKIP] historical skyline fixtures are optional; run --legacy-skyline when provided")

    check(
        command_ok(
            [
                sys.executable,
                "scripts/scaffold_template_task.py",
                "validator-smoke",
                "--svg",
                "assets/templates/two-panel-template.svg",
                "--refs",
                "assets/templates/two-panel-template-raster.png",
                "--dry-run",
            ]
        ),
        "task scaffold dry-run works",
        failures,
    )
    if args.legacy_skyline:
        check(
            command_ok(
                [
                    sys.executable,
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
                sys.executable,
                "scripts/scaffold_template_task.py",
                "city-scape-validator-smoke",
                "--title",
                "City Scape Validator Smoke",
                "--svg",
                "assets/templates/two-panel-template.svg",
                "--refs",
                "assets/templates/two-panel-template-raster.png",
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
