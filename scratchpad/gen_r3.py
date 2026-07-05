#!/usr/bin/env python3
"""Marriott round-3 blank-plaque regen — flux-control-lora-canny + MRCH LoRA.
Unbuffered, per-step logged, cached control-map uploads, per-panel try/except."""
import os, sys, json, time, pathlib, urllib.request

ROOT = pathlib.Path("/Users/za/Documents/product images repo")
CM = ROOT / "tasks/marriott-hospital/geometry/controlmaps"
OUT = ROOT / "tasks/marriott-hospital/outputs"
LORA = json.load(open(ROOT / ".brainer/tenx/marriott-lora/lora.json"))["lora_url"]

def log(*a):
    print(*a, flush=True)

# key
for line in open(ROOT / ".secrets/fal.env"):
    line = line.strip()
    if line.startswith("FAL_KEY") and "=" in line:
        os.environ["FAL_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
import fal_client

SUFFIX = (", MRCH felt-textured storybook illustration style, dense wool-felt fiber grain, "
          "soft rim lighting, flat saturated color, isolated on pure white background, "
          "artwork fills the panel silhouette to its outer contour and nothing outside it, "
          "no photorealism; all signs, plaques and banners are BLANK with no letters, no words, "
          "no writing, no glyphs of any kind")

PANELS = {
    "door": dict(size=(820, 1190), prompt=(
        "MRCH a friendly children's hospital main entrance building, white stone facade with a "
        "domed gable, a blue medical cross badge at the top, a blank rectangular sign board above "
        "the entrance, a curved blue entrance canopy with small downlights, a tall arched central "
        "doorway, a blue hinged door with a cross, potted green shrubs and lamp bollards flanking "
        "the entrance, tiled forecourt")),
    "left": dict(size=(820, 2105), prompt=(
        "MRCH a tall narrow children's hospital garden scene, a big leafy tree, a wooden bench, "
        "a blank standing sign board with small heart and smiley icons, flower beds with daisies, "
        "a lit ground-floor hospital window, soft clouds in a blue sky at the top")),
    "right": dict(size=(820, 2105), prompt=(
        "MRCH a tall narrow children's hospital emergency wing, a rooftop helipad with a white H "
        "in a blue circle and a red and white windsock, a blank red sign board over a canopy, "
        "a cute white ambulance with a blue medical star under a covered bay, a small blank sign "
        "board, flower beds, soft clouds in a blue sky at the top")),
}

def upload(p):
    log(f"[upload] {p.name} ...")
    t = time.time()
    url = fal_client.upload_file(str(p))
    log(f"[upload] {p.name} -> {url[:48]}... ({time.time()-t:.1f}s)")
    return url

def main():
    log(f"=== r3 gen start LoRA={LORA[:48]}...")
    ctrl_urls = {p: upload(CM / f"{p}-control.png") for p in PANELS}
    for name, cfg in PANELS.items():
        w, h = cfg["size"]
        log(f"[gen] {name} {w}x{h} submitting num_images=3 ...")
        t = time.time()
        try:
            res = fal_client.subscribe("fal-ai/flux-control-lora-canny", arguments={
                "prompt": cfg["prompt"] + SUFFIX,
                "control_lora_image_url": ctrl_urls[name],
                "control_lora_scale": 0.35,
                "loras": [{"path": LORA, "scale": 1.05}],
                "image_size": {"width": w, "height": h},
                "num_images": 3, "guidance_scale": 4.0,
                "num_inference_steps": 40, "enable_safety_checker": False,
            })
        except Exception as e:
            log(f"[gen] {name} FAILED: {e}")
            continue
        imgs = res.get("images", [])
        log(f"[gen] {name} done {len(imgs)} imgs ({time.time()-t:.1f}s)")
        for i, im in enumerate(imgs, 1):
            dest = OUT / f"r3_{name}_s{i}.png"
            urllib.request.urlretrieve(im["url"], dest)
            log(f"[save] {dest.name} {dest.stat().st_size//1024}KB")
    log("=== r3 gen COMPLETE")

if __name__ == "__main__":
    main()
