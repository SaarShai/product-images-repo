# ComfyUI Node API Reference — C3 Workflow Builders

**Date:** 2026-07-06 | **Scope:** Exact node class names, params, enum values for workflow JSON construction.

---

## 1. IPAdapter Plus (cubiq/ComfyUI_IPAdapter_plus)

**GitHub:** [cubiq/ComfyUI_IPAdapter_plus](https://github.com/cubiq/ComfyUI_IPAdapter_plus)

### Node: IPAdapterAdvanced
- **Class name:** `IPAdapterAdvanced`
- **Inputs:**
  - `model` → MODEL
  - `ipadapter` → IPADAPTER
  - `image` → IMAGE
  - `weight` → FLOAT (default 1.0, range -1.0 to 5.0)
  - `weight_type` → enum: `linear`, `ease in`, `ease out`, `ease in-out`, `reverse in-out`, `weak input`, `weak output`, `weak middle`, `strong middle`, `style transfer`, `composition`, `strong style transfer`, `style and composition`, `style transfer precise`, `composition precise`
  - `combine_embeds` → enum: `concat`, `add`, `subtract`, `average`, `norm average`
  - `start_at` → FLOAT (0.0–1.0)
  - `end_at` → FLOAT (0.0–1.0)
  - `embeds_scaling` → enum: `V only`, `K+V`, `K+V w/ C penalty`, `K+mean(V) w/ C penalty`
  - `image_negative` → IMAGE (optional)
  - `attn_mask` → MASK (optional; attention mask)
  - `clip_vision` → CLIP_VISION (optional)

### Node: IPAdapterUnifiedLoader
- **Class name:** `IPAdapterUnifiedLoader`
- **Inputs:**
  - `model` → MODEL
  - `preset` → enum: `LIGHT` (SD1.5 only), `STANDARD`, `VIT-G`, `PLUS`, `PLUS FACE` (SD1.5 only), `FULL FACE` (SD1.5 only)
- **Outputs:** MODEL, IPADAPTER
- **Purpose:** Single node that loads both model and IPAdapter in one call; preferred over manual loader wiring.

### CLIP Vision File Expectations
- **For `ip-adapter-plus_sd15`:** Expects `ip-adapter-plus_sd15.safetensors` model + `sd1.5_model.safetensors` CLIP vision encoder (typically `openai/clip-vit-large-patch14` variant).

---

## 2. ControlNet Auxiliary Preprocessors (Fannovel16/comfyui_controlnet_aux)

**GitHub:** [Fannovel16/comfyui_controlnet_aux](https://github.com/Fannovel16/comfyui_controlnet_aux)

### Lineart Nodes
- **Class name:** `LineArtPreprocessor`
- **Inputs:**
  - `image` → IMAGE
  - (Advanced: `coarse` mode toggle, intensity controls)

### Depth Estimation
- **Class name:** `DepthAnythingPreprocessor`
- **Inputs:**
  - `image` → IMAGE
  - (Advanced: model selection, e.g. `DepthAnything` or `DepthAnything v2`)
- **Alternative:** `MiDaSDepthEstimator` (legacy; Depth Anything preferred for modern workflows)

---

## 3. ControlNet Apply (Core ComfyUI)

**GitHub:** [Comfy-Org/ComfyUI](https://github.com/Comfy-Org/ComfyUI)

### Node: ControlNetApplyAdvanced
- **Class name:** `ControlNetApplyAdvanced`
- **Inputs:**
  - `conditioning` → CONDITIONING (input condition)
  - `control_net` → CONTROL_NET
  - `image` → IMAGE (hint image from preprocessor)
  - `strength` → FLOAT (0.0–1.0, default 1.0)
  - `start_percent` → FLOAT (0.0–1.0, default 0.0; when to start applying ControlNet)
  - `end_percent` → FLOAT (0.0–1.0, default 1.0; when to stop applying ControlNet)
- **Output:** CONDITIONING

### Chaining Multiple ControlNets
**Pattern:** Sequential conditioning pass-through
```json
{
  "10": {
    "class_type": "ControlNetApplyAdvanced",
    "inputs": {
      "conditioning": ["9", 0],
      "control_net": ["8", 0],
      "image": ["canny_preprocessor", 0],
      "strength": 1.0,
      "start_percent": 0.0,
      "end_percent": 0.8
    }
  },
  "11": {
    "class_type": "ControlNetApplyAdvanced",
    "inputs": {
      "conditioning": ["10", 0],
      "control_net": ["cn_depth", 0],
      "image": ["depth_preprocessor", 0],
      "strength": 0.7,
      "start_percent": 0.2,
      "end_percent": 1.0
    }
  }
}
```
**Key:** Feed output conditioning `[node_id, 0]` from first ControlNetApplyAdvanced → input conditioning of the next.

---

## 4. macOS Apple Silicon / MPS Launch Flags

**Reference:** [Comfy-Org/ComfyUI discussions #13273](https://github.com/Comfy-Org/ComfyUI/discussions/13273)

### Recommended Invocation
```bash
python main.py --use-pytorch-cross-attention --force-fp16 --fp32-vae
```

### Flag Breakdown
- **`--use-pytorch-cross-attention`** → Forces PyTorch native cross-attention (better for M3/M4 MPS than split).
- **`--force-fp16`** → Use FP16 model precision (faster inference).
- **`--fp32-vae`** → **CRITICAL:** Keep VAE in FP32 to avoid black/corrupted image output on MPS.
- **`--use-split-cross-attention`** → Deprecated; avoid on modern M3/M4 chips (older fallback).

### Environment Variables (Optional)
```bash
export PYTORCH_ENABLE_MPS_FALLBACK=1
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
python main.py --use-pytorch-cross-attention --force-fp16 --fp32-vae
```

### Known Issues & Workarounds
| Issue | Cause | Fix |
|-------|-------|-----|
| Black/grey image output | FP16 VAE on MPS | Always use `--fp32-vae` |
| Slow inference | Split attention fallback | Use `--use-pytorch-cross-attention` |
| MPS fallback crashes | Missing MPS ops | Set `PYTORCH_ENABLE_MPS_FALLBACK=1` |

---

## 5. ComfyUI API Workflow JSON Format

**Reference:** [9elements/hosting-a-comfyui-workflow-via-api](https://9elements.com/blog/hosting-a-comfyui-workflow-via-api/)

### Workflow Structure (POST /prompt)
```json
{
  "1": {
    "class_type": "CheckpointLoaderSimple",
    "inputs": {
      "ckpt_name": "model.safetensors"
    }
  },
  "2": {
    "class_type": "LoadImage",
    "inputs": {
      "image": "input_image.png"
    }
  },
  "3": {
    "class_type": "KSampler",
    "inputs": {
      "model": ["1", 0],
      "positive": ["pos_cond", 0],
      "negative": ["neg_cond", 0],
      "seed": 12345,
      "steps": 20,
      "cfg": 7.5,
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 1.0
    }
  }
}
```

### Node ID Structure
- **Keys** are string node IDs (arbitrary but unique within workflow).
- **Values** contain:
  - `class_type` → string (exact node class name as registered)
  - `inputs` → dict of parameter values
    - **Literal values:** strings, numbers, booleans
    - **Node references:** `[node_id_string, output_index]` (e.g., `["1", 0]` = output 0 of node "1")

### LoadImage Filename Resolution
- **Default dir:** ComfyUI/`input/` folder
- **Filename format:** Relative path from input dir (e.g., `"image.png"` or `"subfolder/image.png"`)
- **Upload endpoint:** `POST /upload/image` (multipart/form-data)
  - Fields: `image` (file), `type` (input/temp/output), `subfolder` (optional)
  - Returns: JSON with `name` (use in LoadImage `image` field)

### Example with Upload
```bash
curl -X POST http://localhost:8188/upload/image \
  -F "image=@myimage.png" \
  -F "type=input" \
  -F "subfolder=mysubfolder"
```
Response:
```json
{
  "name": "myimage.png",
  "subfolder": "mysubfolder",
  "type": "input"
}
```
Then reference in workflow:
```json
"inputs": {
  "image": "mysubfolder/myimage.png"
}
```

---

## Builder Checklist

- [ ] IPAdapterAdvanced: confirm all `weight_type` enum values present (15 options).
- [ ] IPAdapterUnifiedLoader wired for single-call load (preferred over manual).
- [ ] ControlNetApplyAdvanced chaining: conditioning `[node_id, 0]` pass-through verified.
- [ ] start_percent / end_percent scheduling validated (0.0–1.0 range).
- [ ] macOS launch: `--use-pytorch-cross-attention --force-fp16 --fp32-vae` (no split-attention).
- [ ] LoadImage filenames: relative to input/ (or upload via POST first).
- [ ] API workflow JSON: node IDs are strings, references use `[id, idx]` format.

---

**Last verified:** Feb 2025 (cubiq IPAdapter Plus) + Jul 2026 (MPS flags) | **Maintainer:** C3 Workflow Team

---
LEADER VERIFICATION (2026-07-06, against installed ~/ComfyUI clone a590d60):
IPAdapterAdvanced ✓ (attn_mask input present, IPAdapterPlus.py:243), LineArtPreprocessor ✓,
DepthAnythingPreprocessor ✓, ControlNetApplyAdvanced ✓ (nodes.py:892, start_percent/end_percent).
Builders may bind these names as-is.
