#!/usr/bin/env python3
"""run_sweep.py — W2 HARD-conditioning sweep on the hospital DOOR via fal flux-general.

Local, single-purpose runner for this experiment only (writes stay under
tasks/workflow-rebuild/wexp/flux-general/). Reuses scripts/_falcommon.py
(load_fal_key, data_uri) exactly as falgen.py does.

BLOCKER (see report): the brief asked for a control_scale x ip_adapter_scale
sweep, but fal-ai/flux-general's live ip_adapters schema requires BOTH a
"path" (IP-Adapter weights repo) AND an "image_encoder_path" that could not be
resolved within the 2-attempt budget:
  probe 1 (falgen.py's shape, {image_url, scale}): 422 missing "path"
  probe 2 ({image_url, scale, path=XLabs-AI/flux-ip-adapter}): 422 missing
    "image_encoder_path"
Both probes returned 422 (pre-generation schema validation, no image produced,
no seed billed) — not counted as generation spend. Per the brief's hard rule
(max 2 attempts per failing criterion), ip_adapters is DROPPED from the sweep.
reference_strength is swept in its place as the achievable analog of the
requested per-ref-weight axis (still varies HOW HARD the style reference is
enforced), keeping 6 runs total and reusing the same style/medium reference
image via reference_image_url. control_loras (the actual ControlNet-class
ip_adapter-analog ask) is unaffected and is the primary axis under test.

Usage:
  python3 run_sweep.py --dry-run     # print all 6 payloads, no spend
  python3 run_sweep.py               # execute all 6 live fal calls
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests
from PIL import Image

REPO = Path(__file__).resolve().parents[4]
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
from _falcommon import load_fal_key, data_uri  # noqa: E402

GEOM = REPO / "tasks/marriott-hospital/geometry/v3"
HANDLE = REPO / "tasks/workflow-rebuild/round2/handle"
OUTDIR = Path(__file__).resolve().parent

CONTROL_IMAGE = GEOM / "door-control.png"
REF_IMAGE = HANDLE / "01-medium_ref.png"

PROMPT = (
    "storybook watercolor children's hospital facade, blue dome, "
    "monumental arched blue double doors filling the entire arched portal, "
    "doors closed, teddy in upper window, white background, no text"
)

CONTROL_SCALES = [0.35, 0.5, 0.7]
REF_STRENGTHS = [0.5, 0.8]
IMAGE_SIZE = {"width": 832, "height": 1184}
ENDPOINT = "fal-ai/flux-general"
CONTROL_LORA_PATH = "https://huggingface.co/black-forest-labs/FLUX.1-Canny-dev-lora/resolve/main/flux1-canny-dev-lora.safetensors"


def build_body(control_scale: float, ref_strength: float, dry: bool) -> dict:
    def img(p: Path) -> str:
        if dry:
            return str(p)
        return data_uri(Image.open(p).convert("RGB"))

    return {
        "prompt": PROMPT,
        "image_size": IMAGE_SIZE,
        "output_format": "png",
        "num_images": 1,
        "control_loras": [{
            "path": CONTROL_LORA_PATH,
            "control_image_url": img(CONTROL_IMAGE),
            "scale": control_scale,
            "preprocess": "None",
        }],
        "reference_image_url": img(REF_IMAGE),
        "reference_strength": ref_strength,
        "enable_safety_checker": False,
    }


def run_name(control_scale: float, ref_strength: float) -> str:
    return f"cs{control_scale:.2f}_rs{ref_strength:.2f}".replace(".", "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    runs = [(cs, rs) for cs in CONTROL_SCALES for rs in REF_STRENGTHS]
    print(f"{len(runs)} runs planned", file=sys.stderr)

    if a.dry_run:
        for cs, rs in runs:
            body = build_body(cs, rs, dry=True)
            print(json.dumps({"name": run_name(cs, rs), "endpoint": ENDPOINT, "arguments": body}, indent=2))
        return 0

    key = load_fal_key()
    url = f"https://fal.run/{ENDPOINT}"
    results = []
    for cs, rs in runs:
        name = run_name(cs, rs)
        out_path = OUTDIR / f"{name}.png"
        body = build_body(cs, rs, dry=False)
        print(f"[run_sweep] POST {name} control_scale={cs} ref_strength={rs} ...", file=sys.stderr)
        r = requests.post(url, headers={"Authorization": f"Key {key}", "Content-Type": "application/json"},
                           json=body, timeout=300)
        if r.status_code != 200:
            print(f"ERROR {name}: {r.status_code} {r.text[:600]}", file=sys.stderr)
            results.append({"name": name, "control_scale": cs, "ref_strength": rs, "error": r.text[:600]})
            continue
        j = r.json()
        imgs = j.get("images") or ([j["image"]] if j.get("image") else [])
        if not imgs:
            print(f"ERROR {name}: no images in response: {str(j)[:400]}", file=sys.stderr)
            results.append({"name": name, "control_scale": cs, "ref_strength": rs, "error": "no images"})
            continue
        out_url = imgs[0]["url"] if isinstance(imgs[0], dict) else imgs[0]
        data = requests.get(out_url, timeout=120).content
        out_path.write_bytes(data)
        seed = j.get("seed")
        record = {
            "name": name, "control_scale": cs, "ref_strength": rs, "seed": seed,
            "out": str(out_path), "endpoint": ENDPOINT,
            "prompt": PROMPT, "image_size": IMAGE_SIZE,
        }
        (out_path.with_suffix(out_path.suffix + ".artifact.json")).write_text(json.dumps(record, indent=2) + "\n")
        results.append(record)
        print(f"[run_sweep] OK {name} -> {out_path}", file=sys.stderr)

    (OUTDIR / "sweep_results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
