# Candidate lessons (pre-sieved, NOT yet written)

Cap for retrospective: ≤3 durable writes. Many items below should **drop** or **patch existing** memory.

Legend: **NEW?** = not clearly covered by existing gate/skill/wiki in this packet.  
**DEST?** = suggested destination before write-gate.

---

## Already banked (do not re-create)

| Lesson | Where |
|--------|-------|
| Cutouts are decoration slots; no houses/windows/doors inside | `03/CORRECTION-GATE.md`, wiki `gingerbread-panel-cutouts-decoration-slots` |
| Procedural/mask-valid ≠ styled; need reference-attached generation | `03/skill-styled-candidate-proof-gate-SKILL.md`, `03/RETROSPECTIVE-styled-oversight.md` |
| Soft interiors + black bg → blurry upscale; cream + fal clarity wins | `03/upscale-research-DIAGNOSIS.md`, wiki upscale workflow |
| Magenta Stage A 8× + Stage B detail C recipes | `DIAGNOSIS.md` Stage A/B |
| Candy-creative Stage C recipe (params) | `DIAGNOSIS.md` Stage C — **but** Cursor session later rejected many outputs |

---

## Candidate 1 — Tree cutout: unmask vs redesign

**Lesson:** When a cutout graphic is “masked/cropped,” first restore the geometry-matched artwork **without** tight alpha crop; do not invent a new green-tree redesign unless the user still wants that after unmasking. User sequence: (1) ask green tree + candy + icing, (2) reject result, (3) “bring back original tree… NOT masked/cropped.”

**Applies when:** SVG/Illustrator cutout art looks clipped; user says “masked” or “cropped.”

**Trigger/symptom:** Tree (or other) cutout visuals truncated to a wrong bbox / missing icing border after composite.

**Evidence:** Cursor CORRECTIONS U07–U08; TIMELINE phase 4; prompts `opt-tree-green-candy.md`, `opt-tree-exact-silhouette.md` in `04/prompts/`.

**NEW?** Mostly yes as a **gotcha** (mask vs redesign order). Not a full skill.

**DEST?** wiki fact/gotcha under festive/gingerbread cutout compositing — or drop if too one-off.

**route-probe hint:** fact-shaped (gotcha), not multi-step procedure.

---

## Candidate 2 — Chimney = biscuit bricks (semantic slot)

**Lesson:** Top-right chimney cutouts take a **biscuit brick pattern**, not holly/candy dense fill like other slots. Edge-v8 brick-tree was approved.

**Applies when:** Festive gingerbread panel chimney / brick cutouts.

**Trigger/symptom:** User says “chimney” + “biscuit bricks” or rejects candy fill in chimney slots.

**Evidence:** Cursor U05–U06; prompt `opt-h-brick-chimney-gingerbread-tree.md`.

**NEW?** Partial — decoration-slots wiki covers “no houses” but not chimney-brick vocabulary.

**DEST?** Short wiki addendum / patch to gingerbread decoration-slots page OR task CORRECTION-GATE bullet.

---

## Candidate 3 — Edge-v4 base + Styled V1 motif (composition lock)

**Lesson:** For peppermint overlay: lock **edge-v4** as background/edges/geometry; use **Styled V1 Peppermint** only as interior motif reference — never import V1’s background.

**Applies when:** Decorating approved edge-v4 artwork with peppermint/holly items.

**Evidence:** Codex C06–C07; METHODS_AND_FAILURES; festive-edge-v4-peppermint-overlay task.

**NEW?** Partially in session digests; may need wiki/SOP if not already on peppermint-overlay docs.

**DEST?** wiki or task SOP in `tasks/festive-edge-v4-peppermint-overlay/` — check before write.

---

## Candidate 4 — Candy-creative is high-risk; regenerate from clean sources

**Lesson:** High-creativity clarity (`creat ~0.65`, low resemblance) can look “amazing” on one probe then inject **magenta/neon green artifacts** on batch. Do **not** heal failed candy-creative outputs — restart from original magenta/cream Stage A/B path. Prefer approved detail C (`1.5 / 0.5 / 0.7`) for production batches unless user explicitly re-approves creative.

**Applies when:** “Add more interesting candy detail” after a successful clarity upscale.

**Trigger/symptom:** Magenta fringes, neon green blobs, bright artifact speckles after creative clarity pass.

**Evidence:** Cursor U20–U22, U26; ASSISTANT_CLAIMS; DIAGNOSIS Stage C vs later rejection.

**NEW?** **Yes — important.** DIAGNOSIS documents Stage C as approved recipe but Cursor session later rejected the batch. Memory is **stale/dangerous** without the rejection.

**DEST?** **Must update** `outputs/upscale-research/DIAGNOSIS.md` (and/or wiki upscale page) with a WARNING / gate. Possibly patch skill if one is created for festive clarity upscale.

**route-probe hint:** procedure-shaped (ordered stages + params) → consider `/learn` skill **or** patch DIAGNOSIS as SOP-shaped wiki/task doc. Prefer patching DIAGNOSIS first (narrowest).

---

## Candidate 5 — Tall-panel fal 32 MP: split/stitch

**Lesson:** Detail C at 1.5× on tall panels can hit fal 32 MP cap; split vertical halves with ~12% overlap, run, linear-blend stitch.

**Evidence:** ASSISTANT_CLAIMS; DIAGNOSIS already mentions tiling for Stage B.

**NEW?** Mostly already in DIAGNOSIS.

**DEST?** drop (already banked).

---

## Candidate 6 — Unmasked artwork vs masked preview

**Lesson:** Distinguish cutout-fit **preview** composites from **unmasked transparent artwork** deliverables; user often needs the latter for Illustrator.

**Evidence:** Codex C11; Cursor tree mask complaints.

**NEW?** Partially covered by styled-candidate report separation; reinforce as gotcha.

**DEST?** wiki gotcha or AGENTS only if repo-wide — prefer wiki/task note.

---

## Candidate 7 — Live Illustrator geometry beats stale JSON

**Lesson:** For AB5 / open-file shapes, re-export live geometry when user says the shape is “now there.”

**Evidence:** Codex C12.

**NEW?** Yes as gotcha.

**DEST?** drop or short wiki; not a skill.

---

## Suggested write set for receiving model (≤3)

1. **Update DIAGNOSIS.md** — candy-creative rejection + “regenerate from clean sources” gate (Candidate 4). Highest value.
2. **Wiki/gotcha or CORRECTION-GATE bullet** — chimney biscuit bricks + tree unmask-first (Candidates 1–2, merge carefully).
3. **Optional `/learn`** only if route-probe says PROCEDURE and DIAGNOSIS patch is insufficient — e.g. “festive-clarity-upscale-batch” with literal `reupscale.py` flags. Dedup against any existing upscale skill first.

Everything else: **drop** or already banked.
