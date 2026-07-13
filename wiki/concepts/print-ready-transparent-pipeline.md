---
schema_version: 2
title: "Print-Ready Transparent Pipeline (native alpha + decontam_binarize + gate battery)"
type: concept
domain: "experiments"
tier: procedural
confidence: 0.85
trust: agent_verified
created: "2026-07-13"
updated: "2026-07-13"
verified: "2026-07-13"
sources:
  - tasks/transparent-bg-endgame/PIPELINE.md
  - tasks/transparent-bg-endgame/CANARIES.md
  - tasks/transparent-bg-endgame/CALIBRATION.md
  - scripts/decontam_binarize.py
  - scripts/gates/gate_battery.py
  - REVIEW/transparent-bg-endgame/round1/INDEX.md
supersedes: []
superseded-by: []
contradicts: []
tags:
  - transparent-generation
  - background-removal
  - print
  - binary-alpha
  - gate-battery
  - gpt-image
  - native-alpha
  - decontamination
---

# Print-Ready Transparent Pipeline

## Summary

Production route for Illustrator print layers uses native-alpha generation (gpt-image-1 `background=transparent`), not background removal. Empirically verified 2026-07-13 across three gpt-image generations and two image-generation APIs. Paired with `scripts/decontam_binarize.py` (linear-light ridge unmix) and `scripts/gates/gate_battery.py` (tri-state pass/review/fail on print profile), yielding 3/9 auto-PASS results; residual defects are stochastic painted pale patches caught by donor-referenced halo gates and resolved via replication-and-reject (3–4 gens/asset budget).

## Native-Alpha Canaries (2026-07-13)

| Model | Method | Alpha Result | Notes |
|-------|--------|--------------|-------|
| gpt-image-1 | `background=transparent` | Real nonconstant alpha | ✓ Usable |
| gpt-image-1.5 | `background=transparent` | Real nonconstant alpha | ✓ Usable |
| chatgpt-image-latest | `background=transparent` | Real nonconstant alpha | ✓ Usable |
| gpt-image-2 | `background=transparent` | HTTP 400 error | ✗ Not supported |
| fal/BFL Flux.2 | Schema inspection | No alpha parameter exposed | ✗ Not supported |

**Decision rule:** Route print-transparency requests to `gpt-image-1`, `gpt-image-1.5`, or ChatGPT-web generation. Do not attempt `gpt-image-2` or Flux.2 for this workflow.

## Complete Pipeline

### Stage 1: Generation + Anti-Contamination Prompt

Use R4 clean-edge recipe with reinforced anti-aura, anti-ground, anti-backdrop blocks. Starting generation command:

```bash
scripts/subgen.py --provider openai --model gpt-image-1 --prompt <full_recipe> \
  --background transparent --output <raw.png>
```

Ensure prompt blocks include:
- No aura, halo, or glow around the subject
- No ground shadow or backdrop wedges
- No painted pale patches that look like background

### Stage 2: Decontamination (Linear-Light Ridge Unmix)

Apply linear-light ridge unmixing to recover true subject alpha from contaminated edges:

```bash
scripts/decontam_binarize.py \
  --input <raw.png> \
  --output <decontam.png> \
  --lambda 0.04 \
  --donor-pad 8 \
  --upscale x4 \
  --threshold-last
```

**Formula:** F = (a² × F₀ + λ × D) / (a² + λ), where:
- F = final unmixed channel
- a = alpha at that pixel
- F₀ = contaminated foreground
- D = donor field (component-constrained)
- λ = 0.04 × (1 − a)²

**Key settings (verified):**
- `--threshold-last`: Never threshold-then-unmix; alpha threshold is the final step.
- `--donor-pad 8`: Surrounds subject with clean donor context before unmix.
- `--upscale x4`: Optional; improves edge coherence on small subjects or thin details.
- Component-constrained donor field: Recovers true subject color without chroma drift.

**Output:** Soft-alpha sidecar retained (`.soft.png`); use for soft-wash artwork. Binary alpha (`.png`) used for opaque-edge art only.

### Stage 3: Gate Battery (Print Profile)

Run tri-state gate battery to classify each asset:

```bash
scripts/gates/gate_battery.py --input <decontam.png> --profile print
```

**Output codes:**
- Exit 0 / PASS: Auto-approved for print, ship immediately.
- Exit 3 / REVIEW: Marginal candidate, inspect donor-referenced halo metrics before decision.
- Exit 2 / FAIL: Defects exceed print tolerance; regenerate (do not repair).

## Measured Yield (Round 2)

- **3/9 auto-PASS** full print profile (zero manual intervention).
- **Residual defect class:** Stochastic painted pale patches (ground blobs, backdrop wedges).
  - Content defects caught by donor-referenced D1 halo gate.
  - Not reparable via local filters (motion-smearing, over-blur).
  - Resolved via replicate-and-reject (3–4 gens per asset typical).

## Route Comparison (Round 1, 8 gens)

| Route | Pros | Cons | Verdict |
|-------|------|------|---------|
| **gpt-image-1 native alpha** | Best style + cut quality, real alpha | Occasional ground blobs | **Winner** |
| white_key flood + chroma-key | Clean cut, simple | Shreds thin strokes, loses detail | Not primary |
| chroma-green background | Wins on keying metrics (0.026–0.031 aura) | Saturation drift, visual style rejected | Metrics ≠ preference |
| ChatGPT-web (latest) | Real alpha | Glossy stylistic drift | Secondary option |

**User verdict:** gpt-image-1 best style + cut for watercolor.

## Detector Lesson: Absolute Edge-Brightness Metrics Fail on Honest AA

Absolute edge-brightness halo metrics **false-positive on honest anti-aliasing edges** of bright art. Example: a clean white-interior watercolor stroke with proper AA rim registers as "halo" on naive pixel-brightness thresholds.

**Working metric (verified):** Donor-referenced comparison
- Composite candidate vs. donor-composite (same subject, clean generation)
- p95 delta-L* in a 0.3 mm edge band (linear light, not sRGB)
- Detects real contamination without false-positives on AA

**Calibration rule:** Never hard-FAIL on absolute metrics. Build on approved finals (verified PASS set) before trusting any gate threshold. A single false-FAIL on a known-good asset ruins production confidence.

## Advisor Corrections Banked

1. **Threshold LAST, never threshold-then-unmix.** Early binarization breaks the ridge-unmix math; recover soft alpha first, gate at the end.
2. **Binary alpha is print-invisible at ≥300 ppi for opaque-edge art only.** Soft washes and AA-heavy strokes must keep raster soft alpha as a sidecar; binary is correct only for flat closed-contour watercolor.
3. **Rank arms by worst image, not mean.** A batch is only as good as its worst candidate; sorting by average masks tail defects that will fail print inspection.

## Related

- [[concepts/transparent-clear-edge-prompt-recipe]] — Winning prompt structure (gpt-image, R4 clean-edge, deviation-authorization for thin features).
- [[concepts/gate-metrics-on-keyed-deliverable-not-raw-render]] — Gate the shipped artifact, not intermediates (aura 3–4× different raw vs. keyed).
- [[concepts/chroma-green-transparency-workflow]] — Alternative native chroma-key route (verified; metrics win, visual style secondary).

## Open Questions

- Soft-alpha sidecar viability for mixed soft-opaque art (gingerbread, textured watercolor).
- Print-profile thresholds for 240 ppi / 150 ppi delivery (verified at 300+ ppi only).
