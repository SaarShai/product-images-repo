---
schema_version: 2
title: "Key-colored art vs trapped key background is colorimetrically inseparable; ban the hue or separate by shape"
type: fact
domain: experiments
tier: semantic
confidence: 0.9
trust: user_verified
created: "2026-07-13"
updated: "2026-07-13"
verified: "2026-07-13"
sources:
  - tasks/transparent-bg-endgame/LEDGER.md
  - REVIEW/transparent-bg-endgame/round4/
  - REVIEW/transparent-bg-endgame/round5/
supersedes: []
superseded-by: []
contradicts: []
tags:
  - chroma-key
  - background-removal
  - image-generation
  - color-keying
  - palette-constraint
  - shape-detection
  - gpt-image
  - watercolor
---

# Key-Colored Art vs Trapped Key Background Is Colorimetrically Inseparable

## Problem Statement

When using chroma-key (e.g., #00FF00 bright green) for background removal:

1. **Aggressive despill / purge** deletes legitimate artwork (e.g., olive-colored seaweed or bright green plants).
2. **Protected artwork** leaves trapped key-color residue between thin elements (leaves stacked, branches crossing), where the algorithm cannot distinguish subject from background.

The root cause: legitimate artwork can be **literally near-pure key color**. Example: a sampled seaweed pixel at `[1, 137, 0]` (near-pure green) is colorimetrically indistinguishable from trapped `#00FF00` background at the pixel level.

## Why Color-Distance Gates Fail

A hue-based detector cannot separate:
- A thin bright-green leaf (legitimate subject, RGB ≈ [0, 255, 0])
- Trapped background key-color between leaves (RGB = [0, 255, 0])

No threshold exists in color space that catches one without catching the other. Attempts to de-spill via hue-snapping make this worse, causing garish saturation banding as edge-band pixels are forced to interior hue at their own luminance.

## Two Working Resolutions

### Resolution A: Prompt-Side Palette Ban (Unconditional Key Removal)

**Principle:** Force the generation to avoid the key-hue entirely.

**Constraint phrasing:**
```
No bright pure green anywhere in the artwork. Plants are olive, sage, teal, 
or forest-green shades. Avoid neon green, lime, or bright kelly green.
```

**Advantages:**
- Allows unconditional chroma-key removal (e.g., `scripts/green_purge.py --aggressive --no-green-art`).
- Eliminates the false-positive dilemma entirely.
- Ensures legit art is never near the key-hue by generation time.

**Disadvantages:**
- Constrains art palette; may reduce color vibrancy or naturalness for certain subjects (e.g., tropical plants, neon signage).
- Requires user buy-in on color boundaries at prompt time.

### Resolution B: Shape-Based Protection (Solid Blob Identification)

**Principle:** Identify connected solid blobs that are large enough to be legitimate art, not trapped residue.

**Algorithm:**
- Compute max inscribed radius for each connected component of key-hued pixels.
- Protect blobs where **max inscribed radius ≥ 7 px** AND **area ≥ 300 px**.
- Purge all other key-color.

**Why this works:**
- Trapped residue between thin elements has small inscribed radius (<7 px, often 1–2 px).
- Solid legit leaves, petals, or background plants have large inscribed radius (10+ px typical).
- Area gate (≥300 px) rejects single-pixel speckle and thin threads.

**Advantages:**
- Preserves legit subject colors.
- Automatically adapts to subject geometry without palette constraints.

**Disadvantages:**
- Fails on **wavy / feathered leaves:** A thin, crinkled leaf has an area but inscribed radius <7 px due to internal concavities. (Verified failure case: seaweed outline with wrinkled texture.)
- Requires careful threshold calibration (tested 7 px / 300 px; other values not yet validated).

**Failed approach to avoid:** Bbox-fill solidity (ratio of area to bounding-box area) does NOT work on wavy shapes; solidity can be <0.3 for legitimate thin, textured subjects.

## Empirical Evidence (Rounds 4–5)

### Round 4: Aggressive Hue-Based Despill + Hue-Snapping Edge Repair

- **Result:** Deleted legit seaweed; saturated garish banding where edge pixels were forced to interior hue.
- **Defect:** Illegible waving plant; visual quality rejected.

### Round 5: Palette Ban (Olive/Sage/Teal Constraint) + Unconditional Green Purge

- **Result:** Clean removal; no ambiguity. All plants rendered in constrained palette.
- **User verdict:** "Works, but limits palette. Use when subject allows."

### Round 5b: Shape-Based Protection (Max Inscribed Radius ≥ 7 px)

- **Result:** Preserved solid legit plants; trapped residue removed.
- **Limitation found:** Wavy seaweed (legit subject) marked as speckle due to low bbox-fill solidity.
- **Corrected logic:** Inscribed radius (not solidity) works on crinkled shapes. Still fails on very thin, highly wrinkled elements.

## Recommended Decision Tree

1. **Does the subject allow a palette constraint** (e.g., no pure green)?
   - **Yes:** Use Resolution A (palette ban + unconditional purge). Simplest, safest.
   - **No (vibrant greens essential):** Proceed to step 2.

2. **Are key-hued subjects solid and robust** (radius ≥ 7 px typical)?
   - **Yes:** Use Resolution B (shape-based protection). Verify first on a test batch (2–3 gens).
   - **No (wavy, feathered, fine-thread subjects):** Resolution B will fail. Revert to A or accept residue.

3. **Accept trapped residue** (last resort)?
   - Manual touch-up per artifact, or accept visual slight cloudiness in dense plant areas.

## Related Lessons

- [[concepts/print-ready-transparent-pipeline]] — Complete native-alpha pipeline; this lesson applies to post-gen keying steps (white_key.py, chroma_key workflows).
- [[concepts/mandatory-ink-outline-edge-defense]] — Companion lesson: outlines solve diffusion edge-blend (different problem) but not interior color traps.
- [[concepts/gate-metrics-on-keyed-deliverable-not-raw-render]] — Always gate the final keyed/delivered artifact, not the raw generation.

## Open Questions

- Inscribed-radius threshold for wavy subjects (7 px passes test on solid leaves; fails on seaweed—need dataset of 20+ real cases).
- Interaction with soft-wash watercolor (feathered edges reduce inscribed radius; does that invalidate the test?).
- Batch-level logic: If 1/5 subjects is wavy (palette-ban required) and 4/5 are solid (shape-based OK), should batch adopt palette ban or run split strategies?
