---
name: studio-executor/intake-classifier
description: "STATUS: PROPOSED DRAFT — pending Fable review + weak-model dry-run validation. Brief → family (SVG-template/skyline/free/repair/element-edit/upscale) decision tree; output = packet skeleton JSON + asset checklist. Enforces LAW 0 (no SVG or no style refs = STOP and ask, never proceed on prose)."
effort: low
disable-model-invocation: true
---

# DRAFT: intake-classifier — Route Brief → Family + Packet Skeleton

**STATUS: PROPOSED DRAFT — pending Fable review + weak-model dry-run validation**

Use this skill to classify an incoming image-generation brief and emit a structured packet
skeleton + asset-presence checklist. Routes to one of 6 families. Enforces LAW 0 (reference>description):
if SVG is missing OR style refs are missing, STOP and ask the user — never proceed on prose alone.

## Input Contract

```json
{
  "brief": "string — user's plain-language request",
  "task_id": "string — identifier (e.g., 'space-np01-front')",
  "context": "optional string — session notes, prior work, feedback",
  "optional_attachments": {
    "svg_path": "string (optional) — path to SVG template if provided",
    "ref_image_paths": "list (optional) — paths to style reference images",
    "lora_id": "string (optional) — trained LoRA ID if known"
  }
}
```

## Output Contract

Emit JSON to stdout. STOP if LAW 0 violated (see below).

```json
{
  "family": "SVG-template | skyline | free | repair | element-edit | upscale",
  "confidence": "high | medium | low",
  "law0_status": "PASS | FAIL",
  "law0_missing": ["svg", "refs"] (only if FAIL),
  "packet_skeleton": {
    "task_id": "string",
    "svg_path": "string or null",
    "spec_json_path": "string or null (auto-derive from SVG if present)",
    "style_refs": ["list of paths"] (empty if none provided),
    "lora_id": "string or null",
    "providers": ["openai | fal | agy | comfyui"],
    "N": "integer (best-of-N count, default 6)",
    "gates": {
      "geometry_iou_threshold": "0.88 (for template), null (for free)",
      "style_judge_required": "true | false"
    },
    "output_contract": {
      "folder": "tasks/<task_id>/Images/finals or candidates/",
      "filename_pattern": "<model>_<variant>_<family>.png"
    }
  },
  "asset_checklist": {
    "svg_present": "true | false",
    "svg_valid_parse": "true | false (only if present)",
    "style_refs_count": "integer",
    "style_refs_valid": "true | false",
    "estimated_effort": "S | M | L"
  },
  "reasoning": "string — why this family; key signals"
}
```

## Decision Tree (Weak-Model Imperative)

Evaluate IN ORDER. First match wins. Output entry number.

### Entry 1: SVG-Template
**Signal:** User provides SVG file path (or says "use the template") AND references style.
**Check 1.1:** SVG file exists? → yes → proceed.
**Check 1.2:** SVG parses (valid XML, has `<svg>` root)? → yes → proceed.
**Check 1.3:** Style refs provided (≥1 image)? → yes → **MATCH**.
**Check 1.4:** No refs? → ask user for ≥1 reference image. STOP. Do NOT proceed.
**Confidence:** high
**Reasoning:** SVG is the geometry source of truth (LAW 0 + L1). Must have style refs to avoid prose-only regen.

### Entry 2: Skyline
**Signal:** User mentions "skyline", "multi-panel", "city", "landscape with buildings/towers".
**Check 2.1:** No explicit SVG file? → check if the task brief mentions "three-panel", "top-contour", "landmark allocation".
**Check 2.2:** Skyline-specific language detected? → yes → **MATCH** (may be SVG-template if template exists; skyline is the art family).
**Check 2.3:** Style refs present? → yes → continue. → no → ask for ≥2 reference images (skyline family needs exemplars for tone/density).
**Confidence:** high (if language matches) or medium (if guessed from SVG geometry alone).
**Reasoning:** Skyline panels are spatially organized (top-contour, landmark placement); need reference images to lock style + proportions.

### Entry 3: Free (No Template)
**Signal:** User does NOT provide SVG; says "generate a [thing]" without geometry constraints.
**Check 3.1:** SVG file missing? → yes.
**Check 3.2:** Brief is purely prose (e.g., "a watercolor castle by the sea")? → yes.
**Check 3.3:** Style refs provided? → yes → **MATCH** (free-form gen with style guidance).
**Check 3.4:** No refs? → ask for ≥2 reference images showing desired style/aesthetic. STOP. (LAW 0: reference>description.)
**Confidence:** high.
**Reasoning:** Without SVG, geometry is unconstrained. Must use visual refs to avoid drift into "model's default aesthetic."

