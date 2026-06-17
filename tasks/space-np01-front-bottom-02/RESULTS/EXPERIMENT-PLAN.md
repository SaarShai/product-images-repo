# EXPERIMENT PLAN — gorgeous watercolor style AT exact SVG geometry

**Task:** `space-np01-front-bottom-02`. Panel SVG `source/template.svg`, viewBox **767.2328 x 2602.2896** (aspect **1 : 3.393**). 4 openings: 3 six-sided (two axis-aligned hex, one rotated hex) stacked upper-middle + 1 long rounded vertical slot lower half. Top edge has a small V-notch.

**Goal:** >=2 RELIABLE methods that produce a gorgeous, model-painted watercolor illustration whose openings land at the exact SVG coordinates, with model-painted bevelled rims (NOT a flat code-punched white hole).

**GATE (primary):** region-IoU >= 0.85 (`scripts/geom_iou.py`, fill-agnostic placement).
**Secondary gates (from codex consult — adopt):**
- `aperture_painted_frac <= 0.03` per opening (the cut-through center must read empty/pale; measured by `scripts/svg_geometry_check.py` `holes[].painted_frac`).
- bevel present (visual) — rim band must show painted shadow/lip. White-IoU is **NOT** a rim gate; a painted bevel legitimately lowers white-IoU. Do not auto-reject on white-IoU.
- `outside_frac` small (silhouette respected).

**Anti-confounds baked in (the prime lessons):**
1. **Aspect.** Every subscription run uses TRUE 1:3.393 panel proportions. The model is told to draw the panel **centered with white margins (letterboxed), NOT filling the frame**; `auto_bbox` in `geom_adherence_test.py` / `geom_iou.py` recovers the panel region. The old filled base (`np01-fb-02-genmap-filled.png`, 1024x1536 = 2:3) is itself squished — we build a **true-aspect filled base** first (Step 0).
2. **Never chain edits.** Every subscription call restarts from the SAME canonical base PNG, never from a previous generation.
3. **Filled base, not hollow lineart.** Openings shown as solid mid-grey discs in the base. Hollow outlines invite the model to relayout/fill.
4. **Refs ordered:** geometry base = image 1; style refs = images 2..N (max 2 for codex, max 2 here for nano so base+2 <= 3). Explicitly labelled "style only, ignore their layout".
5. **Score after de-letterbox.** `auto_bbox` finds the panel; `geom_iou.py` maps the SVG into that bbox. Always score the recovered panel, not the raw frame.

---

## Step 0 — One-time setup (build true-aspect canonical base + helper) — RUN BEFORE ANYTHING

The existing filled base is 2:3 (squished). Build a **true 1:3.393** filled base on a letterboxed canvas the subscription models can reproduce, plus a verifier wrapper that runs BOTH metrics.

### 0a. Build the true-aspect filled base (openings = solid mid-grey discs)
```bash
cd "/Users/za/Documents/product images repo"
python3 - <<'PY'
# Render template.svg silhouette + openings as a FILLED base at true aspect,
# centered with white margins on a 9:16 canvas (panel fills full height).
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw
import sys
sys.path.insert(0, "scripts")
import svg_classify as C
svg = Path("tasks/space-np01-front-bottom-02/source/template.svg")
shapes = C.classify(C.extract_shapes(svg))          # outer contour + internal cutouts
# panel target: full height of a 9:16 canvas at 1440x2560 -> panel height 2560, width 2560/3.393=754
CW, CH = 1440, 2560
ph = CH; pw = round(ph / 3.393)                      # 754
ox = (CW - pw)//2; oy = 0
vbW, vbH = 767.2328, 2602.2896
def to_px(x,y): return (ox + x/vbW*pw, oy + y/vbH*ph)
canvas = Image.new("RGB", (CW, CH), "white"); d = ImageDraw.Draw(canvas)
outer = [s for s in shapes if s["role"]=="outer_contour"][0]
d.polygon([to_px(*p) for p in outer["points"]], fill=(232,228,220))  # panel body = warm pale
for s in shapes:
    if s["role"]=="internal_cutout":
        d.polygon([to_px(*p) for p in s["points"]], fill=(128,128,128))  # mid-grey disc
out = Path("tasks/space-np01-front-bottom-02/outputs/generated/np01-fb-02-base-trueaspect-1440x2560.png")
canvas.save(out); print("wrote", out, canvas.size)
PY
```
> If `svg_classify.classify`/`extract_shapes` signatures differ, inspect `scripts/svg_classify.py` and adapt the two call sites; the geometry math (true 1:3.393, centered) is the load-bearing part.

