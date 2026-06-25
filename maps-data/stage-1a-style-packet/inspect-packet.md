---
nid: nyd8ax
title: "Inspect packet"
type: decision
x: 660
y: 300
icon: "🔍"
summary: "Does the packet capture the REAL art style, not just palette?"
status: draft
tags: [style-packet, review, gate]
---
# Inspect packet

A human reviews the built packet and answers one question:

> Does it capture the **object vocabulary, line weight, density, lighting, and
> material** of the target style — not just the palette?

A packet that only matches color is the classic failure mode that produced geometry-correct
but style-wrong outputs downstream (the reason the `reference-style-packet` skill exists).
So the bar is the *real* art style, not a color swatch.

- **No** → the packet has a gap; go [[re-curate|re-curate]] the refs and rebuild.
- **Yes** → proceed to [[packet-approved|packet-approved]].
