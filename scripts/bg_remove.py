#!/usr/bin/env python3
"""bg_remove.py — remove an image background to TRANSPARENT (RGBA PNG).

Default = FREE local BiRefNet via rembg (run with .venv-bg/bin/python). `--fal` uses the
hosted fal BiRefNet (instant, costs a call). `--model` picks the rembg model
(birefnet-general best for objects/edges; birefnet-portrait for people; u2net = lighter).

Usage:
  .venv-bg/bin/python scripts/bg_remove.py --image IN.png --out OUT.png
  python3 scripts/bg_remove.py --image IN.png --out OUT.png --fal     # hosted
"""
import argparse, base64, io, os, sys
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _falcommon import load_fal_key, data_uri


def defringe(rgba, erode_px, feather):
    """Kill the grey matte halo: erode the alpha inward past BiRefNet's dark boundary ring,
    then a sub-pixel feather for clean AA. The eroded edge lands on true foreground colour,
    so the fringe goes from dark-grey [~90,80,75] to the real edge tint — no halo on any bg."""
    import numpy as np
    from PIL import ImageFilter
    if erode_px <= 0:
        return rgba
    arr = np.asarray(rgba).copy()
    al = Image.fromarray(arr[:, :, 3])
    al = al.filter(ImageFilter.MinFilter(erode_px * 2 + 1))
    if feather > 0:
        al = al.filter(ImageFilter.GaussianBlur(feather))
    arr[:, :, 3] = np.asarray(al)
    return Image.fromarray(arr, "RGBA")


def local(img_path, out_path, model, erode_px=2, feather=0.8, matting=False):
    from rembg import remove, new_session  # rembg downloads the model on first use
    session = new_session(model)
    img = Image.open(img_path).convert("RGBA")
    if matting:  # rembg's own alpha-matting decontamination (slower, no silhouette shrink)
        out = remove(img, session=session, alpha_matting=True,
                     alpha_matting_foreground_threshold=240,
                     alpha_matting_background_threshold=10, alpha_matting_erode_size=10)
    else:
        out = remove(img, session=session)  # returns RGBA with bg alpha=0
    # always edge-crisp: erode past the semi-transparent matte ring so NO grey/light halo
    # survives on any background (matting decontaminates colour; erode removes the residual ring)
    out = defringe(out, erode_px, feather)
    out.save(out_path)


def via_fal(img_path, out_path):
    import requests
    key = load_fal_key()
    uri = data_uri(Image.open(img_path).convert("RGB"))
    r = requests.post("https://fal.run/fal-ai/birefnet",
                      headers={"Authorization": f"Key {key}", "Content-Type": "application/json"},
                      json={"image_url": uri}, timeout=180)
    if r.status_code != 200:
        print(f"ERROR {r.status_code}: {r.text[:400]}", file=sys.stderr); raise SystemExit(1)
    j = r.json()
    u = (j.get("image") or {}).get("url") or (j.get("images") or [{}])[0].get("url")
    if not u:
        print(f"no image in response: {str(j)[:300]}", file=sys.stderr); raise SystemExit(1)
    Path(out_path).write_bytes(requests.get(u, timeout=120).content)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="bria-rmbg")  # RMBG SOTA: best inner-gaps + keeps wings (beats birefnet-general)
    ap.add_argument("--fal", action="store_true")
    ap.add_argument("--erode", type=int, default=2, help="defringe: erode alpha N px to kill grey halo (0=off)")
    ap.add_argument("--feather", type=float, default=0.8, help="AA feather after erode")
    ap.add_argument("--matting", action="store_true", help="use rembg alpha-matting instead of erode defringe")
    ap.add_argument("--check", action="store_true",
                    help="also write OUT_magenta.png (cutout over magenta) — ALWAYS eyeball this, "
                         "not the editor's grey backing, before trusting the cut [[clarity-grey-edge-halo]]")
    a = ap.parse_args()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    if a.fal:
        via_fal(a.image, a.out); engine = "fal-birefnet"
    else:
        local(a.image, a.out, a.model, a.erode, a.feather, a.matting)
        engine = f"local-rembg:{a.model}" + ("+matting" if a.matting else f"+defringe{a.erode}")
    # report transparency stats so we can verify it actually cut the bg
    im = Image.open(a.out).convert("RGBA")
    import numpy as np
    al = np.asarray(im)[:, :, 3]
    transp = (al < 16).mean() * 100
    msg = f"[bg_remove] {engine} -> {a.out}  size={im.size}  transparent={transp:.1f}% of pixels"
    if a.check:  # residual bg / eaten gaps are invisible on grey but pop on magenta
        mag = Image.new("RGBA", im.size, (255, 0, 255, 255)); mag.alpha_composite(im)
        chk = str(Path(a.out).with_name(Path(a.out).stem + "_magenta.png"))
        mag.convert("RGB").save(chk)
        msg += f"\n[bg_remove] CHECK composite -> {chk}  (eyeball this on magenta)"
    print(msg)


if __name__ == "__main__":
    main()