### 0b. Verifier wrapper — runs region-IoU (GATE) + white/painted (secondary) on a finished image
`geom_adherence_test.py` records ONLY `svg_geometry_check.py` (white-IoU/painted_frac/outside). It does NOT compute region-IoU. So after EVERY subscription gen, also run `geom_iou.py` explicitly:
```bash
# $RAW = the produced PNG; $BBOX = auto or L,T,R,B
python3 scripts/geom_iou.py "$RAW" --svg tasks/space-np01-front-bottom-02/source/template.svg \
    --json-out "$EXPDIR/region_iou.json" --out-overlay "$EXPDIR/region_overlay.png"
# region-IoU = mean over openings in region_iou.json; GATE >= 0.85
```

### 0c. Patch the agy aspect (the 9:16-hardcode is the confound)
`scripts/geom_adherence_test.py:82` hardcodes `AspectRatio='9:16'` AND tells the model to "not squash it". With a true-aspect letterboxed base that is now CORRECT (panel fills full height of the 9:16 frame, white side margins). **Do not change the enum** — 9:16 is the tallest agy enum and matches our 1440x2560 letterbox canvas. The fix is the BASE image (Step 0a) + the prompt phrasing (E2 below), not the enum. Confirm the base passed as image-1 is the trueaspect letterbox.

---

## EXPERIMENT FAMILIES

All experiments append one JSONL record per candidate to `tasks/space-np01-front-bottom-02/RESULTS/results.jsonl` and a CALLOUT/row to `RESULTS-BOARD.md`, with full labels: `id, method, model, platform, reference_images, svg, prompt, control_map, region_iou, white_iou, outside_frac, image_path_raw, image_path_exact, timestamp, notes`.

---

### FAMILY 1 — gpt-image best-of-N, ASPECT-FIXED (codex lane)  [id prefix: BoN2-openai-sN]

**Hypothesis:** The 0.184 ceiling was an aspect artefact. With a true-aspect letterboxed filled base + a letterbox-explicit prompt, region-IoU rises materially (target: median > 0.45, best-of-8 > 0.6; success = any sample >= 0.85, but treat N as reliability multiplier not guarantee).

**Base (image 1):** `np01-fb-02-base-trueaspect-1440x2560.png` (Step 0a).
**Style refs (images 2,3):** the two watercolor refs in `refs/`.
**Prompt** (`prompts/BoN2-openai-letterbox.md`):
```
Produce ONE finished tall, narrow watercolor space control-panel illustration.

CANVAS & FRAMING (critical): the panel is a TALL, NARROW vertical strip — its height is about 3.4x its width. Image 1 shows the EXACT layout contract: the panel sits CENTERED on the canvas with empty WHITE MARGINS on the left and right. Reproduce that framing EXACTLY: do NOT enlarge the panel to fill the frame, do NOT crop the margins, do NOT change the panel's tall-narrow proportions. The white side margins must remain white and empty.

LAYOUT CONTRACT (image 1) — treat as law, not suggestion. Keep every element at the IDENTICAL relative position, size, and shape:
- the outer silhouette and its edges, including the small V-notch in the top edge,
- the THREE six-sided openings stacked in the upper-middle (the middle one is rotated),
- the ONE long rounded vertical opening in the lower half.

CHANGE (surface rendering only): paint the panel body in rich cobalt-and-indigo watercolor with granulated paper texture and soft pigment blooms, hand-painted uneven dark-blue ink outlines, soft top-left lighting, a darker navy rim band around the outer edge with a thin pale edge-highlight, and a few small screws near the corners. Add a few raised rounded control hardware pieces (capsule buttons, small knobs, toggle pins, indicator dots) ONLY in the open body areas, clear of every opening and the outer edge.

OPENINGS — painted recessed ports with bevelled rims (NOT flat holes): around EACH opening paint an illustrated bevelled rim — a soft dark-navy inner shadow hugging the upper-left edge and a pale lit lip on the lower-right edge, with watercolor pigment pooling along the rim. Leave the recessed CENTER of each opening empty and pale (paper-white aperture center) — an actual cut-through port.

DO NOT: move, resize, rotate, reshape, merge, add, remove, fill, close, or round any opening; add new openings; add text, labels, arrows, grid lines, or watermark. One single finished panel, white background, one version only.

Use the other attached images ONLY as watercolor style references (palette, brushwork, bevel/rim treatment) — ignore their layout entirely.
```
**Command (N=8 samples):**
```bash
cd "/Users/za/Documents/product images repo"
BASE=tasks/space-np01-front-bottom-02/outputs/generated/np01-fb-02-base-trueaspect-1440x2560.png
R1="tasks/space-np01-front-bottom-02/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png"
R2="tasks/space-np01-front-bottom-02/refs/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png"
for i in $(seq 1 8); do
  python3 scripts/geom_adherence_test.py --id "BoN2-openai-s$i" --model openai \
    --map "$BASE" --prompt tasks/space-np01-front-bottom-02/prompts/BoN2-openai-letterbox.md \
    --refs "$R1" "$R2" --svg tasks/space-np01-front-bottom-02/source/template.svg \
    --outdir tasks/space-np01-front-bottom-02/experiments --timeout 360
  EXP=tasks/space-np01-front-bottom-02/experiments/BoN2-openai-s$i
  python3 scripts/geom_iou.py "$EXP/raw.png" --svg tasks/space-np01-front-bottom-02/source/template.svg \
    --json-out "$EXP/region_iou.json" --out-overlay "$EXP/region_overlay.png"
done
```
**Expected:** best-of-8 region-IoU 0.55-0.75 (vs prior 0.184). Falsifies "subscription is fundamentally broken at geometry" if it clears 0.85 on any sample; if it plateaus ~0.45 it confirms BoN is a candidate generator, not a primary geometry mechanism.

