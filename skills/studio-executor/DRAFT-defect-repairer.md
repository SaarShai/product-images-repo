---
name: studio-executor/defect-repairer
description: "STATUS: PROPOSED DRAFT — pending Fable review + weak-model dry-run validation. Defect classes → correction-bank routing; 12 proven corrections embedded as lookup table; near-miss loop (max 3 rounds); whole-entity-recreation rule."
effort: high
disable-model-invocation: true
---

# DRAFT: defect-repairer — Correction-Bank Routing + Near-Miss Loop

**STATUS: PROPOSED DRAFT — pending Fable review + weak-model dry-run validation**

Use this skill to:
1. Diagnose a near-miss or failed generation (geometry miss, style drift, anatomy defect, artifact).
2. Route to the **correction-bank** (12 proven corrections).
3. Execute a **near-miss repair loop** (max 3 rounds, generator + verifier + gate).
4. Enforce **whole-entity-recreation rule** (no piecemeal cascading edits).
5. Stop, measure, and present best to human (never self-judge).

---

## Correction Bank (12 Entries — Embedded Reference Table)

**Source:** `.brainer/tenx/correction-bank-draft.md` (2026-07-04). Proven via session data + user feedback.

### Lookup by Problem Class

| Entry | Problem Class | Defect Trigger Keywords | Correction Prompt (Verbatim) | Engine(s) | IoU Delta | Rounds |
|---|---|---|---|---|---|---|
| 1 | Geometry: keep-clear violation | "window middle", "forbidden zone", "don't place in center" | "don't put a window in the middle (in the 'forbidden zone') of narrow panels" | OpenAI gpt-image | +0.08–0.12 | 1 |
| 2 | Geometry: dome/aperture mismatch | "dome top", "cutout mismatch", "roof doesn't match" | "what happened to the dome at the top right area? please find the issue and fix it but also fix what caused it" | OpenAI gpt-image | +0.05–0.10 | 1 |
| 3 | Anatomy: hand distortion | "hands merged", "fingers distorted", "hand malformed" | "Edit Image 1... Make ONE kind of change only: FIX the ANATOMY of the [figure]... hands with five distinct, natural fingers... Keep EVERYTHING ELSE identical... Same framing, same size. Do NOT add or remove elements..." | Nano Banana | +0.15–0.25 | 1 |
| 4 | Style: watercolor tightness | "overworked", "tight", "not delicate", "needs loose watercolor" | "repaint the [scene] in the watercolor STYLE of Images 2-3. KEEP the exact same [geometry]... Change only the rendering STYLE... LOOSE, SOFT, DELICATE WATERCOLOR illustration — light airy watercolor washes, gentle muted pastel palette, fine soft pencil/ink linework..." | OpenAI gpt-image | +0.10–0.15 (style score) | 1 |
| 5 | Geometry: focal element straddling | "element crosses line", "motif in split zone", "fairy on boundary" | "the horizontal top-bottom dividing line must not cut through fairies, birds, butterflies, wings, flowers, windows, lamps, roof tips, or other recognizable motifs... Treat the horizontal split as a hard no-focal-element band." | OpenAI gpt-image | +0.06–0.08 | 1 |
| 6 | Geometry: margin tightness | "too crowded", "elements touching edge", "gutter encroachment" | "Keep the artwork comfortably inside the future yellow safe-area margins... Preserve clean white gutters outside the safe-area boundary... Keep the side masses narrower so the whole composition has breathing room inside the side safe margins. Compose as if every future cut path is already visible..." | OpenAI gpt-image | +0.04–0.07 | 1–2 |
| 7 | Style: center lane filling | "center empty", "background bare", "needs quiet wall" | "The center lane and the red-rectangle areas should not be empty white. Fill them with a quiet background [wall/surface]... simple ivory stone wall texture, subtle masonry blocks, faint watercolor shading... Do not place focal elements in this wall area: no windows, no doors, no faces, no fairies..." | OpenAI gpt-image | +0.08–0.12 (composition) | 1 |
| 8 | Framing: square-bias recomposition | "widened", "contracted", "aspect shifted" | "pad crop to square before / crop padding after... lock framing for tall crops or hidden parts (else it reframes)... ONE-pass whole-figure after... verify all regions BEFORE merge." | Nano Banana | +0.10–0.20 (aspect preserved) | 1 |
| 9 | Defect: clarity upscaler grey halo | "grey outline", "wispy lines", "edge halo" | "look at the screenshot here. there is an outset grey outline around the objects in the image. eliminate this in any of the images that has it." | scripts/dehalo.py (post-process) | N/A (artifact removal) | 1 |
| 10 | Element: vehicle/object reshape | "malformed shape", "car wrong", "door tilted" | "Redraw ONLY the [element]... Fix its shape into a clean, well-proportioned [target form]... Render it in the EXACT same loose hand-drawn style as the rest of the picture... Keep the [element] in the SAME position, the SAME size, and the SAME side-view pose. Do NOT change anything else." | Flux.2-pro or Nano | +0.12–0.18 (element IoU) | 1 |
| 11 | Geometry: contour-first framing | "drawn cut lines", "dashed guides", "red/yellow overlays" | "Use the uploaded watercolor [reference] for style. Use the uploaded [SVG] template/preview only as a production constraint map... Do not draw any black cut line, dashed guide, red rectangle, yellow safe-area line, green contour line, label, measurement, annotation, or production guide." | OpenAI gpt-image | +0.06–0.10 | 1 |
| 12 | Consistency: cross-panel character lock | "fairy size differs", "character inconsistent", "different across panels" | "Redrawing the SAME character across many instances needs the approved instance fed as a reference (Flux.2 image_urls[]/IP-Adapter) or they won't match." | Flux.2-pro | +0.15–0.25 (cross-panel consistency) | 1 |

