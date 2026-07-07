# W1 Multi-Input Conditioning Workflows

## 1. Per-source findings

### 1.1 Latentnaut ComfyUI Multi-Image Loader

URL: https://github.com/Latentnaut/ComfyUI-Multi-Image-Loader

- Capability added: a ComfyUI custom node named `MultiImageLoader` / "Load Multiple Images" that accepts multiple drag-and-drop or file-picker uploads directly in the node.
- Output added: one unified ComfyUI `IMAGE` batch tensor shaped `[B, H, W, C]`.
- Key parameter values:
- `resize_mode = resize_to_first`: resize every uploaded image to match the first image dimensions before stacking.
- `resize_mode = none`: attempt to stack as-is; source says this fails if image dimensions differ.
- Practical recipe:
- Use this for batched style/reference sets before IPAdapter Advanced, QwenVL visual analysis, upscalers, or VAE Encode.
- It is a loader/convenience node, not a conditioning model. It does not add weights, schedules, masks, or generation semantics by itself.
- Our-surface mapping:
- fal `flux-general`: no direct equivalent beyond uploading each image URL into `ip_adapter` or `reference_image_url`; batching must happen in our Python orchestration.
- local diffusers: map to a Python `list[PIL.Image]`, nested list for multi-IP-Adapter masking, or precomputed `ip_adapter_image_embeds`.
- native ComfyUI: install the node and connect `image_batch` to IPAdapter Advanced / QwenVL / any node that accepts `IMAGE` batches.

### 1.2 Ionio ControlNet with ComfyUI article

URL: https://www.ionio.ai/blog/navigating-controlnet-with-comfyui-for-enhanced-diffusion-models

- Capability described: ControlNet supplies image-based control vectors for structure/composition beyond prompt text.
- Concrete hardware guidance:
- For high-resolution images and running multiple ControlNets, the article recommends an NVIDIA GPU with at least `10GB` VRAM.
- For simpler tasks around `512x512`, it says `8GB` VRAM may suffice.
- It recommends `16GB` RAM or higher.
- Practical relevance:
- This is useful for install-risk assessment, not for exact recipe weights. It does not provide concrete ControlNet `strength`, `start_percent`, or `end_percent` values.
- Our-surface mapping:
- fal `flux-general`: ControlNet concept maps to `control_loras[].control_image_url`, `control_loras[].path`, `control_loras[].scale`, and `control_loras[].preprocess`.
- local diffusers: ControlNet concept maps to a `ControlNetModel` or list of `ControlNetModel`s plus matching `image` list.
- native ComfyUI: ControlNet concept maps to `Load ControlNet Model` plus one or more chained `Apply ControlNet` nodes.

### 1.3 ComfyUI Mixing ControlNet tutorial

URL: https://docs.comfy.org/tutorials/controlnet/mixing-controlnets

- Capability described: multiple ControlNets can be chained sequentially in ComfyUI through `Apply ControlNet` node connections.
- Example workflow: Pose ControlNet controls a character on the left; Scribble ControlNet controls a cat and scooter on the right.
- Concrete source values:
- Regional balancing recommendation: set similar ControlNet strengths when controls affect different regions.
- Explicit example value: both ControlNets at `strength = 1.0`.
- Prompt example: `"A woman in red dress, a cat riding a scooter, detailed background, high quality"`.
- Models named:
- `awpainting_v14.safetensors`
- `control_v11p_sd15_scribble_fp16.safetensors`
- `control_v11p_sd15_openpose_fp16.safetensors`
- `vae-ft-mse-840000-ema-pruned.safetensors`
- Start/end gap:
- The page does not expose concrete `start_percent` / `end_percent` values for the ControlNet chain in text.
- Recipe:
- For two equal-status spatial controls, start with `strength = 1.0` for each native ComfyUI `Apply ControlNet`.
- For our die-cut contour + relief case, this supports `canny/lineart contour scale = 1.0` and `depth/relief scale = 1.0` as an initial balanced pair, with the caveat that start/end schedules remain unverified from this source.

### 1.4 hardik-uppal ComfyUI-QwenVL-MultiImage

URL: https://github.com/hardik-uppal/ComfyUI-QwenVL-MultiImage

