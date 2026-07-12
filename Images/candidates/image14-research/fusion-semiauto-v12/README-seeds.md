# Semi-auto v12 — painting seeds for the next round

Pixel-auto BG removal is ill-posed on pale watercolor. This tool accepts
**sure FG / sure BG seeds**; everything else is solved by closed-form matting
+ algebraic paper unmatte.

## How to paint seeds

1. Open `14-semiauto-v12-seed-template.png` (or the source RGB) in Preview /
   Photoshop / Krita at **native x4 size** (do not rescale).
2. Paint on a **new layer**:
   - **Red** `(R≥160, G≤100, B≤100)` = sure **foreground** (keep pale wash).
   - **Blue** `(B≥160, R≤100, G≤100)` = sure **background** (paper / holes).
3. Export flat RGB PNG. Soft brushes OK; only saturated red/blue count.
4. Re-run:

```bash
python3 tasks/double-marine-bed-wrapper-batch/fusion_semiauto_v12b.py \
  --seeds /path/to/your-seeds.png --tag user1 --half-res
```

Optional: `--seeds-only` / `--no-bria` / `--edge-unknown N` / `--rim-kill N`.

## What auto seeds already do

- FG: chroma ≥ 16 or luma ≤ 195 + eroded BRIA (no grow by default).
- BG: border-connected pure paper + large enclosed pure-paper (≥80 px).
- Edge unknown band (~5 px) + rim-kill of near-white opaque boundary pixels.

Paint **only failures**: pale wash deleted → red; paper left opaque → blue.
