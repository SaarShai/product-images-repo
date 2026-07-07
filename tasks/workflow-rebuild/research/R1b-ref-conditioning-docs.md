# R1b — Official Documentation Sweep: Reference-Image Handling

Lane R1b: first-party/official documentation only, covering multi-image reference
conditioning across OpenAI (gpt-image family), Google Gemini (Nano Banana),
Black Forest Labs (Flux Kontext / Flux.2), and fal.ai model pages for the specific
adapters used in this repo's pipeline. Deliberately overlaps lane R1 (different vendor)
for cross-check.

Date pulled: 2026-07-05/06. All quotes verbatim from the fetched pages unless marked
"(search-result summary, not page-verbatim)" where a direct fetch 404'd and a WebSearch
synthesis was used instead — flagged per-section.

---

## 1. OpenAI — `gpt-image` family (`/v1/images/edits`)

Sources:
- https://developers.openai.com/api/docs/guides/image-generation (redirected from platform.openai.com/docs/guides/image-generation, 301)
- https://developers.openai.com/api/reference/resources/images/methods/edit
- https://developers.openai.com/cookbook/examples/generate_images_with_high_input_fidelity
- https://developers.openai.com/cookbook/examples/multimodal/image-gen-1.5-prompting_guide

### Multiple input images

> "You can use one or more images as a reference to generate a new image."

The edits endpoint's `image` field is an array of objects, each `{file_id}` or
`{image_url}` (image_url max 20,971,520 chars, i.e. a data-URL size ceiling). Docs state
support for **up to 16 images** in a single edit call. Images may be supplied as:
- fully qualified URLs
- base64-encoded data URLs
- File IDs (via the Files API)

### Ordering semantics — mask and fidelity both key off position

Two independent "first image is special" rules, confirmed from two different pages:

1. **Mask targeting**: "the mask will be applied to the first image" — when a `mask` is
   passed alongside multiple `image` entries, it always applies to `image[0]`, not to
   whichever image is thematically the "base."
2. **Fidelity/texture preservation**: from the high-input-fidelity cookbook — "Currently,
   while all input images are preserved with high fidelity, only the first one you
   provide is preserved with extra richness in texture." The cookbook's explicit
   recommendation for multi-face composites: **pre-merge into a single composite image
   before sending**, rather than relying on the 2nd+ image slots to carry equal detail.

Practical implication for our pipeline: when we send [subject-geometry, style-ref,
palette-ref], the **subject/geometry image should be image[0]** if texture fidelity on
geometry matters more than on style/palette — or the reverse if faithful color/brush
texture matters most. This is a real trade-off, not a wash.

### `input_fidelity`

> "controls how strongly a model preserves details from input images during edits and
> reference-image workflows."

Model-gated, not universal:
- `gpt-image-1`: supported. Values `high` / `low`. Controls "how much effort the model
  will exert to match the style and features, especially facial features, of input
  images."
- `gpt-image-1-mini`: **not supported.**
- `gpt-image-2`: **must be omitted** — "the API doesn't allow changing it because the
  model processes every image input at high fidelity automatically." (i.e. gpt-image-2
  is always high-fidelity; passing the param is invalid, not merely ignored.)

### `quality`

Enum: `low | medium | high | auto` (default `auto`). Guidance: "Use `quality: "low"` for
fast drafts, thumbnails, and quick iterations."

### `size`

Per the image-generation guide (gpt-image-2-oriented framing): "any resolution" subject
to constraints — max edge ≤ 3840px, both edges multiples of 16px, long:short ratio ≤ 3:1,
total pixels 655,360–8,294,400. Default `auto`.

Per the API reference (edits endpoint, older gpt-image-1 family enum surface): `size`
enum is `auto | 1024x1024 | 1536x1024 | 1024x1536`. **These two pages describe different
generations of the size contract** — the free-form pixel-budget rule is the newer
gpt-image-2-era behavior; the fixed-enum list is what the base `/edits` reference
documents. Treat the enum list as the floor/legacy contract and the pixel-budget rule as
what applies when targeting gpt-image-2 specifically. This discrepancy is worth a follow-up
confirmation against the live API (not resolved by documentation alone) — flagged in gaps.

### Full `/v1/images/edits` parameter table (from API reference page)

