#!/usr/bin/env python3
"""falref_apply.py — reference-locked element edit via fal Flux.2-pro edit.

Crops a region from the source illustration and sends it to fal-ai/flux-2-pro/edit with
image_urls = [region_to_edit, character_reference...] so the redrawn element MATCHES an
approved reference design (cross-instance consistency). Output = the regenerated region;
composite back with compose_fairy.py --diffmask.

Usage:
  python3 scripts/falref_apply.py --src door-v5.png --crop 60,300,560,900 \
     --ref work/ref-X3-fairy.png --prompt-file work/prompt-reflock.md --out sub/F-TL.raw.png
"""
import argparse, base64, io, sys
from pathlib import Path
import requests
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _falcommon import load_fal_key as load_key, data_uri as du


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--crop", required=True, help="x0,y0,x1,y1 region to edit")
    ap.add_argument("--ref", action="append", default=[], help="character reference image(s)")
    ap.add_argument("--prompt"); ap.add_argument("--prompt-file")
    ap.add_argument("--out", required=True)
    ap.add_argument("--endpoint", default="fal-ai/flux-2-pro/edit")
    a = ap.parse_args()

    prompt = a.prompt or (Path(a.prompt_file).read_text() if a.prompt_file else "")
    x0, y0, x1, y1 = (int(v) for v in a.crop.split(","))
    region = Image.open(a.src).convert("RGB").crop((x0, y0, x1, y1))
    urls = [du(region)] + [du(Image.open(r).convert("RGB")) for r in a.ref]

    r = requests.post(f"https://fal.run/{a.endpoint}",
                      headers={"Authorization": f"Key {load_key()}", "Content-Type": "application/json"},
                      json={"image_urls": urls, "prompt": prompt}, timeout=360)
    if r.status_code != 200:
        print(f"ERROR {r.status_code}: {r.text[:400]}", file=sys.stderr); raise SystemExit(1)
    d = r.json()
    imgs = d.get("images") or ([d["image"]] if d.get("image") else [])
    if not imgs:
        print(f"no image: {str(d)[:400]}", file=sys.stderr); raise SystemExit(1)
    u = imgs[0]["url"] if isinstance(imgs[0], dict) else imgs[0]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_bytes(requests.get(u, timeout=120).content)
    print(f"[falref] OK {a.endpoint} crop={a.crop} refs={len(a.ref)} -> {a.out}")


if __name__ == "__main__":
    main()
