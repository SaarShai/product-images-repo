# Production Template Dieline Texture Warp Research

## Problem Statement
Generate a styled watercolor illustration that adheres EXACTLY to SVG geometry (outer contour + internal cutouts) for a tall-narrow panel (767x2602, aspect ~1:3.4). Must use subscription-only methods (gpt-image-2 via codex, Nano Banana via agy, or local diffusers on MPS). Target: region-IoU >= 0.85, with beautiful watercolor rendering (not flat wash).

## Research Findings

### 1. ControlNet Inpainting + Mask-Conditioned Generation
**How it works**: Use ControlNet 2.0 with Canny edge detection + inpaint preprocessor to lock non-target areas while AI fills only within masked region. Dual-constraint system ensures exact geometry adherence.

**Fits our setup**: YES — local diffusers path (ComfyUI on MPS). We already have working SD1.5 + ControlNet lineart control (0.92-0.97 region-IoU).

**Concrete steps**:
1. Use existing lineart CN approach (control_v11p_sd15_lineart + deterministic SVG clear of openings)
2. In ComfyUI: add inpainting-specific nodes:
   - Load image with masked regions (openings)
   - MaskEditor to paint exact opening locations
   - "VAE Encode (for Inpainting)" with grow_mask_by=6
   - Stack ControlNet + text prompt through KSampler
   - VAE Decode for final output
3. For style: use dreamshaper-8 (already confirmed 0.969 region-IoU + watercolor-leaning rendering)
4. Iterate: verify region-IoU with geom_iou.py; white-IoU with svg_geometry_check.py