---

### FAMILY 2 — Nano Banana best-of-N, ASPECT-FIXED (agy lane)  [id prefix: BoN2-nano-sN]

**Hypothesis:** Nano produced the richest style (BoN-nano-s3 visually best) but worst drift, entirely because the 9:16 enum was applied to a 2:3 squished base. With the true-aspect letterbox base + 9:16 enum now CONGRUENT (panel fills full height, white margins), Nano's relative layout should jump from 0.578 toward gate.

**agy specifics:** AspectRatio is an ENUM (tallest = 9:16); NO size knob; writes JPEG. Max 3 input images -> base + exactly 2 style refs. `geom_adherence_test.py --model nanobanana` already wires the 9:16 enum and the brain-dir JPEG recovery; we keep it and feed the true-aspect base.
**Prompt** (`prompts/BoN2-nano-letterbox.md`): same body as FAMILY 1, but prepend an agy-operator note already injected by `gen_agy`; add this line to the prompt file so framing is unambiguous with 9:16:
```
The 9:16 frame is INTENTIONALLY wider than the panel: render the panel as a tall narrow strip centered with WHITE side margins (as in image 1). Do not stretch the panel to fill the 9:16 width.
```
(append the full FAMILY-1 prompt body after that line.)
**Command (N=8):**
```bash
cd "/Users/za/Documents/product images repo"
BASE=tasks/space-np01-front-bottom-02/outputs/generated/np01-fb-02-base-trueaspect-1440x2560.png
R1="tasks/space-np01-front-bottom-02/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png"
R2="tasks/space-np01-front-bottom-02/refs/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png"
for i in $(seq 1 8); do
  python3 scripts/geom_adherence_test.py --id "BoN2-nano-s$i" --model nanobanana \
    --map "$BASE" --prompt tasks/space-np01-front-bottom-02/prompts/BoN2-nano-letterbox.md \
    --refs "$R1" "$R2" --svg tasks/space-np01-front-bottom-02/source/template.svg \
    --outdir tasks/space-np01-front-bottom-02/experiments --timeout 360
  EXP=tasks/space-np01-front-bottom-02/experiments/BoN2-nano-s$i
  python3 scripts/geom_iou.py "$EXP/raw.png" --svg tasks/space-np01-front-bottom-02/source/template.svg \
    --json-out "$EXP/region_iou.json" --out-overlay "$EXP/region_overlay.png"
done
```
**Expected:** best-of-8 region-IoU 0.6-0.8 (vs prior 0.578), richest style of all lanes. If best sample >= 0.85 with good bevels, this is a 2nd reliable method (style-leading).

---

