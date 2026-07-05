#!/usr/bin/env python3
"""onepass_gen.py — ONE-PASS geometry×style generation (the proven v2 route).

fal-ai/flux-control-lora-canny + a trained style LoRA:
  geometry comes from the control map (studio/controlmap.py output),
  style from the LoRA, content from EDGES in the control map (LAW 0).
Proven: Cap Juluca + Marriott 3-panel (silhouette-IoU 0.975-0.988 first-shot).

Usage:
  python3 scripts/onepass_gen.py --control <panel>-control.png \
      --lora-json .brainer/tenx/marriott-lora/lora.json \
      --prompt "MRCH ..." --width 820 --height 2105 \
      --out-prefix tasks/<task>/outputs/r4_left [-n 3] \
      [--control-scale 0.35] [--lora-scale 1.05] [--mask <panel>-mask.png] \
      [--dry-run]

- Prompt rule: signs/plaques BLANK, no glyphs ([[no-painted-text-vector-layers]]).
  Pass --allow-text to skip the auto-appended blank-signage clause (rare).
- fal snaps width/height to buckets (820x2105 -> 576x1536): expected; score
  with --mask (resize-normalized silhouette-IoU) and place finals by spec bbox.
- --dry-run validates inputs + prints the exact request without spending.
- IoU gate = SHAPE ONLY. A near-empty panel can pass. Vision judge is mandatory.
"""
import argparse, json, os, sys, time, urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

BLANK_CLAUSE = (", all signs, plaques and banners are BLANK with no letters, "
                "no words, no writing, no glyphs of any kind")


def load_fal_key():
    for line in open(REPO / ".secrets/fal.env"):
        line = line.strip()
        if line.startswith("FAL_KEY") and "=" in line:
            os.environ["FAL_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
            return
    sys.exit("FAL_KEY not found in .secrets/fal.env")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", required=True, help="control map PNG (white edges on black)")
    ap.add_argument("--lora-json", required=True,
                    help="trained-LoRA registry json (lora_url + trigger_word)")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--width", type=int, required=True)
    ap.add_argument("--height", type=int, required=True)
    ap.add_argument("--out-prefix", required=True, help="saves <prefix>_s1.png ...")
    ap.add_argument("-n", "--num-images", type=int, default=3)
    ap.add_argument("--control-scale", type=float, default=0.35,
                    help="geometry<->style dial; up=tighter geometry (0.3-0.6 useful)")
    ap.add_argument("--lora-scale", type=float, default=1.05)
    ap.add_argument("--guidance", type=float, default=4.0)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--mask", help="panel mask PNG: score each output's silhouette-IoU")
    ap.add_argument("--iou-min", type=float, default=0.85)
    ap.add_argument("--allow-text", action="store_true",
                    help="skip the auto blank-signage clause (text is normally a vector layer)")
    ap.add_argument("--dry-run", action="store_true", help="validate + print request; no spend")
    a = ap.parse_args()

    control = Path(a.control)
    lora_meta = json.load(open(a.lora_json))
    if not control.exists():
        sys.exit(f"control map missing: {control}")
    if lora_meta.get("status") != "COMPLETED" or "lora_url" not in lora_meta:
        sys.exit(f"lora.json not COMPLETED / missing lora_url: {a.lora_json}")
    trigger = lora_meta.get("trigger_word", "")
    if trigger and trigger not in a.prompt:
        sys.exit(f"prompt must contain the LoRA trigger word '{trigger}'")

    prompt = a.prompt if a.allow_text else a.prompt + BLANK_CLAUSE
    args = {
        "prompt": prompt,
        "control_lora_image_url": f"<upload:{control}>",
        "control_lora_scale": a.control_scale,
        "loras": [{"path": lora_meta["lora_url"], "scale": a.lora_scale}],
        "image_size": {"width": a.width, "height": a.height},
        "num_images": a.num_images, "guidance_scale": a.guidance,
        "num_inference_steps": a.steps, "enable_safety_checker": False,
    }
    if a.seed is not None:
        args["seed"] = a.seed

    if a.dry_run:
        print(json.dumps({"endpoint": "fal-ai/flux-control-lora-canny",
                          "arguments": args, "dry_run": True}, indent=2))
        return

    load_fal_key()
    import fal_client
    print(f"[upload] {control.name}", flush=True)
    args["control_lora_image_url"] = fal_client.upload_file(str(control))
    print(f"[gen] {a.width}x{a.height} n={a.num_images} cs={a.control_scale} ls={a.lora_scale}",
          flush=True)
    t = time.time()
    res = fal_client.subscribe("fal-ai/flux-control-lora-canny", arguments=args)
    imgs = res.get("images", [])
    print(f"[gen] done {len(imgs)} imgs ({time.time()-t:.1f}s)", flush=True)

    out_prefix = Path(a.out_prefix)
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    report = []
    for i, im in enumerate(imgs, 1):
        dest = Path(f"{out_prefix}_s{i}.png")
        urllib.request.urlretrieve(im["url"], dest)
        row = {"file": str(dest), "kb": dest.stat().st_size // 1024}
        if a.mask:
            sys.path.insert(0, str(REPO))
            from studio.controlmap import score
            row.update(score(dest, a.mask, a.iou_min))
        report.append(row)
        print(f"[save] {json.dumps(row)}", flush=True)
    print(json.dumps({"outputs": report,
                      "reminder": "IoU is shape-only; run the vision judge before accepting"}))


if __name__ == "__main__":
    main()
