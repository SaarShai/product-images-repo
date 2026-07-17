---
schema_version: 2
title: "Green-art subjects: run BOTH purge modes, gate both, let human pick"
type: fact
domain: transparent-generation
tier: tactical
confidence: 0.9
trust: verified-human
created: "2026-07-17"
updated: "2026-07-17"
verified: "2026-07-17"
sources:
  - tasks/transparent-bg-endgame/evidentiary-festive/VERDICT.md
  - "Arbiter: Saar, viewing full-res finals"
supersedes: []
superseded-by: []
contradicts: []
tags:
  - route-c-green-v2
  - background-removal
  - green-art-preservation
  - purge-modes
  - structural-integrity
  - quality-gates
---

# Green-art subjects: run BOTH purge modes, gate both, let human pick

## Summary

Route C-green v2 on subjects with legitimate green artwork fails differently in each purge mode. Neither mode is universally superior. Run both on the same frozen raw, gate both outputs, and let the human arbiter choose. Structural damage (erosion/holes) is perceptually worse than sub-perceptual recoloring.

## Evidence

**Test subject:** Festive holly illustration with legitimate green-art regions (holly leaves, foliage).

### Destructive mode (`--no-green-art`)
- **Outcome:** ACCEPTED by user.
- **Defect:** Recolors protected green art: 29,692 px, mean Δ11.8 ΔE (sub-perceptual). User accepted at delivery scale.
- **Calibration anchor:** mean ΔE ≈ 12 on protected green art = below user perceptual threshold on this subject.
- **Gate status (post-D1 patch, 260 ppi):** All blocking gates D2–D8 PASS. D1 review-only (single 531px/5.07mm² component, sub-visible ring, human-judgment tier). Resolved by verdict.

### Preserve-green mode (`--green-art-present`)
- **Outcome:** REJECTED by user ("holes cut out of the illustration").
- **Defect:** Structural erosion deleted a 4,048 px holly cluster region.
- **Severity metrics:** min_anchor_component_recall=0.758 (erosion), real edge halo H_L=19.7.
- **Root cause:** Shape-erosion algorithm carved out legitimate artwork as false "background."

### Key finding

Structural damage (holes, erosion, deleted regions) is perceptually WORSE than sub-perceptual recoloring. Do NOT hard-code destructive-wins — recolor magnitude is subject-dependent (one calibration point: this subject accepted ~12 ΔE).

## Routing consequence

When the subject contains legitimate green art:
1. **Run BOTH purge modes** on the same frozen raw (purge is cheap, local operation).
2. **Gate both** outputs independently; expect trade-offs.
3. **Human judgment picks the winner.** Never auto-select.
4. **If preserve mode selected**, mandatory checkpoint: verify `min_anchor_component_recall` to catch structural erosion before ship.

## Related

- [[print-ready-transparent-pipeline]] — complete native-alpha + gate pipeline
- [[key-colored-art-vs-trapped-background]] — shape-based vs hue-distance separation
- [[removal-step-invariant-truth-backed-preservation-proof]] — truth-backed preservation proof required for removal steps
- [[human-verdict-user-verdict-file-required-for-gate-acceptance]] — human-verdict file pattern for gate resolution

## Open Questions

- Calibration extent: is mean ΔE ≈ 12 recolor also acceptable on non-festive subjects with green art? (One data point only; subject-dependent claim.)
- Do other green-art classes (foliage, seaweed, tropical motifs) exhibit similar recolor tolerance?
- Can the preserve-mode erosion be tightened via parameter tuning, or is structural damage inherent to shape-based protection?
