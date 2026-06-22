#!/usr/bin/env python3
"""nanofix.py — fix malformed parts (hands/feet/figures) of small subjects inside a large
illustration, the LEARNED way (princess fairies):

  per box:  crop -> PAD TO SQUARE (white) -> Nano Banana edit -> UNPAD to exact aspect
  then:     feathered composite of all fixed crops back into the source
  verify:   0 pixels changed OUTSIDE the boxes (rest byte-identical)

Why each step (hard-won):
 - Nano Banana (subgen --provider nano) is the best style-preserving part-fix (no mask),
   but it ALWAYS outputs 1024x1024 square and recomposes to fill it -> feed a SQUARE or it
   widens/contracts the subject. Pad-to-square before, crop padding after.  [[nano-banana-edit-square-bias]]
 - Lock framing in the prompt + name only VISIBLE parts, or it zooms out / reframes.
 - Nano is not pixel-aligned, so composite whole feathered crops (seam in white/forgiving
   areas), don't diff-mask.

boxes JSON: [{"name":"A","box":[x0,y0,x1,y1],"prompt":"<optional override>"}, ...]

Usage:
  .venv-gen/bin/python scripts/nanofix.py --src IMG --out OUT --boxes boxes.json \
      [--workdir DIR] [--feather 28] [--prompt "<default prompt>"]
"""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

R = Path(__file__).resolve().parent
PY = str(R.parent / ".venv-gen" / "bin" / "python")

DEFAULT_PROMPT = (
    "Fix only this fairy's hands and feet so each has five simple natural fingers and toes, "
    "painted in the exact same soft loose watercolor children's-book style, same colors, same "
    "exact size pose and position. Do not change anything else — keep dress, wings, face, hair "
    "and background identical. Do not zoom or recompose; keep the white margins exactly as they are."
)


def nano(sq_path, out_path, prompt, timeout=200):
    r = subprocess.run([PY, str(R / "subgen.py"), "--provider", "nano", "-i", sq_path,
                        "--prompt", prompt, "--out", out_path, "--timeout", str(timeout),
                        "--retries", "1"], capture_output=True, text=True)
    ok = Path(out_path).exists() and "OK" in (r.stdout + r.stderr)
    print(("  nano OK " if ok else "  nano FAIL ") + sq_path, file=sys.stderr)
    if not ok:
        print(r.stdout[-400:], r.stderr[-400:], file=sys.stderr)
    return ok


def fix_one(src_img, box, prompt, wd, name):
    c = src_img.crop(box); W, H = c.size; S = max(W, H)
    ox, oy = (S - W) // 2, (S - H) // 2
    sq = Image.new("RGB", (S, S), (255, 255, 255)); sq.paste(c, (ox, oy))
    sqp = str(wd / f"_sq_{name}.png"); sq.save(sqp)
    outp = str(wd / f"_nano_{name}.png")
    if not nano(sqp, outp, prompt):
        return None
    nano_img = Image.open(outp).convert("RGB").resize((S, S), Image.LANCZOS)
    fixed = nano_img.crop((ox, oy, ox + W, oy + H))      # unpad -> exact W x H
    fixed.save(str(wd / f"_fix_{name}.png"))
    # in-box visibility: how much did nano rewrite vs the source crop? The outside-box gate is
    # blind to this. A high, ~uniform delta = nano repainted the WHOLE crop (it silently degrades
    # fine detail like wings) -> eyeball every fine sub-region before trusting it. No threshold/skip
    # (nano INTENTIONALLY changes the hand/foot pixels, so a scalar gate would false-reject good fixes).
    chg = float(np.abs(np.asarray(fixed).astype(int) - np.asarray(c).astype(int)).mean())
    print(f"  {name} in-box mean change={chg:.1f} (uniform-high => whole-crop rewrite; verify wings/face)", file=sys.stderr)
    return fixed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--boxes", required=True, help="JSON file: list of {name,box,prompt?}")
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--feather", type=int, default=28)
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    a = ap.parse_args()
    wd = Path(a.workdir) if a.workdir else Path(a.out).parent / "_nanofix"
    wd.mkdir(parents=True, exist_ok=True)
    specs = json.loads(Path(a.boxes).read_text())

    base = Image.open(a.src).convert("RGB")
    src0 = np.asarray(base).astype(int)   # snapshot BEFORE the paste loop (astype copy, decoupled from paste)
    boxes = []
    for i, s in enumerate(specs):
        name = s.get("name", f"f{i}"); box = tuple(s["box"]); prompt = s.get("prompt", a.prompt)
        print(f"[nanofix] {name} {box}", file=sys.stderr)
        fixed = fix_one(base, box, prompt, wd, name)
        if fixed is None:
            print(f"[nanofix] SKIP {name} (nano failed)", file=sys.stderr); continue
        W, H = box[2] - box[0], box[3] - box[1]
        fe = a.feather
        al = Image.new("L", (W, H), 0); ImageDraw.Draw(al).rectangle([fe, fe, W - fe, H - fe], fill=255)
        al = al.filter(ImageFilter.GaussianBlur(fe / 2))
        base.paste(fixed, (box[0], box[1]), al)
        boxes.append(box)

    base.save(a.out)
    # verify: nothing changed outside the boxes (src0 snapshot taken before the loop -> no 2nd decode)
    out0 = np.asarray(base).astype(int)
    d = np.abs(src0 - out0).sum(2)
    mask = np.zeros(d.shape, bool)
    for b in boxes:
        mask[b[1]:b[3], b[0]:b[2]] = True
    outside = int((d[~mask] > 8).sum())
    print(f"[nanofix] -> {a.out}  fixed={len(boxes)}/{len(specs)}  pixels_changed_outside_boxes={outside}")
    # nonzero exit on any miss so a returncode-gating caller can't read a total no-op as success
    raise SystemExit(0 if len(boxes) == len(specs) else 2)


if __name__ == "__main__":
    main()