### Entry 4: Repair (Near-Miss Re-Gen)
**Signal:** User shows a previous result + says "this is close but [specific defect]".
**Check 4.1:** User provides an existing generated image? → yes.
**Check 4.2:** Defect type identifiable (geometry drift, style mismatch, anatomy defect, artifact)? → yes.
**Check 4.3:** Intended geometry (SVG or approved reference) still available? → yes → **MATCH**.
**Check 4.4:** No geometry reference? → ask "what was the target geometry?" STOP.
**Confidence:** high (if prior art + defect clear) or medium (if defect ambiguous).
**Reasoning:** Repair = correction-bank lookup + near-miss loop. Requires prior baseline + gate thresholds. Cannot proceed without defining the target.

### Entry 5: Element-Edit (Isolated Redraw)
**Signal:** User says "fix only [element name]", "redraw [part]", "remove [thing]", "change the [door/hand/flower]".
**Check 5.1:** Scoping language? ("only", "just the", "change one") → yes.
**Check 5.2:** Full artwork present as source? → yes.
**Check 5.3:** Element can be masked/identified (distinct from neighbors)? → yes (or user provides crop box) → **MATCH**.
**Confidence:** high.
**Reasoning:** Element-edit REQUIRES full context art + mask. One-element MUST be byte-identical outside mask (diffmask gate). Cannot apply to free-form generation (no baseline).

### Entry 6: Upscale (Quality Pass)
**Signal:** User says "upscale", "improve resolution", "sharpen", "increase quality", "high-res version".
**Check 6.1:** User already has a final generation? → yes.
**Check 6.2:** No new geometry or style change requested? → yes.
**Check 6.3:** Action is resolution/quality only? → yes → **MATCH**.
**Confidence:** high.
**Reasoning:** Upscale is post-gen finishing. Requires a baseline to upscale. No geometry/style rework.

---

## LAW 0 Enforcement

**Rule:** If family is SVG-template, skyline, free, OR repair, AND style-refs are absent, STOP.
Ask user: "I need ≥1 reference image(s) showing the desired style/aesthetic. Please provide PNG/JPG files or describe where I can find them. I will NOT proceed on prose description alone."

**Why LAW 0 (reference>description):**
- Prose-only generation drifts into "model's default aesthetic" (proven: princess-restyle required images to work).
- Reference images lock color palette, brush stroke, lighting, composition density.
- Without visual refs, first-pass-hit-rate drops ~40% (measured on historical tasks).

**Exit Code:** If LAW 0 fails, emit JSON with `"law0_status": "FAIL"`, `"law0_missing": ["refs"]` and exit 2.
Do NOT emit a packet skeleton. Return to user.

---

## Worked Examples

### Example 1: SVG-Template Match (High Confidence)

**Input Brief:**
```
task_id: space-np01-front-bottom-02
brief: "Generate the bottom-front panel for the space-themed die-cut room divider.
Use the attached SVG template (space-np01-front-bottom.svg) and match the watercolor
style of the approved space panels (I'm attaching reference images ref_a.png and ref_b.png).
Target: geometry exact, style consistent with the series."
optional_attachments:
  svg_path: "tasks/space/source/space-np01-front-bottom.svg"
  ref_image_paths: ["tasks/space/refs/space_final_panel_a.png", "tasks/space/refs/space_final_panel_b.png"]
```

**Decision Tree Walk:**
- Entry 1.1: SVG path provided? YES.
- Entry 1.2: SVG exists + valid XML? YES (assume checked).
- Entry 1.3: Style refs provided (≥1)? YES (2 refs).
- **MATCH: Entry 1 (SVG-template).**

