#!/usr/bin/env python3
"""defect_scan.py — locate STRUCTURE defects (distorted flowers, broken turrets, malformed
figures) in a tall illustration by tiling it and asking a VLM per tile, then mapping the
boxes back to full-image coords. Tiling avoids the downsampling-hallucination that wrecks
whole-image VLM reads on tall panels.

Output: <out>.json (defect list w/ full-image boxes) + <overlay>.png (boxes drawn). Prints a
ranked summary. This is the IDENTIFY step; fix with edit.py / batch_edit afterward.

Usage:
  python3 scripts/defect_scan.py --image IMG --out-json D.json --overlay OV.png [--tile 1400] [--overlap 0.15]
"""
import argparse, base64, io, json, sys
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from judge import load_key  # reuse OpenAI key loader

MODEL = "gpt-4o"
RUBRIC = (
 "You inspect ONE section of a watercolor children's-book castle illustration for DEFECTS that "
 "should be fixed. List ONLY clear defects: distorted/melted/warped flowers or leaves; "
 "broken/incomplete/duplicated/malformed turrets, spires or towers; deformed figures, faces or "
 "hands; smudges; repeated/garbled artifacts; structural impossibilities. IGNORE intentional "
 "softness, smooth plain walls, and normal painterly style. For EACH defect return a box in THIS "
 "image's pixel coords. Return ONLY JSON: {\"defects\":[{\"box\":[x0,y0,x1,y1],\"type\":\"flower|turret|figure|other\","
 "\"desc\":\"short\",\"severity\":1-5}]}. Empty if none: {\"defects\":[]}."
)
RUBRIC_SENSITIVE = (
 "You are a meticulous QA artist zooming into ONE section of a watercolor children's-book castle. "
 "Flag EVERY spot that a human would want retouched, even mild ones. Look hard for: flowers/leaves "
 "that are smeared, half-formed, fused together, lopsided or melting; turrets/spires/roofs that are "
 "broken, bent, asymmetric, cut off, missing tips, or with warped windows; figures/faces/hands that "
 "are deformed or have wrong counts; doubled/ghosted edges; mushy or garbled texture; tiling seams. "
 "Be generous (high recall) — a human will confirm. Do NOT flag plain smooth walls or normal soft "
 "watercolor washes. Return ONLY JSON: {\"defects\":[{\"box\":[x0,y0,x1,y1],"
 "\"type\":\"flower|turret|figure|texture|other\",\"desc\":\"short\",\"severity\":1-5}]} (severity = how "
 "confident+bad). Empty if truly none: {\"defects\":[]}."
)


def du(pil):
    b = io.BytesIO(); pil.save(b, format="PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def ask(tile, key, rubric=RUBRIC):
    msg = [{"role": "system", "content": rubric},
           {"role": "user", "content": [
               {"type": "text", "text": f"Section is {tile.width}x{tile.height} px. List defects."},
               {"type": "image_url", "image_url": {"url": du(tile)}}]}]
    r = requests.post("https://api.openai.com/v1/chat/completions",
                      headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                      json={"model": MODEL, "messages": msg, "max_tokens": 900, "temperature": 0,
                            "response_format": {"type": "json_object"}}, timeout=120)
    if r.status_code != 200:
        print(f"  tile ERROR {r.status_code}: {r.text[:200]}", file=sys.stderr); return []
    try:
        return json.loads(r.json()["choices"][0]["message"]["content"]).get("defects", [])
    except Exception:
        return []


def iou(a, b):
    ax0, ay0, ax1, ay1 = a; bx0, by0, bx1, by1 = b
    ix0, iy0, ix1, iy1 = max(ax0, bx0), max(ay0, by0), min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0); inter = iw * ih
    if inter == 0: return 0.0
    ua = (ax1-ax0)*(ay1-ay0) + (bx1-bx0)*(by1-by0) - inter
    return inter / ua if ua else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--overlay", required=True)
    ap.add_argument("--tile", type=int, default=1400)
    ap.add_argument("--overlap", type=float, default=0.15)
    ap.add_argument("--sensitive", action="store_true", help="high-recall rubric (more candidates to sift)")
    a = ap.parse_args()
    rubric = RUBRIC_SENSITIVE if a.sensitive else RUBRIC
    key = load_key()
    im = Image.open(a.image).convert("RGB"); W, H = im.size
    step = int(a.tile * (1 - a.overlap))
    xs = list(range(0, max(1, W - 1), step)); ys = list(range(0, max(1, H - 1), step))
    defects = []
    ntiles = 0
    for ty in ys:
        for tx in xs:
            tx1, ty1 = min(W, tx + a.tile), min(H, ty + a.tile)
            tile = im.crop((tx, ty, tx1, ty1)); ntiles += 1
            for d in ask(tile, key, rubric):
                b = d.get("box")
                if not b or len(b) != 4: continue
                fb = [tx + b[0], ty + b[1], tx + b[2], ty + b[3]]  # tile-local -> full
                fb = [max(0, fb[0]), max(0, fb[1]), min(W, fb[2]), min(H, fb[3])]
                if fb[2] - fb[0] < 8 or fb[3] - fb[1] < 8: continue
                d["box"] = [int(v) for v in fb]; defects.append(d)
    # dedup overlapping (same defect seen across overlapping tiles): keep higher severity
    defects.sort(key=lambda d: -(d.get("severity", 1)))
    kept = []
    for d in defects:
        if all(iou(d["box"], k["box"]) < 0.4 for k in kept):
            kept.append(d)
    Path(a.out_json).write_text(json.dumps({"image": a.image, "size": [W, H], "tiles": ntiles,
                                            "defects": kept}, indent=2))
    # overlay
    ov = im.copy(); dr = ImageDraw.Draw(ov)
    col = {"flower": (255, 0, 200), "turret": (255, 60, 0), "figure": (0, 120, 255)}
    for i, d in enumerate(kept, 1):
        x0, y0, x1, y1 = d["box"]; c = col.get(d.get("type"), (255, 0, 0))
        dr.rectangle([x0, y0, x1, y1], outline=c, width=max(3, W // 400))
        dr.text((x0 + 4, y0 + 4), f"{i}:{d.get('type','?')[:4]} s{d.get('severity','?')}", fill=c)
    sc = 1000 / max(W, H)
    ov.resize((int(W * sc), int(H * sc))).save(a.overlay)
    print(f"[defect_scan] {a.image}  {W}x{H}  tiles={ntiles}  defects={len(kept)}")
    for i, d in enumerate(kept, 1):
        print(f"  {i}. [{d.get('type','?')}] sev{d.get('severity','?')} {d['box']}  {d.get('desc','')[:70]}")


if __name__ == "__main__":
    main()
