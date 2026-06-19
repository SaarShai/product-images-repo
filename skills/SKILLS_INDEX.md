# Brainer Skills

Lean skills for AI coding agents (Claude Code · Codex · Cursor · Gemini · Copilot) across four pillars: **(1)** token-use optimization, **(2)** context-window optimization & management, **(3)** LLM wiki-memory framework, **(4)** self-improvement & learning.

This replaces the old `start.md` boot doc. Each skill is a self-contained folder under `skills/<name>/`. Skill descriptions are the only thing always resident in the agent's context; full bodies load on trigger.

For measured per-skill deltas and the live A/B table see [`eval/FINDINGS.md`](../eval/FINDINGS.md); each skill also ships its own `EVAL.md`.

## Catalog

| Skill | One-line |
|---|---|
| [caveman-ultra](caveman-ultra/SKILL.md) | Terse output style. Drops filler; preserves code/numbers/errors verbatim. |
| [plan-first-execute](plan-first-execute/SKILL.md) | Plan before non-trivial/spec-worthy tasks: separate WHAT from HOW, clarify load-bearing unknowns, derive tasks from acceptance criteria, then execute. |
| [think](think/SKILL.md) | How an agent should think: first-principles, reduce/simplify, research & borrow, experiment-to-falsify; ideation + 5-whys + pre-mortem/inversion. **Slash-only** (`/think`). |
| [lean-execution](lean-execution/SKILL.md) | Prune plans/scope to the smallest safe path. |
| [verify-before-completion](verify-before-completion/SKILL.md) | Run fresh verification before claiming done. |
| [wiki-memory](wiki-memory/SKILL.md) | Repo-local markdown wiki: progressive retrieval + gated writes. |
| [prompt-triage](prompt-triage/SKILL.md) | Pre-model classifier hook; routes simple tasks to cheap models. |
| [context-keeper](context-keeper/SKILL.md) | PreCompact hook: structured memory before compaction. |
| [semantic-diff](semantic-diff/SKILL.md) | AST-node diff on file re-reads (95%+ savings; slim Bash CLI default ~9-18M, optional MCP). |
| [index-first](index-first/SKILL.md) | Prefer pre-built indexes / composite verbs over grep+read chains; batch N related lookups into one capped call. |
| [output-filter](output-filter/SKILL.md) | Strip ANSI/progress/dup noise from terminal output; content-aware search/log/diff summaries keep raw output recoverable via archive id / `rewind --grep`. |
| [compliance-canary](compliance-canary/SKILL.md) | UserPromptSubmit hook: the **single always-on drift watcher**. Two mechanisms in one process — (1) symptomatic per-skill `drift_probes.json` scans (filler regex / word-count creep / claim-without-evidence / looping tool errors), and (2) a periodic skill-rule **re-anchor** every N turns (paper-calibrated, arXiv 2510.07777). The re-anchor yields to a fired probe (no double-nag). Absorbed `skill-pulse` (v1.10). Ships an offline `measure.py`. **Default-on since v1.7** (cross-model longrun: +0.44 probes / +0.27 re-anchor, 2 model families). |
| [write-gate](write-gate/SKILL.md) | Content-quality gate before persistent writes. Signal-score (decisions / errors / architecture / code / numbers, minus filler / speculation) + why-clause enforcement for decisions. Lineage: ogham-mcp + codenamev/claude_memory. |
| [wiki-refresh](wiki-refresh/SKILL.md) | Reconcile wiki pages against the current codebase (Keep/Update/Consolidate/Replace/Delete); code-grounded via `audit-refs`, emits typed `contradicts:` edges. Ground-truth reconcile. Lineage: [EveryInc/compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (`plugins/compound-engineering/skills/ce-compound-refresh`). |
| [cache-lint](cache-lint/SKILL.md) | Static audit against Anthropic's 6 prompt-cache rules — dynamic content above breakpoint, prefix mutation by Stop-hooks, model switching, breakpoint sizing — with report-only `suggested_action` hints. Lineage: ussumant/cache-audit. |
| [task-retrospective](task-retrospective/SKILL.md) | Task-end close of the learning loop: agent self-audit (with a rationalization catalog) + show-evidence-first user check (review card, closed verbs) + ≤3 gated lessons routed to the NARROWEST home; a REPEATED failure escalates to a mechanical `compliance-canary` drift probe, not more prose. `tools/audit_lessons.py` scans `wiki/log.md`; `scripts/mine_transcripts.py` can surface advisory candidate lessons without auto-writing memory. |
| [brainer-audit](brainer-audit/SKILL.md) | Report-only Brainer skill-use audit mode: inspect normalized events for missed skill triggers, unverified completion claims, write-gate bypasses, task-retrospective boundary violations, dropped requirements, and output-filter opportunities. Claude/Codex hooks are opt-in and marker-gated; Antigravity uses lower-fidelity sidecar snapshots. Proposes Brainer improvements but does not apply them. |
| [loop-engineering](loop-engineering/SKILL.md) | Design the verifier, not the prompt. Chooses the loop SHAPE (open/closed · inner/outer · single/fleet), pre-flights the harness underneath it (context/tools/permissions/hooks/subagents/skills/memory), adds a loop memory contract (`anchor_files` / `state_store` / `recall` / `writeback` / `state_concurrency`), and wires a generator to a SEPARATE verifier — the net-new layer no other skill provides. Ships `loop_lint.py`: a static gate that refuses a loop spec with no gate / no stop+budget / generator==verifier (self-grading; also catches same-actor-different-verb, human-approval gates, missing long-loop memory, and fleet state without concurrency), plus `loop_run_monitor.py`: a runtime trace gate for stuck/costly loops. Delegates the verify reflex→`verify-before-completion`, the learning loop→`task-retrospective`, the closed-loop plan→`plan-first-execute`, restraint→`lean-execution`. **Default-installed** (v1.11; previously opt-in pending N≥50 — promoted on user request, its loop gates are load-bearing CI value). Lineage: the "design the verifier" generator-verifier framing (ReAct/Reflexion) + pattern sources HarnessCode (yzddp) & autonomy-loop (inferencegod). |
| [eval-gate](eval-gate/SKILL.md) | LLM-as-judge quality gate for AI output: score a draft / post / answer / agent reply against a written rubric before it ships — returns 0–5 + reason, exit code gates, every caught failure becomes a permanent case. The output-side complement to `loop-engineering` (which designs the loop's verifier) and `verify-before-completion` (which runs deterministic checks); eval-gate is the *judgment* check where "good enough" has no test. **Default-installed** (v1.11; previously opt-in, 79% judge–human agreement with N≥50 validation pending — promoted on user request). |
| [requirements-ledger](requirements-ledger/SKILL.md) | Nothing the user said gets dropped. Decomposes every user message into ATOMIC items (asks / questions / constraints / conjuncts / implicit asks) into a USER-VISIBLE markdown ledger (`.brainer/ledger/<sid>.md`) as the hard source of truth; mirrors open items into the native task list on Claude Code; reconciles every item and ASKS before closing (never self-closes). Enforced mechanically by `compliance-canary`: the `ledger_not_materialized` probe + the `completion_without_closure` gate + the request-ledger cross-check (coarse hidden capture audits the visible atomic file). **Default-installed.** |
| [baci-template-fit-repair](baci-template-fit-repair/SKILL.md) | Use when working on tasks/baci-door, Baci door SVG template-fit, hex holes, hole-section scars, or image-generation repairs that must preserve a Screenery door template while fixing local cutout artifacts. |
| [reference-style-packet](reference-style-packet/SKILL.md) | Use when reference images must be turned into a visual style packet for image-generation agents, especially when previous outputs matched geometry but missed the actual art style. |
| [result-vision-judge](result-vision-judge/SKILL.md) | Use whenever judging/reviewing a generated illustration against a geometry template — by YOU or a sub-agent. Judge on BOTH vision (look at the candidate WITH the SVG-geometry overlay drawn on it) AND the geometry calculation (region-IoU / white-IoU). Never score from the metric alone or the raw image alone. Writes a judge.json verdict into the results library. |
| [skyline-template-illustration](skyline-template-illustration/SKILL.md) | Use when generating Screenery skyline or city-scape collections for the three-panel skyline template, including landmark allocation, saloon-door arch planning, run-through elements, top-contour adaptation, and vision review. |
| [svg-geometry-style-illustration](svg-geometry-style-illustration/SKILL.md) | Use when an agent must produce an SVG-template-constrained illustration that both fits exact contour/cutout geometry and adapts to the actual attached reference image style. Orchestrates geometry agents, style-packet/style-imagegen agents, whole-panel redraw, and review judges. |
| [svg-template-illustration](svg-template-illustration/SKILL.md) | Use when a user gives an SVG template, dieline, contour, cutout layout, or Screenery panel plus style/color references and wants generated artwork to fit exactly inside the SVG contour while avoiding internal cutouts and keep-clear areas. |
| [svg-template-review-judge](svg-template-review-judge/SKILL.md) | Use when judging, reviewing, scoring, or deciding whether to accept, patch, or restart SVG-template-constrained illustration candidates. |
| [svg-template-style-agent](svg-template-style-agent/SKILL.md) | Use for agents that generate or transform visual elements from a reference-style packet before SVG geometry placement. This is intentionally separate from geometry/template-fit agents. |

27 skills total in this project: shared Brainer framework skills plus repo-local additions. Shared Brainer skills are default-installed unless their frontmatter explicitly says `auto-install: false`; project-local skills follow their own frontmatter and installer rules.

## Most-recommended stack

The eight slots below cover the measured-win axes (output × routing × memory × retrieval × re-read × terminal × done-claims). Each skill earns its slot with a measured number; numbers compose across axes, diminish within. Per-axis sources in [`eval/FINDINGS.md`](../eval/FINDINGS.md).

| Slot | Skill | Headline measurement |
|---|---|---|
| Output style | [`caveman-ultra`](caveman-ultra/SKILL.md) + [`lean-execution`](lean-execution/SKILL.md) | **−87.7%** output (combo) |
| Routing | [`prompt-triage`](prompt-triage/SKILL.md) | −20.9% total, 100% accuracy |
| Memory across compaction | [`context-keeper`](context-keeper/SKILL.md) | 97.7% transcript compression |
| Retrieval — what/how/connected | external: [graphify](https://github.com/safishamsi/graphify) | **−93%** vs grep+read at parity evidence (`graphify explain`) |
| Retrieval — why/decision | [`wiki-memory`](wiki-memory/SKILL.md) | 100% evidence on project-history questions; combo with graphify: −87% vs grep at 100% evidence |
| Re-reads | [`semantic-diff`](semantic-diff/SKILL.md) | 95.5% reduction on unchanged re-reads |
| Terminal output | [`output-filter`](output-filter/SKILL.md) | −88.8% bytes, errors preserved |
| Claims of done | [`verify-before-completion`](verify-before-completion/SKILL.md) | −33.5% output, evidence-first |

Bootstrap once per project: `python3 skills/wiki-memory/tools/wiki.py init && graphify extract .` (graphify is auto-installed by `./install.sh`; pass `--no-graphify` to opt out).

## Prime directive

- **Caveman-Ultra by default** for emitted prose. Reasoning budget separate.
- **Plan-first** for non-trivial tasks.
- **Lean execution**: smallest reversible action.
- **Verify before claiming done**.
- **Retrieve before reasoning** about project/wiki facts — prefer `graphify explain` for code questions, `wiki-memory` for decision questions.
- **Use cheapest capable worker**; keep main context clean.

Stacking, anti-patterns, and workload guidance live in [`eval/FINDINGS.md`](../eval/FINDINGS.md) — not always-loaded; read once when installing or tuning the catalog.

## Install

```bash
./install.sh             # symlink to all four host loaders
./install.sh --host claude-code   # just one host
```

## Status

Each skill ships an `EVAL.md` with measured token/context deltas. Skills claiming >20% savings get N≥50 Kaggle-T4 verification before being promoted to default. The opt-in mechanism remains supported: a skill carrying `auto-install: false` in its SKILL.md frontmatter is symlinked and listed by `install.sh` but its `tools/install.sh` is not run, so it never auto-wires a hook or pulls a heavy dependency (no skill currently uses it — `skill-pulse` + `compliance-canary` graduated at v1.7, `loop-engineering` + `eval-gate` at v1.11). To **disable** a hook skill: per-skill installers append to `.claude/settings.json` and never delete, so remove the stale hook entry from `.claude/settings.json` by hand.
