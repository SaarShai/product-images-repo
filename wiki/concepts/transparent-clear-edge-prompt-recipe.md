---
schema_version: 2
title: "Transparent-Clear-Edge Prompt Recipe"
type: concept
domain: "experiments"
tier: procedural
confidence: 0.9
trust: user_confirmed
created: "2026-07-12"
updated: "2026-07-12"
verified: "2026-07-12"
sources:
  - tasks/transparent-clear-edge-claude/prompts/full-R4-deviation-authorized.txt
  - tasks/transparent-clear-edge-claude/ROUND-1-results.md
  - tasks/transparent-clear-edge-claude/ROUND-2-results.md
  - tasks/transparent-clear-edge-claude/ROUND-3-results.md
  - tasks/transparent-clear-edge-claude/ROUND-4-results.md
  - REVIEW/transparent-clear-edge-claude/RESULTS.md
  - scripts/white_key.py
  - tests/test_white_key_reopen.py
supersedes: []
superseded-by:
contradicts: []
tags:
  - image-generation
  - prompt-recipe
  - gpt-image
  - clean-edge
  - keyability
  - chroma-key
  - white-key
  - watercolor
  - transparent-generation
  - background-removal
  - user-verified
---

# Transparent-Clear-Edge Prompt Recipe

## Summary

A verified prompt structure for clean-edge, easily-keyable illustration generation on solid backgrounds (gpt-image family via `subgen --provider openai`). Four experimental rounds, 26 total generations, user-judged each round. Final recipe (`full-R4-deviation-authorized.txt`) delivers closed contours, tinted highlights (no pure white interior), and optional fine-detail keyability guidance.

## Winning Prompt Structure (gpt-image, Rounds 1–4)

### [REFERENCE AUTHORITY] Core

The load-bearing section replaces verbose prose descriptions:

> Use the attached image as the authoritative reference for subject and style. Recreate [subject] preserving silhouette, composition, proportions, motifs, palette relationships, lighting, detail density, and paint handling. Do not redesign, embellish, or add objects.

**Why this works:** Cures the density/style drift that a prose core ("dense but airy...") caused in early attempts. Image-anchored generation is more faithful than description-anchored generation (colorful reference style vs. dark monochrome).

### [EDGE CONTOUR] Minimal Block (2 Sentences)

> Every painted shape has a continuous, fully closed contour with no gaps or fade-outs, using a slightly darker or more saturated version of the adjacent local fill—never black and never white. Only the background may be pure #FFFFFF; every white-looking subject detail or highlight is a visibly tinted pastel off-white, fully enclosed by its contour.

**Critical finding:** The interior-white rule is the load-bearing sentence. Arms that rephrased it shipped opaque white-ghost defects. Round 1 proved this 2-sentence block compresses prior 3-paragraph edge specifications with zero edge-quality loss (user-judged best).

### [EXCLUSIONS] Semantic Framings Harmful

Semantic framings (die-cut sticker, screen-print) **lose** — they cause style drift + white-ghost risk. Stick to factual inclusion/exclusion:

> No text, border, cut line, sticker rim, checkerboard, transparency-preview pattern, extra objects, or ground shadow.

### Chroma-Green Alternative (Round 2–3 probe)

Chroma-green #00FF00 background arm won on metrics (keyed aura 0.026–0.031 vs ~0.05–0.11 white). User rejected the look for this watercolor style — **metric dominance ≠ user preference**. Recommendation: use chroma-green when keying is the sole criterion and visual style is secondary; prefer white-background + white-key for watercolor illustration.

## Keyability Modules (Standing Directive)

Include these blocks when the gen will be background-keyed and the subject could produce thin branches/hair/wisps.

### AVOID Mode (Fine Detail Optional)

No hair-thin branches/filaments/wisps; substantial widths, rounded tips; fine texture as interior detail inside solid shapes; prefer chunky varieties.

### KEYABLE-FINE Mode (Fine Detail Essential)

Use when fine detail is essential (e.g., forest, hair). Specify:

- Full pigment strength, non-white mid-tones
- Closed contour on thinnest elements
- Minimum stroke ~thick pencil line
- Filaments grouped into connected fans sharing one silhouette
- No isolated strands over open background

### Critical Conflict Resolution (Round 3–4 Finding)

If the style reference itself contains thin features, a naive prompt conflicts: "preserve the reference" vs. "avoid thin features" → model picks one at random. Round 3 showed 3/6 compliance.

**Solution:** Add one explicit deviation-authorization sentence:

> With ONE exception: wherever the reference shows hair-thin branches/filaments/wisps, replace with a sturdier rounder variety of same color and position; keyability overrides reference fidelity for thin features only.

Result (Round 4): 3/3 compliance.

### Limits and Alternatives (Sol-Ultra Decision Rule)

Prompt modules are probabilistic steering, not geometry guarantees. **Never rely on a prompt module to rescue pale filaments from a white flood-fill key**—for essential fine detail:

1. Change the extraction pipeline (native alpha > chroma+module > separate fine-detail layer > trimap matting)
2. Judge minimum thickness at final delivered resolution
3. One-pixel silhouette gaps let flood-fill erase whole pale regions (topology matters, not just thickness)

## Keyer Upgrade: white_key.py --reopen-interior

`scripts/white_key.py` now includes `--reopen-interior` (opt-in) which reopens trapped/enclosed near-white background regions that flood-fill cannot reach. Purity + area guards protect tinted cream/blush highlights.

### Verification (July 2026)

- Test suite: `tests/test_white_key_reopen.py` (4/4 pass)
- Real candidate: 48 regions / 33k px reopened
- Tinted highlights: untouched

### SAFETY PAIRING (calibrated 2026-07-12 — this flag is only safe WITH the prompt recipe)

The reopen flag cannot distinguish trapped background from PAINTED flat-white openings
(e.g. pale tube-coral tops): a purity/area sweep on known-bad (Codex round-2 arms, no
interior-white discipline: 49 reopens incl. tube tops) vs known-good (R2a-r2: 48 true
gaps) kills both proportionally — no threshold separates them (0.35→0.8 purity: bad
49→4, good 48→10). The discriminator is UPSTREAM: this recipe's interior-white rule
("every white-looking subject detail is a visibly tinted off-white") makes painted
openings non-pure-white, so the purity guard protects them. Rule: `--reopen-interior`
is safe on art generated with this recipe; on foreign art, inspect the magenta keycheck
for punched-out painted openings before shipping, or key without the flag.

### Use Pattern

```bash
scripts/white_key.py <input.png> --output <output.png> --reopen-interior
```

## Recommended Pipeline

1. Generate with final recipe (`full-R4-deviation-authorized.txt`)
2. If native alpha needed: direct alpha output (if model supports `background=transparent`)
3. If white-key extraction: `scripts/white_key.py` (standard mode)
4. Edge decontamination: `scripts/dehalo_edge.py --image keyed.png --out keyed-dehalo.png --check` — white_key produces BINARY alpha that keeps the white-contaminated anti-aliased edge ring fully opaque, which renders as a white HALO over any darker background; dehalo_edge fixes it deterministically (nearest-interior donor-field RGB extension, smoothed; alpha re-solved from whiteness vs donor with a distance-based monotonic floor; interior byte-identical).
5. MANDATORY GATE: before delivering any keyed RGBA, composite an edge-dense crop over #111111 and visually verify no white rim (halo was shipped 2026-07-12 because only transparency%/wrongly-removed/trapped-pocket were gated, never a dark-background composite; user hard rule: never ship halo).
6. If interior-trapped voids: add `--reopen-interior` after reviewing purity/area settings
7. If fine-detail preservation critical: separate layer + trimap matting (do not rely on prompt module alone)

### Calibration Notes (v1/v2 Iterations)

- Per-pixel error-rejection creates speckled patchwork rims (reject rejection — coherence beats accuracy).
- Alpha re-solve without a distance floor punches speckle holes in pale art.

## Evidence & Testing

- **Round 1:** 6 gens, reference-authority core vs. prose core; PASS on reference core
- **Round 2:** 6 gens, chroma-green vs. white background probes; white preferred aesthetically, chroma won on metrics
- **Round 3:** 6 gens, KEYABLE-FINE without deviation auth; 3/6 thin-feature compliance (failure mode: model picked "preserve" over "avoid")
- **Round 4:** 8 gens, KEYABLE-FINE + deviation-authorization sentence; 3/3 thin-feature compliance, edge quality maintained

User-judged all results; selected full-R4 recipe for production.

## Related

- [[concepts/illustrated-product-upscale-and-background-removal-workflow]] (post-gen keying, alpha validation)
- [[concepts/chroma-green-transparency-workflow]] (alternative: native chroma-key pipeline)
- [[concepts/family-a-architectural-watercolor-panel-proven-recipe-geometry-gate-cap-juluca]] (image-generation parent workflow)

## Open Questions

- None yet.
