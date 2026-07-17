# Advisor consult 4 — round-2 composition map (Stage-A geometry PASSED, content collapsed)

Context: experiment-1 Stage A ran per the frozen card (+2 pre-run amendments).
Measured results, all 4 gens (640x1544, ~107s each, MPS):
- outside-silhouette painted px: 0 on all 4
- P1 hole paint: 0.0% (by construction); coverage 99.96-99.98%
- P2: holes painted over as designed
- socket arch respected, model painted a frame around it (arch outline in
  control lineart worked)
- NO NaN/black; VAE tint on kept regions confirmed (~68/255 drift — Stage-C
  registration detection being recalibrated in a parallel lane)

THE FAILURE: content/composition. The panels are mostly abstract watercolor
washes — at best two small turrets near the top (best candidate: A-P2-s7).
No castle body, no windows, no architectural mass. Style-wise the washes are
watercolor-ish but far below the frontier bar (frozen outset-c1 had a full
castle with spires, bird, windows — geometry failed but style/content PASSED).

Diagnosis (pre-registered decision rule, confirmed): the control lineart
carried ONLY contour + cutouts + arch outline. The mask prevents overflow but
nothing conditions interior composition. Round 2 must fix the composition map.

Questions:
1. SOURCE of interior composition lineart. Candidate options:
   a. Canny/line-extract the frozen frontier gen (outset-c1 raw.png, style
      PASSED, geometry failed), REGISTER it into our 640x1544 body (affine
      fit to silhouette), then erase all strokes inside holes/socket/keep-clear
      + re-add our exact contour/cutout/arch strokes. Frontier composition,
      exact geometry.
   b. Procedural/synthetic lineart (draw tower/roof boxes from a layout plan).
   c. Depth or soft-edge map from outset-c1 instead of canny (weaker edges,
      more compositional freedom).
   Pick one (or a precise hybrid), with mechanism + risk. Consider: does
   tracing outset-c1 constitute overfitting to one composition, and does that
   matter for THIS experiment (whose question is architecture viability, not
   novelty)?
2. Control params for a DENSE interior lineart: keep controlnet scale 0.7 +
   end 0.8, or lower interior stroke weight / scale to avoid the "embossed
   canny lines in the wash" failure? Concrete numbers.
3. Should anything ELSE change in round 2 (prompt richness, IP routing/scale
   0.55 style-layer-only, LoRA 0.75, guidance 5.5)? Bias to ONE variable
   (composition map) for discriminability — but if you judge a second change
   near-certain-required (e.g. the minimal prompt cannot describe a castle),
   say so explicitly and give the exact new value.
4. Confirm or amend the round-2 matrix: P1-only (P2 deferred until Stage C
   punch is fixed) x seeds 7,21 with the new map = 2 gens? Or keep both arms?

Answer decisively, <= 500 words.
