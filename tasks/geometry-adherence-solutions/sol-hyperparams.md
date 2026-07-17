The six-run experiment should use a portrait 704×1472 working canvas, paired seeds across the hole-policy arms, and the same inpainting checkpoint for Stage B. Do not rotate the castle sideways or switch Stage B to the plain SDXL base.

## Frozen parameter card

| Parameter | Stage A | Stage B |
|---|---:|---:|
| Canvas | 704×1472 portrait | 704×1472 portrait |
| Scheduler | bundled `EulerDiscreteScheduler` | same |
| ControlNet scale | 0.65 | 0.65 |
| Control start/end | 0.0 / 1.0 | 0.0 / 1.0 |
| IP-Adapter | Plus ViT-H, style layer only | same |
| IP scale | 0.55 | 0.55 |
| LoRA scale | 0.70 | 0.70 |
| Guidance | 5.0 | 5.0 |
| Requested steps | 35 | 50 |
| Strength | 0.99 | 0.35 and 0.50 |
| Effective Stage-B steps | — | approximately 17 and 25 |
| Mask feather | 0 px | 0 px |
| Final Stage-C feather | 1 px, art side only | 1 px, art side only |
| Seeds | 17 and 71, both arms | selected Stage-A seed for both strengths |

Keep `guidance_rescale=0.0`, `guess_mode=False`, and `num_images_per_prompt=1`.

### 1. Resolution and orientation

