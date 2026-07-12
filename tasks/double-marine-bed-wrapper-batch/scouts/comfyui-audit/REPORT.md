# Local ComfyUI background-removal audit

**Audit date:** 2026-07-09

**Scope:** read-only outside this audit folder; no installs, model downloads, paid calls, production finals, ComfyUI changes, or commits

**Verdict:** the local ComfyUI core is healthy on Apple MPS, but no complete background-removal route is runnable from the current Comfy node registry and model folders. The smallest credible image14 scout is a single new SAM 3.1 checkpoint using **point-only positive/negative supervision** before the already-proven local correction-led ViTMatte pipeline. It is specified in `SCOUT-PLAN.md`; it was not run.

## Executive findings

1. There is one bounded-discovery match for a local ComfyUI install: `/Users/za/ComfyUI`. It is a clean Git checkout at `a590d60bb1d7d47c1cdb49fc8116b0e919fc4bd1` (`0.25.0`), not a Desktop app bundle.
2. A fresh isolated core-only server launch succeeded on `127.0.0.1:8198` with Python `3.12.13`, Torch `2.12.1`, and device `mps`. During the live audit, `/system_stats` and `/object_info` responded and 556 core node types registered. The process was stopped cleanly. The isolated directories contained no files afterward and `/Users/za/ComfyUI` remained Git-clean. These response facts are transcript-observed; the intentionally ephemeral launch retained no raw response artifact.
3. ComfyUI core already contains `LoadBackgroundRemovalModel` and `RemoveBackground`, plus the official `Remove Background (BiRefNet)` blueprint. The required `birefnet.safetensors` is absent: `/Users/za/ComfyUI/models/background_removal/` contains only a zero-byte placeholder, and the live node's model dropdown was empty.
4. ComfyUI core also contains `SAM3_Detect` with text, box, positive-point, and negative-point prompts. Its official SAM 3.1 checkpoint is absent. The installed blueprint names `sam3.1_multiplex_fp16.safetensors`, a 1,745,546,848-byte file under the custom SAM License. A concurrent text-only SAM3 scout returned one coarse mask and failed internal topology, bubbles/fish, and edge quality; the proposed local scout therefore deliberately omits text conditioning and tests the core point decoder with explicit negative interior-paper points.
5. Useful weights exist elsewhere but are not wired into active ComfyUI: cached BEN2 and ViTMatte-S safetensors plus six `~/.u2net` ONNX removal models. The active Comfy venv has no BEN2, rembg, PyMatting, diffusers, or transparent-background package, and core's BiRefNet loader does not accept those cached architectures/formats as substitutes.
6. The separate repo environment `.venv-gen` does have BEN2, ViTMatte dependencies, PyMatting, diffusers, and transparent-background. Its ViTMatte-S route already ran successfully on MPS for image14 and proved that matting is viable but cannot repair a wrong upstream topology.
7. No inspected prior Comfy workflow used a background-removal/matting node. Prior Comfy work was generation/inpainting/ControlNet/IPAdapter work. Historical full-node logs prove successful MPS rendering, while LayerDiffuse repeatedly failed import because `diffusers` is missing.

## Bounded discovery and limitation

The search covered:

- indexed/signature-name matches under `/Users/za`;
- expected app, Application Support, Pinokio, and Stability Matrix locations;
- `/Users/za/ComfyUI`, its Git state, launch files, venvs, models, custom nodes, user database, logs, blueprints, and PNG metadata;
- repo-local Comfy helpers and workflow JSONs under `/Users/za/Documents/product images repo`;
- relevant Hugging Face, `~/.u2net`, and repo `.venv-gen` caches.

The only install match was `/Users/za/ComfyUI`; no Comfy `.app`, LaunchServices registration, Pinokio root, or Stability Matrix root was found. This supports “one discoverable local install,” not the impossible stronger claim that an arbitrarily renamed, unindexed copy exists nowhere on disk.

### Install and launch surface

| Item | Exact state |
|---|---|
| Checkout | `/Users/za/ComfyUI` |
| Git | `master...origin/master`, clean |
| Commit | `a590d60bb1d7d47c1cdb49fc8116b0e919fc4bd1`, 2026-06-17, `feat: SCAIL-2 multireference (CORE-310) (#14509)` |
| Origin | `https://github.com/comfyanonymous/ComfyUI.git` |
| Core version | `0.25.0` |
| Frontend/templates/docs | `1.45.15` / `0.10.0` / `0.5.4` |
| Host launcher | `/Users/za/ComfyUI/main.py`; no Mac app wrapper found |
| Repo API helpers | `scripts/comfy_build_workflow.py`, `scripts/comfy_run.py` |
| Active environment | `/Users/za/ComfyUI/venv`, Python 3.12.13 arm64 |
| Old environment | `/Users/za/ComfyUI/venv.py39.bak`, Python 3.9.6 with system-site-packages enabled |
| Separate capable environment | repo `.venv-gen`, not used by `main.py` |