- Capability added: ComfyUI node for Qwen2.5-VL and Qwen3-VL visual-language models with multiple image inputs.
- Inputs:
- `images`: required main image input; supports batches.
- `images_batch_2`: optional second batch.
- `images_batch_3`: optional third batch.
- Default model: `Qwen3-VL-4B-Instruct`.
- Default system prompt: `"You are a helpful assistant."`
- Default user prompt: `"Describe these images..."`
- Quantization:
- Default `quantization = 8-bit (Balanced)`.
- Supported quantization modes: `FP16`, `8-bit`, `4-bit`.
- Advanced parameter ranges:
- `temperature`: `0.1-2.0`.
- `top_p`: `0.0-1.0`.
- `top_k`: `1-100`.
- `num_beams`: `1-10`.
- `repetition_penalty`: `1.0-2.0`.
- `max_tokens`: default `1024`, range `64-4096`.
- `device`: `auto`, `cuda`, `cpu`.
- `keep_model_loaded`: default `True`.
- Capability boundary:
- This is analysis/captioning/comparison over multiple images, not a diffusion-conditioning route.
- Recipe:
- Use it to ask: "Which reference image best matches the target style?", "List differences between generated candidate and template", or "Summarize style axes from several examples."
- Do not treat it as a ControlNet/IPAdapter replacement.
- Our-surface mapping:
- fal `flux-general`: no equivalent parameter; use upstream as a preflight evaluator, then feed selected image URLs into `ip_adapter`, `reference_image_url`, or `control_loras`.
- local diffusers: no generation parameter; use as a separate VLM preprocessor if installed outside diffusers.
- native ComfyUI: install custom node and connect multiple image batches.

### 1.5 comfyanonymous ComfyUI_examples repository

URL: https://github.com/comfyanonymous/ComfyUI_examples

- Capability described: example images contain ComfyUI workflow metadata and can be loaded into ComfyUI with the Load button or by drag-and-drop.
- Relevance:
- The repo is a workflow library rather than a prose parameter manual.
- It establishes the pattern that workflow images are authoritative source artifacts for exact node settings.
- Our recipe implication:
- For future extraction, prefer parsing PNG workflow metadata over reading screenshots manually.
- Current limitation:
- In this research pass, shell network access was unavailable, so PNG metadata values could not be programmatically extracted from remote workflow images.

### 1.6 ComfyUI ControlNet and T2I-Adapter examples

URL: https://comfyanonymous.github.io/ComfyUI_examples/controlnet/

- Important behavior:
- The raw image is passed directly to ControlNet/T2I-Adapter in the examples.
- The `ControlNetApply` node does not convert regular images into depth maps, canny maps, or other required control formats; preprocessing must be separate.
- Model placement:
- ControlNet model files go in `ComfyUI/models/controlnet`.
- SDXL Control LoRAs are used the same way as regular ControlNet model files and can be placed in the same directory.
- Efficiency warning:
- T2I-Adapters are described as much more efficient than ControlNets.
- ControlNet runs once every iteration; T2I-Adapter runs once total.
- Concrete visible value from the Scribble ControlNet example image:
- `Apply ControlNet` strength is visible as `0.500`.
- The same visible example uses `steps = 16`, `cfg = 6.000`, sampler `uni_pc`, scheduler `normal`, denoise `1.000`, latent `512 x 512`, batch size `1`.
- Recipe:
- For contour guides that are already rendered as edge maps, use `preprocess = None` on fal or feed the prepared map directly in ComfyUI.
- Do not expect `Apply ControlNet` to create Canny/depth/lineart maps.

### 1.7 ComfyUI Depth ControlNet tutorial

URL: https://docs.comfy.org/tutorials/controlnet/depth-controlnet

- Capability described: depth maps encode spatial relationships; brighter values represent closer regions, darker values farther regions.
- Example use case: architectural visualization.
- Models named:
- `architecturerealmix_v11.safetensors`
- `control_v11f1p_sd15_depth_fp16.safetensors`
- Workflow behavior:
- The page provides a workflow image with metadata and a separate depth input image.
- Combining guidance:
- The source explicitly recommends combining Depth ControlNet with other controls:
- `Depth + Lineart`: preserve spatial relationships while reinforcing outlines; suitable for architecture, products, and character design.
- `Depth + Pose`: preserve posture and spatial relationships for character scenes.
- Concrete param gap:
- The page does not expose a concrete depth ControlNet `strength`, `start_percent`, or `end_percent` in text.
- Recipe:
- For flat-panel illustration relief, use depth only when we have an intentionally designed relief/depth map; it should not replace the contour control.

