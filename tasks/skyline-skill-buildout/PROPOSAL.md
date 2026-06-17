# Skyline Skill — Proposed Workflow (for review)

Date: 2026-06-17 · Status: **PROPOSAL — awaiting user feedback before build**

This is the deliverable from the "learn from every session → propose a workflow"
brief. It is grounded in 7 parallel research streams mining the current skill
system, the Berlin live example, the other 6 task packets + canonical example
assets, the screenery-lean render-studio + `vision` skill, the Brainer
meta-skills, the recovered creation history, and the confirmed image-gen tooling.
Findings: [research-findings.json](research-findings.json).

---

## `/think` framing (the load-bearing conclusions)

- **Real goal.** Not "write a nicer doc." The real goal is a skyline pipeline
  where *every stage advances only on a recomputed pass/fail signal, never a
  model "done" claim* — and where the one stage that has repeatedly failed
  (judging the picture) is mechanically forced. Quality is capped by the
  verifier, so the verifier is the product.
- **Borrow before building.** ~80% already exists. The skill already names the
  six stages; `export_svg_template_fit.py` already emits the exact overlay
  artifact set a visual judge needs; the Brainer skills (loop-engineering,
  eval-gate, verify-before-completion, task-retrospective, wiki-memory) already
  encode the gates; the `vision` skill already codifies the judging discipline
  (high-DPI crops → measured PASS/FAIL table → refute-not-confirm) which we
  **reimplement natively** for raster candidates. **The build is mostly wiring +
  a few thin tools + doc fixes, not a new architecture.** (render-studio is out
  of scope per the 2026-06-17 decision — see Decisions below; we borrow *ideas*
  only, no external/API dependency.)
- **Aim at the bottleneck.** The recurring, expensive failure across *every*
  session is "passed geometry/metrics, but the picture is wrong" (PIL
  guide-sketch, dimension drift, contour reinvention, squished overlay, cropped
  landmark). The hammer goes on the **VISUAL-JUDGE gate** (Stage 7): high-DPI
  crops over the real-SVG overlay + a forced per-feature PASS/FAIL table, scored
  by a *separate* judge. This is the single highest-leverage thing we build.
- **Reduce before adding.** No new sprawling system. Generalize one scorer,
  add one safe-lane linter, add one visual-judge script, write the
  generation-tools section, fill the empty wiki pattern/SOP homes, fix stale
  paths. Each is small and independently testable.
- **Pre-mortem (how this fails).** (a) Checkpoints become vibes — fix: every
  gate is a runnable exit code, not prose. (b) The judge grades its own homework
  — fix: generator ≠ verifier, cold subagent, ideally cross-vendor. (c)
  Template-geometry language leaks into a prompt and the model reinvents the
  contour — fix: a hard forbidden-token linter *before* every send + a drift
  probe. (d) A good local fix (the tunnel) is mistaken for "done" while the
  punch-list is open — fix: an explicit outstanding-corrections punch-list gate.
  (e) Lessons evaporate into chat/task files — fix: the LEARN stage writes a
  retrievable wiki pattern/SOP and registers it for recurrence escalation.

---

## The proposed workflow — 11 stages in 6 phases

Each stage has an **anchor** (Brainer/skill), a **mechanical gate** (runnable
exit code), and — at the two cheapest-to-catch decision points — a **USER
checkpoint**. Gate legend: **M** = mechanical/automated · **U** = user
approval · **★** = the bottleneck.

### Phase A — Setup
- **0 · Recover & scaffold.** Resume from artifacts not memory (`git status`,
  read newest `outputs/` + brief + `HANDOFF.md`); `scaffold_template_task.py`
  for a new packet (copies `assets/skyline/city-skyline template.svg`).
  **Gate (M):** packet exists; source SVG + refs pinned with paths.
- **1 · Parse geometry & manifest.** `svg_geometry_report.py` (fall back to
  manual — it exits 142 on this SVG family); fill `template-manifest.json` with
  guide roles, the 3 physical panels, saloon arch, run-through lane,
  top-contour zone, red/keep-clear zones, white-sky rule. **Pin the exact SVG
  coordinate bounds as one sourced constant** (1137.68,2350.15..7527.32,6717.08
  → aspect **1.463**) so overlays never use the preview-crop aspect (1.447).
  **Gate (M):** manifest required keys present, else BLOCKED on ambiguous roles.

### Phase B — Plan  ★ first user touchpoint
- **2 · Plan composition.** `/think` diverge→scout→sieve ≥3 compositions;
  `plan-first-execute` writes a `done means:` block (≤5 criteria) to disk.
  Allocate one landmark/composite per panel; name run-through, arch feature,
  top-contour adaptation, white sky. **Gate (M):** packet contains a
  `done means:` block AND the 3 Ask-Early questions (roster / run-through /
  arch) are answered before any image-gen call. **Checkpoint (U):** separated
  approvals — *source packet / landmark roster / composition strategy / visual
  premise* (1A/2A/3A/4A style). Cheapest place to catch a wrong direction.
- **3 · Reference style packet.** `build_reference_style_packet.py` from the
  user's refs (the style+landmark authority); the curated `assets/skyline`
  examples are *rule evidence* the skill **cites by filename** to guide agents.
  **Grow the set:** when a good example emerges (e.g. a successful integrated
  run-through, a clean arch fit), add the PNG to `assets/skyline/` and cite it.
  Attach 8–10 high-signal crops per generation; use style-only refs for a
  city/theme transfer. **Gate (M):** packet built; contact/exemplar sheets exist.