## Fresh isolated server evidence

The one audit launch used the real checkout and model registry but isolated every normal write surface inside this audit folder, disabled all custom/API nodes, used an in-memory database, and set `PYTHONDONTWRITEBYTECODE=1` plus isolated cache variables:

```text
/Users/za/ComfyUI/venv/bin/python /Users/za/ComfyUI/main.py
  --listen 127.0.0.1 --port 8198 --disable-auto-launch
  --disable-all-custom-nodes --disable-api-nodes
  --database-url sqlite:///:memory:
  --input-directory  .../comfyui-audit/live/input
  --output-directory .../comfyui-audit/live/output
  --temp-directory   .../comfyui-audit/live/temp
  --user-directory   .../comfyui-audit/live/user
```

Observed fresh evidence:

- `Starting server` and `To see the GUI go to: http://127.0.0.1:8198`;
- `/system_stats`: macOS arm64, 51,539,607,552 bytes unified RAM/VRAM, Python 3.12.13, Torch 2.12.1, device `mps`, deploy environment `local-git`;
- `/object_info`: 556 registered core node types;
- `/object_info/LoadBackgroundRemovalModel`: loaded, but `options: []`;
- `/object_info/RemoveBackground`, `/object_info/SAM3_Detect`, and `/object_info/JoinImageWithAlpha`: loaded with their expected schemas;
- clean Ctrl-C shutdown; no listener remained on 8198; no files were left in `comfyui-audit/live`; the Comfy checkout remained clean.

This proves the core server can launch without mutating the install. It does not prove that a missing model will infer on MPS, or that every custom node is healthy. Startup still reported missing `comfy_kitchen` (FP8/FP4 unavailable) and duplicate AVFoundation classes from `cv2` and `av`.

Historical full-node logs at `/Users/za/ComfyUI/server.log` and `/Users/za/ComfyUI/user/comfyui_{8188,8199}*.log` independently show successful MPS servers and many completed prompts, including 182–599 second generations. The current server is stopped.

## Installed node and weight inventory

The machine-readable detail is in `inventory.json`.

### Core capabilities present

- Background inference: `LoadBackgroundRemovalModel`, `RemoveBackground`.
- Promptable segmentation: `SAM3_Detect`, `SAM3_VideoTrack`, `SAM3_TrackPreview`, `SAM3_TrackToMask`.
- Mask construction/refinement: `MaskToImage`, `ImageToMask`, `ImageColorToMask`, `SolidMask`, `InvertMask`, `CropMask`, `MaskComposite`, `FeatherMask`, `GrowMask`, `ThresholdMask`, `MaskPreview`.
- Alpha/compositing/save: `PorterDuffImageComposite`, `SplitImageWithAlpha`, `JoinImageWithAlpha`, `SaveImage`, `SaveImageAdvanced`. Core `SaveImage` creates a PIL image from all tensor channels, so a four-channel result from `JoinImageWithAlpha` is saved as RGBA.
- Upscaling: `UpscaleModelLoader`, `ImageUpscaleWithModel`, `ImageScale`, `ImageScaleBy`; local `RealESRGAN_x4plus.safetensors` is present.

### Missing from the active Comfy registry

- no trimap builder or ViTMatte node;
- no foreground-color estimation/decontamination node for paper-colored edge spill;
- no professional chroma key/despill node;
- no true alpha-aware super-resolution node;
- no currently selectable background-removal or SAM3 checkpoint.

### Custom nodes

| Pack | Commit | Runtime state | Background relevance |
|---|---|---|---|
| ComfyUI-Manager | `2e93040d` | imports | catalogue/install manager only |
| ComfyUI-layerdiffuse | `b4f6a9e0` | **import failed**: no `diffusers` | generates/decodes transparent diffusion layers; not an existing-image remover |
| ComfyUI_IPAdapter_plus | `a0f451a5` | imports | no removal/matting route |
| comfyui_controlnet_aux | `e8b689a5` (1.1.5) | imports | has RGB SAM/OneFormer/Uniformer preprocessors, not a foreground alpha pipeline; its `ckpts/` and Facebook SAM cache are absent |
| websocket_image_save.py | loose file | imports | transport helper only |

