# R2 Platform Patterns: Multi-Step Reference Pipelines

Date: 2026-07-06

Scope: workflow shape for reference-driven generative-image systems, not single-model parameter tuning.

Project-local stack assumption from the task brief: our production lane is fal.ai API plus codex-driven gpt-image plus Python glue; we generate watercolor toy-building illustrations that must fit die-cut SVG panel templates; reference images are treated as stronger control signals than text descriptions.

Evidence rule used in this report: each factual platform claim is tied to a source URL in the same pattern entry, or is explicitly marked `Unverified`.

## Pattern Catalog

### 1. ComfyUI Node Graph as a Reusable Reference Pipeline

- How it works: ComfyUI exposes image generation as a node/graph interface, can load and save workflows as JSON, and supports complex workflows through connected nodes. Evidence: https://github.com/Comfy-Org/ComfyUI
- What it buys: the workflow artifact itself becomes a reusable recipe, which is useful when style, geometry, masks, and final export checks need to be kept as separate stages. Evidence: https://github.com/Comfy-Org/ComfyUI
- Portability: Portable. Reason: Python glue can represent the same graph as an explicit DAG of file transforms, codex gpt-image calls, fal endpoint calls, and local geometry checks.

### 2. IP-Adapter Image-Prompt Conditioning

- How it works: IP-Adapter adds image-prompt capability to a pretrained text-to-image diffusion model with a lightweight adapter and separates text and image cross-attention paths. Evidence: https://arxiv.org/abs/2308.06721
- How it works in ComfyUI: `ComfyUI_IPAdapter_plus` is a ComfyUI implementation for IP-Adapter models, and its README describes IP-Adapter as image-to-image conditioning where a reference image can transfer subject or style. Evidence: https://github.com/cubiq/ComfyUI_IPAdapter_plus
- What it buys: it turns a reference image into an active conditioning input rather than a prose description, which matches our adopted "reference images beat text" law. Evidence: https://arxiv.org/abs/2308.06721
- Portability: Partially portable. Reason: gpt-image does not expose IP-Adapter weights or attention layers in the brief, but the workflow shape is portable as "attach a style/reference image, preserve a separate geometry guide, and evaluate output against the guide."

### 3. IP-Adapter Style-vs-Composition Split

- How it works: `ComfyUI_IPAdapter_plus` includes an `ipadapter_style_composition.json` example and an `IPAdapterStyleComposition` node with separate `image_style` and `image_composition` inputs. Evidence: https://raw.githubusercontent.com/cubiq/ComfyUI_IPAdapter_plus/main/examples/ipadapter_style_composition.json
- What it buys: it separates "look" from "layout," letting one image steer medium/palette/texture while a second image steers object placement. Evidence: https://raw.githubusercontent.com/cubiq/ComfyUI_IPAdapter_plus/main/examples/ipadapter_style_composition.json
- Portability: Portable. Reason: our Python glue can build two distinct reference files, one style packet and one SVG-derived composition guide, and pass both into codex gpt-image or fal gpt-image finals as separate image references.

### 4. IP-Adapter Composition-Only / Precise Composition

- How it works: `ComfyUI_IPAdapter_plus` lists `ipadapter_precise_composition.json` and community composition models such as `ip_plus_composition_sd15.safetensors`, described as composition-focused and ignoring style/content. Evidence: https://github.com/cubiq/ComfyUI_IPAdapter_plus and https://github.com/cubiq/ComfyUI_IPAdapter_plus/tree/main/examples
- What it buys: it treats composition as a reference channel that can be tested independently from art style. Evidence: https://github.com/cubiq/ComfyUI_IPAdapter_plus/tree/main/examples
- Portability: Portable. Reason: we can generate a black/white or color-coded composition map from SVG pockets and use it as a reference image while keeping watercolor references separate.

### 5. Regional IP-Adapter / Attention-Masked Reference Routing

- How it works: `ComfyUI_IPAdapter_plus` lists `ipadapter_regional_conditioning.json`, and the style-composition example exposes an `attn_mask` input on `IPAdapterStyleComposition`. Evidence: https://github.com/cubiq/ComfyUI_IPAdapter_plus/tree/main/examples and https://raw.githubusercontent.com/cubiq/ComfyUI_IPAdapter_plus/main/examples/ipadapter_style_composition.json
- What it buys: different references can be aimed at different parts of an image instead of forcing one global style/reference to explain every region. Evidence: https://github.com/cubiq/ComfyUI_IPAdapter_plus/tree/main/examples
- Portability: Partially portable. Reason: gpt-image does not expose attention masks in the brief, but we can make region maps, crop-specific references, and pass-specific prompts; local SVG masks can then verify whether region intent survived.

