# Advisor consult 3 — socket composite-back policy (white-bg rect vs alpha-keyed arch)

Read-only micro-consult, one decision. Context: SYNTHESIS.md architecture;
experiment-1/PARAMS.md frozen card; Stage-C tool
experiment-1/scripts/composite_back.py already passes byte-exact + registration
fixtures.

Fact: the fixed element is an embedded raster in template.svg — a watercolor
arched stone-framed door, native 902x966, but the raster RECTANGLE includes its
white paper background around the arch (white corners above the arch shoulders,
white margin strip below). Placement rect (SVG units): 122.83,1572.21 ->
875.37,2378.14. The evidentiary contract says the fixed door element must
"survive untouched / be preserved and integrated (framed, not painted over)".
The user's banked aesthetic: openings/fixed elements integrated and painted-
framed by the art, not floating; "pasted sprite / collage" look = rejection.

Options:
A. Composite the FULL rect byte-exact (contract-literal). Risk: white corners +
   white margin read as a pasted white card on top of painted wall (cohesion
   gate flags; user rejects collage look).
B. Alpha-key the white bg off the raster (flood-fill white -> alpha, e.g.
   white_key approach with erode 0 / thresh ~246 — repo-proven on flat art)
   and composite ONLY the arch: painted wall shows in the ex-white corners;
   door interior pixels still byte-exact; "byte-exact" gate scoped to the arch
   footprint instead of the rect.
C. Hybrid: option B + require the GENERATION to paint a framing treatment
   around the arch (the neutral-fill zone in the init canvas shaped as the
   arch, not the rect, so the model paints wall right up to the arch outline).

Questions:
1. Pick A, B, or C for THIS experiment (cheap, reversible, measurable). Note
   Stage-A gens will run with the socket zone masked as the FULL rect (frozen
   card) — for B/C, is rect-masked gen + arch-only composite acceptable, or
   must the paintable mask itself become arch-shaped (asset rebuild)?
2. If B/C: exact keying guard so thin watercolor edges of the stone frame
   don't get eaten (the repo has a wrongly-removed-pixels gate precedent).
3. How should the socket byte-exact gate + registration gate be rescoped so
   they stay honest (no gate weakening) under the chosen option?
Answer decisively in <= 400 words.
