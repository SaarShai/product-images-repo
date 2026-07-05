---
name: studio-style-executor
description: "Generate styled panel art: one-pass control+LoRA route (default when a trained LoRA exists), ref-anchored restyle for style correction, style packet + hold-out rule, comparison-board judging. Style refs are IMAGE INPUTS, never prose."
effort: medium
---

# style-executor — one-pass gen, restyle, style judging

Promoted 2026-07-05 after gpt-5.5 read-critique + execution sim, and validated end-to-end on Cap Juluca (easy) + Marriott 3-panel (hard). History: `../DRAFT-style-executor.md`.

## Route A — ONE-PASS control+LoRA (DEFAULT when a trained LoRA exists)

```
python3 scripts/onepass_gen.py --control <panel>-control.png \
    --lora-json <collection>/lora.json --prompt "<TRIGGER> <content>" \
    --width <W> --height <H> --out-prefix <dir>/rN_<panel> -n 3 \
    [--control-scale 0.35] [--lora-scale 1.05] [--mask <panel>-mask.png] [--dry-run]
```
- ALWAYS `--dry-run` first (prints exact request, zero spend). The wrapper refuses a prompt missing the LoRA trigger word, auto-appends the BLANK-signage clause, and with `--mask` scores every output inline.
- `--control-scale` is the geometry↔style dial: 0.35 proven; raise toward 0.6 for tighter geometry, lower for more style.
- LoRA registry: per-collection `lora.json`; usable iff `status=="COMPLETED"` + `lora_url`. Never invent LoRA ids.
- Proven numbers: silhouette-IoU 0.975–0.988 first-shot across 30+ candidates.

## Route B — no LoRA: refs as image inputs

`python3 scripts/falgen.py --mode flux2edit --image <src> --refs <ref1> <ref2> --out <out> --prompt "..."`. Style refs are ALWAYS image inputs; description-only style = forbidden (proven: prose → dark monochrome drift).

## Route C — ref-anchored RESTYLE (style correction of a geometry-good candidate)

Proven Marriott r5: `falgen.py --mode flux2edit --image <full-bleed cand> --refs <ACTUAL ref image>` + minimal prompt: "Repaint in EXACTLY the reference's art style ... keep composition/framing exactly — same crop, do not zoom ... all signs blank". Then deterministic MASK-CUT aperture lock: resize `<panel>-mask.png` to candidate, outside→white, re-gate. Yields IoU 0.985–0.998 at ref-level style.
- Do NOT describe the style in prose — that's description-anchored drift (r4 lesson: "dense wool-felt, 3D relief" prose washed out the palette).
- Watch COLOR PULL: the ref's palette can override the source design's colors. To keep source colors: "keep this building's own colors — <colors>; copy only the reference's material and craftsmanship."
- Restyle from a FULL-BLEED source or fill_inside drops after the cut.
- Cross-panel consistency: feed one approved panel as the ref for the others ([[reference-lock-for-consistency]]).

## Style packet + hold-out

- Packet builder: `python3 scripts/build_reference_style_packet.py <task_dir> --refs <r1 r2 ...>` (positional task dir).
- HOLD-OUT rule: never a target panel's OWN art as its style ref (measures recreation, not generalization). Check by sha256 vs the library (`studio.library.query`), path heuristic as fallback.

## Judging (the r4 lesson — binding)

1. Build a COMPARISON BOARD: refs row + one row per candidate round, same scale. Never judge from memory or a single contact sheet.
2. Deterministic gates first (free): `python3 -m studio.controlmap --score ...` + `python3 scripts/geom_gate.py --cand ... --mask ...`.
3. VLM check: `python3 scripts/judge.py --mode check --image <cand> --criterion "<felt style / blank signage / required content>"`; pairwise: `--mode pairwise --image <A> --ref <B> --criterion "<c>"` (single gpt-4o judge; output = winner/consistent — there is no style_delta). Close aesthetic calls → HUMAN arbiter, always.
4. No-spend mode (sim/CI): gen `--dry-run`, judge SKIPPED and recorded as such — run is then NOT acceptance-complete. Deterministic gates always run.

## Finish chain (winners only)

`scripts/reupscale.py --image <in> --out <out> --creativity 0.5 --resemblance 0.6 --factor 2` → `scripts/dehalo.py --image <in> --out <out>` → `scripts/white_key.py --image <in> --out <out>`. Assemble panels at their `bbox_svg` positions in the shared `viewbox` (read both from spec.jsons).

## Done means

- Every candidate in the results library (`studio.library.add_result`, lib `studio/library_store`) with route + scores.
- Comparison board built; gate JSONs quoted; human shown ALL candidates full-size, not a sample.
- Nothing promoted to production `Images/finals` without explicit user approval.

## Internal-cut geometry (2026-07-05, binding)

Mask-cut fixes the OUTER silhouette only. Restyle engines (flux2edit) drift
INTERNAL cut geometry (saloon-arch door cuts) — proven: r6/r7 arch off the cut
path, option H shrank the whole facade (overlay board:
`tasks/marriott-hospital/outputs/geometry-overlay-board.jpg`). Rules:
- Restyle+mask-cut = PREVIEW-ONLY for panels with internal cuts. Final art for
  cut-bearing panels comes from the one-pass control route (cut edges in the
  control channel) — geometry by construction.
- Prompt-only style in the one-pass route COLLAPSES under a strong control
  channel (r8: flat digital look + garbled painted text despite blank clause).
  The style must ride in a LoRA trained on the TRUE flat-art style (Rule 0:
  text-free, frame-free, opening-free crops — dirty crops teach text/substrate).
- Acceptance for cut-bearing panels adds the OVERLAY check: red cut paths over
  the candidate; painted structure must align with every internal cut. IoU
  cannot see this.
