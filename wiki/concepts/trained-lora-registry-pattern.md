---
schema_version: 2
title: "Trained LoRA registry pattern: per-collection lora.json"
type: fact
domain: image-gen
tier: procedural
confidence: 0.9
trust: verified
created: "2026-07-05"
updated: "2026-07-05"
verified: "2026-07-05"
sources: [".brainer/tenx/lora-pilot/ONEPASS-FINDINGS.md", "commits 53f2e2e/7041dd4"]
resource: "scripts/onepass_gen.py"
supersedes: []
superseded-by: []
contradicts: []
tags: ["lora", "style-transfer", "registry", "flux", "training", "collection"]
---

# Trained LoRA registry pattern: per-collection lora.json

## Summary

**Each art collection carries a per-collection `lora.json` registry** of trained style LoRAs. Schema:
- `lora_url` (string): fal-ai LoRA model URL or local path
- `trigger_word` (string): activation token in prompts (e.g., "CJWC" for Cap Juluca watercolor)
- `status` (enum): "COMPLETED" | "IN_TRAINING" | "FAILED" | "CANDIDATE"

**Use rule:** LoRA is usable in generation iff `status == "COMPLETED"`.

## Why This Matters

Trained style LoRAs (custom fine-tunes on brand style, color palette, medium) are the foundation of one-pass geometry+style generation. Without a registry, agents:
- Re-train duplicate LoRAs
- Use in-progress models (training still running; weights unstable)
- Lose track of which LoRA applies to which collection
- Can't batch-reuse across tasks

Registry + status gate = repeatability + cost savings + quality consistency.

## Schema Example

```json
{
  "lora_pilot": {
    "collection": "cap-juluca",
    "lora_url": "https://fal-sandbox.s3.us-west-2.amazonaws.com/...",
    "trigger_word": "CJWC",
    "status": "COMPLETED",
    "created": "2026-07-04",
    "training_time_minutes": 45,
    "base_model": "flux-pro",
    "notes": "3-panel architecture, watercolor + ink, multicolor palette"
  },
  "marriott-lora": {
    "collection": "marriott",
    "lora_url": "https://fal-sandbox.s3.us-west-2.amazonaws.com/...",
    "trigger_word": "MRCH",
    "status": "COMPLETED",
    "created": "2026-07-05",
    "training_time_minutes": 60,
    "base_model": "flux-pro",
    "notes": "hospitality watercolor, muted earthy palette"
  }
}
```

## Workflow

1. **Before onepass generation:** query `lora.json` for target collection
2. **Check status:** if not "COMPLETED", escalate (training in progress) or re-train
3. **Inject trigger word + lora_url** into onepass_gen.py parameters
4. **Log result:** update status field if training finishes or fails

## Related

- [[concepts/onepass-geometry-style-route-flux-control-lora]]
- [[index]]