---

## Input Contract

```json
{
  "failed_image": {
    "image_path": "string",
    "model": "string (which engine generated it)",
    "region_iou": "float (if geometry, e.g., 0.83)",
    "style_score": "integer 1-5 (if style gate, e.g., 3)",
    "gate_reason": "string (why NEAR_MISS: e.g., 'geometry drift')"
  },
  "generation_context": {
    "task_id": "string",
    "svg_path": "string (if template)",
    "original_prompt": "string"
  },
  "loop_budget": {
    "max_rounds": 3,
    "rounds_used": 0
  }
}
```

## Output Contract

For each repair round:

```json
{
  "round": "integer (1, 2, or 3)",
  "defect_class": "string (from correction-bank)",
  "correction_entry": "integer (1–12)",
  "correction_prompt": "string (verbatim from bank or adapted)",
  "engine": "string",
  "regenerated_image": "string (path)",
  "gate_result": "PASS | FAIL | CONTINUE",
  "new_region_iou": "float (if geometry)",
  "new_style_score": "integer (if style)",
  "delta": "float (improvement vs prior round)",
  "budget_remaining": "integer (rounds left)",
  "reasoning": "string",
  "next_action": "proceed_to_final_judge | repair_loop_round_2 | reject_present_best"
}
```

---

## Step 1: Diagnose Defect Class (Decision Tree)

**Input:** Failed image + gate report (geometry IoU + style score + reason string).

**Decision:** Which correction-bank entry applies?

**Procedure:**

