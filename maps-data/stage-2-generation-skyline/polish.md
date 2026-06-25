---
nid: nlrn41
title: "Polish chosen strategy"
type: step
x: 660
y: 300
icon: "🎨"
summary: "Full-res, ≥3 attempts of the chosen strategy, references + geometry guide fed"
gate: "≥3 attempts of the chosen strategy"
status: draft
tags: [generation, polish, skyline]
---
# Polish chosen strategy

Spend on the strategy picked at [[choose-strategy|choose-strategy]]. Produce a
**full-resolution** candidate set with **≥3 attempts** of that one strategy —
multiplicity over one-shot. Every attempt is fed reference IMAGES (1a style packet)
+ the geometry guide (1b), per law: reference beats prose. Keep the prompts free of
geometry words — name the skyline and the visual look, never the template, contour,
red zone, separator, or saloon arch.

Use [[subgen-py|scripts/subgen.py]] for the generation and `scripts/run_matrix.py`
to drive the ≥3-attempt experiment matrix; fan out in parallel with
`scripts/falbatch.py` where the engine supports it.

Gate: **≥3 attempts of the chosen strategy.** Then the candidate set goes to the
geometry overlay check.

Next: [[overlay-check|overlay-check]].
