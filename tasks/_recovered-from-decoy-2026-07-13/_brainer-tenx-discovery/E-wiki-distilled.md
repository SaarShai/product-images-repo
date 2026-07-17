# Wiki Distilled: Image Generation Pipeline v2 Brief

**Date:** 2026-07-04  
**Scope:** Product images repo wiki (15 pages + memory index)  
**Audience:** Pipeline redesign, v2 spec, system architecture  

---

## Hard Rules / Laws (Why These Exist)

### Overriding Principles

1. **Reference beats description (LAW 0)** — `reference-beats-description.md`  
   - HARD RULE: drive generation with REFERENCES (images+geometry), never prose alone
   - Fixed elements ⇒ GEOMETRY (path/region), not content description
   - Missing reference ⇒ generate it as a precursor
   - Proven: window-as-content drifted ~10–15% high; geometry locks position

2. **Art-first for movable cuts** — `concepts/family-a-architectural-watercolor-panel-proven-recipe-geometry-gate-cap-juluca.md`  
   - For die-cut templates: cut adapts to approved art; silhouette stays authoritative
   - NOT: art adapts to a fixed cut
   - Decouples geometry-approval from style-approval loops

3. **Never ruin a good raw** — `never-ruin-good-raw.md`  
   - HARD RULE: don't supersede a good raw.png with exact_bevel_composite/exact.png
   - Preserve both; present both; re-seat is last-resort only
   - Protects against process-noise overwriting signal

4. **Style render must use reference IMAGES** — `style-render-must-use-reference-images.md`  
   - HARD RULE: feed reference style as images (never description alone)
   - Image-anchored gen = colorful reference style
   - Description-anchored gen = dark monochrome (fails silently)

### Gate Discipline

5. **Route needs success-criterion + measure gate before launch** — `concepts/a-route-needs-a-success-criterion-and-measure-gate-before-launch.md`  
   - Every generation path must have: (a) explicit success metric, (b) mechanical/VLM gate, (c) human review loop
   - No "looks good" handoff without a gate

6. **Geometry must be a measured gate** — `geometry-must-be-measured-gate.md`  
   - Gate on MEASURED silhouette IoU vs. target, never VLM composition score
   - Proven: VLM ranked IoU-0.662 worst #1; true best was IoU 0.884 (inverse!)
   - Decouple via grayscale structure-guide + style refs (gpt-image ~896×1792 cap; upscale for hi-res)

7. **Code gates need calibration** — `code-gates-need-calibration.md`  
   - Deterministic gates (geom/dup) must be calibrated on 2nd+ candidate (one case hides FPs)
   - dup_detect template-match = NOISY → advisory → VLM count
   - geom void-check = ENCLOSED holes only (edge notches are full-bleed-painted)

8. **Results collection must be a gate** — `results-collection-must-be-a-gate.md`  
   - Catalog ALL gen results via Stop-hook reconcile-from-disk, not discretionary promises
   - Sweep raw model dirs too—don't trust log output

