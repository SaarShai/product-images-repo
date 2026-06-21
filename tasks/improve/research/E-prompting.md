# E — Prompting & Reference-Conditioning Best Practices for Instruction-Edit Image Models

Research goal: make our edits more reliable on the four pain points — **no added text/signage**,
**style-match (no realism drift)**, **position/scale lock (no reframing/zoom)**, and
**cross-instance consistency** — across our stack: fal Flux Kontext
(`fal-ai/flux-pro/kontext`), Flux.2-pro edit (`fal-ai/flux-2-pro/edit`, `image_urls[]`),
Flux Fill, and OpenAI gpt-image-1 edits.

Researched 2026-06-21. Sources verified against official docs where possible; community/
republished sources flagged inline. **Prefer official docs; do not treat the templates below
as guaranteed — they encode the documented rules but must be A/B-tested per the repo's
feedback-dual-track LAW.**

---

## 0. The single most important rule (matches our LAW 0)

Both BFL guides and the OpenAI cookbook converge on the same principle our memory already
encodes: **be explicit and specific; name what stays, name what changes; drive with references
+ geometry, not vague prose.** Vague edits ("make it better", "transform") license the model to
reframe, restyle, and re-imagine. Surgical, named edits constrain it.

> "Making things more explicit never hurts if the number of instructions per edit is not too
> complicated." — BFL Kontext i2i guide (via official prompting guide).

---

## 1. FLUX.1 Kontext (`fal-ai/flux-pro/kontext`) — instruction edits

Official source: Black Forest Labs prompting guide for Kontext image-to-image
(`docs.bfl.ml/guides/prompting_guide_kontext_i2i` — note: BFL now redirects new projects to
FLUX.2). Verbatim examples below are from BFL's guide as republished by Replicate's official
write-up. **Note: BFL says FLUX.2 is the recommended successor for editing.**

### 1.1 Prevent reframing / zoom / position drift (our car-recentred bug)

**Rule:** state preservation explicitly — Kontext does NOT preserve composition unless told to.
Append an explicit "keep" clause naming position, scale, camera, framing, perspective.

- Verbatim: *"Change the background to a beach while keeping the person in the exact same position, scale, and pose. Maintain identical subject placement, camera angle, framing, and perspective."*
- Verbatim (background swap): *"Change the background to a beach while keeping the person in the exact same position"* + *"maintain identical subject placement, camera angle, framing, and perspective."*

**Template fragment (always append to any Kontext edit):**
> `... while keeping everything else exactly the same — identical composition, the same camera angle, framing, crop, perspective, position and scale of all elements. Do not zoom, do not recenter, do not reframe.`

### 1.2 Preserve identity / character

**Rule:** explicitly list the identity markers to hold constant (facial features, hairstyle,
clothing, color), and re-name the subject rather than using pronouns.

- Verbatim: *"while keeping the same facial features"*, *"maintain the same person"*.
- Verbatim do/don't on naming: use *"the woman with short black hair"* / *"the red car"*, and **"Avoid pronouns—they're often too vague."** ("it", "her", "this" cause drift.)

### 1.3 Text control (no added/changed text; correct text when wanted)

**Rule (correct text):** put the literal text in quotes with the replace pattern.
- Verbatim: *"Replace '[original text]' with '[new text]'"* — and "Be exact … writing 'replace x with y' works better than general instructions."
- Verbatim example: *"Change the text in the sunglasses to be 'FLUX' and 'Kontrast'"*; BFL's own example replaces "joy" with "BFL" in a "Choose joy" sign.
- Use clear/readable fonts; "Complex or stylized fonts may be harder to edit."

**Rule (no unwanted text):** Kontext has no negative prompt. The reliable lever is a positive
preservation clause + an explicit "no text" instruction phrased positively. Add:
> `Keep all surfaces, walls, and signage blank and unlabeled; add no text, letters, words, logos, watermarks, or signage of any kind.`
(Phrasing it as "keep blank" gives the model something to *do* rather than a negation it may drop.)

### 1.4 Style transfer / avoid realism drift

