#!/usr/bin/env python3
"""
Build a reference-image catalog: sweep all reference/source images in the repo
and emit a JSONL index plus a summary markdown.
"""

import os
import json
from pathlib import Path
from PIL import Image
import sys

REPO_ROOT = Path("/Users/za/Documents/product images repo")
EXCLUDE_DIRS = {
    "outputs",
    "candidates",
    "finals",
    "controlmaps",
    "geometry",
    ".git",
    ".claude",
    "node_modules",
    "scratchpad",
    ".brainer",
    ".cache",
    ".codex",
    ".cursor",
    ".gemini",
    ".genbatch",
    ".github",
    ".iopaint-models",
    ".pytest_cache",
    ".secrets",
    ".venv-bg",
    ".venv-gen",
    ".venv-iopaint",
}

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".tiff", ".bmp"}

def should_exclude(path: Path) -> bool:
    """Check if a path should be excluded."""
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return True
    # Also exclude "Images" directory (generated outputs)
    if "Images" in path.parts:
        return True
    return False

def get_image_dimensions(image_path: Path):
    """Get image dimensions in pixels. Return (width, height) or None if unreadable."""
    try:
        with Image.open(image_path) as img:
            return img.width, img.height
    except Exception as e:
        print(f"Warning: Could not read {image_path}: {e}", file=sys.stderr)
        return None

def get_file_size_kb(image_path: Path) -> int:
    """Get file size in KB."""
    try:
        return int(image_path.stat().st_size / 1024)
    except Exception:
        return 0

def classify_kind(rel_path: str) -> str:
    """Classify image kind based on directory path."""
    if "/refs/" in rel_path or rel_path.startswith("refs/"):
        return "style-ref"
    if "/source/" in rel_path or rel_path.startswith("source/"):
        return "source-design"
    return "other"

def get_task_name(rel_path: str) -> str:
    """Extract task directory name from relative path."""
    parts = Path(rel_path).parts
    if len(parts) > 0 and parts[0] == "tasks":
        if len(parts) > 1:
            return parts[1]
    return "unknown"

def main():
    catalog = []
    unreadable = []
    tasks_seen = set()
    kind_counts = {}
    task_counts = {}

    # Walk through tasks directory
    tasks_dir = REPO_ROOT / "tasks"
    if not tasks_dir.exists():
        print(f"Error: {tasks_dir} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Sweeping {tasks_dir}...", file=sys.stderr)

    for image_path in sorted(tasks_dir.rglob("*")):
        # Skip directories, hidden files, and non-images
        if image_path.is_dir() or image_path.name.startswith("."):
            continue

        if image_path.suffix.lower() not in IMAGE_EXTS:
            continue

        # Check if path should be excluded
        if should_exclude(image_path):
            continue

        # Get relative path from repo root
        rel_path = str(image_path.relative_to(REPO_ROOT))

        # Get dimensions
        dims = get_image_dimensions(image_path)
        if dims is None:
            unreadable.append(rel_path)
            continue

        # Build catalog entry
        kind = classify_kind(rel_path)
        task = get_task_name(rel_path)
        ext = image_path.suffix.lower()
        kb = get_file_size_kb(image_path)
        w, h = dims

        entry = {
            "path": rel_path,
            "task": task,
            "kind": kind,
            "ext": ext,
            "px": [w, h],
            "kb": kb,
        }
        catalog.append(entry)

        # Track for summary
        tasks_seen.add(task)
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
        task_counts[task] = task_counts.get(task, 0) + 1

    # Sort by task, then by path
    catalog.sort(key=lambda x: (x["task"], x["path"]))

    # Write JSONL catalog
    output_jsonl = REPO_ROOT / "studio" / "reference_catalog.jsonl"
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    with open(output_jsonl, "w") as f:
        for entry in catalog:
            f.write(json.dumps(entry) + "\n")

    print(f"Wrote {len(catalog)} entries to {output_jsonl}", file=sys.stderr)

    # Find all task directories to detect gaps
    all_tasks = set()
    for task_dir in sorted(tasks_dir.iterdir()):
        if task_dir.is_dir() and not task_dir.name.startswith("."):
            all_tasks.add(task_dir.name)

    gap_tasks = sorted(all_tasks - tasks_seen)

    # Write summary markdown
    output_md = REPO_ROOT / "studio" / "reference_catalog_summary.md"
    with open(output_md, "w") as f:
        f.write("# Reference Image Catalog Summary\n\n")

        f.write("## Overview\n\n")
        f.write(f"- **Total reference images:** {len(catalog)}\n")
        f.write(f"- **Tasks with references:** {len(tasks_seen)}\n")
        f.write(f"- **Total tasks:** {len(all_tasks)}\n")
        f.write(f"- **Tasks without references:** {len(gap_tasks)}\n")
        if unreadable:
            f.write(f"- **Unreadable images:** {len(unreadable)}\n")
        f.write("\n")

        f.write("## Images by Kind\n\n")
        for kind in sorted(kind_counts.keys()):
            count = kind_counts[kind]
            f.write(f"- **{kind}:** {count}\n")
        f.write("\n")

        f.write("## Images per Task\n\n")
        for task in sorted(task_counts.keys()):
            count = task_counts[task]
            f.write(f"- {task}: {count}\n")
        f.write("\n")

        if gap_tasks:
            f.write("## Tasks WITHOUT References (Gap List)\n\n")
            for task in gap_tasks:
                f.write(f"- {task}\n")
            f.write("\n")

        if unreadable:
            f.write("## Unreadable Images\n\n")
            for path in unreadable:
                f.write(f"- {path}\n")
            f.write("\n")

    print(f"Wrote summary to {output_md}", file=sys.stderr)

    if unreadable:
        print(f"\nWarning: {len(unreadable)} unreadable images detected:", file=sys.stderr)
        for path in unreadable[:5]:
            print(f"  - {path}", file=sys.stderr)
        if len(unreadable) > 5:
            print(f"  ... and {len(unreadable) - 5} more", file=sys.stderr)

if __name__ == "__main__":
    main()
