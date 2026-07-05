---
name: studio-executor/style-executor
description: "STATUS: PROPOSED DRAFT — pending Fable review + weak-model dry-run validation. Style packet/LoRA usage: refs as IMAGE INPUTS always; hold-out rule (never the target panel's own art as its ref); pairwise-only style judging; when LoRA vs IP-Adapter/refs."
effort: medium
disable-model-invocation: true
---

# DRAFT: style-executor — Style Packet + LoRA + Pairwise Judge

**STATUS: PROPOSED DRAFT — pending Fable review + weak-model dry-run validation**

Use this skill to:
1. Build or load a **style packet** (reference images + exemplar crops).
2. Decide **LoRA vs IP-Adapter** routing (when to use trained style LoRA; when to use reference images).
3. Route generation with **style references as IMAGE INPUTS** (never prose alone).
4. Run **pairwise VLM judge** to rank style consistency.
5. Enforce **hold-out rule**: never feed a target panel's own painting as its style ref.

## Input Contract

```json
{
  "packet": {
    "task_id": "string",
    "style_refs": ["list of reference image paths"],
    "lora_id": "string or null (trained LoRA ID if available)",
    "collection": "string (e.g., 'cap-juluca', 'princess', 'space')"
  },
  "geometry_passed_images": [
    {
      "image_path": "string",
      "model": "string (openai | fal | nano)",
      "region_iou": "float (from geometry gate)"
    }
  ]
}
```

## Output Contract

For each geometry-PASS image, emit:

```json
{
  "image_path": "string",
  "style_decision": "ACCEPT | REJECT | PAIRWISE_JUDGE",
  "style_score": "integer 1-5 (if judged)",
  "judge_confidence": "high | medium | low",
  "style_refs_used": ["list of ref paths fed to model"],
  "lora_used": "true | false",
  "hold_out_violated": "true | false (STOP if true)",
  "pairwise_winners": ["image_path_1", "image_path_2"] (ranked best→second),
  "reasoning": "string (why this style decision; which judges agreed)"
}
```

---

## Step 1: Load or Build Style Packet

**Input:** Collection name + reference image paths (from intake-classifier).

**Procedure:**

```
IF style_refs list is empty THEN
  exit 2: "No style references provided. Cannot build style packet. LAW 0 violation."
END IF

FOR each ref_image_path in style_refs DO
  IF file does not exist THEN
    exit 2: "Reference image missing: <path>. Cannot proceed."
  END IF
  IF not valid PNG/JPG THEN
    exit 2: "Reference image invalid format: <path>."
  END IF
END FOR

CALL scripts/build_reference_style_packet.py \
  --collection <collection> \
  --refs <style_refs (list)> \
  --output_dir tasks/<task_id>/style-packet/

OUTPUT files:
  - style-packet.json (schema: refs, lora_id, swatches, exemplars)
  - reference-contact-sheet.png (all refs at same scale)
  - exemplar-crops/ (subdir with detail highlights: key brush strokes, colors, density)

LOAD style-packet.json:
  {
    "refs": [...],
    "lora_id": "null or ID",
    "color_swatches": ["#FF6B9D", ...],
    "exemplars": ["exemplar-crops/detail_01.png", ...],
    "metadata": {
      "collection": "string",
      "artist_notes": "string (optional)",
      "approved_gate_scores": [0.88, 0.91, ...]
    }
  }
```

**Done Means (Style Packet Loaded):**
- style-packet.json valid + parseable.
- All referenced files exist.
- Reference contact sheet generated (for human review).
- Exemplar crops extracted (proof: folder non-empty).

---

## Step 2: Enforce Hold-Out Rule (Critical)

**Rule:** Never use a target panel's OWN approved artwork as its style reference.

**Rationale:** 
- Feeding a panel's own art as its style ref measures **recreation**, not **generalization**.
- Proof: prior runs showed "if you give the model the winning image as style ref, it just copies it" (style score 5/5 but no novelty).
- Production requires NEW interpretations of the style, not exact reproductions.

**Check:**

```
target_panel_id = packet.task_id
target_panel_artwork_path = tasks/<target_panel_id>/Images/finals/*  (most recent approved art)

FOR each ref in style_packet.refs DO
  ref_task_id = extract_task_id_from_path(ref)
  
  IF ref_task_id == target_panel_id THEN
    hold_out_violated := TRUE
    exit 2: "Hold-out rule violation: style ref is the TARGET PANEL'S OWN artwork.
             Use a DIFFERENT panel's approved art from the same collection.
             Proof: feeding own art measures recreation, not generalization."
  END IF
END FOR

hold_out_violated := FALSE (proceed)
```

