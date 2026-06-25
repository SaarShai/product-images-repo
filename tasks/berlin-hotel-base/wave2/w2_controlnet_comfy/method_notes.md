# w2_controlnet_comfy method notes

## Scope and inputs read

- Read `tasks/berlin-hotel-base/HANDOFF.md`.
- Read `tasks/berlin-hotel-base/BRIEF.md`.
- Read `tasks/berlin-hotel-base/wave2/PLAN.md`.
- Read `docs/image-generation.md`.
- Source used read-only: `tasks/berlin-hotel-base/work/src.png`.
- Final composite edit box: `3162,2582,4082,2845` per wave-2 plan.

## Control map

- Built a hand-designed lineart control map rather than reusing wave-1's extracted/tiled guide.
- File: `control_lineart_strong.png`.
- Structure forced into the map:
  - regular vertical limestone pier rhythm;
  - three stacked rows of tall narrow window groups;
  - compressed right/receding side with tighter bays;
  - low plain plinth at the bottom;
  - no canopy, marquee, porte-cochere, glass hall, or sign geometry.
- Companion files:
  - `control_lineart_inverted_preview.png` for lineart polarity testing;
  - `structure_color_guide.png` for palette/texture harmonization;
  - `mask_allowed_box_fullres.png` for the shared full-res edit box;
  - `source_allowed_box.png` and `source_zoom.png` for comparison.

## Comfy attempt

- Built `comfy_workflow.json` with `scripts/comfy_build_workflow.py`.
- Workflow settings:
  - control map: `control_lineart_strong.png`;
  - refs: `structure_color_guide.png`, `ref_building_artwork_guide.png`, `ref_tower_facade_above.png`, `ref_ritz_cahill2.jpg`;
  - size: `920x264`;
  - ControlNet strength: `1.25`;
  - IPAdapter weight: `0.55`;
  - steps: `30`;
  - seed: `220602`.
- Execution blocker:
  - Command: `python3 scripts/comfy_run.py --workflow tasks/berlin-hotel-base/wave2/w2_controlnet_comfy/comfy_workflow.json --out tasks/berlin-hotel-base/wave2/w2_controlnet_comfy/raw_comfy_attempt.png --server 127.0.0.1:8188 --timeout 10`
  - Result: `urllib.error.URLError: <urlopen error [Errno 61] Connection refused>`.
  - Interpretation: no ComfyUI server was listening on `127.0.0.1:8188`.

## Local ControlNet attempts

### Attempt A: SD1.5 lineart, white-on-black control

- Raw file: `raw_sd15_lineart_s220602.png`.
- Command:

```bash
python3 scripts/controlnet_gen.py --control-map tasks/berlin-hotel-base/wave2/w2_controlnet_comfy/control_lineart_strong.png --prompt "$(cat tasks/berlin-hotel-base/wave2/w2_controlnet_comfy/prompt.txt)" --negative-prompt "$(cat tasks/berlin-hotel-base/wave2/w2_controlnet_comfy/negative.txt)" --controlnet lllyasviel/control_v11p_sd15_lineart --base-model stable-diffusion-v1-5/stable-diffusion-v1-5 --steps 28 --cond-scale 1.25 --guidance 6.5 --width 920 --height 264 --seed 220602 --dtype float32 --out tasks/berlin-hotel-base/wave2/w2_controlnet_comfy/raw_sd15_lineart_s220602.png
```

- Raw visual verdict: strong structural lock, but the model read the control polarity as dark blue facade panels with pale window voids.
- Composite file: `candidate_sd15_lineart_s220602_composited.png`.
- Zoom: `candidate_sd15_lineart_s220602_zoom.png`.
- Composite visual verdict: best lane candidate. It reads as limestone bays and avoids canopy/glass-hall/text, but is still too gridded and visibly generated compared with the source watercolor.

### Attempt B: SD1.5 lineart, inverted control

