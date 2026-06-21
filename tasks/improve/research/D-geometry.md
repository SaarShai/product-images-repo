# D — Geometry-Exact Generation: fitting artwork to a die-cut SVG contour

Research goal: make generated artwork **fill an exact die-cut SVG contour, leave
cutouts / keep-clear red zones empty, and adapt a top-contour silhouette** — by
*conditioning* generation on the geometry, instead of free-form generation we
then crop.

Date: 2026-06-21. Sources verified via WebSearch/WebFetch where marked
[verified]. Anything I could not open directly is marked [UNVERIFIED].

---

## 0. What the repo already has (ground truth — read before adding tools)

The codebase has already implemented much of the recommended pipeline. Relevant
scripts in `scripts/`:

- `svg_to_controlmap.py` — renders the **exact** SVG geometry (outer contour +
  every cutout) to a crisp lineart/canny conditioning map at a chosen pixel
  size, mapped from the SVG viewBox the same way `svg_geometry_check.py` maps
  back. This is the correct SVG→ControlNet conditioning image. **(SVG→control
  pipeline already solved locally.)**
- `controlnet_sdxl_gen.py` — SDXL base + `xinsir/controlnet-canny-sdxl-1.0`,
  control image = the SVG lineart (invert for canny). MPS device.
- `controlnet_inpaint_gen.py` — **the exact-geometry route**: ControlNet (locks
  the contour) + inpaint mask built from SVG geometry so openings are *masked
  out by construction* (region-IoU → ~1.0), model only paints the body. Uses
  SD1.5 `lllyasviel/control_v11p_sd15_lineart` today.
- `build_silhouette_base.py` — flood-fill silhouette base for edge-socket /
  open-path boundaries (the recipe from memory `edge-socket-panel-recipe`).
- `mask_to_svg.py`, `register_to_svg.py`, `svg_geometry*.py`, `skyline_panel.py`
  (spec → guide + check), `svg_manifest.py`, `falgen.py`, `localgen.py`,
  `openai_edit.py`.

So the gap is **not** "how to turn an SVG into a control map" (done) — it is
(a) the SD1.5 inpaint route gives weak style, and (b) the SDXL/gpt-image
single-pass routes give good style but weak *contour adherence*. The fix is to
combine **a strong base + a structure ControlNet (or Fill/inpaint) at high
conditioning + a hard mask for holes**, and to move the base up to SDXL/FLUX.

---

## 1. ControlNet for geometry (canny / lineart / scribble / depth / seg)

The conditioning image is what these models honor. For a die-cut panel the
right conditioning is the **exact SVG lineart** (`svg_to_controlmap.py`),
optionally a **depth/segmentation** map (panel = near, holes = far/background).
Canny/lineart/scribble all want the contour as crisp strokes; this is a perfect
match because the line is synthetic and exact (no Canny-of-a-photo noise).

### SDXL ControlNets (run on MPS via diffusers; free/local)

| Model | id | license | conditioning | effort | fit |
|---|---|---|---|---|---|
| xinsir Canny SDXL | `xinsir/controlnet-canny-sdxl-1.0` | apache-2.0 (repo family) | white-on-black edges (our SVG lineart, inverted) | S — already wired | **High.** Best community SDXL canny; contour is exact line, ideal input. |
| xinsir Scribble SDXL | `xinsir/controlnet-scribble-sdxl-1.0` | apache-2.0 | thick black strokes | S | High — tolerant of rough strokes, good for top-contour silhouette. |
| xinsir Depth SDXL | `xinsir/controlnet-depth-sdxl-1.0` | apache-2.0 | depth (panel near / holes far) | M (build depth map) | Med — depth pushes holes to "background", complements canny for emptiness. |
| **xinsir Union SDXL** | `xinsir/controlnet-union-sdxl-1.0` | apache-2.0 | one model, 6+ types (canny/depth/scribble/seg/pose/normal) | S | **High** — one download covers canny+scribble+depth; simplest SDXL upgrade. [verified license apache-2.0] |
| diffusers Canny/Depth SDXL | `diffusers/controlnet-canny-sdxl-1.0`, `diffusers/controlnet-depth-sdxl-1.0` | openrail++ | same | S | Med — official, but xinsir is stronger per community. **[verified: both have HF discussions with working Apple-Silicon M1 Max code]** |

