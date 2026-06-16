#!/usr/bin/env python3
"""Combine a task's prompt variants into one reviewable prompt pack."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("task_dir", type=Path)
    args = parser.parse_args()

    task_dir = args.task_dir
    if not task_dir.is_absolute():
        task_dir = ROOT / task_dir

    prompts_dir = task_dir / "prompts"
    prompt_files = sorted(prompts_dir.glob("prompt-*.md"))
    if not prompt_files:
        raise SystemExit(f"No prompt files found in {prompts_dir}")

    out_path = task_dir / "prompt-pack.md"
    chunks = [
        f"# Prompt Pack: {task_dir.name}",
        "",
        "Use the same reference assets for every prompt variant.",
        "",
    ]
    for prompt_file in prompt_files:
        chunks.append(f"## {prompt_file.stem}")
        chunks.append("")
        chunks.append(prompt_file.read_text(encoding="utf-8").strip())
        chunks.append("")

    out_path.write_text("\n".join(chunks), encoding="utf-8")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