### 1.8 TripoSR ComfyUI node guide

URL: https://www.triposrai.com/posts/triposr-comfyui-node-guide/

- Capability described: TripoSR converts a 2D image into a 3D mesh.
- Basic workflow:
- `Load Image` -> `TripoSR Generate` -> `3D Output`.
- Core settings:
- `resolution`: `256-1024`.
- Default basic workflow value: `512x512`.
- `quality_preset`: `Fast`, `Balanced`, `High`.
- `mesh_format`: `PLY`, `OBJ`, `GLB`.
- `texture_size`: `512-2048`.
- Advanced settings:
- `depth_estimation`: improve geometry.
- `normal_estimation`: improve surface normals.
- `cleanup_mesh`: remove artifacts.
- `subdivision_level`: `0-3`.
- Presets:
- Fast: `resolution = 256`, `Quality = Fast`, `Depth Estimation = False`, processing time `5-10 seconds`.
- Balanced: `resolution = 512`, `Quality = Balanced`, `Depth Estimation = True`, processing time `15-25 seconds`.
- High Quality: `resolution = 1024`, `Quality = High`, `Depth Estimation = True`, `Normal Estimation = True`, processing time `30-60 seconds`.
- Batch guidance:
- Batch size `2-8` depending on VRAM.
- Limited VRAM `6GB`: use `512` or lower and process single images only.
- Relevance to our work:
- LOW for 2D flat-panel illustration. It is useful only if we want a 3D mesh or derived depth/normal reference, which is not our normal Screenery panel output.
- Do not force it into the 2D generation loop unless a task explicitly asks for 3D reconstruction or mesh-derived depth.

### 1.9 Additional source: cubiq ComfyUI_IPAdapter_plus documentation, code, and examples

URLs:

- https://github.com/cubiq/ComfyUI_IPAdapter_plus
- https://raw.githubusercontent.com/cubiq/ComfyUI_IPAdapter_plus/main/NODES.md
- https://github.com/cubiq/ComfyUI_IPAdapter_plus/blob/main/IPAdapterPlus.py
- https://github.com/cubiq/ComfyUI_IPAdapter_plus/blob/main/CrossAttentionPatch.py
- https://raw.githubusercontent.com/cubiq/ComfyUI_IPAdapter_plus/main/examples/ipadapter_combine_embeds.json
- https://raw.githubusercontent.com/cubiq/ComfyUI_IPAdapter_plus/main/examples/ipadapter_regional_conditioning.json

