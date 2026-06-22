#!/usr/bin/env python3
"""automask.py — text-prompt -> tight binary mask via fal SAM 3 (fal-ai/sam-3/image).

Kills the #1 bottleneck: hand-eyeballing mask coordinates. Give the image + a phrase
("the yellow taxi", "TAXI roof sign") and get a clean white=region mask PNG, post-processed
for soft watercolor edges (threshold + morphological close + light feather), resized to the
input image. Pick a specific instance among many with --box (keep the mask whose center falls
inside the box) or --near (closest center).

Auth: FAL_KEY from .secrets/fal.env (same as falgen.py). Local image sent as base64 data URI.

Usage:
  python3 scripts/automask.py --image CTX.png --prompt "yellow taxi" --out mask.png \
      [--max-masks 5] [--box x0,y0,x1,y1] [--near x,y] [--close 5] [--dilate 8] [--feather 2] \
      [--overlay OV.png]
Exit 0 + prints mask bbox/score on success; exit 3 if no mask for the prompt.
"""
import argparse, base64, io, os, sys
from pathlib import Path
import requests
import numpy as np
from PIL import Image, ImageFilter
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gencache import cache_key, cache_get, cache_put
from _falcommon import load_fal_key as load_key, data_uri

ENDPOINT = "fal-ai/sam-3/image"


def box(s):
    return tuple(int(v) for v in s.split(","))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-masks", type=int, default=5)
    ap.add_argument("--box", help="x0,y0,x1,y1 px: keep mask whose center is inside this box")
    ap.add_argument("--near", help="x,y px: keep mask whose center is closest")
    ap.add_argument("--close", type=int, default=5, help="morphological close radius (px)")
    ap.add_argument("--dilate", type=int, default=0, help="extra dilate radius (px)")
    ap.add_argument("--feather", type=int, default=2)
    ap.add_argument("--overlay")
    ap.add_argument("--no-cache", action="store_true")
    a = ap.parse_args()

    img = Image.open(a.image).convert("RGB")
    W, H = img.size

    ckey = cache_key("sam3", a.image, a.prompt, a.max_masks, a.box or "", a.near or "",
                     a.close, a.dilate, a.feather)
    if not a.no_cache:
        hit = cache_get(ckey)
        if hit:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            import shutil; shutil.copy(hit, a.out)
            mb = np.asarray(Image.open(a.out).convert("L")) > 128
            if a.overlay:
                o = np.asarray(img).copy(); o[mb] = (o[mb]*0.45 + np.array([255,0,0])*0.55).astype("uint8")
                Image.fromarray(o).save(a.overlay)
            print(f"[automask] CACHE HIT '{a.prompt}' -> {a.out}  cover={int(mb.sum())}px (0 API calls)")
            return

    body = {"image_url": data_uri(img), "prompt": a.prompt,
            "max_masks": a.max_masks, "output_format": "png", "apply_mask": False}
    r = requests.post(f"https://fal.run/{ENDPOINT}",
                      headers={"Authorization": f"Key {load_key()}", "Content-Type": "application/json"},
                      json=body, timeout=180)
    if r.status_code != 200:
        print(f"ERROR {r.status_code}: {r.text[:500]}", file=sys.stderr); raise SystemExit(1)
    j = r.json()
    masks = j.get("masks") or []
    if not masks:
        print(f"no mask for prompt '{a.prompt}': {str(j)[:300]}", file=sys.stderr); raise SystemExit(3)
    boxes = j.get("boxes") or j.get("normalized_boxes") or []
    scores = j.get("scores") or [None] * len(masks)

    # choose instance
    idx = 0
    centers = []
    for bx in boxes:
        # boxes may be normalized [cx,cy,w,h]
        cx, cy = bx[0], bx[1]
        if cx <= 1.0 and cy <= 1.0:
            cx, cy = cx * W, cy * H
        centers.append((cx, cy))
    if a.box and centers:
        x0, y0, x1, y1 = box(a.box)
        cand = [i for i, (cx, cy) in enumerate(centers) if x0 <= cx <= x1 and y0 <= cy <= y1]
        if cand:
            idx = max(cand, key=lambda i: (scores[i] or 0))
    elif a.near and centers:
        nx, ny = box(a.near)
        idx = min(range(len(centers)), key=lambda i: (centers[i][0]-nx)**2 + (centers[i][1]-ny)**2)
    elif scores and scores[0] is not None:
        idx = max(range(len(masks)), key=lambda i: (scores[i] or 0))

    mdata = requests.get(masks[idx]["url"], timeout=60).content
    m = Image.open(io.BytesIO(mdata)).convert("L").resize((W, H), Image.LANCZOS)
    arr = np.asarray(m)
    binm = (arr > 128).astype("uint8") * 255
    mm = Image.fromarray(binm, "L")
    if a.close > 0:
        k = a.close * 2 + 1
        mm = mm.filter(ImageFilter.MaxFilter(k)).filter(ImageFilter.MinFilter(k))
    if a.dilate > 0:
        mm = mm.filter(ImageFilter.MaxFilter(a.dilate * 2 + 1))
    if a.feather > 0:
        mm = mm.filter(ImageFilter.GaussianBlur(a.feather))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    mm.save(a.out)
    if not a.no_cache:
        cache_put(ckey, a.out)

    mb = np.asarray(mm) > 128
    ys, xs = np.where(mb)
    bb = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())) if len(xs) else None
    print(f"[automask] '{a.prompt}' -> {a.out}  n_masks={len(masks)} picked={idx} "
          f"score={scores[idx] if scores else '?'} mask_bbox={bb} cover={int(mb.sum())}px")
    if a.overlay:
        o = np.asarray(img).copy(); o[mb] = (o[mb]*0.45 + np.array([255,0,0])*0.55).astype("uint8")
        Image.fromarray(o).save(a.overlay)
        print(f"  overlay -> {a.overlay}")


if __name__ == "__main__":
    main()
