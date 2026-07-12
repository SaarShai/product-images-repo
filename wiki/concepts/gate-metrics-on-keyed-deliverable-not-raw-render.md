---
schema_version: 2
title: "Gate metrics on the keyed deliverable, not the raw render"
type: fact
domain: image-gen
tier: semantic
confidence: 0.90
trust: user_verified
created: "2026-07-12"
updated: "2026-07-12"
verified: "2026-07-12"
sources: ["transparent-clear-edge session 2026-07-12", "chroma-key pipeline"]
resource: "scripts/chroma_key.py"
supersedes: []
superseded-by: []
contradicts: []
tags: ["image-generation", "quality-assurance", "gates", "metrics", "chroma-key", "background-removal", "transparency", "pipeline"]
---

# Gate metrics on the keyed deliverable, not the raw render

## Summary

**Quality gates and metrics must measure the artifact that ships, not intermediates.** In chroma-key pipelines (green/blue-screen removal), the same candidates measured aura_index 0.10–0.11 on the raw (pre-key) render but 0.026–0.031 after `chroma_key.py` on the actual RGBA output — a 3-4× gap. Gating on raw data masks real delivered quality.

**Rule:** Always measure post-pipeline, on the exact bytes the user receives.

## Trigger/symptom

- A gate or metric is run on a pre-pipeline intermediate (raw render, pre-key, pre-upscale) while the shipped artifact is downstream.
- Quality score improves dramatically after a pipeline step (key, upscale, denoise).
- Gate accepts candidates that look bad in delivery, or rejects good ones that looked defective during intermediate checks.

## Why This Matters

**Pipeline stages transform artifacts:** Chroma-key removes a synthetic background, upscaling sharpens edges, dehalos clean bright halos. Raw measurements can't predict final quality. Gating intermediates creates a false gate: agents trust the score and ship defective work, or over-polish candidates that improve downstream anyway, wasting iteration budget.

**Silent quality drift:** If review uses raw metrics while delivery uses keyed pixels, the user sees a completely different artifact than what was tested.

## Implementation

1. **Measure on the pipeline OUTPUT**, not inputs.
2. **Keep pipeline state immutable** between gates — measure the exact bytes that will ship.
3. **Document the pipeline chain** so future gates know which post-processing steps apply.
4. Example: for chroma-key + upscale, measure on `upscaled_keyed_final.png`, not `raw.png` or `raw_keyed.png`.

## Related

- [[concepts/chroma-green-transparency-workflow]] (in .claude/projects/memory)
- [[index]]