### FAMILY 3 — fixing-prompt: nudge a well-styled-but-inexact result to exact (codex AND nano)  [id prefix: FIX-{openai,nano}-vN]

**Distinct from restyle:** input here is a FINISHED, gorgeous-but-drifted styled image (the best style sample from FAMILY 1/2, e.g. the new BoN2-nano best, or the historical `BoN-nano-s3` art). We feed it back with a CORRECTION prompt that moves openings to exact position WITHOUT losing the style. Input image 1 = the styled drift; image 2 = the true-aspect filled base as the coordinate target. **Never chain past one hop** (correct from the canonical pair, re-score; do not feed the corrected output back in again).

**4 distinct correction-prompt variants to A/B** (`prompts/FIX-v{1..4}.md`):

- **FIX-v1 (overlay-align):**
```
Image 1 is a finished watercolor panel with the right STYLE but slightly WRONG opening positions. Image 2 is the exact geometry target. Redraw image 1 so that every opening (3 six-sided openings upper-middle + 1 long vertical rounded slot lower half) moves to the EXACT position, size, and shape shown in image 2, while preserving image 1's watercolor style, palette, brushwork, panel body, hardware, and bevelled rims pixel-for-pixel everywhere else. Keep the tall-narrow proportions and white side margins of image 2. Do not restyle; only relocate/resize the openings to match image 2. Keep each opening center empty and pale; keep the painted bevel rims.
```
- **FIX-v2 (delta-language, per-opening):**
```
Image 1 has the correct art but its openings are off. Using image 2 as the coordinate contract, nudge each opening into place: the three six-sided openings belong stacked in the upper-middle third (middle one rotated); the long rounded vertical slot belongs centered in the lower half. Snap them to image 2's exact outlines. Change nothing else — same colors, same watercolor texture, same bevelled rims (dark navy upper-left inner shadow, pale lower-right lip), same hardware. Empty pale center inside each opening.
```
- **FIX-v3 (grid-anchored):**
```
Image 2 is the exact layout. Image 1 is the finished style. Output image 1's exact watercolor look but with openings repositioned to image 2's outlines precisely. Treat image 2 like tracing paper laid over image 1: where image 2 shows an opening, that is the only valid location/size/shape. Preserve all surrounding watercolor rendering and the painted bevelled rims unchanged. Tall narrow panel, white margins, single version.
```
- **FIX-v4 (minimal-edit, strong negative):**
```
Edit image 1 minimally. The ONLY change: relocate and reshape its openings to exactly match image 2's openings (3 hex-like upper-middle, 1 long vertical slot lower half), keeping each center empty/pale with a painted bevelled rim. Do NOT repaint the body, do NOT change colors/texture/hardware, do NOT move the silhouette, do NOT add or remove openings, no text, one panel, white background, true tall-narrow 1:3.4 proportions with white side margins.
```
**Commands (run for codex + nano; STYLED = chosen best-style drift image):**
```bash
cd "/Users/za/Documents/product images repo"
STYLED=tasks/space-np01-front-bottom-02/experiments/BoN2-nano-sBEST/raw.png   # set to actual best-style sample
BASE=tasks/space-np01-front-bottom-02/outputs/generated/np01-fb-02-base-trueaspect-1440x2560.png
SVG=tasks/space-np01-front-bottom-02/source/template.svg
for v in 1 2 3 4; do
  for M in openai nanobanana; do
    ID="FIX-$M-v$v"
    python3 scripts/geom_adherence_test.py --id "$ID" --model $M \
      --map "$STYLED" --prompt tasks/space-np01-front-bottom-02/prompts/FIX-v$v.md \
      --refs "$BASE" --svg "$SVG" \
      --outdir tasks/space-np01-front-bottom-02/experiments --timeout 360
    EXP=tasks/space-np01-front-bottom-02/experiments/$ID
    python3 scripts/geom_iou.py "$EXP/raw.png" --svg "$SVG" \
      --json-out "$EXP/region_iou.json" --out-overlay "$EXP/region_overlay.png"
  done
done
```
> NOTE: `geom_adherence_test.py` passes `--map` as image 1 and `--refs` as images 2..N — so STYLED=image1, BASE=image2, matching the prompt wording. For the nano lane, `gen_agy` labels image-1 the "base/contract"; since here image-1 is the styled drift, edit `prompts/FIX-v*.md` to say "image 1 = style to keep" explicitly (already done above) so the operator note doesn't mislead.
**Expected:** correction lifts a 0.55-style sample to >0.75; best variant identified. If a variant hits >=0.85 keeping style, that is a reliable 2-step subscription method (BoN -> fix).

