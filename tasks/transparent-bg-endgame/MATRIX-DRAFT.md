# Experiment matrix — draft v0 (pre-advisor; merge with Sol reply before launch)

Subjects (held constant across all arms; style ref = existing marine refs, held-out per memory):
- S1 chunky coral cluster (easy case)
- S2 thin-feature stressor: sea fan / fine foliage, KEYABLE-FINE module active (hard case; targets R4/nets/hair)

## Gen-source arms (n=2 seeds each)
| Arm | Source | Key step | Notes |
|---|---|---|---|
| A1 | gpt-image-1 API `background=transparent` | none (native alpha) | + edge-hygiene + anti-aura blocks (verbatim from skill) |
| A2 | Flux.2 `transparent_bg` (BFL/fal) | none | NEW — never probed; schema-check first |
| G1 | gpt-image-2 async on flat #00FF00 | chroma_key.py DE_OPAQUE=11 | verified default, baseline |
| W1 | R4 white-bg recipe | white_key --reopen-interior → dehalo_edge | current user-verified route, baseline |
| H1 | R4 + NON-AA edge block, white bg | white_key → dehalo_edge | "silhouette meets background with zero blending; no anti-aliasing; no soft transition band; boundary is a single crisp hard step" (factual phrasing — semantic framings like 'die-cut sticker' proven harmful) |
| H2 | same NON-AA block, green bg | chroma_key | crosses hard-edge gen with global key |
| H3 | R4 + contour-contrast edge: every silhouette boundary carries a 1-2px darker ink contour of the local fill | white_key → dehalo_edge | edge type: outlined |
| H4 | R4 + tinted-margin edge: outermost 2px of every shape at full pigment saturation (no pale rim) | white_key | edge type: saturated rim, anti-halo-by-construction |

## Post-process factors (crossed on the 2-3 winning source arms only)
- binarize alpha: pre-upscale vs post-upscale vs none
- erode before binarize: 0 / 1 / 2 px
- dehalo_edge: on / off
- known-bg unmultiply decontamination: on / off (white and green variants)
- upscale: chroma_key_upscale (green) or alpha_aware split (others), x4

## Gates (every candidate)
scripts/gates/gate_battery.py --profile print (D1-D8) + board on white/gray/black/#111/magenta/panel-color.
Human inbox: REVIEW/transparent-bg-endgame/ with fullres/ + boards + battery.json per candidate.

## Decision metrics per defect class
halo: D1 edge-band 99pct L* over black; fringe: D2 soft%/perimeter; pockets: D3 count;
aura: D4; holes: D5 recall stratified by thinness (S2 decisive); spill: D6; crop: D7.
User verdict = final arbiter (metric dominance ≠ preference — banked lesson).

## Run plan
1. Schema-probe A2 (flux.2 transparent param name/cost) before spending.
2. One candidate per arm → battery → SHOW USER EARLY (memory: show-results-early-gate) → then n=2 + post-factor cross on winners.
3. All gens via scripts/subgen.py or direct API per arm; image-2 = async background job (memory).