### 6. ControlNet Stack Plus Style Reference

- How it works: ControlNet adds spatial conditions to diffusion models; the original repo lists Canny, HED, scribble, pose, segmentation, depth, and normal-map apps, and says multiple ControlNets are composable for multi-condition control. Evidence: https://github.com/lllyasviel/ControlNet
- How it works in ComfyUI: `comfyui_controlnet_aux` provides ComfyUI preprocessors that make ControlNet hint images such as Canny, scribble, depth, pose, and segmentation. Evidence: https://github.com/Fannovel16/comfyui_controlnet_aux
- What it buys: structural guides can be stacked with style references, so geometry and style do not compete in a single prompt. Evidence: https://github.com/lllyasviel/ControlNet and https://github.com/tencent-ailab/IP-Adapter
- Portability: Partially portable. Reason: we cannot assume native ControlNet in gpt-image, but we can port the pipeline shape by generating edge/depth/silhouette/control-map images in Python and attaching them as geometry references.

### 7. GLIGEN / Text-Box Regional Layout

- How it works: GLIGEN conditions image generation on grounding inputs, including caption and bounding boxes; the ComfyUI GLIGEN example says the Textbox Apply nodes specify where objects or concepts should appear. Evidence: https://github.com/gligen/GLIGEN and https://comfyanonymous.github.io/ComfyUI_examples/gligen/
- What it buys: layout can be specified as named boxes before style rendering, which is useful for windows, doors, signs, awnings, and feature placement inside die-cut panel pockets. Evidence: https://comfyanonymous.github.io/ComfyUI_examples/gligen/
- Portability: Portable. Reason: Python can derive bounding boxes from SVG safe pockets, emit a labeled layout guide, and send that guide as a composition reference to gpt-image/fal.

### 8. Area Composition / Regional Prompting

- How it works: ComfyUI's Area Composition examples demonstrate `ConditioningSetArea` and show different prompts assigned to different image areas, including a two-pass workflow for larger output. Evidence: https://comfyanonymous.github.io/ComfyUI_examples/area_composition/
- What it buys: it lets the user decide region-level semantics before rendering, rather than asking the model to infer all regions from one global prompt. Evidence: https://comfyanonymous.github.io/ComfyUI_examples/area_composition/
- Portability: Portable. Reason: our SVG pocket detector can output region labels and a visual region map, then each gpt-image pass can be prompted with those labels and checked against the same map.

### 9. Flux Redux Style/Image-Variation Chain

- How it works: Black Forest Labs describes FLUX.1 Redux as an adapter for FLUX.1 base models that can reproduce an input image with slight variation and can be combined with a prompt for restyling through the API. Evidence: https://bfl.ai/blog/24-11-21-tools
- What it buys: it supports the "use the last good image as evidence, then restyle/redraw" workflow instead of treating each attempt as text-only. Evidence: https://bfl.ai/blog/24-11-21-tools
- Portability: Partially portable. Reason: the exact Redux adapter is model-specific, but the shape maps directly to our approved-geometry-as-composition-map plus whole-panel redraw/restyle method.

### 10. Flux Fill / Local Inpaint and Outpaint Repair

- How it works: Black Forest Labs describes FLUX.1 Fill as inpainting and outpainting given a text description and binary mask. Evidence: https://bfl.ai/blog/24-11-21-tools
- What it buys: it isolates a defect or missing feature without forcing a full-panel reroll. Evidence: https://bfl.ai/blog/24-11-21-tools
- Portability: Portable. Reason: our stack can make binary masks from SVG holes or feature regions in Python and route only those areas into an image-edit pass where the model supports masks.

### 11. Rough Layout Pass -> Style Pass -> Detail/Inpaint Pass

- How it works: ComfyUI Area Composition documents a two-pass layout/upscale example, ControlNet documents structural controls such as scribble/edge/depth, and Flux Fill documents mask-based inpainting/outpainting. Evidence: https://comfyanonymous.github.io/ComfyUI_examples/area_composition/ and https://github.com/lllyasviel/ControlNet and https://bfl.ai/blog/24-11-21-tools
- What it buys: the pipeline separates low-cost spatial exploration from style commitment and from final defect repair. Evidence: https://comfyanonymous.github.io/ComfyUI_examples/area_composition/ and https://bfl.ai/blog/24-11-21-tools
- Portability: Portable. Reason: codex gpt-image can do the rough/style iterations, fal gpt-image can be reserved for exact-frame finals, and Python can enforce geometry gates between passes.