---

### FAMILY 4 — restyle-in-place on a geometry-EXACT base (codex AND nano)  [id prefix: RIP-{openai,nano}-vN]

**Input image 1 = a geometry-EXACT base** (`experiments/CN-style-exact/raw.png` or `experiments/DREAM1/exact.png`, both 480x1624, true 1:3.38). **Image 2 = gorgeous watercolor style ref.** Instruct repaint-in-place: move/resize/add/remove NOTHING; only enrich surface + bevels. This is the highest-prior-confidence subscription route because geometry starts perfect; risk = the model relayouts during restyle.

**2 prompt variants** (`prompts/RIP-v{1,2}.md`):
- **RIP-v1 (lock-everything restyle):**
```
Image 1 is the EXACT geometry — every edge, the outer silhouette, the top V-notch, the three six-sided openings upper-middle, and the long vertical rounded slot lower half are already in their final correct positions. Repaint image 1 IN PLACE into a gorgeous cobalt-and-indigo watercolor space control panel: granulated washes, soft pigment blooms, hand-painted ink outlines, soft top-left light. Around each EXISTING opening paint a bevelled rim (dark-navy upper-left inner shadow, pale lower-right lip) and keep the center empty/pale. Add small watercolor hardware (knobs, capsule buttons, indicator dots) ONLY in open body areas. CRITICAL: do not move, resize, reshape, add, or remove ANY opening or edge — keep all geometry pixel-identical to image 1. Match the watercolor style of image 2. One panel, white background, tall-narrow proportions preserved.
```
- **RIP-v2 (style-transfer framing):**
```
Apply the watercolor painting style of image 2 onto the exact structure of image 1. Image 1's layout is FINAL and must not change at all — same silhouette, same opening positions/sizes/shapes. Only the rendering changes: rich blue watercolor body, granulated paper texture, painted bevelled rims around each opening (upper-left dark inner shadow, lower-right pale lip, empty pale centers), soft hardware in open areas only. No new openings, no moved openings, no text, single version, white background.
```
**Command:**
```bash
cd "/Users/za/Documents/product images repo"
EXACT=tasks/space-np01-front-bottom-02/experiments/DREAM1/exact.png   # or CN-style-exact/raw.png
STYLEREF="tasks/space-np01-front-bottom-02/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png"
SVG=tasks/space-np01-front-bottom-02/source/template.svg
for v in 1 2; do
  for M in openai nanobanana; do
    ID="RIP-$M-v$v"
    python3 scripts/geom_adherence_test.py --id "$ID" --model $M \
      --map "$EXACT" --prompt tasks/space-np01-front-bottom-02/prompts/RIP-v$v.md \
      --refs "$STYLEREF" --svg "$SVG" \
      --outdir tasks/space-np01-front-bottom-02/experiments --timeout 360
    EXP=tasks/space-np01-front-bottom-02/experiments/$ID
    python3 scripts/geom_iou.py "$EXP/raw.png" --svg "$SVG" \
      --json-out "$EXP/region_iou.json" --out-overlay "$EXP/region_overlay.png"
  done
done
```
**Expected:** because geometry starts exact, region-IoU should be the HIGHEST of all subscription lanes (>0.8 plausible if the model resists relayout). The failure mode to watch: model "helpfully" re-spaces openings. If region-IoU stays >=0.85 with rich style, this is a primary reliable method.

---

### FAMILY 5 — local-diffusers style lift (the reliability anchor)  [ids: DREAM-ip, DREAM-tune-*, SDXL-*]

dreamshaper-8 + lineart ControlNet already hits region-IoU 0.969 (DREAM1) but style is a flat-ish wash. Three sub-experiments to lift style WITHOUT losing the locked geometry. This lane is the dependable >=1 method; we want a 2nd from here too.

