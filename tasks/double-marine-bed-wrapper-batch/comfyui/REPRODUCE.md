# ComfyUI capability — reproduce exactly

Scope: (T1) native transparent-background generation via ComfyUI-layerdiffuse
(LayerDiffuse / TransparentVAE) on SDXL; (T2) BiRefNet-HR background removal
as a comparison baseline, run against `image14`.

## 0. Install location (already existed; reused, not reinstalled)

- ComfyUI checkout: `/Users/za/ComfyUI` (git remote `comfyanonymous/ComfyUI`,
  commit `a590d60`, version `0.25.0`)
- venv: `/Users/za/ComfyUI/venv` (python 3.12.13, torch 2.12.1, MPS available)
- Custom node already present: `/Users/za/ComfyUI/custom_nodes/ComfyUI-layerdiffuse`
- Native core background-removal support already present (no custom node pack
  needed — `comfy/bg_removal_model.py` + `comfy/background_removal/birefnet.py`
  + `comfy_extras/nodes_bg_removal.py`, registering `LoadBackgroundRemovalModel`
  / `RemoveBackground`), so T2 used the **core BiRefNet loader**, not a
  third-party bg-removal node pack.

If ComfyUI is not present at `~/ComfyUI`, install with:

```bash
git clone https://github.com/comfyanonymous/ComfyUI.git ~/ComfyUI
cd ~/ComfyUI && python3 -m venv venv
venv/bin/pip install -r requirements.txt
git clone https://github.com/huchenlei/ComfyUI-layerdiffuse.git custom_nodes/ComfyUI-layerdiffuse
venv/bin/pip install -r custom_nodes/ComfyUI-layerdiffuse/requirements.txt
```

## 1. Model downloads (resumable, size-verified; no partial files kept)

All downloaded with `curl -L -C - --fail --retry 5 --retry-delay 5`, then the
byte size was diffed against the `Content-Length` header. Every file below
matched exactly on first or resumed attempt — no truncation.

```bash
# T1 — SDXL LayerDiffuse, Attention Injection (~700MB) + shared transparent VAE decoder (~200MB)
mkdir -p ~/ComfyUI/models/layer_model
cd ~/ComfyUI/models/layer_model
curl -L -C - --fail --retry 5 --retry-delay 5 -o layer_xl_transparent_attn.safetensors \
  "https://huggingface.co/LayerDiffusion/layerdiffusion-v1/resolve/main/layer_xl_transparent_attn.safetensors"   # 743,352,688 bytes
curl -L -C - --fail --retry 5 --retry-delay 5 -o vae_transparent_decoder.safetensors \
  "https://huggingface.co/LayerDiffusion/layerdiffusion-v1/resolve/main/vae_transparent_decoder.safetensors"     # 208,266,320 bytes

# T1 (secondary probe, SD1.5 attn_sharing) — BLOCKED, see Findings. Files downloaded but path is dead on this core:
curl -L -C - --fail --retry 5 --retry-delay 5 -o layer_sd15_transparent_attn.safetensors \
  "https://huggingface.co/LayerDiffusion/layerdiffusion-v1/resolve/main/layer_sd15_transparent_attn.safetensors" # 350,266,608 bytes
curl -L -C - --fail --retry 5 --retry-delay 5 -o layer_sd15_vae_transparent_decoder.safetensors \
  "https://huggingface.co/LayerDiffusion/layerdiffusion-v1/resolve/main/layer_sd15_vae_transparent_decoder.safetensors" # 208,266,320 bytes

# T1 (tertiary probe, SDXL Conv Injection, ~3.6GB) — downloaded as a follow-up
# probe for the weak-alpha finding on Attention Injection; see Findings for
# whether it was actually run before this report was written.
curl -L -C - --fail --retry 5 --retry-delay 5 -o layer_xl_transparent_conv.safetensors \
  "https://huggingface.co/LayerDiffusion/layerdiffusion-v1/resolve/main/layer_xl_transparent_conv.safetensors"   # 3,619,745,776 bytes

# T2 — BiRefNet-HR (core-native background_removal model type)
mkdir -p ~/ComfyUI/models/background_removal
cd ~/ComfyUI/models/background_removal
curl -L -C - --fail --retry 5 --retry-delay 5 -o birefnet_hr.safetensors \
  "https://huggingface.co/ZhengPeng7/BiRefNet_HR/resolve/main/model.safetensors" # 444,473,596 bytes
```

