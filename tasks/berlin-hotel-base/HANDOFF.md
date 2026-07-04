# SESSION HANDOFF — Berlin watercolor: fix the Ritz/Beisheim tower BASE

**Date:** 2026-06-22 · **Status:** wave-1 fleet complete, awaiting user pick between two finalists (M1 vs M3) and an optional wave-2 refine.

Another agent should be able to resume cold from this file. Read it top to bottom, then look at `RESULTS/ALL5_montage.png` and the two finalist FULL images.

---

## 1. THE ARTWORK & WHAT WE'RE DOING

- **Source (READ-ONLY, Google Drive):** `<DRIVE_ROOT>/Wanderland Folder/Files/Products/Screenery/production files/berlin/Images/berlin-artwork-hires-4x-4192x3848 v2.png` (4192×3848, RGB).
- **Working copy (edit here, never write to Drive without explicit ask):** `tasks/berlin-hotel-base/work/src.png`.
- **Subject:** a fine architectural **watercolor + ink** Berlin skyline. Landmarks, left→right:
  1. **Fernsehturm** (TV tower, Alexanderplatz) — far-left.
  2. **Brandenburger Tor** — foreground-left colonnade + quadriga.
  3. **Berliner Dom** — center, green copper dome.
  4. **Kaiser-Wilhelm-Gedächtniskirche** — center-right Gothic church (rendered loosely; not exact).
  5. **The Ritz-Carlton Berlin / Beisheim Center tower** — right, pale modernist high-rise. **← the building we are fixing.**
  Foreground: yellow Berlin U-Bahn train, brick arched bridge over the Spree, tiled-pattern water reflection, birds, trees flanking the bridge.

- **The problem:** the Ritz tower's **ground floor / base** is broken — it renders as a faint ghostly glass "canopy" grid + a glassy double-height "glass hall" ground floor. It does not read as a finished building.

- **CURRENT OBJECTIVE (after all the pivots below):** replace the base so it reads as a **natural continuation of the limestone facade straight down to the water** — vertical stone piers + regular windows continuing down to a modest ground floor meeting the stone quay. **No canopy. No marquee. No glass high-ceiling hall. No legible text.** Match the artwork's style, palette, lighting, and **flat near-frontal elevation**; integrate seamlessly (region-only, outside pixels byte-stable, no reframe).

---

## 2. ALL USER FEEDBACK & SUGGESTIONS (chronological — the spec evolved a lot)

> Reproduced so nothing is lost. Each line = what the user said + how it changed the task.

1. **(setup)** "Trigger the task-retrospective bit that records the session from the beginning." → session recorder armed (see §8).
2. "We're working on the images in `.../berlin/Images`. I need changes to **berlin-artwork-hires-4x-4192x3848 v2.png** at specific areas. Generally a Berlin skyline; the building on the right is the **Ritz Carlton Berlin** hotel. Identify the other buildings." → studied image, identified landmarks.
3. "Let's start with the hotel building. **The ground floor and the canopy don't look good.** Reference images attached. Try to fix it. **Create different options. Use different methods.** Use whatever workflow/SOPs/skills/instructions we have."
4. "**Do a spread.** Note that **it is NOT a glass canopy** — at least not completely glass. The ref files are in the Downloads folder. There's also **529ewd-bahnhof-potsdamer-platz.jpg** which shows the canopy." → "the canopy" = the dark **Bahnhof Potsdamer Platz station marquee**.
5. "**v1_marquee_flux2.raw.png is not good** — it's a composite of both structures. **The canopy should be in front of the actual entrance of the hotel building.** **Screenshot 2026-06-22 at 08.22.20** in Downloads is a good picture of the entrance — **that should be BEHIND the canopy** from the perspective of the image." → layering: viewer → station canopy (front) → hotel entrance (behind). Also: flux-2 **reframed** to a 3/4 photographic view (bad) and **conflated** the two structures.
6. "**Not really.** I think maybe **let's drop the canopy** and **focus on completing the bottom of the building as it should look.** This is the best representation: **the-ritz-carlton-berlin_john-w-cahill2.jpg**." → **MAJOR PIVOT: canopy abandoned entirely.** Just finish the building's base. cahill2 = the clean full-tower ground-truth.
7. "**These don't look right.** The base of the building is more of **a continuation of the buildings**, whereas what was created was more like **a glass high-ceiling hall.**" → the base must be the SAME facade (piers + regular windows) continuing down — NOT a special tall glassy ground floor.
8. "Check this: **ritz-carlton-berlin-review-v0-z4d9jyqd3smf1.webp**" → another street-level ref of the base.
9. (1) "**Kill any stale background tasks**, let the ones you need complete." (2) "**Stop and think carefully, step by step**, about how to do such a task — editing/re-generating a section of an image based on additional references, then integrating into a composition. **You can do research.** Come up with **5 potential approaches/methods/tools** to experiment. **Write yourself a goal. Spawn agents in parallel — as many as needed — split the work into independent pieces, dispatch concurrently, synthesize results as they return. Give each agent a dedicated goal. Update/set goals based on progress.**" → triggered the 5-method fleet (§5).
10. "**Give me a comprehensive and thorough session handoff file** for another session to pick up where we left off. Include all of my feedback and suggestions." → this file.

