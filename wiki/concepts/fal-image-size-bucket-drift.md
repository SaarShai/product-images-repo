---
schema_version: 2
title: "fal image_size bucket drift: snapping and normalization"
type: fact
domain: image-gen
tier: semantic
confidence: 0.85
trust: verified
created: "2026-07-05"
updated: "2026-07-05"
verified: "2026-07-05"
sources: ["onepass_gen.py impl", "marriott-lora testing 2026-07-05"]
resource: "scripts/onepass_gen.py"
supersedes: []
superseded-by: []
contradicts: []
tags: ["fal", "image-generation", "bucket", "resolution", "aspect", "normalization"]
---

# fal image_size bucket drift: snapping and normalization

## Summary

**fal model API snaps `image_size` to internal buckets.** Spec: 820×2105 → actual output: 576×1536. Output aspect ≠ requested aspect. Consequence: metrics computed on original spec miss actual output dimensions; assembly into shared viewbox fails silently (misaligned crop zones, cutout voids).

**Fix:** Always score resize-normalized metrics against actual returned dimensions. Assemble multi-panel layouts at spec bbox_svg positions in a unified viewbox, not pixel-by-pixel.

## Why This Matters

**Layout assembly failure:** If score computed on spec 820×2105 but output is 576×1536, then mask coords, cutout positions, and overlay registrations all drift. Multi-panel composition breaks: panels misalign, cutouts miss boundaries, void zones expand.

**Silent failure:** API returns valid image at bucketed size; no error raised. Agent assumes dimensions match and proceeds to assembly. Result: mangled layout.

## Implementation

1. **Query actual output dimensions** from fal response (don't assume spec)
2. **Normalize all metrics** (IoU, positioning, cutout containment) to actual output size
3. **Use bbox_svg positions from spec** to place output into unified viewbox, NOT pixel-based coords from spec
4. **Verify assembly** before delivery: check cutout alignment + panel boundaries in final viewbox

## Example

```
spec: image_size=[820, 2105], bbox_svg=[x=100, y=200, w=820, h=2105]
response: {"image": {...}, "image_size": [576, 1536]}
normalize: aspect_ratio_orig = 820/2105 ≈ 0.389; aspect_ratio_actual = 576/1536 ≈ 0.375 (drift)
place: position output at bbox_svg coordinates in viewbox, NOT at pixel[0,0]
```

## Related

- [[concepts/onepass-geometry-style-route-flux-control-lora]]
- [[index]]