### 12. fal.ai Workflow Endpoint

- How it works: fal workflow endpoints chain multiple models into a single endpoint, pass outputs from one model into the next, and run as one API call. Evidence: https://fal.ai/docs/documentation/model-apis/workflows
- What it buys: users do not need to manually orchestrate every endpoint call when a pipeline is stable enough to be productized. Evidence: https://fal.ai/docs/documentation/model-apis/workflows
- Portability: Portable. Reason: mature parts of our Python DAG can later be wrapped as a fal workflow, while exploratory codex iterations can stay local and manual.

### 13. fal Streaming Intermediate Events

- How it works: fal workflow streams emit `submit`, `completion`, `output`, and `error` events; completion events include per-step outputs. Evidence: https://fal.ai/docs/documentation/model-apis/workflows
- What it buys: the caller can inspect intermediate images, timings, and failures instead of only seeing the final result. Evidence: https://fal.ai/docs/documentation/model-apis/workflows
- Portability: Portable. Reason: our review folders can save each intermediate event as a named artifact, which fits the existing evidence-first review style.

### 14. fal Workflow Limits: Verified and Unverified

- How it works: verified by docs: fal workflows chain model calls and stream step events. Evidence: https://fal.ai/docs/documentation/model-apis/workflows
- Limit not verified: I did not find a primary-source statement in this pass confirming arbitrary branching, loops, conditional retries, or human-in-the-loop pauses inside fal workflow definitions. Evidence: Unverified.
- What it buys: the verified part is enough for deterministic server-side chains; open-ended agentic decisions should remain in Python/codex unless fal docs confirm those controls. Evidence: https://fal.ai/docs/documentation/model-apis/workflows
- Portability: Partially portable. Reason: simple linear or fixed-DAG chains are portable to fal workflows; adaptive judge/retry loops should stay in Python until verified.

### 15. Midjourney Style Reference Codes

- How it works: a research paper on style codes reports that Midjourney `sref` style-reference codes encode image style as short numeric codes and are used because style images can be shared without reposting the original source images. Evidence: https://arxiv.org/abs/2411.12811
- What is not verified here: official Midjourney moodboard UX, current `--sref` syntax, and whether users can generate reusable style handles from their own moodboard images were not verified from a primary Midjourney doc in this search pass. Evidence: Unverified.
- What it buys: the portable idea is a reusable style handle that compresses a set of style references into a named token or ID. Evidence: https://arxiv.org/abs/2411.12811
- Portability: Portable. Reason: we can create our own repo-local style handles as folders containing reference images, a contact sheet, palette swatches, and a YAML manifest.

### 16. Recraft Custom / Brand Styles

- How it works: Recraft's docs list `Styles` as a core feature and say users can apply a curated style or create their own style to stay on-brand. Evidence: https://www.recraft.ai/docs
- What it buys: the UX elevates style from one-off prompt text to a reusable brand/style object. Evidence: https://www.recraft.ai/docs
- Portability: Portable. Reason: our style packet can be a reusable object with named slots such as `medium`, `palette`, `line_language`, `toy_building_features`, and `negative_style`.

### 17. Leonardo Style Reference / Image Guidance

- Verified in this pass: not verified; no primary Leonardo doc page was captured by the available web search results. Evidence: Unverified.
- What it would buy if verified: a productized image-guidance UX that asks users to supply style reference images and lets the system abstract them into generation guidance. Evidence: Unverified.
- Portability: Partially portable. Reason: the general shape is already covered by IP-Adapter/Recraft/Midjourney sources, but Leonardo-specific automatic decisions should not be copied without primary docs.

### 18. Scenario Custom Style Training for Game Assets

- Verified in this pass: not verified; no primary Scenario doc page was captured by the available web search results. Evidence: Unverified.
- What it would buy if verified: training or fine-tuning a reusable game-asset style from a reference set so later generations follow one game's art direction. Evidence: Unverified.
- Portability: Partially portable. Reason: our stack can mimic the UX handle with curated reference packets, but actual model training is outside the stated gpt-image/fal/Python workflow unless a fal endpoint or separate training lane is added.

### 19. Layer-Style Asset Training

- Verified in this pass: not verified; no primary Layer doc page was captured by the available web search results. Evidence: Unverified.
- What it would buy if verified: a reusable production style layer for assets, likely useful for consistent sprite/prop libraries. Evidence: Unverified.
- Portability: Partially portable. Reason: adopt the "asset library as style memory" workflow shape, but do not assume Layer-specific training or UX automation.

