#!/usr/bin/env python3
"""artifact_guard_post.py — PostToolUse freshness stamper (companion to artifact_guard.py).

Gate 2 (edit-without-read) must know the agent knows a file's CURRENT content.
A fresh Read proves it (stamped by artifact_guard.py). A successful Edit/Write
also proves it — but only AFTER the write lands. The interim approach stamped
freshness at PreToolUse approval, which was unsafe three ways: it granted
freshness BEFORE the write succeeded, it used global path-only state shared
across sessions, and its +5s grace window could mask an external modification
landing within 5 seconds.

This hook fires PostToolUse on Edit|MultiEdit|Write|NotebookEdit — i.e. only
after the tool actually ran — skips anything whose tool_response signals
failure, and records

    {"sessions": {<session_id>: {"paths": {<resolved path>: <st_mtime_ns>},
                                 "updated": <epoch>}}}

in .claude/state/write_stamps.json. Gate 2 honours a stamp only while the
file's current st_mtime_ns EXACTLY equals the stamped one, and only for the
same session — so a failed write grants nothing, another session's write
grants nothing, and any external mutation after our write (however fast)
invalidates the stamp.

Always exits 0: a stamper bug must never disturb the session.

Wire (in .claude/settings.json PostToolUse, matcher "Edit|MultiEdit|Write|NotebookEdit"):
  python3 "${CLAUDE_PROJECT_DIR:-$PWD}/.claude/hooks/artifact_guard_post.py"
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

WRITE_TOOLS = ("Edit", "MultiEdit", "Write", "NotebookEdit")
MAX_SESSIONS = 16  # prune stamps of long-dead sessions so the file stays small


def _failed(resp) -> bool:
    """Conservative failure sniff across the tool_response shapes hosts emit.
    (PostToolUse normally fires only on success; this guards hosts/versions
    that fire it on errors too.)"""
    if isinstance(resp, dict):
        if resp.get("success") is False:
            return True
        if resp.get("error") or resp.get("is_error") or resp.get("isError"):
            return True
    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    tool = payload.get("tool_name") or payload.get("tool") or ""
    if tool not in WRITE_TOOLS:
        return 0
    if _failed(payload.get("tool_response")):
        return 0  # failed write -> no freshness
    ti = payload.get("tool_input") or payload.get("toolInput") or {}
    fp = ti.get("file_path") or ti.get("notebook_path")
    if not fp:
        return 0
    from artifact_guard import norm, load_write_stamps, save_write_stamps
    path = norm(fp)
    try:
        mtime_ns = Path(path).stat().st_mtime_ns
    except Exception:
        return 0  # nothing landed on disk -> nothing to stamp
    sid = payload.get("session_id") or payload.get("sessionId") or ""
    d = load_write_stamps()
    sessions = d.setdefault("sessions", {})
    sess = sessions.get(sid)
    if not isinstance(sess, dict):
        sess = sessions[sid] = {}
    sess.setdefault("paths", {})[path] = mtime_ns
    sess["updated"] = time.time()
    if len(sessions) > MAX_SESSIONS:
        def age(k):
            v = sessions[k]
            return v.get("updated", 0) if isinstance(v, dict) else 0
        for old in sorted(sessions, key=age)[: len(sessions) - MAX_SESSIONS]:
            del sessions[old]
    save_write_stamps(d)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)  # fail-open: never disturb the session
