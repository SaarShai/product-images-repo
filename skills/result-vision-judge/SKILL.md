---
name: result-vision-judge
description: Use whenever judging/reviewing a generated illustration against a geometry template — by YOU or a sub-agent. Judge on BOTH vision (look at the candidate WITH the SVG-geometry overlay drawn on it) AND the geometry calculation (region-IoU / white-IoU). Never score from the metric alone or the raw image alone. Writes a judge.json verdict into the results library.
effort: medium
---

# Result Vision Judge

A reviewer — you or an agent — must NOT conclude "good/bad" from a number or a
glance. Judge every candidate two ways and combine them:

1. **Geometry calculation** (objective): `region-IoU` (placement, fill-agnostic)
   + `white-IoU`/`painted_frac`/`outside_frac` (cutout cleanliness).
2. **Vision** (corroboration): actually LOOK at the candidate **with the geometry
   overlay** — the SVG openings drawn on top (green = landed right, red = missed)
   — so you SEE how the result relates to the required geometry, not just trust a
   scalar. Also look at the style references to score style.

The calculation and the eye must **agree**. When they disagree, that disagreement
is itself the finding (the metric is lying, or the render fooled the eye) — record
it, don't average it away. A flat panel that scores region-IoU 0.97 is NOT a good
result; a gorgeous panel whose openings are circles where the SVG wants hexagons is
NOT either. Score geometry AND style; overall reflects BOTH.

## Required inputs

- Candidate image (`raw.png`, and `exact.png` if present).
- Source SVG (the geometry contract).
- Geometry overlay (generate it if missing — see step 1).
- Style reference image(s) / style packet.
- The geometry score JSON (`region_iou.json`, `metrics.json`) if present.

If an input is missing, say so and judge only what you can inspect.

## Protocol (run every time)

**Step 1 — prep (one command): compute the calc + draw the overlay.**
```bash
bash skills/result-vision-judge/tools/judge_prep.sh <candidate_dir> <source.svg>
# writes <candidate_dir>/region_overlay.png  (SVG openings drawn on the candidate)
#        <candidate_dir>/region_iou.json      (region-IoU per opening + mean)
#        <candidate_dir>/whitecheck.json       (white-IoU / painted_frac / outside)
```

**Step 2 — LOOK (mandatory).** Open with an image tool (Read), in this order:
- `region_overlay.png` — judge geometry closeness from the green/red overlay.
- the candidate (`raw.png`/`exact.png`) — judge style + cutout cleanliness.
- the geometry contract (true-aspect base or the SVG render) — confirm shapes
  (e.g. hexagons vs circles, slot position, V-notch).
- the style reference(s) — score style vocabulary, edge/rim treatment, palette.
A score produced without having opened the candidate AND the overlay is invalid.

**Step 3 — score** (0–5 each, calibrated, not generous):
- `geometry_score` — openings at the EXACT position/size/SHAPE; silhouette right;
  no paint outside the contour. Vision (overlay) must corroborate the region-IoU.
- `cutout_cleanliness` — opening centers clean/empty; no smear/halo/blue-block/
  sliced hardware around cutouts.
- `style_score` — matches the references' object vocabulary (knobs/toggles/dots),
  hand-painted rim lines, bevel + inner shadow + pale lip, granulated wash,
  density — not just palette.
- `overall_score` — holistic; a result must be strong on BOTH axes to score high.
- `region_iou_agreement` — does the calc agree with what you SEE? `agrees` /
  `overstates` / `understates` + why.

**Step 4 — verdict + write to the library.**
Verdict ∈ `ACCEPT | LOCAL PATCH | PROMPT RESTART | BLOCKED`. Write the full verdict
to `<candidate_dir>/judge.json` (schema below), then `python3 scripts/results_db.py`
folds it into `results.jsonl` + `RESULTS-BOARD.md` (`judge-geom`/`judge-style`/
`judge-verdict` columns). For a high-stakes/contested call, get a cross-vendor
(GPT-vision via `codex exec -i`) second opinion and store it under `crosscheck_gpt`.

## judge.json schema

```json
{
  "geometry_score": 0,            // int 0-5
  "geometry_notes": "per-opening placement/shape; outside-contour; silhouette",
  "cutout_cleanliness": 0,        // int 0-5
  "style_score": 0,               // int 0-5
  "style_notes": "vocabulary / rim+bevel edge treatment / palette / density vs refs",
  "overall_score": 0,             // int 0-5 (strong only if BOTH axes strong)
  "region_iou_agreement": "agrees|overstates|understates + why",
  "verdict": "ACCEPT|LOCAL PATCH|PROMPT RESTART|BLOCKED",
  "passes": ["specific pass"],
  "failures": ["specific failure or risk"],
  "next_move": "one concrete action",
  "one_line": "what's good and what's bad and BY HOW MUCH",
  "crosscheck_gpt": { "gpt_verdict": "", "gpt_geometry": "", "gpt_style": "", "gpt_note": "" }
}
```

## Verdict note format (when reporting to a human)

```text
Verdict: ACCEPT | LOCAL PATCH | PROMPT RESTART | BLOCKED
Scores: geometry G/5  cutout C/5  style S/5  overall O/5  (region-IoU=<calc>, agreement=<agrees|over|under>)
Evidence inspected:
- <overlay path>
- <candidate path>
Passes:
- <specific>
Failures/risks:
- <specific>
Next move:
- <one action>
```

## Notes
- Pairs with `svg-template-review-judge` (the broader accept/patch/restart rubric);
  this skill is the always-on, overlay-grounded SCORING half that feeds the library.
- For a fleet review, fan out one judge per candidate (each runs this protocol),
  then reconcile with `results_db.py`. Generator and judge must be SEPARATE agents.
