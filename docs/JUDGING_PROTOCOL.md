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

## Cross-model judge panel (codex + GLM + Claude) — validated
All-Claude judging shares blind spots (the "3 independent judges" were 3 Claude instances). A cross-MODEL
panel catches what one model family misses. All three are vision-capable (verified):
- **Claude** — Workflow `agent()` / Agent tool (hi-DPI tiles).
- **codex GPT-5.5** — `scripts/codex_judge.sh "PROMPT" img...` (pipes prompt on stdin, image via `-i`;
  needs the codex app/auth open on the device or it hangs).
- **GLM-5.2** — the `glm-executor` subagent (Read the image; it sees pixels).

PROVEN on the exact cases Claude missed: the EW-B2 **double-window** (Claude counted 1 on tiles) → both
codex and GLM counted **2** on the whole-panel context; nano-G3winin **poor proportions** (Claude scored
~90) → both codex and GLM flagged proportions 2/5 + the specific defects (skinny central tower, oversized
window, top template-line artifact).

Rules:
- **One image per call. Do NOT pass A/B pairs** — GLM flipped its verdict on an A/B comparison (label swap),
  then judged correctly on the single image. Comparative pairs risk a swap.
- **Objective defects (count/duplicate/crop/structural proportions) are reliably cross-model-catchable** →
  run codex + GLM (+ Claude) and take the UNION of real flags.
- **Style score still varies across models** (codex style 4 vs GLM 2 on the same image) → style stays
  advisory; PROPORTIONS + structural defects do not.
- **Model DISAGREEMENT is the signal to escalate to the human.**

## Judge against the GEOMETRY SPEC, not a generic prior
A judge with no geometry context scores against its own idea of what the panel "should" look like —
that is how the trapezoid doors passed an eyeball check (the model's prior said "arched poster," and a
tapered building looks arched). **Every geometry judgment must be handed the panel's spec**, the single
contract emitted from the SVG by `scripts/skyline_panel.py --mode spec` (also dropped beside every guide
as `<guide>.spec.json`). The spec gives the judge the exact: `aspect` (+ `aspect_tol`), `contour`
("domed rectangle, fill edge-to-edge"), `saloon_arch_frac`, `keep_clear_lanes_frac`, and `must_not`
(taper/pinch, background in corners/sides, cropped base, focal feature in a keep-clear lane).

Judge instruction template (codex / GLM / Claude — one image per call):
> Here is the candidate and its geometry spec `{spec json}`. Score ONLY against this spec.
> Does the artwork fill the contour edge-to-edge (no taper/pinch/trapezoid, no background in the
> bottom corners or mid-height sides)? Is the gateway aligned to `saloon_arch_frac`? Is anything iconic
> inside a `keep_clear` lane? Is any landmark base cropped? Report each `must_not` as pass/fail.

The deterministic `--mode check` (side-fill/taper gate) is the floor; the spec-anchored VLM judges are
the ceiling. Run both; a `must_not` failure from either blocks acceptance.

## Tools
- `scripts/judge_tiles.py` — candidate → hi-DPI tiles + region crops + manifest.
- `scripts/judge_panel.py` — builds the packet (overlay + tiles + cutout crops + geometry floor) with the
  OBJECTIVE/AESTHETIC rubric + the ≥3-judge protocol baked into its instruction.
