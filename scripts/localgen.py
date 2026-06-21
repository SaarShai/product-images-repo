#!/usr/bin/env python3
"""localgen.py — LOCAL masked inpaint on Apple Silicon (MPS) via diffusers SDXL.

Mirrors subgen.py's role but FREE + LOCAL + true masked inpaint (only the masked region
changes) + optional ControlNet (geometry lock) + watercolor LoRA + IP-Adapter (style from a
reference image). Run inside the gen venv: .venv-gen/bin/python scripts/localgen.py ...

Mask convention (diffusers): WHITE = repaint, BLACK = keep. Build from --mask-box or --mask.

Example:
  .venv-gen/bin/python scripts/localgen.py \
    --image tasks/fairy-fix/work/ctx-crop.png --out tasks/fairy-fix/sub/LOC1.raw.png \
    --prompt-file tasks/fairy-fix/work/prompt-fairy-user.md \
    --mask-box 150,120,670,800 --feather 24 --size 1024x1024 \
    --base diffusers/stable-diffusion-xl-1.0-inpainting-0.1 \
    --lora ~/models-gen/loras/watercolor_style_lora_sdxl.safetensors --lora-scale 0.9 \
    --ip-image tasks/fairy-fix/work/ctx-crop.png --ip-scale 0.5 \
    --strength 0.99 --steps 30 --guidance 6.0 --seed 0
"""
import argparse, os
from pathlib import Path
import torch
from PIL import Image, ImageDraw, ImageFilter

IPDIR = os.path.expanduser("~/models-gen/ipadapter")


def box(s): return tuple(int(v) for v in s.split(","))


def build_mask(W, H, mb, feather):
    m = Image.new("L", (W, H), 0)
    if mb:
        x0, y0, x1, y1 = box(mb)
        ImageDraw.Draw(m).rectangle([x0, y0, x1, y1], fill=255)  # white = repaint
        if feather > 0:
            m = m.filter(ImageFilter.GaussianBlur(feather))
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--prompt"); ap.add_argument("--prompt-file")
    ap.add_argument("--neg", default="ugly, deformed hands, extra fingers, melted, blurry, lowres, glossy, 3d render, photo, anime, vector, text, watermark")
    ap.add_argument("--mask"); ap.add_argument("--mask-box"); ap.add_argument("--feather", type=int, default=24)
    ap.add_argument("--size", default="1024x1024")
    ap.add_argument("--base", default="diffusers/stable-diffusion-xl-1.0-inpainting-0.1")
    ap.add_argument("--lora"); ap.add_argument("--lora-scale", type=float, default=0.9)
    ap.add_argument("--ip-image"); ap.add_argument("--ip-scale", type=float, default=0.5)
    ap.add_argument("--controlnet"); ap.add_argument("--control-image"); ap.add_argument("--control-scale", type=float, default=0.6)
    ap.add_argument("--strength", type=float, default=0.99)
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--guidance", type=float, default=6.0)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    prompt = a.prompt or (Path(a.prompt_file).read_text() if a.prompt_file else "")
    W, H = (int(x) for x in a.size.split("x"))
    dtype = torch.float16
    dev = "mps" if torch.backends.mps.is_available() else "cpu"

    init = Image.open(a.image).convert("RGB").resize((W, H), Image.LANCZOS)
    mask = (Image.open(a.mask).convert("L").resize((W, H)) if a.mask
            else build_mask(W, H, a.mask_box, a.feather))

    common = dict(torch_dtype=dtype, variant="fp16", use_safetensors=True)
    if a.controlnet:
        from diffusers import StableDiffusionXLControlNetInpaintPipeline, ControlNetModel
        cn = ControlNetModel.from_pretrained(a.controlnet, torch_dtype=dtype)
        try:
            pipe = StableDiffusionXLControlNetInpaintPipeline.from_pretrained(a.base, controlnet=cn, **common)
        except Exception:
            pipe = StableDiffusionXLControlNetInpaintPipeline.from_pretrained(a.base, controlnet=cn, torch_dtype=dtype, use_safetensors=True)
    else:
        from diffusers import AutoPipelineForInpainting
        try:
            pipe = AutoPipelineForInpainting.from_pretrained(a.base, **common)
        except Exception:
            pipe = AutoPipelineForInpainting.from_pretrained(a.base, torch_dtype=dtype, use_safetensors=True)

    pipe = pipe.to(dev)
    pipe.set_progress_bar_config(disable=True)

    if a.lora:
        pipe.load_lora_weights(os.path.expanduser(a.lora))
        pipe.fuse_lora(lora_scale=a.lora_scale)

    ip_kw = {}
    if a.ip_image:
        pipe.load_ip_adapter(IPDIR, subfolder="sdxl_models",
                             weight_name="ip-adapter-plus_sdxl_vit-h.safetensors",
                             image_encoder_folder=os.path.join(IPDIR, "models", "image_encoder"))
        pipe.set_ip_adapter_scale(a.ip_scale)
        ip_kw["ip_adapter_image"] = Image.open(a.ip_image).convert("RGB").resize((W, H), Image.LANCZOS)

    if a.controlnet:
        ctrl = Image.open(a.control_image or a.image).convert("RGB").resize((W, H), Image.LANCZOS)
        ip_kw["control_image"] = ctrl
        ip_kw["controlnet_conditioning_scale"] = a.control_scale

    g = torch.Generator(device="cpu").manual_seed(a.seed)
    out = pipe(prompt=prompt, negative_prompt=a.neg, image=init, mask_image=mask,
               strength=a.strength, num_inference_steps=a.steps, guidance_scale=a.guidance,
               width=W, height=H, generator=g, **ip_kw).images[0]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    out.save(a.out)
    print(f"[localgen] OK -> {a.out}  base={a.base} lora={bool(a.lora)} ip={bool(a.ip_image)} cn={bool(a.controlnet)} dev={dev}")


if __name__ == "__main__":
    main()