- Capability described: ComfyUI reference implementation for IPAdapter models.
- General guidance:
- README suggests lowering `weight` to at least `0.8` and increasing steps.
- IPAdapter Advanced `weight`:
- Code default `weight = 1.0`; UI range `-1` to `5`, step `0.05`.
- Nodes doc says for `linear` weight type, a good starting point is `0.8`.
- `start_at` / `end_at`:
- Code default `start_at = 0.0`, `end_at = 1.0`.
- UI range for each is `0.0-1.0`, step `0.001`.
- Nodes doc gives example `start_at = 0.3` and says starting later creates very light conditioning because initial steps are most important.
- `weight_type` enum from code:
- `linear`
- `ease in`
- `ease out`
- `ease in-out`
- `reverse in-out`
- `weak input`
- `weak output`
- `weak middle`
- `strong middle`
- `style transfer`
- `composition`
- `strong style transfer`
- `style and composition`
- `style transfer precise`
- `composition precise`
- `weight_type` semantics from docs/code:
- `linear`: default constant application.
- `ease in`: weight is multiplied by `0.05 + 0.95 * (1 - t_idx / layers)`.
- `ease out`: weight is multiplied by `0.05 + 0.95 * (t_idx / layers)`.
- `ease in-out`: weight peaks around the middle layer index.
- `reverse in-out`: weight is lower around the middle and stronger toward ends.
- `weak input`, `weak middle`, `weak output`: multiply the named block by `0.2`.
- `strong middle`: multiplies input/output blocks by `0.2`, making middle relatively stronger.
- `style transfer`: SDXL maps only layer `6` to `weight`; SD1.5 maps layers `0,1,2,3,9,10,11,12,13,14,15`.
- `composition`: SDXL maps layer `3`; SD1.5 maps layer `4` to `0.25 * weight` and layer `5` to `weight`.
- `style and composition`: SDXL maps layer `3` to `weight_composition` and layer `6` to `weight`.
- `style transfer precise`: code uses the style/composition layer pattern with optional `style_boost`.
- `composition precise`: code uses strong composition routing with non-composition layers reduced to `0.1 * weight`.
- `combine_embeds` enum:
- `concat`
- `add`
- `subtract`
- `average`
- `norm average`
- `combine_embeds` semantics:
- `concat`: sends embeddings one after the other.
- `add`: sums embeddings.
- `subtract`: first image embedding minus the mean of the remaining images.
- `average`: mean of all embeddings.
- `norm average`: mean of normalized embeddings.
- Docs specifically advise `average` for lower-spec GPUs when sending multiple images.
- `embeds_scaling` enum:
- `V only`
- `K+V`
- `K+V w/ C penalty`
- `K+mean(V) w/ C penalty`
- Nodes doc says `K+mean(V) w/ C penalty` gives good quality at high weights `>1.0` without burning the image.
- IPAdapter Advanced multi-image example values:
- Batched via `ImageBatch` from `warrior_woman.png` and `anime_illustration.png`.
- `weight = 0.8`, `weight_type = linear`, `start_at = 0`, `end_at = 1`, `embeds_scaling = V only`.
- It tests `combine_embeds = concat`, `add`, `average`, and `norm average`.
- Example KSampler values: seed `0`, `steps = 30`, `cfg = 6.5`, sampler `dpmpp_2m`, scheduler `karras`, denoise `1`.
- IPAdapter regional example values:
- Three `IPAdapterRegionalConditioning` nodes use `weight = 0.7`, `weight_type = linear`, `start_at = 0`, `end_at = 1`.
- Regions come from a color mask image split into red, green, and black masks.
- `IPAdapterFromParams` combines params with `combine_embeds = concat`, `embeds_scaling = V only`.
- Example output latent: `768 x 512`, batch size `1`.
- Example KSampler values: seed `5`, `steps = 40`, `cfg = 8`, sampler `dpmpp_2m`, scheduler `karras`, denoise `1`.
- Regional routing:
- Node docs describe `attn_mask` as area-of-influence routing: black zones unaffected, white zones maximum influence; mask should match latent size or aspect ratio.
- The regional example uses `IPAdapterRegionalConditioning` plus per-region masks and per-region prompts/negative prompts.

### 1.10 Additional source: Hugging Face Diffusers IP-Adapter guide

URL: https://huggingface.co/docs/diffusers/en/using-diffusers/ip_adapter

- Capability described: IP-Adapter adds image-based guidance via image encoder features passed to new cross-attention layers while the original UNet/text cross-attention are frozen.
- Concrete scale semantics:
- `set_ip_adapter_scale(1.0)`: model is only conditioned on image prompt.
- `set_ip_adapter_scale(0.5)`: typically balanced between text and image prompt.
- Example value: `pipeline.set_ip_adapter_scale(0.8)`.
- Image-to-image example value:
- `strength = 0.5`.
- Image embedding reuse:
- `prepare_ip_adapter_image_embeds(..., num_images_per_prompt = 1, do_classifier_free_guidance = True)`.
- Example generation with reused embeds uses `num_inference_steps = 100`.
- Masking / regional routing:
- Binary masking assigns an IP-Adapter image to a specific output area.
- Example mask preprocessing: `height = 1024`, `width = 1024`.
- Example multiple face images: `pipeline.set_ip_adapter_scale([[0.7, 0.7]])`.
- Example passes masks through `cross_attention_kwargs = {"ip_adapter_masks": masks}`.
- Recipe:
- local diffusers can express regional IPAdapter routing more directly than fal if using `IPAdapterMaskProcessor` and `cross_attention_kwargs`.
- Use `0.5` for balanced prompt/reference, `0.8` when source style/subject should strongly steer the image, and `1.0` only when image conditioning should dominate.