```
defect_reason = gate_report.reason_text

SCAN keywords in defect_reason AGAINST correction_bank trigger keywords:

IF defect_reason contains ("window middle" OR "forbidden zone") THEN
  defect_class := "Geometry: keep-clear violation"
  correction_entry := 1
  
ELSE IF defect_reason contains ("dome" OR "aperture" OR "top feature") THEN
  defect_class := "Geometry: dome/aperture mismatch"
  correction_entry := 2
  
ELSE IF defect_reason contains ("hand" OR "finger" OR "merged" OR "anatomy") THEN
  defect_class := "Anatomy: hand distortion"
  correction_entry := 3
  
ELSE IF defect_reason contains ("overworked" OR "tight" OR "not delicate" OR "needs loose watercolor") THEN
  defect_class := "Style: watercolor tightness"
  correction_entry := 4
  
ELSE IF defect_reason contains ("straddling" OR "line crosses" OR "motif split" OR "focal element") THEN
  defect_class := "Geometry: focal element straddling"
  correction_entry := 5
  
ELSE IF defect_reason contains ("crowded" OR "margin" OR "gutter" OR "safe area") THEN
  defect_class := "Geometry: margin tightness"
  correction_entry := 6
  
ELSE IF defect_reason contains ("center" OR "empty white" OR "wall" OR "background") THEN
  defect_class := "Style: center lane filling"
  correction_entry := 7
  
ELSE IF defect_reason contains ("widened" OR "contracted" OR "aspect" OR "square bias") THEN
  defect_class := "Framing: square-bias recomposition"
  correction_entry := 8
  
ELSE IF defect_reason contains ("halo" OR "grey outline" OR "wispy") THEN
  defect_class := "Defect: clarity upscaler grey halo"
  correction_entry := 9
  
ELSE IF defect_reason contains ("car" OR "vehicle" OR "object" OR "reshape" OR "malformed") THEN
  defect_class := "Element: vehicle/object reshape"
  correction_entry := 10
  
ELSE IF defect_reason contains ("cut line" OR "guide" OR "dashed" OR "red" OR "yellow") THEN
  defect_class := "Geometry: contour-first framing"
  correction_entry := 11
  
ELSE IF defect_reason contains ("character" OR "fairy" OR "consistent" OR "cross panel") THEN
  defect_class := "Consistency: cross-panel character lock"
  correction_entry := 12
  
ELSE
  defect_class := "UNKNOWN"
  correction_entry := null
  reasoning := "Defect class not in correction-bank. Escalate to human review (cannot auto-repair)."
  next_action := "reject_present_best"
END IF
```

**Example Diagnosis:**

```
Input:
  gate_report.reason = "IoU 0.83, region-iou below threshold 0.85. Width drift detected in narrow column."
  
Scan: "narrow column", "width drift"
Match: entry 6 ("margin tightness") or entry 1 (if center window involved).
Decision: "Geometry: margin tightness" (entry 6).
```

---

## Step 2: Near-Miss Repair Loop (Max 3 Rounds)

**Loop Structure:**

```
FOR round = 1 TO 3 DO
  
  step_2a: FETCH correction prompt from correction-bank[correction_entry]
  step_2b: ADAPT prompt if needed (insert task-specific details)
  step_2c: ROUTE to engine (correction_bank[entry].engines[0])
  step_2d: REGENERATE with corrected prompt
  step_2e: RE-MEASURE (geometry IoU or style score)
  step_2f: RE-GATE (PASS | FAIL | CONTINUE)
  step_2g: DECIDE next action
  
  IF gate_result == PASS THEN
    next_action := "proceed_to_final_judge"
    BREAK loop
  ELSE IF round < 3 AND gate_result == FAIL THEN
    reasoning := "Correction ineffective. Round " + round + " failed. Try next entry or escalate."
    next_action := "repair_loop_round_" + (round + 1)
  ELSE IF round == 3 THEN
    next_action := "reject_present_best"
    BREAK loop
  END IF
  
END FOR
```

**Termination Conditions:**

| Condition | Action |
|---|---|
| Gate PASS after round 1 | Done. Advance to final judge. |
| Gate PASS after round 2 | Done. Advance to final judge. |
| Gate FAIL round 1 + 2, PASS round 3 | Done. Advance to final judge. |
| All 3 rounds FAIL (no PASS) | Stop. Present best of 3 to human. |
| Budget exhausted (round 3 done) | Stop. Present best to human. |

---

## Step 3: Route Regeneration

**Engine Selection** (from correction-bank):

