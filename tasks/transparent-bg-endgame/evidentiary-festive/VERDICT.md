# Evidentiary festive run — human verdict (2026-07-17)

Arbiter: user (Saar), viewing full-res finals in
`REVIEW/transparent-bg-endgame/evidentiary-festive/`.

## Verdict (verbatim)

> FINAL-preserve-mode.png has areas cut out of the actual illustration (holes),
> so it's not good. FINAL-destructive-mode.png looks perfect!

## What this resolves

1. **Accepted final:** `FINAL-destructive-mode.png`
   (= `20260717T062957Z-bf72fc/candidate_1/purged.png`, destructive
   `--no-green-art` purge of the frozen raw `20260717T062245Z-a9ee32/raw_1.png`).
2. **Gate status of the accepted final** (re-gated post-D1-patch,
   `regate-destructive-postpatch/battery.json`, ppi 260, physical_units:true):
   - All blocking gates PASS (D2–D8).
   - D1 = REVIEW only: `H_L=0.0`, `H_key=0.0`, `weighted_p95_delta_l=0.0`;
     trigger is a single 531px / 5.07mm² component — sub-visible ring class,
     human-judgment tier (same class as round-7 ppi260 finals). **Resolved by
     this verdict.**
3. **The 29,692 recolored sage/teal px (mean Δ11.8)** measured in DIAGNOSIS.md
   finding 3 are below the user's perceptual acceptance threshold at delivery
   scale. Real palette drift, accepted by the arbiter. Calibration anchor for
   the future palette-preservation gate (patch C): mean ΔE ≈ 12 on protected
   green art = user-accepted on this subject.
4. **Preserve-green mode = REJECTED / negative result** on this class:
   its erosion deleted visible structure (holly cluster, 4,048px region,
   `holly-preserve-mode-before-after.png`), D1 real halo H_L=19.7,
   min_anchor_component_recall=0.758. Structural damage is worse than
   sub-perceptual recoloring.

## Routing consequence (green-art subjects, C-green v2)

When the subject contains legitimate green art:
- Run BOTH purge modes on the same frozen raw (cheap — purge is local).
- Gate both; expect destructive to risk recolor, preserve to risk erosion.
- Human picks. Destructive mode won here; do NOT hard-code that — the recolor
  magnitude is subject-dependent.
- Never ship preserve-mode output without checking anchor-component recall.

Claim ceiling: "passed calibrated print gates + human-approved on one hostile
green-art subject." NOT "green-art subjects validated."
