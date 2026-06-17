#!/usr/bin/env python3
"""Local Stable Diffusion + ControlNet generation, MPS-first.

Conditions SD generation on an exact edge/line control map so the geometry is
structurally locked (vs gpt-image/Nano-Banana which drift). Built on the stock
diffusers StableDiffusionControlNetPipeline example, adapted for Apple MPS.

Examples
--------
Lineart ControlNet on SD1.5, geometry-aspect canvas:
  scripts/controlnet_gen.py \
    --control-map .../controlmap-lineart-512.png \
    --controlnet lllyasviel/control_v11p_sd15_lineart \
    --base-model runwayml/stable-diffusion-v1-5 \
    --prompt "watercolor space control-panel ..." \
    --cond-scale 1.2 --steps 28 \
    --out tasks/.../experiments/CN1-controlnet/raw.png

Canny ControlNet:
  --controlnet lllyasviel/sd-controlnet-canny  (feed a canny-style map)

Notes
-----
* Device: MPS if available, else CPU. float32 by default (fp16 on MPS is buggy);
  pass --dtype float16 to try half precision.
* The control map is resized to (--width x --height); if --height 0 it is taken
  from the map's own aspect, rounded to a multiple of 8.
* The output canvas == control-map size, so a panel that fills the frame lands
  exactly on the SVG lines that svg_geometry_check.py measures against.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import torch
from PIL import Image


def pick_device(requested: str) -> str:
    if requested != "auto":
        return requested
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--control-map", required=True, type=Path)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--negative-prompt", default=(
        "blurry, low quality, text, watermark, signature, frame, border, "
        "extra openings, deformed holes, photo, 3d render"))
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--controlnet", default="lllyasviel/control_v11p_sd15_lineart")
    ap.add_argument("--base-model", default="runwayml/stable-diffusion-v1-5")
    ap.add_argument("--steps", type=int, default=28)
    ap.add_argument("--cond-scale", type=float, default=1.2,
                    help="controlnet_conditioning_scale (geometry lock strength)")
    ap.add_argument("--guidance", type=float, default=7.0)
    ap.add_argument("--width", type=int, default=0, help="0 = control-map width")
    ap.add_argument("--height", type=int, default=0, help="0 = control-map height")
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--device", default="auto", choices=["auto", "mps", "cpu", "cuda"])
    ap.add_argument("--dtype", default="float32", choices=["float32", "float16"])
    ap.add_argument("--guess-mode", action="store_true",
                    help="ControlNet guess mode (let CN steer even without strong prompt)")
    a = ap.parse_args()

    # Imported here so --help is instant and import warnings don't precede usage errors.
    from diffusers import (ControlNetModel, StableDiffusionControlNetPipeline,
                           UniPCMultistepScheduler)

    device = pick_device(a.device)
    dtype = torch.float16 if a.dtype == "float16" else torch.float32
    print(f"[controlnet_gen] device={device} dtype={a.dtype} controlnet={a.controlnet} base={a.base_model}")

    control = Image.open(a.control_map).convert("RGB")
    W = a.width or control.width
    H = a.height or control.height
    W -= W % 8
    H -= H % 8
    if (W, H) != control.size:
        control = control.resize((W, H), Image.LANCZOS)
    print(f"[controlnet_gen] canvas={W}x{H} (aspect {W/H:.4f})")

    t0 = time.time()
    controlnet = ControlNetModel.from_pretrained(a.controlnet, torch_dtype=dtype)
    pipe = StableDiffusionControlNetPipeline.from_pretrained(
        a.base_model, controlnet=controlnet, torch_dtype=dtype, safety_checker=None)
    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)
    pipe = pipe.to(device)
    pipe.enable_attention_slicing()
    print(f"[controlnet_gen] models loaded in {time.time()-t0:.1f}s")

    gen = torch.Generator(device="cpu").manual_seed(a.seed)
    t1 = time.time()
    image = pipe(
        prompt=a.prompt,
        negative_prompt=a.negative_prompt,
        image=control,
        num_inference_steps=a.steps,
        guidance_scale=a.guidance,
        controlnet_conditioning_scale=a.cond_scale,
        guess_mode=a.guess_mode,
        width=W,
        height=H,
        generator=gen,
    ).images[0]
    dt = time.time() - t1

    a.out.parent.mkdir(parents=True, exist_ok=True)
    image.save(a.out)
    print(f"[controlnet_gen] inference {dt:.1f}s ({dt/max(1,a.steps):.2f}s/step) -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