**Standing preferences inferred:** wants a real spread of options across methods; values exact reference fidelity but also seamless integration into the existing art; dislikes reframing/conflation; the base should be quiet/continuous, not a feature element.

---

## 3. GEOMETRY CONTRACT (full-source pixel coords, 4192×3848)

- **Tower footprint (x):** 3162 – 4082 (width ~920).
- **BASE REGION to replace** (the bad glass / ghost-canopy band): **y 2582 – 2828** (down to quay top). Only region that may change. (M1 extended to y2845; still verified region-only.)
- **KEEP UNTOUCHED:** upper tower (y<2582), stone quay coping + water (y>2828), brick bridge + trees on the left (x<3162).
- **Clean facade to continue** is directly above: y ~2350–2580 — pale limestone, vertical piers, regular tall-window bays, **floor period ≈ 87–88 px** (measured: 87.1).
- Convenience crop `work/crop_base.png` (1070×420) = source region (3050,2480)-(4120,2900); band in crop-local coords ≈ x112–1030, y102–348.
- Build a labeled coord grid with the snippets in `work/grid_*.png` if you need to re-measure (do NOT eyeball; read coords off a grid).

---

## 4. REFERENCE IMAGES (`tasks/berlin-hotel-base/refs/`)

- `ritz_cahill2.jpg` — **BEST full-tower** photo (limestone, vertical pilasters, stepped art-deco crown w/ "BC" monogram, left ~12-storey podium wing, base). User-endorsed ground truth (feedback #6).
- `ritz_cahill1.jpg`, `ritz_cahill3.jpg` — more real tower views (cahill3 shows the dark Bahnhof marquee in front).
- `ritz_streetlevel.png` (from the .webp) — clean real BASE / ground-floor view.
- `entrance.png` — the Ritz entrance porte-cochère (from "Screenshot 2026-06-22 at 08.22.20"). **HISTORICAL** — canopy dropped, don't add it.
- `canopy_bahnhof.jpg`, `beisheim_potsdamer.jpg` — **HISTORICAL** (the station-marquee era, feedback #4–5). Do NOT reintroduce a canopy.
- Derived style/perspective anchors in `work/`: `building_artwork_guide.png` (artwork's own building, crown→base), `tower_facade_above.png` (the facade rhythm to continue).

**HARD RULE used throughout:** drive generation with reference IMAGES, never prose alone. Feed the artwork guide + cahill2 + streetlevel.

---

## 5. METHODS TRIED & VERDICTS

### Early single-method attempts (pre-fleet)
- **flux-2 ref-fed marquee** (`RESULTS/raw_v2_flux2.png`, also `optionA_*`): beautiful watercolor but **reframed to 3/4** and **conflated** entrance+canopy. Rejected (feedback #5). Lesson: `falgen --mode flux2edit`/`falref_apply.py` give ref fidelity but **reframe** — counter with explicit flat-elevation wording or avoid for in-frame edits.
- **Flux Fill, canopy prompt** (`work/sub/fill_v1.raw.png`): in-frame (good) but prompt-only → rendered a **pale neoclassical portico + hallucinated text**. Rejected.
- **Collage-init + Kontext** (`work/collage_init_v3.png` → `work/sub/collage_kontext.raw.png`): reframed + too loose/cartoonish.
- **Flux Fill facade-continuation** (`work/sub/facade_s11*`, `RESULTS/optionB_*` tiling P=88): the in-frame inpaint read as a **glass hall** (feedback #7); the procedural tile (optionB) was faithful but **mechanically uniform**.

### The 5-method fleet (wave-1, turn 12) — shared brief in `tasks/berlin-hotel-base/BRIEF.md`
Each method wrote to `work/mN/`; all claimed region-only. **Main-loop re-verification (don't trust subagent claims):**

| Method | What it did | Outside-region delta (main-loop check) | Verdict |
|---|---|---|---|
| **M1 ref-fed regen → register** | gpt-image standalone watercolor of the tower, scaled/registered into the base | **0 (clean)** | **FINALIST.** Distinct ground floor + stone plinth, nicest stonework. Risk: dead-frontal base under slightly-angled tower → faint seam-rhythm. |
| **M2 ControlNet structure-guided** | canny guide (tiled facade rhythm) → local SDXL inpaint; fell back to falgen kontext | 0 | SDXL = blurry/grey VAE tint; kontext fallback = crisp but **reframed** (own cornice, wider bays, seam). Rejected. |
| **M3 procedural facade-continuation** | measured artwork's own facade (P=87.1), tiled down + jitter + plinth (no model on structure) | **0 (clean)** | **FINALIST.** Truest continuation, perfect seam, preserves receding right wing. Risk: uniform/repetitive, less ground-floor character. |
| **M4 collage-init → restyle** | real ref base crops composited + kontext restyle | **256 max, ~42,000 px LEAKED outside region** | **DISQUALIFIED** — its own delta=0 claim was false; caught on reverify. |
| **M5 masked-inpaint ensemble** | falgen fill/kontext, engineered prompts, seed fan-out | (not re-measured; visually) | Still reads **glass-hall-ish** at the base. Weakest on the core criterion. |
| **M0 research** | best-practice survey + ranked the 5 | n/a (read-only) | Ranked **M2 (ControlNet) #1**, M1 #4, M3 #5. **Empirics inverted this** — M1/M3 won. `work/research/` is EMPTY (findings were in the agent's return message, not persisted to a file). |

---

## 6. CURRENT STATE — THE OPEN DECISION

Two clean, verified finalists. Both fix the problem at scene scale.

- **M1 (ref-regen):** `RESULTS/M1_ref-regen_composited.png` (full-res), `..._FULL.png` (600px), `..._zoom.png` (base zoom). Nicer defined ground floor + plinth; base is dead-frontal.
- **M3 (procedural):** `RESULTS/M3_procedural_composited.png`, `..._FULL.png`, `..._zoom.png`. Seamless true continuation; more uniform.
- Spread of all 5: `RESULTS/ALL5_montage.png`.

**Verification quoted (main-loop, `np.abs(cand-src)` outside the region box):**
- M1: outside max=0, nonzero=0 ✓ (region edited: 239,316 px inside)
- M3: outside max=0, nonzero=0 ✓ (226,191 px inside)
- M4: outside nonzero=42,000 ✗ (disqualified)

**Recommendation given to user:** M3 for a true seamless continuation; M1 if a more defined ground floor is wanted and the frontal base is acceptable. **Awaiting user's pick.**

---

## 7. NEXT STEPS (wave-2 options, once a direction is chosen)

1. **If M3 wins:** de-mechanize further — vary per-floor window wash/ink slightly more; optionally graft **M1's ground-floor + stone plinth** onto M3's seam-perfect upper continuation (best-of-both).
2. **If M1 wins:** apply a slight **homography/shear** to M1's base so its pier rhythm matches the tower's slight recede at the y2582 seam; re-blend; re-verify outside-delta=0.
3. Either way: final **region-only diffmask composite** into a fresh copy of `work/src.png`, measure outside-delta=0, VLM/no-text check (`scripts/judge.py`), then present full-size.
4. **Delivery:** the source is on **read-only Drive**. Do NOT overwrite it without an explicit user OK. Likely output a new `v3.png` next to it once approved (ask first).
5. Other sections of the artwork may still need work (the user said "specific areas" plural in feedback #2). Only the hotel base has been addressed. Ask what's next after this lands.

---

## 8. TOOLING, SOP & SESSION BOOKKEEPING

- **Element-edit SOP:** `skills/element-edit/SKILL.md` (crop → mask-from-text → guardrail → routed engine → diffmask composite + pixel gate → VLM judge). Engine routing in memory `image-edit-engine-routing`.
- **Engines (keys in `.secrets/fal.env`, `.secrets/openai.env`):**
  - `scripts/falgen.py --mode {fill,kontext,flux2edit,eraser}` — fal Flux. `fill` = framing-safe masked inpaint. **NOTE: `flux2edit` mode does NOT wire reference images** (docstring lies; code sends only the source). Use `scripts/falref_apply.py` for true ref-fed flux-2 (`image_urls`).
  - `scripts/subgen.py --provider {openai,nano}` — subscription gpt-image / Nano Banana, multiple `-i` inputs. openai = tall 1024×1536; nano squares + reframes.
  - `scripts/controlnet_sdxl_gen.py` + `measure_sdxl_cn.py` — local SDXL + canny CN; blurry/grey-tint at this wide-short aspect (3.74). Not great here.
  - `scripts/automask.py` (SAM-3 text→mask), `scripts/compose_fairy.py --diffmask`, `scripts/judge.py`.
- **Always re-verify subagent region-only claims in the main loop** — M4 lied (42k px leaked). Use the `np.abs(cand-src)` outside-box check.
- **Session recorder (task-retrospective, ARMED):** `task_id 20260622T145631Z-session-...contract-tbd`, events at `.brainer/task-retrospective/sessions/20260622T145631Z-.../events.jsonl`. Add notes via `python3 skills/task-retrospective/tools/task_audit.py note --type <t> --text "..."`. At session end run a `/retro` review.
- **Requirements ledger (authoritative):** `.brainer/ledger/berlin-hotel-base-20260622.md` — atomic rows, never delete, only re-status.
- **Fleet brief (reusable):** `tasks/berlin-hotel-base/BRIEF.md` — the shared packet all method-agents read.

---

## 9. LESSONS FROM THIS SESSION (candidate durable facts)

- For **"continue an existing repetitive facade,"** the **procedural clone of the artwork's own pixels** (measure period via row autocorrelation/visual, tile with jitter + plinth) beat every generative engine on seam continuity and faithfulness — and it's free + deterministic. Generative engines either reframe (flux-2/kontext) or hallucinate a glass hall (Flux Fill prompt-only).
- **Ref-fed engines reframe; in-frame engines hallucinate content.** For a section edit that must stay in-frame AND match refs, the winning shapes were: (a) procedural clone, or (b) ref-fed **standalone** regen + **geometric register** back into the region — NOT a single ref-fed in-place edit.
- **Research ranking ≠ empirical ranking.** The research agent ranked ControlNet #1; it lost. Run the experiments; gate on measured + visual reality.
- **A separate verifier is mandatory.** M4's self-reported delta=0 was false; only the main-loop reverify caught the 42k-px leak.

---

## 10. FILE INVENTORY (key paths)

- Finalists + spread: `RESULTS/M1_ref-regen_*`, `RESULTS/M3_procedural_*`, `RESULTS/ALL5_montage.png`.
- Earlier options: `RESULTS/optionA_*` (flux-2 marquee era), `RESULTS/optionB_*` (P=88 tile), `RESULTS/raw_v2_flux2.png`.
- Per-method work: `work/m1/`…`work/m5/`; judge montage `work/judge/montage_zooms.png`.
- Refs: `refs/`; derived guides: `work/building_artwork_guide.png`, `work/tower_facade_above.png`, `work/crop_base.png`, `work/grid_*.png`.
- Brief/ledger/recorder: `BRIEF.md`, `.brainer/ledger/berlin-hotel-base-20260622.md`, `.brainer/task-retrospective/sessions/20260622T145631Z-...`.

---

## APPENDIX A — EXACT PROMPTS USED (verbatim, on disk under `work/`)

**Pre-fleet (canopy era):**
- `work/prompts/v1_marquee.md` — first flux-2 marquee (canopy in front of entrance). REFRAMED+conflated → rejected.
- `work/prompts/fill_v1.md` — Flux Fill canopy+entrance → neoclassical portico + hallucinated text.
- `work/prompts/flux2_v2.md` — flux-2 v2 flat-elevation marquee (the `raw_v2_flux2.png`/optionA source).
- `work/prompts/kontext_collage.md` — Kontext restyle of the collage → reframed/cartoonish.
- `work/prompts/fill_facade.md` — Flux Fill "complete the facade" (gave the glass-hall `facade_s11`).

**Fleet wave-1 (prompts live in each method dir):**
- M1: `work/m1/prompt_m1.md` — "redraw whole tower, FLAT near-frontal elevation, pier rhythm continues to a quiet masonry base, NO glass hall/canopy/text."
- M2: `work/m2/prompt.txt` (+ `neg.txt`) for SDXL; `work/m2/kontext_prompt.txt` for the kontext fallback (keep exact pier/window structure, no reframe).
- M3: `work/m3/_kontext_prompt.txt` — light "blend to watercolor, keep exact structure, do not reframe" (procedural structure was NOT model-generated).
- M5: `work/m5/prompts/p_a.md`, `p_b.md`, `p_c.md` — three continuation-prompt variants (same rhythm/size windows, no enlarged openings, no glass hall).
- Dead recreate-agent: `work/building_recreate/prompt_p1..p3.md`.

(All five fleet prompts share the spine: watercolor+ink, pale limestone, continue the SAME pier/window rhythm down, modest ground floor meets quay, NO glass hall / canopy / text, flat elevation, no reframe.)

## APPENDIX B — COMPLETE FILE MANIFEST (185 files)

By area (counts): `RESULTS/` 12 · `refs/` 8 · `work/` 34 (grids, study crops, collages v1–v3, masks, tiles) · `work/prompts/` 5 · `work/sub/` 6 · `work/m1/` 21 · `work/m2/` 29 · `work/m3/` 24 · `work/m4/` 14 · `work/m5/` 13 · `work/building_recreate/` 13 · `work/judge/` 1.

Notable intermediates:
- Measurement/inspection: `work/grid_base.png`, `grid_facade_rows.png`, `grid_rows_sharp.png`, `grid_flux2.png`, `study_base.png`, `study_canopy_2x.png`, `study_tower.png`, `tower_facade_above.png`.
- Finalist build chains: M1 `m1/_oa_block_raw.png`→`_oa_block_scaled.png`→`_base_meet.png`→`m1_composited.png`; M3 `m3/_facade_measure.png`,`_kontext_out.png`,`m3_composited.png` (+`m3_kontext_composited.png`).
- Rejected-but-instructive: `work/sub/fill_v1.raw.png`, `collage_kontext.raw.png`, `facade_s11.raw.png`, `tile_p88.png`.

## APPENDIX C — DEAD AGENT PARTIAL OUTPUT (salvageable)

The first background "recreate full tower" agent DIED when the host process exited (state lost, no pick). It left **5 standalone full-building watercolor candidates** in `work/building_recreate/`: `cand_openai_p1/p2/p3.png`, `cand_flux2_p1/p3.png` (+ logs + `prompt_p1..p3.md`). **Unjudged.** Its job was folded into fleet method **M1**. If M1's register isn't chosen, these are a ready pool to re-register. Not inspected in detail this session.

## APPENDIX D — VERBATIM TRAIL (the actual everything-record)

This HANDOFF is a curated summary. The closest verbatim logs:
- **Session recorder events:** `765` events at `.brainer/task-retrospective/sessions/20260622T145631Z-session-.../events.jsonl` (every correction/decision/evidence note, timestamped). `python3 skills/task-retrospective/tools/task_audit.py finish --report` renders the retrospective at session end.
- **Requirements ledger:** `.brainer/ledger/berlin-hotel-base-20260622.md` — every atomic user request (S1, B0–B12, C1–C8) with live status.

## APPENDIX E — DISCUSSION POINTS NOT ELSEWHERE CAPTURED

- **Gedächtniskirche (#4) is not an exact likeness** — generic neo-Gothic fusion (real one has a squat ruined "hollow tooth" tower). Flagged at start; user didn't request a change. Possible future fix.
- **Stale recorder:** at arm time a stale 2026-06-20 armed session (11,623 events, never closed) was finished before arming this one. Bookkeeping only.
- **`falgen.py flux2edit` bug:** docstring claims "up to 9 refs" but code sends only the source image — use `scripts/falref_apply.py` for true ref-fed flux-2. (One-line fix later; not done.)
- **Nothing written to the Drive source.** All edits live in `tasks/berlin-hotel-base/`. Final delivery (`v3.png`) requires explicit user OK.