```
correction_entry = (diagnosed from Step 1)
engines = correction_bank[correction_entry].engines

PRIMARY_engine = engines[0]  (e.g., "OpenAI gpt-image" for entry 1, 2, 4–7, 11)
FALLBACK_engine = engines[1] (e.g., "fal Flux" if OpenAI rate-limited)

TRY PRIMARY_engine:
  CALL api(model=PRIMARY_engine, prompt=correction_prompt)
  IF success THEN output = result
  ELSE IF error 429 OR 401 THEN fallback to FALLBACK_engine
  ELSE abort (exit 1)
END TRY
```

**Adapted Prompt** (Task-Specific Insertion):

```
correction_template = correction_bank[correction_entry].prompt

IF correction_entry == 1 THEN
  # Geometry: keep-clear violation
  adapted_prompt = correction_template
  # (no insertion needed; template is generic)

ELSE IF correction_entry == 3 THEN
  # Anatomy: hand distortion
  adapted_prompt = correction_template
    .replace("[figure]", "{figure_name from task}")
    .replace("[EVERYTHING ELSE]", "{list preserved elements}")
  # Example: "Fix ONLY the left fairy's hand... Keep the dress, wings, facial features identical."

ELSE IF correction_entry == 12 THEN
  # Cross-panel consistency
  adapted_prompt = correction_template
    .replace("image_urls[]", "{approved_character_image}")
  # Example: "approved-fairy-panel-01.png as reference"

ELSE
  # Generic template
  adapted_prompt = correction_template

END IF
```

---

## Step 4: Re-Measure & Re-Gate

**Procedure:**

```
REGENERATE image via corrected prompt (Step 3).
OUTPUT: new_image.png

IF correction_entry in [1, 2, 5, 6, 7, 11] THEN
  # Geometry-focused entries
  CALL scripts/measure_sdxl_cn.py --image new_image.png --svg <svg_path>
  new_region_iou = measure_result.region_iou
  delta = new_region_iou - old_region_iou
  
  threshold = packet.gates.geometry_iou_threshold
  
  IF new_region_iou >= threshold THEN
    gate_result := "PASS"
  ELSE IF new_region_iou >= 0.80 THEN
    gate_result := "CONTINUE" (near-miss, may try round 2)
  ELSE
    gate_result := "FAIL" (too low; ineffective correction)
  END IF

ELSE IF correction_entry in [4] THEN
  # Style-focused entries
  CALL pairwise_judge(
    image_A = old_image,
    image_B = new_image,
    rubric = "style_consistency"
  )
  delta = pairwise_judge_result.style_delta
  
  IF delta > 0 AND pairwise_judges prefer new_image THEN
    gate_result := "PASS"
  ELSE IF delta >= 0 THEN
    gate_result := "CONTINUE"
  ELSE
    gate_result := "FAIL"
  END IF

ELSE IF correction_entry in [9] THEN
  # Artifact removal (dehalo)
  CALL scripts/dehalo.py --image new_image.png
  VERIFY halo eliminated via visual check (automated: edge-histogram unchanged outside object mask)
  IF halo cleared THEN
    gate_result := "PASS"
  ELSE
    gate_result := "FAIL"
  END IF

ELSE
  # Default: pairwise judge on overall quality
  gate_result := "CONTINUE" (advance to final judge)

END IF
```

---

## Step 5: Whole-Entity-Recreation Rule (Anti-Pattern)

**Rule:** If piecemeal correction fails >1 round, do NOT cascade edits. Instead, flag for **whole re-generation**.

**Why (Historical Proof):**
- B-session-feedback #1 failure mode: "Piecemeal edits cascade."
- Example: fix hand → introduces halo → fix halo → loses brush stroke consistency → etc.
- Proof: princess-improve series showed "multiple targeted passes → accumulates artifacts."
- Solution: if correction 1 + 2 both fail or only marginally improve (delta < 0.03), stop and **re-generate the whole panel from scratch** with tighter prompt.

**Decision Gate:**

```
IF round >= 2 AND (
  gate_result == FAIL OR
  delta < 0.03 (marginal improvement)
) THEN
  reasoning := "Piecemeal cascade risk. Best approach: whole-entity recreation (new generation with tighter prompt)."
  next_action := "reject_present_best_and_recommend_restart"
ELSE
  next_action := (normal repair_loop_continue OR proceed_to_final_judge)
END IF
```

