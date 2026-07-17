---
schema_version: 2
title: "Models ignore numeric prompt constraints; mandatory-NOUN framing binds"
type: fact
domain: "experiments"
tier: semantic
confidence: 0.9
trust: audited
created: "2026-07-16"
updated: "2026-07-16"
verified: "2026-07-16"
sources:
  - "2026-07-16 dual-audit session (transparent-bg-endgame)"
  - "mandatory-ink-outline-edge-defense page: 3/3 compliance observed only with NOUN enforcement language"
  - "observed in gpt-image-2 across 5+ sessions"
supersedes: []
superseded-by: []
contradicts: []
tags:
  - image-generation
  - prompt-engineering
  - gpt-image
  - constraints
  - diffusion
  - phrasing
---

# Models Ignore Numeric Prompt Constraints; Mandatory-NOUN Framing Binds

## Core Rule

**Models systematically ignore numeric/percentage/relative constraints in prompts.** Instead, use mandatory **noun-based framing** that treats the constraint as a design feature, not a request.

**Observed:** 
- Height/width percentages ("keep the door at 70% height") → ignored; actual ≈ 1.4× overshoot.
- Polite outline wording ("prefer outlines" / "may have outlines") → silently dropped; no outlines generated.
- Numeric thresholds ("avoid bright green") → inconsistent; semantic palette bans work.

**Working:** 
- "This image is NON-NEGOTIABLE... every shape has a MANDATORY dark ink contour" → 3/3 compliance.
- "No bright green anywhere in the image" (absolute semantic ban, not percentage) → respected.

## Evidence

### Experiment 1: Outline Phrasing (2026-07-13)

| Phrasing | Result | Compliance |
|----------|--------|-----------|
| "Prefer outlines" | 0/3 with outlines | 0% |
| "May have thin outlines" | 0/3 with consistent outlines | 0% |
| "NON-NEGOTIABLE... MANDATORY dark ink contour on every silhouette" | 3/3 with strong outlines | 100% |

**Evidence source:** `tasks/transparent-bg-endgame/round7_outline/gen_round7.py` (~line 34); REVIEW folder rounds 6–7 images.

### Experiment 2: Height/Width Constraints

- Prompt: "Subject should occupy 70% of canvas height"
- Observed: Subject ≈ 98% height (1.4× overshoot)
- Failed approach: Increasing %s, adjusting aspect language → still ≈ 1.4× overshoot
- Workaround: Composition belongs to placement; enforce budget via geometric guides (fit_gate.py) + bottom-crop, not prompt constraints.

**Related:** [[concepts/composition-belongs-to-placement]] (if it exists in memory).

### Experiment 3: Color Bans

| Constraint | Method | Result |
|-----------|--------|--------|
| "Avoid bright green (>200 saturation)" | Numeric | ~40% non-compliant |
| "No bright green anywhere" | Semantic absolute | ~5% non-compliant (residual edge-blend) |

## Why This Happens

1. **Diffusion models optimize for aesthetic coherence, not rule compliance.** A numeric constraint is treated as a weak preference; the model balances it against visual coherence.
2. **Percentage/aspect language is ambiguous.** "70% height" could mean subject baseline, bounding box, or visual center; the model picks whichever looks good.
3. **Polite/optional language signals non-binding.** "May have" or "prefer" tells the model: this is optional. Hard, mandatory framing signals: this is structural to the image.

## The Fix: Mandatory Noun Framing

Reframe every constraint as a **design feature**, not a limit:

- ❌ "Keep door height to 70%" → ✅ "Door stands as a complete, full-height architectural feature"
- ❌ "Avoid bright green" → ✅ "Palette contains NO bright green; all greens are muted naturalistic tones"
- ❌ "Prefer outlines" → ✅ "MANDATORY... VISIBLE dark ink contour on every silhouette"

The constraint becomes a non-negotiable property of the image, not a request.

## Related Lessons

- [[concepts/mandatory-ink-outline-edge-defense]] — Original lesson; phrasing calibration in action.
- [[concepts/composition-belongs-to-placement]] (if it exists) — Composition constraints belong to placement tools (geometry guide), not prompt percentages.
- [[concepts/transparent-clear-edge-prompt-recipe]] — Clean-edge recipe; uses mandatory NOUN framing throughout.

## Open Questions

- Does this pattern hold for other frontier models (Flux, Turbo, Claude vision gen)?
- What is the minimum threshold for "mandatory" language (e.g., "MUST" vs. "NON-NEGOTIABLE" vs. "is")?
- Can mandatory NOUN framing be automated in prompt templates, or does it require hand-tuning per domain?
