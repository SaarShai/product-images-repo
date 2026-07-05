---
name: studio-defect-repairer
description: "Repair a specific defect in a generated panel (malformed element, painted hole, halo, text artifact) via bounded correction rounds with measured gates — never unbounded retry, never self-judged success."
effort: medium
---

# defect-repairer — bounded, measured correction loops

Promoted 2026-07-05 after gpt-5.5 read-critique + execution sim. History: `../DRAFT-defect-repairer.md`.

## Loop contract

Max 3 rounds per defect. A round "improves" iff it WINS the pairwise judge vs the previous round on the defect criterion (`python3 scripts/judge.py --mode pairwise --image <new> --ref <prev> --criterion "<defect>"` — output is winner/consistent; there is no numeric style_delta). Two consecutive non-wins → STOP, switch engine or entry, or escalate to human. Never round 4.

## Entry routing (defect → tool)

| defect | route |
|---|---|
| ONE malformed element | `python3 scripts/edit.py --src <img> --op redraw|remove --element "<name>" --desc "<fix>" --out <out>` (automask→guardrail→diffmask→judge built in) |
| erase object/text | `falgen.py --mode eraser` (flux-fill negatives are weak); overlay-verify the mask first |
| painted die-cut hole | `python3 scripts/punch_holes.py --gen <png> --svg <svg> --out <png> --halo` |
| grey edge-halo / wispy lines | `python3 scripts/dehalo.py --image <in> --out <out>` (reports whitened% + protected_px); PASS = VLM check "grey outline or wispy halo? YES/NO" answers NO on the OUTPUT; one retry with `--bright` −8, then escalate |
| blur/melt overall | whole-image re-upscale (`reupscale.py` 0.5/0.6), NOT per-defect surgery |
| geometry off | back to geometry-executor; repair edits can't fix silhouette |

## LAW 0 on every regen

Every regeneration call re-attaches the original inputs — control map / geometry guide AND style refs (or LoRA trigger). A correction prompt alone is prose-only generation: forbidden.

## Gates per round (all, in order)

1. `python3 -m studio.controlmap --score <cand> --mask <panel>-mask.png` — shape.
2. `python3 scripts/geom_gate.py --cand <cand> --mask <panel>-mask.png` — fill/holes (packet threshold field: `gates.geom_iou_min`).
3. Pairwise judge vs previous round (defect criterion).
4. Library writeback BEFORE gating verdicts: `python3 -c "from studio.library import add_result; print(add_result('studio/library_store','<img>',{'task':'<t>','round':N,'kind':'repair','engine':'<e>','verdict':'<v>'}))"`. No orphan images.

## Terminal states — evidence pack mandatory

fixed / no-improvement / unknown-defect all require: original + every round + overlays + gate JSONs + judge verdicts + library ids, contact-sheeted via `scripts/contact_sheet.py`. "Present best" without the pack is a self-judged claim: forbidden. Human closes the defect, not you.
