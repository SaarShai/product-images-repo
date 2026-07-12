# comfyui — LayerDiffuse (T1) + BiRefNet-HR (T2) capability stand-up

Review folder (absolute path):
`/Users/za/Documents/product images repo/REVIEW/marine-bg-complete/comfyui/`

ComfyUI install reused at `/Users/za/ComfyUI` (already present from a prior
session; not reinstalled). Full reproduce steps:
`/Users/za/Documents/product images repo/tasks/double-marine-bed-wrapper-batch/comfyui/REPRODUCE.md`.
Metrics: `/Users/za/Documents/product images repo/tasks/double-marine-bed-wrapper-batch/comfyui/metrics.json`.

## T1 — LayerDiffuse native transparent generation (SDXL, Attention Injection)

Two prompts tried, both real end-to-end RGBA (`ComfyUI-layerdiffuse` +
`LayeredDiffusionDecode` + core `InvertMask`/`JoinImageWithAlpha`), **but
alpha does not separate foreground from background in either case** —
verdict is: capability wired up and executing, but the transparency itself
is not usable yet from this model/config.

- [t1-layerdiffuse-sdxl-attn-fullscene.png](t1-layerdiffuse-sdxl-attn-fullscene.png)
  — full-scene marine watercolor prompt (sailboat, waves, seashells,
  starfish). 99.66% of pixels are alpha>200 (near-opaque); background
  renders as opaque white, not transparent (only ~65 px out of ~1.01M are
  alpha<20).
- [t1-layerdiffuse-sdxl-attn-turtle-single.png](t1-layerdiffuse-sdxl-attn-turtle-single.png)
  — single-object retest per coordinator ask ("does alpha track ONE
  subject?"). Answer: **no** — worse than the full-scene case: alpha ranges
  145–255 with a mean of 254.86; **zero** pixels are below alpha 20.
  Background is not tracked at all; this rules out "prompt was too busy" as
  the cause.

Cross-lane note: a sibling lane ran the same custom node on the same core
and got the *opposite* failure mode on a full-scene prompt (81% transparent,
opaque only in corner blotches). Between the two lanes we've now seen both
"almost all opaque" and "almost all transparent" from
`ComfyUI-layerdiffuse` + SDXL Attention Injection on this core — the
takeaway is the ATTN path is **unreliable on ComfyUI 0.25.0**, not that one
particular prompt/seed is unlucky.

A follow-up probe with the heavier `layer_xl_transparent_conv.safetensors`
("Conv Injection", ~3.6GB) was started to see whether the non-attention
model (the one LayerDiffuse's authors documented as visually stronger) fixes
alpha separation; see the builder report for whether it completed and its
result.

## T2 — BiRefNet-HR background removal (comparison baseline), image14

- [t2-birefnet-hr-image14.png](t2-birefnet-hr-image14.png) — ComfyUI **core**
  native background-removal loader (`LoadBackgroundRemovalModel` +
  `RemoveBackground`, model type `birefnet`), no third-party node pack
  needed. Checkpoint: `ZhengPeng7/BiRefNet_HR/model.safetensors`.

Frozen gate (`tasks/double-marine-bed-wrapper-batch/bg-benchmark/verify_bg_solution.py`,
read-only, never edited):

```
image14: FAIL machine_pass=false
  FAIL rgb_reconstruction: straight RGBA does not reconstruct the pre-removal RGB over paper
  FAIL white_edge_contamination: edge probe edge-fish-translucent-fin contains too many paper-colored boundary pixels
  FAIL white_edge_contamination: edge probe edge-known-fringe-pink contains too many paper-colored boundary pixels
  FAIL white_edge_contamination: edge probe edge-right-pale-seaweed contains too many paper-colored boundary pixels
```

All `sure_foreground` and `sure_background` guard probes pass (correct
subject coverage, no leaked exterior/enclosed background) — BiRefNet-HR gets
the coarse cutout right. It fails on **edge quality**: RGB reconstruction MAE
2.667 (limit 1.5) and a bright paper-colored halo on 3 translucent-watercolor
edge probes (fish fin, pink fringe, pale seaweed — white_fraction 0.62–0.73
vs a 0.25 limit). This matches the existing project lesson (wiki:
"White-key beats birefnet (flat art)") — ML matting leaves an edge halo on
flat watercolor-on-white art; `scripts/white_key.py` (flood-fill) is the
gate-clean approach for this asset class. BiRefNet-HR is confirmed here as a
legitimate general-purpose comparison baseline, not a drop-in replacement.

Full gate JSON:
`/Users/za/Documents/product images repo/tasks/double-marine-bed-wrapper-batch/comfyui/gate_report_birefnet_hr.json`.

## Drive candidates

`.../double Marine Bed Wrapper/images/Images/candidates/comfyui-v1/`:
- `layerdiffuse-sdxl-attn-fullscene/marine_layerdiffuse_sdxl_attn_fullscene.png`
- `layerdiffuse-sdxl-attn-turtle-single/marine_layerdiffuse_sdxl_attn_turtle.png`
- `birefnet-hr/image14_birefnet_hr.png`
