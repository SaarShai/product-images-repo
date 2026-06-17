# OpenAI GPT-Image Edit & Reference: Exact Geometry + Watercolor Style

Research on using gpt-image-2 via codex CLI to force precise SVG geometry adherence while maintaining watercolor illustration quality. GOAL: >=2 reliable methods to generate styled illustrations that match exact cutout/opening placement (region-IoU >= 0.85).

## PROBLEM RECAP
- Tall-narrow SVG panel: 767x2602 (aspect ~1:3.4)
- Openings at precise SVG coordinates; want bevelled rims painted by model (not flat code-punched)
- Subscription only: gpt-image-2 via codex CLI (no API keys)
- Previous attempts: aspect-ratio mismatch (forced 9:16 on 1:3.4 panel) squished image, caused coordinate drift
- ControlNet local works geometrically (0.92–0.97 IoU) but style is flat; need subscription + style simultaneously

---

## FINDINGS: >=2 CONCRETE OPTIONS

### OPTION 1: gpt-image EDIT ENDPOINT + MASK (Codex CLI)

**How it works:**
- gpt-image edit endpoint accepts 3 inputs: base image, mask PNG (transparent=edit zone), text prompt
- Mask indicates WHERE to regenerate; prompt controls WHAT to generate there
- **Critical:** "Masking with GPT Image is entirely prompt-based. The model uses the mask as guidance, but may NOT follow its exact shape with complete precision" [OpenAI docs]
- Mask serves as directional hint, not hard boundary; geometry loss expected without additional constraints

**Fit for our setup:**
- ✅ Via codex CLI: `codex exec --skip-git-repo-check - -i <base.png> <mask.png>` (prompt on stdin)
- ✅ Outputs PNG to `~/.codex/generated_images/<id>/ig_*.png`
- ❌ **GEOMETRY RISK:** Mask is prompt-guided only; no hard inpaint boundary. Likely repeat of drift seen with aspect mismatch
- ⚠️  Best used for STYLE REFINEMENT on already-correct geometry, not primary geometry enforcement

**Concrete steps:**
1. Generate clean SVG base (all openings transparent or white-filled)
2. Create mask PNG (same 767x2602 dims): white where content should preserve, transparent at openings
3. Craft prompt: "Watercolor illustration of [scene]. Keep all surrounding geometry identical. Paint only the masked white areas with beautiful watercolor. Do NOT move or resize any openings."
4. Run: `echo "<prompt>" | codex exec --skip-git-repo-check - -i base.png mask.png`
5. Evaluate output with `scripts/geom_iou.py` and `scripts/svg_geometry_check.py`
6. If IoU < 0.85: iterative refinement (tighter prompt, different base)