### 20. Layout-First: Boxes, Scribbles, Edges, and SVG-Derived Guides

- How it works: ControlNet supports controls such as Canny, HED, scribble, segmentation, depth, and normal maps; GLIGEN and ComfyUI GLIGEN route concepts into bounding boxes. Evidence: https://github.com/lllyasviel/ControlNet and https://comfyanonymous.github.io/ComfyUI_examples/gligen/
- What it buys: geometry is decided before style, which directly matches die-cut SVG panel constraints. Evidence: https://github.com/lllyasviel/ControlNet and https://comfyanonymous.github.io/ComfyUI_examples/gligen/
- Portability: Portable. Reason: Python can render SVG silhouettes, cutout masks, safe-pocket boxes, dashed guides, and labeled feature regions as reference images before any model call.

### 21. Generate-Elements-Then-Compose

- How it works: verified sources in this pass support multi-step workflows and intermediate artifacts, but no primary source captured here specifically documented sprite-sheet generation followed by composition for Scenario/Layer. Evidence: https://fal.ai/docs/documentation/model-apis/workflows and Unverified for Scenario/Layer-specific sprite-sheet UX.
- What it buys: feature vocabulary can be developed separately from final panel layout, which is useful when windows, doors, signs, rooflines, and toy details need style consistency. Evidence: Workflow composition source: https://fal.ai/docs/documentation/model-apis/workflows
- Portability: Portable. Reason: gpt-image can generate candidate feature sheets during free iteration, Python can select/crop/arrange them into a composition guide, and the final model can redraw the full panel from that guide.

### 22. Iterative Region Inpainting for Feature Placement

- How it works: Flux Fill supports mask-based inpainting/outpainting, and ComfyUI lists inpainting as a supported workflow category. Evidence: https://bfl.ai/blog/24-11-21-tools and https://github.com/Comfy-Org/ComfyUI
- What it buys: missing or malformed localized features can be repaired without throwing away a good full-panel composition. Evidence: https://bfl.ai/blog/24-11-21-tools
- Portability: Portable. Reason: the SVG cutout masks, feature masks, and local defect masks can be generated deterministically in Python and passed to edit-capable image routes.

### 23. Intermediate Artifact Review as a First-Class UX

- How it works: fal workflow completion events expose per-step outputs, and ComfyUI workflows can be loaded/saved as artifacts. Evidence: https://fal.ai/docs/documentation/model-apis/workflows and https://github.com/Comfy-Org/ComfyUI
- What it buys: the reviewer can approve or reject rough layout, style transfer, and repair stages independently. Evidence: https://fal.ai/docs/documentation/model-apis/workflows
- Portability: Portable. Reason: our review folder can store `01-layout`, `02-style`, `03-final`, overlays, and gate logs as stable artifacts.

### 24. Reusable Style Handle as a Repo Object

- How it works: Midjourney-style codes compress style references into reusable codes according to the Stylecodes paper, while Recraft exposes reusable styles to stay on-brand. Evidence: https://arxiv.org/abs/2411.12811 and https://www.recraft.ai/docs
- What it buys: the same watercolor/toy-building look can be reused across multiple panels without restating it in prose every time. Evidence: https://www.recraft.ai/docs
- Portability: Portable. Reason: create a repo-local `style_handle` directory with source refs, crops, palette, line-language notes, prompt snippets, and a manifest consumed by Python.

## What Is Portable to Our Stack

- Fully portable workflow shapes: reference packet as reusable style handle; separate style and composition references; SVG-derived layout-first guides; labeled box/region maps; fixed multi-pass DAGs; intermediate artifact review; mask-based local repair where the target model supports image editing. Evidence: https://raw.githubusercontent.com/cubiq/ComfyUI_IPAdapter_plus/main/examples/ipadapter_style_composition.json and https://comfyanonymous.github.io/ComfyUI_examples/gligen/ and https://fal.ai/docs/documentation/model-apis/workflows and https://bfl.ai/blog/24-11-21-tools
- Partially portable workflow shapes: regional attention masking and IP-Adapter internals, because our gpt-image path does not expose model attention or adapter weights in the task brief. Evidence for source pattern: https://github.com/cubiq/ComfyUI_IPAdapter_plus/tree/main/examples
- Not portable as-is: copying Scenario/Layer/Leonardo product behavior, because primary docs were not verified in this pass. Evidence: Unverified.

## Recommendations

### Adopt First

