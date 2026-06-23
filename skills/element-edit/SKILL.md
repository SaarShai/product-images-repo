# element-edit — edit ONE element of a finished illustration, change nothing else

Use when the task is: redraw / remove / restyle / reshape / move a single element inside a
finished watercolor+ink illustration (or any fixed art) while keeping the rest byte-identical.
This encodes the verified pipeline so you never re-derive it or hand-eyeball masks again.

## One command (preferred)
```
python3 scripts/edit.py --src IMG --op remove  --element "the small yellow taxi" [--box x0,y0,x1,y1]
python3 scripts/edit.py --src IMG --op redraw  --element "the yellow taxi" --desc "a clean classic NYC sedan"
```
It runs: auto-mask (text) → mask guardrail → routed engine → diff-mask composite + pixel gate →
VLM judge, and prints SUCCESS/NEEDS-REVIEW with the gate + judge results. Always open the
`*_editov.png` overlay to confirm.

## The pipeline (what edit.py chains; use the steps directly for non-standard ops)
1. **Mask from TEXT, never eyeball** — `scripts/automask.py --image X --prompt "the element"` (fal SAM-3).
   Disambiguate a specific instance with `--box` (edit.py crops to it first). Post-processed +
   `--dilate ~8-12` (covers ink halos). [[auto-mask-and-guardrail]]
2. **Guardrail BEFORE spending** — `scripts/mask_check.py` (containment/leak; exit 2 on fail) or eyeball
   the overlay. Catches the off-by-100px mistake for free.
3. **Route engine by op** (don't re-derive): [[image-edit-engine-routing]]
   - remove → `falgen.py --mode eraser` (fal Bria) — reconstructs bg in-style. NOT flux-fill (it heals back).
   - redraw in place → `falgen.py --mode fill` (Flux Fill) + a prompt from `prompt_templates.py`.
   - restyle keeping layout → Flux.2 edit; reshape to exact dims → stretch-then-Kontext ([[element-reshape-stretch-then-refine]]).
   - same element across many instances → reference-lock ([[reference-lock-for-consistency]]).
   - broad ghost/haze or smeared local artifact → mask-bounded external redraw donor:
     bank the best full-res baseline, generate an OpenAI edit via `scripts/subgen.py`,
     treat the raw output as a donor only, composite it back through the issue mask,
     then verify outside-mask delta is 0. This is the preferred escalation when
     conservative clone/inpaint variants pass mechanically but look blocky or
     smeared. See [[concepts/mask-bounded-external-redraw-donor]].
4. **Composite + MEASURE** — `compose_fairy.py --diffmask`; outside-mask delta MUST be 0. In busy
   scenes a global-repaint engine seams → use masked-inpaint so the diff is localized. [[element-edit-diffmask-composite]]
5. **Auto-verify** — `judge.py` check (leftover-text/artifacts hard gate); use `--mode pairwise` to pick
   the best candidate. Absolute "wellformed" is lenient on loose art → pairwise for quality. [[auto-verify-judge]]

## Prompts
Build edit prompts from `scripts/prompt_templates.py` (anti-reframe + positive-no-text + prescribe-medium).
Never say "keep the style"; prescribe the medium. Never rely on negative prompts to remove things — erase.

## Efficiency
- Cache: `--cache` on falgen (deterministic calls; pin `--seed`); automask caches always. [[auto-mask-and-guardrail]]
- Parallel fan-out: `scripts/falbatch.py --jobs jobs.json` (fal queue, ~slowest-call wall time).
- For subscription image edits, prefer `scripts/subgen.py --provider openai`
  over ad-hoc nested `codex exec`; it validates real image output and avoids
  timeout/orphan/newest-image races.
- Regression: `python3 scripts/eval_runner.py` must stay green after changes.

## Hard rules
Source art (Drive) is READ-ONLY → copy first. REFERENCE/GEOMETRY beats prose. Verify before claiming
done; show full-size; link text = filename. Maximize fan-out across candidates, gate objectively.
