# LOOP.spec — closed verify loop for SVG → exact-geometry styled illustration

The generator is the **structure-locked backend** (pluggable, Stage 3 of
`PIPELINE.md`). The verifier is **`scripts/svg_geometry_check.py`**, run as a
SEPARATE scoring actor (via `geom_adherence_test.py`), never the generator. The
gate is the exact-geometry triple-condition. Stop on accept or `N` rounds;
budget caps `N`. The fenced block below is the `loop_lint.py` input contract.

```loop
name: svg-exact-geometry-styled-illustration
topology: closed · inner · fleet
generator: structure-locked backend (pluggable: diffusers-ControlNet | ComfyUI | hybrid-bevel | gpt-image-refine), N candidates per round, opus/sonnet art-director prompts
verifier: scripts/svg_geometry_check.py run by a SEPARATE scoring step (geom_adherence_test.py), never the generator
gate: python3 scripts/svg_geometry_check.py CAND --svg TEMPLATE.svg --bbox L,T,R,B --json-out m.json && mean_iou >= 0.85 && max_painted_frac <= 0.03 && outside_frac <= 0.02
stop: a candidate clears the gate (accept) OR N rounds exhausted
budget: max_iterations=6
quorum: best-of-N select by highest mean_iou then lowest max_painted_frac; accept only if the selected candidate passes the gate, else escalate to hybrid-bevel backstop
```

## Gate — three machine-checkable conditions (AND)

All three are read from the verifier's `metrics.json`. The verifier already
computes them; the gate is the conjunction.

| condition | threshold | source field | meaning |
|---|---|---|---|
| `mean_iou ≥ 0.85` | **0.85** | `metrics.mean_iou` | each opening rendered at (near-)exact coordinate |
| `max painted_frac ≤ 0.03` | **0.03** | `max(holes[].painted_frac)` | no opening bled into beyond 3% |
| `outside_frac ≤ 0.02` | **0.02** | `metrics.outside_frac` | ≤2% of panel paint outside the contour |

## Threshold justification (grounded in measured data + the existing tool defaults)

**`max painted_frac ≤ 0.03`** — this is `svg_geometry_check.py`'s own
`--cutout-tol` default (0.03). Using the tool's native per-hole PASS tolerance
keeps the loop gate identical to the mechanical check the repo already trusts;
no new constant invented. Measured pure-model runs sit at 0.37–1.0 painted_frac
(E1 0.45–0.52, E5 0.33–0.54, Nano 1.0) — i.e. all current routes FAIL this by a
wide margin, which is exactly why the loop + backstop exist.

**`outside_frac ≤ 0.02`** — this is `svg_geometry_check.py`'s hard-coded
silhouette tolerance (`silhouette_fail = outside_frac > 0.02`). Reusing it means
the loop's silhouette gate == the tool's overall verdict, so a loop PASS can
never disagree with a standalone `svg_geometry_check.py` PASS. Measured runs are
0.066–0.084 (3–4× over), again confirming pure-prompt routes miss it.

**`mean_iou ≥ 0.85`** — the placement-fidelity target. Anchored between two
measured points: the best pure-model run to date is **E5-bestof-1 at 0.436**, and
the SYSTEM-BUILD-PLAN names **0.9** as the goal vs a **0.449** gpt-image
baseline. Choosing **0.85** (not 0.9):
- 0.85 is comfortably above every measured pure-model result (max 0.436), so the
  gate can only be cleared by a genuinely structure-locked backend
  (ControlNet/ComfyUI) or the exact backstop — it cannot be gamed by a lucky
  gpt-image sample;
- it leaves ~0.05 headroom below the 0.9 aspiration to absorb verifier noise
  (the white-IoU is measured in a 50%-dilated bbox and is sensitive to a few px
  of anti-aliasing), so a backend that is genuinely on-coordinate isn't bounced
  by sub-pixel jitter;
- the `hybrid-bevel` backstop scores ≈1.0 by construction, so the *deliverable*
  is never blocked by the threshold — 0.85 only decides whether a *model-rendered*
  candidate is good enough to skip the backstop.

If a winning backend reliably clears 0.9, raise the threshold to 0.9 (one
constant in `pipeline_run.py`); the loop shape is unchanged.

## Topology + wiring (why each axis)

- **closed** — bounded paths, ships on the gate; novelty is not wanted here, exact
  fit is. (open would drift and burn budget; RESEARCH already mapped the space.)
- **inner** — within one task: generate → score → confirm pass THEN deliver; regen
  on fail. (The outer/across-session learning — "which backend won" — is handed to
  `task-retrospective` + `wiki-memory`, not re-implemented here.)
- **fleet** — N candidates per round (best-of-N is the reliability layer,
  RESEARCH rank #2), converged by the `quorum` select-then-gate rule.
- **generator ≠ verifier** — the backend produces; `svg_geometry_check.py`
  (run by `geom_adherence_test.py`'s scoring step) grades. The producer never
  scores its own candidate; the verdict is recomputed from `metrics.json`, never
  taken from a model "done" claim (anti-Ralph-Wiggum, R3).
- **stop on recomputed gate state** — accept only when the three conditions hold
  in the freshly-written `metrics.json`, not on a generator's say-so.

## Instrumentation (loop-engineering "instrument before you scale")

`pipeline_run.py` records per run: iteration count, accept-rate, per-round
failure reason (which condition missed), per-backend cost/secs, and
**cost-per-accepted-candidate**. If accept-rate over a backend stays under ~50%,
that backend is making review work, not saving it — evidence to switch the
default `--backend` to the race winner (or to lean on the backstop).

## Run `loop_lint.py` on this spec

```bash
python3 skills/loop-engineering/tools/loop_lint.py tasks/space-np01-front-bottom-02/experiments/LOOP.spec
# optional: see it
python3 skills/loop-engineering/tools/loop_lint.py --diagram tasks/space-np01-front-bottom-02/experiments/LOOP.spec
```

### Confirmation it passes (validated)

Linting the fenced block above returns **exit 0** (`0 fail · 0 warn`):

- **R1 (no-gate)** — PASS. The gate names a command-anchored code file
  (`scripts/svg_geometry_check.py`, matches `_STRONG_GATE`) AND code-like
  assertions (`mean_iou >= 0.85`, `outside_frac <= 0.02` — `_CODELIKE` operands).
- **R2 (no-stop-or-budget)** — PASS. `stop` is present and measurable; `budget`
  binds a number to a cap unit (`max_iterations=6`).
- **R3 (self-grading)** — PASS. `generator` (the backend) and `verifier`
  (`svg_geometry_check.py` / scoring step) are distinct actors; no shared model
  slug or acting proper name.
- **R4 (open-no-ack)** — N/A, topology is `closed`.
- **R5 (fleet-no-quorum)** — PASS. `fleet` topology has a `quorum` field
  (best-of-N select-then-gate).
- **R6 (no-topology)** — PASS. `topology: closed · inner · fleet` is declared.
- **R7 (irreversible-no-human)** — N/A. The loop names no deploy/merge/migrate/
  charge; the only side effect is writing candidate images and metrics.

No self-grading (R3 clean: generator ≠ verifier), has a gate (R1), and has both
stop + budget (R2). The spec is itself a closed inner loop with `loop_lint.py`
as its gate — if any field regresses, re-lint until exit 0.