### 1.11 Additional source: xinsir ControlNet Union SDXL model card

URL: https://huggingface.co/xinsir/controlnet-union-sdxl-1.0

- Capability described: one ControlNet-like SDXL model supporting many condition types.
- Source claims:
- Supports `10+` control conditions.
- Supports multi-condition generation.
- Condition fusion is learned during training.
- Source says there is no need to set hyperparameters or design prompts for condition fusion.
- Listed controls:
- Openpose, Depth, Canny, Lineart, AnimeLineart, Mlsd, Scribble, Hed, Pidi/Softedge, Teed, Segment, Normal.
- Listed multi-control examples:
- Openpose + Canny.
- Openpose + Depth.
- Openpose + Scribble.
- Openpose + Normal.
- Openpose + Segment.
- Apple note:
- The Diffusers usage snippet says switch to `"mps"` for Apple devices.
- Gaps:
- The model card does not provide exact ComfyUI node parameters, conditioning scales, or per-control start/end schedules in the visible text.
- Recipe:
- Potentially relevant for reducing multi-ControlNet memory/compute because one model can fuse multiple conditions, but exact ComfyUI param mapping needs separate workflow extraction.

### 1.12 Additional source: Hugging Face Diffusers ControlNet guide

URL: https://huggingface.co/docs/diffusers/en/using-diffusers/controlnet

- The page was opened during this pass as a quality source candidate.
- The available web view did not expose relevant concrete multi-ControlNet values in the snippet returned.
- It remains a source to revisit if we need exact diffusers `control_guidance_start`, `control_guidance_end`, and `controlnet_conditioning_scale` examples from the current docs.
- No numeric recipe in this report is derived from this source.

## 2. Cross-source recipe table

| Scenario | Source-backed recipe | Concrete params |
|---|---|---|
| Two spatial ControlNets, different regions | Use chained ComfyUI `Apply ControlNet` nodes. Keep strengths similar so one region does not overpower the other. | `strength = 1.0` for each ControlNet from ComfyUI mixing tutorial. |
| Simple single ControlNet scribble example | Prepared control map goes directly to ControlNet; do not rely on `ControlNetApply` preprocessing. | Visible example: `strength = 0.500`, `steps = 16`, `cfg = 6.000`, sampler `uni_pc`, scheduler `normal`, denoise `1.000`, latent `512 x 512`. |
| Depth + contour/product-line workflow | Combine depth with lineart/contour when spatial relationship plus outline fidelity matter. | Source gives the pairing `Depth + Lineart`; no concrete strength/start/end values exposed. |
| Batched style references into IPAdapter Advanced | Batch images, then combine embeds. Use lower-memory combination if needed. | `weight = 0.8`, `weight_type = linear`, `combine_embeds = average` for low-spec GPUs; example also uses `concat`, `add`, `norm average`; `start_at = 0`, `end_at = 1`, `embeds_scaling = V only`. |
| Stronger style transfer without full composition capture | Use IPAdapter Advanced style-oriented layer routing. | `weight_type = style transfer`; SDXL layer map `{6: weight}`; SD1.5 layers `{0,1,2,3,9,10,11,12,13,14,15}`. |
| Composition steering rather than style steering | Use composition layer routing. | `weight_type = composition`; SDXL layer `{3: weight}`; SD1.5 layers `{4: 0.25 * weight, 5: weight}`. |
| Precise style + composition split on SDXL | Use style/composition node or `style and composition` weight type. | SDXL map: layer `3 = weight_composition`, layer `6 = weight`; style composition node defaults `weight_style = 1.0`, `weight_composition = 1.0`, `expand_style = False`, `combine_embeds = average`. |
| High IPAdapter weights without burn | Use alternative embed scaling. | `embeds_scaling = K+mean(V) w/ C penalty`; source says useful at weights `>1.0`. |
| Regional IPAdapter routing | Attach masks to per-region IPAdapter params; black no influence, white max influence. | Comfy example: three regions with `weight = 0.7`, `weight_type = linear`, `start_at = 0`, `end_at = 1`, `combine_embeds = concat`, `embeds_scaling = V only`; diffusers example uses masks at `1024 x 1024` and `set_ip_adapter_scale([[0.7, 0.7]])`. |
| Multi-image visual-language preflight | Use QwenVL node to compare/caption multiple image batches before generation. | Inputs `images`, `images_batch_2`, `images_batch_3`; `model_name = Qwen3-VL-4B-Instruct`; `quantization = 8-bit`; `max_tokens = 1024`; optional `temperature = 0.1-2.0`, `top_p = 0.0-1.0`, `top_k = 1-100`. |
| Multi-condition ControlNet Union | Use one union model when many condition types must fuse. | Source states `10+` controls and learned multi-condition fusion with no extra hyperparameter, but gives no exact scale/start/end values. |
| TripoSR 3D extraction | Use only when output is mesh/depth/normal derived from a 2D image. | Basic default `512x512`; High Quality preset `resolution = 1024`, `Depth Estimation = True`, `Normal Estimation = True`; LOW relevance to normal flat-panel work. |

