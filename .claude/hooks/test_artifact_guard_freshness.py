#!/usr/bin/env python3
"""Tests for the gate-2 freshness contract:
PreToolUse blocker (artifact_guard.py) + PostToolUse stamper (artifact_guard_post.py).

Each test drives the REAL hook entry points as subprocesses with simulated hook
payloads, against an isolated state dir (ARTIFACT_GUARD_STATE_DIR).

Run:  python3 .claude/hooks/test_artifact_guard_freshness.py
  or: python3 -m pytest .claude/hooks/test_artifact_guard_freshness.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent
PRE = HOOKS / "artifact_guard.py"
POST = HOOKS / "artifact_guard_post.py"


class FreshnessContractTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.state = root / "state"
        self.files = root / "files"
        self.files.mkdir()

    def run_hook(self, script, payload):
        env = dict(os.environ, ARTIFACT_GUARD_STATE_DIR=str(self.state))
        return subprocess.run(
            [sys.executable, str(script)],
            input=json.dumps(payload),
            capture_output=True, text=True, env=env,
        )

    def pre(self, fp, sid="sess-A", tool="Edit"):
        return self.run_hook(PRE, {
            "session_id": sid,
            "tool_name": tool,
            "tool_input": {"file_path": str(fp)},
        })

    def post_write(self, fp, sid="sess-A", tool="Write", resp=None):
        return self.run_hook(POST, {
            "session_id": sid,
            "tool_name": tool,
            "tool_input": {"file_path": str(fp)},
            "tool_response": {"filePath": str(fp), "success": True}
                             if resp is None else resp,
        })

    def write_stamps(self):
        f = self.state / "write_stamps.json"
        return json.loads(f.read_text()) if f.exists() else {}

    def read_stamps(self):
        f = self.state / "read_paths.json"
        return json.loads(f.read_text()) if f.exists() else {}

    # --- required cases ---

    def test_successful_write_then_edit_passes(self):
        f = self.files / "new.txt"
        # PreToolUse on the creating Write: allowed, and must stamp NOTHING
        r = self.pre(f, tool="Write")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.write_stamps(), {}, "no pre-approval stamp allowed")
        self.assertEqual(self.read_stamps(), {}, "no pre-approval stamp allowed")
        f.write_text("hello")  # the Write lands
        self.assertEqual(self.post_write(f).returncode, 0)
        r = self.pre(f, tool="Edit")
        self.assertEqual(r.returncode, 0, f"Write->Edit false-blocked: {r.stderr}")

    def test_failed_write_stamps_nothing(self):
        f = self.files / "fail.txt"
        f.write_text("partial")
        for resp in ({"success": False}, {"error": "disk full"}, {"is_error": True}):
            self.assertEqual(self.post_write(f, resp=resp).returncode, 0)
        self.assertEqual(self.write_stamps(), {})
        r = self.pre(f)
        self.assertEqual(r.returncode, 2, "failed write must not grant freshness")
        self.assertIn("edit-without-read", r.stderr)

    def test_external_mutation_after_write_blocks(self):
        f = self.files / "mut.txt"
        f.write_text("v1")
        self.post_write(f)
        self.assertEqual(self.pre(f).returncode, 0)
        # external touch — even 1ns later (the old +5s window would mask this)
        st = f.stat()
        os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns + 1))
        r = self.pre(f)
        self.assertEqual(r.returncode, 2, "external mutation must invalidate stamp")
        self.assertIn("edit-without-read", r.stderr)

    def test_cross_session_isolation(self):
        f = self.files / "iso.txt"
        f.write_text("v1")
        self.post_write(f, sid="sess-A")
        self.assertEqual(self.pre(f, sid="sess-A").returncode, 0)
        r = self.pre(f, sid="sess-B")
        self.assertEqual(r.returncode, 2, "another session's stamp must not count")
        self.assertIn("edit-without-read", r.stderr)

    # --- guard rails around the contract ---

    def test_cold_edit_still_blocks(self):
        f = self.files / "cold.txt"
        f.write_text("v1")
        self.assertEqual(self.pre(f).returncode, 2)

    def test_fresh_read_still_passes(self):
        f = self.files / "read.txt"
        f.write_text("v1")
        r = self.run_hook(PRE, {"session_id": "s", "tool_name": "Read",
                                "tool_input": {"file_path": str(f)}})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.pre(f, sid="s").returncode, 0)

    def test_stamp_records_exact_post_write_mtime_ns(self):
        f = self.files / "ns.txt"
        f.write_text("v1")
        self.post_write(f, sid="S")
        stamped = self.write_stamps()["sessions"]["S"]["paths"][str(f.resolve())]
        self.assertEqual(stamped, f.stat().st_mtime_ns)

    def test_edit_chain_stays_fresh(self):
        f = self.files / "chain.txt"
        f.write_text("v1")
        self.post_write(f, tool="Edit")
        f.write_text("v2")  # our own next edit lands...
        self.post_write(f, tool="Edit")  # ...and is re-stamped post-success
        self.assertEqual(self.pre(f).returncode, 0)


if __name__ == "__main__":
    unittest.main()
