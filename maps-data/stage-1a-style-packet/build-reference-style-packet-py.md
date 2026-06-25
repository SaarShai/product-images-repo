---
nid: nmysrb
title: "build_reference_style_packet.py"
type: reference
x: 400
y: 450
icon: "🛠️"
summary: "Tool: refs/ → style-packet/ (contact + exemplar sheets)"
status: draft
tags: [tool, style-packet]
---
# build_reference_style_packet.py

The tool that builds the packet. Given a task directory, it reads `tasks/<task>/refs/` and
emits `tasks/<task>/style-packet/` with the contact sheet and exemplar sheets.

```
scripts/build_reference_style_packet.py tasks/<task>
```

Cited path: `scripts/build_reference_style_packet.py`. Drives [[build-packet|build-packet]].
Companion: the `reference-style-packet` skill (SOP for turning refs into a style packet).