1. Adopt a two-reference baseline: `style_packet` plus `composition_guide`.
   - Why: ComfyUI IP-Adapter has a direct style/composition split, and our SVG-panel work already needs separate art style and geometry channels. Evidence: https://raw.githubusercontent.com/cubiq/ComfyUI_IPAdapter_plus/main/examples/ipadapter_style_composition.json
   - First implementation shape: Python renders the SVG panel, safe pockets, cutout masks, and labeled feature boxes; Python also builds a contact sheet from watercolor/toy-building references.

2. Adopt layout-first guides before any style pass.
   - Why: ControlNet and GLIGEN both demonstrate that geometry can be routed through explicit structure channels before full rendering. Evidence: https://github.com/lllyasviel/ControlNet and https://comfyanonymous.github.io/ComfyUI_examples/gligen/
   - First implementation shape: make a deterministic `layout_ref.png` per panel with silhouette, no-go cutouts, safe pockets, labeled feature zones, and major facade boxes.

3. Adopt fixed three-stage generation: rough layout -> whole-panel style redraw -> local repair/final.
   - Why: Area Composition documents multi-pass workflows, Flux Redux documents image-variation/restyle from an input image, and Flux Fill documents mask-based inpainting/outpainting. Evidence: https://comfyanonymous.github.io/ComfyUI_examples/area_composition/ and https://bfl.ai/blog/24-11-21-tools
   - First implementation shape: codex gpt-image explores layout/style cheaply, fal gpt-image-2 is reserved for exact-frame finals, and Python gates each stage against the SVG template.

4. Adopt intermediate artifact review folders.
   - Why: fal workflows expose per-step completion outputs, and ComfyUI saves workflows as artifacts; both make intermediate inspection normal rather than exceptional. Evidence: https://fal.ai/docs/documentation/model-apis/workflows and https://github.com/Comfy-Org/ComfyUI
   - First implementation shape: each attempt gets `layout/`, `style/`, `repair/`, `final/`, overlays, and a `FEEDBACK.md` decision surface.

5. Adopt repo-local reusable style handles before training or platform-specific style products.
   - Why: Midjourney-style codes and Recraft styles both point toward reusable style handles, but our most portable version is just files plus manifest plus contact sheet. Evidence: https://arxiv.org/abs/2411.12811 and https://www.recraft.ai/docs
   - First implementation shape: `style-handle.yaml` records source images, crops, palette, line language, medium notes, forbidden artifacts, and the exact references to attach.

### Defer

1. Defer native regional attention masking.
   - Why: the source pattern is real in ComfyUI/IP-Adapter examples, but the gpt-image/fal path in the task brief does not expose attention masks. Evidence: https://github.com/cubiq/ComfyUI_IPAdapter_plus/tree/main/examples
   - Safer interim: use SVG-derived region maps, crop-specific references, and local validation overlays.

2. Defer Scenario/Layer-style training decisions.
   - Why: primary Scenario/Layer docs were not captured in this search pass, and actual training is outside the stated stack unless a separate training lane is added. Evidence: Unverified.
   - Safer interim: curate feature sheets and style handles, then test whether gpt-image/fal can reuse them consistently without model training.

3. Defer fal workflow productization until the Python DAG stabilizes.
   - Why: fal workflows are good for stable multi-step endpoint chains, but dynamic branch/retry/human-review behavior was not verified in the docs found here. Evidence: https://fal.ai/docs/documentation/model-apis/workflows and Unverified for dynamic branching/loops.
   - Safer interim: keep adaptive choices in Python/codex, then wrap only stable linear stages as fal workflows.

## Bottom Line

The strongest portable pattern is not a single platform feature. It is a contract:

1. make reference roles explicit;
2. separate style references from geometry references;
3. derive composition guides from the SVG template, not from prose;
4. pass through rough/style/repair stages with saved intermediate artifacts;
5. use masks and local repair only after a whole-panel style/composition pass is close enough to preserve.

This contract is supported by ComfyUI's graph workflows, IP-Adapter's style/composition split, ControlNet/GLIGEN layout controls, Flux Redux/Fill restyle and repair patterns, and fal workflow endpoint chaining. Evidence: https://github.com/Comfy-Org/ComfyUI and https://raw.githubusercontent.com/cubiq/ComfyUI_IPAdapter_plus/main/examples/ipadapter_style_composition.json and https://github.com/lllyasviel/ControlNet and https://comfyanonymous.github.io/ComfyUI_examples/gligen/ and https://bfl.ai/blog/24-11-21-tools and https://fal.ai/docs/documentation/model-apis/workflows