### Phase C — Prove before spending
- **4 · Proof-before-spend scout.** `loop-engineering` open-loop scout spec →
  `loop_lint.py`; 2–3 *visibly distinct* image-gen scout routes **saved as
  files**; independent geometry + visual reviewers. **Gate (M):** `loop_lint`
  exit 0 (gate+budget+generator≠verifier) AND scout pairwise distinctness above
  a threshold (faint lookalikes ~2–3/255 are rejected as inventory, not
  approval) AND one route proves enough — else method pivot.

### Phase D — Make
- **5 · Generate (subscription-only).** Two routes, no API/metered tools:
  **OpenAI via Codex (priority)** — img2img with `-i <base>` and the **prompt on
  stdin** (the `-i` flag is variadic); **agy / Nano Banana (testing &
  certain renders)**. Once geometry is approved, whole-panel **redraw** from the
  approved rough as a composition map — never locked-geometry restyle/crop-collage.
  House-style prompt blocks. **Gate (M):** safe-lane linter rejects any prompt
  containing forbidden template-geometry tokens (SVG/contour/panel proportions/
  red zone/green line/orange arch/saloon-door guide/safe margin/production
  stroke) **before send**. PIL/ImageDraw is diagnostic-only, never a deliverable.
- **6 · Place / overlay (geometry door).** `export_svg_template_fit.py
  --require-pass` → artwork-only / clean-black-lines / debug-mask / metadata.json;
  overlay built from exact SVG coordinates. **Gate (M):** scorer exit 0
  (aspect / seams / no escaped paint / coverage). `verify-before-completion`.

### Phase E — Judge  ★ the bottleneck + second user touchpoint
- **7 · Visual-judge gate ★.** New `skyline_visual_judge.py`: slice the
  clean-black-lines overlay into **high-DPI crops per skyline rule** (per panel,
  per seam/separator, saloon arch, top-contour band, each red zone, white-sky)
  → a forced **per-feature PASS/FAIL table** filled by *looking* (measure,
  no hedging, FAIL-if-unsure — the `vision` discipline). The judge is a **COLD
  separate agent** (generator ≠ verifier), ideally cross-vendor. `eval-gate`
  rubric score ≥ threshold. 7 rows: RED ZONES · SEAMS/SEPARATORS · SALOON ARCH ·
  TOP CONTOUR · LANDMARK INTEGRITY · WHITE SKY · RUN-THROUGH CONTINUITY.
  **Gate (M+judgment):** all-PASS from a separate judge AND eval-gate ≥
  threshold; every rejected render becomes a permanent eval-gate case (ratchet).
- **8 · Repair-or-restart.** Verdict ∈ **ACCEPT | LOCAL PATCH** (subscription
  img2img on the candidate; to contain a fix, **crop the region → edit the crop
  via Codex → recomposite** — there is no masked-inpaint path now) **| PROMPT
  RESTART** (whole redraw) **| BLOCKED**. ≤3 attempts per approach then PIVOT;
  an **outstanding-corrections punch-list** is carried across passes (a good
  tunnel ≠ done while TV-tower / hotel-base / statue / bridge remain open); ONE
  candidate vs ONE SVG per review image. **Checkpoint (U)** when ambiguous.

### Phase F — Close
- **9 · Final handoff & export.** Export final clipped artwork;
  `register_result.py`; update `HANDOFF.md` (visual state, approved choices,
  pending punch-list, safe prompt lane). **Gate (M):** final artifacts + verdict
  recorded; punch-list empty or explicitly deferred.
- **10 · Learn.** `task-retrospective` (5-whys, route to the NARROWEST home) →
  write `wiki/patterns/skyline-*.md` + `wiki/L3_sops/skyline-render-playbook.md`
  + concept page; register the pattern in `lesson_patterns.json`;
  `audit_lessons.py`; a *repeated* failure escalates to a `compliance-canary`
  drift probe, not more prose. **Gate (M):** wiki page written + read-back;
  `audit_lessons` clean.

---

## Failure classes each stage closes (traceability)

| Recurring failure (from the research) | Closed by |
|---|---|
| PIL "guide-sketch" rejection | Stage 5 (PIL = diagnostic only; integrated illustration via img2img) |
| Dimension / aspect drift | Stage 1 (pinned SVG bounds) + Stage 6 (geometry door) |
| Contour reinvention from geometry-in-prompt | Stage 5 (safe-lane linter) + Stage 10 (drift probe) |
| Overlay from preview-crop aspect (squished) | Stage 1 (exact-bounds constant) + Stage 6 |
| Landmark base cropping | Stage 7 (LANDMARK INTEGRITY row) |
| Faint lookalike scouts | Stage 4 (distinctness threshold, image-gen scouts saved) |
| "Metrics passed but picture wrong" | Stage 7 (the bottleneck gate) |
| Good local fix mistaken for done | Stage 8 (punch-list gate) |
| Lessons evaporate | Stage 10 (wiki pattern/SOP + recurrence escalation) |

---

## Decisions (resolved by user 2026-06-17)

1. **Build order** — **consolidate first (B1), then the visual-judge (B2).**
2. **Generation is subscription-only.** **Drop render-studio entirely** (no
   API/metered tools, no masked inpaint). Use only the confirmed subscription
   routes: OpenAI via Codex (priority) and Nano Banana via `agy` (testing).
   LOCAL PATCH = subscription img2img; contain a fix by crop→edit→recomposite.
3. **Reference examples** — keep the existing `assets/skyline` examples, **grow
   the set** as good ones appear, and **cite the relevant examples inside the
   skill** to guide agents. No separate graded library/picker for now.
4. **First test target** — **close Berlin.** It won't finish in one session, so
   the close-out is tracked in its own focused handoff that doubles as the
   learn-into-skill loop: [berlin-handoff.md](../berlin-skyline-live-example/berlin-handoff.md).

This is a living proposal — push back, reorder, cut, or add at any checkpoint.