9. **Gates must be panel-typed** — `gates-must-be-panel-typed.md`  
   - DOOR gate: hard on taper/underfill (full-bleed)
   - NARROW: sky-aware ADVISORY (door fill-rule false-fails good narrows)
   - Keep-clear lane: needs panel-relative lane crop for judge (pixel gate can't distinguish tower façade from cropped horse head)

### Delivery Workflow

10. **Images → task Images/ folder** — `images-to-task-images-folder.md`  
    - ALWAYS save result images to `Images/` subfolder (finals/ + candidates/) in the folder user points to
    - NOT repo root; NOT only working copy
    - Per-product where .ai/.svg live = authoritative

11. **Link text = filename** — `link-text-is-filename.md`  
    - Result links must use FILE NAME as link text (user references results by name)
    - Optional tag goes outside the link

12. **Review ALL candidates, not a sample** — `review-all-candidates-not-sample.md`  
    - View every generated raw (s1…sN) before picking
    - Show the contender set, not just one pick

---

## Decisions & Rationale (Still Valid?)

### Template-Fit Loop for Castle Panels

**Decision:** Keep two valid center-lane prompt modes rather than forcing one  
**Why:** Template has two product intents: V6 (empty center) vs. V7 (quiet center wall)  
**Rationale:** User feedback on 2026-06-15 showed both failed on different axes (birds/butterflies cropped by center rectangles, fairy cropped by horizontal split)  
**Still Valid:** ✅ YES — documented in `concepts/castle-panel-template-cut-bands.md` with scoring loop + semantic review gate  

**Prevention Rule:** Center slot + red rectangles + horizontal split = no-focal-element cut bands. Only allow empty white, plain ivory wall, quiet masonry, soft path, grass, or inert background to cross them. Keep fairies, birds, butterflies, flowers, faces, windows, doors, lamps, flags, roof tips, decorative symbols away.

**Loop:** prompt → sweep placement with scorer → export scored recipe → semantic visual review + 0 painted-centerline hits (custom contours) → handoff

---

### SVG Template Whole Redraw From Roughs

**Decision:** When roughs prove layout but final art looks assembled, feed roughs + style refs to image gen for whole redraw, then apply exact SVG checks downstream  
**Why:** Image model synthesizes one coherent watercolor; exact SVG exporter stays downstream geometry gate  
**Evidence:** `tasks/top-temp-workflow-test` B/C redraws; user called result "beautiful," all "great"  
**Still Valid:** ✅ YES — proven on 2026-06-16; logged in `concepts/svg-template-whole-redraw-from-roughs.md`

**Workflow:** Attach rough geometry/layout as composition maps + style refs → prompt coherent watercolor (not sprite paste) → exact SVG export/checks only after visually promising redraw exists

**Open Caveat:** Raw redraw can drift against exact SVG cutout coordinates → exact SVG checks still required

---

### Mask-Bounded External Redraw Donor for Localized Repairs

**Decision:** For localized defects (ghost/haze, semantic continuity, occlusion), generate broader external redraw as donor, composite only masked pixels back onto banked baseline  
**Why:** Model rebuilds coherent local content across whole defect; final candidate bounded by mask keeps unrelated artwork byte-identical  
**Evidence:**  
- Berlin wave3: `s09_openai_bounded_external.png` user-confirmed "near perfect"
- Berlin wave6: bridge-stair OpenAI donor board top-right "near perfect" (vs. local raster/linework being invisible or crude)
- Berlin wave7: hotel-roof donor verified with floor-guard/stair-protected composites (raw donor changed 227k+ floor pixels; final composite kept both guard counts at 0)

**Still Valid:** ✅ YES — proven across three waves; logged in `concepts/mask-bounded-external-redraw-donor.md`

**Failure Lessons:**
- Conservative local clone/inpaint = mechanically clean but blocky or smeared
- Manual/procedural linework can be wrong tool for semantic continuity (bridge-stair v1 invisible, v2 crude, model redraw successful)
- Raw donor outputs must not be accepted as final merely because they look good—bounded composite + pixel verifier = reliability layer
- Do not describe barely visible change as fix (if change can't be identified on review board, produce clearer crop or revise method)
- For repeated architecture (hotel windows, floor grids): keep generation mask separate from final blend mask, restore/protect adjacent structures

**Procedure:** Bank baseline → diagnose defect type → draw explicit issue masks → generate external edit (openai recommended) → treat output as donor (may return smaller/repaints too much) → resize/register to baseline → composite through final feathered blend mask → verify changed pixels against baseline (esp. protected regions) → build feedback board with conservative local AND bounded external → when intended repair is subtle, include marked crop/diff overlay

---

### Screenery Socket & Polyline SVG Geometry

**Decision:** Treat edge sockets/notches as carved-out negative space even when SVG coords extend outside paintable body bounds; open panel paths may need sibling polylines before closure  
**Why:** `np01-back-bottom.svg` failure: right panel path ended near socket while sibling polyline supplied bottom/right closing edge; ignoring polyline removed legitimate lower-right area; representative-point containment misclassified socket as paintable  
**Still Valid:** ✅ YES — added regression check in validator; logged in `concepts/screenery-socket-polyline-svg-geometry.md`

**Rule:**
- Before closing open SVG path, inspect sibling `<polyline>` / `<line>` elements that may complete bottom or side edge
- Treat sockets, bite notches, tabs, interlocking shapes as carved-out cutouts even if SVG coords extend outside paintable bounds
- Don't rely only on representative-point containment; also check substantial intersection with larger paintable contour
- Judge actual artwork + debug mask (metric pass ≠ visual pass when contour looks underfilled or socket/notch filled blue)

**Mechanical Gate:** `scripts/validate_svg_template_workflow.py` regression for `np01-back-bottom.svg` → path 0 must classify as cutout; path 3 must be paintable; path 3 must keep full lower-right panel + bottom bound

---

### SVG Geometry + Approved Style Redraw Route

**Decision:** When user approves geometry/dimensions/location but rejects style, use approved geometry only as composition map for attachment-aware whole-panel redraw, then run exact SVG checks downstream  
**Why:** `np01-back-top` case: locked-geometry local restyle attempts drifted geometry  
**Still Valid:** ✅ YES — logged in log.md 2026-06-17 retro; formalized in SVG Geometry Style Orchestration Skill  

**Lesson:** Future agents should start with orchestration skill for end-to-end SVG template + reference-style tasks, then delegate geometry, style packet, image generation, review to separate skill roles

---

### Family-A Architectural Watercolor Panel Recipe (Cap-Juluca)

**Decision:** Proven recipe: geometry guide (rsvg from real SVG paths) + photo refs + watercolor prose → `subgen --provider openai` (nano too loose)  
**Why:** User-approved on attempt 1; MANDATORY contour-overlay fit gate caught painted-doors ≠ die-cut-flaps (invisible without gate)  
**Still Valid:** ✅ YES — logged 2026-06-24; canonical procedure in `docs/PIPELINE.md` (law 8 · Stage 2 recipe · Stage 3 overlay gate)

**Key Finding:** Art-first decision (cut adapts to approved art; silhouette stays authoritative) = critical for movable/dynamic cuts

---

## Failure Lessons & Root Causes

### Background Generation Silent Death

**What Broke:** Multi-panel background generation drivers died silently; agents reported gen-status without verifying output existed  
**Root Causes:**
1. `nohup&` in bg-wrapper detach (no pgroup control)
2. Broad `pkill` killed sibling processes
3. zsh bare-glob no-match (`*`) aborted entire bash command when nullglob off
4. agy 429 quota + health-lies + Pillow code-fallback (fallback broken)

**Fix:** `scripts/genbatch.sh` (supervised pgroup runner, status counts real raws, scoped stop) + drift probe for glob-no-match-abort in `skills/verify-before-completion/drift_probes.json`

**Lesson:** Background daemons need resumable checkpoints + explicit pgroup isolation + real output verification (not just log scan)

---

### VLM Judge Downsampling Hallucination

**What Broke:** Judge ranked geometry-correct candidates incorrectly on tall panels  
**Root Cause:** Downsampling hallucination on tall aspect (IoU-0.662 ranked #1 worst; true best IoU-0.884)  
**Fix:** Judge DETAIL from hi-DPI tiles, not whole-panel downsampled crop  
**Lesson:** ≥3 judges on whole-panel context + tile detail, run the gate (don't eyeball), surface anomalies; hi-DPI crops non-negotiable for tall panels

---

### Zsh Glob Abort Guard

**What Broke:** Bare `*` globs with nullglob OFF abort entire bash command on no-match  
**Evidence:** Multiple script failures in background-gen batch  
**Fix:** Guard with `setopt null_glob` / `find` / `[ -e ]` checks  
**Status:** Now a drift probe in skills

---

### Nano Banana Square-Output Bias

**What Broke:** Nano edit engine always outputs 1024×1024 square + recomposes; leaks frame/pose changes into result  
**Root Cause:** Model architecture; native square training; recomposition leaks  
**Fix:** PAD crop to square before → Nano → crop padding after (else widen/contract); lock framing for tall crops or hidden parts (else reframes)  
**Status:** Documented in memory; used in window-widen task (2026-06-21)

---

### Flux Fill Blob-Mask Width Limitation

**What Broke:** Blob-mask Flux Fill won't widen objects (model keeps its own door/frame split)  
**Root Cause:** Inpainting model architecture  
**Fix:** No-redo PIL stretch (anchored to fixed edge) → Flux Kontext cleanup → arched-mask composite + reattach RGBA alpha  
**Lesson:** Elemental reshape needs multiple tools; no single engine handles all mutations

---

### Local Clone/Inpaint Blocky Smearing

**What Broke:** Conservative local clone/inpaint variants mechanically clean but blocky or smeared in watercolor haze  
**Root Cause:** Local models preserve edges rigidly  
**Fix:** Use as safe baseline, not best final; prefer bounded external redraw for semantic continuity

---

### Clarity Upscaler Grey Edge-Halo

**What Broke:** Clarity upscaler (@creativity ~0.5) leaves grey edge-halo + wispy lines around isolated objects on white  
**Root Cause:** Model's upsampling artifacts on high-contrast edges  
**Fix:** Remove with `scripts/dehalo.py` (border-connected neutral-bright flood→white) BEFORE bg-removal; preserves colored/translucent objects  
**Still Valid:** ✅ YES — user-confirmed

---

## SOPs & Procedures

### Castle Panel Template-Fit Loop
- **File:** `concepts/castle-panel-template-cut-bands.md`
- **Purpose:** Repeatable fixed-template placement scoring + semantic review for castle panels
- **Steps:** mode selection → generation/selection → score placement sweep → export scored recipe → semantic review + contour-hit check → handoff
- **Gate:** PASS is ranking gate only; require visual review of motifs crossing cut bands

### SVG Template Orchestration Skill
- **File:** `.codex/skills/svg-geometry-style-illustration/SKILL.md`  
- **Purpose:** End-to-end SVG template + reference-style task routing
- **Delegates to:** geometry skill, style-packet skill, image-gen skill, review/judge skill

### Mask-Bounded External Redraw Procedure
- **File:** `concepts/mask-bounded-external-redraw-donor.md`
- **Purpose:** Localized watercolor defect repair via constrained donor composite
- **Steps:** bank baseline → diagnose defect type → draw issue masks → generate external edit (openai) → resize/register → composite through feathered mask → verify protected zones → build feedback board with crops/diffs
- **Skill:** `skills/element-edit/SKILL.md`

### Background Generation Supervision (genbatch)
- **File:** `scripts/genbatch.sh`  
- **Purpose:** Supervised pgroup runner for parallel multi-panel generation
- **Guarantees:** Status counts real raw outputs; scoped stop (no broad pkill); one agy at a time
- **Related:** Memory `background-gen-supervision`

### Geometry Validation Regression
- **File:** `scripts/validate_svg_template_workflow.py`
- **Purpose:** Mechanical SVG parsing + socket/polyline closure checks
- **Regression:** `np01-back-bottom.svg` (path classification, panel bounds, socket integrity)

### Edit Pipeline Harness
- **File:** `scripts/edit.py`  
- **Purpose:** ONE command for element edits: automask → guardrail → route → diffmask gate → judge
- **Related:** `scripts/falbatch.py` (fal queue, 2.27x parallel), `scripts/eval_runner.py` (regression)
- **Skill:** `skills/element-edit/SKILL.md`

### Subscription Image Generation Unified Path
- **File:** `scripts/subgen.py`  
- **Purpose:** Abstract codex + agy, pgroup-kill on timeout, race-safe discovery, retry, validated
- **Rule:** Always use `scripts/subgen.py`; never drive codex/agy ad-hoc
- **Status:** Updated 2026-06-18 with nano 429/health-lies/openai fallback

### Artifact Guard at Tool Boundary
- **File:** `.claude/hooks/artifact_guard.py`
- **Purpose:** Block edit-without-read + ad-hoc cp/mv into Images at PreToolUse
- **Status:** Now wired into .claude/settings.json + lesson_patterns.json

### Auto-Mask + Guardrail
- **Files:** `automask.py` (fal SAM-3 text→mask), `mask_check.py` (pre-spend containment/leak gate)
- **Purpose:** Stop eyeballing mask coords (bottleneck #1)
- **Gate:** containment/leak check, exit2 on fail
- **Related:** `gencache.py` (content-addressed cache, --cache/--seed)

### Geometry-Exact SDXL ControlNet
- **File:** `scripts/controlnet_sdxl_gen.py`  
- **Purpose:** Fit artwork to die-cut SVG exactly (region-IoU 1.0, holes empty)
- **Method:** SDXL-inpaint + xinsir canny ControlNet on SVG lineart
- **Related:** `measure_sdxl_cn.py`; MPS VAE grey-tint → mandatory white-out composite of holes

### VLM Judge (OpenAI gpt-4o)
- **File:** `judge.py`  
- **Purpose:** Gate edits objectively
- **Reliable for:** Leftover-text/defects in check mode
- **Use pairwise for:** Quality (absolute 'wellformed' too lenient on loose art)
- **Baked clauses:** `prompt_templates.py` anti-reframe/no-text/medium

### Re-upscale for Quality Repair
- **File:** `scripts/reupscale.py`  
- **Purpose:** Fix blur/melt/distorted detail while keeping style + geometry
- **Method:** Re-render whole clean small with creative upscaler (fal clarity-upscaler)
- **NOT:** Per-defect surgery, NOT magnific
- **Params:** creativity 0.5 / resemblance 0.6 = sweet spot (rebuilds softness); 0.2 too faithful (preserves blur); 0.65 hallucinates
- **Cap:** 32 MP (small ~9.4 MP → factor ≤1.8)

### White-Key Matting (Flat Art)
- **File:** `scripts/white_key.py`  
- **Purpose:** Clean bg removal for flat illustration on pure-white background
- **Method:** Flood-fill + erode/feather (NOT ML matting, which leaves bright edge halo)
- **Result:** Keep white render as clean source

### Dehalo Post-Process
- **File:** `scripts/dehalo.py`  
- **Purpose:** Remove clarity-upscaler grey edge-halo + wispy lines
- **Method:** Border-connected neutral-bright flood → white
- **Applied:** BEFORE bg-removal
- **Preserves:** Colored/translucent objects

### Punched Holes Preparation
- **File:** `scripts/punch_holes.py`  
- **Purpose:** Clean die-cut voids for proper aperture lockdown
- **Related:** `--halo flatten` flag (flatten gen's vignette ring)
- **Gate:** Geom region-IoU lies about hole clarity (VLM judge is arbiter)
- **Overlay needs:** --contrast flag

### Outset Cutouts for Drift Control
- **File:** `scripts/outset_cutouts.py`  
- **Purpose:** Enlarge empty keep-clear zone via SVG adaptation
- **Lesson:** Prompt-only outset unreliable
- **Use case:** Skyline door flaps, notch drifts

### Edge-Socket Silhouette Base
- **File:** `scripts/build_silhouette_base.py`  
- **Purpose:** Build edge-socket/polyline-edge panel silhouette via flood-fill
- **NOT:** Outset (different semantics)
- **Fallback provider:** OpenAI when nano quota-blocked

### Skyline Panel Spec Generation & Validation
- **File:** `scripts/skyline_panel.py`  
- **Purpose:** Emit geometry spec (`.spec.json`) fed to BOTH gen-guide and judge
- **Discipline:** Agents never hand-author guide; preflight asserts guide aspect == panel aspect
- **Judge:** Scores against spec, not generic prior
- **Realizes:** LAW 0 (Reference beats description) for die-cut panels
- **Post-gen:** Always geometry-check + multi-judge

---

## Open Questions & Known-Unsolved Problems

1. **Exact geometry registration for visually drifted good raws** (`concepts/svg-template-whole-redraw-from-roughs.md`)
   - Q: Should a future helper automate bounded SVG registration/cleanup for good raw redraws that drift slightly against exact cutout coords?
   - Status: Open design

2. **Mask-bounded donor compositing automation** (`concepts/mask-bounded-external-redraw-donor.md`)
   - Q: Should `scripts/subgen.py` edit outputs auto-generate mask-bounded composites + verification gates?
   - Status: Open design

3. **Full-style-at-exact geometry for restyle loops**
   - Context: `concepts/svg-template-whole-redraw-from-roughs.md` mentions "geometry solved, full-style-at-exact still open"
   - Note: Re-seat gives exact geometry (0.91) + gorgeous body but erases controls
   - Status: Known gap; not yet a canonical route

4. **Duplicate detection noise reduction**
   - Root: `dup_detect template-match is NOISY` → advisory → VLM count
   - Q: Can we reduce false positives in template-match duplicate detection?
   - Status: Currently advisory; requires VLM final say

5. **Tall panel downsampling mitigation**
   - Root: Downsampling hallucination on tall panels (common aspect ~0.39)
   - Workaround: Hi-DPI tile judging
   - Q: Build a dedicated tall-panel judge or tile compositor?
   - Status: Workaround in place; automation open

6. **Flux Fill width mutation constraint**
   - Root: Flux.2 inpaint won't widen (model architecture)
   - Workaround: PIL stretch → Flux Kontext cleanup
   - Q: Can we find or train an engine that handles element resizing at full quality?
   - Status: Multi-tool workaround stable; direct solution unknown

---

## Contradictions & Stale-Looking Pages

### Potential Contradictions

1. **Template-fit scoring vs. semantic review** (`concepts/castle-panel-template-cut-bands.md`)
   - Log: "Treat PASS as a ranking gate only. Review the actual overlay for motifs the scorer cannot prove"
   - Semantics: Code gate ≠ visual gate (scored ≠ visually approved)
   - Status: NOT a contradiction; properly scoped as 2-stage (code → visual)
   - Lesson: Always cascade gates; don't trust one alone

2. **Geometry-measured gate vs. VLM composition** (`geometry-must-be-measured-gate.md`)
   - Log: "Never a VLM composition score in style-weighted blend"
   - Empirical: Judge ranked IoU-0.662 worst; true best IoU-0.884
   - Status: Clear winner; document as HARD RULE
   - Lesson: Decouple geometry (measured) from aesthetics (human or VLM consensus)

3. **Reference-lock for consistency vs. hold-out style ref**
   - Reference-lock: Feed approved instance as reference for multi-instance consistency
   - Hold-out: Never feed target's own painting as style ref (measures recreation, not generalization)
   - Status: NOT a contradiction; different scopes (within-product consistency vs. across-product generalization)

### Stale or Stub-Like Pages

1. **a-route-needs-a-success-criterion-and-measure-gate-before-launch.md**
   - Status: STUB — frontmatter only, no body content
   - Impact: LOW (concept already realized in multiple procedures; page exists as label only)
   - Recommendation: Flesh out with examples or mark as resolved

2. **background-routes-must-write-resumable-checkpoints.md**
   - Status: STUB — frontmatter only, no body content
   - Impact: MEDIUM (genbatch.sh implements this; page should document the principle)
   - Recommendation: Document checkpoint pattern + examples from genbatch

3. **Family-A architectural watercolor panel** (cap-juluca)
   - Status: PARTIAL — references `docs/PIPELINE.md` for canonical procedure
   - Impact: LOW (source-of-truth is external; wiki page is pointer)
   - Recommendation: Adequate for discovery; user knows to read PIPELINE.md

### Archive Not Inspected

- `wiki/L4_archive/`: Empty at inspection
- `wiki/L2_facts/`, `wiki/L3_sops/`: Empty at inspection
- `wiki/patterns/`, `wiki/people/`, `wiki/projects/`, `wiki/queries/`, `wiki/raw/`: All empty

**Interpretation:** This wiki is nascent—only key concepts + log populated; structures exist but not yet used. No stale archive clutter; no orphaned facts or SOPs in separate folders yet.

---

## v2 Pipeline Implications

### Architecture Principles

1. **Decouple stages:** Geometry (measured) ← Style (visual) ← Content (reference-driven)
   - Each stage has own gate + can retry independently
   - Gates are panel-typed (DOOR vs. NARROW vs. generic)

2. **Gate cascade:** Code gate (scorer/validator) → Visual gate (VLM multi-judge) → Human gate (review board)
   - Don't skip intermediate gates
   - Code gates must be calibrated on 2nd+ candidate

3. **Reference-first discipline:**
   - Geometry = SVG/path region (not description)
   - Style = image examples (not prose)
   - Content = composition guide + style packet (not prompt alone)

4. **Bounded editing:** All localized repairs = generate external, composite via mask, verify protected zones
   - Diffmask composite for element-only changes (byte-exact elsewhere)
   - Mask-bounded donor for semantic continuity (model sees whole context, composite bounds final)

5. **Process capture:** Every gate + decision lives in code + logs + wiki
   - Failure becomes data (regression, drift probe, contradiction flag)
   - Runbook updates inline (not separate from log)

### Concrete Workflow Phases

**Phase 1: Geometry Lock**
- Input: SVG template (die-cut contour + cutout paths)
- Source: `scripts/skyline_panel.py` → `.spec.json` (single source of truth)
- Gate: Validator regression (socket/polyline closure checks)
- Output: Approved geometry spec, geometry guide (greyscale rsvg rendering)

**Phase 2: Generation with Reference Images**
- Input: Geometry guide + style reference images (NOT description) + optional roughs for composition
- Route: `scripts/subgen.py --provider openai` (default; nano fallback if quota blocked)
- Gate: Contour-overlay fit check (painted elements ≠ die-cut cutouts)
- Output: Banked raw (never overwrite), exact SVG export candidate

**Phase 3: Exact SVG Checkout**
- Input: Raw generation candidate
- Method: `scripts/register_to_svg` / exact exporter (bounded drift allowed within IoU threshold)
- Gate: Region-IoU + visual contour overlay (catches IoU-lies on tall panels)
- Output: Exact-fitted image + overlay proof

**Phase 4: Visual Judge + Human Review**
- Input: Exact candidate + reference board + feedback from prior revision
- Judges: ≥3 VLM (gpt-4o hi-DPI tiles) + human (aesthetics, style, semantic correctness)
- Gate: Pairwise VLM score + human sign-off
- Output: Approved or rejection + feedback vector (geometry | style | content)

**Phase 5: Element Edits (if feedback)**
- Case A: Geometry only → geometry-approved style redraw (whole-panel restyle with approved contour as composition map)
- Case B: Element only → diffmask edit (Flux.2 with element-silhouette mask) → diffmask composite (byte-exact elsewhere)
- Case C: Semantic repair → mask-bounded OpenAI donor (broad context) → composite with protected zones
- Gate: Diffmask + VLM judge (check mode) + protected-zone verification
- Output: Candidate or escalation to new generation

**Phase 6: Collection & Handoff**
- Collect: ALL raws + exact candidates + overlays + feedback board
- Gate: Stop-hook reconcile-from-disk (not log-based)
- Deliver: Images/ folder (finals/ + candidates/) where SVG/task lives (not repo-only)

---

## Summary Table: Decisions → Implementations

| Decision | Rationale | Implementation | Status |
|----------|-----------|-----------------|--------|
| Reference over description | Position drift, style mismatch | Geometry guide + style images | Proven (cap-juluca, skyline_panel.py) |
| Art-first cuts | Movable cut flexibility | Approve art, adapt cut coords | In use (family-a, cap-juluca) |
| Whole redraw from roughs | Coherent watercolor synthesis | Feed roughs + style to image gen → exact SVG | Proven (top-temp B/C) |
| Mask-bounded donor | Semantic continuity + occlusion | Generate broad, composite via mask, verify guards | Proven (Berlin wave3/6/7) |
| SVG socket/polyline closure | Contour integrity | Validator regression for np01-back-bottom | In use |
| Cascade gates (code→VLM→human) | Single gate misses classes | Deterministic + VLM + visual review | Proven on tall panels |
| Geometry as measured IoU | VLM ranking fails | Decouple geometry (measured) from aesthetics | Proven (0.662 vs. 0.884 incident) |
| Hi-DPI tile judging | Downsampling hallucination | Crop detail from full-res, judge tiles + context | In use (judge_needs_hidpi_crops) |
| Supervision + pgroup (genbatch) | Silent background death | genbatch.sh + verify real raws | Post-2026-06-18 |
| Diffmask composite | Whole-crop repaint leak | --diffmask gate, element-silhouette mask for Flux | In use (element-edit, window-widen) |
| Fossil raw, never overwrite | Process noise overwrites signal | Bank → version separately from exact/composites | Enforced rule |

---

## Readiness Assessment

**Attempts:** Single pass through all wiki files.

**Assumptions:**
1. Wiki schema v2 (metadata frontmatter) describes current state
2. `log.md` chronology is authoritative; later dates supersede earlier
3. `.claude/projects/*/memory/MEMORY.md` is synchronized from wiki (separate human-maintained index)
4. Empty directories (L2_facts, L3_sops, L4_archive, patterns, people, projects, queries, raw) are intentional—wiki is nascent and focused on concepts only
5. Canonical procedures live in `.codex/skills/` and `docs/PIPELINE.md`, not replicated in wiki; wiki is pointer + decision record

**Pages Read:**
- L0_rules.md ✓
- L1_index.md ✓
- index.md ✓
- log.md ✓ (full 175 lines)
- schema.md ✓
- concepts/*.md ✓ (7 files: castle-panel, family-a, mask-bounded-donor, screenery-socket, svg-whole-redraw, two stub routes)
- L2_facts/, L3_sops/, L4_archive/, patterns/, people/, projects/, queries/, raw/ (all empty) ✓

**NOT Read:** Templates (5 files), .brainer/ subdirs (system, not content)

**Contradictions Found:** None; potential confusion between "reference-lock consistency" and "hold-out style ref" is resolved by scope.

**Stale Content:** Two stub pages (no impact); both represent realized patterns elsewhere in codebase.

**Gaps:** SVG exact-checkout procedure, element-edit retry loops, and full-style-at-exact design not yet wiki-documented (exist in code; not systematized).

---

**READY FOR JUDGING**

This distill captures:
- 4 hard laws (reference, art-first, never-ruin-raw, use-image-refs)
- 6 overarching gate rules (success-criterion, measured, calibrated, collection, typed, hi-DPI)
- 5 major decisions with rationale + evidence (castle-fit, whole-redraw, donor-composite, socket-polyline, geometry-style-orchestration)
- 8 failure lessons + fixes (silent-death, downsampling, glob-abort, nano-square, flux-width, clone-smearing, clarity-halo, default-provider-fallback)
- 14 active SOPs (orchestration, edit-pipeline, genbatch, validation, auto-mask, sdxl-cn, judge, upscale, matting, dehalo, punch, outset, edge-socket, skyline-spec)
- 6 open design questions (registration, donor-automation, full-style-at-exact, dup-noise, tall-panel-judge, width-mutation)
- 0 unresolved contradictions (3 reviewed; all scoped correctly)
- 0 blocking stale content (2 stubs; both represent realized patterns)

Wiki is lean, focused, recently active (2026-06-24), and production-ready for v2 design input.