## 3. Our-surface mappings

### 3.1 Scenario: die-cut contour plus relief/depth control plus style references

ComfyUI concept -> fal `flux-general`:

- Canny/lineart ControlNet -> `control_loras[{path, control_image_url, scale, preprocess}]`.
- Use contour map as `control_image_url`.
- Use `preprocess = None` when our pipeline already created the edge/contour map.
- Source-backed initial `scale = 1.0` maps from ComfyUI mixing `strength = 1.0` balancing guidance.
- Depth ControlNet -> second `control_loras` entry with depth map as `control_image_url`.
- If fal must preprocess a normal image into depth, use `preprocess = depth`; if we already generated a depth map, keep `preprocess = None`.
- IPAdapter style refs -> `ip_adapter[{image_url, scale}]`.
- Source-backed initial style scale: `scale = 0.8` from IPAdapter Advanced and Diffusers examples.
- Simple reference-only style -> `reference_image_url` plus `reference_strength`; this is a simpler fallback when no separate IPAdapter weights are selected.

ComfyUI concept -> local diffusers SDXL/SD1.5:

- Canny/lineart + depth -> multi-ControlNet list, with matching control images in the same order.
- IPAdapter style refs -> `load_ip_adapter(...)`, `set_ip_adapter_scale(0.8)`, and `ip_adapter_image = [...]`.
- Regional masks -> `IPAdapterMaskProcessor().preprocess(..., height = 1024, width = 1024)` then `cross_attention_kwargs = {"ip_adapter_masks": masks}`.
- Source-backed scale choices: `0.5` balanced text/image, `0.8` stronger image guidance, `1.0` image-dominant.

ComfyUI concept -> native ComfyUI graph:

- `Load ControlNet Model` for contour/canny/lineart and depth.
- Chain `Apply ControlNet` nodes.
- Start with `strength = 1.0` for both when both controls are equally important.
- Feed prepared maps directly; add preprocessors upstream only when source images are not already control maps.
- Load IPAdapter via Unified Loader or Model Loader + CLIP Vision.
- IPAdapter Advanced: `weight = 0.8`, `weight_type = linear`, `combine_embeds = average` or `norm average`, `start_at = 0`, `end_at = 1`, `embeds_scaling = V only`.

### 3.2 Scenario: multiple style references, no regional masks

ComfyUI concept -> fal `flux-general`:

- Each style image -> one `ip_adapter` item.
- Set each `scale = 0.8` for stronger-but-not-exclusive style influence.
- If using one simpler style reference, use `reference_image_url` instead of IPAdapter.
- There is no sourced fal equivalent for ComfyUI `combine_embeds`; our orchestration must choose whether to pass separate adapters, make a contact sheet, or preselect/average externally.

ComfyUI concept -> local diffusers:

- For one adapter with several images, use `ip_adapter_image` / image embeds according to diffusers support.
- Use `set_ip_adapter_scale(0.5)` for balanced text/image or `0.8` for stronger reference adherence.
- For repeated runs, precompute with `prepare_ip_adapter_image_embeds(..., num_images_per_prompt = 1, do_classifier_free_guidance = True)`.

ComfyUI concept -> native ComfyUI:

