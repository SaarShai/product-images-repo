# C1 ComfyUI Bring-Up Report

Date: 2026-07-06

READY FOR JUDGING

## Verdict

Partial staging only. The reusable/offline model paths were inventoried and linked into a writable ComfyUI model root under this task folder, but this Codex sandbox blocked the required final bring-up:

- `~/ComfyUI/models` is not writable from this session, so direct links there failed with `Operation not permitted`.
- DNS/network resolution failed for Hugging Face, so missing SD1.5 and SD1.5 lineart weights could not be downloaded.
- Binding `127.0.0.1:8188` failed with `PermissionError: [Errno 1] ... operation not permitted`, so HTTP smoke testing could not run.

## Paths

- ComfyUI checkout: `/Users/za/ComfyUI`
- ComfyUI commit: `a590d60bb1d7d47c1cdb49fc8116b0e919fc4bd1`
- Python used: `/Users/za/ComfyUI/venv/bin/python`
- Writable model root used for this session: `/Users/za/Documents/product images repo/tasks/workflow-rebuild/comfy/models`
- Extra model config: `/Users/za/Documents/product images repo/tasks/workflow-rebuild/comfy/extra_model_paths.yaml`
- Startup log: `/Users/za/Documents/product images repo/tasks/workflow-rebuild/comfy/user/comfyui_8188.log`

## Venv / MPS

Command:

```bash
/Users/za/ComfyUI/venv/bin/python -c "import sys; print(sys.executable); import torch; print('torch', torch.__version__); print('mps_built', torch.backends.mps.is_built()); print('mps_available', torch.backends.mps.is_available())"
```

Observed:

```text
/Users/za/ComfyUI/venv/bin/python
torch 2.12.1
mps_built True
mps_available False
```

Base `/usr/bin/python3` also reported `mps_available False` in this managed session, so I treated MPS as unavailable here and used `--cpu` for the startup attempt. I did not reinstall torch because torch is present in the venv and the MPS failure is not isolated to the venv.

## HF Cache Inventory

| Cached repo | Snapshot path | File inventory | Decision |
|---|---|---:|---|
| `stable-diffusion-v1-5/stable-diffusion-v1-5` | `/Users/za/.cache/huggingface/hub/models--stable-diffusion-v1-5--stable-diffusion-v1-5/snapshots/451f4fe16113bff5a5d2269ed5ad43b0592e9a14` | 0 files; repo has one incomplete blob outside snapshot | Not usable. Requires SD1.5 checkpoint download. |
| `diffusers/stable-diffusion-xl-1.0-inpainting-0.1` | `/Users/za/.cache/huggingface/hub/models--diffusers--stable-diffusion-xl-1.0-inpainting-0.1/snapshots/115134f363124c53c7d878647567d04daf26e41e` | 17 files | Linked as diffusers model, but incomplete for use: no UNet weight file, only `unet/config.json`. |
| `xinsir/controlnet-canny-sdxl-1.0` | `/Users/za/.cache/huggingface/hub/models--xinsir--controlnet-canny-sdxl-1.0/snapshots/1271357eda52d54b857c650cacb5b51144643ccb` | 3 files | Linked both safetensors into writable `models/controlnet`. |

SDXL inpaint snapshot file list:

```text
model_index.json 690
scheduler/scheduler_config.json 479
text_encoder/config.json 746
text_encoder/model.fp16.safetensors 246144867
text_encoder_2/config.json 758
text_encoder_2/model.fp16.safetensors 1389382884
tokenizer/merges.txt 524619
tokenizer/special_tokens_map.json 472
tokenizer/tokenizer_config.json 737
tokenizer/vocab.json 1059962
tokenizer_2/merges.txt 524619
tokenizer_2/special_tokens_map.json 460
tokenizer_2/tokenizer_config.json 725
tokenizer_2/vocab.json 1059962
unet/config.json 1932
vae/config.json 659
vae/diffusion_pytorch_model.fp16.safetensors 167335338
```

xinsir snapshot file list:

```text
config.json 1235
diffusion_pytorch_model.safetensors 2502139104
diffusion_pytorch_model_V2.safetensors 2502139104
```

## Model Inventory

| Name | Path used by ComfyUI config | Source | Size |
|---|---|---|---:|
| IPAdapter SD1.5 model already present | `/Users/za/ComfyUI/models/ipadapter/ip-adapter-plus_sd15.safetensors` | Existing ComfyUI model file | 94M reported in task context |
| CLIP vision `CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors` | `/Users/za/Documents/product images repo/tasks/workflow-rebuild/comfy/models/clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors` | Symlink to `/Users/za/models-gen/ipadapter/models/image_encoder/model.safetensors` | 2,528,373,448 bytes |
| xinsir SDXL canny ControlNet | `/Users/za/Documents/product images repo/tasks/workflow-rebuild/comfy/models/controlnet/xinsir-controlnet-canny-sdxl-1.0.safetensors` | Symlink to HF cache blob via cached snapshot | 2,502,139,104 bytes |
| xinsir SDXL canny ControlNet V2 | `/Users/za/Documents/product images repo/tasks/workflow-rebuild/comfy/models/controlnet/xinsir-controlnet-canny-sdxl-1.0-v2.safetensors` | Symlink to HF cache blob via cached snapshot | 2,502,139,104 bytes |
| SDXL inpaint diffusers folder | `/Users/za/Documents/product images repo/tasks/workflow-rebuild/comfy/models/diffusers/stable-diffusion-xl-1.0-inpainting-0.1` | Symlink to HF cache snapshot | Incomplete; largest present file 1,389,382,884 bytes |
| SD1.5 checkpoint | expected under `models/checkpoints/` | Missing; download blocked by DNS | 0 |
| SD1.5 lineart ControlNet | expected under `models/controlnet/` | Missing; download blocked by DNS | 0 |
| Optional SD1.5 depth ControlNet | expected under `models/controlnet/` | Not attempted after required downloads were blocked | 0 |