**5a. DREAM-ip — dreamshaper-8 + lineart CN + IP-Adapter (style refs)** [most direct style lever]
```bash
cd "/Users/za/Documents/product images repo"
python3 scripts/controlnet_style_gen.py \
  --control-map tasks/space-np01-front-bottom-02/outputs/generated/cn-lineart-480.png \
  --svg tasks/space-np01-front-bottom-02/source/template.svg \
  --outdir tasks/space-np01-front-bottom-02/experiments/DREAM-ip \
  --base-model Lykon/dreamshaper-8 \
  --style-refs "tasks/space-np01-front-bottom-02/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png" \
               "tasks/space-np01-front-bottom-02/refs/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png" \
  --ip-scale 0.45 --cond-scale 1.25 --guidance 6.5 --steps 32 \
  --prompt "gorgeous hand-painted watercolor space control panel, granulated cobalt and indigo washes, soft pigment blooms, inked hand-painted edges, recessed openings with painted bevelled rims, dark blue inner shadow on upper-left rim, pale lower-right lip highlight, white paper background" \
  --negative-prompt "flat wash, flat vector, plastic, photorealistic, 3d render, text, watermark, extra openings, missing openings, filled openings, distorted openings, hard digital stroke"
# then score BOTH metrics on raw.png AND exact.png
for IMG in raw exact; do
  python3 scripts/geom_iou.py tasks/space-np01-front-bottom-02/experiments/DREAM-ip/$IMG.png \
    --svg tasks/space-np01-front-bottom-02/source/template.svg \
    --json-out tasks/space-np01-front-bottom-02/experiments/DREAM-ip/region_iou_$IMG.json
  python3 scripts/svg_geometry_check.py tasks/space-np01-front-bottom-02/experiments/DREAM-ip/$IMG.png \
    --svg tasks/space-np01-front-bottom-02/source/template.svg \
    --report tasks/space-np01-front-bottom-02/experiments/DREAM-ip/metrics_$IMG.json
done
```
**Sweep if IP fails on MPS:** rerun with `--no-ip` (style from checkpoint+prompt). Sweep `--ip-scale {0.35,0.5,0.65}`, `--cond-scale {1.15,1.4}`, `--guidance {5.5,7.0}`.
**Expected:** raw.png region-IoU 0.90-0.97 retained (cond-scale 1.25 keeps geometry) with visibly richer watercolor than DREAM1. This is the leading candidate for reliable method #1.

**5b. SDXL+ControlNet relaunch (download was crashing — scout small first)** [richer prior]
```bash
cd "/Users/za/Documents/product images repo"
# Scout size first (codex consult: start 512x1736, not 768x2608, on MPS). Make a 512-wide lineart if needed.
python3 scripts/controlnet_sdxl_gen.py \
  --control-map tasks/space-np01-front-bottom-02/outputs/generated/np01-fb-02-controlmap-lineart-512.png \
  --out tasks/space-np01-front-bottom-02/experiments/SDXL-scout/raw.png \
  --controlnet xinsir/controlnet-canny-sdxl-1.0 --invert \
  --cond-scale 0.9 --guidance 6.5 --steps 28 --seed 7
python3 scripts/geom_iou.py tasks/space-np01-front-bottom-02/experiments/SDXL-scout/raw.png \
  --svg tasks/space-np01-front-bottom-02/source/template.svg \
  --json-out tasks/space-np01-front-bottom-02/experiments/SDXL-scout/region_iou.json
```
> If the SDXL download crashes again, pre-pull with `huggingface-cli download stabilityai/stable-diffusion-xl-base-1.0` and `huggingface-cli download xinsir/controlnet-canny-sdxl-1.0` with retries, monitor disk (~99GB free is enough; SDXL+CN ~13GB). cond-scale 0.7-1.1 (LOWER than SD1.5 to avoid over-rigidity). Only scale to full 768x2608 after 512 is stable.
**Expected:** if it runs, SDXL gives the richest local style; region-IoU 0.88-0.95 at cond 0.9. Second reliable local method if download cooperates.

