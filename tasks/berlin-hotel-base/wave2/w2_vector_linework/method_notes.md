# w2_vector_linework Method Notes

## Goal

Construct a vector/linework-first replacement for the Berlin Ritz/Beisheim tower base, then rasterize it into a watercolor/ink patch composited only inside the wave-2 edit box:

- Source: `tasks/berlin-hotel-base/work/src.png`
- Edit box: `3162,2582,4082,2845`
- Output lane: `tasks/berlin-hotel-base/wave2/w2_vector_linework/`

## Method

1. Built a local SVG facade guide with:
   - regular front-face vertical piers,
   - three stacked rows of regular window groups,
   - a modest lower plinth,
   - a skewed right receding face with narrower window bays.
2. Rasterized the guide using deterministic PIL drawing at 4x scale for antialiasing.
3. Sampled color from the artwork itself:
   - limestone and glass values from the clean facade above the broken base,
   - plinth values from the quay edge.
4. Added watercolor texture by layering low-opacity stone washes, faint horizontal ink marks, blurred wash passes, and source-facade texture.
5. Composited the patch into a copy of the full 4192x3848 source image using only the allowed edit box.

No external image-generation engine was used in this lane.

## Attempts

- `v1`: Cleanest architectural plate. Strong piers, windows, plinth, and receding face, but visually too hard-edged/vector for the surrounding watercolor.
- `v2`: Softer wash and right-edge preservation. Still reads as a synthetic linework plate.
- `v3`: Recommended candidate. Same vector geometry, but reduced window opacity, stronger watercolor blur, and more sampled source-facade texture. Best color/style match of this lane, though it remains visibly vector-first.

## Assumptions

- The allowed edit box is the wave-2 default `3162,2582,4082,2845`, not the older y=2828 boundary.
- A deterministic vector/raster lane is useful as a structure/control candidate even if another worker produces a more organic generative repaint.
- Since the user asked for a missing architectural base, the design should suppress the old glass-hall/canopy read and favor regular stone facade continuation all the way to the plinth.
- Existing tree/bridge/water pixels outside the edit box must remain byte-identical; foreground details inside the edit box may be affected by the base repair.

## Visual Review

- Opened and inspected `w2_vector_linework_zoom_board.png`.
- `v1` and `v2` are valid structural attempts but are not the recommended pick because their ink/window shapes look too crisp.
- `v3` is the recommended pick for judging because it is softer and more source-textured while preserving the vector-first structure: piers, regular windows, plinth, and the right receding face.

## Verifier

All full-res candidates are 4192x3848 and passed the wave-2 region-only verifier:

```text
PASS candidate=tasks/berlin-hotel-base/wave2/w2_vector_linework/w2_vector_linework_v1_composited.png box=3162,2582,4082,2845 outside_max=0 outside_nonzero=0 inside_nonzero=715072
PASS candidate=tasks/berlin-hotel-base/wave2/w2_vector_linework/w2_vector_linework_v2_composited.png box=3162,2582,4082,2845 outside_max=0 outside_nonzero=0 inside_nonzero=713562
PASS candidate=tasks/berlin-hotel-base/wave2/w2_vector_linework/w2_vector_linework_v3_composited.png box=3162,2582,4082,2845 outside_max=0 outside_nonzero=0 inside_nonzero=713205
```

Full command transcript is in `verifier_output.txt`.
