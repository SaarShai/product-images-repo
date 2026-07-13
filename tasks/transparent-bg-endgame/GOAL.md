# GOAL — Transparent-background pipeline, solved once and for all

Owner session: 2026-07-12 (Fable 5 orchestrator).

## End state (done means)
A single documented, gated, repeatable pipeline that produces **high-res RGBA
images with faultless transparent backgrounds** usable in Illustrator print
layers (`~/Documents/screenery-lean`, spot-white underlay, colored panel shows
through). "Faultless" = passes ALL defect gates below AND user visual sign-off.

## Defect classes — every one gets its OWN measured gate (memory: gate-per-visible-defect-class)
1. **Bright-edge / semi-transparent halo** — dehalo_edge + dark-composite gate (memory: dehalo-gate-mandatory). Judge on dark/colored composite, never white.
2. **Holes in objects** (removal ate real art) — deleted-art recall, stratified by feature thinness (memory: flood-bria fusion; skill: chroma verify harness).
3. **Trapped background pockets** — enclosed-pocket count (global key kills these by construction; flood-fill does not).
4. **Painted aura/glow** (opaque pigment halo; alpha gates blind to it) — `scripts/aura_gate.py`.
5. **Edge color contamination** (green/key spill) — despill band check + recomposition error.
6. **Canvas-edge crops** — 3px border-strip occupancy (memory: never-crop-canvas-edges).
Machine pass = PENDING_HUMAN_REVIEW, never final. Composite on white/gray/black/magenta + panel-colored bg.

## Key thesis to validate (Fable analysis, needs testing)
At print resolution, **binarized (hard/non-anti-aliased) alpha is invisible**:
a 1px jaggy at ~4000px on a ~40cm panel ≈ 0.1mm at 300dpi. Halos exist ONLY
in partial-alpha edge pixels + contaminated edge RGB. So: hi-res → threshold
alpha to binary → decontaminate edge RGB (unmultiply vs known bg) should be
structurally halo-proof. Explore per user's explicit ask: **non-anti-aliased
edge generation + hard-alpha post-processing — a matrix of edge types.**

## Lanes
- L1 branch/stash forensics → disposition of `retrospective-band-panel-workflow` (+stash@{0}) and `transparent-clear-edge-workflow`.
- L2 session mining → timeline of every prior attempt + outcome (claude desktop + codex sessions).
- L3 repo prior-art inventory → tool/status/evidence table + gaps.
- L4 web research → SOTA transparent gen, matting/despill, print-prep, hard-edge techniques.
- L5 advisor (GPT-5.6 Sol Ultra via codex) → architecture critique + experiment matrix.
- L6 experiment matrix → run arms incl. non-AA edges; gate; REVIEW folder for user.
- L7 consolidate → ONE canonical pipeline script + skill update + wiki + commit.

## Standing gates instantiated from memory (pre-flight)
- Geometry/edges judged by overlay/1:1 crops only; judges get hi-DPI crops.
- Reference images (not prose) drive style; hold out ground-truth style ref.
- Results → `REVIEW/transparent-bg-endgame/` (single inbox, full abs paths, fullres/ subdir, filename = link text).
- Show results early; one candidate → user gate → then batch.
- Keyability language in every gen prompt (thin/pale features must be keyable).
- Economy: Fable = think/judge only; labor → codex/GLM/ollama/sonnet-tier.