**Rule:** name the exact style/movement and its concrete traits; do not say "make it artistic".
- Verbatim do/don't: Poor — *"make it better"*, *"make it artistic"*; Strong — name styles like *"impressionist painting"*, *"watercolor sketch"*, movements like *"Renaissance"*, *"1960s pop art"*, with traits *"visible brushstrokes, thick paint texture, and rich color depth."*
- For our realism-drift problem: explicitly forbid photorealism by *prescribing* the target medium ("flat 2D storybook gouache illustration, hand-painted, no photographic shading") rather than just "keep the style."

### 1.5 Verb choice

**Rule:** verbs scope the edit. **"transform" implies a full identity rework** (causes drift);
**"change the clothes" / "replace the background"** is scoped and safer. Prefer
change / replace / swap / recolor over transform / reimagine / restyle.

---

## 2. FLUX.2 / Flux.2-pro edit (`fal-ai/flux-2-pro/edit`, `image_urls[]`)

Official source: BFL FLUX.2 prompting guide (`docs.bfl.ml/guides/prompting_guide_flux2`) and
FLUX.2 image-editing page (`docs.bfl.ml/flux_2/flux2_image_editing`). FLUX.2 launched 2025-11-25.

### 2.1 Prompt structure & length

- Framework: **Subject + Action + Style + Context**. "Word order matters — FLUX.2 pays more attention to what comes first." Put the most important elements first: Main subject → Key action → Critical style → Essential context → Secondary details.
- Length: 10–30 words quick; **30–80 words "usually ideal for most projects"**; 80+ for complex scenes.

### 2.2 NO negative prompts

- Verbatim: **"FLUX.2 does not support negative prompts. Focus on describing what you want, not what you don't want."** ⇒ for "no text", phrase positively ("surfaces remain blank/unlabeled"), do not write "no text" as a negative-prompt field.

### 2.3 Multi-reference (`image_urls[]`) — roles, counts, consistency

