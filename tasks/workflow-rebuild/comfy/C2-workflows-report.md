# C2 ComfyUI Workflow Suite Report

## Built

Files touched:
- `scripts/comfy_build_workflow.py`
- `tests/test_comfy_build_workflow.py`
- `tasks/workflow-rebuild/comfy/C2-workflows-report.md`

The existing single-graph builder is now one coherent arm-based CLI:

```bash
python3 scripts/comfy_build_workflow.py --arm geometry --control-map guide.png --out geometry.json
python3 scripts/comfy_build_workflow.py --arm style --refs r1.png r2.png r3.png --out style.json
python3 scripts/comfy_build_workflow.py --arm combined --control-map line.png --refs r1.png --depth-map depth.png --out combined.json
python3 scripts/comfy_build_workflow.py --arm regional --control-map line.png --refs r1.png --mask door-portal-mask.png --out regional.json
```

Common controls:
- `--stage-inputs` copies local `--control-map`, `--refs`, `--depth-map`, and `--mask` files into `~/ComfyUI/input/`.
- `--print-graph` prints API-format JSON to stdout.
- `--width`, `--height`, `--control-strength`/`--cond`, `--depth-strength`, `--ip-weight`, `--ip-weight-type`, `--combine-embeds`, `--prefix`, model-name flags.
- `--out` writes API-format JSON ready for `scripts/comfy_run.py`; submit/poll behavior was not duplicated.

Arm coverage:
- `geometry`: SD1.5 + lineart `ControlNetApplyAdvanced`, no IPAdapter.
- `style`: SD1.5 + `IPAdapterAdvanced`, accepts 1-3 refs, no ControlNet.
- `combined`: lineart ControlNet + IPAdapter; optional depth ControlNet is chained as a second `ControlNetApplyAdvanced`.
- `regional`: combined lineart+IPAdapter graph plus `attn_mask` on `IPAdapterAdvanced`; optional depth is also supported.

## Resolution Strategy

Default generation size is `512x728`, preserving the 832x1184 door frame aspect ratio at SD1.5-native scale. This keeps the latent near the 512-pixel native regime and avoids adding latent upscale nodes before the C2 experiment proves the conditioning works. Upscale back to 832x1184 should happen externally after arm comparison.

## Confirmed Local Node Schema

Read from `~/ComfyUI/custom_nodes/ComfyUI_IPAdapter_plus/IPAdapterPlus.py`:
- `IPAdapterAdvanced`
- required inputs: `model`, `ipadapter`, `image`, `weight`, `weight_type`, `combine_embeds`, `start_at`, `end_at`, `embeds_scaling`
- optional inputs: `image_negative`, `attn_mask`, `clip_vision`
- output: `MODEL`
- `NODE_CLASS_MAPPINGS` registers `"IPAdapterAdvanced": IPAdapterAdvanced`

Read from `~/ComfyUI/custom_nodes/ComfyUI_IPAdapter_plus/NODES.md`:
- `attn_mask` is a MASK influence map; black zones are unaffected, white zones get maximum influence; mask should match latent size or aspect ratio.

Read from `~/ComfyUI/nodes.py`:
- `ControlNetApplyAdvanced` inputs: `positive`, `negative`, `control_net`, `image`, `strength`, `start_percent`, `end_percent`; outputs `positive`, `negative`.
- `LoadImage` returns `IMAGE`, `MASK`; regional arm wires mask as `["mask_load_node", 1]`.
- `ImageBatch` inputs are `image1`, `image2`; used to batch 2-3 style refs before IPAdapter.

W1 recipe defaults used:
- lineart ControlNet strength default `1.0`
- depth ControlNet strength default `1.0`
- IPAdapter weight default `0.8`
- IPAdapter `weight_type` default `linear`
- IPAdapter `combine_embeds` default `average`

`--ip-weight-type style transfer` remains available; W1 documents that the plugin's SD1.5 style-transfer routing touches layers `0-3,9-15`, but the suite default stays `linear` because that is the explicit W1 experiment recipe.

## Input References for Later Runs

Control maps / guides:
- `tasks/workflow-rebuild/round3/`
- `tasks/marriott-hospital/`
- `tasks/workflow-rebuild/refs/demo-layout/door-layout-geometry.png`

Style refs:
- `tasks/workflow-rebuild/round2/handle/*.png`
- `tasks/workflow-rebuild/refs/demo-handle/*.png`