MPS notes [verified]: SDXL+ControlNet runs on Apple Silicon but is memory-heavy
— M1 Max/64 GB fine, 16 GB machines OOM on SDXL+CN img2img. Drop
`torch_dtype=torch.float16` where MPS chokes (or upcast layernorm to fp32),
set `PYTORCH_ENABLE_MPS_FALLBACK=1`, 15–20 steps. The repo already runs SDXL on
MPS, so this is proven on this host.

### FLUX ControlNets

| Model | id | license | conditioning | local/API | effort | fit |
|---|---|---|---|---|---|---|
| **FLUX.1 Canny [dev]** (BFL, full model) | `black-forest-labs/FLUX.1-Canny-dev` | FLUX.1 [dev] **Non-Commercial** | canny edges (our lineart) | local (12B, heavy for MPS) or API | M/L | **High structure**, but it's a full 12B model not an adapter — heavy. Non-commercial. [verified license] |
| FLUX.1 Canny [dev] LoRA | `black-forest-labs/FLUX.1-Canny-dev-lora` | FLUX.1 [dev] NC | canny | API/local | M | Same control, lighter (LoRA on FLUX.1-dev). [verified] |
| FLUX.1 Depth [dev] | `black-forest-labs/FLUX.1-Depth-dev` | FLUX.1 [dev] NC | depth | API/local | M | Depth = holes-as-background. [verified family] |
| InstantX Canny | `InstantX/FLUX.1-dev-Controlnet-Canny` | FLUX.1 [dev] **Non-Commercial** | canny | API/local | M | adapter (lighter than BFL full model); `controlnet_conditioning_scale≈0.6`, 28 steps, guidance 3.5. [verified] |
| InstantX Union | `InstantX/FLUX.1-dev-Controlnet-Union` | FLUX.1 [dev] NC | multi | API/local | M | one adapter, multiple types. [verified] |
| Shakker Union Pro 2.0 | `Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro-2.0` | FLUX.1 [dev] **Non-Commercial** | canny/softedge/depth/pose/gray | API/local | M | Strong unified FLUX CN; v2.0 is 3.98 GB (was 6.15), improved canny. [verified] |
| XLabs Canny v3 | `XLabs-AI/flux-controlnet-canny-v3` | (XLabs; check repo) | canny | local/ComfyUI | M | community alt. [UNVERIFIED license] |

> **License flag:** every FLUX.1 [dev] ControlNet (BFL, InstantX, Shakker,
> XLabs) inherits the **FLUX.1 [dev] Non-Commercial License**. Generated
> *outputs* are usable for personal/commercial per the dev license, but the
> *model weights* are non-commercial. SDXL xinsir/diffusers CNs (apache /
> openrail++) are the clean commercial-safe local path. [verified]

---

## 2. Mask-confining / regional methods (force holes empty, confine to contour)

These are the "make the cutouts stay empty" half of the problem. The
exact-geometry guarantee comes from a **hard mask**, not from prompting.

