#!/usr/bin/env python3
"""Verify this repo's local setup."""

from __future__ import annotations

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
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
    "scripts/asset_report.py",
    "scripts/build_reference_style_packet.py",
    "scripts/crop_nonwhite.py",
    "scripts/export_composite.py",
    "scripts/make_overlay_preview.py",
    "scripts/register_result.py",
    "scripts/score_template_fit.py",
    "scripts/scaffold_template_task.py",
    "scripts/validate_svg_template_workflow.py",
    "scripts/svg_geometry_report.py",
]

REQUIRED_ASSETS = [
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

    check(command_ok([sys.executable, "scripts/asset_report.py"]), "asset report runs", failures)
    check(command_ok([sys.executable, "scripts/svg_geometry_report.py"]), "SVG geometry report runs", failures)
    check(command_ok([sys.executable, "scripts/build_reference_style_packet.py", "--help"]), "reference style packet builder CLI runs", failures)
    check(command_ok([sys.executable, "scripts/validate_svg_template_workflow.py"]), "SVG-template workflow validator runs", failures)
    check(
        command_ok(
            [
                sys.executable,
                "scripts/scaffold_template_task.py",
                "verify-smoke",
                "--svg",
                "assets/templates/two-panel-template.svg",
                "--refs",
                "assets/templates/two-panel-template-raster.png",
                "--dry-run",
            ]
        ),
        "SVG-template task scaffold dry-run runs",
        failures,
    )
    check(command_ok([sys.executable, "scripts/export_composite.py", "--help"]), "composite exporter runs", failures)
    check(command_ok([sys.executable, "scripts/score_template_fit.py", "--help"]), "template-fit scorer runs", failures)

    if failures:
        print("\nSetup verification failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nSetup verification passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
