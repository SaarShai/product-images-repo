#!/usr/bin/env python3
"""esrgan_upscale.py — FREE local ML upscaler (Real-ESRGAN x4), any aspect ratio.

Fills the gap the fal clarity upscaler leaves: clarity caps output ~2.5-3 MP so
tall panels top out ~1040x2560; Real-ESRGAN tiles internally and has no aspect/MP
limit, so it takes the narrow panels to true 4x with no seams. Detail is
model-hallucinated sharpening (not a creative repaint) — geometry/style preserved.

Run in the gen venv (has torch + realesrgan + patched basicsr):
  .venv-gen/bin/python scripts/esrgan_upscale.py --image IN.png --out OUT.png \
      [--scale 4] [--tile 512] [--device cpu|mps] [--denoise 0.5]

First run downloads RealESRGAN_x4plus.pth (~64MB) into ~/models-gen/esrgan/.
"""
from __future__ import annotations
import argparse, sys, urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

MODELS = {
    "x4plus": ("RealESRGAN_x4plus.pth",
               "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"),
    "anime":  ("RealESRGAN_x4plus_anime_6B.pth",
               "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth"),
}


def fetch(model_key: str) -> Path:
    name, url = MODELS[model_key]
    dst = Path.home() / "models-gen" / "esrgan" / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        print(f"[esrgan] downloading {name} ...", file=sys.stderr)
        urllib.request.urlretrieve(url, dst)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=float, default=4.0, help="final outscale")
    ap.add_argument("--tile", type=int, default=512, help="0=whole image; else tile size (avoids OOM on tall panels)")
    ap.add_argument("--device", default="cpu", choices=["cpu", "mps"],
                    help="realesrgan MPS support is spotty; cpu is the safe default")
    ap.add_argument("--model", default="x4plus", choices=list(MODELS))
    ap.add_argument("--denoise", type=float, default=1.0, help="dni strength for x4plus (0-1)")
    a = ap.parse_args()

    import torch
    from realesrgan import RealESRGANer
    from basicsr.archs.rrdbnet_arch import RRDBNet

    nb = 6 if a.model == "anime" else 23
    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=nb, num_grow_ch=32, scale=4)
    dev = torch.device(a.device)
    up = RealESRGANer(scale=4, model_path=str(fetch(a.model)), model=model,
                      tile=a.tile, tile_pad=10, pre_pad=0, half=False, device=dev)

    img = np.array(Image.open(a.image).convert("RGB"))[:, :, ::-1]  # RGB->BGR for realesrgan
    out, _ = up.enhance(img, outscale=a.scale)
    Image.fromarray(out[:, :, ::-1]).save(a.out)  # BGR->RGB
    h, w = out.shape[:2]
    print(f"[esrgan] {a.model} {a.device} -> {a.out}  {w}x{h}")


if __name__ == "__main__":
    main()
