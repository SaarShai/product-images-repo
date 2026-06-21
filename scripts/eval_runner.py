#!/usr/bin/env python3
"""eval_runner.py — regression harness for the edit pipeline. Runs the gate cases in
tasks/improve/eval/manifest.json and reports PASS/FAIL. Deterministic + free by default
(skips live/API cases unless --live). Exit nonzero if any case fails — wire into CI / pre-commit.

Run:  python3 scripts/eval_runner.py [--manifest path] [--live]
"""
import argparse, json, subprocess, sys
from pathlib import Path

R = Path(__file__).resolve().parent
ROOT = R.parent
PY = sys.executable


def sh(cmd):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, cwd=ROOT)


def case_mask_check(c):
    cmd = [PY, R/"mask_check.py", "--image", c["image"], "--target", c.get("target", "nonwhite"),
           "--region", c["region"], "--min-contain", c.get("min_contain", 0.85),
           "--max-leak", c.get("max_leak", 0.65)]
    cmd += ["--mask", c["mask"]] if c.get("mask") else ["--mask-box", c["mask_box"]]
    rc = sh(cmd).returncode
    got = "PASS" if rc == 0 else "FAIL"
    return got == c["expect"], f"got {got}, expect {c['expect']}"


def case_compose_gate(c):
    out = ROOT / "tasks/improve/eval/_tmp_compose.png"
    r = sh([PY, R/"compose_fairy.py", "--orig", c["orig"], "--regen", c["regen"], "--out", out,
            "--crop", c["crop"], "--mask", c["mask"], "--diffmask", "--diff-thresh", "28",
            "--diff-close", "5", "--diff-dilate", "3", "--diff-feather", "3"])
    line = [l for l in r.stdout.splitlines() if "OUTSIDE-MASK" in l]
    if not line:
        return False, "no gate line"
    ok = f"outside_max_delta={c.get('expect_outside_delta',0)}" in line[0]
    return ok, line[0].strip()


def case_cmd(c):
    r = subprocess.run(c["cmd"], capture_output=True, text=True, cwd=ROOT, shell=isinstance(c["cmd"], str))
    want = c.get("expect_exit", 0)
    return r.returncode == want, f"exit {r.returncode}, expect {want}"


HANDLERS = {"mask_check": case_mask_check, "compose_gate": case_compose_gate, "cmd": case_cmd}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="tasks/improve/eval/manifest.json")
    ap.add_argument("--live", action="store_true")
    a = ap.parse_args()
    cases = json.loads((ROOT / a.manifest).read_text())["cases"]
    npass = 0; fails = []
    for c in cases:
        if c.get("live") and not a.live:
            print(f"  SKIP (live)  {c['id']}"); continue
        h = HANDLERS.get(c["type"])
        if not h:
            print(f"  ?? unknown type {c['type']} ({c['id']})"); fails.append(c["id"]); continue
        try:
            ok, msg = h(c)
        except Exception as e:
            ok, msg = False, f"error: {e}"
        print(f"  {'PASS' if ok else 'FAIL'}  {c['id']}: {msg}")
        npass += ok
        if not ok:
            fails.append(c["id"])
    total = sum(1 for c in cases if not (c.get('live') and not a.live))
    print(f"\n[eval] {npass}/{total} passed" + (f"  FAILED: {fails}" if fails else "  ALL GREEN"))
    raise SystemExit(1 if fails else 0)


if __name__ == "__main__":
    main()