| Param | Type | Values / Notes |
|---|---|---|
| `image` (`images` in newer schema) | array of `{file_id}` \| `{image_url}` | up to 16 images |
| `mask` | `{file_id}` \| `{image_url}` | applies to first image only when multiple images passed |
| `model` | enum | `gpt-image-1.5`, `gpt-image-1`, `gpt-image-1-mini`, `chatgpt-image-latest` |
| `n` | integer | 1–10 |
| `quality` | enum | `low, medium, high, auto` |
| `size` | enum (this page's version) | `auto, 1024x1024, 1536x1024, 1024x1536` |
| `input_fidelity` | enum | `high, low` — model-gated, see above |
| `background` | enum | `transparent, opaque, auto` |
| `output_format` | enum | `png, jpeg, webp` |
| `output_compression` | integer | 0–100 |
| `partial_images` | integer | 0–3 (streaming partial renders) |
| `stream` | boolean | — |
| `user` | string | end-user identifier |

### Reference-image prompting guidance (gpt-image-1.5 cookbook)

Directly applicable to our style/geometry-separation design:

> "Reference each input by index and description ('Image 1: product photo… Image 2:
> style reference…')"

> "describe how they interact ('apply Image 2's style to Image 1'). When compositing, be
> explicit about which elements move where."

> "use 'change only X' + 'keep everything else the same,' and repeat the preserve list on
> each iteration to reduce drift."

Demonstrated multi-image patterns: style transfer (1 source + 1 style ref), virtual
try-on (1 person + 4–5 clothing refs), compositing (2 scene/subject refs). This confirms
first-party support for the exact "indexed-role" prompting pattern (Image 1 = X, Image 2
= Y) that lane R1b was checking — not just a community convention.

---

## 2. Google Gemini (Nano Banana / Gemini 3 image models)

Source: https://ai.google.dev/gemini-api/docs/image-generation (primary);
https://ai.google.dev/gemini-api/docs/image-understanding (annotated-input check)

### Max input images — model-gated, NOT a single flat number

This is the most important correction vs. a naive "N images" assumption: the cap is
split by **image role** (object / character / style) and differs per model:

| Model | Objects | Characters | Style refs | Total |
|---|---|---|---|---|
| Gemini 3.1 Flash Lite (Nano Banana 2 Lite) | up to 10 | — | — | up to 14 total; "not optimized for multiple reference inputs or multi-turn sequential editing" |
| Gemini 3.1 Flash (Nano Banana 2) | up to 10 | up to 4 | up to 3 | up to 14 (documented as excelling at "multiple reference image processing and consistency") |
| Gemini 3 Pro (Nano Banana Pro) | up to 6 | up to 5 | up to 3 | fewer total than Flash tier |

(Numbers reconstructed from the fetched image-generation guide's role-segmented limits;
the guide does not give one flat "max images" figure — it partitions by role, which is
itself a design signal: Google's own docs model references as typed slots, not a
homogeneous list.)

### Multi-image composition prompt template (official)

> "Create a new image by combining the elements from the provided images. Take the
> [element from image 1] and place it with/on the [element from image 2]."

Worked example (e-commerce): "Create a professional e-commerce fashion photo. Take the
blue floral dress from the first image and let the woman from the second image wear it."

### Style transfer guidance (official)

> "Provide an image and ask the model to recreate its content in a different artistic
> style."

### Detail-preservation guidance (official — directly relevant to our geometry-fidelity concern)

> "To ensure critical details (like a face or logo) are preserved during an edit,
> describe them in great detail along with your edit request."

Note the contrast with OpenAI: OpenAI's `input_fidelity` is a **parameter** that
mechanically raises preservation; Google's official guidance for the same problem is
**textual re-description**, not a knob. If true (docs give no counter-evidence), Gemini
has no first-party fidelity-strength parameter equivalent to `input_fidelity` — detail
preservation is prompt-engineered, not parameterized. Flag this as a real asymmetry
between the two platforms, not an omission in our research.

### Prompt templates by use case (official, verbatim structure)

- Photorealistic: "A photorealistic [type of shot] of a [subject description] in a
  [setting description]. [Description of the light]. Shot from a [camera angle] with a
  [lens type]."
- Stylized illustration: "A [style] of a [subject, with details about accessories or
  actions] doing [activity]. The design features [visual qualities, e.g., bold outlines,
  cel-shading, etc.] and [color/background preference]."