`comfyui_controlnet_aux`'s `SAMPreprocessor` automatically produces a colored segmentation visualization (`IMAGE`), not a promptable foreground `MASK`. Treating its presence as a ready remover would be a category error.

## Framework / node / model / suitability matrix

| Route | Framework and node layer | Model/weight | Current readiness | License evidence | Image14 suitability |
|---|---|---|---|---|---|
| Native BiRefNet | Comfy core `LoadBackgroundRemovalModel` → `RemoveBackground` → `InvertMask` → `JoinImageWithAlpha` | Official Comfy repack, 444,473,596 bytes, missing from `models/background_removal` | Node + blueprint present; **weight absent** | [Comfy-Org BiRefNet](https://huggingface.co/Comfy-Org/BiRefNet) says MIT and exact folder | Mechanically simple, but it repeats the class-agnostic BiRefNet family already represented in prior CLI failures. It returns a mask only and adds no semantic supervision or color decontamination. Not the one scout. |
| RMBG/BiRefNet/BEN/SDMatte omnibus | Third-party [1038lab/ComfyUI-RMBG](https://github.com/1038lab/ComfyUI-RMBG) | Many automatically downloaded models | Not installed; broad node/model/dependency surface | Node pack GPL-3.0; BRIA RMBG-2.0 weights are [non-commercial without a separate agreement](https://huggingface.co/briaai/RMBG-2.0) | Credible general toolkit, but too broad for a one-scout audit and mostly repeats failed automatic architecture families. |
| BEN2 | Third-party [BEN2_ComfyUI](https://github.com/PramaLLC/BEN2_ComfyUI) or 1038lab | BEN2 Base; 380,577,976-byte safetensors is cached | Weight cached outside Comfy; node and `ben2` package absent from active venv | [BEN2 model card](https://huggingface.co/PramaLLC/BEN2) labels Base MIT and describes confidence-guided matting | Credible automatic remover; still no user-conditioned topology. Better than a binary-only model in principle, but not the smallest differentiating test. |
| InSPyReNet | Third-party [ComfyUI-Inspyrenet-Rembg](https://github.com/john-mnz/ComfyUI-Inspyrenet-Rembg) | Automatically downloaded InSPyReNet | Not installed; active venv lacks `transparent-background`; prior image14 hybrid exists and failed | Node/upstream [transparent-background](https://github.com/plemeri/transparent-background) are MIT | Not selected because image14 already has direct InSPyReNet evidence and the failure was semantic/topological, not merely node packaging. |
| SAM 3.1 topology | Native core `CheckpointLoaderSimple` + point-only `SAM3_Detect` | `sam3.1_multiplex_fp16.safetensors`, 1,745,546,848 bytes, missing | Core nodes + blueprint present; weight absent; MPS inference not yet proven | [Official Comfy SAM 3.1 guide](https://docs.comfy.org/tutorials/utility/video-segment-sam3), [Comfy-Org checkpoint](https://huggingface.co/Comfy-Org/sam3.1), [SAM License](https://github.com/facebookresearch/sam3/blob/main/LICENSE) | **Best remaining differentiating topology scout, but high-risk.** A concurrent text-only SAM3 request produced one solid coarse silhouette and failed. Core point-only decoding is still untested and can explicitly reject interior paper; its hard mask must feed matting/decontamination and fail closed if it cannot keep disconnected details. |
| Trimap + ViTMatte | No installed Comfy node. Credible third-party option: Timesaver `TS_Matting_ViTMatte`; lean option: existing repo CLI | Cached ViTMatte-S, 103,294,572 bytes; proven MPS | Ready in `.venv-gen`, not in active Comfy | [ViTMatte official repo](https://github.com/hustvl/ViTMatte) MIT; cached HF model is [Apache-2.0](https://huggingface.co/hustvl/vitmatte-small-composition-1k) | Proven to preserve soft alpha, but prior run inherited wrong sure-foreground regions. Pairing it with SAM3's supervised topology is the selected hybrid. |
| Chroma key + despill | Credible third-party [Timesaver](https://github.com/AlexYez/comfyui-timesaver) `TS_Keyer` / `TS_Despill` | Algorithmic, no removal weight | Not installed; pack exposes 60 nodes and has a broad audio/LLM dependency surface | MIT | Green/blue/red keying is mismatched to a near-white paper background whose pale peach/cream watercolor must remain. Despill targets saturated screen spill, not paper-colored unmixing. |
| Alpha-aware upscale | Core split/recombine plus RGB RealESRGAN; no single alpha-aware SR node | Local RealESRGAN x4+ present | Partial only | Core GPL-3.0; model provenance should be rechecked before product use | `SplitImageWithAlpha` → RGB upscale + separately resampled mask → `JoinImageWithAlpha` preserves a channel, but is not premultiplied/alpha-aware SR and can create edge halos. Keep out of the scout; upscale only after alpha acceptance. |

Timesaver is technically attractive because one pack contains SAM point picking, ViTMatte, keying, and despill. It is not the smallest safe install: its own README describes 60 nodes, and its current [pyproject core dependencies](https://github.com/AlexYez/comfyui-timesaver/blob/master/pyproject.toml) include Qwen utilities and OpenAI Whisper. Its [requirements.txt](https://github.com/AlexYez/comfyui-timesaver/blob/master/requirements.txt) includes Qwen utilities and documents Whisper as a separate legacy fallback installation; `bitsandbytes`, `demucs`, `geomloss`, and `pykeops` are optional extras in `pyproject.toml`, not core dependencies. Reusing the repo's already-working ViTMatte environment avoids that broader node and dependency surface.

## Prior Comfy workflows and logs

- 89 core blueprint JSONs, including native BiRefNet and SAM3 image/video templates.
- 10 LayerDiffuse example workflows and 21 IPAdapter+ example workflows.
- 23 repo API runner graphs matching `tasks/workflow-rebuild/comfy/**/wf-*.json`; nine other JSON files there are result, gate, or baseline records rather than submit-ready graphs.
- 59 PNGs in `/Users/za/ComfyUI/output`, all with embedded API `prompt` graphs; the 16 unique node classes are generation/ControlNet/IPAdapter/inpainting primitives. None is a background-removal, matting, SAM3, keyer, or despill graph.
- No saved user workflow JSON was found under `/Users/za/ComfyUI/user`; its SQLite database contains asset tables, not workflow history.
- The repo's older `tasks/space-np01-front-bottom-02/.../workflow.json` and `tasks/berlin-hotel-base/.../comfy_workflow.json` are generation graphs, not removers.
- Generation rounds demonstrate real MPS use and useful operational lessons (query `/object_info`, inspect HTTP 400 bodies, avoid trusting stale failure logs), but they do not establish image14 background-removal quality.
- During this audit, the sibling `tasks/double-marine-bed-wrapper-batch/scouts/sam3/` lane completed one paid **text-prompted** SAM3 request. It returned one 55.29%-opaque hard mask and failed as a complete route because it filled enclosed paper, dropped bubbles/fish/tips, and had no matting. This does not validate local core inference; it specifically eliminates repeating text conditioning in the proposed local scout.

## Image14 evidence and recommendation

The native source is 941×1672, SHA-256 `925c34a39a0e2b5a09ad92ba39dace87f652bcc90ff8e063e2a6f644e735df9d`. Existing evidence says:

- automatic BRIA/BiRefNet/InSPyReNet/fusion/Photoshop-style proposals did not solve both pale-foreground retention and interior-paper deletion;
- the fixed ViTMatte-S scout succeeded technically on MPS in 2.974 seconds, kept 99.10% soft alpha, and preserved delicate structure, but retained ghost paper and fringe because its proposal marked wrong regions as sure foreground;
- sparse correction labels add five sure-foreground sand strokes but no sure-background strokes; they were created without reading the independent benchmark;
- the concurrent text-only SAM3 proposal also failed internal topology, so combining its text mask with point masks would be counterproductive: core `SAM3_Detect` unions text and point outputs, allowing the coarse text silhouette to refill holes excluded by negative points;
- therefore the missing primitive is a supervised topology producer, not another class-agnostic remover or another downstream blur/threshold pass.

**Recommendation:** conditionally authorize the one-pass `SAM3.1 point-only positive/negative mask → existing correction-led ViTMatte → independent frozen benchmark` scout in `SCOUT-PLAN.md`. It downloads one model, installs no node pack, writes no final, uses the product `Images/candidates/` location, and stops after one candidate whether it passes or fails. It is a narrow test of interactive topology—not a rerun of the failed text-only SAM3 request.

Remaining uncertainty is explicit: SAM 3.1 inference on this Mac has not been tested because the weight is absent; the model's custom license requires acceptance; a hard point-supervised mask may still miss pale bubbles, disconnected objects, or thin coral; machine PASS still requires native white/gray/black/magenta human review.

## Status

**STATUS: AUDIT COMPLETE; SCOUT SPECIFIED BUT NOT EXECUTED.**

**READY FOR JUDGING.**