- Counts: **up to 8 reference images via API**, up to 10 in playground. [pro] has a **9MP total budget for input+output**; at 1MP output you can use ~8 refs (more refs ⇒ lower per-image res).
- **Assign each reference an explicit role in the prompt.** Verbatim: *"When using multiple input images, clearly describe the role of each: subject from image 1, style from image 2, background from image 3."*
- Refer to images positionally by **"image 1", "image 2"** (BFL's editing examples: *"Place the chickens from image 1 in their new home"*, *"the wood from image 5"*, *"Apply the style of image 1 to the entire new scene"*). **Order of `image_urls[]` therefore matters — keep a fixed convention (e.g. element[0]=structure/identity, [1]=style, [2]=approved-instance).**
- **Cross-instance consistency:** repeat the *same detailed description* of the character/product in every prompt. Verbatim: *"Notice how Diffusion Man's description stays detailed and consistent across panels … Repeat these details in every panel prompt."* (Use a frozen description block + the approved instance as a reference image.)

### 2.4 Position / scale on FLUX.2

The guide does not give a one-liner "preserve composition" clause for edit; it controls position
via **explicit spatial descriptors** ("Right side of the black mug on polished concrete surface",
"Center foreground …") and camera terms ("high angle", "medium shot", "rule of thirds"). For
position-lock on an edit, combine a Kontext-style "keep the same composition/scale/framing" clause
with explicit spatial descriptors.

### 2.5 Text on FLUX.2

- Quote the literal string and specify placement/style/color/size. Verbatim: *"The text 'OPEN' appears in red neon letters above the door"*; describe style (*"elegant serif typography"*, *"bold industrial lettering"*), size (*"large headline text"*), and **hex for brand color** (*"the logo text ACME in color #FF5733"*).
- No-text: same positive-preservation approach as §1.3.

---

## 3. OpenAI gpt-image-1 / gpt-image-1.5 edits

Official sources: OpenAI image-generation guide (`developers.openai.com/api/docs/guides/image-generation`),
edit API reference (`.../api/reference/python/resources/images/methods/edit`), and the cookbook
"Generate images with high input fidelity".

### 3.1 `input_fidelity` — the key lever for our style/identity drift

- Values **`high` | `low`**, default `low`; supported on **gpt-image-1 and gpt-image-1.5** (NOT gpt-image-1-mini). "Controls how much effort the model will exert to match the style and features, **especially facial features**, of input images."
- Verbatim: *"Setting `input_fidelity='high'` is especially useful when editing images with faces, logos, or any other details that require high fidelity in the output."*
- **First-image bonus:** *"While all input images are preserved with high fidelity, only the first one you provide is preserved with extra richness in texture."* ⇒ put the image we most need to preserve **first**.
- Recommended pairing in the cookbook: `input_fidelity="high"`, `quality="high"`, `output_format="jpeg"`.
- Caveats from OpenAI dev forum (community, not official): chaining many high-fidelity edits can introduce graininess, and there have been reported regressions of `input_fidelity` with masked edits — re-test before relying on it.

### 3.2 Mask behavior (Flux Fill analog on the OpenAI side)

- Mask is a PNG with an **alpha channel**; **transparent (alpha=0) areas = the region to edit**; opaque = keep. Mask must match the image's format/size and be < 4MB (guide also cites <50MB for newer models) and **applies to the first input image** if several are provided.
- Verbatim: **"masking with GPT Image is entirely prompt-based. The model uses the mask as guidance, but may not follow its exact shape with complete precision."** ⇒ a soft rectangular mask leaks repaint outside the intended element (matches our element-edit diff-mask memory). Use a tight element-shaped mask and a **diff-driven composite** to keep outside-mask bytes exact.
- **Inpainting prompt requirement:** describe the *whole intended image*, not just the patch — gpt-image regenerates in context, so the prompt should restate the scene so the unmasked content is reaffirmed.

### 3.3 Text

- Official limitation: **"the model can still struggle with precise text placement and clarity."** Correct text is improved but not guaranteed.
- For no-text: state it positively in the prompt ("all signage blank"), and crucially **mask out** any region prone to spurious signage so it's locked.

### 3.4 Parameters

- `quality`: low/medium/high (low = fast drafts); `size` square/portrait/landscape (gpt-image-1 caps ~1024–1536 per side; matches our memory that gpt-image caps ~896×1792 — upscale for hi-res). `background` transparent/opaque/auto.

---

## 4. Qwen-Image-Edit (fallback engine)

Official sources: Qwen blog (`qwenlm.github.io/blog/qwen-image-edit/`), Qwen-Image report
(`arxiv.org/pdf/2508.02324`). Community prompt threads on HF.

- Architecture: feeds the input image to **Qwen2.5-VL for semantic control AND the VAE encoder for appearance control** ⇒ strong at both "what it is" and "how it looks"; SOTA text editing.
- **Best at precise text edits**: "direct addition, deletion, and modification of text … while preserving the original font, size, and style", bilingual (EN/中文). ⇒ route text-heavy edits here.
- It uses an LLM as the text encoder, so **natural-language instructions work** ("just talk to it"); still apply our rules: name what to keep, quote literal text, name the subject.
- Recommended structure (community): Subject + Style/Medium + Lighting/Mood + Composition + Quality; "clearly specify what to keep or change."

---

## 5. Reference / IP conditioning — style-lock & cross-instance consistency

Sources: XLabs FLUX IP-Adapter model cards + discussions (HuggingFace), FLUX.1-Redux-dev
(Stable Diffusion Art / ComfyUI-nunchaku DeepWiki), "Only-Style" paper (arXiv 2506.09916),
plus FLUX.2 multi-ref (§2.3).

- **Two reference channels, keep them separate:** *structure/identity* (what + where) vs *style* (look). Mixing them in one high-weight reference is what breaks consistency.
- **Flux Redux** is purpose-trained for style/visual conditioning and outperforms the unofficial XLabs IP-Adapter for retaining style. Strength on Redux is set by **downsampling_factor** (1=strongest … 9=weakest); lower it to let the prompt/structure through, raise it to lock style.
- **IP-Adapter weight ~1.0–1.15** typical; **high weight needed for the aesthetic "breaks" consistency when combined with ControlNet** — so for "exact geometry + exact style" you must *decouple*: ControlNet/structure-guide for geometry at modest strength, style reference at the weight that holds the look, and accept iteration (matches our geometry-must-be-a-measured-gate memory).
- **Cross-instance (same character/car many times):** the robust recipe across all engines is
  **(a) approve one canonical instance, (b) feed that approved instance back as a reference**
  (Flux.2 `image_urls[]`, IP-Adapter/Redux image), **(c) repeat a frozen text description** of the
  subject in every prompt, **(d) judge the whole set together**, not one at a time (our
  reference-lock-for-consistency memory).
- **How many refs:** Flux.2 up to 8 (API); more refs trade resolution. For consistency keep it
  lean — 1 structure + 1 style + 1 approved-instance is usually enough; piling on refs dilutes each.

---

## 6. Seed / guidance / strength

- **Seed:** fix the seed to make an edit reproducible and to A/B one prompt change at a time
  (fal exposes `seed` on Kontext/Flux.2/Fill). Vary seed only when you want fresh candidates;
  hold it fixed when isolating a prompt/parameter change.
- **Guidance (Kontext `guidance_scale`, default ~2.5–3.5):** higher = closer prompt adherence but
  more drift/over-baking; lower = gentler, preserves more of the source. For *preserve-heavy*
  edits keep guidance modest. (fal/BFL defaults are a sane start; tune empirically.)
- **Strength / denoise (img2img & Flux Fill):** the dominant fidelity knob. **Low strength = stays
  close to the input (less reframing, less drift); high strength = more change.** For "redraw one
  element, keep everything else" use the *lowest* strength that still makes the change, plus a tight
  mask. (Note from our memory: blob-mask Flux Fill won't *widen* an element — for reshape use
  PIL-stretch → Kontext cleanup → element-shaped mask composite.)
- **gpt-image:** `input_fidelity="high"` + `quality="high"` is the fidelity pairing; there is no
  strength slider — control is via mask tightness + prompt restating the scene.

---

## 7. DELIVERABLE — reusable templates

### (i) Redraw ONE element, keep position/scale/style, NO added text

**Kontext / Flux.2 (instruction edit):**
```
Replace only the <ELEMENT> with <NEW ELEMENT, concrete visual description>.
Keep everything else exactly the same: identical composition, the same camera angle,
framing, crop, and perspective; the same position, scale, and proportions of every element;
the same <art style / medium — name it, e.g. flat 2D storybook gouache, hand-painted>,
the same colors and lighting. Do not zoom, recenter, reframe, or crop.
Keep all surfaces and signage blank and unlabeled — add no text, letters, words, logos,
or watermarks of any kind.
```
- Name the element by description, never a pronoun. Use "replace/change", never "transform".
- fal params: low strength / lowest denoise that works; fixed seed; modest guidance.

**gpt-image-1 (masked):** tight element-shaped transparent mask over `<ELEMENT>` only;
`input_fidelity="high"`, `quality="high"`; put the must-preserve image **first**; prompt restates
the *whole* scene + the no-text clause; then **diff-mask composite** the result back so outside-mask
pixels stay byte-exact.

### (ii) Fit / restyle to a target look

```
<SUBJECT + ACTION, most important first>. Render in <EXACT STYLE: medium, movement, named
traits — e.g. flat 2D storybook gouache, visible brush texture, matte, no photographic shading,
no 3D rendering, no realism>. Apply the style of image <N> to the entire scene while keeping the
structure, layout, and proportions of image <M> unchanged. Keep the composition and framing of
the source; do not reframe or zoom. <30–80 words.>
```
- Forbid realism by *prescribing the medium*, not by negating (FLUX.2 has no negative prompt).
- Decouple: structure-guide/ControlNet for geometry, style reference (Redux/IP-Adapter or
  Flux.2 style image) for look; gate geometry on **measured silhouette IoU**, not a VLM blend.

### (iii) Cross-instance CONSISTENCY recipe (same character/car, many panels)

1. Generate candidates → **approve ONE canonical instance**.
2. Freeze a **detailed text description block** of the subject (every distinguishing trait,
   colors as hex where brand-critical) and **paste it verbatim into every panel prompt**.
3. **Feed the approved instance as a reference image** in every subsequent generation:
   Flux.2 `image_urls[]` ("the <subject> from image 1, exactly as shown"), or IP-Adapter/Redux.
4. Keep a **fixed `image_urls[]` order convention** (e.g. [0]=structure/geometry guide,
   [1]=style ref, [2]=approved instance) and reference them as "image 1/2/3".
5. Hold seed/guidance constant across the set; vary only the per-panel scene text.
6. **Judge the whole set together** (≥3 judges, our gate), not panel-by-panel — drift only shows
   in comparison.

---

## 8. DO / DON'T phrasing cheat-sheet

**DO**
- Name what stays: "keep the exact composition, camera angle, framing, position, and scale."
- Name the subject: "the red car", "the woman with short black hair."
- Scope verbs: change / replace / swap / recolor.
- Quote literal text: `Replace 'OLD' with 'NEW'`; specify font/placement/hex.
- Prescribe the medium to avoid realism drift: "flat 2D gouache illustration, no photographic shading."
- Positive no-text: "surfaces and signage remain blank and unlabeled."
- Assign reference roles: "structure from image 1, style from image 2."
- Repeat the frozen subject description in every consistency panel.
- Put the must-preserve image **first** (gpt-image first-image fidelity bonus).
- Fix the seed; use lowest strength/denoise that achieves the change; tight masks.

**DON'T**
- Use pronouns ("it", "her", "this") — too vague, causes drift.
- Use "transform / reimagine / restyle" when you mean a scoped change.
- Rely on negative prompts (FLUX.2 has none; "no text" alone is weak) — phrase positively.
- Say "make it better / more artistic" — name the exact style + traits.
- Trust a loose rectangular mask to contain a gpt-image edit — it leaks; diff-composite.
- Pile on reference images — more refs dilute each; keep 1 structure + 1 style + 1 instance.
- Claim fit/consistency from a number — judge with the overlay and the whole set (repo LAW).

---

## Sources (verified)
- BFL Kontext i2i prompting guide — https://docs.bfl.ml/guides/prompting_guide_kontext_i2i (and FLUX.2 redirect note)
- BFL FLUX.2 prompting guide — https://docs.bfl.ml/guides/prompting_guide_flux2
- BFL FLUX.2 image editing — https://docs.bfl.ml/flux_2/flux2_image_editing
- BFL FLUX.2 announcement — https://bfl.ai/blog/flux-2
- Replicate (official Kontext write-up, verbatim BFL examples) — https://replicate.com/blog/flux-kontext
- OpenAI image generation guide — https://developers.openai.com/api/docs/guides/image-generation
- OpenAI image edit API reference — https://developers.openai.com/api/reference/python/resources/images/methods/edit
- OpenAI cookbook, high input fidelity — https://developers.openai.com/cookbook/examples/generate_images_with_high_input_fidelity
- Qwen-Image-Edit blog — https://qwenlm.github.io/blog/qwen-image-edit/ ; report — https://arxiv.org/pdf/2508.02324
- FLUX.2 [pro] edit on fal (image_urls[]) — https://fal.ai/models/fal-ai/flux-2-pro/edit
- XLabs FLUX IP-Adapter (weight/ControlNet consistency) — https://huggingface.co/XLabs-AI/flux-ip-adapter-v2/discussions/19
- FLUX.1 Redux (style conditioning, downsampling_factor) — https://stable-diffusion-art.com/flux-redux/
- Only-Style (style consistency without content leakage) — https://arxiv.org/pdf/2506.09916

*Note on confidence: BFL Kontext verbatim examples are sourced via Replicate's official republished
guide because docs.bfl.ml/.../prompting_guide_kontext_i2i returned 404 on direct fetch (the page
exists in search index; BFL is migrating editing docs to FLUX.2). FLUX.2, OpenAI, and Qwen findings
are from official domains. Treat all templates as hypotheses to A/B-test, not guarantees.*