- Raw file: `raw_sd15_lineart_inverted_s220603.png`.
- Command:

```bash
python3 scripts/controlnet_gen.py --control-map tasks/berlin-hotel-base/wave2/w2_controlnet_comfy/control_lineart_inverted_preview.png --prompt "$(cat tasks/berlin-hotel-base/wave2/w2_controlnet_comfy/prompt.txt)" --negative-prompt "$(cat tasks/berlin-hotel-base/wave2/w2_controlnet_comfy/negative.txt)" --controlnet lllyasviel/control_v11p_sd15_lineart --base-model stable-diffusion-v1-5/stable-diffusion-v1-5 --steps 28 --cond-scale 1.10 --guidance 6.5 --width 920 --height 264 --seed 220603 --dtype float32 --out tasks/berlin-hotel-base/wave2/w2_controlnet_comfy/raw_sd15_lineart_inverted_s220603.png
```

- Raw visual verdict: still blue/line-heavy, with a glyph-like mark on the far-right facade.
- Composite file: `candidate_sd15_lineart_inverted_s220603_composited.png`.
- Zoom: `candidate_sd15_lineart_inverted_s220603_zoom.png`.
- Composite visual verdict: mechanically valid, but visually weaker than Attempt A because the far-right mark reads like accidental signage.

## Compositing method

- Script: `build_lane_assets.py`.
- Raw ControlNet output was resized into the allowed edit box and harmonized against `structure_color_guide.png` plus the source crop.
- Feathering is applied only inside the allowed box, so outside pixels remain byte-identical.
- Full source outside the edit box was not changed.

## Verifier output

```text
PASS candidate=tasks/berlin-hotel-base/wave2/w2_controlnet_comfy/candidate_sd15_lineart_s220602_composited.png box=3162,2582,4082,2845 outside_max=0 outside_nonzero=0 inside_nonzero=720885
PASS candidate=tasks/berlin-hotel-base/wave2/w2_controlnet_comfy/candidate_sd15_lineart_inverted_s220603_composited.png box=3162,2582,4082,2845 outside_max=0 outside_nonzero=0 inside_nonzero=719600
```

## Assumptions

- Used the wave-2 edit box `3162,2582,4082,2845`, not the earlier wave-1 shorter box.
- Treated Comfy as unavailable because the local API refused the connection.
- Used cached local SD1.5 lineart ControlNet because `torch`, MPS, diffusers, and the model cache were available.
- Copied reference images into this lane directory only so the Comfy workflow packet is portable.
- Did not write to the Google Drive source.
- Did not edit other method lanes or wave-1 artifacts.

## Recommended judging pick

Judge `candidate_sd15_lineart_s220602_composited.png` first. It is the cleaner of the two ControlNet composites and passes the pixel gate, but it should be considered a method-spread candidate rather than a production finalist because the lower facade is still too regular and rectangular.

## File index

- `control_lineart_strong.png`
- `control_lineart_inverted_preview.png`
- `structure_color_guide.png`
- `mask_allowed_box_fullres.png`
- `source_allowed_box.png`
- `source_zoom.png`
- `comfy_workflow.json`
- `raw_sd15_lineart_s220602.png`
- `raw_sd15_lineart_inverted_s220603.png`
- `candidate_sd15_lineart_s220602_composited.png`
- `candidate_sd15_lineart_s220602_zoom.png`
- `candidate_sd15_lineart_s220602_patch.png`
- `candidate_sd15_lineart_s220602_diff_inside_box.png`
- `candidate_sd15_lineart_inverted_s220603_composited.png`
- `candidate_sd15_lineart_inverted_s220603_zoom.png`
- `candidate_sd15_lineart_inverted_s220603_patch.png`
- `candidate_sd15_lineart_inverted_s220603_diff_inside_box.png`
- `contact_sheet.png`
- `prompt.txt`
- `negative.txt`
- `asset_manifest.json`
- `build_lane_assets.py`
