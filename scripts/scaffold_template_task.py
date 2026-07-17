#!/usr/bin/env python3
"""Create a task packet for SVG-template illustration work."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "tasks" / "_template"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "template-task"


def rel_or_abs(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def render_template(path: Path, values: dict[str, str]) -> str:
    text = path.read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def copy_unique(source: Path, destination_dir: Path, preferred_name: str) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    candidate = destination_dir / preferred_name
    if candidate.exists():
        stem = candidate.stem
        suffix = candidate.suffix
        for index in range(2, 1000):
            alternate = destination_dir / f"{stem}-{index}{suffix}"
            if not alternate.exists():
                candidate = alternate
                break
        else:
            raise SystemExit(f"Could not choose a unique destination for {source}")
    shutil.copy2(source, candidate)
    return candidate


def is_skyline_task(task_slug: str, source_svg: Path, title: str = "") -> bool:
    haystack = f"{task_slug} {title} {source_svg}".lower()
    return any(term in haystack for term in ["skyline", "cityscape", "city-scape", "city-skyline"])


def write(path: Path, content: str, dry_run: bool, skip_existing: bool = False) -> None:
    if skip_existing and path.exists():
        print(f"{'would keep' if dry_run else 'kept'} existing {rel_or_abs(path)}")
        return
    if dry_run:
        print(f"would write {rel_or_abs(path)}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", help="Task name or slug under tasks/")
    parser.add_argument("--svg", required=True, type=Path, help="Authoritative SVG template")
    parser.add_argument("--refs", nargs="*", type=Path, default=[], help="Style/color reference images")
    parser.add_argument("--title", help="Human-readable task title")
    parser.add_argument("--no-copy", action="store_true", help="Record source paths without copying assets into the task")
    parser.add_argument("--dry-run", action="store_true", help="Show planned writes without touching files")
    parser.add_argument(
        "--allow-existing", action="store_true",
        help="Allow scaffolding into a task dir that already exists (e.g. a "
             "pre-authored contract file); scaffolds only the MISSING pieces "
             "and never overwrites files already present",
    )
    args = parser.parse_args()

    task_slug = slugify(args.task)
    title = args.title or task_slug.replace("-", " ").title()
    task_dir = ROOT / "tasks" / task_slug
    if task_dir.exists() and not args.dry_run and not args.allow_existing:
        raise SystemExit(f"Task already exists: {rel_or_abs(task_dir)}")

    source_svg = args.svg.expanduser().resolve()
    refs = [item.expanduser().resolve() for item in args.refs]
    missing = [str(path) for path in [source_svg, *refs] if not path.exists()]
    if missing:
        raise SystemExit("Missing input file(s):\n" + "\n".join(f"- {item}" for item in missing))

    planned_dirs = [
        task_dir / "source",
        task_dir / "refs",
        task_dir / "style-packet",
        task_dir / "prompts",
        task_dir / "outputs" / "generated",
        task_dir / "outputs" / "reviews",
        task_dir / "outputs" / "final",
    ]
    if args.dry_run:
        for directory in planned_dirs:
            print(f"would create {rel_or_abs(directory)}")
    else:
        for directory in planned_dirs:
            directory.mkdir(parents=True, exist_ok=True)

    if args.no_copy:
        task_svg = source_svg
        task_refs = refs
    else:
        task_svg = task_dir / "source" / "template.svg"
        if args.allow_existing and task_svg.exists():
            print(f"{'would keep' if args.dry_run else 'kept'} existing {rel_or_abs(task_svg)}")
        elif args.dry_run:
            print(f"would copy {source_svg} -> {rel_or_abs(task_svg)}")
        else:
            shutil.copy2(source_svg, task_svg)
        task_refs = []
        for ref in refs:
            if args.dry_run:
                planned = task_dir / "refs" / ref.name
                print(f"would copy {ref} -> {rel_or_abs(planned)}")
                task_refs.append(planned)
            else:
                task_refs.append(copy_unique(ref, task_dir / "refs", ref.name))

    ref_list = "\n".join(f"- `{rel_or_abs(path)}`" for path in task_refs) or "- Pending."
    values = {
        "TASK_TITLE": title,
        "TASK_SLUG": task_slug,
        "SVG_PATH": rel_or_abs(task_svg),
        "REF_LIST": ref_list,
    }

    is_skyline = is_skyline_task(task_slug, source_svg, title)
    workflow = "docs/skyline-template-illustration-workflow.md" if is_skyline else "docs/svg-template-illustration-workflow.md"
    skill = (
        ".codex/skills/skyline-template-illustration/SKILL.md"
        if is_skyline
        else ".codex/skills/svg-geometry-style-illustration/SKILL.md"
    )
    manifest = {
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "task": task_slug,
        "title": title,
        "copy_assets": not args.no_copy,
        "source_svg_original": str(source_svg),
        "task_svg": rel_or_abs(task_svg),
        "style_references_original": [str(path) for path in refs],
        "task_style_references": [rel_or_abs(path) for path in task_refs],
        "workflow": workflow,
        "base_workflow": "docs/svg-template-illustration-workflow.md",
        "skill": skill,
        "review_checklist": "docs/review-judge-checklist.md",
    }
    if is_skyline:
        manifest["asset_map"] = "assets/skyline/README.md"

    write(task_dir / "asset-manifest.json", json.dumps(manifest, indent=2) + "\n", args.dry_run, args.allow_existing)
    write(task_dir / "template-manifest.json", render_template(TEMPLATE_DIR / "template-manifest.json", values), args.dry_run, args.allow_existing)
    write(task_dir / "session-brief.md", render_template(TEMPLATE_DIR / "session-brief.md", values), args.dry_run, args.allow_existing)
    write(task_dir / "review-judge.md", render_template(TEMPLATE_DIR / "review-judge.md", values), args.dry_run, args.allow_existing)
    if is_skyline:
        write(
            task_dir / "skyline-example-feedback.md",
            render_template(TEMPLATE_DIR / "skyline-example-feedback.md", values),
            args.dry_run, args.allow_existing,
        )
    write(
        task_dir / "prompts" / "prompt-v1-contour-first.md",
        (TEMPLATE_DIR / "prompts" / "prompt-v1-contour-first.md").read_text(encoding="utf-8"),
        args.dry_run, args.allow_existing,
    )

    for keep in [
        task_dir / "outputs" / "generated" / ".gitkeep",
        task_dir / "outputs" / "reviews" / ".gitkeep",
        task_dir / "outputs" / "final" / ".gitkeep",
        task_dir / "style-packet" / ".gitkeep",
    ]:
        write(keep, "", args.dry_run, args.allow_existing)

    if not args.dry_run:
        print(rel_or_abs(task_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
