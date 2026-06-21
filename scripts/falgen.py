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

ENDPOINTS = {
    "fill": "fal-ai/flux-pro/v1/fill",
    "kontext": "fal-ai/flux-pro/kontext",
    "flux2edit": "fal-ai/flux-2-pro/edit",
    "eraser": "fal-ai/bria/eraser",
}


def load_key():
    k = os.environ.get("FAL_KEY")
    if k:
        return k
    env = Path(__file__).resolve().parent.parent / ".secrets" / "fal.env"
    for line in env.read_text().splitlines():
        if line.startswith("FAL_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("no FAL_KEY")


def data_uri(img: Image.Image) -> str:
    b = io.BytesIO(); img.save(b, format="PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=list(ENDPOINTS))
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--prompt"); ap.add_argument("--prompt-file")
    ap.add_argument("--mask"); ap.add_argument("--mask-box"); ap.add_argument("--feather", type=int, default=24)
    ap.add_argument("--maxside", type=int, default=1024, help="resize longer side to this before sending")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--guidance", type=float, default=None)
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
    else:
        body = {"prompt": prompt, "image_url": data_uri(img), "output_format": "png", "num_images": 1}
    if a.seed is not None: body["seed"] = a.seed
    if a.guidance is not None: body["guidance_scale"] = a.guidance

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
