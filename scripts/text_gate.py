#!/usr/bin/env python3
"""text_gate.py — DETERMINISTIC leftover-text HARD-GATE (no API call).

Companion to the VLM judge in the removal/erase pipeline. After an element
(e.g. a door sign reading "TAXI") is removed, a generative engine sometimes
"heals" the text back in — repaints faint but legible glyphs where the original
text was. The expensive VLM judge can catch this, but every call costs an API
round-trip. This gate runs a local OCR pass over the (optionally cropped) region
and FAILS deterministically if any legible text survives, so the VLM judge only
ever sees genuinely clean erasures.

How it works:
  - Crops to --region (x0,y0,x1,y1) if given, else OCRs the whole image.
  - OCR is finicky on watercolor / low-contrast art, so the crop is preprocessed
    before recognition: upscaled (default 3x), grayscaled, and contrast-stretched
    (CLAHE-style autocontrast). This is what makes a faint healed "TAXI" legible
    to the recognizer. Tune with --upscale / --no-prep.
  - Engine: PaddleOCR (PP-OCRv5/v6) by default; falls back to easyocr then
    pytesseract if Paddle is unavailable. Pick explicitly with --engine.

Output: JSON {has_text: bool, found: [strings], ...diagnostics...} on stdout.
Each detection in `kept`/`all_detections` also carries a `box` field —
[x0,y0,x1,y1] axis-aligned pixel coords *in the (optionally preprocessed) crop
space* (i.e. after --region crop and --upscale). This lets a caller map the box
back to full-image coords (full = region_origin + box/upscale) to erase only the
leftover text. `box` is null if the engine doesn't expose box geometry.
Exit code: 2 if any text with confidence >= --min-conf is found (GATE FAIL,
leftover text), else 0 (clean). This lets it gate a shell pipeline / loop.
NOTE: box geometry is purely ADDITIVE — the exit-code contract and existing JSON
keys are unchanged. --json is accepted as an explicit opt-in alias (box geometry
is emitted regardless; the flag exists so callers can self-document intent).

CLI:
  python3 scripts/text_gate.py --image IMG [--region x0,y0,x1,y1] \
      [--min-conf 0.5] [--upscale 3] [--engine paddle|easyocr|tesseract|auto] \
      [--no-prep] [--lang en] [--save-crop OUT.png] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

# Quiet noisy deps before they import.
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
os.environ.setdefault("GLOG_minloglevel", "3")
os.environ.setdefault("FLAGS_call_stack_level", "0")
import warnings

warnings.filterwarnings("ignore")


def _eprint(*a, **k):
    print(*a, file=sys.stderr, **k)


def parse_region(s: str):
    parts = [p.strip() for p in s.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(
            "region must be x0,y0,x1,y1 (four integers)"
        )
    x0, y0, x1, y1 = (int(round(float(p))) for p in parts)
    if x1 <= x0 or y1 <= y0:
        raise argparse.ArgumentTypeError("region must have x1>x0 and y1>y0")
    return (x0, y0, x1, y1)


def load_crop(image_path, region, upscale, do_prep, save_crop=None):
    """Return a preprocessed RGB numpy array ready for OCR."""
    from PIL import Image, ImageOps
    import numpy as np

    im = Image.open(image_path).convert("RGB")
    W, H = im.size
    if region is not None:
        x0, y0, x1, y1 = region
        # clamp to image bounds
        x0 = max(0, min(x0, W))
        y0 = max(0, min(y0, H))
        x1 = max(0, min(x1, W))
        y1 = max(0, min(y1, H))
        if x1 <= x0 or y1 <= y0:
            raise ValueError(
                f"region {region} is empty after clamping to image {W}x{H}"
            )
        im = im.crop((x0, y0, x1, y1))

    if do_prep:
        if upscale and upscale != 1:
            im = im.resize(
                (max(1, int(im.width * upscale)), max(1, int(im.height * upscale))),
                Image.LANCZOS,
            )
        # grayscale -> autocontrast (stretch faint glyphs) -> back to RGB
        g = ImageOps.grayscale(im)
        g = ImageOps.autocontrast(g, cutoff=1)
        im = g.convert("RGB")

    if save_crop:
        im.save(save_crop)
    return np.asarray(im)


# ---------------------------------------------------------------------------
# Engines: each returns list[(text, conf_float, box)] for ALL detected lines.
# `box` is [x0,y0,x1,y1] axis-aligned int pixel coords in the (preprocessed)
# crop space, or None if the engine doesn't expose box geometry.
# ---------------------------------------------------------------------------

_PADDLE_CACHE = {}


def _bbox_from_poly(poly):
    """Axis-aligned [x0,y0,x1,y1] from a list/array of (x,y) points; None if bad."""
    try:
        xs = [float(p[0]) for p in poly]
        ys = [float(p[1]) for p in poly]
        if not xs or not ys:
            return None
        return [int(round(min(xs))), int(round(min(ys))),
                int(round(max(xs))), int(round(max(ys)))]
    except Exception:
        return None


def run_paddle(arr, lang):
    from paddleocr import PaddleOCR

    if lang not in _PADDLE_CACHE:
        # Disable the doc-orientation / unwarping / textline-orientation
        # submodels: a tight art crop is already upright, and skipping them
        # roughly halves init + inference time.
        _PADDLE_CACHE[lang] = PaddleOCR(
            lang=lang,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
    ocr = _PADDLE_CACHE[lang]
    res = ocr.predict(arr)
    out = []
    for page in res:
        # PaddleOCR 3.x returns dict-like results.
        d = page if isinstance(page, dict) else getattr(page, "json", {}).get("res", {})
        texts = d.get("rec_texts") or []
        scores = d.get("rec_scores") or []
        # rec_boxes: axis-aligned [x0,y0,x1,y1]; rec_polys: 4-pt quads (fallback).
        rb = d.get("rec_boxes")
        rp = d.get("rec_polys")
        boxes = []
        if rb is not None:
            rb = rb.tolist() if hasattr(rb, "tolist") else rb
            boxes = [[int(round(v)) for v in b] for b in rb]
        elif rp is not None:
            for poly in rp:
                poly = poly.tolist() if hasattr(poly, "tolist") else poly
                boxes.append(_bbox_from_poly(poly))
        for i, (t, s) in enumerate(zip(texts, scores)):
            box = boxes[i] if i < len(boxes) else None
            out.append((str(t), float(s), box))
    return out


def run_easyocr(arr, lang):
    import easyocr

    reader = easyocr.Reader([lang], gpu=False, verbose=False)
    res = reader.readtext(arr)
    return [(str(t), float(c), _bbox_from_poly(box)) for (box, t, c) in res]


def run_tesseract(arr, lang):
    import pytesseract
    from pytesseract import Output

    lang_t = {"en": "eng"}.get(lang, lang)
    data = pytesseract.image_to_data(
        arr, lang=lang_t, output_type=Output.DICT
    )
    out = []
    for i, (t, c) in enumerate(zip(data["text"], data["conf"])):
        t = (t or "").strip()
        try:
            c = float(c)
        except (TypeError, ValueError):
            c = -1.0
        if t and c >= 0:
            try:
                x, y = int(data["left"][i]), int(data["top"][i])
                w, h = int(data["width"][i]), int(data["height"][i])
                box = [x, y, x + w, y + h]
            except Exception:
                box = None
            out.append((t, c / 100.0, box))  # tesseract conf is 0..100
    return out


ENGINES = {
    "paddle": run_paddle,
    "easyocr": run_easyocr,
    "tesseract": run_tesseract,
}


def pick_auto():
    """Return ordered list of engines that import cleanly."""
    order = []
    for name, mod in (("paddle", "paddleocr"), ("easyocr", "easyocr"),
                      ("tesseract", "pytesseract")):
        try:
            __import__(mod)
            order.append(name)
        except Exception:
            pass
    return order


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--image", required=True, help="path to image")
    ap.add_argument("--region", type=parse_region, default=None,
                    help="x0,y0,x1,y1 crop region (default: whole image)")
    ap.add_argument("--min-conf", type=float, default=0.5,
                    help="confidence threshold to count text as present (default 0.5)")
    ap.add_argument("--upscale", type=float, default=3.0,
                    help="upscale factor before OCR (default 3.0; helps faint art)")
    ap.add_argument("--no-prep", action="store_true",
                    help="skip upscale/grayscale/contrast preprocessing")
    ap.add_argument("--engine", default="auto",
                    choices=["auto", "paddle", "easyocr", "tesseract"],
                    help="OCR engine (default auto: paddle->easyocr->tesseract)")
    ap.add_argument("--lang", default="en", help="OCR language (default en)")
    ap.add_argument("--save-crop", default=None,
                    help="save the preprocessed crop to this path (debug)")
    ap.add_argument("--json", action="store_true",
                    help="explicit opt-in for machine consumption; box geometry "
                         "is emitted regardless (this flag only self-documents "
                         "caller intent — output and exit codes are unchanged)")
    args = ap.parse_args()

    if not os.path.exists(args.image):
        _eprint(f"ERROR: image not found: {args.image}")
        sys.exit(3)

    t0 = time.time()
    arr = load_crop(args.image, args.region, args.upscale,
                    not args.no_prep, args.save_crop)

    if args.engine == "auto":
        candidates = pick_auto()
        if not candidates:
            _eprint("ERROR: no OCR engine available "
                    "(install paddleocr, easyocr, or pytesseract)")
            sys.exit(3)
    else:
        candidates = [args.engine]

    last_err = None
    detections = None
    used = None
    for name in candidates:
        try:
            detections = ENGINES[name](arr, args.lang)
            used = name
            break
        except Exception as e:  # noqa: BLE001 - try next engine
            last_err = f"{name}: {type(e).__name__}: {e}"
            _eprint(f"WARN engine {name} failed -> {last_err}")
            continue

    if detections is None:
        _eprint(f"ERROR: all engines failed. last: {last_err}")
        sys.exit(3)

    # `box` (additive) is in the (preprocessed) crop space. To recover full-image
    # coords: full_x = region_x0 + box_x / upscale_eff (and likewise y), where
    # upscale_eff is `upscale` below and region_x0/y0 default to 0 when no region.
    all_dets = [{"text": t, "conf": round(c, 4), "box": box}
                for (t, c, box) in detections]
    kept = [d for d in all_dets if d["conf"] >= args.min_conf]
    found = [d["text"] for d in kept]
    has_text = len(found) > 0

    result = {
        "has_text": has_text,
        "found": found,
        "engine": used,
        "min_conf": args.min_conf,
        "region": list(args.region) if args.region else None,
        "region_origin": [args.region[0], args.region[1]] if args.region else [0, 0],
        "upscale": (1.0 if args.no_prep else args.upscale),
        "prep": (not args.no_prep),
        "kept": kept,
        "all_detections": all_dets,
        "runtime_s": round(time.time() - t0, 3),
    }
    print(json.dumps(result, indent=2))
    sys.exit(2 if has_text else 0)


if __name__ == "__main__":
    main()
