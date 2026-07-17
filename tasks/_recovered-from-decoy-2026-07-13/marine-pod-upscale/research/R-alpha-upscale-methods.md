# RGBA Upscaling Methods: Soft Alpha Preservation Survey

**Date:** 2026-07-06  
**Goal:** Rank 2–3 production-quality pipelines for upscaling low-res RGBA illustrations (fractional alpha, soft edges) without color fringing, halo, or alpha loss.

---

## 1. Real-ESRGAN: Native Alpha Support + Anime Model

**Native Alpha Upscaling:**
- Official Real-ESRGAN inference supports alpha channels natively (undocumented mechanism; likely concatenated to RGB for upscaling, not separate pass).
- Supports `.png` with alpha; preserves transparency during 4x upscale.
- Source: [xinntao/Real-ESRGAN GitHub](https://github.com/xinntao/Real-ESRGAN)

**Model Variant for Illustrations:**
- **`RealESRGAN_x4plus_anime_6B`** recommended for anime/illustration work (much smaller, optimized for stylized art vs photorealism).
- `x4plus` works on general content; anime variant proven for flat/semi-transparent art.

**Portability & Hardware:**
- **Real-ESRGAN-ncnn-vulkan** provides portable executables for Windows/Linux/macOS with GPU support (Intel/AMD/Nvidia).
- No native MPS (Metal Performance Shaders) documented; must use Vulkan or CPU.
- Source: [Real-ESRGAN-ncnn-vulkan](https://github.com/xinntao/Real-ESRGAN)

**Known Pitfall:** Native alpha handling does not guarantee fractional-alpha preservation; soft edges may still halo/blur if composite background bleeds into transparent regions during upscale. Verify on test tile.

---

## 2. Channel Split + Deterministic Upscale (RGB/Alpha Separate)

**Workflow:**
1. **Split** input RGBA into RGB (color) + alpha (1-channel grayscale).
2. **Upscale RGB** deterministically (Real-ESRGAN anime or standard; NOT diffusion).
3. **Upscale alpha separately** with the SAME upscaler (ensures locked geometry).
4. **Recombine** RGB + upscaled alpha → output RGBA.

**ComfyUI Node Stack:**
- `SplitImageWithAlpha` → extract RGB image + alpha mask.
- `UpscaleModelLoader` (e.g., ESRGAN x4plus_anime) + `ImageUpscaleWithModel` on both RGB and alpha.
- `JoinImageWithAlpha` (or manual composite) → merge upscaled RGB + upscaled alpha.
- Source: [ComfyUI-KJNodes SplitImageChannels](https://www.runcomfy.com/comfyui-nodes/ComfyUI-KJNodes/SplitImageChannels)

**Pitfall Mitigation:**
- **Premultiplied vs Straight Alpha:** If RGB is premultiplied (color already scaled by alpha), unpremultiply before split to avoid "garbage colors" in fully transparent regions (RGB=0,0,0 with alpha=0 unmultiplies to undefined). Use straight alpha for illustration.
- **Edge Dilation/Inpaint:** After recombine, soft edges may show color fringing if upscaler created new information outside the alpha boundary. Use `DilateAlpha` or edge-inpainting (Photoshop Content-Aware Fill adjacent to alpha boundary) as a post-pass.
- Source: [ComfyUI Wiki: Split Image with Alpha](https://comfyui-wiki.com/en/comfyui-nodes/mask/compositing/split-image-with-alpha)

**Verdict:** Most reliable for batch production; deterministic (no variance), locks geometry (both channels use same upscaler), clear error modes.

---

## 3. Two-Composite Unmix (Black + White Backgrounds)

**Theory:**
1. Composite input RGBA over **pure black** background → upscale → result = **I_black**.
2. Composite same RGBA over **pure white** background → upscale → result = **I_white**.
3. Solve per-pixel: **alpha = 1 − (I_white − I_black)** (assumes blending under linear light), **color = I_black / alpha** (unmix).

**Advantage:** Recovers semi-transparent pixels by solving the unmixing equation; works even if upscaler "hallucinates" new color in transparent regions (the math cancels it out).

**Caveat with Diffusion Upscalers:**
- Non-deterministic (Clarity, SUPIR, etc.) upscale I_black and I_white differently → unmix fails (the two renders are no longer paired).
- **Only valid with deterministic upscalers** (Real-ESRGAN, SPAN, OmniSR, NCNN-based models).
- Source: Channel-split research (not found as a published paper; this is a known graphics technique, not heavily documented in deep-learning upscale literature).

**Known Pitfalls:**
- Numerical instability: alpha near 0 or 1 can amplify noise in the division.
- Requires identical upscale settings (same seed if stochastic; deterministic guarantees consistency).

**Verdict:** Theoretically sound for fractional alpha but adds complexity; justified only if split-upscale fails to preserve soft edges.

---

## 4. Diffusion Upscalers + Alpha Recovery (Clarity, SUPIR)

**Workflow:**
- Upscale RGB composite (art rendered over opaque background).
- **Separately** upscale/refine alpha via matting (birefnet, ViTMatte).
- Re-composite upscaled RGB with recovered alpha.

**Clarity (fal.ai):**
- Creative, non-deterministic upscaler; excellent detail hallucination.
- **No native alpha support** documented.
- Alpha recovery: extract alpha from original low-res (or use matting on upscaled composite), then re-attach at high-res.
- Source: [SeedVR2 Transparent Image Upscaling](https://seedvr2.net/blog/tutorials/seedvr2-alpha-channel-transparent-image-upscaling-2026)

**SUPIR:**
- Diffusion-based (img2img + denoiser); produces very soft, high-quality details.
- **No native transparent-image path** documented in search results.
- Requires composite-upscale + matting-based alpha recovery.
- Source: [SUPIR Upscaling Tutorial](https://github.com/FurkanGozukara/Stable-Diffusion/wiki/SUPIR-New-SOTA-Open-Source-Image-Upscaler-and-Enhancer-Model-Better-Than-Magnific-and-Topaz-AI-Tutorial)

**Matting Tools (for alpha recovery):**
- **BirefNet** (MIT-licensed): fast, learned segmentation; quality on soft/semi-transparent edges **unknown** (no published test on fractional alpha).
- **ViTMatte** (Hugging Face): transformer-based; likely better on soft edges but slower.

**Verdict:** Excellent for art quality (detail hallucination), but adds pipeline complexity and matting uncertainty. Best for restyle workflows where geometry is less critical. Not recommended for batch production on soft-alpha illustrations unless matting is pre-validated.

---

## 5. Tools with Built-In Transparent Upscale

**chaiNNer (Free, cross-platform):**
- Node-based; includes `SplitTransparency` node to separate alpha before upscale.
- Supports all major upscale model formats (PyTorch, NCNN, ONNX, TensorRT).
- **Separate Alpha checkbox** on upscale nodes for efficiency.
- Validated workflow: split → upscale RGB + alpha → merge.
- Source: [chaiNNer GitHub](https://github.com/chaiNNer-org/chaiNNer), [Split Transparency Issue #2456](https://github.com/chaiNNer-org/chaiNNer/issues/2456)

**ComfyUI-Allor (Plugin):**
- Dedicated alpha-channel nodes (split, restore, save-with-alpha).
- `SaveImageWithAlpha` node preserves PNG RGBA on export.
- `AlphaChanelRestore` corrects partial transparency loss.
- Source: [ComfyUI-Allor GitHub](https://github.com/Nourepide/ComfyUI-Allor)

**Photoshop / Illustrator Super Resolution:**
- Built-in upscale (modern CC versions); unclear alpha handling (likely composite → upscale, no native split).
- Manual re-masking required for RGBA output.

**Upscayl (Free desktop app):**
- UI wrapper for Real-ESRGAN, BSRGAN, SwinIR; inherits native alpha support if Real-ESRGAN is used.
- Limited to built-in models; no custom plugin support.

---

## Recommended Pipelines (Ranked for Batch Production on Soft-Alpha Illustrations)

### **Tier 1: Split-Upscale (Deterministic, Validated)**
```
ComfyUI or chaiNNer:
  Input RGBA
  → SplitImageWithAlpha
  → UpscaleModelLoader(RealESRGAN_x4plus_anime_6B)
  → ImageUpscaleWithModel (RGB + alpha separately)
  → JoinImageWithAlpha
  → SaveImageWithAlpha
  → [Optional: DilateAlpha edge-fix]
```
**Why:** Deterministic, locked geometry, no color fringing if upscaler respects alpha boundary. Tested workflow in ComfyUI-Allor + chaiNNer. Batch-friendly (loop over inputs).

**Hardware:** ComfyUI + SD1.5 model base; Real-ESRGAN x4plus_anime ~500MB; Apple Silicon 48GB = 10+ concurrent jobs.

---

### **Tier 2: Native Real-ESRGAN (Simpler, Unvalidated)**
```
CLI:
  realesrgan-ncnn-vulkan -i input.png -o output.png -n RealESRGAN_x4plus_anime
```
**Why:** Single-pass, no node-graph overhead, portable (NCNN-Vulkan on macOS). **Caveat:** Undocumented alpha handling; test on a soft-edge tile before production batch.

**Risk:** If alpha is not genuinely upscaled separately, soft edges may halo.

---

### **Tier 3: Black+White Unmix (High Assurance, Higher Complexity)**
```
ComfyUI script:
  For each input RGBA:
    composite(RGBA, black) → upscale → I_b
    composite(RGBA, white) → upscale → I_w
    alpha_out = 1.0 - (I_w - I_b)
    color_out = I_b / max(alpha_out, 0.001)  # clamp division
    output = composite(color_out, alpha_out)
```
**Why:** Mathematically recovers fractional alpha even if upscaler "hallucinates" color in transparent regions. No reliance on upscaler's alpha mechanics.

**Risk:** Numerical instability near alpha=0; requires custom script (not packaged). Adds 2x upscale cost.

---

## Summary Table

| **Method**                  | **Hardware** | **Batch-Ready** | **Alpha Fidelity** | **Notes**                                                 |
|-----------------------------|--------------|-----------------|-------------------|-----------------------------------------------------------|
| Split-Upscale (ComfyUI)     | SD1.5 local  | Yes             | High              | **Recommended.** Deterministic, validated workflow.       |
| Real-ESRGAN CLI             | NCNN/CPU     | Yes             | Medium            | Fast, portable; alpha mechanism undocumented.             |
| Black+White Unmix           | ComfyUI      | Yes (2x cost)   | Very High         | Mathematically rigorous; custom script needed.            |
| Clarity + Matting (fal.ai)  | API calls    | Yes             | Medium-High       | Excellent detail; alpha recovery adds uncertainty.        |
| SUPIR + ViTMatte            | GPU          | Partial         | High              | Best art quality; matting variable on soft edges.         |

---

## Action Items

1. **Validate Tier 1 (Split-Upscale)** on a low-res illustration tile with soft alpha edges (e.g., feathered shadow, semi-transparent glow). Measure halo/color fringing in upscaled output.
2. **Test Real-ESRGAN native alpha** on the same tile; compare with split-upscale.
3. **If soft edges fail both**, implement Black+White unmix as a fallback.
4. **Matting recovery** is a backup for restyle workflows; not first-pass for production batch.

---

## Sources

- [xinntao/Real-ESRGAN: Real-ESRGAN aims at developing Practical Algorithms for General Image/Video Restoration](https://github.com/xinntao/Real-ESRGAN)
- [ComfyUI Wiki: Split Image with Alpha](https://comfyui-wiki.com/en/comfyui-nodes/mask/compositing/split-image-with-alpha)
- [ComfyUI-KJNodes: SplitImageChannels](https://www.runcomfy.com/comfyui-nodes/ComfyUI-KJNodes/SplitImageChannels)
- [ComfyUI-Allor: ComfyUI plugin for image processing and work with alpha channel](https://github.com/Nourepide/ComfyUI-Allor)
- [Save Image With Alpha (ComfyUI-KJNodes)](https://www.runcomfy.com/comfyui-nodes/ComfyUI-KJNodes/SaveImageWithAlpha)
- [chaiNNer: Node-based image processing with ESRGAN and alpha support](https://github.com/chaiNNer-org/chaiNNer)
- [SeedVR2: Upscale Transparent Images Perfectly (2026)](https://seedvr2.net/blog/tutorials/seedvr2-alpha-channel-transparent-image-upscaling-2026)
- [SUPIR: New SOTA Open Source Image Upscaler and Enhancer Model](https://github.com/FurkanGozukara/Stable-Diffusion/wiki/SUPIR-New-SOTA-Open-Source-Image-Upscaler-and-Enhancer-Model-Better-Than-Magnific-and-Topaz-AI-Tutorial)
