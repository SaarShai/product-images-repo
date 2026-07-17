# Advisor consult 2 — concrete run parameters for the authorized experiment

Read-only consult. Context: tasks/geometry-adherence-solutions/SYNTHESIS.md
(decided staged architecture). Experiment authorized: ~6 local gens on the
frozen princess-n02 panel (tall narrow, viewBox ~1850x864 rotated — see
tasks/geometry-evidentiary-princess-n02/svg-geometry-report.md), Apple Silicon
MPS, .venv-gen torch 2.12.1 / diffusers 0.38.

Stack: StableDiffusionXLControlNetInpaintPipeline
- base diffusers/stable-diffusion-xl-1.0-inpainting-0.1 (fp16)
- CN xinsir/controlnet-canny-sdxl-1.0, control image = white-on-black SVG
  lineart (outer contour + cutouts), precedent region-IoU 0.969 at
  control-scale ~0.6
- IP-Adapter ip-adapter-plus_sdxl_vit-h + ViT-H encoder, style ref = frozen
  watercolor princess refs (2 images)
- LoRA watercolor_v1_sdxl.safetensors

Arms:
- A-P1 (holes masked OUT of paintable) x2 seeds
- A-P2 (holes painted OVER, punched later) x2 seeds
- B: img2img style pass on best base at denoise 0.35 / 0.5, same conditioning

Questions (be concrete — numbers, not ranges wider than ±0.1):
1. Resolution strategy for a tall narrow panel on SDXL/MPS: recommended
   working WxH (SDXL-native bucket), and whether to gen rotated-landscape vs
   portrait given the panel is wider than tall in SVG user units.
2. Conditioning scales for style-vs-structure balance: control-scale,
   ip-scale (plus variant), lora-scale, guidance, steps, strength (inpaint),
   mask feather px (hard-geometry intent).
3. IP-Adapter with TWO reference images: pass both (list) vs one combined
   sheet vs pick one — which for style fidelity without layout copying?
4. Stage-B img2img on an inpaint pipeline: same checkpoint img2img vs plain
   SDXL base img2img + CN; keep IP/LoRA on? Exact denoise pair confirmed?
5. Known MPS/diffusers-0.38 pitfalls for this pipeline (dtype, attention
   slicing, VAE tiling) worth setting defensively.
6. Prompt text: minimal positive/negative prompt that complements (not
   fights) IP-Adapter+LoRA for watercolor architectural panels.