- Product mockup: "A high-resolution, studio-lit product photograph of a [product
  description] on a [background surface/description]. The lighting is a [lighting
  setup]..."
- Image editing: "Using the provided image of [subject], please [add/remove/modify]
  [element] to/from the scene..."
- Style transfer: "Transform the provided photograph of [subject] into the artistic
  style of [artist/art style]..."

### Annotated inputs (bounding boxes / markup) — IMPORTANT DISTINCTION

The **API docs** (ai.google.dev/gemini-api/docs/image-understanding) describe bounding
boxes and segmentation masks only as **model OUTPUT** (detection/segmentation results,
coordinates normalized 0–1000), not as a supported **input** annotation format for
steering generation.

The "draw-to-edit" doodle/markup feature (circle, arrow, scribble, text annotation to
guide an edit) is a **consumer Gemini app feature** (web/Android/iOS, rolled out ~Dec 18,
2025), not a documented `ai.google.dev` API parameter. Do not assume this is
API-accessible — it wasn't found in the developer docs; treat as a product-UI-only
feature until/unless an API doc surfaces it (see gaps).

### Image-count hard limit (unrelated to reference-role caps above)

> "Gemini models support a maximum of 3,600 image files per request." — this is a
> platform-wide ceiling (e.g., video-frame-as-images use cases), not the practical
  reference-image guidance number; the role-segmented table above is what actually
  governs style/character/object reference workflows.

---

## 3. Black Forest Labs — Flux Kontext, Flux.2, Redux

Sources:
- https://docs.bfl.ai/kontext/kontext_overview
- https://docs.bfl.ai/flux_2/flux2_overview
- https://docs.bfl.ai/flux_2/flux2_image_editing
- https://docs.bfl.ai/api-reference/models/generate-or-edit-an-image-with-flux2-%5Bpro%5D
- (docs.bfl.ml is the legacy/redirect domain for the same content; docs.bfl.ai is
  current — several old deep links, e.g. `guides/prompting_guide_kontext_i2i`, now 404
  on docs.bfl.ai and must be reached via search/redirect)

### Kontext: single-reference edit model, now legacy

Kontext's overview page **contains no multi-reference documentation** — Kontext is a
single `input_image` + text-instruction edit model. The docs are explicit that Kontext is
superseded:

> "FLUX.2 is now our recommended model" ... FLUX.1 Kontext explicitly positioned as a
> "previous-generation model," with FLUX.2 offering "multi-reference support (up to 10
> images)" as a named advantage Kontext lacks.

Kontext editing semantics (from prior fetch before 404, cross-checked via search):
quoted-text replacement syntax `Replace 'old text' with 'new text'`, strong at
straightforward object/color edits and multi-turn character consistency, max prompt
length 512 tokens. Three tiers: `[max]` ($0.08/img), `[pro]` ($0.04/img, 5–6s), `[dev]`
(open-weight, non-commercial).

### Flux.2: multi-reference is the headline feature, limits vary by variant

From `flux2_overview`:

| Variant | Max references |
|---|---|
| `[klein]` | up to 4 |
| `[max]` | up to 8 (API), 10 (playground) |
| `[pro]` | up to 8 (API), 10 (playground) |
| `[flex]` | up to 8 (API), 10 (playground) |
| `[dev]` | recommended max 6 |

Note the **API vs playground gap** (8 vs 10) for the hosted-tier variants — the
playground UI permits 2 more references than the programmatic API allows for the same
model. This is a real, documented asymmetry (not a typo) worth remembering when a
prototype "looks fine in playground" but the same reference count fails via API.

Framing: multi-reference lets you "combine elements from multiple images while
maintaining identity across complex scenes." Use cases named: ad variants with
consistent faces, product mockups in any context, fashion editorials with consistent
models.

### Flux.2 API — exact parameter names (from `generate-or-edit-an-image-with-flux2-[pro]`)