**Example:**
- **Task:** princess-fairy-panel-03 (current generation).
- **Style ref provided:** princess-fairy-panel-03_final.png ← WRONG (own artwork).
- **Correct ref:** princess-fairy-panel-01_final.png (approved panel from same series).
- **Decision:** REJECT input; ask user for different-panel reference.

---

## Step 3: Decide LoRA vs IP-Adapter Routing

**Decision Tree:**

```
IF lora_id is null OR empty THEN
  route_mode := "IP-ADAPTER-REFS"
ELSE IF lora_id is provided AND collection in TRAINED_LORA_COLLECTIONS THEN
  route_mode := "LORA-PRIMARY"
ELSE
  route_mode := "IP-ADAPTER-REFS" (fallback)
END IF
```

**Trained LoRA Collections** (from ROADMAP.md P1.3):
- `cap-juluca` — LORA-YES (trained, validated, 12+ on-style candidates).
- `space` — LORA-PARTIAL (reference library exists; LoRA TBD).
- `princess` — LORA-PARTIAL (reference library consolidated; LoRA TBD).

**Routing Logic:**

| Condition | Route | Model | Config |
|---|---|---|---|
| LoRA trained + available | LORA-PRIMARY | fal Flux | LoRA ID + trigger phrase in prompt. |
| LoRA NOT trained OR unavailable | IP-ADAPTER-REFS | fal Flux or OpenAI | style_refs as image inputs (image_urls[]). |
| Element-edit (isolated) | IP-ADAPTER-REFS | Flux.2 or Nano | Reference lock via image_urls[]. |

**Why LoRA vs IP-Adapter:**
- **LoRA:** Best for consistent style across many panels (style fused into model weights). Used when training budget available + style is proven.
- **IP-Adapter:** Best for reference-locking single elements or when style is new (no training). Zero training cost; works immediately.

---

## Step 4: Route Generation with Style Refs as IMAGE INPUTS

**Critical Rule:** Feed reference images as IMAGE INPUTS to the generation model; NEVER as text-only prompts.

**Why (LAW 0 + Evidence):**
- Text description alone ("loose watercolor", "delicate brush strokes") produces monochrome or generic output.
- Image inputs **anchor** the model to actual color, brush stroke, lighting, composition density.
- Proof: princess-restyle required image refs to work; prior prose-only attempts drifted into "model's default aesthetic."

**Procedure:**

```
IF route_mode == "IP-ADAPTER-REFS" THEN
  
  CALL generation_api(
    model: "fal flux.2-pro" | "openai gpt-image",
    prompt: "<task-specific prompt>",
    image_urls: [
      style_refs[0],  # Primary style ref
      style_refs[1],  # Secondary (if exists)
      geometry_guide  # (optional, for ControlNet conditioning)
    ],
    ip_adapter_scale: 0.7,  # strength of style lock
    negative_prompt: "[see anti-patterns in element-edit SKILL.md]"
  )

ELSE IF route_mode == "LORA-PRIMARY" THEN
  
  CALL generation_api(
    model: "fal flux.2-pro",
    prompt: "<task-specific prompt> in the style of [LORA_TRIGGER_PHRASE]",
    image_urls: [
      geometry_guide  # (optional, spatial conditioning)
    ],
    lora_id: "<trained LoRA ID>",
    lora_scale: 0.8  # strength of LoRA influence
  )

END IF
```

**Prompt Template** (from element-edit SKILL.md):
- Use `scripts/prompt_templates.py` to generate anti-reframe + positive-no-text clauses.
- Example: "a watercolor illustration of [scene]... Render in loose, soft brushstrokes. No text, no labels, no annotations."

