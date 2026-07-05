---
schema_version: 2
title: "No painted text rule: signage text is vector layer / omitted / manual"
type: fact
domain: image-gen
tier: procedural
confidence: 0.95
trust: user_confirmed
created: "2026-07-05"
updated: "2026-07-05"
verified: "2026-07-05"
sources: ["user rule 2026-07-04", "scripts/onepass_gen.py impl"]
resource: "scripts/onepass_gen.py"
supersedes: []
superseded-by: []
contradicts: []
tags: ["text", "signage", "image-generation", "diffusion", "vector", "prompt-clause"]
---

# No painted text rule: signage text is vector layer / omitted / manual

## Summary

**Never generate painted text in diffusion output.** Diffusion garbles signage/lettering. Rule: all text is handled via **.ai vector layer** (Illustrator), **omitted** (leave blank), or **manual** (user hand-draws post-generation).

For generation: prompt auto-clause baked into `scripts/onepass_gen.py`: "generate blank plaques/signage without text; text will be added as a vector layer."

## Why This Matters

Diffusion models struggle with legible, well-formed text. Generated signage:
- Warps or distorts letter forms
- Mixes characters (8→B, illegible smears)
- Breaks readability in scale or rotation
- Multiplies handoff friction: user must repair or replace

Vector text avoids all these: clean, editable, scalable, integrates seamlessly in final SVG/artwork.

## Implementation

**In generation prompts:** auto-append → "blank/empty plaques and signage areas with no text; text will be added as a separate vector layer"

**In workflow:**
1. Generate with blank plaques
2. Approve geometry + painted elements
3. In Illustrator: add text as vector layer above image layer
4. Export final artwork with integrated vector text

**Code:** `scripts/onepass_gen.py` includes this clause automatically; never remove it.

## Related

- [[concepts/no-painted-text-vector-layers]] (memory record)
- [[index]]
