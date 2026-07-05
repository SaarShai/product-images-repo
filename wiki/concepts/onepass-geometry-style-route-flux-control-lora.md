---
schema_version: 2
title: "ONE-PASS geometry×style route SOLVED: flux-control-lora-canny + trained LoRA"
type: fact
domain: image-gen
tier: semantic
confidence: 0.95
trust: verified
created: "2026-07-05"
updated: "2026-07-05"
verified: "2026-07-05"
sources: [".brainer/tenx/lora-pilot/ONEPASS-FINDINGS.md", "commits 53f2e2e/7041dd4/d46e227"]
resource: "scripts/onepass_gen.py"
supersedes: []
superseded-by: []
contradicts: []
tags: ["image-generation", "flux", "lora", "control-lora", "geometry", "style", "onepass", "cap-juluca", "marriott"]
---

# ONE-PASS geometry×style route SOLVED: flux-control-lora-canny + trained LoRA

## Summary

**One-pass geometry-to-style generation is solved.** Route: fal-ai/flux-control-lora-canny + trained style LoRA + control_lora_scale dial (0.35 = optimal geometry↔style balance). Content placement driven by EDGES in the control map (LAW 0: reference beats description). Proven on Cap Juluca + Marriott 3-panel test: silhouette-IoU **0.975–0.988 first-shot**, eliminating the two-phase (geometry-lock → style-restyle) bottleneck.

**Implementation:** `scripts/onepass_gen.py` wrapper (abstracts fal queue, LoRA registry, scale tuning, result validation).

## Why This Matters

Previously: geometry-approved raw → exact-SVG-lock → style feedback → whole-panel restyle. Multiple generation passes, no control lever between geometry fidelity and style coherence.

Now: single generation pass with trained style LoRA + control-lora-scale dial locks geometry while admitting style variation. First-shot geometry-fidelity enables approval without restyle loop.

## Evidence

- **Cap Juluca**: multicolor watercolor architectural panels, silhouette-IoU 0.975–0.988 across 3 panels
- **Marriott**: 3-panel hospitality watercolor, same IoU range, first-shot approval
- **Commits**: 53f2e2e (foundation), 7041dd4 (pilot findings), d46e227 (wrapper stable)
- **Raw findings**: `.brainer/tenx/lora-pilot/ONEPASS-FINDINGS.md`

## Key Tuning Parameters

- `control_lora_scale: 0.35` = proven sweet spot (geometry fidelity + style diversity)
- Control map: canny edges from SVG geometry guide (exact contours)
- LoRA trigger word: per-collection (cap-juluca→CJWC, marriott→MRCH; see lora.json registry)
- Provider: fal-ai (quota stable, API consistent)

## Related

- [[concepts/trained-lora-registry-pattern]]
- [[concepts/two-gate-acceptance-silhouette-iou-plus-vision-judge]]
- [[index]]