Door portal mask:
- existing demo mask: `tasks/workflow-rebuild/refs/demo-layout/door-portal-mask.png`
- source derivation reference: `scripts/layout_ref.py` portal mask code (`_load_door_portal_mask`, `CACHED_PORTAL_MASK_PNG`)

## Verification Results

Per-arm builds:

```text
python3 scripts/comfy_build_workflow.py --arm geometry --control-map-name door-lineart.png --control-strength 1.0 --out /private/tmp/c2-workflows/geometry.json
wrote /private/tmp/c2-workflows/geometry.json  (10 nodes)

python3 scripts/comfy_build_workflow.py --arm style --ref-names style-a.png style-b.png style-c.png --ip-weight 0.8 --out /private/tmp/c2-workflows/style.json
wrote /private/tmp/c2-workflows/style.json  (15 nodes)

python3 scripts/comfy_build_workflow.py --arm combined --control-map-name door-lineart.png --depth-map-name door-depth.png --depth-strength 1.0 --ref-names style-a.png style-b.png --out /private/tmp/c2-workflows/combined.json
wrote /private/tmp/c2-workflows/combined.json  (19 nodes)

python3 scripts/comfy_build_workflow.py --arm regional --control-map-name door-lineart.png --ref-names style-a.png style-b.png --mask-name door-portal-mask.png --out /private/tmp/c2-workflows/regional.json
wrote /private/tmp/c2-workflows/regional.json  (17 nodes)
```

JSON round-trip:

```text
python3 -m json.tool /private/tmp/c2-workflows/geometry.json > /private/tmp/c2-workflows/geometry.pretty.json
python3 -m json.tool /private/tmp/c2-workflows/style.json > /private/tmp/c2-workflows/style.pretty.json
python3 -m json.tool /private/tmp/c2-workflows/combined.json > /private/tmp/c2-workflows/combined.pretty.json
python3 -m json.tool /private/tmp/c2-workflows/regional.json > /private/tmp/c2-workflows/regional.pretty.json
all exited 0
```

Node-link integrity:

```text
geometry: 10 nodes, 13 refs, link integrity PASS
style: 15 nodes, 17 refs, link integrity PASS
combined: 19 nodes, 23 refs, link integrity PASS
regional: 17 nodes, 20 refs, link integrity PASS
```

Syntax / print mode / pytest:

```text
PYTHONPYCACHEPREFIX=/private/tmp/c2-pycache python3 -m py_compile scripts/comfy_build_workflow.py tests/test_comfy_build_workflow.py
exit 0

PYTHONPYCACHEPREFIX=/private/tmp/c2-pycache python3 scripts/comfy_build_workflow.py --arm geometry --control-map-name door-lineart.png --print-graph > /private/tmp/c2-workflows/print-graph.json
python3 -m json.tool /private/tmp/c2-workflows/print-graph.json > /private/tmp/c2-workflows/print-graph.pretty.json
both exited 0

PYTHONPYCACHEPREFIX=/private/tmp/c2-pycache python3 -m pytest tests/test_comfy_build_workflow.py -q
....                                                                     [100%]
4 passed in 0.52s
```

Impact/security gates:
- `impact-of-change` ran in degraded lexical mode over the whole dirty worktree; for this task's file it flagged only local builder/test symbols, with targeted pytest as the relevant verification.
- `security-oversight` ran over the whole dirty worktree and reported unrelated existing MEDIUM/REVIEW items; it produced no finding for `scripts/comfy_build_workflow.py` or `tests/test_comfy_build_workflow.py`.

## Remaining Assumptions

- ComfyUI server was not running, so no workflow was POSTed or rendered.
- Referenced input images must exist under `~/ComfyUI/input/` before POST; use `--stage-inputs` with local source paths to copy them.
- Model filenames are defaults and may need adjustment to match the local ComfyUI model folders:
  - `v1-5-pruned-emaonly-fp16.safetensors`
  - `control_v11p_sd15_lineart_fp16.safetensors`
  - `control_v11f1p_sd15_depth_fp16.safetensors`
  - `ip-adapter_sd15.safetensors`
  - `CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors`
- The graph builder validates API JSON structure and internal node references only; it does not validate ComfyUI runtime model availability or plugin runtime compatibility.

READY FOR JUDGING
