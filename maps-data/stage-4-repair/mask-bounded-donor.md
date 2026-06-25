---
nid: n97dj2
title: "Mask-bounded donor"
type: reference
x: 660
y: 570
icon: "📄"
summary: "Concept: external redraw donor with separate generation- and blend-masks"
status: draft
tags: [concept, donor, repair]
---
# Mask-bounded donor

The documented concept behind the ghost/haze branch: repair a broad artifact in a busy scene
by generating a clean external redraw and harvesting only the masked region as a donor patch.

The key rule is **two masks, not one**: a wide *generation mask* gives the donor model enough
surrounding context to paint a coherent region, while a tight *blend mask* governs what is
actually composited back. Separating them is what stops the blend from seaming — conflating
them is the classic failure.

Cited source: `wiki/concepts/mask-bounded-external-redraw-donor.md`. Governs the
[[donor|donor]] step.
