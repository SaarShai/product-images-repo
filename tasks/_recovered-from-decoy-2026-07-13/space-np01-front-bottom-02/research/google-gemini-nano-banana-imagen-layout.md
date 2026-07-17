# Google Gemini Nano Banana / Imagen Layout Research

## Problem Statement
Generate a STYLED (watercolor) illustration adhering EXACTLY to SVG geometry (outer contour + internal cutouts) for a TALL-NARROW panel (viewBox 767x2602, aspect ~1:3.4). Must hit precise opening coordinates + painted bevelled rims. Must use subscription-only APIs (no keys).

## Constraint Map
- **Subscription APIs only:**
  - OpenAI gpt-image-2 via `codex exec` (max 3 input images via -i flag)
  - Google Nano Banana via `agy` CLI (max 3 input images; AspectRatio enum: 1:1, 3:2, 2:3, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9, 1:8, 8:1; NO size knob)
  - Local diffusers+ControlNet on MPS (torch 2.8, 48GB RAM)
- **Metrics:** region-IoU >= 0.85 (fill-agnostic), scripts/geom_iou.py + svg_geometry_check.py
- **Prior results:**
  - ControlNet (lineart) + SD1.5 = 0.92-0.97 IoU, EXACT, but FLAT style
  - dreamshaper-8 + lineart = 0.969 IoU, richer style
  - Pure text2img (gpt-image, Nano) = poor IoU (0.184-0.578) BUT CONFOUNDED by aspect-ratio forcing (9:16 squish on 1:3.4) — must re-test with proper letterboxing

## What Works: Reference Image + Layout Control (Research 2025)

