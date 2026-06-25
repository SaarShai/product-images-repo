---
nid: ns21f0
title: "Subscription lane"
type: step
x: 660
y: 420
icon: "🎨"
summary: "subgen.py / falgen.py — multi-model candidates"
status: draft
tags: [generation, subscription, models]
---
# Subscription lane

The faster multi-model path for panels that don't need pixel-exact fit at
generation time. Run [[subgen-py|scripts/subgen.py]] (OpenAI + Nano Banana, the
subscription path) and `scripts/falgen.py` (Flux Fill / Kontext / Flux.2) to
produce candidates across models.

Both engines are still fed the style-packet references + the geometry guide
(reference beats prose), and the prompt still carries **no geometry words**. Fit is
recovered downstream rather than locked here.

Then fan out for multiplicity at [[fan-out|fan-out]].