**Image Input Quality Checklist:**
- [ ] All ref images ≥512×512 pixels (else upscale first).
- [ ] All refs valid PNG/JPG (PIL can open).
- [ ] Refs match the target collection style (no cross-collection mixing).
- [ ] Hold-out rule enforced (no target panel's own art).

---

## Step 5: Run Pairwise VLM Judge (Style Only)

**Rule:** Pairwise judging ONLY. Absolute "wellformed" scoring is too lenient on loose art.

**Why (Evidence):**
- Absolute scoring ("rate 1-5 on style consistency") clusters judges around 4–4.5 (middle of scale).
- Pairwise ("pick the better one: A or B?") forces discrimination; judges rarely tie.
- Proof: user review notes show "both look good" → pairwise reveals one has edge fraying, the other doesn't.

**Procedure:**

```
LOAD ≥3 geometry-PASS images (best-of-N candidates).

FOR each pair (Image_i, Image_j) WHERE i < j DO
  CALL pairwise_judge(
    image_A: Image_i,
    image_B: Image_j,
    rubric: {
      "style_consistency": "Does the image match the style references (color palette, brush stroke, lighting, simplicity)?",
      "color_palette": "Does color match the references? (±1 hue deviation acceptable.)",
      "brush_stroke": "Does brush technique match? (loose vs tight, watercolor vs ink blend?)",
      "composition_density": "Does focal/negative space density match the references? (busy vs airy?)",
      "overall_preference": "Which image is better overall on STYLE alone (ignore geometry)?"
    },
    judges: ["Gemini Flash", "GPT-4o", "GLM-5.2"],
    aggregation: "majority vote (2/3 judges prefer A → A wins this pair)"
  )
  
  OUTPUT: pairwise_result = {
    "pair": (Image_i, Image_j),
    "winner": Image_i | Image_j,
    "judge_votes": {"Gemini": Image_i, "GPT-4o": Image_j, "GLM": Image_i},
    "consensus": 2/3 (Gemini + GLM agree → Image_i wins)
  }
END FOR

RANK images by pairwise wins (tournament style):
  Image with most wins = best style.
  Image with fewest wins = worst style.
```

**Aggregation Rule:**
```
majority_vote = sum(judge votes for Image_A) / num_judges

IF majority_vote >= 2/3 THEN
  decision := Image_A wins
ELSE IF majority_vote < 1/3 THEN
  decision := Image_B wins
ELSE
  decision := TIE (flag for human review)
END IF
```

**Pairwise Judge Integration:**

```
CALL scripts/judge.py \
  --mode pairwise \
  --image_a <path_A> \
  --image_b <path_B> \
  --rubric style_rubric \
  --judges gemini,gpt4o,glm \
  --output pairwise_result.json
```

---

## Step 6: Style Decision Output

**Decision Logic:**

```
IF pairwise_ranking is complete AND all ≥3 judges agree THEN
  style_decision := "ACCEPT"
  style_score := 5 (consensus best)
  judge_confidence := "high"

ELSE IF pairwise_ranking is complete AND 2/3 judges agree BUT 1 disagrees THEN
  style_decision := "ACCEPT"
  style_score := 4 (majority consensus)
  judge_confidence := "medium"

ELSE IF pairwise_ranking is TIE (judges split 1.5-1.5 or worse) THEN
  style_decision := "PAIRWISE_JUDGE" (flag for human review)
  judge_confidence := "low"
  reasoning := "Judges split on style preference; tie indicates novelty vs tradition trade-off (human decides)."

ELSE IF hold_out_violated == TRUE THEN
  style_decision := "REJECT"
  reasoning := "Hold-out rule violated; cannot assess true style generalization."

END IF
```

---

## Worked Example 1: LoRA Route (Cap Juluca Collection)

**Input:**
```json
{
  "task_id": "cap-juluca-narrow-L-02",
  "collection": "cap-juluca",
  "lora_id": "fal:txcl_watercolor_lora_v2",
  "style_refs": [
    "tasks/cap-juluca/refs/cap-juluca-narrow_L_approved.png",
    "tasks/cap-juluca/refs/cap-juluca-wide_approved.png"
  ],
  "geometry_passed_images": [
    {
      "image_path": "tasks/cap-juluca/outputs/fal_lora_v1_narrow.png",
      "model": "fal",
      "region_iou": 0.91
    }
  ]
}
```

**Checks:**
- Hold-out rule: neither ref is cap-juluca-narrow-L-02 (current task). ✓ PASS.
- LoRA available: cap-juluca is LORA-YES collection. ✓ PASS.
- Refs exist + valid: ✓ PASS.

**Generation Route:**
```
Model: fal Flux
LoRA ID: fal:txcl_watercolor_lora_v2
Prompt: "[scene description] in the style of txcl_watercolor"
IP-Adapter scale: OFF (LoRA primary)
Image inputs: geometry_guide only (spatial conditioning)
```

**Pairwise Judge Output (1 best-of-N candidate vs previous best):**
```json
{
  "image_path": "tasks/cap-juluca/outputs/fal_lora_v1_narrow.png",
  "style_decision": "ACCEPT",
  "style_score": 5,
  "judge_confidence": "high",
  "pairwise_winners": [
    "tasks/cap-juluca/outputs/fal_lora_v1_narrow.png",
    "tasks/cap-juluca/outputs/openai_v3_narrow.png"
  ],
  "lora_used": true,
  "hold_out_violated": false,
  "reasoning": "LoRA-route (cap-juluca trained). Pairwise: 3/3 judges prefer fal_lora_v1 (color consistency, brush texture). Style score 5."
}
```

---

## Worked Example 2: IP-Adapter Route (No LoRA; refs as images)

**Input:**
```json
{
  "task_id": "princess-fairy-04",
  "collection": "princess",
  "lora_id": null,
  "style_refs": [
    "tasks/princess/refs/princess-fairy-01_approved.png",
    "tasks/princess/refs/princess-fairy-02_approved.png"
  ],
  "geometry_passed_images": [
    {
      "image_path": "tasks/princess/outputs/openai_v2_fairy.png",
      "model": "openai",
      "region_iou": 0.89
    }
  ]
}
```

**Checks:**
- Hold-out rule: refs are fairy-01 + fairy-02 (NOT fairy-04). ✓ PASS.
- LoRA: princess LORA-PARTIAL (not trained yet). Route to IP-Adapter.
- Refs: 2 approved artwork images. ✓ PASS.

**Generation Route:**
```
Model: OpenAI gpt-image (proven for princess series)
Prompt: "[fairy scene description]. Match the watercolor style of the references."
Image inputs (image_urls): [
  princess-fairy-01_approved.png,
  princess-fairy-02_approved.png
]
IP-Adapter scale: 0.7 (medium style lock)
```

**Pairwise Judge Output:**
```json
{
  "image_path": "tasks/princess/outputs/openai_v2_fairy.png",
  "style_decision": "ACCEPT",
  "style_score": 4,
  "judge_confidence": "medium",
  "pairwise_winners": [
    "tasks/princess/outputs/openai_v2_fairy.png",
    "tasks/princess/outputs/fal_ip_adapter_v1_fairy.png"
  ],
  "style_refs_used": [
    "tasks/princess/refs/princess-fairy-01_approved.png",
    "tasks/princess/refs/princess-fairy-02_approved.png"
  ],
  "lora_used": false,
  "hold_out_violated": false,
  "reasoning": "IP-Adapter route (no LoRA available). Pairwise: 2/3 judges prefer openai_v2 (color palette closer, brush stroke consistency). Fal_ip_adapter_v1 more saturated (drifted from refs)."
}
```

---

## Done Means (Style-Executor Success)

- Style packet built or loaded (refs, exemplars, metadata).
- Hold-out rule enforced (target panel's own art excluded).
- LoRA vs IP-Adapter routing decided (deterministic per collection + lora_id).
- Generation routed with style_refs as image_urls (NOT prose-only).
- Pairwise VLM judge run (≥3 judges, majority vote aggregation).
- Style decision assigned (ACCEPT | REJECT | PAIRWISE_JUDGE).
- Style ranking computed (top candidate identified).
- Weak-model executor (GLM/Sonnet) can read JSON and advance to final gate (judge) or rejection.

---

## FABLE REVIEW AMENDMENTS (2026-07-04 — binding; apply these over the text above; tool interfaces below were verified against the actual scripts)

1. **CRITICAL — packet field names:** the canonical packet is `studio/packet.py`: style refs live at `packet.style.ref_images`, LoRA at `packet.style.lora_id` — not top-level `style_refs`/`lora_id`. Emit/read the canonical shape only (see the same amendment in DRAFT-intake-classifier.md).
2. **LoRA registry is a FILE, not prose:** the trained-LoRA source of truth is `.brainer/tenx/lora-pilot/lora.json` (fields: request_id, lora_url, local_path, trigger_word=`CJWC`, steps). Never cite the invented `fal:txcl_watercolor_lora_v2` id or a hardcoded collections table — read lora.json (later: a consolidated `assets/loras.json`). A collection has a usable LoRA iff its entry exists there AND it passed the A4 pairwise gate.
3. **Real judge.py interface** (verified 2026-07-04): `python3 scripts/judge.py --mode pairwise --image <candidate_A> --ref <candidate_B> --criterion "<style criterion>"` — there is NO `--judges`/`--rubric`/`--image_a` flag. judge.py is a single OpenAI gpt-4o judge. Multi-judge (Gemini/GPT/GLM majority) is P4.3 future work — until it lands, run judge.py pairwise per criterion (style_consistency, palette, brush) and aggregate criteria votes yourself; flag ties to human.
4. **Real falgen.py interface** (verified): `--mode <endpoint> --image <src> --refs <r1 r2 ...> --out <path> --prompt/--prompt-file --seed --guidance --strength`. There are NO `ip_adapter_scale`/`lora_id` params today — reference-locking goes through `--refs` (flux2edit image_urls). LoRA-routed generation requires extending falgen.py (add a flux endpoint with `loras=[{path, scale}]`) or a direct `fal_client.subscribe` call — do NOT invent CLI flags; check the wrapper first.
5. **Hold-out check by CONTENT, not path:** task_id-in-path misses refs stored in Drive/production folders. Robust check: sha256 the candidate refs and compare against the target panel's existing finals (the results library stores sha256 per artifact — `studio.library.query`). Path heuristic is only the fallback.
6. **Style packet builder:** `scripts/build_reference_style_packet.py` exists (verified) — use it as drafted; if its output schema differs from the JSON sketched above, the script's actual output wins. For packet-construction methodology load skill `reference-style-packet`.
