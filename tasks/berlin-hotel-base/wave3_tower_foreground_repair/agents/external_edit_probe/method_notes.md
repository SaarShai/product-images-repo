# external_edit_probe method notes

## Inputs inspected

- `docs/image-generation.md`: documents the subscription routes, with OpenAI image editing via `codex exec` as priority and Nano Banana via `agy` as fallback.
- `scripts/subgen.py`: repo wrapper around `codex exec` and `agy`; used here because its header says it is the always-working subscription route and it validates real image output.
- `tasks/berlin-hotel-base/wave2/w2_photoshop_firefly/method_notes.md`: previous Photoshop connector attempt was blocked with `McpServerError: Forbidden`, HTTP 403.
- `tasks/berlin-hotel-base/wave2/w2_whole_tower/method_notes.md`: direct nested `codex exec` had previously started writing a ledger outside the lane before image output; this run used `scripts/subgen.py` instead.
- `tasks/berlin-hotel-base/wave2/w2_controlnet_comfy/method_notes.md`: prior generated lanes used explicit edit boxes and post-compositing to keep pixels outside the allowed region byte-identical.
- `tasks/berlin-hotel-base/wave3_tower_foreground_repair/verify_wave3.py`: candidates must preserve the banked hotel-base box and change pixels only in the broad allowed far-left context.

## Local bounding method

Created lane-local masks from the two user issue regions:

- sphere ghost: `x=190..470 y=1120..1580`
- foreground: `x=0..620 y=2050..2920`

External raw edits were treated as donor images only. Final candidates were composited back onto the banked baseline through `issue_mask_feathered.png`, so all pixels outside the issue regions remain from the original baseline. This is why the full-res candidates pass `verify_wave3.py` even though the raw provider outputs changed the whole image and returned at lower resolution.

## Health check

Command:

```bash
python3 scripts/subgen.py --health
```

Output:

```text
{'openai': 'ok', 'nano': 'ok'}
```

## OpenAI image edit probe

Command:

```bash
python3 scripts/subgen.py --provider openai --prompt-file tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/external_edit_probe/openai_bounded_prompt.md --out tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/external_edit_probe/openai_bounded_raw.png -i tasks/berlin-hotel-base/wave2/BANKED_CURRENT_BEST/berlin_hotel_base_current_best.png tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/external_edit_probe/issue_mask_feathered.png --timeout 420 --retries 1
```

Result:

```text
[subgen openai] OK attempt 1 -> tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/external_edit_probe/openai_bounded_raw.png
```

Raw output:

```text
raw_size=(1308, 1202)
baseline_size=(4192, 3848)
raw_resized_for_bounded_composite=True
raw_changed_bbox_after_optional_resize=(0, 0, 4192, 3848)
raw_max_delta=182
```

Verifier:

```text
PASS candidate=tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/external_edit_probe/openai_bounded_candidate.png bbox=(0, 1120, 621, 2921) max_delta=159 inside_allowed_changed=669176 outside_allowed_changed=0 hotel_base_changed=0 allowed_box=(0, 900, 860, 3050) hotel_base_box=(3162, 2582, 4082, 2845)
```

Visual note: this is the best external candidate from this probe. It removes the tower-sphere ghost and replaces the harsh foreground wipes with coherent illustrated content. Caveat: the raw edit was lower resolution than the baseline, so the bounded patches are sharper/stronger than the surrounding original watercolor.

## Nano Banana / agy image edit probe

Command:

```bash
python3 scripts/subgen.py --provider nano --prompt-file tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/external_edit_probe/openai_bounded_prompt.md --out tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/external_edit_probe/nano_bounded_raw.png -i tasks/berlin-hotel-base/wave2/BANKED_CURRENT_BEST/berlin_hotel_base_current_best.png tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/external_edit_probe/issue_mask_feathered.png --timeout 420 --retries 1
```

Result:

```text
[subgen nano] OK attempt 1 -> tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/external_edit_probe/nano_bounded_raw.png
```

Raw output:

```text
raw_size=(1024, 1024)
baseline_size=(4192, 3848)
raw_resized_for_bounded_composite=True
raw_changed_bbox_after_optional_resize=(0, 0, 4192, 3848)
raw_max_delta=232
```

Verifier:

```text
PASS candidate=tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/external_edit_probe/nano_bounded_candidate.png bbox=(0, 1120, 621, 2921) max_delta=224 inside_allowed_changed=670143 outside_allowed_changed=0 hotel_base_changed=0 allowed_box=(0, 900, 860, 3050) hotel_base_box=(3162, 2582, 4082, 2845)
```

Visual note: mechanically bounded, but not recommended. The square raw output created visible rectangular seams, changed the tower form too aggressively, and introduced a disjoint tower-tip/sphere relationship inside the mask.

## Photoshop connector probe

Tool attempted:

```text
mcp__codex_apps__adobe_photoshop._instructedit
nativeImage=/Users/za/Documents/product images repo/tasks/berlin-hotel-base/wave2/BANKED_CURRENT_BEST/berlin_hotel_base_current_best.png
resolutionLevel=4MP
promptReasoner=quality
seed=220623
```

Prompt summary: edit only `x=190..470 y=1120..1580` and `x=0..620 y=2050..2920`, repair the TV tower sphere ghost and foreground wipes, and preserve the rest of the image.

Result:

```text
McpServerError: Forbidden
error_code=FORBIDDEN
http 403
url=https://photoshop-mcp-service.adobe.io/mcp
```

No Photoshop image was produced.