## Download Attempts

Required lineart download probe:

```bash
curl -L -I --connect-timeout 20 --max-time 60 https://huggingface.co/comfyanonymous/ControlNet-v1-1_fp16_safetensors/resolve/main/control_v11p_sd15_lineart_fp16.safetensors
```

Observed:

```text
curl: (6) Could not resolve host: huggingface.co
```

Because DNS was unavailable, I did not start large fallback downloads or touch the Hugging Face cache.

## Server Launch Attempt

Requested log target `~/ComfyUI/server.log` was not usable because this session cannot write under `~/ComfyUI`. I used the task log path instead.

Command attempted:

```bash
/Users/za/ComfyUI/venv/bin/python /Users/za/ComfyUI/main.py \
  --listen 127.0.0.1 \
  --port 8188 \
  --cpu \
  --extra-model-paths-config "/Users/za/Documents/product images repo/tasks/workflow-rebuild/comfy/extra_model_paths.yaml" \
  --input-directory "/Users/za/Documents/product images repo/tasks/workflow-rebuild/comfy/input" \
  --output-directory "/Users/za/Documents/product images repo/tasks/workflow-rebuild/comfy/output" \
  --user-directory "/Users/za/Documents/product images repo/tasks/workflow-rebuild/comfy/user"
```

Observed useful startup facts:

```text
Adding extra search path checkpoints /Users/za/Documents/product images repo/tasks/workflow-rebuild/comfy/models/checkpoints
Adding extra search path clip_vision /Users/za/Documents/product images repo/tasks/workflow-rebuild/comfy/models/clip_vision
Adding extra search path controlnet /Users/za/Documents/product images repo/tasks/workflow-rebuild/comfy/models/controlnet
Adding extra search path diffusers /Users/za/Documents/product images repo/tasks/workflow-rebuild/comfy/models/diffusers
Device: cpu
```

Observed blockers:

```text
Cannot import /Users/za/ComfyUI/custom_nodes/ComfyUI-layerdiffuse module for custom nodes: No module named 'diffusers'
Failed to initialize database ... [Errno 1] Operation not permitted: '/Users/za/ComfyUI/user/comfyui.db.lock'
PermissionError: [Errno 1] error while attempting to bind on address ('127.0.0.1', 8188): [errno 1] operation not permitted
```

ComfyUI-Manager also attempted network fetches and fell back to local mode because `raw.githubusercontent.com` could not resolve.

## Smoke Test

Not verified. I did not run `scripts/comfy_run.py` because both prerequisites failed:

- no HTTP server could bind to `127.0.0.1:8188`;
- no usable SD1.5 checkpoint is available in `models/checkpoints/`.

No PNG was produced, so PNG dimensions and nonblank variance are unverified.

## Assumptions

- The managed Codex sandbox, not the physical Mac, is responsible for the localhost bind denial and write denial under `~/ComfyUI`.
- The offline SD1.5 cache cannot be converted because its snapshot contains zero files.
- The cached SDXL inpaint repo cannot be relied on until the missing UNet weight is present.
- A non-sandboxed shell with DNS access should first fetch SD1.5 checkpoint and SD1.5 lineart ControlNet into the writable model root or directly into `~/ComfyUI/models`, then relaunch.

## Next Safe Commands Outside This Sandbox

Run from a normal local terminal if network and local writes are available:

```bash
mkdir -p ~/ComfyUI/models/checkpoints ~/ComfyUI/models/controlnet ~/ComfyUI/models/clip_vision
ln -sfn /Users/za/models-gen/ipadapter/models/image_encoder/model.safetensors ~/ComfyUI/models/clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors
```

Then fetch the missing SD1.5 checkpoint and SD1.5 lineart ControlNet with resume into `~/ComfyUI/models/checkpoints/` and `~/ComfyUI/models/controlnet/`, and run:

```bash
cd ~/ComfyUI
PYTORCH_ENABLE_MPS_FALLBACK=1 ~/ComfyUI/venv/bin/python ~/ComfyUI/main.py --listen 127.0.0.1 --port 8188 --use-pytorch-cross-attention --force-fp16 --fp32-vae > ~/ComfyUI/server.log 2>&1
```