| Param | Required | Type | Notes |
|---|---|---|---|
| `prompt` | yes | string | — |
| `input_image` … `input_image_8` | no | string \| null | up to 8 slots, each "Path to the input image" — numeric-suffix params, NOT an array |
| `seed` | no | integer \| null | reproducibility |
| `width` / `height` | no | integer ≥64 \| null | default 0 (auto) |
| `safety_tolerance` | no | integer 0–5 | default 2 |
| `output_format` | no | `jpeg\|png\|webp` \| null | default jpeg |
| `webhook_url` / `webhook_secret` | no | string | async callback |

Confirmed: **no `aspect_ratio` and no `prompt_upsampling` parameter** on this endpoint
(these exist on other BFL endpoints/generations but are absent from the current
Flux.2 [pro] edit/generate schema per the fetched reference).

Prompting for multi-reference (from `flux2_image_editing`): reference images by ordinal
number in the prompt text itself — "Create a house for the chickens from image 1 using
materials from images 2, 3, 4, and 5." This is a **numeric-parameter-slot + numeric-prompt-reference**
double convention: `input_image_2` is genuinely image #2 both in the request shape and in
how the prompt should refer to it — unlike OpenAI (single array, referred to as "Image 1/2"
in prose by convention only) or Gemini (role-typed slots, referred to by role not number).

Signed URLs for input images are time-limited: "only valid for 10 minutes" — an
operational constraint for any pipeline that pre-signs URLs and queues requests.

### Redux — not present in current docs.bfl.ai IA

No `docs.bfl.ai` page for Redux was found; it surfaces only in older
Hugging Face/GitHub/community material as a FLUX.1-era "image variation" adapter
(reproduce input with slight variation). It appears to have been folded into/superseded
by Flux.2's native multi-reference editing and no longer has independent first-party
documentation. Flag as unresolved — see gaps (could not confirm a current, dedicated BFL
doc page; only third-party/legacy mentions found).

---

## 4. fal.ai model pages — exact param schemas

### `openai/gpt-image-2/edit` (fal-hosted GPT Image 2 edit)

Source: https://fal.ai/models/openai/gpt-image-2/edit/api (+ corroborating search of fal's own prompting-guide copy)

| Param | Type | Notes |
|---|---|---|
| `image_urls` | list<string>, required | "The URLs of the images to use as a reference for the generation." fal's own guide states the GPT Image family "accepts up to 16 reference images for edits" — consistent with the first-party OpenAI 16-image cap above |
| `mask_url` | string | region to edit |
| `prompt` | string, required | — |
| `image_size` | enum or `{width,height}` | default `auto`; presets `square_hd, square, portrait_4_3, portrait_16_9, landscape_4_3, landscape_16_9, auto` |
| `quality` | enum | default `high` (note: **differs from OpenAI-first-party default of `auto`** — fal has set its own default) |
| `num_images` | integer | default 1 |
| `output_format` | enum | default `png` |

No dedicated `input_fidelity`-equivalent field surfaced on this fal wrapper page.

### `fal-ai/nano-banana-pro/edit`

