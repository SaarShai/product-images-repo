#!/usr/bin/env python3
"""Generate images with a trained style LoRA on fal (flux-lora endpoint).

Companion to flux-lora-fast-training. Reads FAL_KEY from .secrets/fal.env when
not in the environment (same convention as falgen.py). Default LoRA comes from
.brainer/tenx/lora-pilot/lora.json so callers don't hardcode URLs.

Usage:
  python3 scripts/lora_gen.py --prompt "CJWC style watercolor ..." \
      --out out_dir/name.png --size 816x1928 --n 3 --seed 7
"""
import argparse, json, os, sys, urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_LORA_JSON = REPO / ".brainer/tenx/lora-pilot/lora.json"
ENDPOINT = "fal-ai/flux-lora"


def _load_key():
    if os.environ.get("FAL_KEY"):
        return
    env = REPO / ".secrets/fal.env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("FAL_KEY"):
                os.environ["FAL_KEY"] = line.split("=", 1)[1].strip().strip('"')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt")
    ap.add_argument("--prompt-file")
    ap.add_argument("--out", required=True, help="output path; _2.._N suffixed when --n>1")
    ap.add_argument("--lora", default=None, help="LoRA url/path; default: lora_url from lora.json")
    ap.add_argument("--lora-json", default=str(DEFAULT_LORA_JSON))
    ap.add_argument("--scale", type=float, default=0.9, help="LoRA scale")
    ap.add_argument("--size", default="816x1928", help="WxH; flux-lora custom image_size")
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--steps", type=int, default=28)
    ap.add_argument("--guidance", type=float, default=3.5)
    a = ap.parse_args()

    prompt = a.prompt or (Path(a.prompt_file).read_text().strip() if a.prompt_file else None)
    if not prompt:
        sys.exit("need --prompt or --prompt-file")
    lora = a.lora or json.load(open(a.lora_json))["lora_url"]
    if not lora:
        sys.exit("no LoRA url (train first, or pass --lora)")
    w, h = (int(x) for x in a.size.lower().split("x"))

    _load_key()
    import fal_client

    args = {
        "prompt": prompt,
        "loras": [{"path": lora, "scale": a.scale}],
        "image_size": {"width": w, "height": h},
        "num_images": a.n,
        "num_inference_steps": a.steps,
        "guidance_scale": a.guidance,
        "enable_safety_checker": False,
    }
    if a.seed is not None:
        args["seed"] = a.seed
    res = fal_client.subscribe(ENDPOINT, arguments=args)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, im in enumerate(res["images"]):
        p = out if i == 0 else out.with_name(f"{out.stem}_{i+1}{out.suffix}")
        urllib.request.urlretrieve(im["url"], p)
        paths.append(str(p))
    print(json.dumps({"endpoint": ENDPOINT, "seed": res.get("seed"), "paths": paths}))


if __name__ == "__main__":
    main()
