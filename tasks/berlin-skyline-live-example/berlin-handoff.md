# Berlin Close-Out Handoff

Date: 2026-06-17 · Status: **ACTIVE — multi-session close-out**

**Two jobs at once** (per user, 2026-06-17):
1. **Close Berlin** to a production-ready, all-PASS skyline candidate.
2. **Use each Berlin correction to LEARN and implement back into the skill** —
   every closed punch-list item produces a durable rule + (where useful) a cited
   `assets/skyline` example + a `skyline_visual_judge` table row.

This will **not** finish in one session. Resume from this file. It supersedes the
older `HANDOFF.md` (kept as history). Workflow + build context:
[../skyline-skill-buildout/PROPOSAL.md](../skyline-skill-buildout/PROPOSAL.md).

---

## Generation rules — SUBSCRIPTION ONLY (no render-studio, no API, no masked inpaint)

- **OpenAI / Codex (priority), img2img:**
  `printf '%s' '<ARTWORK-ONLY PROMPT> … save the result PNG to <ABS OUT>' | codex exec -i <ABS BASE.png> -`
  (prompt **on stdin** — `-i` is variadic and eats a trailing arg).
- **Nano Banana via agy (testing / certain renders):**
  `agy --dangerously-skip-permissions --add-dir <DIR> --print "<ARTWORK-ONLY PROMPT> … save to <ABS OUT>"`
  (`--print` **must be last**).
- **Contain a local fix** (no masking available): **crop the region → Codex
  img2img the crop → recomposite** with feathering. Use full-image img2img only
  for global/cohesion changes.
- **SAFE LANE (hard):** never put these in a prompt — `SVG`, `contour`, `panel
  proportions`, `red zone`, `green line`, `orange arch`, `saloon-door guide`,
  `safe margin`, `production stroke`. Geometry lives only in the overlay/export.
- **Build on the best base**; if a patch is worse, revert. ≤3 tries per
  correction, then reassess. ONE candidate vs ONE SVG per review image.

---

## Current visual state

- **Approved style/composition base:** `refs/user-feedback/20260616-image-a-artwork-only.png`
- **Best candidate so far (new working base):**
  `refs/user-feedback/20260617-image-a-train-tunnel-edit.png` — OpenAI img2img;
  fixed the run-through tunnel (integrated masonry portal, train continues in),
  composition preserved (overlay box (0,116,1048,832) ≈ Image A (0,122,1048,838)).
  **Awaiting accept as the base for the remaining corrections.**
- **Exact SVG overlay:** aspect **1.463**, bounds `1137.68,2350.15 .. 7527.32,6717.08`;
  tooling `make_train_tunnel_edit_overlay.py` (reuses `make_image_a_correct_svg_overlay.py`).

---

## Punch-list (carry until empty)

| # | Correction | Type | Status |
|---|---|---|---|
| 0 | Tunnel / run-through continuity | done — pending accept | candidate ready |
| 1 | Fernsehturm (TV tower): reduce height to controlled overflow; keep LEFT of the red-center | local patch | open |
| 2 | Hotel / high-rise: restore the cropped lower base on the left of the right narrow panel | local patch | open |
| 3 | Brandenburg Quadriga (horse statue): realign clear of the left-panel red-center | local patch | open |
| 4 | Right bridge span: shift to center under the saloon-door flaps for symmetry | local patch | open |

---

## Close-out steps — each is a CHECKPOINT to involve the user

> Pattern for every correction: **generate (subscription img2img, safe-lane) →
> overlay real SVG (exact bounds) → visual-judge crops → show ONE candidate vs
> ONE SVG → USER verdict (ACCEPT / LOCAL PATCH / PROMPT RESTART) → LEARN.**

- **Step 0 — Accept the tunnel base.** 〔USER CHECKPOINT〕 Accept the 2026-06-17
  tunnel edit as the working base, or request a lighter A4.
  〔LEARN〕 run-through-continuity rule; add the accepted tunnel crop to
  `assets/skyline/` as a cited "run-through continues through infrastructure"
  example.
- **Step 1 — Fernsehturm height.** Crop the tower band → Codex img2img "lower the
  slender TV tower so its tip sits just above the skyline, keep it on the left,
  same watercolor style" → recomposite → overlay + judge. 〔USER CHECKPOINT〕
  〔LEARN〕 controlled-overflow rule (confirm it's already in the skill; add the
  before/after as evidence).
- **Step 2 — Hotel base.** Crop the right-panel base → img2img "extend the
  building's lower facade straight down to the waterline, keep everything else
  identical" → recomposite → overlay + judge. 〔USER CHECKPOINT〕
  〔LEARN〕 landmark-base-integrity check → a `skyline_visual_judge` row.
- **Step 3 — Quadriga.** Crop the gate top → img2img "nudge the horse statue a
  little left so it sits over the gate, not the empty center lane" → recomposite
  → overlay + judge. 〔USER CHECKPOINT〕 〔LEARN〕 recognizable-feature-vs-red-center
  rule → a `skyline_visual_judge` row.
- **Step 4 — Bridge symmetry.** img2img "center the small arched bridge under the
  middle of the scene" (may need a wider edit) → overlay + judge. 〔USER
  CHECKPOINT〕 〔LEARN〕 saloon-arch-symmetry rule.
- **Step 5 — Finalize.** All items closed → `export_svg_template_fit.py
  --require-pass` → `skyline_visual_judge` all-PASS 7-row table (cold judge) →
  `register_result.py` → update this handoff. 〔USER CHECKPOINT: final approval〕
- **Step 6 — Learn consolidation.** `task-retrospective`; write the skyline wiki
  pattern + SOP; grow `assets/skyline`; promote durable rules into the skill
  (folds into build increments B1–B4).

---

## Learn-into-skill mapping (the second half of the goal)

| Berlin correction | Rule harvested | Lands in |
|---|---|---|
| Tunnel | run-through must visibly continue through infrastructure | skill rule + `assets/skyline` example + judge row |
| TV tower | only controlled overflow above the top contour | confirm in skill; add evidence |
| Hotel base | landmark bases stay whole inside their panel | visual-judge LANDMARK INTEGRITY row |
| Quadriga | no recognizable feature in a red-center lane (quiet filler OK) | visual-judge RED ZONES row |
| Bridge | prefer arch feature centered on the saloon-door middle | skill saloon-arch rule |

Dependency: the cleanest close-out uses the **visual-judge gate (build B2)**.
We can run Berlin manually before B2 exists, but Step 5's all-PASS table wants
B2 done. Suggested interleave: **B1 (consolidate) → Step 0–1 of Berlin → B2
(judge) → Steps 2–5 with the judge → B3/B4 as rules accrue.**

---

## Resume pointer (next session)

1. Read this file → check the punch-list → pick the next `open` item.
2. Generate the fix (subscription img2img, safe-lane) on the best base.
3. Overlay the real SVG (exact bounds) + run the visual-judge crops.
4. Show ONE candidate vs ONE SVG → get the user verdict.
5. Update the punch-list + the learn-into-skill table.