**5c. DREAM-inpaint — aperture/rim mask split (model-painted bevel, exact aperture by construction)**
Use `StableDiffusionControlNetInpaintPipeline` (control_v11p_sd15_inpaint or lineart): lock `aperture_mask` (exact SVG cutout, kept), generate body + `rim_annulus_mask` (dilate aperture 6-22px minus aperture). This GUARANTEES exact aperture geometry while the model paints the bevel band.
```bash
# If no inpaint script exists yet, this is the one new script to add:
#   scripts/controlnet_inpaint_gen.py  (already stubbed in repo root per git status: scripts/controlnet_inpaint_gen.py)
python3 scripts/controlnet_inpaint_gen.py \
  --control-map tasks/space-np01-front-bottom-02/outputs/generated/cn-lineart-480.png \
  --svg tasks/space-np01-front-bottom-02/source/template.svg \
  --base-model Lykon/dreamshaper-8 \
  --rim-dilate 14 --aperture-keep \
  --out tasks/space-np01-front-bottom-02/experiments/DREAM-inpaint/raw.png \
  --cond-scale 1.4 --guidance 6.5 --steps 34 \
  --prompt "recessed cutout openings with painted bevelled rims, dark navy inner shadow hugging upper-left edge, soft pale paper lip on lower-right, watercolor pigment pooling around rims, clean empty pale aperture centers, cobalt watercolor control panel" \
  --negative-prompt "flat hole, punched, digital stroke, text, filled opening, moved opening"
python3 scripts/geom_iou.py tasks/space-np01-front-bottom-02/experiments/DREAM-inpaint/raw.png \
  --svg tasks/space-np01-front-bottom-02/source/template.svg \
  --json-out tasks/space-np01-front-bottom-02/experiments/DREAM-inpaint/region_iou.json
```
> `scripts/controlnet_inpaint_gen.py` exists in repo root (untracked). Confirm its args; if absent/incompatible, this sub-experiment is the one place a small script is written, reusing `svg_classify` for aperture polygons + PIL dilate for the annulus.
**Expected:** region-IoU >= 0.93 (aperture exact by construction) with `aperture_painted_frac <= 0.03` AND a real painted bevel — directly satisfies the user's "illustrated bevel, not flat punch".

---

## BACKSTOP (always available, guarantees a deliverable)
If after N=8 rounds no subscription lane clears the gate, take the best-STYLE drifted art and re-seat openings with the existing exact-bevel compositor (region-IoU 1.0 by construction, painted bevel):
```bash
python3 scripts/exact_bevel_composite.py \
  --art <best-style-art.png> --svg tasks/space-np01-front-bottom-02/source/template.svg \
  --out tasks/space-np01-front-bottom-02/experiments/HYB2/exact.png \
  --debug-overlay tasks/space-np01-front-bottom-02/experiments/HYB2/overlay.png
```
This is HYB1's method (already PASS by construction); use only as fallback since it smears art near openings.

---

## RECORDING (every candidate)
After scoring, append to `RESULTS/results.jsonl` and update `RESULTS-BOARD.md`. Minimal append helper:
```bash
python3 - "$ID" "$METHOD" "$MODEL" "$PLATFORM" "$REGION_IOU" "$WHITE_IOU" "$OUTSIDE" "$RAW" "$NOTES" <<'PY'
import json,sys,datetime
id_,method,model,plat,riou,wiou,out,raw,notes=sys.argv[1:10]
rec={"id":id_,"method":method,"model":model,"platform":plat,
 "reference_images":["tasks/space-np01-front-bottom-02/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png",
                     "tasks/space-np01-front-bottom-02/refs/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png"],
 "svg":"tasks/space-np01-front-bottom-02/source/template.svg",
 "prompt":"<prompt path>","control_map":"<base/map path>",
 "region_iou":float(riou) if riou not in("unknown","n/a") else riou,
 "white_iou":float(wiou) if wiou not in("unknown","n/a") else wiou,
 "outside_frac":float(out) if out not in("unknown","n/a") else out,
 "image_path_raw":raw,"image_path_exact":"unknown",
 "timestamp":datetime.datetime.now().isoformat(timespec="seconds"),"notes":notes}
open("tasks/space-np01-front-bottom-02/RESULTS/results.jsonl","a").write(json.dumps(rec)+"\n")
print("recorded",id_)
PY
```

---

## DECISION RULE (>=2 reliable methods)
A method is "reliable" if it clears region-IoU >= 0.85 with `aperture_painted_frac <= 0.03` and a visible painted bevel on **>=2 independent seeds/samples**.
- **Expected reliable #1:** FAMILY 5a (DREAM-ip) or 5c (DREAM-inpaint) — local, deterministic, geometry already proven.
- **Expected reliable #2:** FAMILY 4 (RIP restyle-in-place) if the model resists relayout, OR FAMILY 5b (SDXL) if download cooperates, OR FAMILY 3 (BoN->FIX two-step) if a correction variant lands.
- Subscription BoN (FAMILIES 1-2) is treated as a candidate generator feeding FAMILY 3, not a standalone reliable method, unless a sample clears the gate directly.
