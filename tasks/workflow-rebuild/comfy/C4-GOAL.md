# C4 GOAL — ComfyUI round 4 (2026-07-06, leader: opus session 7956ac39)

Finish GOAL.md done-means #2 + #3: head-to-head board vs round-3 gpt-image
baseline + measured verdict. Plus run the 3 queued experiments.

## Arms (focused matrix — pruned by C1-C3 findings: endpct 0.8 best from-scratch,
## rich ref >> abstract tiles, dualregion 0.9/0.9 = mud)
| arm | recipe | why |
|---|---|---|
| dr-55 | dualregion 0.5/0.5, seeds 100/300 | queued fix for 0.9/0.9 mud |
| dr-75 | dualregion 0.7/0.5, seed 100 | midpoint probe |
| comb-e8 | combined CN lineart 1.0 + IP 0.8, endpct 0.8, seeds 100/300 | best-known from-scratch |
| i2i-d5 | i2i init=approved raw, denoise 0.5, CN 1.0, ref w0.8, seeds 100/300 | proven recipe, fresh seeds |
| hires | best arm of above + --hires-scale 1.5 | queued retry now RAM free |

## Lanes
- R (leader bg): build+queue renders via scripts/comfy_build_workflow.py + comfy_run.py, serial through :8188.
- B (glm): locate round-3 gpt-image baseline (arm-g_s1 + door_fill numbers), write baseline-manifest.json.
- S (glm): SDXL canny lane feasibility — model files on disk? (checkpoints/controlnet for SDXL) → feasibility note.
- G (post-renders, cheap): door_fill gate + overlays per raw, then board build (ComfyUI arms row + round-3 baseline row + overlay row).
- Leader: vision-judge boards (overlay-only geometry verdicts), synthesize verdict #3, ask user feedback.

## Done means
1. ≥6 new raws with door_fill overlay gates.
2. ONE board: C4 arms vs round-3 baseline, overlay row included, in REVIEW/workflow-rebuild/round-c4/.
3. Written verdict: where ComfyUI beats gpt-image / where it loses. User feedback requested.

## Constraints
- MPS renders serial; boost job (realesrgan Vulkan) running concurrently — accept slower renders.
- Geometry verdicts by overlay ONLY. No painted text. Raws immutable once written.
