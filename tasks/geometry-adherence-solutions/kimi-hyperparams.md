# Hyperparameter consult — concrete run parameters (independent advisor)

Scope: the authorized ~6-gen experiment on the frozen princess-n02 panel,
SDXL-inpaint + xinsir canny CN + IP-Adapter-plus + watercolor LoRA, Apple
Silicon MPS, .venv-gen (torch 2.12.1 / diffusers 0.38). Every number below is
a single value, not a range. Verified against `scripts/controlnet_sdxl_gen.py`,
`scripts/localgen.py`, `scripts/measure_sdxl_cn.py`, and by re-running
`svg_classify.py` on the frozen SVG (roles re-derived, not assumed).

## Ground truth used (re-measured, not from the brief)

`svg_classify.py --json` on the frozen template gives:

- outer_contour `st5`: 163.32,179.08 → 1687.54,4092.71
- paintable_region (front subpanel): 103.38,1538.46 → 1747.48,4160.76
- cutouts: `st1` window (1644.1×654.0, hfrac 0.164), two `st4` side slivers
  (28.5×769.2, hfrac 0.193), two `st2` bars (734.6×86.0, hfrac 0.022)
- keep-clear (NOT handled by the gen script): `st3` fold band 97.6×3040.3,
  `st0` socket rect 507.0×94.2 at bottom

Default (no `--bbox`) body bounds = 103.38,179.08 → 1747.48,4160.76 =
**1644.10 × 3981.68 SVG units, aspect W/H = 0.4129 (H/W = 2.422)**.

All five cutouts have hfrac < 0.45, so legacy mode (no `--full-bleed`) carves
all of them — correct here; this is a genuine-openings panel, not a door
facade. Do NOT pass `--full-bleed`.

## 1. Resolution strategy: 640×1544, portrait, no rotation

- **Working size: W=640, H=1544** (`--width 640` in controlnet_sdxl_gen.py;
  H = round8(640 × 3981.68/1644.10) = round8(1549.97) = 1544). 0.988 Mpx,
  aspect error after round8 = 0.4 % (sx vs sy), imperceptible and harmless to
  the IoU gate (measure_sdxl_cn.py uses the same W/H mapping).
- This sits 8 px off the native SDXL training bucket 640×1536, so composition
  behavior is bucket-native. Do not exceed ~1.0 Mpx (704×1704 = 1.20 Mpx is
  over the SDXL quality cliff and doubles MPS pressure for zero gate benefit).
- **Orientation: PORTRAIT, gen the panel exactly as the SVG describes it.**
  The brief's premise "panel is wider than tall in SVG user units" is stale:
  the frozen report and a fresh parse both show viewBox 1874.73×4213.29 and a
  body 2.42× taller than wide. No rotation is needed. Even in principle
  rotation buys nothing: SDXL's extreme buckets are symmetric (1536×640 vs
  640×1536), so a landscape gen of this panel would use the same training
  marginal as portrait — while adding a lossy rotate-back step that can
  mis-register the Stage-C socket composite. Portrait, direct.
- Production-scale pixels are Stage C's problem (upscale art before socket
  paste, never after) — do not chase resolution at gen time.

## 2. Conditioning scales (Stage A, both hole-policy arms)

