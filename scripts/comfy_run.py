#!/usr/bin/env python3
"""Submit an API-format workflow to a running ComfyUI server, poll, fetch the PNG.

Talks to ComfyUI's HTTP API (POST /prompt, GET /history, GET /view). No websocket
needed — we poll /history until the prompt id appears, then download the SaveImage
output and copy it to --out.

Usage:
  comfy_run.py --workflow workflow.json --out raw.png [--server 127.0.0.1:8188] [--timeout 1200]
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
import urllib.parse
import shutil
from pathlib import Path


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--server", default="127.0.0.1:8188")
    ap.add_argument("--timeout", type=int, default=1800)
    a = ap.parse_args()

    base = f"http://{a.server}"
    wf = json.loads(a.workflow.read_text())
    t0 = time.time()
    resp = post_json(f"{base}/prompt", {"prompt": wf})
    pid = resp["prompt_id"]
    print(f"[comfy_run] queued prompt {pid}")

    out_img = None
    while time.time() - t0 < a.timeout:
        hist = get_json(f"{base}/history/{pid}")
        if pid in hist:
            status = hist[pid].get("status", {})
            outs = hist[pid].get("outputs", {})
            for node_id, node_out in outs.items():
                for img in node_out.get("images", []):
                    out_img = img
                    break
            if out_img:
                break
            if status.get("status_str") == "error":
                print("[comfy_run] ERROR:", json.dumps(status, indent=2)[:2000])
                return 1
        time.sleep(2)

    if not out_img:
        print(f"[comfy_run] TIMEOUT after {a.timeout}s, no output image")
        return 1

    q = urllib.parse.urlencode({"filename": out_img["filename"],
                                "subfolder": out_img.get("subfolder", ""),
                                "type": out_img.get("type", "output")})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(f"{base}/view?{q}", timeout=120) as r, open(a.out, "wb") as f:
        shutil.copyfileobj(r, f)
    print(f"[comfy_run] saved {a.out}  ({time.time()-t0:.0f}s total)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
