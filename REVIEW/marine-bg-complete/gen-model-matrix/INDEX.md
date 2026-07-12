# bg-gen-matrix-v1 — model probe review (native-transparent + keyable arms)

Question this batch answers: (Q1) which gen models produce native transparent RGBA for
watercolor product art, vs gpt-image-1? (Q2) can any model reliably produce a keyable
uniform background when prompted?

Full research matrix (all models surveyed, incl. those we couldn't reach): see
`scratchpad/transparent-gen-matrix.md` (or ask for a copy — it's a session scratch file).
This INDEX covers only the 4 models we could actually probe live.

Same prompt motif across all 4 arms (marine sea turtle + coral + bubbles, watercolor,
plus the mandatory edge-hygiene block verbatim):
> watercolor illustration of a marine sea turtle swimming among coral branches, seaweed,
> and small bubbles, soft loose wet-on-wet watercolor washes, pastel teal/coral/gold
> palette, product-illustration style, isolated single subject, every object has clearly
> defined, fully closed outlines; no shape fades into the background; edges crisp;
> interior highlights enclosed by visible outlines

All raw outputs + metrics.json + edge crops (4x, on white/gray/black/magenta) live at:
`.../production files/double Marine Bed Wrapper/images/Images/candidates/bg-gen-matrix-v1/<arm>/`

Review board (side-by-side thumbnails): [review-board-4arms.png](review-board-4arms.png)

---

## Arm 1 — Recraft V4 (fal-ai/recraft/v4/text-to-image), keyable via `background_color`
- **Params:** `background_color: {r:255,g:0,b:255}` (magenta), `image_size: square_hd`, motif+hygiene prompt, `enable_safety_checker: false`. n=1.
- **Verdict: background_color param is unreliable — wrong hue rendered.** Requested magenta; sampled corner color = RGB(255, 2, 48), i.e. **solid crimson red**, 0.0% ΔE<5 to the requested magenta target (0.002% even at ΔE<60 "practical key" tolerance).
- Measured against its *own actual* fill color instead: 28.5% pixels ΔE<5, 44.8% ΔE<10, 54.7% at ΔE<15 — a moderately-but-not-perfectly flat fill, 0% edge-band spill, but 1063 enclosed background-colored pockets (mostly small gaps between coral branches, part of the illustration's real topology, not noise).
- File: [recraft_v4_magenta_out1.png](file:///Users/za/Library/CloudStorage/GoogleDrive-saar.shai%40gmail.com/My%20Drive/Wanderland%20Folder/Files/Products/Screenery/production%20files/double%20Marine%20Bed%20Wrapper/images/Images/candidates/bg-gen-matrix-v1/recraft-v4-keyable/recraft_v4_magenta_out1.png)
- Metrics: `recraft-v4-keyable/metrics.json` (vs requested magenta) and `metrics_actualcolor.json` (vs sampled actual color).
- Illustration quality: genuinely convincing wet-watercolor rendering (V4 has no explicit "watercolor" style enum — this came from prose alone).

## Arm 2 — Flux/dev (fal-ai/flux/dev), keyable via prompt-hack
- **Params:** motif+hygiene prompt + appended `"background: perfectly uniform solid pure magenta #FF00FF, zero texture, zero gradient, no magenta anywhere on the subject"`. `image_size: square_hd`, `enable_safety_checker: false`. n=1.
- **Verdict: total failure to follow the color instruction.** Sampled corner = RGB(253, 238, 235) — a pale blush/off-white, **0.0% match at any ΔE tolerance tested (5/10/60) to magenta.** The model also drifted away from "watercolor" toward a flatter, more vector-illustration look.
- File: [flux_dev_magenta_out1.png](file:///Users/za/Library/CloudStorage/GoogleDrive-saar.shai%40gmail.com/My%20Drive/Wanderland%20Folder/Files/Products/Screenery/production%20files/double%20Marine%20Bed%20Wrapper/images/Images/candidates/bg-gen-matrix-v1/flux-dev-keyable/flux_dev_magenta_out1.png)
- Metrics: `flux-dev-keyable/metrics.json`.

## Arm 3 — gpt-image-1 (OpenAI direct API `images/generations`), keyable via prompt-hack
- **Params:** motif+hygiene prompt + appended `"background: perfectly uniform solid pure magenta #FF00FF, flat solid fill, no watercolor texture in background, zero gradient, no magenta anywhere on the subject"`. `size: 1024x1024`, `quality: high`, `background: opaque`. n=1.
- **Verdict: best keyable arm of the three, by a wide margin.** Sampled corner = RGB(230, 4, 139) — a deep magenta/pink, still 0.0% ΔE<5 to *literal* #FF00FF, but **69.8%** of all pixels fall within the practical ΔE<60 key tolerance. Measured against its own actual color: **68.8% ΔE<5, 0% edge-band spill, only 4 enclosed pockets** (one real ~2258px gap between coral fronds, not noise). This is a materially better result than the prior-session green-screen probe (which had 28.45% edge spill) — the "flat solid fill, no watercolor texture in background" phrasing addition appears to be the effective lever.
- File: [gptimage1_magenta_out1.png](file:///Users/za/Library/CloudStorage/GoogleDrive-saar.shai%40gmail.com/My%20Drive/Wanderland%20Folder/Files/Products/Screenery/production%20files/double%20Marine%20Bed%20Wrapper/images/Images/candidates/bg-gen-matrix-v1/gpt-image-1-keyable-magenta/gptimage1_magenta_out1.png)
- Metrics: `gpt-image-1-keyable-magenta/metrics.json` (vs literal magenta) and `metrics_actualcolor.json` (vs sampled actual color).

## Arm 4 — LayerDiffuse (local ComfyUI, SDXL, Attention Injection), native RGBA
- **Setup:** Already installed at `/Users/za/ComfyUI` — `layer_xl_transparent_attn.safetensors` checkpoint + `ComfyUI-layerdiffuse` custom node were present before this session; missing Python dependency `diffusers` was installed into the ComfyUI venv (`pip install diffusers`, ~30s, no other blockers). MPS confirmed working.
- **Bug found + worked around:** the shipped `LayeredDiffusionDecodeRGBA` convenience node throws `AttributeError: 'JoinImageWithAlpha' object has no attribute 'join_image_with_alpha'` — the custom node is unmaintained against the current ComfyUI core's V3 node schema. Fix used: call the lower-level `LayeredDiffusionDecode` node instead (outputs IMAGE + MASK separately, and that path works), then composite RGBA myself in PIL (`alpha = 255 - mask`, matching the RGBA node's own formula).
- **Params:** SDXL base checkpoint (`sd_xl_base_1.0.safetensors`) + `layer_xl_transparent_attn` LoRA patch (`LayeredDiffusionApply`, config "SDXL, Attention Injection", weight 1.0), same motif+hygiene prompt, negative "text, watermark, background scenery, frame, border", 1024x1024, 20 steps euler/normal, cfg 8. n=1.
- **Verdict: real alpha channel, but semantically wrong for this prompt.** 80.96% of pixels fully transparent, 19.04% semi, essentially 0% (0.001%) fully opaque. Critically, **the alpha mask does not track the turtle subject** — see [layerdiffuse_sdxl_out1_mask-raw.png](file:///Users/za/Library/CloudStorage/GoogleDrive-saar.shai%40gmail.com/My%20Drive/Wanderland%20Folder/Files/Products/Screenery/production%20files/double%20Marine%20Bed%20Wrapper/images/Images/candidates/bg-gen-matrix-v1/layerdiffuse-sdxl-local/layerdiffuse_sdxl_out1_mask-raw.png): opacity concentrates in scattered blotches near the canvas edges/corners, while the turtle itself (clearly visible in the underlying RGB) ends up mostly transparent. This matches LayerDiffuse's known training assumption — its FG mode expects a single-object-floating-in-void prompt, not a full scene description (turtle+coral+bubbles+water) in one sentence, and this probe used the same full-scene prompt as the other 3 arms for a fair comparison rather than special-casing it.
- Files: [layerdiffuse_sdxl_out1_rgba.png](file:///Users/za/Library/CloudStorage/GoogleDrive-saar.shai%40gmail.com/My%20Drive/Wanderland%20Folder/Files/Products/Screenery/production%20files/double%20Marine%20Bed%20Wrapper/images/Images/candidates/bg-gen-matrix-v1/layerdiffuse-sdxl-local/layerdiffuse_sdxl_out1_rgba.png) (composited RGBA), `_rgb-raw.png` / `_mask-raw.png` (raw node outputs before my composite).
- Metrics: `layerdiffuse-sdxl-local/metrics.json`.

---

## Ranking

**(a) Native-transparent watercolor gen:** gpt-image-1 (KNOWN-good from prior session) >> local LayerDiffuse (real alpha but subject/background separation was wrong on this prompt style; would need a stripped single-object prompt to get a fair second look, not attempted here).

**(b) Keyable-bg gen:** gpt-image-1 prompt-hack (69.8% practical-key match, 0% spill, only 4 minor pockets) > Recraft V4 `background_color` (flat-ish fill but wrong hue delivered, 1063 pockets from coral-gap topology) > Flux/dev prompt-hack (ignored the instruction entirely, 0% match).

**Best next candidate we cannot yet reach:** OpenAI **gpt-image-2** — its OpenAI-hosted API (not the fal proxy, which lacks a `background` param) was not tested in this session. If it shares gpt-image-1's `background=transparent` API surface, it is the single most promising untested lead for Q1, reachable with the same `.secrets/openai.env` key already in hand — just not exercised here to stay inside the assigned probe scope (brief named gpt-image-1 specifically for the comparison arm). Stability AI's own API is the other named-but-unreachable item (no key in `.secrets/`).