**Citation**: [Inpainting With ComfyUI - Basic Workflow & With ControlNet](https://medium.com/@promptingpixels/inpainting-with-comfyui-basic-workflow-with-controlnet-911428c5c57c), [ControlNet 2.0 Local Inpainting](https://civitai.com/models/2231784/z-image-controlnet-20-local-inpainting)

---

### 2. Displacement Map Texture Warp → Exact Geometry Fitting
**How it works**: Generate a full watercolor illustration (text2img via subscription), then use a displacement map (grayscale mask of target SVG geometry + cutout shapes) to warp the generated texture into exact contours. Displacement maps use intensity values to shift pixels in X/Y, making generated content conform to exact geometry without losing style.

**Fits our setup**: YES — two lanes:
- **Lane 1 (fastest)**: Generate with codex (gpt-image-2), export as PNG; use ComfyUI "Image Displacement Warp" node (local MPS) to apply SVG-derived displacement map
- **Lane 2 (backup)**: Generate with agy (Nano), same warp pipeline
- **Lane 3 (fullstack local)**: Pure diffusers + displacement (no subscription step)

**Concrete steps**:
1. Create displacement map from SVG template:
   - Render SVG with filled contours (white interior, black exterior)
   - Generate grayscale displacement map with peaks at edge transitions
   - Invert so openings (cutouts) are black (maximum warp away)
2. Generate base watercolor:
   - Via `codex exec --skip-git-repo-check - -i <ref1> <ref2> ... < prompt.txt` (writes PNG to ~/.codex/generated_images/<id>/ig_*.png)
   - OR via `agy generate_image` with AspectRatio enum letterboxed to true 1:3.4
   - Prompt: explicit watercolor style, consistent color palette
3. Apply displacement warp in ComfyUI:
   - Load generated image
   - Load displacement map (SVG-derived grayscale)
   - Use ComfyUI "Image Displacement Warp" node (WAS Node Suite)
   - Strength parameter controls warp intensity (tunable)
   - VAE Decode → save
4. Verify geometry with geom_iou.py (should hit >= 0.85 if displacement map is accurate)

**Citations**: [Displacement Maps for Easy Image Transformations](https://cloudinary.com/blog/how_to_use_displacement_maps_to_transform_images), [ComfyUI Image Displacement Warp Node](https://www.runcomfy.com/comfyui-nodes/was-node-suite-comfyui/Image-Displacement-Warp), [Displacement Map Complete Tutorial 2024](https://borisfx.com/blog/displacement-map-complete-tutorial-2024/)

---

### 3. Generate-Then-Mask-Composite (Professional Packaging Workflow)
**How it works**: Professional packaging designers generate full artwork (fast, loose), then apply exact mask/crop to final composite. Workflow: generate best-of-N candidates → select best match → apply exact SVG mask to crop interior, beveled rim treatment via style prompt ("illustrated bevelled edge") or post-processing.

**Fits our setup**: YES — subscription lane.

**Concrete steps**:
1. Generate N candidates (e.g., 5–10 samples) via codex or agy with explicit aspect ratio matching true 1:3.4 (NOT 9:16 squeeze):
   - `codex`: variadic `-i <ref1> <ref2> ... -i <ref3>` (max images unclear; test)
   - `agy`: max 3 input images; use AspectRatio ENUM closest to 1:3.4 (if 9:16 available, apply pre-generation letterbox to avoid vertical squish)
   - Prompt includes "bevelled rim", "illustrated opening edge", "watercolor style"
2. Evaluate each candidate:
   - region-IoU >= 0.85 (geom_iou.py)
   - white-IoU check (svg_geometry_check.py) — opening placement precision
   - Visual quality (watercolor coherence, no flat wash)
3. Post-process best candidate:
   - Apply exact SVG mask (crop/clip interior to template)
   - Optional: composite bevelled rim texture separately if model output is weak
4. Quality gate: visual review + metrics

**Challenge** (from prior work): Forcing AspectRatio 9:16 on 1:3.4 panel caused vertical squish → geometry drift. CRITICAL: match true aspect in generation request.

**Citations**: [AI Packaging Design Generator for Product Design & Mockup](https://www.fotor.com/design/ai-packaging-design-generator/), [Packify - The First AI Packaging Design Agent](https://www.packify.ai/), [How to Use AI for Packaging Design](https://pakfactory.com/blog/artificial-intelligence-packaging-design/)

---

## Recommended Priority Ranking

1. **ControlNet Inpainting** (Method 1): Lowest latency, most direct control, proven 0.96+ region-IoU locally. Already have the model + pipeline. Add inpainting nodes to ComfyUI workflow → immediate test.

2. **Displacement Warp** (Method 2): Highest style flexibility (decouples geometry from generation). Works with subscription OR local diffusers. Displacement map creation is deterministic (no magic). Best for "gorgeous watercolor" + exact coords.

3. **Generate-Then-Mask** (Method 3): Fastest to prototype (no new infra). Risk: subscription models may not hit exact coords even with aspect fix. Use as fallback/validation of Methods 1 & 2.

---

## Open Questions for Next Phase

- **Displacement map precision**: How fine must grayscale gradient be for < 0.15 region-IoU error? Can SVG stroke width → displacement intensity?
- **ComfyUI node availability**: Is WAS Node Suite's "Image Displacement Warp" stable on MPS? Any known issues?
- **Aspect ratio limits in agy**: Can we call `agy generate_image` with custom aspect, or only enum values? If enum-only, which is closest to 1:3.4?
- **Bevelled rim rendering**: Does watercolor-style prompt alone produce convincing painted rim, or must we composite separately?
- **Codex multi-image handling**: Variadic `-i` — what's the practical limit? Does order/weighting matter?

---

## Files to Create/Update

- [ ] `scripts/svg_to_displacement_map.py` — deterministic SVG → grayscale displacement map renderer
- [ ] ComfyUI workflow (Method 1): inpainting-enhanced CN lineart
- [ ] ComfyUI workflow (Method 2): displacement warp + style prompt
- [ ] Test harness: compare region-IoU across Methods 1, 2, 3 on N=5 candidates each

---

## References

### Geometric Control in AI Generation
- [ControlVP: Interactive Geometric Refinement of AI-Generated Images](https://arxiv.org/pdf/2512.07504) — vanishing point correction via mask + contour
- [Geometry-Based Feature Extraction & Synthesis Survey](https://arxiv.org/pdf/2412.01450) — taxonomy of geometric conditioning

### Practical Inpainting & ControlNet
- [Inpainting With ComfyUI](https://medium.com/@promptingpixels/inpainting-with-comfyui-basic-workflow-with-controlnet-911428c5c57c)
- [ControlNet 2.0 Local Inpainting](https://civitai.com/models/2231784/z-image-controlnet-20-local-inpainting)
- [ControlNet Complete Guide](https://stable-diffusion-art.com/controlnet/)

### Displacement & Warp
- [Displacement Maps for Image Transformations](https://cloudinary.com/blog/how_to_use_displacement_maps_to_transform_images)
- [ComfyUI Image Displacement Warp Node](https://www.runcomfy.com/comfyui-nodes/was-node-suite-comfyui/Image-Displacement-Warp)
- [Displacement Map Tutorial 2024](https://borisfx.com/blog/displacement-map-complete-tutorial-2024/)

### Professional Packaging Workflow
- [AI Packaging Design Agents](https://www.packify.ai/)
- [How to Use AI for Packaging Design](https://pakfactory.com/blog/artificial-intelligence-packaging-design/)
- [AI Product Packaging Designer](https://www.artificialstudio.ai/create/product-packaging)