Use **704×1472 portrait**. SDXL was trained across approximately 1024²-equivalent aspect buckets, and 704×1472 gives the narrow panel more usable width than 640×1536 while staying near the intended pixel area. SDXL generally performs best near its native high-resolution regime. [Diffusers SDXL documentation](https://huggingface.co/docs/diffusers/main/api/pipelines/stable_diffusion/stable_diffusion_xl)

The authoritative SVG is 1874.73×4213.29, ratio 0.445, as recorded in [svg-geometry-report.md](/Users/za/Documents/product%20images%20repo/tasks/geometry-evidentiary-princess-n02/svg-geometry-report.md). Fit it without distortion into 704×1472:

- Scale to approximately **655×1472**.
- Center with **24 px left / 25 px right** padding.
- Apply that identical affine transform to init image, mask, ControlNet image, hole polygons, socket mask, and later measurements.
- Never independently resize those inputs.

Generate upright. Rotating to landscape would make the model interpret the architecture sideways and force ControlNet to oppose its castle/building priors.

Important: [localgen.py](/Users/za/Documents/product%20images%20repo/scripts/localgen.py) currently stretches every input directly to `W×H`; that must be replaced by one shared aspect-preserving fit-and-pad transform before this experiment is valid.

### 2. Conditioning balance

Use:

```python
controlnet_conditioning_scale = 0.65
control_guidance_start = 0.0
control_guidance_end = 1.0

pipe.set_ip_adapter_scale({
    "up": {"block_0": [0.0, 0.55, 0.0]}
})

lora_scale = 0.70
guidance_scale = 5.0
```

The style-layer-only IP configuration is preferable to a global scalar for the Plus model: it retains reference appearance while suppressing its tendency to import composition/layout. Diffusers documents this exact “up block 0” style-only routing. [Official IP-Adapter guide](https://huggingface.co/docs/diffusers/using-diffusers/ip_adapter)

The Xinsir card demonstrates 1.0, but the repo’s measured structural precedent is around 0.6; **0.65** is the appropriate frozen compromise for already-exact lineart. [Xinsir model card](https://huggingface.co/xinsir/controlnet-canny-sdxl-1.0)

For Stage A:

```python
num_inference_steps = 35
strength = 0.99
mask_feather = 0
```

Use `NEAREST` for the binary mask resizing. Do not Gaussian-blur the Stage-A mask. Stage C supplies the deliberately bounded 1 px edge treatment.

### 3. Two IP-Adapter references

Pass both original flat-art references to one loaded adapter:

```python
ip_adapter_image = [[ref1, ref2]]
```

This nested structure means “two reference images for one adapter.” A plain `[ref1, ref2]` is interpreted as inputs for two separately loaded adapters and does not match the current single-adapter configuration.

Do not use the contact sheet: its whitespace, cards, labels, and reduced artwork scale contaminate the embedding. Do not pick only one reference: the two originals jointly represent the intended castle vocabulary.

Diffusers explicitly supports multiple images per IP-Adapter and batches their embeddings. [Official IP-Adapter guide](https://huggingface.co/docs/diffusers/using-diffusers/ip_adapter)

`localgen.py` currently accepts only one `--ip-image` and only a scalar IP scale. Both surfaces need adjustment before running.

### 4. Stage B

Use **the same `StableDiffusionXLControlNetInpaintPipeline` and the same inpainting checkpoint**, with the winning Stage-A image as `image`.

Treat Stage B as low-strength full-paintable-region inpainting:

- P1 winner: mask = silhouette − holes − socket.
- P2 winner: mask = silhouette − socket.
- Keep ControlNet, both IP references, LoRA, prompt, scales, scheduler, and seed unchanged.
- Run strengths **0.35 and 0.50** at **50 requested steps**.

Do not instantiate `StableDiffusionXLControlNetImg2ImgPipeline` with the inpainting checkpoint: the cached inpainting UNet has 9 input channels, while ordinary img2img expects a 4-channel UNet. Switching to `stabilityai/stable-diffusion-xl-base-1.0` would also change the checkpoint and confound the Stage-A-versus-Stage-B conclusion.

The 0.35/0.50 pair is correctly discriminating. At 50 requested steps it provides roughly 17 versus 25 active denoising steps, enough separation without making the lighter arm merely a handful of updates.

### 5. MPS defenses

Set:

```python
torch_dtype = torch.float16
generator = torch.Generator(device="cpu").manual_seed(seed)

pipe.to("mps")
pipe.enable_attention_slicing()
```

Then:

- Run one image at a time; do not batch the two seeds.
- Keep UNet, ControlNet, text encoders, IP image encoder, and bundled VAE in fp16 initially.
- Do not enable xFormers on MPS.
- Do not enable VAE slicing for batch size 1; it provides little benefit.
- Leave VAE tiling **off initially**. At 704×1472 it should not be necessary, and tiling can introduce tile-wise tone variation that would contaminate a style comparison. Enable it only if the load smoke test shows real memory pressure, then keep it enabled for all six scored runs. [Diffusers memory guide](https://huggingface.co/docs/diffusers/optimization/memory)
- Attention slicing is the useful defensive setting on Apple Silicon, especially below 64 GB unified memory or at nonstandard resolutions. [Diffusers MPS guidance](https://huggingface.co/docs/diffusers/v0.35.0/optimization/mps)
- Use `PYTORCH_ENABLE_MPS_FALLBACK=1` only after a specific unsupported-operation error; do not silently allow CPU fallback in the frozen run.
- Replace `localgen.py`’s broad model-loading `except Exception` with a pre-resolved load path for the experiment. A silent fallback changes the tested stack.

A two-step load/shape smoke test is appropriate before the scored seeds. It should verify weight loading, output dimensions, mask convention, two-reference embedding shape, and finite pixels—not judge image quality.

### 6. Prompt

Positive:

```text
Tall narrow fairytale princess-castle architectural panel, stacked ivory stone towers, slender coral roofs and small gold accents, coherent front elevation, fine hand-painted watercolor with delicate ink detail, soft translucent washes, warm cream peach and muted blue palette, subtle pigment granulation, polished children's storybook illustration, dense but orderly architectural detail.
```

Negative:

```text
photograph, photorealism, 3D render, glossy plastic, flat vector art, heavy black outlines, felt, fabric or fiber texture, neon colors, text, letters, watermark, sideways architecture, cropped main towers, floating fragments, duplicated buildings
```

No LoRA trigger word is needed; the installed LoRA README explicitly says so. Avoid prompting about apertures, masks, punching, exact SVGs, or white holes—the hard mask and ControlNet own those constraints.

Finally, use the same two seeds in both A-P1 and A-P2. That makes the hole-policy comparison paired rather than allowing seed variance to decide the winner. This remains an experiment authorizing a later evidentiary run, not a validation claim, consistent with [SYNTHESIS.md](/Users/za/Documents/product%20images%20repo/tasks/geometry-adherence-solutions/SYNTHESIS.md). No files were changed.


tokens used
200,090
The six-run experiment should use a portrait 704×1472 working canvas, paired seeds across the hole-policy arms, and the same inpainting checkpoint for Stage B. Do not rotate the castle sideways or switch Stage B to the plain SDXL base.

## Frozen parameter card

| Parameter | Stage A | Stage B |
|---|---:|---:|
| Canvas | 704×1472 portrait | 704×1472 portrait |
| Scheduler | bundled `EulerDiscreteScheduler` | same |
| ControlNet scale | 0.65 | 0.65 |
| Control start/end | 0.0 / 1.0 | 0.0 / 1.0 |
| IP-Adapter | Plus ViT-H, style layer only | same |
| IP scale | 0.55 | 0.55 |
| LoRA scale | 0.70 | 0.70 |
| Guidance | 5.0 | 5.0 |
| Requested steps | 35 | 50 |
| Strength | 0.99 | 0.35 and 0.50 |
| Effective Stage-B steps | — | approximately 17 and 25 |
| Mask feather | 0 px | 0 px |
| Final Stage-C feather | 1 px, art side only | 1 px, art side only |
| Seeds | 17 and 71, both arms | selected Stage-A seed for both strengths |

Keep `guidance_rescale=0.0`, `guess_mode=False`, and `num_images_per_prompt=1`.

### 1. Resolution and orientation

Use **704×1472 portrait**. SDXL was trained across approximately 1024²-equivalent aspect buckets, and 704×1472 gives the narrow panel more usable width than 640×1536 while staying near the intended pixel area. SDXL generally performs best near its native high-resolution regime. [Diffusers SDXL documentation](https://huggingface.co/docs/diffusers/main/api/pipelines/stable_diffusion/stable_diffusion_xl)

The authoritative SVG is 1874.73×4213.29, ratio 0.445, as recorded in [svg-geometry-report.md](/Users/za/Documents/product%20images%20repo/tasks/geometry-evidentiary-princess-n02/svg-geometry-report.md). Fit it without distortion into 704×1472:

- Scale to approximately **655×1472**.
- Center with **24 px left / 25 px right** padding.
- Apply that identical affine transform to init image, mask, ControlNet image, hole polygons, socket mask, and later measurements.
- Never independently resize those inputs.

Generate upright. Rotating to landscape would make the model interpret the architecture sideways and force ControlNet to oppose its castle/building priors.

Important: [localgen.py](/Users/za/Documents/product%20images%20repo/scripts/localgen.py) currently stretches every input directly to `W×H`; that must be replaced by one shared aspect-preserving fit-and-pad transform before this experiment is valid.

### 2. Conditioning balance

Use:

```python
controlnet_conditioning_scale = 0.65
control_guidance_start = 0.0
control_guidance_end = 1.0

pipe.set_ip_adapter_scale({
    "up": {"block_0": [0.0, 0.55, 0.0]}
})

lora_scale = 0.70
guidance_scale = 5.0
```

The style-layer-only IP configuration is preferable to a global scalar for the Plus model: it retains reference appearance while suppressing its tendency to import composition/layout. Diffusers documents this exact “up block 0” style-only routing. [Official IP-Adapter guide](https://huggingface.co/docs/diffusers/using-diffusers/ip_adapter)

The Xinsir card demonstrates 1.0, but the repo’s measured structural precedent is around 0.6; **0.65** is the appropriate frozen compromise for already-exact lineart. [Xinsir model card](https://huggingface.co/xinsir/controlnet-canny-sdxl-1.0)

For Stage A:

```python
num_inference_steps = 35
strength = 0.99
mask_feather = 0
```

Use `NEAREST` for the binary mask resizing. Do not Gaussian-blur the Stage-A mask. Stage C supplies the deliberately bounded 1 px edge treatment.

### 3. Two IP-Adapter references

Pass both original flat-art references to one loaded adapter:

```python
ip_adapter_image = [[ref1, ref2]]
```

This nested structure means “two reference images for one adapter.” A plain `[ref1, ref2]` is interpreted as inputs for two separately loaded adapters and does not match the current single-adapter configuration.

Do not use the contact sheet: its whitespace, cards, labels, and reduced artwork scale contaminate the embedding. Do not pick only one reference: the two originals jointly represent the intended castle vocabulary.

Diffusers explicitly supports multiple images per IP-Adapter and batches their embeddings. [Official IP-Adapter guide](https://huggingface.co/docs/diffusers/using-diffusers/ip_adapter)

`localgen.py` currently accepts only one `--ip-image` and only a scalar IP scale. Both surfaces need adjustment before running.

### 4. Stage B

Use **the same `StableDiffusionXLControlNetInpaintPipeline` and the same inpainting checkpoint**, with the winning Stage-A image as `image`.

Treat Stage B as low-strength full-paintable-region inpainting:

- P1 winner: mask = silhouette − holes − socket.
- P2 winner: mask = silhouette − socket.
- Keep ControlNet, both IP references, LoRA, prompt, scales, scheduler, and seed unchanged.
- Run strengths **0.35 and 0.50** at **50 requested steps**.

Do not instantiate `StableDiffusionXLControlNetImg2ImgPipeline` with the inpainting checkpoint: the cached inpainting UNet has 9 input channels, while ordinary img2img expects a 4-channel UNet. Switching to `stabilityai/stable-diffusion-xl-base-1.0` would also change the checkpoint and confound the Stage-A-versus-Stage-B conclusion.

The 0.35/0.50 pair is correctly discriminating. At 50 requested steps it provides roughly 17 versus 25 active denoising steps, enough separation without making the lighter arm merely a handful of updates.

### 5. MPS defenses

Set:

```python
torch_dtype = torch.float16
generator = torch.Generator(device="cpu").manual_seed(seed)

pipe.to("mps")
pipe.enable_attention_slicing()
```

Then:

- Run one image at a time; do not batch the two seeds.
- Keep UNet, ControlNet, text encoders, IP image encoder, and bundled VAE in fp16 initially.
- Do not enable xFormers on MPS.
- Do not enable VAE slicing for batch size 1; it provides little benefit.
- Leave VAE tiling **off initially**. At 704×1472 it should not be necessary, and tiling can introduce tile-wise tone variation that would contaminate a style comparison. Enable it only if the load smoke test shows real memory pressure, then keep it enabled for all six scored runs. [Diffusers memory guide](https://huggingface.co/docs/diffusers/optimization/memory)
- Attention slicing is the useful defensive setting on Apple Silicon, especially below 64 GB unified memory or at nonstandard resolutions. [Diffusers MPS guidance](https://huggingface.co/docs/diffusers/v0.35.0/optimization/mps)
- Use `PYTORCH_ENABLE_MPS_FALLBACK=1` only after a specific unsupported-operation error; do not silently allow CPU fallback in the frozen run.
- Replace `localgen.py`’s broad model-loading `except Exception` with a pre-resolved load path for the experiment. A silent fallback changes the tested stack.

A two-step load/shape smoke test is appropriate before the scored seeds. It should verify weight loading, output dimensions, mask convention, two-reference embedding shape, and finite pixels—not judge image quality.

### 6. Prompt

Positive:

```text
Tall narrow fairytale princess-castle architectural panel, stacked ivory stone towers, slender coral roofs and small gold accents, coherent front elevation, fine hand-painted watercolor with delicate ink detail, soft translucent washes, warm cream peach and muted blue palette, subtle pigment granulation, polished children's storybook illustration, dense but orderly architectural detail.
```

Negative:

```text
photograph, photorealism, 3D render, glossy plastic, flat vector art, heavy black outlines, felt, fabric or fiber texture, neon colors, text, letters, watermark, sideways architecture, cropped main towers, floating fragments, duplicated buildings
```

No LoRA trigger word is needed; the installed LoRA README explicitly says so. Avoid prompting about apertures, masks, punching, exact SVGs, or white holes—the hard mask and ControlNet own those constraints.

Finally, use the same two seeds in both A-P1 and A-P2. That makes the hole-policy comparison paired rather than allowing seed variance to decide the winner. This remains an experiment authorizing a later evidentiary run, not a validation claim, consistent with [SYNTHESIS.md](/Users/za/Documents/product%20images%20repo/tasks/geometry-adherence-solutions/SYNTHESIS.md). No files were changed.