| Param | Notes |
|---|---|
| `image_urls` | list<string>, required — no explicit max stated on this page (contrast: first-party ai.google.dev gives the role-typed 14-image structure above; fal's wrapper does not surface that role split) |
| `aspect_ratio` | default `auto`; `21:9,16:9,3:2,4:3,5:4,1:1,4:5,3:4,2:3,9:16` |
| `resolution` | default `1K`; `1K, 2K, 4K` |
| `safety_tolerance` | default `4` (API only); `1–6` |
| `num_images`, `seed`, `output_format`, `sync_mode`, `system_prompt`, `enable_web_search`, `limit_generations` | secondary controls |

### `fal-ai/flux-general` — ip_adapter / reference_image_url / control_loras

This is the closest fal-side equivalent to a fine-grained "separable style/geometry
conditioning" mechanism referenced in our workflow design goal:

**`ip_adapter`** (list of IPAdapter objects) — "IP-Adapter to use for image generation."
Each object:
- `path` (required) — HF path to the IP-Adapter weights
- `image_encoder_path` (required) — e.g. `"openai/clip-vit-large-patch14"`
- `image_url` (required) — "URL of Image for IP-Adapter conditioning"
- `scale` (required, float) — adapter strength
- optional: `subfolder`, `weight_name`, `image_encoder_subfolder`,
  `image_encoder_weight_name`, `mask_image_url`, `mask_threshold` (default 0.5)

**`reference_image_url` / `reference_strength`** — a separate, simpler "reference-only"
mechanism (not IP-Adapter): `reference_strength` default **0.65**; also
`reference_start` / `reference_end` (default `reference_end` = 1) control what fraction
of the diffusion timeline the reference guidance is active over — i.e. reference
conditioning can be scheduled to fade out before the final denoising steps.

**`control_loras`** (list of ControlLoraWeight) — geometry/structure conditioning via
LoRA rather than ControlNet proper:
- `path` (required) — LoRA weights URL
- `control_image_url` (required)
- `scale` (float or per-layer dict, default 1) — supports `{"layer_name": layer_scale}`
  for per-layer control strength
- `preprocess` (default `"None"`) — `canny | depth | None`

This confirms fal's `flux-general` wrapper genuinely exposes THREE separable
conditioning channels (IP-Adapter for subject/style image conditioning,
reference_image_url for a lighter-weight "reference-only" pass with a fade-out schedule,
control_loras for geometry/structure via canny/depth preprocessing) — which maps cleanly
onto this project's stated goal of decomposing style into separable reference-image
channels (art medium / palette / illustration style vs. geometry).

### `fal-ai/flux-kontext-lora`

Single-image edit model (`image_url`, required, max 14142×14142px) + text prompt — no
multi-reference support at this endpoint. `loras` param (list of `{path, scale}`) adds
style/subject LoRAs on top, separate from the image-conditioning path.
`resolution_mode` default `"match_input"` (also accepts fixed aspect-ratio enums or
`auto`). `guidance_scale` default 2.5, `num_inference_steps` default 30.

---

## 5. Cross-platform cheat-sheet

| Platform / endpoint | Multi-ref? | Max images | Ordering semantics | Fidelity/strength knob | Prompt convention |
|---|---|---|---|---|---|
| OpenAI `/images/edits` (gpt-image-1/1.5/2) | yes | 16 | **image[0]** gets mask target AND extra texture fidelity; rest still "high fidelity" but less rich | `input_fidelity` (`high`/`low`) — gpt-image-1 only; **forbidden param** on gpt-image-2 (always high, auto) | "Image 1: X… Image 2: Y…" + "apply Image 2's style to Image 1" + repeat preserve-list each turn |
| fal `openai/gpt-image-2/edit` | yes | 16 (per fal's own guide) | same as above (pass-through) | none exposed on wrapper | same |
| Google Gemini (Nano Banana 2 / Pro) | yes | role-typed: up to 10 objects + 4 characters + 3 style (Flash); 6 objects + 5 characters + 3 style (Pro) — NOT one flat number | role, not position, is the organizing axis | **none documented** — preservation is achieved by re-describing the detail in the prompt, not a parameter | "Take [element from image 1] and place it with/on [element from image 2]" |
| fal `nano-banana-pro/edit` | yes | unstated on wrapper page | unstated | none | — |
| BFL Flux Kontext (`[pro]/[max]/[dev]`) | **no** (single `input_image`) | 1 | n/a | n/a | quoted-text edits: `Replace 'X' with 'Y'`; legacy, BFL recommends Flux.2 instead |
| BFL Flux.2 (`[pro]/[max]/[flex]`) | yes | 8 via API / 10 in playground (klein: 4; dev: ~6 recommended) | numeric parameter slots `input_image`..`input_image_8`; prompt should reference by the SAME ordinal ("image 1", "image 2"…) | none exposed (no input_fidelity equivalent found) | "materials from images 2, 3, 4, and 5" |
| BFL Redux | unclear — no current first-party doc page found | — | — | — | legacy FLUX.1-era variation adapter; likely superseded by Flux.2 multi-ref |
| fal `flux-general` (ip_adapter) | yes, list | unbounded (list) | independent per-adapter `scale`; can combine multiple IP-Adapters | `scale` per adapter (required float) | separate from `reference_image_url` |
| fal `flux-general` (reference_image_url) | single slot | 1 | — | `reference_strength` (default 0.65), schedulable via `reference_start`/`reference_end` (default end=1) | lighter-weight than IP-Adapter |
| fal `flux-general` (control_loras) | yes, list | unbounded (list) | per-LoRA `scale` (float or per-layer dict) + `preprocess` (`canny`/`depth`/`None`) | scale | geometry/structure channel, separate from style/subject channels |
| fal `flux-kontext-lora` | no | 1 (`image_url`) | n/a | n/a | + separate `loras` list for style |

### Key cross-cutting findings for the workflow-rebuild design

1. **"First image is special" is real but means different things per platform.**
   OpenAI: image[0] = mask target + max texture fidelity. Flux.2: images are referenced
   by explicit ordinal in the prompt text (not implicitly privileged) — position still
   matters but for prompt-legibility, not a hidden preservation bonus. Gemini: no
   position privilege found; role (object/character/style) is the organizing axis
   instead of array position.

2. **Only OpenAI (gpt-image-1, not -2) exposes a literal fidelity-strength parameter.**
   Gemini and Flux.2 both rely on **prompt text** to request detail preservation; this
   is a documented capability gap, not a research gap — worth encoding directly into our
   prompt templates for those two backends rather than expecting a param.

3. **fal's `flux-general` wrapper is the only surface here with 3 independently-scaled
   conditioning channels** (IP-Adapter / reference_image_url+strength / control_loras),
   directly matching this project's decomposition goal (style medium vs. palette vs.
   geometry as separate reference images with separate strengths). None of the
   first-party hosted APIs (OpenAI, Gemini, BFL-hosted Flux.2) expose a per-image
   strength/weight parameter — they treat all reference images as equally-weighted
   inputs modulated only by prompt text and (OpenAI only) a single global fidelity flag.

4. **API vs. playground limits can silently differ** (Flux.2: 8 API / 10 playground).
   Any prototyping done in a playground UI needs re-validation against the actual API
   cap before being assumed production-ready.

5. **Annotated/markup input-side guidance is NOT in first-party API docs for either
   OpenAI or Gemini.** Gemini's doodle/markup editing is a consumer-app feature (Gemini
   app, Dec 2025), not a documented `ai.google.dev` API parameter. OpenAI's docs show no
   bounding-box/markup input mechanism at all. If the workflow design assumed
   annotation-driven geometry control was API-available on either platform, that
   assumption is not supported by current official docs — geometry control on these two
   platforms is image-based (a geometry reference image) or prompt-based only.

