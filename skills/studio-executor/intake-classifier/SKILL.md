---
name: studio-intake-classifier
description: "Classify an incoming product-image task into a family and emit a VALIDATED PanelPacket (studio/packet.py) — the single contract every downstream executor reads. LAW 0 gate: template families need an SVG; style refs are always required."
effort: medium
---

# intake-classifier — task → validated PanelPacket

Promoted 2026-07-05 after gpt-5.5 read-critique + execution sim (both passed post-fix).
History/rationale: `../DRAFT-intake-classifier.md`.

## Output = one thing

A packet JSON that passes `studio.packet.validate_packet` with `[]`. Nothing else counts.

## Families

| family | trigger | svg required |
|---|---|---|
| template-panel | die-cut panel art (door/narrow/skyline/edge-socket) | YES |
| element-edit | change ONE element of finished art | no (source image is the geometry) |
| upscale-finish | blur/melt fix, bg removal, finishing | no |
| free | unconstrained illustration | no |

STOP rules (write STOP + reason in your report; emit no packet):
- template family AND no SVG → STOP.
- ANY family AND no style reference images → STOP (LAW 0 — prose style is forbidden).

## Steps

1. **Inventory inputs.** SVG path, ref images (verify each exists + opens with PIL), source design, task text.
2. **Pick family** (table above). Element-edit: the source artwork doubles as its own style ref — set `style.ref_images = [source_image]`; the run routes to `scripts/edit.py`, not fresh gen.
3. **Spec.** Skyline templates: `python3 scripts/skyline_panel.py --svg <svg> --panel <door|left|right> --mode spec` (all three flags required). Other templates without a spec: `spec_json_path: null` + flag for human. Never hand-author.
4. **LoRA lookup.** Per-collection `lora.json` (e.g. `.brainer/tenx/marriott-lora/lora.json`). Usable iff `status=="COMPLETED"` and `lora_url` present. OMIT `style.lora_id` entirely when absent — `null` fails validation.
5. **Output dirs.** User pointed at a production folder → `output.production_images_dir = <that folder>/Images`. Otherwise `tasks/<task_id>/Images` + `"production_dir_pending": true` in meta — never guess a Drive path.
6. **Emit + validate (mandatory final step):**
   ```
   python3 -c "from studio.packet import validate_packet; import json; print(validate_packet(json.load(open('<packet.json>'))))"
   ```
   Must print `[]`. Fix and re-run until it does.

## Packet shape (canonical — studio/packet.py, not this doc)

Valid `panel_type`: `door | narrow | generic | skyline | edge-socket`.
Gate threshold field: `gates.geom_iou_min` (default 0.85). Output keys: `output.production_images_dir`, `output.task_dir`.
Prompts downstream will auto-carry the BLANK-signage rule (no painted text — text is an .ai vector layer).

## Effort estimate

S = one panel, existing LoRA + spec. M = ≤3 panels or new control map/content edges. L = LoRA training, new template family, or >3 panels.

## Done means

- Packet file written AND `validate_packet` printed `[]` (paste the output).
- Every referenced path in the packet exists.
- STOPs reported with the failed rule quoted.
