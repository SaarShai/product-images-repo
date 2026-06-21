# A — Automatic mask generation (text-prompt → tight binary mask)

Research date: 2026-06-21. Goal: stop hand-eyeballing mask coordinates. Given a finished
watercolor+ink illustration PNG (up to ~4200px) and an element description (e.g. "the yellow
taxi", "the TAXI roof sign"), automatically produce a tight binary mask PNG (white = region)
for inpaint/erase/recolor while keeping the rest byte-identical.

Environment: Apple M3 Max (48GB, MPS), fal.ai + OpenAI keys, Python 3.12 venv.

> Honesty notes: every repo/endpoint below was opened and verified to exist on 2026-06-21.
> I did NOT find a published benchmark of any of these models on watercolor/illustration art —
> all are trained mostly on photographs. Treat the "works on illustration" question as
> something to validate on OUR images, not assume from a number. Star counts not collected
> (the task said not to invent them; I did not pull them).

---

## 0. The key distinction (text vs box/click)

Plain **SAM / SAM2** do NOT take a text prompt. They take a **point / box / mask** and return a
mask. To go from *words* → mask you need a grounding stage (text → box) in front of SAM, OR a
model that natively accepts text. The text-capable options are:

- **SAM 3** (native text "concept" prompts) — newest, best.
- **Grounded-SAM / lang-SAM / GroundingDINO+SAM2** (grounding model finds the box, SAM segments it).
- **EVF-SAM** (a single model that fuses a text encoder with SAM).
- **Florence-2** `REFERRING_EXPRESSION_SEGMENTATION` (VLM emits a polygon directly).

Box/click-only (no text): **SAM2, MobileSAM, FastSAM, EfficientSAM**. These are great as the
*second stage* (precise mask from a box) or for an interactive "click the taxi" UI, but they
don't read "the yellow taxi" on their own.

---

## 1. Promptable / text-driven segmentation — option-by-option

### SAM 3 (Meta) — native text-concept → masks  ★ top pick via API
- Repo (verified): https://github.com/facebookresearch/sam3
- Paper: https://arxiv.org/abs/2511.16719 ("Segment Anything with Concepts"), released 2025-11-19.
- Input: **text phrase** ("yellow taxi"), AND/OR point_prompts, AND/OR box_prompts. Returns ALL
  instances of an open-vocabulary concept (270K-concept benchmark), with masks + scores + boxes.
- Output: mask(s). 848M params.
- License: "SAM License" (Meta's source-available SAM license — verify the LICENSE file before
  any redistribution; it is NOT plain Apache/MIT).
- **Local on MPS: effectively NO right now.** The official repo lists CUDA 12.6+ / PyTorch 2.7+
  as prerequisites and does not mention CPU/MPS. There is a confirmed open MPS bug
  (`pin_memory()` fails on Apple Silicon) tracked in Ultralytics:
  https://github.com/ultralytics/ultralytics/issues/22954
- **Use via API instead** — see fal.ai `fal-ai/sam-3/image` in §2. This is the clean path on M3.
- Effort: **S** (as an API), **L** (local on Mac — fighting CUDA assumptions, not worth it).

### lang-segment-anything (langSAM) — GroundingDINO + SAM2, local
- Repo (verified): https://github.com/luca-medeiros/lang-segment-anything
- Fork w/ updated deps (verified): https://github.com/paulguerrero/lang-sam
- License: **Apache 2.0** (the wrapper). Note GroundingDINO weights/code carry their own terms.
- Input: **text** ("wheel."). API is trivially small:
  ```python
  from PIL import Image
  from lang_sam import LangSAM
  model = LangSAM()
  img = Image.open("page.png").convert("RGB")
  results = model.predict([img], ["yellow taxi."])   # returns masks, boxes, scores
  ```
- Local MPS: install instructions assume PyTorch+CUDA 12.4 and the Docker uses `--gpus all`; it
  is plain PyTorch under the hood so MPS is *plausible* with `PYTORCH_ENABLE_MPS_FALLBACK=1`, but
  this is **not advertised/supported** — expect some op-fallback friction. Unverified that it runs
  cleanly on M3.
- Effort: **M** (pip install one line; the friction is MPS/dep wrangling).

### Grounded-SAM / Grounded-SAM-2 (IDEA-Research) — the reference pipeline
- Repos (verified): https://github.com/IDEA-Research/Grounded-Segment-Anything ,
  https://github.com/IDEA-Research/Grounded-SAM-2 (the latter pairs GroundingDINO/Florence-2 + SAM2).
- License: **Apache 2.0** (repo). Same caveat: GroundingDINO + SAM checkpoints have their own licenses.
- Input: **text** → boxes (GroundingDINO) → masks (SAM/SAM2). Supports multi-mask + negative mask.
- Local MPS: heavier setup (custom CUDA ops in GroundingDINO historically); more install pain than
  langSAM on a Mac. Better consumed hosted (see Replicate `schananas/grounded_sam`, §2).
- Effort: **L** local / **S** via Replicate.

### EVF-SAM — single fused text→mask model (offered hosted on fal)
- Hosted (verified): https://fal.ai/models/fal-ai/evf-sam/api  (endpoint id `fal-ai/evf-sam`)
- Underlying project: EVF-SAM (text-encoder-fused SAM). Input: `prompt` + `image_url`
  (+ optional `negative_prompt`); output: **binary mask PNG** when `mask_only: true` (default).
- License of the OSS model: BSD-ish/research — verify before local use; the easy path here is the
  fal endpoint, so license matters less for API use.
- Effort: **S** (API). Good cheap fallback if SAM 3 mis-segments.

### Florence-2 (Microsoft) — VLM that emits a mask polygon from a referring expression
- Model cards (verified): https://huggingface.co/microsoft/Florence-2-large ,
  https://huggingface.co/docs/transformers/model_doc/florence2
- License: **MIT**. Sizes: base ~230M, large ~770M (weights public).
- Input: task token `<REFERRING_EXPRESSION_SEGMENTATION>` + text ("the yellow taxi"); also
  `<REGION_TO_SEGMENTATION>` (box→mask) and `<OPEN_VOCABULARY_DETECTION>` (text→boxes).
  Output: **polygon points** (you rasterize to a binary mask), not a pixel-tight mask directly.
- Local MPS: runs in HF `transformers` PyTorch; MPS works for transformer models (set
  `device="mps"`, `PYTORCH_ENABLE_MPS_FALLBACK=1`). Smallest footprint of the bunch.
- Caveat: its RES masks are **coarse** (Florence-2-L ~35.8 mIoU on RefCOCO RES; Roboflow's own
  writeup calls some masks "faint"/loose). Best used as a *grounding* step (text→box) whose box
  you hand to SAM2 for a tight mask — i.e. roll-your-own Florence-2→SAM2 (this is exactly what
  Grounded-SAM-2 does).
- Effort: **M** (HF load + post-process polygon → mask; or wire to SAM2).

### Box/click-only stage-2 mask refiners (NOT text)
All of these take a point/box and return a tight mask — ideal stage-2 after grounding, or for an
interactive click UI. None reads text.
- **SAM 2** (Meta): https://github.com/facebookresearch/sam2 . Via **Ultralytics** it is the
  easiest to install AND is reported running on **Apple Silicon (M4 Air) and CPU** — docs:
  https://docs.ultralytics.com/models/sam-2 . Checkpoints: tiny 78MB, base 162MB (small/large
  larger). Input: `bboxes=[x1,y1,x2,y2]` or `points=[[x,y]], labels=[1]`. License: see repo
  (Apache-2.0 code; checkpoints under Meta terms). Effort: **S**.