---

## Step 6: Present Best to Human (Never Self-Judge)

**Rule:** At end of loop (budget exhausted or unknown defect), do NOT claim victory. Measure, rank, and present.

**Output Format:**

```
RANK all images (original + rounds 1–3) by:
  1. Gate score (PASS > NEAR_MISS > FAIL).
  2. Numeric delta (highest improvement).
  3. Timestamp (oldest = more refined).

EMIT JSON:
{
  "loop_complete": true,
  "total_rounds": 3,
  "best_image": "round_2_regenerated.png",
  "ranking": [
    { "image": "round_2_regenerated.png", "gate": "PASS", "iou": 0.91, "rank": 1 },
    { "image": "round_1_regenerated.png", "gate": "NEAR_MISS", "iou": 0.84, "rank": 2 },
    { "image": "original_failed.png", "gate": "FAIL", "iou": 0.83, "rank": 3 }
  ],
  "recommendation": "Best is round_2 (PASS, IoU=0.91). Accept or re-run with different prompt.",
  "next_action": "proceed_to_final_judge" OR "human_review_needed"
}

OUTPUT: contact sheet (all 3 candidates + overlay) → user picks or rejects all.
```

---

## Worked Example: Geometry Margin Tightness (Entry 6)

**Input (Failed Image):**
```json
{
  "image_path": "tasks/castle-v7/outputs/openai_v7_tall_wall.png",
  "model": "openai",
  "region_iou": 0.82,
  "gate_reason": "geometry_drift: margin encroachment on left side, elements too close to safe-area boundary"
}
```

**Step 1: Diagnose**
- Keywords in gate_reason: "margin", "safe-area", "elements too close"
- Match: Entry 6 (Geometry: margin tightness)

**Step 2–4: Loop Round 1**
```json
{
  "round": 1,
  "correction_entry": 6,
  "correction_prompt": "Keep the artwork comfortably inside the future yellow safe-area margins... Preserve clean white gutters outside the safe-area boundary on both sides and along the bottom... Keep the side castle masses narrower than V7 so the whole composition has breathing room inside the side safe margins. Compose the illustration as if every future cut path is already visible: focal elements should sit clearly between cut bands, never straddling them.",
  "engine": "OpenAI gpt-image",
  "regenerated_image": "tasks/castle-v7/outputs/openai_v8_center_wall_safe_gutters.png",
  "new_region_iou": 0.87,
  "delta": 0.05,
  "gate_result": "NEAR_MISS",
  "reasoning": "IoU 0.87, threshold 0.85. Margin improved but still 0.01 below. Continue to round 2.",
  "next_action": "repair_loop_round_2"
}
```

**Step 2–4: Loop Round 2**
```json
{
  "round": 2,
  "correction_entry": 6,
  "correction_prompt": "[same, with emphasis] The horizontal gutters outside the safe-area MUST remain completely empty (no painted pixels). The side masses should be at least 3% narrower than the prior attempt.",
  "engine": "OpenAI gpt-image",
  "regenerated_image": "tasks/castle-v7/outputs/openai_v8b_margins_tightened.png",
  "new_region_iou": 0.88,
  "delta": 0.01,
  "gate_result": "PASS",
  "reasoning": "IoU 0.88 == threshold 0.88. Geometry gate PASS. Margin discipline achieved.",
  "next_action": "proceed_to_final_judge"
}
```

**Step 6: Final Output**
```json
{
  "loop_complete": true,
  "total_rounds": 2,
  "best_image": "tasks/castle-v7/outputs/openai_v8b_margins_tightened.png",
  "ranking": [
    { "image": "v8b_margins_tightened.png", "gate": "PASS", "iou": 0.88, "rank": 1 },
    { "image": "v8_center_wall_safe_gutters.png", "gate": "NEAR_MISS", "iou": 0.87, "rank": 2 },
    { "image": "v7_tall_wall.png", "gate": "FAIL", "iou": 0.82, "rank": 3 }
  ],
  "recommendation": "v8b PASS. Proceed to style judge."
}
```

