#!/usr/bin/env python3
"""artifact_guard.py — PreToolUse blocker (operation-boundary enforcement).

Born from the two-session task-retrospective (2026-06-17). compliance-canary is a
UserPromptSubmit hook: it can only WARN post-hoc, never BLOCK at the tool boundary
(cross-vendor/GPT finding). These two failures recurred past prose gates and earn a
real block:

  1. file-op-without-verify — an ad-hoc `cp`/`mv` into the central results library
     `tasks/space-np01-front-bottom-02/RESULTS/Images/` once silently dropped 8 files
     (`$n__raw` expanded empty). BLOCK it; require the verified
     `scripts/sync_results_images.py` instead.
  2. edit-without-read — Edit/Write to an EXISTING file with no fresh Read of that
     path this session (since the file's last modification). The native guard catches
     the never-read case; this also catches stale-read and bash-cat-then-edit.

Mechanism: PreToolUse hook. exit 0 = allow; exit 2 + stderr = BLOCK (stderr shown to
the model). State for read-tracking lives in .claude/state/read_paths.json.

Wire (in .claude/settings.json PreToolUse, matcher "*"):
  python3 ./.claude/hooks/artifact_guard.py
"""
from __future__ import annotations
import json
import os
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STATE = REPO / ".claude/state/read_paths.json"
IMAGES = "tasks/space-np01-front-bottom-02/RESULTS/Images"
SYNC = "scripts/sync_results_images.py"


def load_state() -> dict:
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def save_state(s: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s))


def norm(p: str) -> str:
    try:
        return str(Path(p).resolve())
    except Exception:
        return p or ""


def block(msg: str):
    print(msg, file=sys.stderr)
    sys.exit(2)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # never break the session on a parse error
    tool = payload.get("tool_name") or payload.get("tool") or ""
    ti = payload.get("tool_input") or payload.get("toolInput") or {}

    # --- record reads (so Edit/Write can require a fresh read) ---
    if tool in ("Read", "NotebookRead"):
        fp = ti.get("file_path") or ti.get("notebook_path")
        if fp:
            s = load_state()
            s[norm(fp)] = time.time()
            save_state(s)
        return 0

    # --- gate 1: ad-hoc cp/mv INTO the central Images library ---
    if tool == "Bash":
        cmd = ti.get("command", "") or ""
        is_copy = re.search(r"\b(cp|mv|rsync|install)\b", cmd) is not None
        uses_sync = "sync_results_images.py" in cmd
        # Only block when Images is a DESTINATION, not a source (`cp Images/x refs/` is fine).
        # An IMAGES occurrence is a SOURCE iff it sits in first-arg position right after
        # cp/mv/rsync/install (optionally quoted). If ANY occurrence is NOT in source
        # position, it's a destination -> block.
        def _img_is_dest(c):
            for m in re.finditer(re.escape(IMAGES), c):
                pre = c[max(0, m.start() - 8):m.start()]
                if re.search(r"\b(cp|mv|rsync|install)\b\s*[\"']?$", pre):
                    continue  # source position
                return True   # destination position
            return False
        if IMAGES in cmd and is_copy and not uses_sync and _img_is_dest(cmd):
            block(
                "BLOCKED (artifact_guard: file-op-without-verify).\n"
                f"Ad-hoc {('cp/mv')} into {IMAGES} is forbidden — a hand-rolled loop "
                "once silently dropped 8 files ($n__raw -> empty).\n"
                f"Use the verified script instead:\n"
                f"  python3 {SYNC}          # copies every raw/exact/overlay\n"
                f"  python3 {SYNC} --check  # verifies none are missing (exit 1 if any)\n"
                "If you truly need a one-off copy, run sync afterward and quote its --check output."
            )
        return 0

    # --- gate 2: edit/write to an existing file with no fresh read ---
    if tool in ("Edit", "MultiEdit", "Write", "NotebookEdit"):
        fp = ti.get("file_path") or ti.get("notebook_path")
        if not fp:
            return 0
        p = Path(fp)
        if not p.exists():
            return 0  # creating a new file is fine
        s = load_state()
        last_read = s.get(norm(fp), 0)
        try:
            mtime = p.stat().st_mtime
        except Exception:
            mtime = 0
        if last_read <= mtime:
            block(
                "BLOCKED (artifact_guard: edit-without-read).\n"
                f"You are about to {tool} {fp} but have no Read of it newer than its "
                "last modification this session.\n"
                "Read the file with the Read tool FIRST (a bash cat/sed/head does NOT count), "
                "then Edit. Editing on a stale/absent read is how wrong-line edits and "
                "clobbers happen."
            )
        return 0

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        # fail-open: a guard bug must never brick the session
        sys.exit(0)
