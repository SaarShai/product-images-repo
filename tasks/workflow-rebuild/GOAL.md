# GOAL — v2 panel-illustration workflow (workflow-rebuild)

## Master goal
Design + build a reference-first, geometry-controlled, user-in-loop generation
workflow: template SVG + theme in → approved panel set out. Each step produces a
REFERENCE ARTIFACT (image, not prose) that feeds the next step. Validated on the
hospital DOOR panel (E5 = baseline to beat). Collection-generic; hospital = test case.

LAW 0 (unchanged): references beat descriptions. The rebuild's core move is
DECOMPOSING style into separable reference images:
1. **art medium** ref (e.g. transparent watercolor, visible-but-mild texture/bleed)
2. **dominant palette** ref (hospital-white+red+blue; police red+blue+black+white; fire red+yellow)
3. **illustration style** ref (toy-like, blocky right-angled, colored lineart, rounded plush)
4. **features & details** refs (teddy characters, windows, sirens, medical kit …)
plus **geometry refs** (contour + feature-placement annotations) for composition control.

User is DECIDER on all property choices (brainstorm → selection boards → M/N/X).

## Style guidelines to encode (user, turn-54)
- **Complete/self-contained building**: edges intentionally drawn, not cropped;
  slight (<~2% width) detail overhang past silhouette = plus. Exemplars: space
  narrows, princess (partly), E5/E9.
- **Top-contour freedom**: dome border in template = BOUND, not shape mandate.
  E7's central tower > plain dome (tower height right because within dome border;
  its side roofs too low for top sub-panel; sky background not needed). Generalize:
  any architectural top that fills the bound intentionally.

## Phases
- **P1 RESEARCH (running)**: lanes R1/R1b (ref-image conditioning), R2 (ComfyUI/fal/
  platform patterns), R3 (geometry+annotation conditioning), R4 (internal evidence
  mine), R5 (exemplar harvest). Outputs → tasks/workflow-rebuild/research/.
- **P2 SYNTHESIS (leader)**: research → WORKFLOW-SPEC.md — step DAG, per-step
  input/output/owner/gate, reference formats, experiment matrix.
- **P3 USER REVIEW**: spec markup + property brainstorm boards (user decides).
- **P4 BUILD (delegated)**: ref-builder tools, guides, gates. Verified before permanent.
- **P5 EXPERIMENT**: wide matrix on DOOR panel, cheap models first, learn what works.

## Lane goals (P1)
- R1 /goal: per-model truth table of how ref images are consumed (count, role,
  weighting, params, failure modes) + ref FORMAT best practice.
- R1b /goal: same, official-docs-only sweep (OpenAI/Google/BFL/fal) — overlap on purpose.
- R2 /goal: portable multi-step reference-pipeline patterns from ComfyUI/fal/MJ/Recraft.
- R3 /goal: ranked geometry/layout-control techniques + guide-construction recipes.
- R4 /goal: evidence table of OUR OWN geometry/ref successes+failures + tool inventory.
- R5 /goal: labeled exemplar contact sheets for the two style guidelines.

## Status
2026-07-06: P1 fleet dispatched. Ledger rows S78–S89.