| Technique | what it is | URL [verified] | local/API | conditioning | effort | fit |
|---|---|---|---|---|---|---|
| **ControlNet + inpaint mask** (repo's `controlnet_inpaint_gen.py`) | mask openings out so they're never generated; CN locks contour; model paints only body | (in repo) | local MPS | SVG lineart + binary opening mask | S (done; needs SDXL upgrade) | **Best exact route.** region-IoU→~1.0 by construction. Currently SD1.5 → weak style; port to SDXL inpaint. |
| SDXL inpainting model | `diffusers/stable-diffusion-xl-1.0-inpainting-0.1` | huggingface.co/diffusers/stable-diffusion-xl-1.0-inpainting-0.1 | local MPS | image + mask | S | High — drop-in SDXL replacement for the SD1.5 inpaint base; combine w/ CN canny. [verified exists] |
| **Differential Diffusion** | per-pixel *soft* mask: a change-map (grayscale) sets how much each region may change (0=frozen, 255=free) | huggingface.co/blog/OzzyGT/outpainting-differential-diffusion ; mybyways.com/blog/differential-diffusion-for-in-painting | local (diffusers) + **fal** | init image + **change_map** | M | **High.** Lets the body be freely painted while the contour edge / hole rims stay frozen — softer than a binary mask, no seam. |
| SoftFill / Flux differential inpaint | diffusers pipelines built on Diff-Diffusion that act like soft-inpaint without extra steps | github.com/zacheryvaughn/softfill-pipelines ; github.com/mofos/Flux_Differential-diffusion_Inpainting_Diffusers | local | image + blurred mask + perlin noise in mask | M | Med/High — robust soft-inpaint; the noise-in-mask trick aligns output to mask shape. [verified repos exist] |
| Regional / Attention Couple | bind different prompts to mask regions (e.g. "panel body" vs "empty") | github.com/pamparamm/ComfyUI-ppm (Attention Couple SDXL) ; stable-diffusion-art.com/regional-prompter | local (ComfyUI — installed) | per-region masks + prompts | M | Med — controls *content placement*, not a hard empty guarantee; weaker than a mask for "keep this hole empty". |
| Latent Couple | older region-conditioning (superseded by Attention Couple) | stable-diffusion-art.com/regional-prompter | local | region masks | M | Low/Med — legacy; use Attention Couple instead. |
| IP-Adapter (style) regional | `IPAdapter_plus` (installed) for style, can be masked | (ComfyUI custom node, installed) | local | style ref image + mask | M | Style fidelity, not geometry — pairs *with* a CN, doesn't replace it. |

**Key insight:** binary inpaint mask = hardest guarantee for holes/keep-clear
(they are literally not generated). Differential Diffusion = same idea but a
*graded* mask, giving a clean painted body up to the rim with no hard seam —
the best of both. Regional/Attention Couple is for *what goes where*, not *what
stays empty*, so it's a complement, not the answer.

---

## 3. img2img / structure-guide strength tuning

To honor a guide while restyling, the dial is **denoise strength** (img2img) or
**conditioning_scale + start/end percentage** (ControlNet):

- **ControlNet `conditioning_scale`**: 0.6–0.9 for FLUX adapters (InstantX
  recommends 0.6), ~0.9–1.2 for SDXL canny on a synthetic crisp line. Higher =
  tighter contour, lower = more style freedom. [verified InstantX 0.6/28/3.5]
- **`control_guidance_start/end`** (HF) / fal `start_percentage`/`end_percentage`
  [verified fal field names]: apply the CN only for the **first** part of
  denoising (e.g. end at 0.5–0.7) so structure is locked early, then let the
  model paint freely late — gives style without contour drift.
- **img2img `strength`** (fal: `1.0` remakes, `0.0` preserves; default 0.85)
  [verified]: feed the grey geometry guide as init at strength ~0.7–0.85 to
  keep aspect+focal while restyling.
- **Differential strength**: fal `fal-ai/flux-general/differential-diffusion`
  `strength` default 0.85 [verified] combined with the change-map graded values.

Memory cross-ref: `geoguide-input-locks-aspect` (grey geometry guide as image-1
locks aspect, esp. narrow 0.39) and `geometry-must-be-measured-gate` (gate on
measured silhouette IoU, never a VLM score) both apply here — tune strength,
then **measure** region/silhouette IoU.

---

## 4. SVG → conditioning images (mask, lineart, depth)

This is largely solved in-repo (`svg_to_controlmap.py`). Recommended outputs to
generate from one SVG, all in panel-pixel space (viewBox-mapped):

1. **Lineart / canny map** — outer contour + cutouts as crisp strokes. (done)
   - canny ControlNet wants white-on-black (`--invert`); lineart wants
     black-on-white. `svg_to_controlmap.py --style {lineart|canny}` does both.
2. **Binary opening mask** — white = paintable body, black = holes/keep-clear
   (so inpaint/Fill never touches them). Build from the same classified paths
   (`svg_classify`); `controlnet_inpaint_gen.py` already does this.
3. **Differential change-map** — grayscale: 255 in body interior, 0 over
   holes + a black ring along the contour edge and hole rims, soft-blurred
   between. Feed as `change_map_image_url`. (new, small script — extend
   `svg_to_controlmap.py`.)
4. **Depth map** — body = bright/near, holes = dark/far. Optional, for a depth
   CN to reinforce "holes are background". (new, small.)
5. **Grey geometry guide** — already produced by `skyline_panel.py`/the guide
   path; locks aspect for single-pass gpt-image. (done)

No external "SVG→ControlNet" tool is needed or recommended — rendering the SVG
ourselves is *more* exact than any learned line detector, because there is no
photo to detect; the geometry is authoritative. (This is the repo's existing
design and it's the right one.)

---

## 5. FLUX-specific control (Fill / Canny / Depth / Redux)

| Tool | id / endpoint [verified] | what | license | conditioning |
|---|---|---|---|---|
| **FLUX.1 Fill [dev]** | `black-forest-labs/FLUX.1-Fill-dev`; fal `fal-ai/flux-general/inpainting` (also `fal-ai/flux-lora-fill`, pro: `fal-ai/flux-pro/v1/fill`) | dedicated inpaint/outpaint — fills a masked region from a prompt, keeps unmasked frozen | dev Non-Commercial | `image_url` + `mask_url` (fal) / image+mask (HF). Recommended `guidance_scale=30`, `steps=50`. **Caveat (BFL docs): slight color shift outside mask + lines at filled-area edges** — so re-paste original outside the mask after. |
| FLUX.1 Canny [dev] | `black-forest-labs/FLUX.1-Canny-dev` (+`-lora`) | structure from canny | dev NC | canny map |
| FLUX.1 Depth [dev] | `black-forest-labs/FLUX.1-Depth-dev` | structure from depth | dev NC | depth map |
| FLUX.1 Redux [dev] | `black-forest-labs/FLUX.1-Redux-dev`; fal `fal-ai/flux/dev/redux` | image-variation adapter (style/restyle of an input image) | dev NC | image (+ optional prompt) |
| **fal flux-general (CN+LoRA+IP)** | `fal-ai/flux-general/image-to-image` | one endpoint: controlnets, controlnet_unions, ip_adapters, masks | API (paid) | `control_image_url`, `mask_image_url`, `mask_threshold` (0.5), `conditioning_scale` (1), `start/end_percentage`, `image_url`, `strength` (0.85) [all verified field names]; control methods canny/depth/inpainting/pose/seg/subject |
| **fal flux differential-diffusion** | `fal-ai/flux-general/differential-diffusion` | graded change-map img2img + CN/IP | API (paid) | `image_url`, **`change_map_image_url`**, `strength` (0.85), plus controlnets/ip_adapters [verified] |

fal note: "only one controlnet supported at a time" on flux-general [verified].
The repo's `falgen.py` (Key auth) is the existing fal wrapper to extend.

---

## RANKED recommendations — "fill exact contour, holes empty, adapt top silhouette"

The exactness must come from a **mask/structure conditioning**, never from
prompt wording, and must be **measured** (region/silhouette IoU), per repo
memory. Ranked:

1. **[BEST, free/local, commercial-safe] SDXL inpaint + xinsir canny ControlNet,
   driven by the SVG lineart + a binary opening mask.** This is the repo's
   existing `controlnet_inpaint_gen.py` route **upgraded from SD1.5 to SDXL**:
   - base: `diffusers/stable-diffusion-xl-1.0-inpainting-0.1`
   - controlnet: `xinsir/controlnet-canny-sdxl-1.0` (or `controlnet-union-sdxl-1.0`)
   - holes/keep-clear masked out → region-IoU ~1.0 by construction
   - canny on the exact contour → outer silhouette locked; top-contour adapts
     because the line IS the top contour
   - apache/openrail++ weights = commercial-safe, runs on this MPS host.

2. **[BEST style, free/local] SDXL + xinsir Canny/Union CN with
   `control_guidance_end≈0.6` + a Differential-Diffusion graded change-map.**
   Softer than a binary mask: body painted freely, contour edge + hole rims
   frozen, no seam. More work to build the change-map; best look.

3. **[BEST exactness if budget OK, paid] fal `fal-ai/flux-general/inpainting`
   (FLUX.1 Fill) with `image_url`=grey guide, `mask_url`=opening mask**, then
   **re-paste the original outside the mask** (Fill color-shifts unmasked
   pixels). FLUX style >> SDXL; geometry guaranteed by the mask. Weights are
   non-commercial but outputs are usable; it's an API so no weight hosting.

4. **[paid, best graded control] fal
   `fal-ai/flux-general/differential-diffusion`** with `change_map_image_url`
   from the SVG (body=255, holes/edges=0, blurred) + a canny `controlnet_unions`
   entry. One call does structure + soft-confine. `strength≈0.8`.

5. **[supporting] Attention Couple / IP-Adapter (ComfyUI, installed)** — only to
   place style/content per region or inject reference style; pair with #1–#4,
   not a substitute for the hole-emptiness guarantee.

### Single best pick

**Upgrade the existing `controlnet_inpaint_gen.py` to SDXL** (option 1). It
reuses the repo's proven SVG→control + opening-mask machinery, runs free on the
current MPS host, is commercial-safe, and makes the holes/keep-clear exact *by
construction* (not by hoping a prompt works). If style still lags SDXL's
ceiling, escalate to option 3/4 on fal for the hero renders.

### Minimal adoption plan (option 1)

- **Conditioning images** (one SVG → three, all viewBox-mapped to panel px):
  1. canny map: `svg_to_controlmap.py SVG --style canny --width W` (white-on-black)
  2. binary opening mask: white body / black holes+keep-clear (reuse
     `controlnet_inpaint_gen.py`'s mask builder / `svg_classify`)
  3. (init) grey geometry guide for the inpaint init image
- **Call shape** (diffusers, MPS):
  - `StableDiffusionXLControlNetInpaintPipeline.from_pretrained(`
    `"diffusers/stable-diffusion-xl-1.0-inpainting-0.1",`
    `controlnet=ControlNetModel.from_pretrained("xinsir/controlnet-canny-sdxl-1.0"))`
  - `pipe(prompt, image=guide, mask_image=opening_mask,`
    `control_image=canny_map, controlnet_conditioning_scale=0.9,`
    `control_guidance_end=0.7, strength=0.85, num_inference_steps=18)`
  - device `mps`; if OOM/fp16 issues: drop `torch.float16` or upcast layernorm,
    `PYTORCH_ENABLE_MPS_FALLBACK=1`.
- **After**: hard-clear the holes from the SVG mask (don't trust the model),
  then **measure** region-IoU + silhouette-IoU vs the spec and run the
  multi-judge gate (per `geometry-must-be-measured-gate`,
  `code-gates-need-calibration`). Never claim fit from a number alone.

### Free-local vs paid summary

- **Free / local (MPS), commercial-safe weights:** SDXL inpaint + xinsir/diffusers
  CN (apache/openrail++); Differential Diffusion via diffusers; Attention Couple
  + IP-Adapter in the installed ComfyUI. → options 1, 2, 5.
- **Paid (fal API), best style, non-commercial *weights* but usable outputs:**
  FLUX Fill / flux-general CN / differential-diffusion. → options 3, 4.

---

## Unverified / to confirm before relying on it
- XLabs `flux-controlnet-canny-v3` license [UNVERIFIED] — confirm on its repo.
- fal pricing for flux-general / Fill not shown on the API pages fetched
  [UNVERIFIED $].
- fal differential-diffusion change-map polarity (which gray value = "change")
  not documented in fetched page — confirm with a 1-tile test before batch.
- Whether SDXL **ControlNet-inpaint** pipeline specifically (vs plain SDXL CN or
  plain SDXL inpaint) is memory-feasible on *this* exact host — proven for SDXL
  and SDXL+CN on M1 Max/64 GB [verified]; do a single-image smoke test before a
  batch.

## Sources (verified)
- https://huggingface.co/black-forest-labs/FLUX.1-Canny-dev
- https://huggingface.co/black-forest-labs/FLUX.1-Fill-dev
- https://huggingface.co/black-forest-labs/FLUX.1-Redux-dev
- https://huggingface.co/InstantX/FLUX.1-dev-Controlnet-Canny
- https://huggingface.co/Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro-2.0
- https://huggingface.co/xinsir/controlnet-canny-sdxl-1.0
- https://huggingface.co/xinsir/controlnet-union-sdxl-1.0  (apache-2.0)
- https://huggingface.co/xinsir/controlnet-scribble-sdxl-1.0
- https://huggingface.co/xinsir/controlnet-depth-sdxl-1.0
- https://huggingface.co/diffusers/stable-diffusion-xl-1.0-inpainting-0.1
- https://huggingface.co/diffusers/controlnet-canny-sdxl-1.0 (discussion #17 — Apple Silicon code)
- https://fal.ai/models/fal-ai/flux-general/image-to-image/api
- https://fal.ai/models/fal-ai/flux-general/inpainting/api
- https://fal.ai/models/fal-ai/flux-general/differential-diffusion/api
- https://fal.ai/models/fal-ai/flux-1/dev/redux/api
- https://huggingface.co/blog/OzzyGT/outpainting-differential-diffusion
- https://mybyways.com/blog/differential-diffusion-for-in-painting
- https://github.com/zacheryvaughn/softfill-pipelines
- https://github.com/mofos/Flux_Differential-diffusion_Inpainting_Diffusers
- https://github.com/pamparamm/ComfyUI-ppm  (Attention Couple SDXL)
- https://stable-diffusion-art.com/regional-prompter/
