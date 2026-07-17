#!/usr/bin/env python3
"""experiment-1 Stage-A driver (STANDALONE -- does NOT modify
scripts/localgen.py, which stays generic). Implements PARAMS.md's FROZEN
parameter card exactly: fp16 SDXL-inpaint + xinsir canny ControlNet + fused
watercolor LoRA + IP-Adapter-plus (STYLE-LAYER-ONLY routing, multi-ref
average) + VAE-fp32 decode + hard silhouette/hole composite.

Run (env var is REQUIRED by the card, set at the shell, never silently in
code):

  PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0 .venv-gen/bin/python \\
    tasks/geometry-adherence-solutions/experiment-1/scripts/gen_stage_a.py \\
    --arm P1 --seed 7 --steps 30 \\
    --out-dir tasks/geometry-adherence-solutions/experiment-1/runs/A-P1-s7

Cheap IP-Adapter embedding-shape probe (no full diffusion, still loads the
pipeline once):

  PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0 .venv-gen/bin/python \\
    tasks/geometry-adherence-solutions/experiment-1/scripts/gen_stage_a.py --shape-check
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
ROOT = EXP.parents[2]
sys.path.insert(0, str(HERE))
import build_assets as BA  # noqa: E402 (reuse rasterize_geometry for the hard composite)

ASSETS = EXP / "assets-640"
REFS = [
    ROOT / "tasks/geometry-evidentiary-princess-n02/refs/princess style 01.png",
    ROOT / "tasks/geometry-evidentiary-princess-n02/refs/princess style 02.png",
]
LORA = Path("/Users/za/models-gen/loras/watercolor_v1_sdxl.safetensors")
IPDIR = Path("/Users/za/models-gen/ipadapter")
BASE_MODEL = "diffusers/stable-diffusion-xl-1.0-inpainting-0.1"
CN_MODEL = "xinsir/controlnet-canny-sdxl-1.0"

# ---- PARAMS.md verbatim prompt --------------------------------------------
POSITIVE = ("watercolor children's book illustration of a fairytale princess castle, "
            "soft pastel washes on textured paper, gentle ink outlines, tall narrow "
            "vertical composition, airy, delicate, hand-painted")
NEGATIVE = ("photo, realistic, 3d render, glossy, text, words, signage, watermark, frame, "
            "border, clutter, people, oversaturated, heavy black outlines, vector, flat "
            "color blocks, sideways architecture, cropped main towers, floating fragments, "
            "duplicated buildings")

LORA_SCALE = 0.75
IP_ROUTING = {"up": {"block_0": [0.0, 0.55, 0.0]}}  # STYLE-LAYER-ONLY routing


def center_crop_square(im: Image.Image) -> Image.Image:
    w, h = im.size
    s = min(w, h)
    left = (w - s) // 2
    top = (h - s) // 2
    return im.crop((left, top, left + s, top + s))


def load_pipe():
    from diffusers import ControlNetModel, StableDiffusionXLControlNetInpaintPipeline

    dtype = torch.float16
    cn = ControlNetModel.from_pretrained(CN_MODEL, torch_dtype=dtype)
    pipe = StableDiffusionXLControlNetInpaintPipeline.from_pretrained(
        BASE_MODEL, controlnet=cn, torch_dtype=dtype, variant="fp16", use_safetensors=True)
    pipe.to("mps")
    # NOTE: VAE stays fp16 here (matches the rest of the pipe) -- casting it
    # to float32 THIS early breaks the pipeline's OWN internal VAE ENCODE
    # calls (masked-image latents, image latents), which run in fp16 space
    # before the denoising loop even starts (RuntimeError: Input type Half
    # and bias type float should be the same). The card's "VAE forced fp32
    # before decode" is applied at the actual decode call site in
    # generate(), which is where it's needed (fp16 VAE decode overflows on
    # MPS) and where it's safe (encode has already happened).
    pipe.set_progress_bar_config(disable=True)

    # card load order: LoRA -> fuse_lora(0.75) -> load_ip_adapter -> set_ip_adapter_scale(routing)
    pipe.load_lora_weights(str(LORA))
    pipe.fuse_lora(lora_scale=LORA_SCALE)

    pipe.load_ip_adapter(str(IPDIR), subfolder="sdxl_models",
                          weight_name="ip-adapter-plus_sdxl_vit-h.safetensors",
                          image_encoder_folder=str(IPDIR / "models" / "image_encoder"))
    pipe.set_ip_adapter_scale(IP_ROUTING)

    # DEVIATION FROM CARD (flagged, not silent): attention_slicing is NOT
    # enabled. `enable_attention_slicing()` wholesale-replaces EVERY attn
    # processor with plain `SlicedAttnProcessor` instances, which do not know
    # how to unpack the `(text_hidden_states, image_embeds)` TUPLE that
    # `process_encoder_hidden_states()` always builds once an IP-Adapter is
    # loaded (added_cond_kwargs has "image_embeds") -- crashes with
    # `AttributeError: 'tuple' object has no attribute 'shape'` deep inside
    # cross-attention, on EVERY layer, regardless of scale (incl. 0.0-scaled
    # layers outside the style-routing block). Tried BOTH orderings
    # (before/after load_ip_adapter): before -> `_convert_ip_adapter_attn_to_
    # diffusers` crashes instantiating SlicedAttnProcessor() with no
    # slice_size for non-cross-attn layers; after -> the tuple-unpack crash
    # above. This is a structural incompatibility between
    # `enable_attention_slicing()` and any loaded IP-Adapter in diffusers
    # 0.38's StableDiffusionXLControlNetInpaintPipeline, not a fixable
    # ordering bug. IP-Adapter (style transfer) is the card's core semantic
    # requirement; attention_slicing is a memory-management convenience --
    # kept OFF so the run can proceed at all. vae_slicing (does not touch
    # UNet attn processors) stays ON per the card; vae_tiling stays OFF.
    pipe.vae.enable_slicing()
    return pipe


def averaged_ip_embeds(pipe, ref_images, device):
    """Multi-ref for a SINGLE loaded IP-Adapter: encode each ref separately
    (the pipeline's own encode_image -- correct dtype/hidden-states for
    ip-adapter-plus), average the (positive, negative) embeddings, hand back
    via `ip_adapter_image_embeds` (diffusers 0.38's supported precomputed-
    embeds slot). See run_shape_check() / PARAMS.md Card note: the literal
    nested-list form `[[ref1, ref2]]` fed to `ip_adapter_image` is REJECTED
    by this pipeline for a single adapter (extra un-squeezed ref-count dim
    breaks the UNet cross-attention shape) -- diffusers batches multiple
    images for one adapter as an extra leading dim, it does not average
    them. Averaging is what this diffusers version actually supports for
    "multiple reference images -> one adapter"."""
    output_hidden_state = True  # ip-adapter-plus reads hidden_states[-2]
    pos_list, neg_list = [], []
    for im in ref_images:
        pos, neg = pipe.encode_image(im, device, 1, output_hidden_state)
        pos_list.append(pos)
        neg_list.append(neg)
    pos_avg = torch.stack(pos_list, dim=0).mean(dim=0)
    neg_avg = torch.stack(neg_list, dim=0).mean(dim=0)
    combined = torch.cat([neg_avg, pos_avg], dim=0)  # (negative, positive) -- prepare_ip_adapter_image_embeds chunk(2) convention
    # MultiIPAdapterImageProjection.forward requires [batch, num_images, seq, dim]
    # (4D) per adapter -- our multi-ref averaging already collapsed the 2 refs
    # into ONE representative embedding, so num_images=1 here (verified against
    # the diffusers 0.38 source, diffusers/models/embeddings.py
    # MultiIPAdapterImageProjection.forward's own shape[0]/shape[1] unpack).
    combined = combined.unsqueeze(1)
    return [combined]


def run_shape_check(pipe, device) -> int:
    refs = [center_crop_square(Image.open(p).convert("RGB")) for p in REFS]

    print("[shape-check] form A: nested list [[ref1, ref2]] via ip_adapter_image=...")
    try:
        embeds = pipe.prepare_ip_adapter_image_embeds([refs], None, device, 1, True)
        print(f"  ACCEPTED (shape check only, not used for gen): shapes={[tuple(e.shape) for e in embeds]}")
    except Exception as e:
        print(f"  REJECTED: {type(e).__name__}: {e}")

    print("[shape-check] form B: manually-averaged embeds via ip_adapter_image_embeds=...")
    try:
        embeds = averaged_ip_embeds(pipe, refs, device)
        print(f"  ACCEPTED: shapes={[tuple(e.shape) for e in embeds]}")
        print("  -> form B is what gen_stage_a.py actually uses for generation.")
    except Exception as e:
        print(f"  REJECTED: {type(e).__name__}: {e}")
    return 0


def hard_composite(img: Image.Image, arm: str, W: int, H: int) -> Image.Image:
    """Card: after decode, pixels outside silhouette_mask forced pure white;
    for arm P1 also force hole interiors pure white (by-construction
    guarantee). Socket/arch compositing is Stage C's job (composite_back.py),
    NOT done here."""
    silhouette, holes, st1_zone, socket_rect_px, socket_arch_mask, shapes, src_rect = BA.rasterize_geometry(W, H)
    arr = np.asarray(img.convert("RGB")).copy()
    sil_bool = np.asarray(silhouette) > 127
    arr[~sil_bool] = 255
    if arm == "P1":
        hol_bool = np.asarray(holes) > 127
        arr[hol_bool] = 255
    return Image.fromarray(arr)


def generate(pipe, arm, seed, steps, guidance, strength, cond_scale, cg_start, cg_end, device,
             control_image="control_canny.png", init_image=None):
    """init_image: Stage-A default None -> assets-640/init_canvas.png (neutral
    fill). Stage B passes a prior Stage-A gen.png here (img2img re-render at
    strength<1.0, same 9-channel-UNet inpaint pipeline -- never plain img2img,
    per the card)."""
    init_path = Path(init_image) if init_image else (ASSETS / "init_canvas.png")
    init = Image.open(init_path).convert("RGB")
    W, H = init.size
    mask = Image.open(ASSETS / f"paintable_{arm}.png").convert("L")  # WHITE = repaint (diffusers convention, matches localgen.py)
    ctrl_path = Path(control_image)
    if not ctrl_path.is_absolute():
        ctrl_path = ASSETS / ctrl_path
    ctrl = Image.open(ctrl_path).convert("RGB")

    refs = [center_crop_square(Image.open(p).convert("RGB")) for p in REFS]
    ip_embeds = averaged_ip_embeds(pipe, refs, device)

    g = torch.Generator("cpu").manual_seed(seed)
    t0 = time.time()
    out = pipe(
        prompt=POSITIVE, negative_prompt=NEGATIVE,
        image=init, mask_image=mask,
        control_image=ctrl, controlnet_conditioning_scale=cond_scale,
        control_guidance_start=cg_start, control_guidance_end=cg_end,
        strength=strength, num_inference_steps=steps, guidance_scale=guidance,
        width=W, height=H, generator=g,
        ip_adapter_image_embeds=ip_embeds,
        output_type="latent",
    )
    latents = out.images
    # card: VAE forced fp32 before decode. Cast HERE (post denoising-loop,
    # pre-decode) -- this pipeline version's own auto-upcast branch only
    # fires when self.vae.dtype == float16 at the END of __call__, which we
    # bypass entirely via output_type="latent"; we do the decode ourselves so
    # the cast is applied deterministically instead of relying on that
    # internal branch. See PARAMS.md build note (encode must stay fp16).
    pipe.vae.to(torch.float32)
    with torch.no_grad():
        latents_f32 = latents.to(torch.float32) / pipe.vae.config.scaling_factor
        decoded = pipe.vae.decode(latents_f32, return_dict=False)[0]
    image = pipe.image_processor.postprocess(decoded, output_type="pil")[0]
    dt = time.time() - t0

    arr = np.asarray(image.convert("RGB"))
    nan_or_black = bool(np.isnan(arr.astype(np.float32)).any()) or bool((arr == 0).all())
    return image, dt, (W, H), nan_or_black


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["P1", "P2"])
    ap.add_argument("--seed", type=int)
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--guidance", type=float, default=5.5)
    ap.add_argument("--strength", type=float, default=1.0)
    ap.add_argument("--cond-scale", type=float, default=0.7)
    ap.add_argument("--cg-start", type=float, default=0.0)
    ap.add_argument("--cg-end", type=float, default=0.8)
    ap.add_argument("--control-image", default="control_canny.png",
                     help="filename within assets-640/ (or an absolute path) for the control image "
                          "(round 2 / Amendment 4: control_composition.png)")
    ap.add_argument("--init-image", default=None,
                     help="Stage B: path to a prior Stage-A gen.png to re-render at strength<1.0 "
                          "(default: assets-640/init_canvas.png, Stage-A neutral fill)")
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--shape-check", action="store_true",
                     help="cheap IP-Adapter embedding-shape probe, no full diffusion")
    a = ap.parse_args()

    if os.environ.get("PYTORCH_MPS_HIGH_WATERMARK_RATIO") != "0.0":
        print("[gen_stage_a] WARNING: PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0 is not set in the "
              "environment (card requires it set at the shell, never silently in code).", file=sys.stderr)

    t_load0 = time.time()
    pipe = load_pipe()
    device = "mps"
    load_dt = time.time() - t_load0
    print(f"[gen_stage_a] pipeline loaded in {load_dt:.0f}s")

    if a.shape_check:
        return run_shape_check(pipe, device)

    if not a.arm or a.seed is None or not a.out_dir:
        ap.error("--arm/--seed/--out-dir are required unless --shape-check")

    a.out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = a.out_dir / "raw.png"
    if raw_path.exists():
        raise SystemExit(f"[gen_stage_a] refusing to overwrite existing raw {raw_path}")

    out_img, gen_dt, (W, H), nan_or_black = generate(
        pipe, a.arm, a.seed, a.steps, a.guidance, a.strength,
        a.cond_scale, a.cg_start, a.cg_end, device, control_image=a.control_image,
        init_image=a.init_image)

    out_img.save(raw_path)
    composited = hard_composite(out_img, a.arm, W, H)
    composited.save(a.out_dir / "gen.png")

    meta = {
        "arm": a.arm, "seed": a.seed, "steps": a.steps, "guidance": a.guidance,
        "strength": a.strength, "controlnet_conditioning_scale": a.cond_scale,
        "control_guidance_start": a.cg_start, "control_guidance_end": a.cg_end,
        "control_image": a.control_image, "init_image": a.init_image or "assets-640/init_canvas.png",
        "lora_scale": LORA_SCALE, "ip_adapter_scale": IP_ROUTING,
        "positive_prompt": POSITIVE, "negative_prompt": NEGATIVE,
        "size": [W, H], "pipeline_load_s": round(load_dt, 1), "gen_s": round(gen_dt, 1),
        "nan_or_black": nan_or_black, "raw": str(raw_path), "gen": str(a.out_dir / "gen.png"),
    }
    (a.out_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    print(f"[gen_stage_a] arm={a.arm} seed={a.seed} steps={a.steps} size={W}x{H} "
          f"gen_time={gen_dt:.0f}s nan_or_black={nan_or_black} -> {a.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
