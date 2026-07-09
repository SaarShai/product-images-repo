# Upscale blur diagnosis — best option 2-05 / 2-06

## Root cause (verified)

1. **Source is already soft inside.** `best option 2-05.png` is only **224×946**.
   Edge gradients are strong (~100+), but interior cookie texture is soft
   (local variance drops sharply a few px inside the silhouette). Upscalers
   cannot invent true high-frequency cookie crumb from mush — they either
   smooth it further or invent plastic grain.

2. **Hard black silhouette confuses denoise.** RGB-on-black with a dark fringe
   (~17% of fringe pixels lum<80) makes Real-ESRGAN treat the object as a
   cutout on void. It over-protects the outer icing edge and **over-smooths
   the low-contrast interior** (classic "sharp outline, blurry fill").

3. **Mixed edge types in one object.** Hard AA silhouette + soft painted
   icing-to-cookie transitions + soft sugar pearls. One global sharpen/upscale
   pass cannot treat all three correctly → patchy blur.

4. **Photoshop provenance.** XMP shows Adobe Photoshop 27.9 export; not a
   native high-res render. Softness is baked into the pixels.

## Fix that works

- Put the object on a **neutral cream paper** before ML upscale (not black).
- Prefer a **detail-rebuilding** upscaler (fal clarity) over pure ESRGAN when
  interiors are soft.
- Optional: adaptive sharpen after ESRGAN for edge-only boost.

## Method ranking on 2-05 mid-cookie metrics

| Method | cookie♯ | cookie var | notes |
|--------|---------|------------|-------|
| C fal clarity (cream) | **8.1** | **267** | best interior rebuild |
| A ESRGAN x4plus black | 5.1 | 164 | sharp rim, soft fill |
| D Recraft Crisp | 4.9 | 158 | clean edges, milder texture |
| E ESRGAN cream+adaptsharp | 4.8 | 139 | better than A on edges |
| B ESRGAN anime cream | 4.2 | 164 | oversmooths cookie |

## Magenta series — approved detail recipes (2026-07-09)

### Stage A — 8× cream rebuild (soft sources)
1. Magenta/transparent → cream `(252,249,240)`
2. Downsample short side ≈ **240**
3. Clarity **4×** creat **0.25** res **0.85** steps 22
4. Clarity **2×** creat **0.4** res **0.75** steps 24 → cream final

### Stage B — detail C (sharpen/rebuild, layout-faithful)
- Source: Stage A 8× cream
- Clarity **1.5×** creat **0.5** res **0.7** steps 24
- Tall panels (>~32 MP at 1.5×): split vertical halves with ~12% overlap, run C, linear-blend stitch
- Use when the user already approved detail C on a sample (e.g. `detail06-C-clarity-1.5-c0.5.png`).
  Not the universal batch default — Stage A 8× alone was later approved for some series
  (e.g. downloads `img62-clarity-8x.png`).

### Production default (safe path)
- **Default batch:** Stage A 8× cream rebuild.
- **Add Stage B detail C** only where that sample was already approved, or the user
  explicitly asks for the same detail pass.
- Do **not** default the batch to Stage C.

### Stage C — candy-creative (PROBE ONLY — not batch-safe)
Not sharpen — invent confectionery micro-detail while keeping layout.
- Source: Stage A 8× cream (**not** Stage B detailC)
- Clarity **1.25×** creat **0.65** res **0.55** steps 28
- Prompt must name materials: translucent gumdrop facets, star-tip icing ridges,
  peppermint stripes, sugar-crystal dusting, pearl speculars, jewel depth
- Neg must forbid: flat matte blobs, plain smooth circles, featureless candy
- At 1.25×, tall 1920×~9k panels stay under fal’s 32 MP cap (no tiling needed)
- **Probe-proven only on magenta-06** (user said “amazing” once). **Not batch-proven.**

#### WARNING — Stage C artifact gate (2026-07-09 correction)
**Trigger / symptom:** magenta fringes, neon-green blobs, or bright artifact speckles
after a high-creativity clarity “candy detail” pass.

- Stage C looked great on one probe, then the rolled batch
  (`detailNN-candy-creative-c0.65.png` / `magenta-NN-candy-creative.png`) was
  **rejected** for magenta and bright green artifacts.
- Treat Stage C as **probe-only**. Require **explicit per-image re-approval** before
  any further creative batch.
- **Do not heal** failed candy-creative outputs (palette locks / speckle scrubbing
  still failed). Restart from the **original magenta/transparent source** → Stage A
  → (optional approved Stage B).
- Prefer the safe path above for production batches unless the user re-approves
  creative on a fresh probe.
