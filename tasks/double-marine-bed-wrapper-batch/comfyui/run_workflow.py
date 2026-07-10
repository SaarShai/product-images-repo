#!/usr/bin/env python3
"""Submit an API-format ComfyUI workflow JSON, poll history, print output paths.

Usage:
    python3 run_workflow.py <workflow.json> [--host 127.0.0.1] [--port 8199] [--timeout 600]
"""
import argparse
import json
import sys
import time
import urllib.request
import urllib.error


def post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(url):
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workflow")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", default="8199")
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()

    base = f"http://{args.host}:{args.port}"
    with open(args.workflow) as f:
        workflow = json.load(f)

    resp = post_json(f"{base}/prompt", {"prompt": workflow})
    prompt_id = resp.get("prompt_id")
    if not prompt_id:
        print("ERROR: no prompt_id in response:", resp, file=sys.stderr)
        sys.exit(1)
    print(f"Queued prompt_id={prompt_id}")

    deadline = time.time() + args.timeout
    while time.time() < deadline:
        try:
            hist = get_json(f"{base}/history/{prompt_id}")
        except urllib.error.URLError as e:
            print("poll error:", e, file=sys.stderr)
            time.sleep(2)
            continue
        if prompt_id in hist:
            entry = hist[prompt_id]
            status = entry.get("status", {})
            if status.get("completed") or status.get("status_str") == "success":
                outputs = entry.get("outputs", {})
                print("COMPLETED")
                for node_id, out in outputs.items():
                    for img in out.get("images", []):
                        fn = img.get("filename")
                        sub = img.get("subfolder", "")
                        typ = img.get("type", "output")
                        view_url = f"{base}/view?filename={fn}&subfolder={sub}&type={typ}"
                        print(f"OUTPUT node={node_id} filename={fn} subfolder={sub} type={typ} url={view_url}")
                sys.exit(0)
            if status.get("status_str") == "error":
                print("ERROR status:", json.dumps(status, indent=2), file=sys.stderr)
                sys.exit(2)
        time.sleep(2)
    print("TIMEOUT waiting for prompt", prompt_id, file=sys.stderr)
    sys.exit(3)


if __name__ == "__main__":
    main()
