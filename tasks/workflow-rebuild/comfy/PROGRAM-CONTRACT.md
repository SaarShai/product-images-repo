# Program contract — what every round measures (pinned 2026-07-06 after user reset)

THE QUESTION: what is the best method/tool/model/workflow to generate panel art
FROM SCRATCH meeting the user's requirements. Not relock, not recreation-from-self.

## Requirements (fixed judging axes)
1. Geometry: art fits the SVG contour; door portal filled to its exact lineart; door_fill gate + overlay (overlay-only verdicts).
2. Style: soft transparent watercolor, storybook; judged vs reference examples.
3. Content richness: complete intentional building with characterful detail (teddy/dome/clock/topiary tier — arm-g_s1 is the bar).
4. Integration: cutouts/keep-clears painted-framed as design features; no painted text; door flaps carry only door content.

## Standings (from-scratch only)
| method | geometry | style | richness | verdict |
|---|---|---|---|---|
| gpt-image (round-3 arm-g) | good, drifts ~1-2% | excellent | excellent | CHAMPION |
| SD1.5 CN+IP (combe8) | exact | good | PLAIN | geometry proof only |
| SD1.5 dualregion | exact | mud | mud | DEAD |
| SDXL canny CN0.9/e0.8 (c5) | WARN 0.67-0.81, visible miss | good watercolor | RICH — teddy/domes/florals, champion-tier | richness solved; geometry weak; painted-text leak |
| SDXL canny CN1.0/e1.0 (c5b) | FAIL 0.36-0.62 | — | — | CONFOUNDED (IPAdapter dropped mid-run); lesson: canny-strength alone cannot hold die-cut — hard canny makes SDXL avoid edge-free regions |
| SDXL inpaint-mask + canny + IP (c5c) | FAIL 0.0 — all-white renders | — | — | Comfy SetLatentNoiseMask port failed; leader diagnosis: mask likely all-zero after ImageToMask (worker's white-init theory doesn't explain denoise-1.0 behavior); Comfy mask route parked |
| SDXL-inpaint diffusers script (c5d) | WARN 0.8955 (s100 only) | not judged | not judged | INCOMPLETE — the decisive open experiment. 1/4 seeds gated; best SDXL geometry yet but still sub-0.90 PASS. Uses PROVEN scripts/controlnet_sdxl_gen.py (region-IoU 1.0 history), bypassing ComfyUI's failed mask nodes. Finish per COMFY-RND-HANDOFF.md |

i2i-relock (baseline init + CN): NOT a contender — it's a salvage/finishing tool
for drifted champions. Keep, but never score it as from-scratch.

## Resume
Parked 2026-07-07. Full state + next steps: COMFY-RND-HANDOFF.md.

## Rule
Every new arm gets one row here. An arm that can't beat the champion on at least
one axis without losing another is retired, not re-tuned indefinitely.
