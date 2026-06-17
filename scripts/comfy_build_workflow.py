#!/usr/bin/env python3
"""Build a ComfyUI API-format workflow JSON: SD1.5 + ControlNet(lineart) + IPAdapter(style).

The graph stacks two conditioning sources — the multi-node power ComfyUI is known for:
  * ControlNet (control_v11p_sd15_lineart) locks the EXACT panel geometry from a
    crisp SVG-derived line map (controlnet_conditioning strength ~1.0).
  * IPAdapter (ip-adapter_sd15 + CLIP-ViT-H) injects the watercolor style from the
    reference crops, WITHOUT dragging their geometry along.

Outputs an API-format dict (node-id -> {class_type, inputs}) suitable for POST /prompt.

Usage:
  comfy_build_workflow.py --control-map MAP.png --refs R1.png R2.png \
     --prompt "..." --width 512 --height 1736 --cond 1.0 --ip-weight 0.8 \
     --out workflow.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def build(args) -> dict:
    neg = args.negative_prompt
    g: dict = {}

    # 1. base checkpoint
    g["1"] = {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": args.ckpt}}
    # 2/3 prompts
    g["2"] = {"class_type": "CLIPTextEncode",
              "inputs": {"text": args.prompt, "clip": ["1", 1]}}
    g["3"] = {"class_type": "CLIPTextEncode",
              "inputs": {"text": neg, "clip": ["1", 1]}}
    # 4 empty latent at panel aspect
    g["4"] = {"class_type": "EmptyLatentImage",
              "inputs": {"width": args.width, "height": args.height, "batch_size": 1}}
    # 5 control map image
    g["5"] = {"class_type": "LoadImage", "inputs": {"image": args.control_map_name}}
    # 6 controlnet loader
    g["6"] = {"class_type": "ControlNetLoader",
              "inputs": {"control_net_name": args.controlnet}}
    # 7 controlnet apply (advanced: start/end + strength)
    g["7"] = {"class_type": "ControlNetApplyAdvanced",
              "inputs": {
                  "positive": ["2", 0],
                  "negative": ["3", 0],
                  "control_net": ["6", 0],
                  "image": ["5", 0],
                  "strength": args.cond,
                  "start_percent": 0.0,
                  "end_percent": 1.0,
              }}

    # --- IPAdapter style branch ---
    # 8 ipadapter model loader, 9 clip vision loader, 10 ref image(s)
    g["8"] = {"class_type": "IPAdapterModelLoader",
              "inputs": {"ipadapter_file": args.ipadapter}}
    g["9"] = {"class_type": "CLIPVisionLoader",
              "inputs": {"clip_name": args.clip_vision}}
    # batch the refs together so the style is averaged across both
    last_img_node = None
    for i, rn in enumerate(args.ref_names):
        nid = f"10_{i}"
        g[nid] = {"class_type": "LoadImage", "inputs": {"image": rn}}
        if last_img_node is None:
            last_img_node = nid
        else:
            bid = f"11_{i}"
            g[bid] = {"class_type": "ImageBatch",
                      "inputs": {"image1": [last_img_node, 0], "image2": [nid, 0]}}
            last_img_node = bid

    # 12 IPAdapterAdvanced: style transfer onto the base model
    g["12"] = {"class_type": "IPAdapterAdvanced",
               "inputs": {
                   "model": ["1", 0],
                   "ipadapter": ["8", 0],
                   "image": [last_img_node, 0],
                   "clip_vision": ["9", 0],
                   "weight": args.ip_weight,
                   "weight_type": args.ip_weight_type,
                   "combine_embeds": "concat",
                   "start_at": 0.0,
                   "end_at": 1.0,
                   "embeds_scaling": "V only",
               }}

    # 13 sampler — model from IPAdapter, conditioning from ControlNet
    g["13"] = {"class_type": "KSampler",
               "inputs": {
                   "model": ["12", 0],
                   "positive": ["7", 0],
                   "negative": ["7", 1],
                   "latent_image": ["4", 0],
                   "seed": args.seed,
                   "steps": args.steps,
                   "cfg": args.cfg,
                   "sampler_name": args.sampler,
                   "scheduler": args.scheduler,
                   "denoise": 1.0,
               }}
    # 14 decode, 15 save
    g["14"] = {"class_type": "VAEDecode",
               "inputs": {"samples": ["13", 0], "vae": ["1", 2]}}
    g["15"] = {"class_type": "SaveImage",
               "inputs": {"images": ["14", 0], "filename_prefix": args.prefix}}
    return g


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--control-map-name", required=True, help="filename in ComfyUI/input/")
    ap.add_argument("--ref-names", nargs="+", required=True, help="ref filenames in ComfyUI/input/")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--negative-prompt", default=(
        "blurry, low quality, jpeg artifacts, text, watermark, signature, frame, "
        "border, extra openings, deformed holes, photo, 3d render, cluttered"))
    ap.add_argument("--width", type=int, default=512)
    ap.add_argument("--height", type=int, default=1736)
    ap.add_argument("--cond", type=float, default=1.0)
    ap.add_argument("--ip-weight", type=float, default=0.8)
    ap.add_argument("--ip-weight-type", default="style transfer")
    ap.add_argument("--steps", type=int, default=26)
    ap.add_argument("--cfg", type=float, default=7.0)
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--sampler", default="dpmpp_2m")
    ap.add_argument("--scheduler", default="karras")
    ap.add_argument("--ckpt", default="v1-5-pruned-emaonly-fp16.safetensors")
    ap.add_argument("--controlnet", default="control_v11p_sd15_lineart_fp16.safetensors")
    ap.add_argument("--ipadapter", default="ip-adapter_sd15.safetensors")
    ap.add_argument("--clip-vision", default="CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors")
    ap.add_argument("--prefix", default="CW1")
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    # attribute aliases used in build()
    a.control_map_name = a.control_map_name
    a.ref_names = a.ref_names
    g = build(a)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(g, indent=2))
    print(f"wrote {a.out}  ({len(g)} nodes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
