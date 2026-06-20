# Whole-panel generation — VALIDATED recipe (from B2 panel-3, honest generalization test)

## LAW 0 — REFERENCE BEATS DESCRIPTION (the overriding rule)
Always drive the model with REFERENCES (images + geometry), never prose description, for anything that
must be exact. Corollaries, in priority order:
1. **A fixed element must be GEOMETRY, not content.** If the panel carries a fixed feature (a window/
   door/landmark at an exact place+size), encode it as a PATH/region in the SVG geometry (an outlined
   opening the pipeline enforces) — do NOT feed it only as a content image or describe it in the prompt.
   PROOF (princess panel02): the window was a raster patch fed as content → across every gen the painted
   window drifted ~10–15% too HIGH vs the SVG window-region (see the `-GEO` overlays). Window-as-geometry
   would pin it exactly. Position from description/content is approximate; position from geometry is exact.
2. **Style from reference IMAGES, never prose** (see [[style-render-must-use-reference-images]]).
3. **If a needed reference does not exist, GENERATE it as an explicit precursor step**, then feed it —
   don't substitute a text description.

The pipeline below assumes Law 0 throughout.

The proven pipeline for "exact die-cut geometry AND rich reference style", validated end-to-end on
space-narrow panel-3 with a held-out style reference (generalization, not recreation).

## Pipeline
1. **Geometry intake.** `scripts/mask_to_svg.py` traces a production silhouette MASK
   (`illustration-N.png`, solid body + holes) → clean single-panel SVG (cut contour + enclosed
   cutouts). Cleaner than isolating a panel from a messy N-up authoring sheet (`extract_panel.py`
   gave unreliable contours). Then build a **geometry-guide PNG** (grey body / white holes / black
   outline) — the clean geometry conveyor for image models.
2. **Generate (subscription).** `scripts/subgen.py` (`openai` = codex/gpt-image, `nano` = agy
   gemini-3.1-flash-image). Refs = `[geometry-guide, HELD-OUT different-panel style painting]`.
   Prompt: paint the exact outline, keep the cutouts EMPTY, match the style, design a NEW arrangement.
3. **Recover exact geometry.** `scripts/register_to_svg.py` bbox+IoU best-fits the free-form gen onto
   the SVG body, clips outside the true contour, punches cutouts to clean voids + bevel. For panels
   with a FIXED embedded image (window/door), `scripts/composite_window.py` pastes the exact image
   back at its true SVG transform after registration.
4. **Judge (gate).** `scripts/judge_panel.py` (overlay `--contrast`) + a VLM judge scoring
   style / shape / holes-empty / novelty. eval-gate: nothing below bar ships.

## Findings (measured)
- **Local SDXL/SD1.5 + IP-Adapter PLATEAUS** at style_match 33–42 and cannot reproduce SPECIFIC
  control motifs (invents generic shapes, edge fringe). Geometry locks fine; style does not. Do NOT
  use local IP-Adapter for rich reference style.
- **Subscription >> local.** Valid held-out test: openai style 88 / shape 90 / holes-empty 98 /
  novelty 90; nano 90 / 62 / 20 / 88. The pipeline GENERALIZES (novelty 88–90 = genuinely new
  designs, not copies).
- **openai = best geometry + hole discipline** (respects keep-empty + outline). **nano = richer
  watercolor but warps the outline and paints over holes** → needs `register_to_svg` punch rescue.
- **Style crops are NOT needed** — the full reference painting already carries the motifs (noC ≈ GS).
- **Nano Banana variant (Pro/2) is NOT selectable per call** via the agy CLI (fixed to
  gemini-3.1-flash-image); true Pro/2 split needs Antigravity IDE or the Gemini API.
- `register_to_svg` body IoU ≈ 0.81–0.89 — a small contour edge-trim remains; tighten the fit later.

## HARD validity rule
NEVER feed the target panel's OWN finished painting as its style reference — that measures
recreation, not generalization. Use a DIFFERENT panel's art (same house style) and judge **novelty**.

## Overlay readability
`make_anchor_overlay --contrast` recolors guides by role (cutout=magenta, contour=lime, red-zone=red)
— required for monochrome/all-black templates where same-colour guides read as a false misalignment.

