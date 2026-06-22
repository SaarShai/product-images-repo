#!/usr/bin/env python3
"""reupscale.py — controlled CREATIVE re-upscale (fix blur/melt, keep style+geometry).

This is the right tool for "re-render the whole thing properly: keep all detail/style/
geometry but fix the issues" — instead of per-defect surgery. It is the same family as
Magnific; the difference is we keep the dials LOW so it stays faithful and does NOT
hallucinate (which is what melted the spires / blurred one side in the magnific output).

Run it on the CLEAN small original (NOT the broken magnific). It tiles + re-renders at
low denoise so composition/colors/geometry survive while soft/melted detail is rebuilt.

Engine: fal-ai/clarity-upscaler (open Magnific clone). Dials:
  --creativity  (0..1, deviation from source; LOW = faithful)        default 0.25
  --resemblance (0..1, keep original; HIGH = faithful)               default 0.85
  --factor      upscale_factor                                       default 2
  --steps       num_inference_steps                                  default 18

Usage:
  .venv-gen/bin/python scripts/reupscale.py --image IN.png --out OUT.png \
      --creativity 0.25 --resemblance 0.85 --factor 2
"""
import argparse, os, sys
from pathlib import Path

import fal_client
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _falcommon import load_fal_key as load_key
import requests

# Faithful default prompt: name the medium so it rebuilds in-style, forbid new content.
DEFAULT_PROMPT = (
    "a soft watercolor children's-book castle illustration, fine clean detail, "
    "crisp painted edges, coherent towers spires and flowers, masterpiece, best quality"
)
DEFAULT_NEG = (
    "blurry, smeared, melted, warped, distorted, deformed, extra structures, "
    "text, watermark, jpeg artifacts, oversharpened, plastic, noise"
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--creativity", type=float, default=0.25)
    ap.add_argument("--resemblance", type=float, default=0.85)
    ap.add_argument("--factor", type=float, default=2)
    ap.add_argument("--steps", type=int, default=18)
    ap.add_argument("--guidance", type=float, default=4.0)
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--neg", default=DEFAULT_NEG)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()

    os.environ["FAL_KEY"] = load_key()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)

    print(f"[reupscale] uploading {a.image} ...", file=sys.stderr)
    url = fal_client.upload_file(a.image)

    args = {
        "image_url": url,
        "prompt": a.prompt,
        "negative_prompt": a.neg,
        "upscale_factor": a.factor,
        "creativity": a.creativity,
        "resemblance": a.resemblance,
        "guidance_scale": a.guidance,
        "num_inference_steps": a.steps,
        "seed": a.seed,
        "enable_safety_checker": False,
    }
    print(f"[reupscale] clarity-upscaler creativity={a.creativity} resemblance={a.resemblance} "
          f"factor={a.factor} steps={a.steps}", file=sys.stderr)

    def on_q(u):
        for log in getattr(u, "logs", []) or []:
            print("   ", log.get("message", ""), file=sys.stderr)

    res = fal_client.subscribe("fal-ai/clarity-upscaler", arguments=args,
                               with_logs=True, on_queue_update=on_q)
    img = (res.get("image") or {}) if isinstance(res, dict) else {}
    out_url = img.get("url") or (res.get("images") or [{}])[0].get("url")
    if not out_url:
        print(f"no image in response: {str(res)[:400]}", file=sys.stderr); raise SystemExit(1)
    Path(a.out).write_bytes(requests.get(out_url, timeout=300).content)

    from PIL import Image
    w, h = Image.open(a.out).size
    print(f"[reupscale] -> {a.out}  {w}x{h}  (seed={res.get('seed')})")


if __name__ == "__main__":
    main()
