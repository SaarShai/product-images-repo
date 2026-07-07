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
import shlex
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STATE = REPO / ".claude/state/read_paths.json"
IMAGES = "tasks/space-np01-front-bottom-02/RESULTS/Images"
SYNC = "scripts/sync_results_images.py"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}
# only round-CANDIDATE images need a gate bundle; boards/overlays/previews flow free
CANDIDATE_NAME = re.compile(r"(final|_s\d+)", re.IGNORECASE)


def _review_candidate_copy_without_bundle(cmd: str) -> str | None:
    """PROCESS-V3 law 4: a candidate image cannot enter REVIEW/ without its
    sibling *-bundle.json (the gate runner's output). Fail-open on parse errors
    (a hook crash blocks ALL tools — never risk that for this check)."""
    try:
        words = shlex.split(cmd)
        if not words or Path(words[0]).name not in ("cp", "mv"):
            return None
        args = [w for w in words[1:] if not w.startswith("-")]
        if len(args) < 2:
            return None
        dest = args[-1]
        if not (dest == "REVIEW" or dest.startswith("REVIEW/") or "/REVIEW/" in dest):
            return None
        for src in args[:-1]:
            sp = Path(src)
            if sp.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            if not CANDIDATE_NAME.search(sp.name):
                continue  # boards / overlays / previews are not gated candidates
            src_path = sp if sp.is_absolute() else REPO / sp
            if not any(src_path.parent.glob("*-bundle.json")):
                return src
        return None
    except Exception:
        return None


def _is_existing_raw(pth: Path) -> bool:
    try:
        p = pth if pth.is_absolute() else REPO / pth
        return (
            p.suffix.lower() in IMAGE_SUFFIXES
            and "raws" in p.parent.parts
            and p.exists()
        )
    except Exception:
        return False


def _raw_overwrite_dest(cmd: str) -> str | None:
    """never-ruin-good-raw (memory law): block cp/mv whose destination would
    OVERWRITE an existing image inside a raws/ dir. Fail-open on parse errors."""
    try:
        words = shlex.split(cmd)
        if not words or Path(words[0]).name not in ("cp", "mv", "rsync", "install"):
            return None
        args = [w for w in words[1:] if not w.startswith("-")]
        if len(args) < 2:
            return None
        dest = Path(args[-1])
        if _is_existing_raw(dest):
            return args[-1]
        # dest is a raws/ DIR: overwrite iff a same-named source exists inside it
        dp = dest if dest.is_absolute() else REPO / dest
        if dp.is_dir() and dp.name == "raws":
            for src in args[:-1]:
                cand = dp / Path(src).name
                if cand.suffix.lower() in IMAGE_SUFFIXES and cand.exists():
                    return str(cand)
        return None
    except Exception:
        return None


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
        raw_overwrite = _raw_overwrite_dest(cmd)
        if raw_overwrite:
            block(
                "BLOCKED (artifact_guard: raw-overwrite).\n"
                f"cp/mv would OVERWRITE an existing generator raw: {raw_overwrite}\n"
                "Raws are immutable evidence (user law: never ruin a good raw — "
                "'raw was good, you ruined it with exact.png').\n"
                "Write derived outputs beside the raw under a new name "
                "(exact/overlay/repair-*), never on top of it."
            )
        missing_bundle_src = _review_candidate_copy_without_bundle(cmd)
        if missing_bundle_src:
            block(
                "BLOCKED (artifact_guard: review-candidate-without-gate-bundle).\n"
                "A CANDIDATE image cannot enter REVIEW/ without its gate bundle "
                "(*-bundle.json beside the source image).\n"
                f"Ungated source: {missing_bundle_src}\n"
                "Run the one-command gate first:\n"
                "  python3 scripts/gates.py --cand <img> --geom <geomdir> --panel <name> --outdir <dir>\n"
                "then copy the image together with its bundle + overlay."
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
        if _is_existing_raw(p):
            block(
                "BLOCKED (artifact_guard: raw-overwrite).\n"
                f"{tool} would overwrite an existing generator raw: {fp}\n"
                "Raws are immutable evidence (never ruin a good raw). Write derived "
                "outputs under a new name beside it."
            )
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