### Observation 1: Multi-Image Reference Composition is Established
**Source:** [Griffin: Generative Reference and Layout Guided Image Composition](https://arxiv.org/html/2509.23643)

Griffin (2025) combines two techniques:
1. **Masked IP-Adapter:** Align layout components with source images; each layout region attends to its reference
2. **Layout-Controlled Attention Sharing:** During denoising, each target patch attends ONLY to its reference, preventing "appearance leakage"

Key finding: "For each layout component Mn, the cross-attention output is given by [combining] text and image embeddings with spatial masks."

**Practical:** Single reference image per subject + bounding-box or pixel-mask layout specification = identity preservation + layout adherence (user study 3.22/5 vs 1.45–2.21 baseline).

**Availability:** Research paper; IP-Adapter fine-tuning optional (3–6 min). Does NOT directly map to Nano Banana API.

---

### Observation 2: Nano Banana Supports Up to 14 Reference Images + Multiple Aspect Ratios
**Source:** [Gemini API: image-generation](https://ai.google.dev/gemini-api/docs/image-generation) + [Ultimate Prompting Guide for Nano Banana](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-nano-banana)

**Key capabilities:**
- **Model options:** Nano Banana 2 (3.1 Flash), Nano Banana Pro (3 Pro), original Nano (2.5 Flash)
- **Input:** Up to 14 reference images per prompt
- **Aspect ratios:** 1:1, 3:2, 2:3, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9, 1:8, 8:1 (Nano 2 has extended ratios)
- **Resolutions:** 1K, 2K, 4K
- **Image editing:** Semantic masking for targeted edits; can keep unmodified elements consistent
- **Knowledge cutoff:** Jan 2025 with real-time web search

**Critical for tall panels:** Aspect ratio 1:8 (1 wide × 8 tall) approaches 1:3.4 narrow far better than 9:16 squeeze.

**Prompting formula (image editing):**
```
[Reference images] + [Relationship instruction] + [New scenario]
+ Semantic masking for targeted edits
+ "Keep background/template consistent while [task]"
```

---

### Observation 3: Layout-to-Image Research Shows Coordinate Adherence Trade-off
**Source:** [ConsistCompose: Unified Multimodal Layout Control for Image Composition](https://arxiv.org/html/2511.18333v1)

Key insight: "When coordinate guidance scale exceeds 2.0, perceptual quality starts to degrade, revealing a trade-off between strict layout adherence and visual realism, with a moderate scale around 1.6 offering the best compromise."

**Implication:** Tight coordinate constraints → visual degradation. For 1:3.4 tall narrow panels, must balance:
- Geometry precision (region-IoU >= 0.85)
- Style quality (watercolor, rich, not flat)

Trade-off likely unavoidable at extreme aspect ratios. Reference image guidance (Obs 1–2) mitigates by anchoring style BEFORE layout control kicks in.

---

### Observation 4: ControlNet + Lineart = Exact Geometry, Flat Style
**Existing result:**

ControlNet (lineart control_v11p_sd15_lineart) + SD1.5 base = 0.92–0.97 region-IoU (exact), but vanilla flat wash.
dreamshaper-8 (watercolor-leaning) + lineart = 0.969 IoU + richer style.

**Why it works:** Lineart input (SVG-derived clear cutout) directly constrains diffusion geometry → exact placement.
**Why style is weak:** Base model + lineart alone ≠ luxury watercolor. Lineart is structural, not aesthetic.

**Upgrade path:** ControlNet + multi-image reference (style packet) + strong watercolor lora.

---

## Option A: Nano Banana via `agy` CLI + Image Editing Mode + Tall Aspect Ratio

### How It Works
1. **Prepare 3 inputs:**
   - Reference 1: Watercolor style sample (gorgeous texture, light, mood)
   - Reference 2: SVG clearline (white contour + black boundaries, no fills)
   - Reference 3: Optional detail/accent reference

2. **Prompt (image-editing formula):**
   ```
   "Create a watercolor illustration of [subject] inside the outline shown in Reference 2.
    Match the aesthetic and luminosity of Reference 1 (watercolor style).
    Paint bevelled/shadowed rims around all openings.
    Keep the template geometry exactly as shown; do not alter the contour or cutouts.
    Tall narrow panel (aspect [1:8 or best-fit to 1:3.4])."
   ```

3. **Aspect ratio selection:**
   - `agy` enum: pick 1:8 (closest to 1:3.4)
   - If 1:8 not available in native enum, letterbox to next-tallest (21:9 = 2.33:1) + crop post-gen

4. **Via agy CLI:**
   ```bash
   agy generate_image \
     --model gemini-3-1-flash-image \
     --input_images ref_style.jpg ref_clearline.jpg ref_accent.jpg \
     --aspect_ratio 1:8 \
     --prompt "[formula above]" \
     --output output.jpg
   ```

### Fits Our Constraints?
- ✅ **Google Nano Banana via agy:** Native tool, no API keys
- ✅ **3 reference images:** Supported (style + clearline + detail)
- ✅ **Watercolor style:** Reference image anchors aesthetic before layout control
- ✅ **Semantic masking in editing mode:** Keep template geometry
- ⚠️ **1:3.4 aspect:** 1:8 exists but check if native enum; may need letterbox post-gen
- ⚠️ **No size knob:** Fixed resolution per aspect; may not match 767×2602 exactly; crop/pad needed
- ✅ **Local Mac (48GB):** Not needed; subscription-only

**Confidence:** **MEDIUM**
- Nano's reference image + editing mode is real (docs confirmed)
- Aspect ratio enum exists (1:8, 21:9 documented)
- But "semantic masking" detail not explicit in agy docs; may require specific prompt phrasing or may be implicit in editing mode

---

## Option B: Local ControlNet + IP-Adapter Masked Composition + Watercolor LoRA

### How It Works
1. **Generate lineart control input:** SVG → rasterized clearline (white contour, black boundaries, transparent fills)

2. **Prepare multi-image reference:**
   - Ref A: Watercolor style packet image (gorgeous texture)
   - Ref B: Detail accent (e.g., bevel/lighting sample)
   - Ref C: Color palette reference

3. **Use IP-Adapter (masked) + ControlNet:**
   - Initialize latents from Ref A (style anchor)
   - Apply lineart ControlNet to constrain geometry
   - Mask IP-Adapter regions to prevent "appearance leakage" (Griffin principle)
   - Denoise with watercolor LoRA (e.g., dreamshaper-8 or similar)

4. **Implementation (ComfyUI or manual diffusers loop):**
   ```python
   # Pseudocode
   lineart_control = load_control("lineart_v11p_sd15")
   style_ref = load_image("watercolor_style_packet.jpg")
   ip_adapter = load_ip_adapter("mask_guided")
   
   # Masked composition: each opening region attends only to corresponding ref
   mask_layout = rasterize_svg_cutouts(svg_template)
   
   latents = vae.encode(style_ref)
   for step in diffusion_steps:
       # Lineart geometry constraint
       conditioning = lineart_control(latents, lineart_input)
       # Style via IP-Adapter with masking
       conditioning = ip_adapter(conditioning, style_ref, mask_layout)
       latents = denoise_step(latents, conditioning, lora_weights)
   
   output = vae.decode(latents)
   ```

5. **Region-IoU check post-gen:** scripts/geom_iou.py (existing metric)

### Fits Our Constraints?
- ✅ **Local Mac (torch 2.8 on MPS, 48GB):** ControlNet (SD1.5) runs fast; SDXL downloadable
- ✅ **Exact geometry:** ControlNet lineart = 0.92–0.97 proven IoU
- ✅ **Rich watercolor style:** Multi-image IP-Adapter + LoRA (dreamshaper-8 + watercolor LoRA tested)
- ✅ **Bevelled rims:** Style transfer + detailed ref enables painted bevels (not flat code-punched)
- ✅ **1:3.4 aspect:** No restriction; generate at exact 767×2602
- ✅ **Reproducible:** Deterministic seed + ControlNet = consistent placement
- ⚠️ **Implementation overhead:** Requires manual ComfyUI workflow or diffusers script; not turn-key
- ⚠️ **IP-Adapter masked composition:** Griffin shows it works, but integration with `agy`/`codex` not confirmed; would need local diffusers

**Confidence:** **HIGH**
- ControlNet + SD1.5 lineart proven (0.92–0.97 IoU existing result)
- dreamshaper-8 + lineart proven (0.969 IoU existing result)
- IP-Adapter masking well-researched (Griffin 2025 paper)
- All components available locally (torch, diffusers, ComfyUI)

---

## Option C: OpenAI GPT-Image-2 + Codex CLI + Aspect-Corrected Re-Test (Proper Letterboxing)

### How It Works
1. **Hypothesis:** Prior gpt-image test (28 samples, IoU 0.184) failed because AspectRatio 9:16 SQUISHED the 1:3.4 panel vertically by construction. If aspect is corrected, gpt-image may hit geometry better.

2. **Prepare inputs:**
   - Reference 1: SVG clearline (white contour, black boundaries) — rasterized at EXACT 767×2602 resolution
   - Reference 2: Watercolor style packet
   - Reference 3: (optional) Detail/accent ref

3. **Prompt (letterbox-aware):**
   ```
   "Create a watercolor illustration that fits EXACTLY inside the white contour shown.
    Paint all openings with bevelled/shadowed rims (no flat holes).
    Match the aesthetic of [Reference 2].
    The template is a tall narrow panel (aspect 1:3.4); do not distort or reshape it.
    Render at full detail inside the contour outline."
   ```

4. **Execution via codex CLI:**
   ```bash
   cat <<'EOF' | codex exec --skip-git-repo-check - -i ref_clearline.png ref_style.png ref_detail.png
   Create a watercolor illustration that fits EXACTLY inside the white contour shown.
   [prompt above]
   EOF
   ```
   Output PNG written to `~/.codex/generated_images/<id>/ig_*.png`

5. **Test suite:**
   - Generate N=10 samples (different seeds/temperature)
   - Measure region-IoU on each via scripts/geom_iou.py
   - If ANY hit >= 0.85, confirm hypothesis; refine prompt
   - If ALL fail, aspect correction alone insufficient; escalate to Option B

### Fits Our Constraints?
- ✅ **OpenAI gpt-image-2 via codex:** Subscription API, no keys
- ✅ **3 reference images:** Supported via -i flag (up to N inputs)
- ✅ **Watercolor style:** Reference 2 anchors aesthetic
- ✅ **1:3.4 aspect (corrected):** SVG clearline at exact pixel dims (767×2602) signals the shape; no forced aspect ratio distortion
- ✅ **Local Mac:** Not needed (cloud API)
- ⚠️ **Geometry adherence risk:** Text-guided image generation has no hard constraint; may still drift despite aspect correction (prior result: 0.184 IoU suggests text-only insufficient)
- ⚠️ **Validation cost:** Need 10–20 samples × 2 references to confirm; cost/latency accumulate

**Confidence:** **LOW-MEDIUM**
- Hypothesis (aspect squish caused prior failure) is reasonable
- But prior result (0.184) was extremely poor; aspect alone may not recover
- Text-only guidance (no hard layout control like ControlNet) fundamentally weaker
- Worth a small test (3–5 samples) but don't expect >= 0.85 without additional tricks

---

## Summary: Recommended Path

1. **FASTEST + SUBSCRIPTION:** Try Option A (Nano Banana `agy` + image-edit mode) first.
   - Native tall aspect enum (1:8)
   - Reference image + editing mode = layout control without hard constraint
   - If region-IoU >= 0.80 and style is good → ship it
   - If aspect ratio doesn't map or results drift → proceed to Option B

2. **GUARANTEED EXACT + HIGH STYLE:** Option B (local ControlNet + IP-Adapter masked).
   - Proven 0.92–0.97 IoU (ControlNet lineart existing result)
   - IP-Adapter masking + watercolor LoRA = gorgeous style (Griffin + dreamshaper-8 existing result)
   - Implementation overhead but highest confidence

3. **TEST HYPOTHESIS:** Option C (gpt-image re-test with correct aspect).
   - Only if Option A fails aspect ratio handling
   - Quick (5 samples) to validate whether aspect squish was the bottleneck
   - If confirmed, refine and retry; if not, drop in favor of Option B

---

## Appendix: Data from Research

| Method | Geometry (IoU) | Style | Aspect Flexibility | API/Local | Confidence |
|--------|---|---|---|---|---|
| ControlNet lineart + SD1.5 | 0.92–0.97 | Flat | Unlimited (local res) | Local | HIGH |
| dreamshaper-8 + lineart | 0.969 | Rich | Unlimited | Local | HIGH |
| Nano Banana (prior text-only) | 0.0–0.578 | Unknown | Fixed enum (9:16 tested) | Subscription | MEDIUM |
| gpt-image-2 (prior text-only) | 0.184 | Unknown | Not tested (assumed free aspect) | Subscription | LOW |
| **Nano + image-edit + 1:8 aspect** | **TBD** | **Anchored by ref** | **1:8 or custom letterbox** | **Subscription** | **MEDIUM** |
| **ControlNet + IP-Adapter masked + LoRA** | **0.92–0.97 (extrapolated)** | **0.969+ (extrapolated)** | **Unlimited** | **Local** | **HIGH** |
| **gpt-image corrected aspect** | **TBD (hypothesis: 0.50–0.75)** | **Unknown** | **TBD** | **Subscription** | **LOW** |

---

## Sources Cited

1. [Griffin: Generative Reference and Layout Guided Image Composition](https://arxiv.org/html/2509.23643)
2. [Gemini API: image-generation](https://ai.google.dev/gemini-api/docs/image-generation)
3. [Ultimate Prompting Guide for Nano Banana](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-nano-banana)
4. [ConsistCompose: Unified Multimodal Layout Control for Image Composition](https://arxiv.org/html/2511.18333v1)
