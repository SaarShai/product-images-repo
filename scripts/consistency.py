#!/usr/bin/env python3
"""consistency.py — redraw the SAME character/element consistently across MANY instances.

Realizes the reference-lock rule: feed the APPROVED instance as a reference so every
redrawn instance MATCHES it, then JUDGE THE SET TOGETHER (not one instance in isolation).

Pipeline, per target instance:
  1. resolve the instance box (explicit --box per target, or SAM-3 automask from
     `element` text confined to a search --box).
  2. redraw via scripts/falref_apply.py  ->  image_urls = [target_region, REF, *extra-refs]
     so Flux.2-pro/edit reproduces the canonical design inside the target crop.
  3. composite back onto --src with scripts/compose_fairy.py --diffmask  (figure-only
     paste, surroundings byte-exact) and GATE on the outside-mask delta (<= --gate).
  4. CONSISTENCY check: pairwise-judge the redrawn region vs --ref ("same character
     design/style?") via scripts/judge.py --mode pairwise, both orders -> match verdict.

Outputs:
  - <outdir>/<suffix>.raw.png      : raw falref region
  - <outdir>/<suffix>.final.png    : full src with ONLY this instance redrawn (composited)
  - <outdir>/<suffix>.region.png   : the redrawn region cropped back out (for the sheet/judge)
  - <outdir>/_consistency_sheet.png: contact sheet — REF first, then every redrawn region
  - <outdir>/_consistency.json     : per-instance gate + match verdicts + set summary

falref_apply returns a region at the model's own size; we rescale it to the crop box
before compositing (compose_fairy already resizes regen->crop, but we also emit a
crop-sized region for the sheet/judge).

Usage:
  python3 scripts/consistency.py \
    --src tasks/nyc-taxi/out/nyc-fixed.png \
    --ref work/left_cab.png \
    --targets '[{"box":"1700,2950,2700,3340","out_suffix":"mid"}]' \
    --prompt-file work/prompt.md \
    --outdir tasks/improve --gate 0 [--retries 2] [--extra-ref R.png]

--targets is a JSON list (inline string or @file.json). Each item:
  {"box":"x0,y0,x1,y1", "out_suffix":"name"}            explicit box
  {"element":"the yellow taxi", "search_box":"x0,..", "out_suffix":"name"}  automask
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def run(cmd):
    """Run a subprocess, stream nothing sensitive, return (rc, stdout+stderr)."""
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out


def box_tuple(s):
    return tuple(int(v) for v in s.split(","))


def load_targets(spec):
    if spec.startswith("@"):
        spec = Path(spec[1:]).read_text()
    data = json.loads(spec)
    if isinstance(data, dict):
        data = [data]
    return data


def resolve_box(src, item, suffix, outdir):
    """Return an explicit "x0,y0,x1,y1" box. If only `element` is given, automask it."""
    if item.get("box"):
        return item["box"]
    element = item.get("element")
    if not element:
        raise SystemExit(f"[consistency] target '{suffix}' has neither box nor element")
    mask_out = outdir / f"{suffix}.mask.png"
    cmd = ["python3", str(SCRIPTS / "automask.py"),
           "--image", str(src), "--prompt", element, "--out", str(mask_out)]
    if item.get("search_box"):
        cmd += ["--box", item["search_box"]]
    rc, out = run(cmd)
    if rc != 0:
        raise SystemExit(f"[consistency] automask failed for '{suffix}':\n{out}")
    # parse mask_bbox=(x0, y0, x1, y1) from automask stdout
    import re
    m = re.search(r"mask_bbox=\((\d+), (\d+), (\d+), (\d+)\)", out)
    if not m:
        raise SystemExit(f"[consistency] could not parse mask bbox for '{suffix}':\n{out}")
    return ",".join(m.group(i) for i in range(1, 5))


def parse_outside(compose_out):
    """Parse 'OUTSIDE-MASK changed_pixels=N' from compose_fairy stdout."""
    import re
    m = re.search(r"OUTSIDE-MASK changed_pixels=(\d+)", compose_out)
    return int(m.group(1)) if m else None


def parse_match(judge_out):
    """Extract the pairwise judge JSON object from mixed stdout/stderr (which may carry
    urllib3 warnings). Scans for the first balanced top-level {...} and parses it."""
    s = judge_out
    start = s.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(s)):
            c = s[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(s[start:i + 1])
                    except Exception:
                        break
        start = s.find("{", start + 1)
    return {}


def redraw_instance(args, src, ref, item, suffix, outdir):
    box = resolve_box(src, item, suffix, outdir)
    raw = outdir / f"{suffix}.raw.png"
    final = outdir / f"{suffix}.final.png"
    region = outdir / f"{suffix}.region.png"

    x0, y0, x1, y1 = box_tuple(box)
    result = {"suffix": suffix, "box": box}

    # ---- 1. redraw via falref_apply (image_urls=[region, ref, *extra]) with bounded retries
    fr = ["python3", str(SCRIPTS / "falref_apply.py"),
          "--src", str(src), "--crop", box, "--ref", str(ref), "--out", str(raw)]
    for r in args.extra_ref:
        fr += ["--ref", r]
    if args.prompt_file:
        fr += ["--prompt-file", args.prompt_file]
    elif args.prompt:
        fr += ["--prompt", args.prompt]

    ok = False
    last = ""
    for attempt in range(args.retries + 1):
        rc, out = run(fr)
        if rc == 0 and raw.exists():
            ok = True
            break
        last = out
    if not ok:
        result["error"] = f"falref_apply failed after {args.retries+1} tries: {last[-300:]}"
        result["gate_pass"] = False
        result["match"] = "ERROR"
        return result

    # ---- 1b. emit a crop-sized region for the sheet/judge (rescale raw -> crop box)
    Image.open(raw).convert("RGB").resize((x1 - x0, y1 - y0), Image.LANCZOS).save(region)

    # ---- 2. composite back, gate on outside-mask delta
    comp = ["python3", str(SCRIPTS / "compose_fairy.py"),
            "--orig", str(src), "--regen", str(raw), "--out", str(final),
            "--crop", box, "--mask", box, "--diffmask",
            "--diff-thresh", str(args.diff_thresh)]
    rc, cout = run(comp)
    outside = parse_outside(cout)
    result["outside_changed"] = outside
    result["gate_pass"] = (rc == 0 and outside is not None and outside <= args.gate)
    if not result["gate_pass"]:
        # gate is on the area OUTSIDE the instance box; diffmask should make it ~0.
        result["gate_note"] = cout.strip().splitlines()[-1] if cout.strip() else "compose failed"

    # ---- 3. consistency check: pairwise-judge region vs ref ("same character design")
    jud = ["python3", str(SCRIPTS / "judge.py"), "--mode", "pairwise",
           "--image", str(region), "--ref", str(ref),
           "--criterion", args.criterion]
    rc, jout = run(jud)
    verdict = parse_match(jout) if rc == 0 else {}
    # "match" = the judge can't reliably prefer one over the other => they look the same.
    # consistent==True means a clear winner across both orders (a DIFFERENCE is detectable);
    # winner=="tie" or consistent==False => indistinguishable => MATCH.
    if not verdict:
        result["match"] = "JUDGE_ERROR"
        result["judge_raw"] = jout[-300:]
    else:
        winner = verdict.get("winner")
        consistent = verdict.get("consistent")
        result["judge_winner"] = winner
        result["judge_consistent"] = consistent
        if winner == "tie" or consistent is False:
            result["match"] = "MATCH"      # indistinguishable from ref
        else:
            # a clear, order-stable difference exists; report which way it leans
            result["match"] = "DIFFERS"
            result["differs_toward"] = "ref" if winner == "B" else "redraw"
    result["files"] = {"raw": str(raw), "final": str(final), "region": str(region)}
    return result


def contact_sheet(ref, results, out_path, cols=3, cell_w=420):
    imgs = [("REF", ref)]
    for r in results:
        reg = r.get("files", {}).get("region")
        if reg and Path(reg).exists():
            imgs.append((f"{r['suffix']} [{r.get('match','?')}]", reg))
    n = len(imgs)
    cols = min(cols, n)
    rows = (n + cols - 1) // cols
    cell_h = 0
    thumbs = []
    for label, p in imgs:
        im = Image.open(p).convert("RGB")
        s = cell_w / im.width
        th = im.resize((cell_w, max(1, round(im.height * s))), Image.LANCZOS)
        thumbs.append((label, th))
        cell_h = max(cell_h, th.height)
    cell_h += 28  # label strip
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    except Exception:
        font = ImageFont.load_default()
    for i, (label, th) in enumerate(thumbs):
        cx = (i % cols) * cell_w
        cy = (i // cols) * cell_h
        draw.rectangle([cx, cy, cx + cell_w - 1, cy + 26], fill=(30, 30, 30))
        draw.text((cx + 6, cy + 4), label, fill=(255, 255, 255), font=font)
        sheet.paste(th, (cx, cy + 28))
    sheet.save(out_path)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--ref", required=True, help="canonical/approved instance (a crop)")
    ap.add_argument("--targets", required=True, help="JSON list (inline or @file)")
    ap.add_argument("--prompt")
    ap.add_argument("--prompt-file")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--extra-ref", action="append", default=[],
                    help="extra character reference(s) beyond --ref")
    ap.add_argument("--gate", type=int, default=0,
                    help="max OUTSIDE-MASK changed pixels allowed (diffmask should be ~0)")
    ap.add_argument("--diff-thresh", type=int, default=40)
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--criterion",
                    default="the SAME character/vehicle design and art style (shape, colors, line work)")
    a = ap.parse_args()

    src = Path(a.src)
    ref = Path(a.ref)
    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        raise SystemExit(f"src not found: {src}")
    if not ref.exists():
        raise SystemExit(f"ref not found: {ref}")

    targets = load_targets(a.targets)
    if not targets:
        raise SystemExit("no targets")

    results = []
    for i, item in enumerate(targets):
        suffix = item.get("out_suffix") or f"inst{i}"
        print(f"[consistency] === instance '{suffix}' ===", flush=True)
        r = redraw_instance(a, src, ref, item, suffix, outdir)
        results.append(r)
        print(f"[consistency]   gate_pass={r.get('gate_pass')} "
              f"outside_changed={r.get('outside_changed')} match={r.get('match')}", flush=True)

    sheet = outdir / "_consistency_sheet.png"
    contact_sheet(ref, results, sheet)

    n = len(results)
    matched = sum(1 for r in results if r.get("match") == "MATCH")
    gated = sum(1 for r in results if r.get("gate_pass"))
    summary = {
        "n_instances": n, "matched": matched, "gate_passed": gated,
        "set_consistent": matched == n and gated == n,
        "ref": str(ref), "src": str(src), "sheet": str(sheet),
        "instances": results,
    }
    (outdir / "_consistency.json").write_text(json.dumps(summary, indent=2))
    print(f"[consistency] SET: {matched}/{n} MATCH, {gated}/{n} gate-pass  "
          f"set_consistent={summary['set_consistent']}")
    print(f"[consistency] sheet -> {sheet}")
    print(f"[consistency] report -> {outdir / '_consistency.json'}")
    raise SystemExit(0 if summary["set_consistent"] else 2)


if __name__ == "__main__":
    main()