- **MobileSAM**: https://github.com/ChaoningZhang/MobileSAM — ~7x smaller / ~5x faster than
  FastSAM; ~3s on a Mac i5 CPU (so faster on M3 MPS). Apache-2.0. Box/point. Effort: **S**.
- **FastSAM**: https://github.com/CASIA-LMC-Lab/FastSAM — YOLO-based "segment everything", fast
  but lower AP. AGPL-3.0 (copyleft — note for any product use). Effort: **S**.
- **EfficientSAM**: https://github.com/yformer/EfficientSAM — ~20x faster than SAM-B at small
  AP cost; box/point. License: Apache-2.0 (verify). Effort: **M**.
- All also available via **Ultralytics** (`pip install ultralytics`) which abstracts MPS/device
  and gives one consistent API for SAM2/MobileSAM/FastSAM/SAM3.

---

## 2. Hosted endpoints (no local install) — VERIFIED

| Endpoint (verified URL) | id | Input | Output | Notes |
|---|---|---|---|---|
| https://fal.ai/models/fal-ai/sam-3/image/api | `fal-ai/sam-3/image` | **text `prompt`** + optional `point_prompts`/`box_prompts`, `max_masks`, `output_format` | `masks: [{url,width,height}]` + scores + normalized boxes `[cx,cy,w,h]` | SAM 3, native text concept. **Best text→mask API.** |
| https://fal.ai/models/fal-ai/sam-3/image-rle/api | `fal-ai/sam-3/image-rle` | same | masks as RLE | RLE variant (compact). |
| https://fal.ai/models/fal-ai/evf-sam/api | `fal-ai/evf-sam` | **text `prompt`** (+`negative_prompt`), `mask_only` | **binary mask PNG** | EVF-SAM2; good cheap fallback. |
| https://fal.ai/models/fal-ai/sam2/image | `fal-ai/sam2/image` | box/point | mask | SAM2, no text. |
| https://fal.ai/models/fal-ai/sam2/auto-segment | `fal-ai/sam2/auto-segment` | none/auto | all masks | "segment everything". |
| https://replicate.com/schananas/grounded_sam | `schananas/grounded_sam` | **text** mask_prompt (+ negative) | mask image for inpainting | GroundingDINO+SAM. **~$0.0017/run (~588 runs/$1), ~2s.** Cheapest text→mask. |

