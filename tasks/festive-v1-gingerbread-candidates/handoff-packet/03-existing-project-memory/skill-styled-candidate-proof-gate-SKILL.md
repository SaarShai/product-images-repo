---
name: styled-candidate-proof-gate
description: Gate styled generated image claims
status: proposed
source: tasks/festive-v1-gingerbread-candidates/retrospective-styled-oversight-rationale.md
learned_at: 2026-07-08
requires_tools: 
disable-model-invocation: true
auto-install: false
---

# styled-candidate-proof-gate

> **Proposed skill** — born from `/learn`. Slash-only until trusted: it will NOT
> auto-fire. Promote with the telemetry-gated gate once usage proves it out:
> `python3 skills/learn-skill/tools/learn.py promote --name styled-candidate-proof-gate` (needs N
> consecutive recorded hits, no trailing abort — see `learn-skill/SKILL.md` → Trust).

## When to Use
Use when a Screenery/template image task asks to show styled generated images, styled candidates, reference-style options, or final-looking watercolor candidates after geometry-safe roughs or procedural previews already exist.

## Procedure
1. Identify the exact user-facing claim: styled generated image, style-matched
   candidate, or reference-style option.
2. Prove method provenance before looking at geometry: the candidate must come
   from image generation with actual reference images or style-packet sheets
   attached, or from an equivalent style-generation tool; local Pillow/SVG/
   procedural output is only a composition map.
3. Inspect the actual image visually against the reference packet: object
   vocabulary, watercolor texture, line/edge behavior, lighting, density, and
   material language must match, not just palette.
4. Check semantic constraints from the task, such as no houses/windows/doors/
   text inside gingerbread decoration cutouts.
5. Only after style and semantic gates pass, run exact geometry containment/mask
   verification.
6. In the report, separate raw styled redraws, exact-masked previews, and old/
   stale procedural roughs by filename so the user can tell what they are seeing.

## Pitfalls
Do not let zero outside-mask pixels stand in for style proof. Do not call a local/procedural preview styled because it uses watercolor-ish colors. Do not judge style from a board label or filename. Do not skip visual inspection of the rendered image. Do not bury old wrong-direction candidates among the corrected styled set.

## Verification
A claim of styled generated images passes only when the report names the attached reference/style-packet inputs, shows or cites the actual rendered images inspected, confirms semantic constraints, and includes a fresh exact-mask or containment command for the final preview/artwork. If eval-gate or an LLM judge is unreachable, mark that as NOT-RUN and use the manual rubric explicitly rather than claiming a judged pass.

<!-- Rationale (why this earns a skill) — scored by write-gate before commit:
# Rationale: Styled Candidate Proof Gate

This earns a narrow proposed skill because the oversight happened despite
existing broad style-packet and review rules. The repeated future trigger is
specific and high-risk: when a user asks to see "styled generated images" after
a geometry-safe rough set exists, the agent can mistakenly show mask-valid
procedural previews and claim they are styled.

The prevention needs a pre-claim proof gate because geometry verification and
visual style verification are different layers. The bad `d1`-`d6` candidates had
zero outside-mask pixels, but they were local Pillow procedural renders, not
reference-attached image-generation outputs. The corrected `styled-v1`-`styled-v3`
candidates used the actual reference screenshots/style packet as image inputs
to OpenAI generation, then ran exact mask containment afterward.

Future agents should run this gate before saying "styled generated image":
prove method provenance, inspect visual style against packet references, confirm
semantic constraints, then run geometry containment. This is project-specific
to Screenery/template image generation and should remain proposed/slash-only
until it earns usage.
-->
