# PLAN — local image-edit stack (M3 Max 48GB, ~86GB free disk)

Goal: a LOCAL, COMMERCIAL-safe, scriptable pipeline for masked inpaint + geometry lock (ControlNet) + watercolor style + hand-fix + upscale. Synthesized from 5 research streams (sources in task notes).

## Strategy
- **Platform = ComfyUI headless** (already cloned). It alone has, all working on MPS: HTTP `/prompt` API (scriptable like subgen), SDXL + Flux, masked inpaint, ControlNet. Launch: `python main.py --listen 127.0.0.1 --use-pytorch-cross-attention` (force PyTorch attention on Mac; avoid FP8 on MPS). Optional secondary = **mflux** (Apple MLX) for Flux-only CLI.
- **Isolate**: install the new Python deps in a DEDICATED venv (or ComfyUI's own), so we don't break the existing diffusers 0.27.2 / proven SDXL-0.969 pipeline.
- **The known weak point is STYLE** (local SDXL scored ~33–42 vs subscription ~88–90). Tier 1 is built to crack that: commercial illustration checkpoint + watercolor LoRA + IP-Adapter (style from a reference panel) + lineart/softedge ControlNet.
- Where local wins vs the working OpenAI-edit key: $0 per image, offline/unlimited iteration, **exact geometry via ControlNet** (OpenAI edit is mask-only), LoRA style control, hand-specific models. Where API wins: convenience + top quality right now. Keep BOTH.

## Tier 0 — already installed (reuse)
SDXL base 1.0 · xinsir canny-controlnet-sdxl · dreamshaper-8 + dreamshaper-8-inpainting (SD1.5) · ComfyUI · torch 2.8+MPS.

## Tier 1 — CORE commercial stack (install now) — ~22–26GB, all MPS-proven
| item | repo | size | license | role |
|---|---|---|---|---|
| ControlNet Union SDXL | xinsir/controlnet-union-sdxl-1.0 | ~1.9GB | Apache-2.0 ✓ | lineart/softedge/depth/tile/inpaint geometry lock |
| Watercolor LoRA | ostris/watercolor_style_lora_sdxl | ~48MB | Apache-2.0 ✓ | painterly style boost |
| IP-Adapter Plus SDXL | h94/IP-Adapter (ip-adapter-plus_sdxl) | ~103MB | Apache-2.0 ✓ | style from reference panel |
| CLIP image encoder | for IP-Adapter (ViT-H or bigG) | 0.6–3.7GB | verify | required by IP-Adapter |
| Illustration checkpoint | Juggernaut-XL-v9 (or clearly-commercial alt) | ~6.1GB | RAIL-M ⚠ (commercial = contact RunDiffusion) | better base than dreamshaper for storybook |
| SDXL inpaint checkpoint | Juggernaut-XL-inpainting (or SDXL-inpaint) | ~6.1GB | RAIL-M ⚠ | masked inpaint at SDXL quality |
| HandRefiner | wenquanlu/HandRefiner + depth-inpaint ckpt | ~0.45GB (+SD1.5 base) | MIT ✓ | fix hands (min ~60px → fix after upscale) |
| ComfyUI Impact Pack | ltdrdata/ComfyUI-Impact-Pack (+YOLO detect) | ~0.1GB | GPL node / YOLO AGPL ⚠ (internal-use OK) | auto-detect+detail hands/faces |
| Upscaler | 4x-UltraSharp (RealESRGAN) | ~64MB | MIT ✓ | tiled hi-res, watercolor-safe (blend w/ orig) |
| py deps | peft, accelerate, (openai), pinned diffusers in venv | small | — | enable LoRA/IP-Adapter/Flux |

## Tier 2 — FRONTIER experiments (after Tier 1 validated) — ~25–33GB, commercial but unproven on MPS/our style
| item | repo | size | license | note |
|---|---|---|---|---|
| FLUX.2 klein 4B | black-forest-labs/FLUX.2-klein-4B | ~9GB | Apache-2.0 ✓ | + text encoder (Mistral? ~13–15GB VERIFY) + VAE; via mflux/ComfyUI. ControlNet/Fill on 4B NOT yet validated |
| HiDream-O1-Image-Dev FP8 | Abiray/HiDream-O1-Image-FP8 | ~8GB | MIT ✓ | instruction edit; MPS maturity unproven |

## Tier 3 — SKIP (for now)
Flux.2 dev 32B (non-commercial + memory-borderline) · Qwen-Image-Edit 20B (no MPS/quant, ~40GB) · SUPIR (non-commercial) · Magnific (whole-image only, enterprise API).

## Execute order (after approval)
1. Make isolated venv; install peft/accelerate/diffusers(+optional openai). Smoke-test torch MPS.
2. Pull Tier 1 weights into ComfyUI/models/{controlnet,loras,ipadapter,checkpoints,upscale_models} + HandRefiner. VERIFY each card's size+license; abort any pull that would drop disk < ~20GB free.
3. Start ComfyUI headless; build a masked-inpaint + ControlNet(lineart) + watercolor-LoRA + IP-Adapter workflow JSON.
4. Wrap it as `scripts/localgen.py` (calls /prompt, polls /history, collects output) — mirrors subgen.py.
5. SMOKE TEST on the bottom-left fairy crop → composite back → compare vs OAI1 + N1.
6. (Optional) Tier 2: pull Flux.2 klein via mflux, test edit.

## done means
- [ ] User-approved tier scope + license stance + isolation
- [ ] Tier 1 weights downloaded, each verified (size+license logged), disk headroom ≥ ~20GB
- [ ] ComfyUI headless serves; `scripts/localgen.py` runs an inpaint+controlnet+LoRA gen
- [ ] Smoke test produces a fairy edit (gate: outside-mask unchanged) viewable + compared to OAI1/N1
- [ ] PLAN.md + install log committed to tasks/local-stack/
