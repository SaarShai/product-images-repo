# System build: SVG → exact-geometry styled illustration

GOAL: reliable, repeatable pipeline that makes an image model adhere to EXACT geometry
(contour + cutouts at precise coords, illustrated rims) + watercolor style, verified by
scripts/svg_geometry_check.py (mean white-IoU; target ≥0.9 vs gpt-image baseline 0.449).

## Stages (built / to build)
1. SVG parse + role classify — DONE: svg_geometry.py, svg_classify.py
2. Geometry → control maps (lineart / canny / filled) — partial
3. Generation w/ structural lock — UNDER TEST (ControlNet diffusers + ComfyUI)
4. Verify — DONE: svg_geometry_check.py (IoU + paint + overlay + json)
5. Loop generate→verify→select→refine — to design (loop-engineering)
6. Style (watercolor via IPAdapter / refs / gpt-image refine) — to test
7. Exact deliverable + skill wiring — to build

## Tracks (parallel)
| # | track | tool | status |
|---|---|---|---|
| T1 | diffusers ControlNet (structure lock) | local SD+MPS | running |
| T2 | hybrid: model art + exact illustrated-bevel openings (fallback) | PIL | running |
| T3a | Nano Banana 2/Pro adherence | agy | running (gen_agy fixed) |
| T3b | best-of-N gpt-image ceiling | codex | running |
| R1 | ControlNet recipe research | web | done (synthesis saved) |
| R2 | ComfyUI techniques wave 1 | web | running |
| R3 | ComfyUI exhaustive wave 2 | web | running |
| T4 | ComfyUI stand-up + ControlNet+IPAdapter run | ComfyUI | NEW |
| T5 | system + loop architecture spec | design | NEW |
| T6 | gpt-image refine combo (structure→style) | codex | after T3b frees codex |

## Decision gate
Pick the method with best mean_IoU AND acceptable watercolor quality AND repeatability.
Wire winner into PIPELINE.md + svg-geometry-style-illustration skill. Adopt/adapt ComfyUI ideas.