---

## Gaps / unresolved (what was tried)

- **OpenAI `size` param contract conflict**: the image-generation guide (pixel-budget
  rule, ≤3840px edge / 16px multiples / 655K–8.3M px total) vs. the `/images/edits` API
  reference (fixed enum `auto|1024x1024|1536x1024|1024x1536`) describe different-looking
  contracts. Tried: fetched both pages directly; both returned confidently but
  inconsistent framings. Likely explained by gpt-image-2-specific vs. legacy gpt-image-1
  enum surfaces, but not explicitly reconciled in the docs I could reach. Would need a
  live API call or a changelog page to confirm which is current for gpt-image-2 --
  out of scope for spend-free research.
- **BFL Redux current status**: no live docs.bfl.ai page found (only overview/blog/HF/GitHub
  mentions, several dead/legacy links off docs.bfl.ml). Tried two targeted searches
  ("docs.bfl.ai Redux", plus checking flux2_overview for a Redux mention — it wasn't
  named there). Could not confirm whether Redux is still a supported, separately-documented
  product or fully folded into Flux.2 multi-reference.
- **Exact `image_urls` max count on `fal-ai/nano-banana-pro/edit`**: the fal wrapper
  page itself states no explicit ceiling; only the first-party ai.google.dev role-typed
  table (10 objects/4 characters/3 style for Flash; 6/5/3 for Pro) gives real numbers,
  and it's unclear whether fal's wrapper enforces/exposes that same role split or just
  passes through a flat list. Not resolved by documentation alone.
- **Kontext single-page re-fetch 404**: `docs.bfl.ai/guides/prompting_guide_kontext_i2i`
  returned 404 on direct fetch (legacy path); content was reconstructed via WebSearch
  synthesis + the still-live `kontext_overview` page rather than a full page fetch. Flagged
  inline above wherever this applies.
- **Whether Gemini's per-role caps (objects/characters/style) are hard API-enforced
  limits or soft prompting recommendations** — the docs present them as capability
  numbers ("up to N") without stating what happens if exceeded (truncation? error?
  degraded quality?). Not addressed in the fetched pages.
