# studio-executor — v2 pipeline executor skills (repo-local)

Four executor skills for the studio v2 pipeline, written for everyday (non-frontier)
models: exact verified commands, deterministic gates, no room to improvise.

**PROMOTED 2026-07-05** after two-stage validation: gpt-5.5 read-critique (top-8
fixes applied) + gpt-5.5 execution sim (3 fixes applied). The `DRAFT-*.md` files
are the history layer (body + review amendments); the promoted skills distill them.

| skill | job |
|---|---|
| [intake-classifier/SKILL.md](intake-classifier/SKILL.md) | task → family → VALIDATED PanelPacket (studio/packet.py) |
| [geometry-executor/SKILL.md](geometry-executor/SKILL.md) | spec → guide → control map → deterministic gates |
| [style-executor/SKILL.md](style-executor/SKILL.md) | one-pass control+LoRA gen, ref-anchored restyle, style-board judging |
| [defect-repairer/SKILL.md](defect-repairer/SKILL.md) | bounded measured correction loops per defect |

Shared laws: LAW 0 references-not-prose (geometry AND style AND restyle channels);
LAW 1 measured geometry overrides VLM; two-gate acceptance (shape + vision);
blank signage always (text = .ai vector layer); results → library; human arbiter
on aesthetics and promotion to finals.