Pricing: fal SAM-3 / EVF-SAM per-call price not published on the API docs page (check
https://fal.ai/pricing). Replicate grounded_sam is explicitly ~$0.0017/run.

---

## 3. Apple-Silicon / MPS feasibility summary (M3 Max, 48GB)

- **SAM 3 local: not practically supported on MPS today** (CUDA-only prereqs + open `pin_memory`
  MPS bug). → use fal API.
- **SAM2 / MobileSAM / FastSAM via Ultralytics: yes** — Ultralytics docs report SAM2 on Apple
  Silicon + CPU; `pip install ultralytics` then `device="mps"`. Sizes are small (tiny 78MB,
  base 162MB), so memory is a non-issue at 48GB. Speed: interactive (sub-second to a few seconds
  per mask on MPS for the small checkpoints).
- **Florence-2: yes** — plain HF transformers, `device="mps"`, ~230M/770M; works with
  `PYTORCH_ENABLE_MPS_FALLBACK=1`. Smallest install.
- **langSAM / Grounded-SAM local: maybe, with friction** — plain PyTorch so MPS is plausible but
  unsupported/untested upstream; GroundingDINO has historically shipped custom CUDA ops. If you
  want this stack, prefer it hosted.
- Always set `PYTORCH_ENABLE_MPS_FALLBACK=1` so unsupported ops fall back to CPU instead of crashing.

---

## 4. Illustration-domain caveats (watercolor + ink, flat art)

- **No published benchmark** of SAM/GroundingDINO/Florence-2 on illustration/cartoon art was found;
  all are photo-trained. Do NOT trust a confidence score as "fit" — eyeball the overlay on OUR
  art (consistent with the repo's existing "region-IoU ≠ fit" / "judge needs hi-DPI crops" rules).
- Expected failure modes on flat art: soft watercolor edges and low ink contrast can make the
  grounding box loose and the SAM mask bleed past a soft edge; a named *sub-part* ("the TAXI roof
  sign") may be harder to ground than a whole object ("the taxi").
- Mitigations: (a) prompt the whole object first, then refine with a box/point on the sub-part via
  SAM2; (b) at 4200px, segment a downscaled copy for grounding then upscale the mask, OR crop to
  the grounded box and run SAM2 at full res for a tight edge; (c) post-process the returned mask
  (threshold + small morphological close + 1–2px feather) before compositing; (d) for byte-exact
  background preservation, composite only inside the mask (the repo's existing `--diffmask` discipline).
- SAM 3's "segment ALL instances of a concept" is a genuine plus for our use (e.g. all windows) —
  but for "the ONE taxi" you'll filter by score/box, which is easy from its output.

---

## 5. RANKED top-3 for "text-prompt → tight mask of a named element in an illustration"

1. **fal-ai/sam-3/image (SAM 3 via fal API)** — best accuracy + native text concept prompts,
   returns masks + boxes + scores, zero local setup, runs anywhere. Adoption **S**.
2. **schananas/grounded_sam (Replicate)** — proven text→mask-for-inpainting, dirt cheap
   (~$0.0017/run), supports negative prompts; great fallback / second opinion. Adoption **S**.
3. **Florence-2 (text→box) → SAM2 (box→tight mask), local on MPS** — fully local, free, MIT/Apache,
   small models, gives you a tight SAM2 edge; more glue code. Adoption **M**.
   (Equivalent hosted form: `fal-ai/evf-sam` as a single-call local-free alternative — also strong.)

Honorable mention: **lang-segment-anything** if you specifically want a one-line local
GroundingDINO+SAM2 — Apache-2.0, but MPS is unverified.

---

## 6. THE PICK + minimal adoption plan

**Pick: `fal-ai/sam-3/image` (SAM 3 on fal.ai).**
Why: it is the only option that natively takes a free-text concept ("the yellow taxi", "the TAXI
roof sign") and returns tight masks + boxes + scores, with no local install and no CUDA/MPS pain —
which is exactly the M3 reality (SAM 3 local is CUDA-only). It removes the hand-coded-rectangle
step entirely, and you already have a fal key. Keep `schananas/grounded_sam` (Replicate) as a
one-line fallback, and stand up the local **Florence-2→SAM2** combo later if you want an offline /
zero-marginal-cost path.

### Minimal adoption (drop-in: PNG + description → binary mask PNG, white = region)

```python
# scripts/automask.py  — fal SAM 3 text→mask
import os, sys, requests, fal_client   # pip install fal-client requests

def automask(image_path, prompt, out_path="mask.png", max_masks=1):
    url = fal_client.upload_file(image_path)              # FAL_KEY env must be set
    r = fal_client.subscribe("fal-ai/sam-3/image", arguments={
        "image_url": url,
        "prompt": prompt,          # e.g. "yellow taxi" or "TAXI roof sign"
        "max_masks": max_masks,
        "output_format": "png",
        "apply_mask": False,       # we want the MASK, not the cutout
    })
    masks = r["masks"]             # also r has scores + boxes [cx,cy,w,h] normalized
    if not masks:
        raise SystemExit("no mask for prompt: " + prompt)
    m = requests.get(masks[0]["url"]).content
    open(out_path, "wb").write(m)
    return out_path, r

# usage: FAL_KEY=... python scripts/automask.py page.png "yellow taxi" mask.png
if __name__ == "__main__":
    print(automask(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "mask.png"))
```
Post-process (always, given soft watercolor edges): threshold to 0/255, `cv2.morphologyEx(CLOSE)`
with a 3–5px kernel, optional 1px feather; then composite ONLY inside the mask so the rest stays
byte-identical (existing `--diffmask` rule). And per repo discipline: view the mask overlaid on
the page before trusting it — don't accept it from the score alone.

Fallback one-liner (Replicate grounded_sam):
```bash
# REPLICATE_API_TOKEN must be set
curl -s -X POST https://api.replicate.com/v1/predictions \
  -H "Authorization: Bearer $REPLICATE_API_TOKEN" -H "Content-Type: application/json" \
  -d '{"version":"schananas/grounded_sam",
       "input":{"image":"<png-url>","mask_prompt":"yellow taxi","negative_mask_prompt":""}}'
```

### Local offline path (when you want it), via Ultralytics on MPS
```bash
pip install ultralytics                       # one API for SAM2/MobileSAM/SAM3
export PYTORCH_ENABLE_MPS_FALLBACK=1
```
```python
from ultralytics import SAM
m = SAM("sam2.1_b.pt")                         # 162MB; runs on device="mps"
res = m("page.png", bboxes=[x1,y1,x2,y2], device="mps")   # box from a grounder → tight mask
```
For text grounding locally, run Florence-2 `<OPEN_VOCABULARY_DETECTION>` (HF transformers,
`device="mps"`) to get the box, feed that box to SAM2 above.

---

## Verified source URLs
- SAM 3 repo: https://github.com/facebookresearch/sam3
- SAM 3 paper: https://arxiv.org/abs/2511.16719
- SAM 3 MPS bug: https://github.com/ultralytics/ultralytics/issues/22954
- SAM 2 repo: https://github.com/facebookresearch/sam2
- SAM 2 / Ultralytics (MPS, sizes): https://docs.ultralytics.com/models/sam-2
- lang-segment-anything: https://github.com/luca-medeiros/lang-segment-anything
- lang-sam fork: https://github.com/paulguerrero/lang-sam
- Grounded-Segment-Anything: https://github.com/IDEA-Research/Grounded-Segment-Anything
- Grounded-SAM-2: https://github.com/IDEA-Research/Grounded-SAM-2
- MobileSAM: https://github.com/ChaoningZhang/MobileSAM
- FastSAM: https://github.com/CASIA-LMC-Lab/FastSAM
- EfficientSAM: https://github.com/yformer/EfficientSAM
- Florence-2 large: https://huggingface.co/microsoft/Florence-2-large
- Florence-2 docs: https://huggingface.co/docs/transformers/model_doc/florence2
- Florence-2 RES writeup: https://blog.roboflow.com/florence-2-instance-segmentation/
- fal SAM 3 image API: https://fal.ai/models/fal-ai/sam-3/image/api
- fal EVF-SAM API: https://fal.ai/models/fal-ai/evf-sam/api
- fal SAM 2 image: https://fal.ai/models/fal-ai/sam2/image
- Replicate grounded_sam: https://replicate.com/schananas/grounded_sam