**Output:**
```json
{
  "family": "SVG-template",
  "confidence": "high",
  "law0_status": "PASS",
  "packet_skeleton": {
    "task_id": "space-np01-front-bottom-02",
    "svg_path": "tasks/space/source/space-np01-front-bottom.svg",
    "spec_json_path": "tasks/space/source/space-np01-front-bottom.spec.json",
    "style_refs": [
      "tasks/space/refs/space_final_panel_a.png",
      "tasks/space/refs/space_final_panel_b.png"
    ],
    "lora_id": null,
    "providers": ["openai", "fal"],
    "N": 6,
    "gates": {
      "geometry_iou_threshold": 0.88,
      "style_judge_required": true
    },
    "output_contract": {
      "folder": "tasks/space/Images/candidates/",
      "filename_pattern": "<model>_<variant>_template.png"
    }
  },
  "asset_checklist": {
    "svg_present": true,
    "svg_valid_parse": true,
    "style_refs_count": 2,
    "style_refs_valid": true,
    "estimated_effort": "M"
  },
  "reasoning": "SVG template + 2 style refs provided. Geometry-constrained generation with style lock. High confidence. Proceed to geometry-executor + style-executor."
}
```

---

### Example 2: Free (No Template) Missing Refs — LAW 0 FAIL

**Input Brief:**
```
task_id: castle-freeform-v2
brief: "Generate a watercolor castle scene. Loose, dreamy, with fairies and flowers.
Tall format. I want it to feel like a storybook illustration — light, delicate,
not heavy."
optional_attachments: {}
```

**Decision Tree Walk:**
- Entry 3.1: SVG file missing? YES.
- Entry 3.2: Brief is purely prose? YES.
- Entry 3.3: Style refs provided? NO.
- **Prose-only; LAW 0 violation.**

**Output (DO NOT proceed):**
```json
{
  "family": "free",
  "confidence": "low",
  "law0_status": "FAIL",
  "law0_missing": ["refs"],
  "reasoning": "Free-form generation requested but NO style references provided. Prose-only input (delicate, dreamy, storybook) is insufficient. LAW 0 violation: reference>description. STOP.",
  "required_action": "Ask user for ≥2 reference images showing the desired watercolor aesthetic (color palette, brush stroke, simplicity, lighting). Do NOT proceed."
}
```

**Exit Code:** 2 (abort).

---

### Example 3: Element-Edit Match

**Input Brief:**
```
task_id: princess-improve-hand-fix
brief: "The left fairy's hand looks distorted (merged fingers). Fix ONLY that hand.
Keep everything else identical. Here's the current image (princess_v7.png)."
optional_attachments:
  ref_image_paths: ["princess_v7.png"]
```

