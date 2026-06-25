#!/usr/bin/env python3
"""falgen.py — image edit via fal.ai (Flux Fill masked inpaint / Flux Kontext instruction edit / Flux.2 edit).

The high-ceiling engine: hosted Flux on real GPUs. Reads FAL_KEY from .secrets/fal.env.
Auth scheme is `Key <id:secret>` (NOT Bearer). Local images are sent as base64 data URIs.

Modes:
  fill      : fal-ai/flux-pro/v1/fill  — masked inpaint (mask white=repaint). Best for "change nothing else".
  kontext   : fal-ai/flux-pro/kontext  — instruction edit (whole image; strong consistency).
  flux2edit : fal-ai/flux-2-pro/edit   — reference-based edit (prose + up to 9 refs).

Usage (fill):
  python3 scripts/falgen.py --mode fill --image CROP.png --out OUT.png --prompt-file P.md \
      --mask-box 100,100,420,550 --feather 24
Usage (kontext):
  python3 scripts/falgen.py --mode kontext --image CROP.png --out OUT.png --prompt "redraw only the fairy ..."
"""
import argparse, base64, io, os, sys
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFilter
from _falcommon import load_fal_key as load_key, data_uri

ENDPOINTS = {
    "fill": "fal-ai/flux-pro/v1/fill",
    "kontext": "fal-ai/flux-pro/kontext",
    "flux2edit": "fal-ai/flux-2-pro/edit",
    "i2i": "fal-ai/flux/dev/image-to-image",   # low-strength img2img: keep structure, restyle. --strength (0=keep, 1=ignore)
    "eraser": "fal-ai/bria/eraser",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=list(ENDPOINTS))
    ap.add_argument("--image", required=True)
    ap.add_argument("--refs", nargs="*", default=[], help="extra reference images (flux2edit only; appended to image_urls)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--prompt"); ap.add_argument("--prompt-file")
    ap.add_argument("--mask"); ap.add_argument("--mask-box"); ap.add_argument("--feather", type=int, default=24)
    ap.add_argument("--maxside", type=int, default=1024, help="resize longer side to this before sending")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--guidance", type=float, default=None)
    ap.add_argument("--strength", type=float, default=None, help="i2i denoise strength (low=keep structure, e.g. 0.3)")
    ap.add_argument("--cache", action="store_true", help="reuse cached result for identical deterministic calls")
    a = ap.parse_args()

    prompt = a.prompt or (Path(a.prompt_file).read_text() if a.prompt_file else "")
    img = Image.open(a.image).convert("RGB")
    if a.maxside:
        w, h = img.size; s = a.maxside / max(w, h)
        if s < 1:
            img = img.resize((round(w * s), round(h * s)), Image.LANCZOS)
    W, H = img.size

    # cache only deterministic calls: eraser (no seed) or an explicit seed was given
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent))
    from gencache import cache_key, cache_get, cache_put
    deterministic = (a.mode == "eraser") or (a.seed is not None)
    ckey = None
    if a.cache and deterministic:
        mb = Path(a.mask).read_bytes() if a.mask else (a.mask_box or "")
        ckey = cache_key(a.mode, a.image, prompt, mb, a.seed if a.seed is not None else "", a.guidance or "", a.maxside, a.feather)
        hit = cache_get(ckey)
        if hit:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            import shutil; shutil.copy(hit, a.out)
            print(f"[falgen] CACHE HIT mode={a.mode} -> {a.out} (0 API calls)"); return
    elif a.cache and not deterministic:
        print("[falgen] --cache ignored: non-deterministic call (set --seed to enable caching)", file=sys.stderr)

    if a.mode == "eraser":
        body = {"image_url": data_uri(img)}  # bria eraser: image_url + mask_url, no prompt
    elif a.mode == "flux2edit":
        # flux-2-pro/edit takes image_urls[] (up to 9 refs) + prose; resize refs to maxside
        def _ref(p):
            r = Image.open(p).convert("RGB")
            if a.maxside:
                w, h = r.size; s = a.maxside / max(w, h)
                if s < 1: r = r.resize((round(w * s), round(h * s)), Image.LANCZOS)
            return data_uri(r)
        body = {"prompt": prompt, "image_urls": [data_uri(img)] + [_ref(r) for r in a.refs],
                "output_format": "png", "num_images": 1}
    else:
        body = {"prompt": prompt, "image_url": data_uri(img), "output_format": "png", "num_images": 1}
    if a.mode == "i2i" and a.strength is not None: body["strength"] = a.strength
    if a.seed is not None: body["seed"] = a.seed
    if a.guidance is not None: body["guidance_scale"] = a.guidance
    # fal Flux safety checker false-flags innocuous content (e.g. skin/fairy hands) and
    # returns a BLANK BLACK image. Disable it + max tolerance so legit edits aren't blanked.
    body["enable_safety_checker"] = False
    if a.mode != "i2i":  # safety_tolerance is a flux-pro param; flux/dev i2i rejects it
        body["safety_tolerance"] = "5" if a.mode == "flux2edit" else "6"  # flux-2-pro validates 1-5; kontext/fill accept 6

    if a.mode in ("fill", "eraser"):
        if a.mask:
            m = Image.open(a.mask).convert("L").resize((W, H))
        else:
            m = Image.new("L", (W, H), 0)
            if a.mask_box:
                x0, y0, x1, y1 = (int(v) for v in a.mask_box.split(","))
                ImageDraw.Draw(m).rectangle([x0, y0, x1, y1], fill=255)  # white=repaint/erase
                if a.feather > 0: m = m.filter(ImageFilter.GaussianBlur(a.feather))
        body["mask_url"] = data_uri(m.convert("RGB"))

    key = load_key()
    url = f"https://fal.run/{ENDPOINTS[a.mode]}"
    r = requests.post(url, headers={"Authorization": f"Key {key}", "Content-Type": "application/json"},
                      json=body, timeout=300)
    if r.status_code != 200:
        print(f"ERROR {r.status_code}: {r.text[:600]}", file=sys.stderr); raise SystemExit(1)
    j = r.json()
    imgs = j.get("images") or ([j["image"]] if j.get("image") else [])
    if not imgs:
        print(f"no images in response: {str(j)[:400]}", file=sys.stderr); raise SystemExit(1)
    out_url = imgs[0]["url"] if isinstance(imgs[0], dict) else imgs[0]
    data = requests.get(out_url, timeout=120).content
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_bytes(data)
    if ckey is not None:
        cache_put(ckey, a.out)
    print(f"[falgen] OK mode={a.mode} -> {a.out}  sent={W}x{H} seed={j.get('seed')}")


if __name__ == "__main__":
    main()