- Use Multi-Image Loader or `ImageBatch`.
- IPAdapter Advanced:
- `weight = 0.8`.
- `weight_type = linear`.
- `combine_embeds = average` when memory is tight or when refs are peers.
- `combine_embeds = norm average` when ref magnitudes should be normalized before averaging.
- `combine_embeds = concat` when keeping separate image identities matters and memory allows it.
- `combine_embeds = add` when intentionally summing influences.
- `combine_embeds = subtract` when image 1 should keep identity and subsequent images define what to remove from the embedding.

### 3.3 Scenario: regional style/subject routing

ComfyUI concept -> fal `flux-general`:

- Task-specified fal surface has no explicit regional `mask` field in `ip_adapter[{image_url, scale}]`.
- Best mapped fallback: separate region-specific generations or a composed guide image, then merge with our mask/composite pipeline.
- If fal schema exposes optional IPAdapter masks, it must be reverified before use; not part of the required surface here.

ComfyUI concept -> local diffusers:

- Use binary masks with `IPAdapterMaskProcessor`.
- Example source values: mask preprocess `height = 1024`, `width = 1024`; `set_ip_adapter_scale([[0.7, 0.7]])`.
- Pass `cross_attention_kwargs = {"ip_adapter_masks": masks}`.

ComfyUI concept -> native ComfyUI:

- Use `IPAdapterRegionalConditioning` per region.
- Source-backed example values:
- Region weights `0.7`.
- `weight_type = linear`.
- `start_at = 0`.
- `end_at = 1`.
- Combine params with `IPAdapterCombineParams`.
- Apply with `IPAdapterFromParams` using `combine_embeds = concat`, `embeds_scaling = V only`.
- Use masks where black means no influence and white means maximum influence.

### 3.4 Scenario: QwenVL multi-image evaluation before generation

ComfyUI concept -> fal `flux-general`:

- No direct parameter mapping.
- Use QwenVL output as upstream decision text: select reference images, create style axes, or flag mismatches.

ComfyUI concept -> local diffusers:

- No direct pipeline parameter.
- Use QwenVL outside the generation pipe to choose `ip_adapter_image`, control map, prompt, or negative prompt.

ComfyUI concept -> native ComfyUI:

- Install QwenVL Multi-Image node.
- Feed `images`, `images_batch_2`, and `images_batch_3`.
- Use `model_name = Qwen3-VL-4B-Instruct`, `quantization = 8-bit`, `max_tokens = 1024` as source defaults.

### 3.5 Scenario: ControlNet Union instead of several ControlNets

ComfyUI concept -> fal `flux-general`:

- Closest map remains multiple `control_loras[]` entries.
- There is no source-backed fal ControlNet Union-specific `path`/selector recipe in this pass.

ComfyUI concept -> local diffusers:

- Potentially use the xinsir ControlNet Union model if supported by the installed diffusers version.
- Source says switch to `mps` for Apple devices, but does not provide Apple performance evidence.
- Exact scale/start/end values remain a gap.

ComfyUI concept -> native ComfyUI:

- Install a ControlNet Union-compatible custom node/model only after extracting an actual workflow.
- Source supports using one model for many control types and learned multi-condition fusion.
- Do not assume per-control weighting exists unless the workflow node exposes it.

### 3.6 Scenario: TripoSR

ComfyUI concept -> fal `flux-general`:

- No mapping for flat-panel generation.

ComfyUI concept -> local diffusers:

- No mapping unless a 3D-derived depth/normal pass is explicitly requested.

ComfyUI concept -> native ComfyUI:

- `Load Image` -> `TripoSR Generate` -> `3D Output`.
- Use only for mesh/depth/normal experiments, not for normal 2D panel art.

## 4. Install recommendation

Recommendation: not worth making local ComfyUI the primary SDXL multi-ControlNet + IPAdapter production surface on Apple Silicon yet; worth a small prototype install only if we specifically need native IPAdapter Advanced regional routing, workflow-image import, or visual graph debugging.

Evidence:

- Ionio recommends NVIDIA `10GB` VRAM for high-resolution images and multiple ControlNets; `8GB` may suffice only for simpler `512x512` tasks.
- ComfyUI_examples warns that ControlNet slows generation because the ControlNet model runs every iteration.
- The same ComfyUI_examples page says T2I-Adapter is far more efficient because it runs once total.
- IPAdapter_plus is powerful but is now maintenance-only and requires latest ComfyUI; this raises dependency risk for a production path.
- xinsir ControlNet Union may reduce multi-control overhead by fusing many conditions in one network, and its model card mentions switching to `mps` for Apple devices, but it does not provide Apple Silicon performance numbers or exact ComfyUI parameters.
- TripoSR docs are CUDA/NVIDIA-oriented and not relevant enough to justify ComfyUI for our 2D workflow.

Practical stance:

- Primary path: keep fal `flux-general` and local diffusers as the production-facing surfaces for separable geometry/style experiments.
- Prototype path: install ComfyUI only to inspect/import workflows and validate IPAdapter Advanced settings that are difficult to express elsewhere.
- Acceptance gate before relying on local ComfyUI: one local Apple Silicon run that proves SDXL + two controls + IPAdapter at our panel dimensions without unacceptable latency or memory failure.

## 5. Gaps list

- Remote PNG workflow metadata could not be programmatically extracted because shell network access was unavailable. Values visible in screenshots are cited only where readable.
- ComfyUI Mixing ControlNet tutorial provides `strength = 1.0` balancing guidance but does not expose concrete `start_percent` or `end_percent` values in text.
- ComfyUI Depth ControlNet tutorial does not expose concrete depth `strength`, `start_percent`, or `end_percent` values in text.
- The ControlNet and T2I-Adapter example screenshot visibly shows `strength = 0.500`, but no ControlNet start/end schedule is visible.
- Hugging Face Diffusers ControlNet docs were opened, but the returned web view did not expose source-backed multi-ControlNet numeric values; no numeric values in this report rely on that page.
- fal `flux-general` exact live schema was not reverified from a fal model page in this pass. The mapping uses the task-provided surface names and source-backed analogous values from ComfyUI/IPAdapter/Diffusers.
- fal regional IPAdapter masking is not part of the task-provided `ip_adapter[{image_url, scale}]` surface. Any optional fal mask field must be schema-checked before use.
- ControlNet Union exact ComfyUI node parameters, control-type selectors, condition scales, and schedule fields were not verified from a workflow file.
- No source provided Apple Silicon runtime numbers for SDXL + multiple ControlNets + IPAdapter in local ComfyUI.
- No source found in this pass gives a concrete canny-plus-depth recipe with both strengths and start/end percents for die-cut contour plus relief. The best sourced initial strength is balanced `1.0` / `1.0`; schedules remain unverified.

## 6. Sources

- https://github.com/Latentnaut/ComfyUI-Multi-Image-Loader
- https://www.ionio.ai/blog/navigating-controlnet-with-comfyui-for-enhanced-diffusion-models
- https://docs.comfy.org/tutorials/controlnet/mixing-controlnets
- https://github.com/hardik-uppal/ComfyUI-QwenVL-MultiImage
- https://github.com/comfyanonymous/ComfyUI_examples
- https://comfyanonymous.github.io/ComfyUI_examples/controlnet/
- https://docs.comfy.org/tutorials/controlnet/depth-controlnet
- https://www.triposrai.com/posts/triposr-comfyui-node-guide/
- https://github.com/cubiq/ComfyUI_IPAdapter_plus
- https://raw.githubusercontent.com/cubiq/ComfyUI_IPAdapter_plus/main/NODES.md
- https://github.com/cubiq/ComfyUI_IPAdapter_plus/blob/main/IPAdapterPlus.py
- https://github.com/cubiq/ComfyUI_IPAdapter_plus/blob/main/CrossAttentionPatch.py
- https://raw.githubusercontent.com/cubiq/ComfyUI_IPAdapter_plus/main/examples/ipadapter_combine_embeds.json
- https://raw.githubusercontent.com/cubiq/ComfyUI_IPAdapter_plus/main/examples/ipadapter_regional_conditioning.json
- https://huggingface.co/docs/diffusers/en/using-diffusers/ip_adapter
- https://huggingface.co/xinsir/controlnet-union-sdxl-1.0
- https://huggingface.co/docs/diffusers/en/using-diffusers/controlnet
