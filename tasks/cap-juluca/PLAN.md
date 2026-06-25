# PLAN — Cap Juluca sub-panel illustrations

Family **A — SVG-template / die-cut panel**. Run stages in order; each emits a reviewable artifact
and passes its gate before the next. Per-stage detail: `docs/PIPELINE.md`.

## Stages
- [ ] 0 INTAKE & PLAN — this packet. GATE: you review plan + refs before spend.
- [ ] 1a STYLE PACKET — build_reference_style_packet.py. GATE: packet captures real style.
- [ ] 1b GEOMETRY — svg_geometry_report.py + guide. GATE: guide aspect==panel, coords verified.
- [ ] 2 GENERATION — multi-model x multi-prompt x >=3 attempts/variant, ref+geom-fed. GATE: deterministic gates.
- [ ] 3 SELECT — judge.py + full-size board. GATE: metric + vision judge + your pick.
- [ ] 4 REPAIR/REFINE — edit.py / mask-bounded donor. GATE: outside-mask delta==0, leak<0.06, judge.
- [ ] 5 FINALIZE/EXPORT — export_svg_template_fit.py --require-pass + sync_results. GATE: 0 px outside masks.

## Multiplicity rule (Stage 2)
For every input variation: >=3 attempts, >=2 models/prompts where it applies.
Prioritize a spread of candidates over a one-shot. Show all at full size.

## Gate ledger
- [ ] Stage 0 plan + refs reviewed by user
- [ ] 1a STYLE PACKET — build_reference_style_packet.py. — gate met
- [ ] 1b GEOMETRY — svg_geometry_report.py + guide. — gate met
- [ ] 2 GENERATION — multi-model x multi-prompt x >=3 attempts/variant, ref+geom-fed. — gate met
- [ ] 3 SELECT — judge.py + full-size board. — gate met
- [ ] 4 REPAIR/REFINE — edit.py / mask-bounded donor. — gate met
- [ ] 5 FINALIZE/EXPORT — export_svg_template_fit.py --require-pass + sync_results. — gate met