Verified `ZhengPeng7/BiRefNet_HR/model.safetensors` is the correct checkpoint
for the core loader by reading the safetensors header via an HTTP range
request (no full download needed to check) and confirming it contains the key
`bb.layers.1.blocks.0.attn.relative_position_index`, the exact key
`comfy/bg_removal_model.py::load_background_removal_model` gates on to select
the BiRefNet path.

Total downloaded for the delivered arms (attn + vae + birefnet_hr):
743,352,688 + 208,266,320 + 444,473,596 ≈ **1.34 GB** (well under the 8GB cap).
The SD1.5 + Conv probes added ≈ 4.16GB more (dead-end / follow-up probe,
see Findings) — grand total downloaded this session ≈ 5.5GB, still under 8GB.

## 2. Start ComfyUI headless

```bash
cd ~/ComfyUI
venv/bin/python main.py --listen 127.0.0.1 --port 8199 \
  --use-pytorch-cross-attention --force-fp16 --fp32-vae \
  > /path/to/logs/server.log 2>&1 &
curl -s http://127.0.0.1:8199/system_stats   # readiness probe
```

Note: port 8188 was already occupied by another concurrent ComfyUI process
(reparented to launchd, PID 19289, started by a sibling lane the same
morning) — left untouched; this task's server runs on **8199** to avoid any
interference.

## 3. Submit workflows (API format, no browser needed)

`run_workflow.py` POSTs an API-format workflow JSON to `/prompt`, polls
`/history/<id>`, and prints the `/view` URL of every output image.

```bash
cd "/Users/za/Documents/product images repo/tasks/double-marine-bed-wrapper-batch/comfyui"
python3 run_workflow.py workflow_t1_layerdiffuse_sdxl.json --port 8199               # T1 full-scene marine
python3 run_workflow.py workflow_t1_layerdiffuse_sdxl_turtle_single.json --port 8199  # T1 single-object retest
python3 run_workflow.py workflow_t2_birefnet_hr_image14.json --port 8199             # T2 BiRefNet-HR on image14
```

`workflow_t2_birefnet_hr_image14.json` expects the source image copied into
`~/ComfyUI/input/image14_source.png` first:

```bash
cp "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/ChatGPT Image Jul 7, 2026, 11_22_35 AM.png" \
  ~/ComfyUI/input/image14_source.png
```

## 4. Required workflow-graph fix (ComfyUI-layerdiffuse vs current core)

`ComfyUI-layerdiffuse`'s `LayeredDiffusionDecodeRGBA` node calls
`JoinImageWithAlpha().join_image_with_alpha(image, alpha)` — an **instance
method that no longer exists** on ComfyUI core 0.25.0's `JoinImageWithAlpha`
(core migrated to a `classmethod execute()` v3 IO-schema node). Every run
against `LayeredDiffusionDecodeRGBA` fails with
`AttributeError: 'JoinImageWithAlpha' object has no attribute
'join_image_with_alpha'`. Worked around by **not using that node** — use the
plain `LayeredDiffusionDecode` node (outputs `IMAGE, MASK`) plus a manual
`InvertMask` → `JoinImageWithAlpha` pair built from core's actual node
classes (see any `workflow_t1_*.json`, nodes `8`/`10`/`11`). No file inside
`custom_nodes/ComfyUI-layerdiffuse` was edited.

`ComfyUI-layerdiffuse`'s SD1.5 **`attn_sharing`** path (`AttentionSharingPatcher`)
is separately broken on this core: `AttentionSharingUnit.forward()` doesn't
accept the `transformer_options` kwarg the current attention-call plumbing
passes. This is a deeper monkey-patch incompatibility, not something a graph
work-around can fix — see Findings.

## 5. Measurement

```bash
# alpha histogram + stray-pocket flood fill: see metrics.json in this folder,
# produced by ad-hoc numpy/scipy.ndimage scripts (connected-components on
# alpha>127 for opaque islands, alpha<127 for background/holes).

# T2 frozen gate (read-only use of bg-benchmark; never edit that folder):
python3 tasks/double-marine-bed-wrapper-batch/bg-benchmark/verify_bg_solution.py \
  --manifest tasks/double-marine-bed-wrapper-batch/bg-benchmark/manifest.json \
  --candidate "image14=tasks/double-marine-bed-wrapper-batch/comfyui/outputs/t2-birefnet-hr/image14_birefnet_hr.png" \
  --json-report /tmp/gate_report_birefnet_hr.json
```

See `metrics.json` and `gate_report_birefnet_hr.json` in this folder for full
numbers, and the builder report for the verdicts.
