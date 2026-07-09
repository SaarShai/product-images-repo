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
