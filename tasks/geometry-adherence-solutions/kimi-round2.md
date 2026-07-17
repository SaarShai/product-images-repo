# Round-2 consult — composition map (independent answer)

Inspected: RESULTS-stageA.md + metrics-stageA.json, all 4 gens, outset-c1 raw.png,
control_canny.png, svg_to_controlmap.py, build_assets.py, gen_stage_a.py.

## Q1 — Source of interior lineart: option (a), trace outset-c1. Decisively.

(b) procedural boxes will read as assembled/vector and throws away the one
proven asset we have: outset-c1's composition PASSED review. (c) depth/soft-edge
is too weak — Stage A just proved weak conditioning collapses to washes.

Mechanism (verified against ground truth):
1. outset-c1 is 768x1376 (aspect 0.558); our body is 640x1544 (0.4145). Register
   corner-to-corner with per-axis rescale (sx=0.833, sy=1.122). Evidence this is
   correct: the fold slab edge sits at ~0.331 of height in outset-c1 vs ~0.340 in
   our canvas — the compositions are co-registered full-body renders, and the
   anisotropy rightly slims the castle into our narrower panel.
2. Canny-extract at 640-wide working res, thresholds tuned to keep structure
   (tower silhouettes, roof apexes, window rows, door arch, birds) and drop
   texture (stone joints, paper grain).
3. AND the trace with paintable_P1 dilated -2px: outset-c1 painted over holes
   3-5 and bled 6633px outside silhouette, so its strokes MUST be clipped.
   This erases by construction all strokes in holes/socket/keep-clear.
4. Re-add authoritative SVG strokes (contour, cutouts, socket arch, folds) via
   the existing draw_control_lines — geometry stays exact, never traced.

Overfitting: yes, it is, and it does not matter. This experiment's question is
"can the inpaint+CN+IP+composite architecture deliver rich content inside exact
geometry?" The frontier composition is the strongest test fixture, not the
product. Novelty is a later-round variable once the pipeline is proven.

Risk: traced door in the dome section + empty socket zone (socket is unpainted
init-fill by design, Stage C composites the real door) — both acceptable.

## Q2 — Lower the conditioning. Concrete numbers.

Seed-21 gens ALREADY show embossed dotted seam lines from the SPARSE map at
0.7/0.8. A dense map multiplies emboss area ~10x. And boundary enforcement is
now redundant: the hard composite already guarantees 0 outside px / 0% hole
paint (measured, all 4 runs).

- controlnet_conditioning_scale: 0.55
- control_guidance_end: 0.65 (last 35% of denoise free to soften lines into wash)
- interior traced strokes: 2px; boundary/arch strokes: keep 4px
- keep cg_start 0.0

If emboss persists at 0.55, the round-3 lever is two ControlNets (geometry
canny 0.8 + composition lineart 0.45), not a further global cut.

## Q3 — No other change. Explicitly.

The prompt already says "fairytale princess castle... tall narrow vertical
composition" and seed 7 DID produce turrets — the prompt works when given a
scaffold. Keep prompt verbatim, IP 0.55 style-layer-only, LoRA 0.75, guidance
5.5. One variable: the composition-map package (new map + its required
conditioning retune, which is inseparable from the map itself).

## Q4 — Confirm P1-only x seeds 7,21 = 2 gens.

P2's hole data is uninterpretable until the Stage-C punch exists (st2 painted
100% by design — nothing new to measure). The composition question is
arm-independent. Seeds 7/21 bracket the observed content variance (best vs
worst). ~4 min of compute for a decisive visual verdict. Defer P2.
