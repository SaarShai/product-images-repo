---
schema_version: 2
title: "Two-gate acceptance proven necessary: silhouette-IoU + vision judge"
type: fact
domain: image-gen
tier: semantic
confidence: 0.9
trust: verified
created: "2026-07-05"
updated: "2026-07-05"
verified: "2026-07-05"
sources: ["marriott-lora task evidence, 2026-07-05"]
resource: "scripts/onepass_gen.py"
supersedes: []
superseded-by: []
contradicts: []
tags: ["gates", "silhouette-iou", "vision-judge", "quality-assurance", "marriott"]
---

# Two-gate acceptance proven necessary: silhouette-IoU + vision judge

## Summary

**Silhouette-IoU alone is insufficient.** Code evidence: Marriott r3_right_s1 scored silhouette-IoU 0.976 (near-perfect geometry shape match) but was **near-EMPTY** (failed visual content). Vision judge caught it; IoU pass is a false positive on content completeness.

**Rule: Always gate both geometry (measured IoU) and visual quality (vision judge).** Never accept on IoU alone.

## Why This Matters

- IoU measures contour shape fidelity but is blind to completeness, density, and semantic presence.
- A candidate can match the silhouette boundary perfectly while failing to paint interior detail or leaving large voids.
- Decoupling gates (geometry-only + visual-only) allows independent iteration on each axis.

## Failure Case

**Marriott r3_right_s1:**
- silhouette-IoU: 0.976 (pass)
- Visual content: near-empty (fail)
- Root: LoRA style influence over-weakened geometry control at that specific seed/scale combo; generated valid outline with insufficient interior rendering

## Gate Discipline

1. **Geometry gate** (code): `python3 -m studio.controlmap --score` → silhouette-IoU ≥ threshold
2. **Visual gate** (vision): OpenAI gpt-4o on hi-DPI tiles or full-panel → presence/density/semantic check
3. **Human gate** (review): aesthetic + style approval

Never combine gates or omit intermediate steps.

## Related

- [[concepts/onepass-geometry-style-route-flux-control-lora]]
- [[concepts/geometry-must-be-measured-gate]] (existing)
- [[index]]