---

## Done Means (Defect-Repairer Success)

- Defect class diagnosed (correction-bank entry assigned).
- Repair loop executed (≤3 rounds, generator + verifier + gate).
- Best candidate ranked + presented (never auto-claimed).
- Whole-entity-recreation rule enforced (no cascading piecemeal edits).
- Output JSON valid; next_action = proceed_to_final_judge OR reject_present_best.
- Weak-model executor (GLM/Sonnet) can read JSON and route to final judge or abandon task.

---

## FABLE REVIEW AMENDMENTS (2026-07-04 — binding; apply these over the text above)

1. **Regression guard (Step 4):** a round whose `delta <= 0` is a FAILED correction even if IoU ≥ 0.80 — do NOT repeat the same entry+engine next round; switch to the fallback engine or the next-best matching correction entry. Repeating an approach that made things worse is the cascade anti-pattern in miniature.
2. **LAW 0 on every regen (Step 3):** every regeneration call MUST re-attach the original inputs — geometry guide image + style reference images (or LoRA trigger) — alongside the correction prompt. A correction prompt alone is prose-only generation and is forbidden.
3. **Results-library writeback (Steps 2-4):** every round's regenerated image is appended to the results library (`studio.library.add_result` with meta: task_id, round, correction_entry, engine, iou/style scores) BEFORE gating. No orphan images, ever.
4. **Entry 9 gate made concrete (Step 4):** dehalo verification = run `scripts/dehalo.py`, then re-run the border-connected neutral-bright pixel count it reports; PASS iff count == 0 AND a VLM check-mode call ("is there a grey outline or wispy halo around the objects? YES/NO") answers NO. No "visual check" without a named command.
5. **Keyword-scan precedence note (Step 1):** the IF-chain order IS the precedence — entries 1 and 3 deliberately precede 10 and 11 so "forbidden zone"/"hand malformed" match their specific entries before the broad "red/yellow/malformed" triggers. Do not reorder the chain.

## DRY-RUN FIXES (2026-07-05 — binding; from a gpt-5.5 executor dry-run, verified against actual code)

6. **`measure_sdxl_cn.py` positional:** `python3 scripts/measure_sdxl_cn.py <candidate.png> --svg <svg>` (no `--image` flag). Packet threshold field is `gates.geom_iou_min` (NOT `geometry_iou_threshold`).
7. **judge.py emits winner/consistent, NOT `style_delta`:** `python3 scripts/judge.py --mode pairwise --image <A> --ref <B> --criterion "<c>"` → winner A/B + consistency. "Improvement" = new round WINS the pairwise vs previous round on the defect criterion. Two consecutive non-wins = FAILED correction → switch engine/entry (amendment: delta≤0 rule maps to "did not win").
8. **dehalo gate corrected (supersedes amendment 4's metric):** `scripts/dehalo.py --image <in> --out <out>` reports `whitened=X% protected_px=N` — it does NOT report a remaining-count. PASS = VLM check-mode "is there a grey outline or wispy halo around the objects? YES/NO" answers NO on the OUTPUT. If still YES, one re-run with `--bright` lowered by 8; then escalate.
9. **Library writeback convention:** central store is `studio/library_store/` — `python3 -c "from studio.library import add_result; print(add_result('studio/library_store', '<img>', {'task': '<task_id>', 'round': <n>, 'kind': 'repair', 'engine': '<e>', 'verdict': '<v>'}))"`. Every round BEFORE gating (amendment 3 stands).
10. **Contact sheet:** use `scripts/contact_sheet.py` (exists) — not a hand-rolled PIL loop.
11. **Mandatory evidence pack on ANY terminal state** (fixed / unknown-defect / gave-up): original + all rounds + overlays + gate JSONs + judge verdicts + library ids. "Present best" without the pack is a forbidden self-judged claim.
