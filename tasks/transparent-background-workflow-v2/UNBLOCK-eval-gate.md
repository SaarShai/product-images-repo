# Unblock note (from Claude session, 2026-07-12 03:45)

## Your eval-gate 404, diagnosed

`eval_gate.py` DEFAULT_MODEL is `qwen2.5:7b-instruct` — NOT installed on this host
(installed: gemma4:26b-mlx, gemma4:31b-mlx, deepseek-r1:32b, qwen3.6:35b-a3b-q4km).
Absent tag → Ollama /api/generate returns HTTP 404 → "judge unreachable". The file's
own comment (line 47) documents exactly this.

Fix attempt status: `EVAL_GATE_MODEL=gemma4:26b-mlx` (or 31b) clears the 404 but the
judge output is unparseable ("judge returned no parseable score"); qwen3.6 emits
reasoning chatter the parser also can't score. So on this host eval-gate currently has
NO working ollama judge — options: `--stub-score` to keep the pipeline moving, mimo
backend, or harden the score parser for reasoning models.

## Your round-2 arms — already measured (you don't need eval-gate for this)

aura_gate --nonwhite on the raws, then white_key --reopen-interior:

| arm | aura_index | band | hit_rate | verdict |
|---|---|---|---|---|
| a2-control-repeat | 0.105 | 3.33 | 0.976 | PASS |
| d-crisp-boundary-no-outline | 0.122 | 3.70 | 0.969 | PASS |
| e-subtle-matching-outline | **0.084** | **2.91** | **0.981** | PASS |

Ranking: e (subtle matching outline) > a2 (control) > d (crisp boundary, no outline).
Consistent with round 1 (B 0.080 < A 0.132): the colored outline is what buys edge
margin; "crisp boundary" language without an outline measures WORSE than control.

Keyed RGBAs + .aura.json sit next to your PNGs in `white-outline-ab/round2/`.
Caution: `--reopen-interior` (new white_key flag) false-positived on pale tube-coral
openings in these images (punched them transparent) — inspect before shipping keyed
outputs, or key without the flag.

Converged findings from the parallel Claude lane (full recipe:
`wiki/concepts/transparent-clear-edge-prompt-recipe.md`, results:
`REVIEW/transparent-clear-edge-claude/RESULTS.md`): minimal 2-sentence edge block ≈ full
arm-B language; interior-white sentence is load-bearing; reference-authority core cures
density drift; keyability module needs an explicit deviation-authorization sentence when
the reference itself has thin features (3/6 → 3/3 compliance).
