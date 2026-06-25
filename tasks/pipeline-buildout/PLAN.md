# PLAN — pipeline buildout (make the lifecycle bulletproof, stage by stage)

Goal: turn the fragmented per-family tooling into one staged lifecycle (see
`docs/PIPELINE.md`) that an agent follows from a cold brief to a delivered image,
with a reviewable artifact + gate at every stage. Harden stages in pipeline order
(0→5), with the user in the loop at each stage gate.

## Sequence (user-chosen: front-to-back)
- **Phase 1 — Architecture (this session):** lock the stage model. Artifact: `docs/PIPELINE.md`. GATE: user redlines the spine. ← awaiting review
- **Phase 2 — Stage 0 Intake (universal):** build a task-type classifier + universal BRIEF/PLAN generator that works for ALL families (not just SVG-template). Prove on 2 real briefs: one template task + one repair task (berlin). GATE: plans are correct & complete.
- **Phase 3 — Stage 1 Constraint prep:** harden references→style-packet (1a) and geometry (1b). Mostly exists; verify + fill gaps. GATE: packet captures real style; guide aspect==panel.
- **Phase 4 — Stage 2 Generation:** standardize the multi-model × multi-prompt × ≥3-attempts matrix as one command with a contact sheet. GATE: ≥3 attempts/variant, full-size board.
- **Phase 5 — Stage 3 Select:** confirm the gate chain (deterministic → vision judge → human full-size).
- **Phase 6 — Stage 4 Repair (the bottleneck):** solve the 3 open problems — sharpness harmonization, reliable single-element regen-and-composite, integration. Pilot Qwen-Image-Edit-2509 + ComfyUI Flux-Fill+Differential-Diffusion. Vehicle: finish the stuck berlin-hotel task. GATE: user accepts a berlin fix that previously failed.
- **Phase 7 — Stage 5 Export + skill capture:** confirm export/log; capture each hardened stage as/into a skill so the next agent skips discovery.

## Principles
- Reduce/simplify: index & consolidate existing docs; do NOT rewrite working tooling.
- Reference-beats-prose at every gen step. Multiplicity over one-shot.
- Reviewable intermediate + gate per stage; user confirms before next stage.
- Each solved stage → a skill.

## Open questions surfaced
- Stage model order (1a parallel with 1b; geometry conditional; explicit gate+export) — awaiting user confirm on `docs/PIPELINE.md`.
- Stage 4: invest in local ComfyUI/Qwen stack vs API-only — decide at Phase 6 after a spike.
