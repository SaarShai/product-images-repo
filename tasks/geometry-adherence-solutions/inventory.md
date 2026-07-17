# Repo capability inventory — mechanical geometry enforcement (lane A, 2026-07-17)

Compiled by Explore agent (haiku), raw data. Measured numbers from tasks/*/RESULTS,
VERDICT/DIAGNOSIS files, wiki.

| Asset | Path | Mechanism | Measured result | Limitation |
|---|---|---|---|---|
| controlnet_sdxl_gen.py | scripts/controlnet_sdxl_gen.py | SDXL inpaint + xinsir canny CN on SVG lineart; exact openings via white-on-black control + inpaint mask; full-bleed facade mode | region-IoU ~0.969 (DREAM1, space-np01-front-bottom-02); holes ~1.0 by construction via hard composite | Needs hard white-out composite for exact cutouts; drift ~0 only when kept regions masked out |
| punch_holes.py | scripts/punch_holes.py | Aperture-lock post-process: fill hole interiors clean + bevel ring; optional vignette halo flatten | Clean die-cut appearance on multiple candidates | Bevel tone sampled from output; weak on low-contrast bg |
| outset_cutouts.py | scripts/outset_cutouts.py | Buffer cutouts outward (shapely) as prompt-side keep-clear guide | FAILED as sole enforcement: mean_iou 0.120 princess-n02 | Advisory only; model ignores 71-98% on cutout-heavy panels |
| exact_bevel_composite.py | scripts/exact_bevel_composite.py | Re-seat openings at exact SVG coords with illustrated bevel; cover drifted opening w/ body-toned mottle | region-IoU 1.0 by construction (HYB1); white-IoU 0.795 | Style degrades (smears controls); last-resort |
| build_silhouette_base.py | scripts/build_silhouette_base.py | Open-path socket boundaries drawn + exterior flood-fill → exact silhouette | Verified on edge-socket panels | Needs polyline/line socket boundaries in SVG |
| build_trueaspect_base.py | scripts/build_trueaspect_base.py | Outer contour + solid-disc cutouts at true aspect on 9:16 letterbox | Aspect preserved 1:1 in subgen use | Cutouts solid discs; needs auto_bbox de-letterbox in scorer |
| svg_to_controlmap.py | scripts/svg_to_controlmap.py | Exact SVG → lineart/canny control map, viewBox-identical to svg_geometry_check | Authoritative control source for CN gen | Standalone; no downstream measurement |
| svg_geometry_check.py | scripts/svg_geometry_check.py | Gate: white-IoU per opening + silhouette fit; PASS/FAIL cutout_tol 0.03 | Caught 71.5-98.5% painted holes on failed runs | Fill-agnostic placement not measured |
| geom_iou.py | scripts/geom_iou.py | Fill-agnostic placement: flood region at opening centroid, IoU vs SVG polygon | 0.969 (space-np01); 0.578 (nano, aspect-confounded); gate ≥0.85 | Needs strong gradient edges; poor on soft fills |
| geom_gate.py | scripts/geom_gate.py | Deterministic hard-gate: fill_inside, edge_iou, per-role cutout/keep-clear, overflow; exit 0/1 | Pipeline guard before VLM judge | Thresholds need per-project tuning |
| export_svg_template_fit.py | scripts/export_svg_template_fit.py | Clip art into SVG paths; fit metrics | Structural FP on rect/cutout-path templates FIXED at 40cbd70 | Historical PASSes pre-fix untrustworthy |
| measure_sdxl_cn.py | scripts/measure_sdxl_cn.py | Gate mirroring controlnet_sdxl_gen contract: region-IoU, coverage, per-hole painted | Feeds RESULTS-BOARD; hole_tol 0.03 | Only valid for that workflow |
| localgen.py | scripts/localgen.py | LOCAL SDXL inpaint (MPS): base + watercolor LoRA + IP-Adapter style ref + CN geometry lock, masked inpaint | NO measurements in repo — unmeasured on full panels | Needs .venv-gen + ~/models-gen/ weights |
| geom_adherence_test.py | scripts/geom_adherence_test.py | Orchestrator: gen → auto-register → measure → JSON row | Used in princess-n02 evidentiary run | No rollback on failure |
| region-map-guide (skill) | skills/region-map-guide/ | Semantic color-region map + legend → placement lock | Fire-station: drift ~26%→~5%; gpt-image 0.009-0.12% overlap | ONLY openai/gpt-image respect maps (nano rejected 2026-07-12); map aspect locks output |

## Absent capabilities

- **Post-gen socket composite-back** (finding C): only composite_window.py (PRE-gen
  embed) exists; no post-gen socket re-masking/composite tool. Blocks "0 cutout
  violations" on fixed-element panels.
- Watercolor LoRA training (inference only; weights external).
- IP-Adapter training (inference only).
- Nano/Gemini as geometry-disciplined provider (rejected on region maps).

## Best confirmed geometry PASS

space-svg-exports-batch procedural runs: outside=0, cutout=0, coverage 98-100% —
but style simulated, not model-generated. Confirms: geometry solvable; the open
problem is geometry+style in one model-generated output.
