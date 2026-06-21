# L-utils: two small image utilities (impl + test results)

Two independent, no-GPU utilities. Both run in the existing **`.venv-gen`** venv
(`./.venv-gen/bin/python`; PIL 12.2, numpy 2.4). Only new dependency:
`imagehash==4.3.2` (light; pulled pywavelets + scipy), installed via
`VIRTUAL_ENV=$PWD/.venv-gen uv pip install imagehash`.

## (1) style_packet.py  — PASS

Path: `/Users/za/Documents/product images repo/scripts/style_packet.py`

Auto-extracts N varied, content-rich style-reference crops from a finished
illustration (LAW: reference beats prose). Grid-samples fixed windows, scores
each by **edge density + colour variance**, drops near-white (coverage floor)
and `--avoid` boxes, then greedily keeps the top-N while enforcing spatial
spread (IoU cap). Saves `crop_1..N.png` + `contact-sheet.png`.

CLI: `--image IMG --out-dir DIR [--n 6] [--avoid x0,y0,x1,y1 ...]
[--crop-frac 0.28] [--min-coverage 0.45] [--max-overlap 0.30]`

### TEST
Command:
```
./.venv-gen/bin/python scripts/style_packet.py \
  --image tasks/nyc-taxi/src/nyc-hires.png --out-dir tasks/improve/style-packet-test --n 6
```
Output: `image=nyc-hires.png size=4192x3848 crop=1077px candidates=39 kept=6/6`

6 crops saved, all non-empty (844KB–1.44MB each), spatially spread:

| crop | bbox (x0,y0,x1,y1) | size | interest |
|------|--------------------|------|----------|
| crop_1 | (538,1614,1615,2691)  | 1077x1077 | 0.243 |
| crop_2 | (538,2690,1615,3767)  | 1077x1077 | 0.243 |
| crop_3 | (2690,1614,3767,2691) | 1077x1077 | 0.242 |
| crop_4 | (1076,2152,2153,3229) | 1077x1077 | 0.242 |
| crop_5 | (1614,1614,2691,2691) | 1077x1077 | 0.238 |
| crop_6 | (1614,2690,2691,3767) | 1077x1077 | 0.236 |

**Eyeballed `contact-sheet.png` (Read):** all 6 are colourful illustrated NYC
buildings + yellow taxis (watercolour/ink line-art style) — in-style art crops,
NOT blank sky. crop_1 = Flatiron + Brooklyn Bridge + row houses.

`--avoid` verified: excluding top-left quadrant (`--avoid 0,0,2096,1924`)
produced 4 crops none of which overlap that box.

## (2) dup_prefilter.py  — PASS

Path: `/Users/za/Documents/product images repo/scripts/dup_prefilter.py`

Cheap near-dupe detector to prune candidate sets before the costly VLM pairwise
judge. Perceptual hash (`imagehash.phash`) per image, union-find clusters any
pair with Hamming distance <= `--threshold`, emits one keeper (first in input
order) per cluster + the deduped list.

CLI: `--images a.png b.png ... [--threshold 5] [--hash phash|ahash|dhash]
[--hash-size 16]`

### TEST
Command:
```
cp tasks/nyc-taxi/work/L2_ctx.png /tmp/L2_ctx_copy.png
./.venv-gen/bin/python scripts/dup_prefilter.py --images \
  tasks/nyc-taxi/work/L2_ctx.png /tmp/L2_ctx_copy.png tasks/nyc-taxi/work/L2_erased.png
```
Result (`hash=phash size=16 threshold=5 images=3 clusters=2`):
```
L2_ctx.png <-> L2_ctx_copy.png: 0   DUP
L2_ctx.png <-> L2_erased.png:   32
cluster 1 (near-dupes): [L2_ctx.png, L2_ctx_copy.png]  -> keep L2_ctx.png
cluster 2 (unique):     [L2_erased.png]                -> keep L2_erased.png
deduped: L2_ctx.png, L2_erased.png   (kept 2 of 3)
```
The two identical files cluster (distance 0); the erased variant stays separate
(distance 32). Required behaviour met.

**Calibration note (load-bearing):** the imagehash default `hash_size=8` is too
coarse here — L2_erased differs from L2_ctx only by erased "TAXI" text + a door
window, which an 8x8 DCT pHash collapses to distance **4** (< threshold 5 →
wrongly merged). Bumped the **default to `hash_size=16`**: identical copies stay
at 0, the local-edit pair jumps to 32, so the two are cleanly separated out of
the box. (Confirmed visually: the only difference between L2_ctx and L2_erased
is the removed text/window on the otherwise-identical taxi scene.)

## Notes
- No other scripts modified. Both utils kept simple (no extra knobs beyond what
  the CLI spec asked for).
- Test artifacts: `tasks/improve/style-packet-test/` (crops + contact sheet).
