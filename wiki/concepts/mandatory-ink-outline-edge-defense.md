---
schema_version: 2
title: "Mandatory ink outline defeats diffusion edge-blend contamination"
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
  - REVIEW/transparent-bg-endgame/round6/
  - REVIEW/transparent-bg-endgame/round7/
supersedes: []
superseded-by: []
contradicts: []
tags:
  - image-generation
  - edge-quality
  - prompt-engineering
  - diffusion-limitation
  - gpt-image
  - transparent-generation
  - background-removal
  - keyability
  - watercolor
---

# Mandatory Ink Outline Defeats Diffusion Edge-Blend Contamination

## Problem Statement

Stray background-colored pixels survive keying at edges and branch junctions even though the generation prompt explicitly demanded hard, non-anti-aliased edges. These pixels are fully opaque colors contaminated with background hue — not semi-transparent alpha — making them impossible to separate post-hoc using hue-based keying or color-distance gates.

## Root Cause

Diffusion and autoregressive image renderers mathematically blend at all boundaries during the denoising process. Prompt-side instructions like "hard edge / no anti-aliasing" reduce but cannot eliminate blend pixels because the underlying rendering pipeline produces semi-transparent intermediate states that resolve to opaque contaminated colors at edges. Observed consistently on tested gpt-image-2 outputs in rounds 4–7; the precise renderer mechanism is unverified.

**Key fact:** You cannot prompt a diffusion model into pixel-perfect edge separation. The architectural constraints of the model make some blending inevitable.

## Failed Approaches

- **Hue-snapping post-hoc:** Detecting and removing background-hued pixels at edges is whack-a-mole (each band-green pixel or ground-shadow blob requires new gate logic).
- **Prompt-hardening alone:** Escalating edge-hardness language gets silently dropped by gpt-image-2; prompts around "no blending" or "razor-sharp" do not transfer to consistent model behavior.
- **Color distance gates:** No threshold separates contaminated edge pixels (e.g., [100, 200, 100] green-tinted seaweed) from trapped background key-hue.

## Working Solution: Mandatory Visible Ink Outline

Add a **slim, dark ink contour on every silhouette**. The contour frames all edges and branch junctions, so blend pixels from diffusion automatically land on dark ink where they are **invisible**.

### Prompt Phrasing (Calibrated for GPT-Image)

Use mandatory, non-negotiable framing — medium-strength wording was
under-painted (round 5) and silently dropped by the model. Verbatim
`SIGNIFICANT_CONTOUR_BLOCK` from
`tasks/transparent-bg-endgame/round7_outline/gen_round7.py` (~line 34):

```
[EDGE CONTOUR - SIGNIFICANT, MANDATORY]
This is a NON-NEGOTIABLE style requirement: every shape in the artwork
is enclosed by a clearly VISIBLE, continuous, fully closed dark ink
contour line - like classic pen-and-ink illustration with watercolor
fill. The line is slim and elegant (fine felt-tip weight, never chunky),
but it must be DARK and OBVIOUS at a glance: a deep, saturated, darker
shade of the adjacent fill color, never faded, never soft, never
blended away. The outermost silhouette of the whole subject carries the
most defined, unbroken line in the image; if any part of the silhouette
lacks a visible dark contour line the image is wrong. No open, soft, or
lineless watercolor edges anywhere.
```

**Critical:** Do not rely on weaker phrasing like "prefer outlines" or "may have outlines" — such language is silently dropped by gpt-image-2. Enforcement language works; permissive language does not.

## Empirical Evidence (Rounds 6–7 Comparison)

### Round 6: No Visible Outlines

- **Result:** Stray band-green pixels at junctions and thin strokes.
- **Defect count at hard gate:** 604 band-green pixels identified via flood-fill.
- **User verdict:** Circled visible artifacts at 12× zoom; failed all hard-alpha gates.

### Round 7: Mandatory Dark Ink Contour on Every Silhouette

- **Result:** Blend pixels land on dark ink.
- **Defect count:** 110 band-green pixels (acceptable near-zero noise; 15 pixels after conservatism threshold).
- **Hard gates:** Passed all gates including halo detection and edge-purity checks.
- **User verdict:** "Best yet — bank it."

## Why This Works

1. **Diffusion still blends**, but blend colors now mix with dark ink (near-black) instead of subject interior or air.
2. **Keying is immune:** Chroma-key, white_key.py, or binary-alpha masking all treat dark outlines as "subject" (correctly), absorbing blend artifacts.
3. **No post-hoc repair:** The outline is generated as part of the subject, not added later.
4. **Watercolor-compatible:** Ink outlines are a legitimate art style in watercolor tradition; they enhance rather than distract from the finished piece.

## Related Lessons

- [[concepts/print-ready-transparent-pipeline]] — Complete native-alpha pipeline; this outline discipline is a prerequisite for clean decontamination.
- [[concepts/transparent-clear-edge-prompt-recipe]] — R4 clean-edge recipe; mandatory-outline principle is baked in as a core constraint.
- [[concepts/key-colored-art-vs-trapped-background]] — Companion lesson on color-based keying limits; outlines solve edge-blend but not interior color traps.

## Open Questions

- Outline thickness / darkness in relation to subject scale (preliminary: dark=RGB<80, width=0.5–1 mm at target DPI).
- Interaction with soft-wash watercolor (thin subjects with heavy feathering; does outline compete or complement?).
- Non-watercolor styles: Do outlines force a particular aesthetic in architectural or realistic generation?
