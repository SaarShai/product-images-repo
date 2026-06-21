# K — Deterministic leftover-text gate (OCR) — implementation

**Goal:** a deterministic, no-API gate that catches "removal healed the text
back in" — complementing the VLM judge so a regenerated/erased region that
re-grows legible glyphs (e.g. a door sign reading **TAXI**) is rejected without
spending an API call.

**Status: PASS** — both test cases discriminate correctly.

---

## Engine

**PaddleOCR 3.7.0** (PP-OCRv6 medium det+rec) on **paddlepaddle 3.3.1**, CPU,
Apple Silicon (arm64), Python 3.9.6.

- Paddle installed cleanly on this Mac — no fallback needed. `easyocr` and
  `pytesseract` are wired as automatic fallbacks (`--engine auto` tries
  paddle → easyocr → tesseract), but paddle is the one that ran for both tests.
- PaddleOCR 3.x dropped the old `use_angle_cls` / `show_log` kwargs. The script
  uses the 3.x API: `PaddleOCR(lang=..., use_doc_orientation_classify=False,
  use_doc_unwarping=False, use_textline_orientation=False)` + `.predict(arr)`,
  reading `rec_texts` / `rec_scores` off the result dict. Disabling the three
  doc/orientation submodels (the crop is already an upright tight art region)
  roughly halves init + inference time.

## Install

Dedicated venv (constraint honored — no other scripts touched):

```bash
python3 -m venv .venv-ocr
.venv-ocr/bin/python -m pip install --upgrade pip
.venv-ocr/bin/python -m pip install paddleocr paddlepaddle
```

First run downloads ~5 models (det, rec, doc-ori, unwarp, textline-ori) to
`~/.paddlex/official_models/` (one-time, cached thereafter). Cold init incl.
download was ~90s; warm runs reuse the cache.

## Script

`scripts/text_gate.py`

```
python3 scripts/text_gate.py --image IMG [--region x0,y0,x1,y1] [--min-conf 0.5]
        [--upscale 3] [--engine auto|paddle|easyocr|tesseract] [--no-prep]
        [--lang en] [--save-crop OUT.png]
```

- Crops to `--region` (clamped to image bounds), preprocesses (default **3x
  LANCZOS upscale → grayscale → autocontrast cutoff=1** — the watercolor-tuning
  that makes faint healed glyphs legible), OCRs, and emits
  `{has_text, found, engine, kept, all_detections, runtime_s, ...}` JSON.
- **Exit code: 2** if any detection has `conf >= --min-conf` (GATE FAIL =
  leftover text), **0** if clean, **3** on error / no engine. Designed to gate a
  shell pipeline / loop.
- The preprocessing defaults were sufficient — no extra tuning was required for
  these inputs. (`--no-prep` disables it; `--upscale` adjusts the factor if a
  future faint case needs 2x/4x.)

## TEST results

Run with the venv interpreter; min-conf 0.5; default 3x prep.

**Has-text case** — `tasks/nyc-taxi/work/L2_ctx.png` region `405,492,728,592`
(the door "TAXI"):
```json
{ "has_text": true, "found": ["TAXI"], "engine": "paddle",
  "kept": [{"text": "TAXI", "conf": 1.0}], "runtime_s": 2.343 }
```
→ exit **2**. Verified it actually reads **TAXI** at conf **1.0**. ✅

**Clean case** — `tasks/nyc-taxi/work/L2_erased.png` same region:
```json
{ "has_text": false, "found": [], "engine": "paddle",
  "kept": [], "all_detections": [], "runtime_s": 2.266 }
```
→ exit **0**. No detections at all. ✅

The gate cleanly separates the two: leftover "TAXI" → FAIL(2), erased → PASS(0).

## Runtime

- Warm (models cached, doc/orientation submodels disabled): **~2.3s per call**
  on a ~323×100 region upscaled 3×.
- Cold (first ever call, model download): ~90s one-time.

## Notes / constraints honored

- Dedicated `.venv-ocr` venv; no other scripts modified.
- No secrets printed.
- Verified `--help` and `auto` engine selection (lands on paddle).
- Models live in `~/.paddlex/official_models/` (outside the repo).
