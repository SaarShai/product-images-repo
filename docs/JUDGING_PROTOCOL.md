# Judging protocol (fixed after the princess-window judge failures)

VLM judge subagents failed in two ways; this is the corrected, evidence-based protocol.

## Failure modes observed
1. **Hallucination on tall/large images.** A judge handed the whole 1024×2301 panel scored a
   plainly-present mid-height window "ABSENT (12) + bottom gate." Cause: the Read tool DOWNSAMPLES;
   a mid-panel feature becomes a few px → the model answers from a style-prior. Same image, a HIGH-DPI
   CROP → correct (present, 82/90/88).
2. **Aesthetics not rankable.** 3 reference-anchored judges scored a POOR-style gen and a GOOD-style gen
   the SAME (~72–82 style, ~74–80 proportions). VLMs cluster on "looks like the genre" and miss
   artist-level refinement. The human's eye disagreed sharply with the judge.
3. **Duplicate / over-count missed.** A gen-edit ("enlarge the window") ADDED a second stacked window
   instead of enlarging the one; it was presented as a strong candidate because (a) the gate was not run
   (eyeballed), and (b) even the rubric had no element-COUNT check — it asked "is the window present &
   positioned" (yes) but never "is there exactly ONE." The hi-DPI fix cures *under*-detection ("absent");
   a duplicate is *over*-count, the opposite error, and needs its own check. Double-door/double-window is a
   recurring mode (the model paints its own gate/window on top of the intended one).

## Protocol
1. **Never judge the whole tall image alone.** Run `scripts/judge_tiles.py` → hi-DPI tiles (+ region
   crops, + a downscaled `context.png` for composition only). `judge_panel.py` now emits these in the
   packet. Presence/position/detail/edge checks read the TILES.
2. **≥3 independent judges**, reference-anchored to the gold example. Report per-metric **median + spread**.
   On disagreement (wide spread), a **human verifies** — do not average past a conflict.
3. **OBJECTIVE vs AESTHETIC split.**
   - OBJECTIVE (gate on these — judges ARE reliable on hi-DPI tiles): fill-to-contour, cutout/hole-fit,
     keep-clear, top-contour, feature present+faithful+positioned, margins/seams, **edges-organic**
     (full-bleed, no drawn arch-frame, no white-background panel, no hard straight cut), **element-count /
     no-duplicates** (exactly the specified number of windows/doors/gates — a single-window panel = ONE).
     In the princess test all 6 judges independently caught the arch-frame + white-bg + sharp edges — these
     gate well.
   - AESTHETIC (advisory only → HUMAN decides): style refinement, proportions, taste. Never auto-PASS on
     these; always show the human full-size.
4. **COUNT on the whole-panel view, not on tiles.** Report `window_count`. Presence ✓ is not enough — a
   duplicate passes a presence check. **Count from the downscaled full `context.png`** (large elements
   survive downscale and every instance is visible at once); use tiles only to confirm each instance is
   real. Counting from tiles is actively WRONG: tiling splits a duplicate across a seam, each tile shows
   one, and the overlap makes you read the 2nd as the "same instance continuing" — this is exactly how two
   stacked windows passed even *after* the count metric was added. (Proven: tiles → count 1; context → count 2.)
5. **View the WHOLE candidate, not just the expected-feature zone.** A zone crop centered on where the
   element *should* be will clip a duplicate that appears elsewhere (this is the original way the 2nd window
   was missed).
6. **Never declare a "winner" by eyeballing sub-metrics.** Run the gate first; quote the verdict; for
   aesthetics, defer to the human. **Surface every anomaly you notice — never silently drop it.**

## Tools
- `scripts/judge_tiles.py` — candidate → hi-DPI tiles + region crops + manifest.
- `scripts/judge_panel.py` — builds the packet (overlay + tiles + cutout crops + geometry floor) with the
  OBJECTIVE/AESTHETIC rubric + the ≥3-judge protocol baked into its instruction.