| knob | value | why |
|---|---|---|
| controlnet_conditioning_scale | **0.7** | The 0.969-IoU precedent ran ~0.6 without IP+LoRA fighting it. With two style injectors on, structure needs +0.1 to hold the window arch and side slivers. Above 0.8 the canny lines start embossing into the wash. |
| control_guidance_start / end | **0.0 / 0.8** | Silhouette edges are committed by ~60–70 % of denoise; releasing the CN for the last 20 % of steps lets the watercolor texture develop without moving any edge the gate measures. (Supported by the inpaint pipeline in diffusers 0.38.) |
| ip-scale (plus variant) | **0.5** | Total, with both refs passed. Plus is copy-prone above ~0.6; below 0.4 the refs stop influencing palette. 0.5 is the measured localgen default and the right anchor. |
| lora-scale (fused) | **0.8** | LoRA carries the *medium* (watercolor), IP carries *palette/mood* from the refs. At the localgen default 0.9 the LoRA overpowers IP and you get generic watercolor instead of princess-ref watercolor. |
| guidance (CFG) | **5.5** | With CN+IP+LoRA the text prompt should be the weakest conditioner; 5.5 avoids the waxy over-saturated look 7+ gives on SDXL-inpainting-0.1 while keeping the negative prompt live. |
| steps | **30** | Inpaint + CN converges by ~28; more steps only cost MPS minutes. |
| strength (Stage A inpaint) | **1.0** | Init image is pure white; anything <1.0 leaves white contamination inside the body that reads as unpainted region at the coverage gate. |
| mask feather | **0 px** | Hard-geometry intent. The mask is the rasterized SVG polygon; feathering (localgen's default 24 is for photo repair boxes) blurs the silhouette and produces a soft grey rim that the white-composite then guillotines into a visible halo. 0. |
| control stroke | **3 px** bold / **1 px** faint | Script default 4 px is calibrated for --width 1024; scale by 640/1024 → 2.5 → 3. |
| seeds | **7** and **21** | 7 is the script default (continuity with precedent); 21 is the second arm seed. |

## 3. IP-Adapter with two refs: pass BOTH as a list, scale 0.5

Pass `[ref1, ref2]` as a list to `ip_adapter_image` (diffusers concatenates the
16 plus-tokens per image → 32 tokens; the adapter averages them). This is the
intended multi-ref path and transfers palette/texture — what you want — while
0.5 keeps it below the layout-copying threshold.

- **Do NOT use a combined contact sheet.** The ViT-H encoder will treat the
  grid as one composition; sheet seams and the doubled side-by-side layout
  leak into the panel as a bipartite composition. Worst of the three options.
- **Do NOT pre-stretch refs to panel aspect.** localgen.py currently does
  `ip_image.resize((W,H))` — at 640×1544 that vertically stretches the ref
  2.4× and corrupts the style tokens. Center-crop each ref to square and pass
  at native resolution (the encoder handles it). This is a one-line fix and
  worth it.
- Fallback if any layout copying (castle footprint mirroring ref 01) appears
  in the first two gens: drop to the single anchor ref (`princess style 01`)
  at 0.5, don't lower scale below 0.4 — a weaker-but-mixed signal is worse
  than a clean single-anchor one.

## 4. Stage B img2img: same checkpoint, same pipeline, everything stays ON

- **Same checkpoint** (sdxl-inpainting-0.1) through the *same*
  StableDiffusionXLControlNetInpaintPipeline, `image` = Stage-A output,
  `mask_image` = the same paint mask used in Stage A. Do not switch to plain
  SDXL-base img2img+CN: the inpaint UNet is fine at partial denoise when the
  mask is full-coverage of the region, you keep kept-regions pinned, and you
  avoid a second pipeline load on MPS.
- **Keep CN ON at 0.7 (end 0.8), IP ON at 0.5, LoRA ON at 0.8**, same
  prompt/negative, same seed. Stage B exists to lift style; the CN at 0.7 is
  precisely the anti-drift lock that makes the ≥0.97 pre-cleanup silhouette
  gate reachable at denoise 0.5. Dropping IP in Stage B would drift palette
  away from the refs — the exact failure Stage B is meant to fix.
- **Denoise pair confirmed: 0.35 and 0.5.** Prediction: 0.35 passes the drift
  gate and is the realistic ship on this stack; 0.5 is the informative arm —
  expect it to fail worst_corner_fill/opening_fill on the window arch first.
  Pre-registered rule stands: 0.5 fails → ship 0.35 if it gates green → else
  ship Stage A. That is a staging result, not an engine verdict.

## 5. MPS / diffusers-0.38 defensive settings

- **Weights fp16 (variant fp16), VAE decode in fp32.** controlnet_sdxl_gen.py
  defaults `--dtype float32` ("MPS-safe") — that doubles unified-memory
  pressure with CN+IP+LoRA loaded and buys nothing for the UNet. The actual
  fp16/MPS failure is in the *VAE decoder* (NaN/black tiles, and the
  grey-tinted kept regions the script already documents). Fix at the right
  layer: fp16 everywhere + `pipe.vae.to(torch.float32)` before generation.
  Keep the hard white composite (`--no-composite` OFF) regardless — it is the
  holes-clear guarantee, not a workaround.
- **attention_slicing ON, vae_slicing ON, vae_tiling OFF.** At 0.988 Mpx
  tiling adds decode seams for no memory need. Enable tiling only if a later
  Stage-C upscale pass OOMs, never for Stage A/B gen.
- **Generator on CPU** (`torch.Generator(device="cpu")`, both scripts already
  do this) — MPS generators are nondeterministic; seeds 7/21 must be
  reproducible across arms.
- **`PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0`** in the env. Without it MPS aborts
  around the ~65–75 % unified-memory watermark mid-denoise once the ViT-H
  encoder is resident; with it you get graceful paging instead of a hard
  `MPSAllocator` crash.
- **No xformers** (not on MPS); default SDPA attention in 0.38 is correct.
- **Load order:** LoRA → `fuse_lora(lora_scale=0.8)` → `load_ip_adapter(...)`
  → `set_ip_adapter_scale(0.5)`. localgen.py already does this order; keep it
  and keep the LoRA fused at 0.8 for ALL arms (fusing is not cleanly
  reversible mid-session; scale consistency across arms matters more than the
  convenience of `unfuse_lora`).
- If a black/grey canvas appears: suspect order is (1) VAE dtype, (2) ViT-H
  encoder dtype — not the UNet, not the CN.

## 6. Prompt text (minimal, content+style only — no geometry/production words)

Positive (use verbatim for all Stage-A and Stage-B gens):

> watercolor children's book illustration of a fairytale princess castle,
> soft pastel washes on textured paper, gentle ink outlines, tall narrow
> vertical composition, airy, delicate, hand-painted

Negative (extends the repo default with the two watercolor-specific
failure modes — heavy contour ink and vector-flat fills):

> photo, realistic, 3d render, glossy, text, words, signage, watermark,
> frame, border, clutter, people, oversaturated, heavy black outlines,
> vector, flat color blocks

Rationale: at CFG 5.5 the prompt is the weakest conditioner by design; its
only jobs are (a) declare the medium so the LoRA doesn't have to carry it
alone, (b) declare the vertical composition so the IP refs' landscape
compositions don't pull sideways, (c) keep the negative list killing the
frame/border/vector modes that fight a watercolor panel. Anything about
contours, cutouts, holes, safe areas, or "fit inside" is forbidden — geometry
comes only from the control image and mask.

## Integration notes (gaps an executor will hit, not hyperparams)

- **Entry point must be localgen.py-shaped.** controlnet_sdxl_gen.py has no
  IP-Adapter/LoRA flags; localgen.py has the full stack but builds masks only
  from boxes. Precompute the control map + paint mask at 640×1544 with
  controlnet_sdxl_gen.py's renderer (`--save-debug` path) and feed localgen
  `--mask mask.png --control-image control.png --size 640x1544 --feather 0`.
- **localgen.py lacks the hard white composite.** For A-P1 ("violations
  impossible by construction") that composite is the construction. Either add
  the 4-line composite from controlnet_sdxl_gen.py or accept that hole paint
  is cleaned at Stage C and measure it honestly in the gate.
- **A-P2 mechanics:** paint mask = body only (holes NOT subtracted), control
  map unchanged (holes still bold lineart so composition routes around them),
  composite still pins outside-contour only. One-line change (`paint =
  body_m`). All conditioning numbers above are identical across arms — that is
  what makes the arm comparison discriminating.
- **st3 fold band + st0 socket** are keep-clear, not holes: they must NOT go
  into the inpaint mask (painting over them is correct). They are enforced by
  Stage-0 lineart routing and the new element-vs-cutout clearance gate, not
  by generation parameters.