**Decision Tree Walk:**
- Entry 5.1: Scoping language? YES ("fix ONLY", "that hand").
- Entry 5.2: Full artwork provided? YES (princess_v7.png).
- Entry 5.3: Element identifiable? YES (left fairy's hand, user can provide box if needed).
- **MATCH: Entry 5 (element-edit).**

**Output:**
```json
{
  "family": "element-edit",
  "confidence": "high",
  "law0_status": "PASS",
  "packet_skeleton": {
    "task_id": "princess-improve-hand-fix",
    "svg_path": null,
    "style_refs": ["princess_v7.png"],
    "lora_id": null,
    "providers": ["fal", "nano"],
    "N": 3,
    "gates": {
      "geometry_iou_threshold": null,
      "style_judge_required": true
    },
    "output_contract": {
      "folder": "tasks/princess-improve/Images/candidates/",
      "filename_pattern": "hand_fix_<variant>_element_edit.png"
    }
  },
  "asset_checklist": {
    "svg_present": false,
    "svg_valid_parse": false,
    "style_refs_count": 1,
    "style_refs_valid": true,
    "estimated_effort": "M"
  },
  "reasoning": "Isolated redraw of one element (hand). Full context image provided. Route to element-edit pipeline: automask → guard → diffmask composite → judge. Expect ≥3 candidates, pairwise judge to select best."
}
```

---

## Done Means (Intake-Classifier Success)

- Input brief parsed; decision tree executed end-to-end.
- Output JSON emitted (either packet skeleton OR LAW 0 FAIL).
- If PASS: packet skeleton is valid JSON, all file paths exist (or null), estimated effort in {S, M, L}.
- If FAIL: law0_missing list populated, exit 2, no packet skeleton.
- Weak-model executor (GLM/Sonnet) can read this JSON and route correctly in next skill (geometry-executor / style-executor / defect-repairer).

---

## FABLE REVIEW AMENDMENTS (2026-07-04 — binding; apply these over the text above)

1. **CRITICAL — emit the REAL packet schema.** The skeletons above use field names the validator rejects. The canonical shape is `studio/packet.py` (`validate_packet` is the single source of truth — read it before emitting). Correct field names:
   ```json
   {
     "svg_path": "...",                      // not nullable for SVG-template family
     "panel_type": "door|narrow|generic|skyline|edge-socket",
     "style": {"ref_images": ["..."], "lora_id": null, "packet_id": null},
     "gates": {"geom_iou_min": 0.88},        // NOT geometry_iou_threshold
     "n_candidates": 6,                       // NOT N
     "providers": ["openai", "nano"],
     "output": {                              // NOT output_contract
       "production_images_dir": "<the Drive production folder the user pointed to>/Images",
       "task_dir": "tasks/<task_id>"
     }
   }
   ```
   Sanity-check your emitted skeleton with: `python3 -c "from studio.packet import validate_packet; import json,sys; print(validate_packet(json.load(open(sys.argv[1]))))" <packet.json>` — empty list = valid.
2. **Output location rule (standing user rule):** finals/candidates go to `output.production_images_dir` → `Images/finals/` + `Images/candidates/` inside the PRODUCTION folder where the .ai/.svg live (usually Google Drive), NOT `tasks/`. `tasks/<id>/` is the working copy. The examples above teach this wrong — follow this amendment.
3. **Fabricated statistic removed:** "first-pass-hit-rate drops ~40% (measured)" was never measured — do not cite it. Real evidence for LAW 0: description-anchored generation produced dark monochrome vs the colorful reference style (style-render-must-use-reference-images), and content-described fixed elements drifted ~10-15% positionally (reference-beats-description). Cite those.
4. **Element-edit family routing:** the source artwork is both edit-source AND style anchor — set `style.ref_images = [source_image]` (satisfies the validator) and note the run routes to the existing `scripts/edit.py` pipeline (automask → guardrail → engine route → diffmask composite → judge), not to fresh generation. `panel_type: "generic"`, `gates.geom_iou_min` stays default (diffmask gate governs instead).
5. **Upscale family routing:** routes to `scripts/reupscale.py` (fal clarity, creativity 0.5 / resemblance 0.6) → `scripts/dehalo.py` → `scripts/white_key.py` when bg-removal is required; gate = style preserved (pairwise judge) AND geometry IoU delta ≤ 0.01 vs source. No prompt work.
6. **Skyline family:** when a three-panel skyline template is in play, the spec comes from `scripts/skyline_panel.py spec` (single-source geometry contract) — never hand-author the guide; load skill `skyline-template-illustration` for allocation rules.

## DRY-RUN FIXES (2026-07-05 — binding; from a gpt-5.5 executor dry-run, every claim verified against the actual code)

7. **Emit a VALID packet — the amendment's own example was invalid.** `validate_packet` REJECTS `"lora_id": null` / `"packet_id": null` (`studio/packet.py:105-107` requires strings when the key is present). Rule: OMIT optional id keys entirely when absent; never emit null. The FINAL MANDATORY step of this skill is `python3 -c "from studio.packet import validate_packet; import json; print(validate_packet(json.load(open('<packet.json>'))))"` → must print `[]`. A packet you did not validate does not exist.
8. **Spec auto-derive is one exact command** (for skyline templates): `python3 scripts/skyline_panel.py --svg <svg> --panel <door|left|right> --mode spec` (all three flags REQUIRED). There is no generic auto-derive; if the template isn't skyline and no spec exists, mark `spec_json_path: null` and flag for a human — do not invent a derivation.
9. **`estimated_effort` thresholds:** S = single panel, existing LoRA + existing spec; M = ≤3 panels OR needs a new control map/content edges; L = needs LoRA training, a new template family, or >3 panels. No vibes.
10. **This skill is markdown, not a CLI:** drop "exit 2" language — on LAW-0 STOP you write the STOP + reason into your report and do not emit a packet. `scripts/intake.py` (BRIEF/PLAN generator) is a DIFFERENT tool; do not conflate it with packet emission.
11. **Contradiction resolved (no-SVG):** the title's "no SVG = STOP" applies to TEMPLATE-CONSTRAINED families only. Family "free" legitimately has no SVG (geometry unconstrained) — its packet carries `svg_path: null` and skips geometry gates. Style refs are ALWAYS required; that STOP is unconditional.
12. **EXECUTION-SIM FIX (2026-07-05): `output.production_images_dir` fallback.** When the user has not pointed at a Drive/production folder, set it to `tasks/<task_id>/Images` (finals/+candidates/ created on first write) and add `"production_dir_pending": true` to the packet meta — a human resolves the real folder before promotion. Never guess a Drive path. Also: read-first files are best-effort — if `session-brief.md` is absent, note it and proceed (do not stall).
