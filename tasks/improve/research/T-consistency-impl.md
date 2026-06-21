# T — Cross-instance consistency: redraw the SAME element across MANY instances (`consistency.py`)

**Status: PASS** — built `scripts/consistency.py`; on the NYC-taxi stand-in test it
redrew the middle taxi to match an approved left-cab reference, gate passed
(`outside_changed=0`), and the pairwise consistency judge returned **MATCH**
(`set_consistent=True`). Eyeballed the contact sheet: same design.

## Goal

Realize the **reference-lock** rule from memory: to redraw one character/element
consistently across many instances, feed the *approved* instance as a reference so
each redraw MATCHES it, then **judge the set together** (not one instance alone).
(Fairy task: 5 fairies must match one approved design — taxis here are a cheap
stand-in.)

## Design

`scripts/consistency.py` (only new file; everything else reused unchanged).

Inputs:
- `--src IMG` — the full illustration containing all instances.
- `--ref APPROVED.png` — the canonical instance (a crop of the approved design).
- `--targets` — JSON list (inline or `@file.json`), one entry per instance:
  - `{"box":"x0,y0,x1,y1", "out_suffix":"name"}` — explicit box, OR
  - `{"element":"the yellow taxi", "search_box":"...", "out_suffix":"name"}` — box
    resolved via SAM-3 `automask.py` (center-filtered by `search_box`).
- `--prompt` / `--prompt-file`, `--outdir`, `--extra-ref` (more refs beyond `--ref`),
  `--gate` (max outside-mask changed px, default 0), `--diff-thresh`, `--retries`
  (bounded), `--criterion` (judge question).

Per-instance pipeline:
1. **Resolve box** — explicit, or automask from `element` text.
2. **Redraw** via `scripts/falref_apply.py` → `image_urls=[target_region, REF, *extra]`
   (Flux.2-pro/edit reproduces the canonical design inside the target crop). Bounded
   retries on failure.
3. **Rescale + composite** — emit a crop-sized `region.png` (rescale raw→box) for the
   sheet/judge, then composite back onto `--src` with `scripts/compose_fairy.py
   --diffmask`. **Gate** on `OUTSIDE-MASK changed_pixels <= --gate` (diffmask keeps
   surroundings byte-exact; figure-only paste).
4. **Consistency check** — `scripts/judge.py --mode pairwise` on `region` vs `ref`,
   both orders. Interpretation: a clear, order-stable winner = a *detectable
   difference* → `DIFFERS`; `winner=="tie"` or `consistent==False` (judge can't
   reliably tell them apart across both orders) → **MATCH** (indistinguishable from
   the ref = the design carried over). This is the right reading for *consistency*:
   we want the redraw to be indistinguishable from the approved instance.

Outputs per instance: `<suffix>.raw.png` (falref region), `<suffix>.final.png` (full
src, only this instance redrawn), `<suffix>.region.png` (redrawn region for sheet/
judge). Set-level: `_consistency_sheet.png` (**REF first, then every redrawn region,
each labeled with its MATCH verdict**) and `_consistency.json` (per-instance gate +
verdict + set summary). Exit 0 iff every instance MATCHes and gate-passes
(`set_consistent`), else 2.

Notes / hardening:
- `falref_apply` returns the region at the model's own size; we rescale to the exact
  crop box before compositing and for the region crop (handles the rescale the spec
  flagged).
- The pairwise judge prints JSON mixed with urllib3 SSL warnings on this host;
  `parse_match` scans for the first balanced top-level `{...}` so the warning noise
  can't break parsing (this was the one bug found + fixed during the test).
- No secrets printed — keys are read inside the reused scripts from `.secrets/`.

## TEST (cheap, NYC taxis as stand-in instances)

- `--src tasks/nyc-taxi/out/nyc-fixed.png` (4192×3848).
- `--ref` = crop `150,2950,1260,3370` of the left cab → `tasks/improve/_left_cab_ref.png`
  (1110×420).
- target = middle taxi box `1700,2950,2700,3340`, suffix `mid`.
- prompt `tasks/improve/_consistency_prompt.md` (restyle the cab to match the
  reference design; don't touch background). `--gate 0 --retries 2`.

Command:
```
python3 scripts/consistency.py \
  --src tasks/nyc-taxi/out/nyc-fixed.png \
  --ref tasks/improve/_left_cab_ref.png \
  --targets '[{"box":"1700,2950,2700,3340","out_suffix":"mid"}]' \
  --prompt-file tasks/improve/_consistency_prompt.md \
  --outdir tasks/improve --gate 0 --retries 2
```

Run output:
```
[consistency] === instance 'mid' ===
[consistency]   gate_pass=True outside_changed=0 match=MATCH
[consistency] SET: 1/1 MATCH, 1/1 gate-pass  set_consistent=True
```

Independent verification (not just the script's own report):
- **Composite isolation**: final-vs-src changed bbox = `(1700,2950,2699,3339)` —
  entirely inside the target box; **0 pixels changed outside the box** (surroundings
  byte-exact). Confirms `--diffmask` gate.
- **Eyeball** `tasks/improve/_consistency_sheet.png`: REF (left cab) and the redrawn
  middle taxi sit side by side — same hand-drawn watercolor+ink yellow cab, same warm
  yellow body, dark ink outline, "TAXI" door lettering, boxy 1980s-sedan silhouette.
  The redraw is clearly the same design as the reference.

## Match verdicts

| instance | box | gate (outside_changed) | judge winner / consistent | verdict |
|----------|-----|------------------------|---------------------------|---------|
| mid | 1700,2950,2700,3340 | PASS (0) | tie / false | **MATCH** |

Set summary: **1/1 MATCH, 1/1 gate-pass, set_consistent=True**.

## Artifacts
- `scripts/consistency.py` — the pipeline (only new file).
- `tasks/improve/_consistency_sheet.png` — contact sheet (ref vs redrawn instances).
- `tasks/improve/_consistency.json` — machine report.
- `tasks/improve/mid.{raw,region,final}.png` — per-instance outputs.
- `tasks/improve/_left_cab_ref.png`, `tasks/improve/_consistency_prompt.md` — test inputs.

## PASS/FAIL: **PASS**
