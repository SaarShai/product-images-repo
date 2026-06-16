#!/usr/bin/env python3
"""Copy a generated image into a task output folder and record metadata."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("task", help="task folder name under tasks/")
    parser.add_argument("variant", help="prompt variant, for example prompt-a-strict")
    parser.add_argument("image", type=Path, help="path to generated image")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    source = args.image.expanduser().resolve()
    if not source.exists():
        raise SystemExit(f"Image not found: {source}")

    task_dir = ROOT / "tasks" / args.task
    output_dir = task_dir / "outputs" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = output_dir / f"{timestamp}-{args.variant}{source.suffix.lower()}"
    shutil.copy2(source, dest)

    record = {
        "timestamp": timestamp,
        "task": args.task,
        "variant": args.variant,
        "source": str(source),
        "path": str(dest.relative_to(ROOT)),
        "notes": args.notes,
    }
    metadata_path = task_dir / "outputs" / "results.jsonl"
    with metadata_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")

    print(dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