## Altering / enlarging a fixed embedded element on an already-good gen (validated, princess panel02)
Goal: keep a chosen winning illustration but change ONE local thing (e.g. make the window bigger).
Ranked routes — prefer the model, never composite:
1. **FRAMING-LOCKED gen-EDIT (best for "keep this exact picture, change only X").** Feed the winner +
   prompt "Edit Image 1. Make ONE change only: <enlarge the window to ~1.5x to fill the outline>. Change
   NOTHING else — same towers/flowers/colors/composition, SAME zoom + SAME crop, do NOT zoom or recompose;
   re-grow stone+vines around the change so it stays integrated." Output keeps the original framing/size and
   integrates the change. (openai EW-B1 — user "beautiful".) Open-ended edits ("refine/extend/improve") DO
   zoom-crop — keep edits tightly locked.
2. **Geometry-opening REGEN (best integration, new arrangement OK).** guide with the element as a big
   geometric OPENING (guide-opening: grey body + black opening at the SVG-true size) + the element image +
   the winning gen as a style/composition ref → model paints a large, fully-integrated element.
   (openai EW-C2 — user "best integration".)
3. **AVOID local composite / cv2.seamlessClone paste.** Pasting the element bigger (even Poisson-blended)
   reads pasted — double stone frame, ungrounded base. (EW-D/D2 — user "complete crap integration".)
HARD: give the GEOMETRY of the change (a drawn target OUTLINE / opening), not words alone — a words-only
enlarge edit DUPLICATED the window (added a 2nd, double-door mode); the outline-guided edit gave one
correct window. nano forces ~square aspect and recomposes → out for tall panels (use openai/codex).
Then GATE with the element-COUNT check (count on the whole-panel context, not tiles) — see
`docs/JUDGING_PROTOCOL.md`.

## Objective-gate harness — Step 1.5, BUILT (from the codex/GLM reviews)
Run the cheap DETERMINISTIC gate BEFORE any human/VLM look, so eyeballs only land on geometrically-valid art.
- `scripts/svg_manifest.py` — parse ANY panel SVG → manifest JSON (viewBox; roles by hue: cut/keep-clear/
  fold/top-contour/arch/safe; `<image>` fixed-element bboxes; expected_element_counts). The geometry source
  of truth — kills hardcoded per-panel constants.
- `scripts/geom_gate.py` — deterministic hard-gate: fill-inside-contour, overflow, edge-IoU, per-role voids.
- `scripts/dup_detect.py` — code element-count via multi-scale template-match (ADVISORY only, see below).
- `scripts/objective_gate_report.py` — INTEGRATOR → one JSON: `objective_verdict` = geom PASS AND size_ok
  (deterministic); element count is ADVISORY → `needs_vlm_count` flags escalation to the VLM count-on-context.
- `scripts/run_matrix.py` — experiment orchestrator (route-matrix JSON → subgen, with provenance/versioning),
  replaces hardcoded `run_*.sh`. `scripts/style_board.py` — full-size ref-vs-candidate board for the human.

CALIBRATION LESSONS (found by running the gate on a 2nd candidate, C2 — heuristic gates MUST be calibrated):
- **dup_detect is NOISY** — a real element can score as low as a false match (clean panel window 0.436 vs
  another panel's false arch 0.440; no clean threshold). So it is ADVISORY: on disagreement, escalate to the
  VLM count-on-context (the reliable arbiter), do NOT hard-fail on the code count.
- **geom void check = ENCLOSED holes only.** Only an exterior island fully enclosed by panel is a die-cut
  void that must be empty; an EDGE NOTCH (exterior connected to the outer background) is legitimately painted
  by a full-bleed gen and cut away. Failing notches false-fails clean panels — fixed via connected-components.

SEQUENCING (reviews): lock current panel via the gate (not eyeball) → Step 1.5 gate harness (done) →
ONE generalization on a NEW panel → THEN full regression/gold-set (building it from only 2 cases overfits).
First generalization target = a non-castle space panel with cutouts/holes + keep-clear (openai-only, tall);
stress order ≈ cutouts/holes + keep-clear first, then fold seams, then non-rect contour; avoid multi-fixed-
element first. Encode any fixed element as GEOMETRY before gen.
