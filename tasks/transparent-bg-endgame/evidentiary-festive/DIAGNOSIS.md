# Evidentiary festive run — diagnosis (2026-07-16)

Run: 20260717T062245Z-a9ee32 (phase 1) → 20260717T062957Z-bf72fc (phase 2, FAIL exit 2).
Contract: EVIDENTIARY-RUN-festive.md. Frozen artifacts in the run dirs; no rescue applied.

## Findings

1. **User-seen green edge pixels (pre-purge) were removed by the purge.** Post-purge,
   two independent hue scans find 0 greenish edge-band pixels. The pipeline's core
   claim held on a new subject class.
2. **D1 FAIL is partially spurious: `h_key` pull metric false-positives on
   warm-yellow art.** Worst offenders are gold icing edge gradients (pull ≥0.5, zero
   visible green). Yellow (G≈R) gradients read as movement toward key-green. Gap:
   `h_key` needs a green-sector hue condition. Evidence:
   `REVIEW/transparent-bg-endgame/evidentiary-festive/FAIL-keypull-*.png`.
3. **REAL defect (Sol had warned): `--no-green-art` purge recolors legitimate
   green/teal art.** 39% of sage-leaf-metric pixels changed >12 levels (29,692/76,607,
   mean Δ11.8); teal bauble visibly dulled (side-by-side archived). Root cause: the
   global green cap + olive/khaki kills are palette-destructive BY DESIGN — valid only
   when the subject truly has no green art. This subject has holly. The eligibility
   checklist asked exactly this and was confirmed anyway (deliberately, per the frozen
   contract's trap) — nothing ENFORCED the answer.
4. **No hue-damage gate exists.** D5 blocks deletion; nothing gates recoloring of
   protected art. Third gap.

## Patches (observed-failure-tied)

A. D1 `h_key`: require flagged pull pixels to lie in the green hue sector; add a
   yellow-gradient regression fixture (must not trigger).
B. Eligibility becomes BINDING: `--eligibility-confirmed` with green-art subjects must
   switch the pipeline to preserve-green mode (purge WITHOUT `--no-green-art`,
   palette-stop in preserve policy) or refuse. Checklist answers get recorded in the
   manifest.
C. (Follow-up lane, banked): palette-preservation gate — pre-vs-post purge ΔE on
   protected components.
D. Re-run phase 2 on the same frozen raw with preserve-green purge; compare sage/teal
   deltas + full gates.
