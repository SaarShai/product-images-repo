# EVIDENTIARY RUN — geometry workflow, held-out panel: princess narrow 02

Frozen 2026-07-17 BEFORE execution, per skills/evidentiary-run/SKILL.md.
Repo HEAD at freeze: 7a2d4ea. Question under test: is the repo's
geometry-following image-gen a production workflow a cold agent can execute,
or a set of demonstrations?

## Frozen inputs
- Template SVG (held-out: zero references in tasks/ or REVIEW/):
  `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/princess/princess narrow panel 02 with window.svg`
  sha256 b4f424f66aa921a83e4bc66e23d06de2b04427b8d0712104471a6a8ae1633e60 (1,572,953 B).
  Contains an EMBEDDED RASTER arched door image = fixed element (freeze: preserve/frame it;
  parser failure on it = valid evidence, not rescue grounds).
- Style refs (collection refs, NOT target-derived — hold-out rule):
  `…/princess/Images/princess style 01.png` sha256 cda9f0040f82a0e7…
  `…/princess/Images/princess style 02.png` sha256 9779cea4364dc1fc…
- FORBIDDEN inputs: every file matching `*narrow panel 02*` / `*n02*` in
  `…/princess/Images/` (existing art of THIS panel). Reserved for the judge's
  post-hoc ground-truth comparison ONLY.

## Frozen procedure
Cold executor agent (did not design this test) follows
`skills/svg-geometry-style-illustration/SKILL.md` steps as written
(scaffold_template_task.py → svg_geometry_report.py → outset_cutouts.py
--outset 30 → build_trueaspect_base.py 1440x2560 → build_reference_style_packet.py
→ geom_adherence_test.py → export_svg_template_fit.py --require-pass →
sync_results_images.py). Task dir: tasks/geometry-evidentiary-princess-n02/.
Executor resolves placeholders from this contract only. Skill ambiguity or
tool failure = FINDING (freeze + report), never improvise around it.
Measure IoU/violations BEFORE any enforcing mask/composite (no tautological gate).

## Frozen acceptance criteria
1. Outside-silhouette + cutout-violation pixels: 0.
2. Silhouette/region-IoU vs template spec: >= 0.95 (measured, overlay attached).
3. Overlay vision judge: ACCEPT (raw metric alone insufficient).
4. Style judge vs frozen refs: ACCEPT (side-by-side, per style-match rule).
5. Fixed door element preserved and integrated (framed, not painted over/deleted).
6. Safe-stop case: one run invoked with ZERO style refs must refuse with a named
   signal (`style.ref_images must contain at least one path` or nonzero exit) —
   proves the precondition is mechanical, not advisory.
7. Claim ceiling: "production-capable on one held-out panel" max. Never "validated".

## No-rescue clause
No mid-run parameter tuning, no threshold changes after seeing outputs, no
manual pixel fixes. FAIL → freeze artifacts → DIAGNOSIS.md (FP vs real split)
→ patches land only with regression fixtures → re-gate frozen artifacts.
Human verdict recorded in VERDICT.md.
