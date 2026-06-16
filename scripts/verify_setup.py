#!/usr/bin/env python3
"""Verify this repo's local setup."""

from __future__ import annotations

import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = [
    "plan-first-execute",
    "lean-execution",
    "verify-before-completion",
    "wiki-memory",
    "write-gate",
    "think",
    "index-first",
    "output-filter",
]

REQUIRED_FILES = [
    ".gitignore",
    "AGENTS.md",
    "README.md",
    "docs/brainer-skills.md",
    "docs/local-tooling.md",
    "docs/setup-verification.md",
    "docs/workflow.md",
    "docs/svg-template-illustration-workflow.md",
    "docs/review-judge-checklist.md",
    ".codex/skills/svg-template-illustration/SKILL.md",
    ".codex/skills/svg-template-review-judge/SKILL.md",
    "scripts/asset_report.py",
    "scripts/build_prompt_pack.py",
    "scripts/crop_nonwhite.py",
    "scripts/export_composite.py",
    "scripts/make_overlay_preview.py",
    "scripts/register_result.py",
    "scripts/score_template_fit.py",
    "scripts/scaffold_template_task.py",
    "scripts/validate_svg_template_workflow.py",
    "scripts/svg_geometry_report.py",
    "tasks/castle-panels/CURRENT.md",
    "tasks/castle-panels/final-handoff.md",
    "tasks/castle-panels/system-plan.md",
    "tasks/castle-panels/session-brief.md",
    "tasks/castle-panels/asset-manifest.json",
    "tasks/castle-panels/prompts/prompt-a-strict.md",
    "tasks/castle-panels/prompts/prompt-b-balanced.md",
    "tasks/castle-panels/prompts/prompt-c-contour-first.md",
    "tasks/castle-panels/prompts/prompt-v2-mask-first.md",
    "tasks/castle-panels/prompts/prompt-v3-svg-mask-artwork-only.md",
    "tasks/castle-panels/prompts/prompt-v4-clearance-bands.md",
    "tasks/castle-panels/prompts/prompt-v5-safe-margin-top-bridge.md",
    "tasks/castle-panels/prompts/prompt-v6-narrow-center-safe-gutters.md",
    "tasks/castle-panels/prompts/prompt-v7-tall-with-background-wall.md",
    "tasks/castle-panels/prompts/prompt-v8-center-wall-safe-gutters.md",
    "tasks/castle-panels/prompts/prompt-v9a-empty-center-split-safe.md",
    "tasks/castle-panels/prompts/prompt-v9b-wall-background-split-safe.md",
    "tasks/castle-panels/outputs/reviews/2026-06-15-v6-v7-decision-packet.md",
    "tasks/_template/session-brief.md",
    "tasks/_template/review-judge.md",
    "tasks/_template/template-manifest.json",
    "tasks/_template/prompts/prompt-v1-contour-first.md",
    "wiki/index.md",
    "wiki/L0_rules.md",
    "wiki/L1_index.md",
]

REQUIRED_ASSETS = [
    "assets/reference-images/castle-style-reference.png",
    "assets/reference-images/adapted-contour-example-1.png",
    "assets/reference-images/adapted-contour-example-2.png",
    "assets/templates/two-panel-template-raster.png",
    "assets/templates/two-panel-template.svg",
    "assets/templates/previews/two-panel-template-cropped.png",
]


def check(condition: bool, label: str, failures: list[str]) -> None:
    mark = "OK" if condition else "FAIL"
    print(f"[{mark}] {label}")
    if not condition:
        failures.append(label)


def command_ok(command: list[str]) -> bool:
    try:
        subprocess.run(command, cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def main() -> int:
    failures: list[str] = []

    check((ROOT / ".git").is_dir(), "git repository initialized", failures)

    for rel in REQUIRED_FILES:
        check((ROOT / rel).is_file(), f"file exists: {rel}", failures)

    for rel in REQUIRED_ASSETS:
        check((ROOT / rel).is_file(), f"asset exists: {rel}", failures)

    svg = ROOT / "assets/templates/two-panel-template.svg"
    try:
        root = ET.parse(svg).getroot()
        svg_ok = root.tag.endswith("svg") and bool(root.attrib.get("viewBox"))
    except Exception:
        svg_ok = False
    check(svg_ok, "template SVG parses and has a viewBox", failures)

    for skill in SKILLS:
        codex_link = ROOT / ".codex/skills" / skill
        gemini_link = ROOT / ".gemini/skills" / skill
        check(codex_link.is_symlink() and codex_link.exists(), f"Codex skill linked: {skill}", failures)
        check(gemini_link.is_symlink() and gemini_link.exists(), f"Gemini skill linked: {skill}", failures)

    check(shutil.which("gemini") is not None, "gemini CLI on PATH", failures)
    check(shutil.which("agy") is not None, "agy CLI on PATH", failures)
    check(command_ok(["python3", "scripts/asset_report.py"]), "asset report runs", failures)
    check(command_ok(["python3", "scripts/svg_geometry_report.py"]), "SVG geometry report runs", failures)
    check(command_ok(["python3", "scripts/build_prompt_pack.py", "tasks/castle-panels"]), "prompt pack builder runs", failures)
    check(command_ok(["python3", "scripts/validate_svg_template_workflow.py"]), "SVG-template workflow validator runs", failures)
    check(
        command_ok(
            [
                "python3",
                "scripts/scaffold_template_task.py",
                "verify-smoke",
                "--svg",
                "assets/templates/two-panel-template.svg",
                "--refs",
                "assets/reference-images/castle-style-reference.png",
                "--dry-run",
            ]
        ),
        "SVG-template task scaffold dry-run runs",
        failures,
    )
    check(command_ok(["python3", "scripts/export_composite.py", "--help"]), "composite exporter runs", failures)
    check(command_ok(["python3", "scripts/score_template_fit.py", "--help"]), "template-fit scorer runs", failures)

    if failures:
        print("\nSetup verification failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nSetup verification passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