**Citations:**
- [Image generation | OpenAI API](https://developers.openai.com/api/docs/guides/image-generation)
- [Codex CLI features](https://developers.openai.com/codex/cli/features)

---

### OPTION 2: gpt-image REFERENCE MODE + LETTERBOXING + BEST-OF-N

**How it works:**
- gpt-image-2 supports reference images (1 to edit, or multiple to blend styles/subjects)
- Model processes references at high fidelity automatically—no adjustment knob
- Aspect ratio support: 1:1, 3:2, 2:3, or custom (both edges multiples of 16, longest ≤3840px, ratio <3:1, pixel count 655k–8.2M)
- **Key insight:** Previous test failure (Nano ceiling 0.578, gpt-image 0.184) forced 9:16 on 1:3.4 panel → VERTICAL SQUISH → coordinate drift
- **Solution:** Letterbox to TRUE aspect (767:2602 ≈ 0.295:1); add padding to reach supported aspect (e.g., 1:3.4 → add side padding → 1.5:5 or 2:6 valid ratio). Model paints inside letterbox; crop padding in post-processing.
- Best-of-N: generate 3–5 candidates, gate by region-IoU >= 0.85

**Fit for our setup:**
- ✅ Via codex CLI: multi-image reference + prompt
- ✅ gpt-image-2 supports custom aspect (767 → nearest multiple of 16 is 768; 2602 → 2608; ratio 768:2608 ≈ 1:3.4, valid)
- ✅ Can embed reference watercolor style images (e.g., existing output with good style, prior art)
- ✅ Prompt: "preserve layout," "keep structure identical," absolute spatial references ("upper quadrant," "bottom center")
- ✅ Letterbox → generate → crop = exact aspect preserved, no squish-induced drift
- ⚠️  **Cost:** 5 generations = 5x image cost; geometry match NOT guaranteed even at correct aspect (model may still drift)

**Concrete steps:**
1. Create letterboxed canvas: pad 767x2602 to 960x2560 (or similar, ratio <3:1, dims = 16k multiples). Add side padding with white/transparent.
2. Prepare reference images: 1–2 watercolor style refs (either successful prior outputs or external watercolor illustration images)
3. Generate SVG template interior (clear of openings; just contour outline + grid/guide marks at opening locations)
4. Craft prompt: "Watercolor illustration of [scene]. Reference [style_ref]. Preserve all geometry and opening locations exactly. Layout: opening A at 20% from top center, opening B at 50% from top left, [etc. spatial coords]. Do NOT move, resize, or shift any feature."
5. Run 5 times: `echo "<prompt>" | codex exec --skip-git-repo-check - -i template.png ref1.png ref2.png > output_$i.png`
6. Crop output (remove letterbox padding) back to 767x2602
7. Measure region-IoU; select best candidate (threshold 0.85)

**Citations:**
- [How to Make GPT Image 2 Follow Exact Layout Instructions](https://www.rewarx.com/blogs/how-to-make-gpt-image-2-follow-exact-layout-instructions)
- [GPT Image 2 Prompt Guide](https://pixverse.ai/en/blog/gpt-image-2-review-and-prompt-guide)
- [fal.ai: How to Use GPT Image 2](https://fal.ai/learn/tools/how-to-use-gpt-image-2)

---

## COMPARISON TABLE

| Method | Geometry Precision | Style Fidelity | Cost | Complexity | Risk |
|--------|-------------------|----------------|------|-----------|------|
| **Edit + Mask (Opt 1)** | Medium (prompt-guided, not hard boundary) | High (gpt-image-2 quality) | Low (1 gen) | Low | Drift from soft masking |
| **Reference + Letterbox + Best-of-N (Opt 2)** | Medium–High (correct aspect, but still generative) | High (multi-ref style blend) | High (5 gens) | High | Model variability; need gating |

---

## KNOWN LIMITATIONS (From Research)

1. **gpt-image Edit Endpoint:**
   - "Masking with GPT Image is entirely prompt-based" → NOT a rigid inpaint boundary
   - May edit outside mask zone; may fail to edit inside it
   - Aspect ratio mismatch (observed in prior test) causes structural drift

2. **Reference Mode + Aspect:**
   - Aspect ratio support is ENUM: 1:1, 3:2, 2:3, or custom (within 3:1 limit)
   - 1:3.4 aspect requires custom size; letterboxing is workaround
   - Model processes refs at high fidelity but does NOT guarantee layout preservation (prompt-guided)

3. **Codex CLI Image Tool:**
   - Accepts reference images (variadic `-i` flag) but exact inpaint/mask syntax not documented
   - No published examples of mask-based edits via Codex CLI
   - May fall through to gpt-image-2 gen (not edit) if mask API not exposed

---

## NEXT STEPS FOR VALIDATION

1. **Quick test (Option 1):** Prepare 767x2602 base + mask PNG; run single edit via codex CLI; measure IoU
2. **Full test (Option 2):** Letterbox to valid aspect; generate 5 candidates with reference images; gate by IoU >= 0.85
3. **Fallback:** If both fail geometry, return to ControlNet local + style-transfer post-processing (ComfyUI + SD1.5 dreamshaper + style reference node)

---

## SOURCES READ

- [Image generation | OpenAI API](https://developers.openai.com/api/docs/guides/image-generation)
- [Codex CLI features](https://developers.openai.com/codex/cli/features)
- [How to Make GPT Image 2 Follow Exact Layout Instructions](https://www.rewarx.com/blogs/how-to-make-gpt-image-2-follow-exact-layout-instructions)
- [GPT Image 2 Prompt Guide: 80+ Examples and API Tips](https://pixverse.ai/en/blog/gpt-image-2-review-and-prompt-guide)
- [How to Use GPT Image 2 in 2026?](https://fal.ai/learn/tools/how-to-use-gpt-image-2)
- OpenAI Community: [Image editing with mask](https://community.openai.com/t/help-with-images-edit-mask-not-constraining-edit-to-specific-area/1351283)
