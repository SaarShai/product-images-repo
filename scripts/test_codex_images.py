#!/usr/bin/env python3
"""Regression test: codex generated-image discovery must go through codex_images.py.

The codex CLI has renamed its output files once already (~2026-07), silently
breaking every script that carried its own hardcoded filename glob.
scripts/codex_images.py is now the single source of truth; this test fails if
any script under scripts/ hardcodes one of the known codex image filename
globs instead of importing the helper. The ban-list is derived from
codex_images.CODEX_IMAGE_PATTERNS itself, so adding the next rename there
automatically bans hardcoding it anywhere else.

Also functionally checks that the helper discovers every known pattern (and
nothing else) in a synthetic session dir.

Run:  python3 scripts/test_codex_images.py
Exit: 0 = clean, 1 = a consumer bypasses the helper or the helper is broken.
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import codex_images  # noqa: E402

# The helper defines the patterns; this test scans everything else for them.
ALLOWED = {SCRIPTS / "codex_images.py", Path(__file__).resolve()}


def check_no_hardcoded_globs() -> list[str]:
    rx = re.compile("|".join(re.escape(p) for p in codex_images.CODEX_IMAGE_PATTERNS))
    failures = []
    for py in sorted(SCRIPTS.glob("*.py")):
        if py in ALLOWED:
            continue
        for lineno, line in enumerate(
                py.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if rx.search(line):
                failures.append(
                    f"{py.name}:{lineno}: hardcoded codex image glob "
                    f"(use codex_images.py) -> {line.strip()}")
    return failures


def check_helper_discovers_all_patterns() -> list[str]:
    failures = []
    with tempfile.TemporaryDirectory(prefix="codex_images_test_") as tmp:
        base = Path(tmp)
        sess = base / "0000-fake-session"
        sess.mkdir()
        want = set()
        for i, pat in enumerate(codex_images.CODEX_IMAGE_PATTERNS):
            f = sess / pat.replace("*", f"sample{i}")
            f.write_bytes(b"not-really-a-png")
            want.add(str(f))
        (sess / "decoy.txt").write_bytes(b"x")  # must NOT be discovered
        got_all = set(codex_images.all_images(base))
        got_sess = set(codex_images.session_images(sess))
        if got_all != want:
            failures.append(f"all_images: want {sorted(want)}, got {sorted(got_all)}")
        if got_sess != want:
            failures.append(f"session_images: want {sorted(want)}, got {sorted(got_sess)}")
        newest = codex_images.newest_image(base)
        if newest not in want:
            failures.append(f"newest_image: got {newest}, expected one of {sorted(want)}")
    return failures


def main() -> int:
    failures = check_no_hardcoded_globs() + check_helper_discovers_all_patterns()
    for f in failures:
        print(f"FAIL: {f}")
    if not failures:
        print("PASS: no hardcoded codex image globs outside codex_images.py; "
              f"helper discovers all {len(codex_images.CODEX_IMAGE_PATTERNS)} patterns")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
