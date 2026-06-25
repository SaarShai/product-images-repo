---
nid: nmsij2
title: "Build packet"
type: step
x: 400
y: 300
icon: "📦"
summary: "Run build_reference_style_packet.py; emit contact + exemplar sheets"
gate: "style-packet/ built (contact + exemplar sheets)"
status: draft
tags: [style-packet, tooling]
---
# Build packet

Compile the gathered refs into an attachable **style packet**. Run:

```
scripts/build_reference_style_packet.py tasks/<task>
```

This emits `tasks/<task>/style-packet/` containing the **contact sheet** (every ref at a
glance) and **exemplar sheets** (the representative crops that carry the style signal).
These are what an image-generation agent attaches to the model in Stage 2 — the packet
IS the reference, per core law 1.

**Gate:** `style-packet/` built (contact + exemplar sheets present).

Tool: [[build-reference-style-packet-py|build_reference_style_packet.py]].
Reached from [[gather-references|gather-references]] (and re-entered from
[[re-curate|re-curate]] on a rebuild); feeds [[inspect-packet|inspect-packet]].
