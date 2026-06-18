# Brainer Skills

Lean skills for AI coding agents (Claude Code · Codex · Cursor · Gemini · Copilot) across four pillars: **(1)** token-use optimization, **(2)** context-window optimization & management, **(3)** LLM wiki-memory framework, **(4)** self-improvement & learning.

This replaces the old `start.md` boot doc. Each skill is a self-contained folder under `skills/<name>/`. Skill descriptions are the only thing always resident in the agent's context; full bodies load on trigger.

For measured per-skill deltas and the live A/B table see [`eval/FINDINGS.md`](../eval/FINDINGS.md); each skill also ships its own `EVAL.md`.

## Catalog

| Skill | One-line |
|---|---|
| [caveman-ultra](caveman-ultra/SKILL.md) | Terse output style. Use at session start, or whenever the user asks for compact, short, terse, or "caveman" responses. Drops filler, pleasantries, hedging, soft closings. Keeps code blocks, paths, numbers, math, errors verbatim. Affects emitted prose only; reasoning budget unchanged. |
| [plan-first-execute](plan-first-execute/SKILL.md) | Plan before executing non-trivial tasks. Trigger when the task has more than 3 steps, unclear scope, multiple files, real risk, or architecture decisions. Inspect reality first, draft a phased plan with verification gates, simplify, then execute. |
| [think](think/SKILL.md) | How an agent should think and approach problems — first-principles, reduce/simplify before adding, research-and-borrow before building, experiment-and-falsify, never hallucinate or flatter. Manual-only: invoke deliberately with `/think` when planning an approach, ideating, stuck, choosing build-vs-research, or tackling a non-trivial / open-ended problem. Does not auto-fire. **Slash-only** (`/think`). |
| [lean-execution](lean-execution/SKILL.md) | Prune plans, process, context, and delegation to the smallest safe path. Trigger when the user asks to simplify, be lean, reduce process, remove steps, or cut rot; or when a plan has more steps than the task seems to need. |
| [verify-before-completion](verify-before-completion/SKILL.md) | Use before claiming work is done, fixed, passing, committed, or ready. Evidence before claims. Run the verification fresh; report exact command + output + remaining risk. For high-stakes or hard-to-reverse results, escalate to a separate cross-vendor verifier before shipping. |
| [wiki-memory](wiki-memory/SKILL.md) | Repo-local markdown wiki with progressive retrieval (search → timeline → fetch) and gated writes (verified facts only). Use when the task references past work, decisions, memory, "have we done X", project facts, or when you need to record a durable finding. Tiered: L0 rules · L1 pointer index · L2 facts · L3 SOPs · L4 archive. Replaces note-app sprawl; no global agent config. |
| [prompt-triage](prompt-triage/SKILL.md) | Use on every UserPromptSubmit (pre-model hook) to classify the prompt and emit a directive telling the main model which subagent/model should handle it. Regex fast-path then local-Ollama fallback. Goal: avoid spending opus tokens on tasks solvable by haiku/sonnet/local. Override per prompt by typing NO TRIAGE. |
| [context-keeper](context-keeper/SKILL.md) | PreCompact hook that extracts structured state (files, commands, errors, numbers, decisions, failures) from the transcript before compaction. Preserves grep-able recovery memory so the summarizer can't silently drop facts. Use when the host supports project-local PreCompact hooks. |
| [semantic-diff](semantic-diff/SKILL.md) | AST-node-level diff for file re-reads. Use whenever you'd re-read a file you've read before — the skill returns only the changed AST nodes, not the full file. 95.5% token savings measured on argparse.py (2575 lines, 2 method edits). Default runtime is a Bash CLI (works on every host); an optional MCP server adds a native read_file_smart tool. Supports Python, JavaScript, TypeScript, Rust. |
| [index-first](index-first/SKILL.md) | Prefer pre-built indexes over chains of grep/read/scan. Use when about to look up symbols, callers, references, routes, or "where is X used / what depends on Y" — query the index (codegraph, ctags, wiki search) before scanning raw text. Batch related lookups into one capped call. Applies to code and any indexed corpus (wiki, tickets, docs). |
| [output-filter](output-filter/SKILL.md) | Use when terminal output is noisy with ANSI / progress bars / duplicate lines and you want to keep the agent's eyes on signal. Strips ANSI, collapses adjacent duplicates, archives raw output locally for recovery, exposes stats and rewind. Wire as a shell pipe or PostToolUse hook on Bash. Preserves error lines and exact failure evidence verbatim. |
| [compliance-canary](compliance-canary/SKILL.md) | Use when a long session drifts — the single always-on drift watcher: one UserPromptSubmit hook combining a periodic skill-rule re-anchor (every N turns), symptomatic per-skill drift probes (filler creep, word-count growth, unverified done-claims, self-closing without asking, looping tool errors, rule fade), and a request ledger that keeps every user request OPEN until completed or the user closes it (so nothing the user asked for is silently dropped). Absorbs the former skill-pulse; the re-anchor yields to a fired probe so the two never double-nag. Tune/disable via COMPLIANCE_CANARY_* env vars (SKILL_PULSE_* honored as aliases). |
| [write-gate](write-gate/SKILL.md) | Decide whether a candidate fact deserves persistent memory. Use before writing to wiki-memory, CLAUDE.md, AGENTS.md, or any cross-session store. Scores content on signal (decisions / errors / architecture / code) and rejects reasonless decisions (must embed because… / so that… / to avoid…). Prevents memory pollution at source. |
| [wiki-refresh](wiki-refresh/SKILL.md) | Reconcile wiki-memory pages against the current codebase — Keep / Update / Consolidate / Replace / Delete drifted ones. Use on "refresh the wiki", "audit wiki against code", "are these facts still true", "clean up stale pages", or after a refactor/rename/migration that invalidated cited paths. Ground-truth reconcile; emits typed contradicts: edges. |
| [cache-lint](cache-lint/SKILL.md) | Audit a Claude Code project for prompt-cache hygiene against Anthropic's six cache rules (ordering, dynamic-content injection, tool stability, model switching, breakpoint sizing, fork safety). Use before shipping new hooks or skills, after a costly session, or when cache-bust costs spike. Produces a typed report; exit codes signal pass / warn / fail. |
| [task-retrospective](task-retrospective/SKILL.md) | Use at the end of any non-trivial task (after the work is verified, before the final report); ALSO fire mid-task the moment the user corrects you — says you were wrong, that you skipped a step or claimed something without actually running it, calls out a mistake you have made before ("again", "second time", "you keep", "I told you", "stop doing that"), or pushes back on your approach; or when the user types /retro. Runs a fixed agent self-audit (incl. 5-whys root-cause), shows the user the evidence, asks at most 3 closed feedback questions, then routes each banked lesson through write-gate to the NARROWEST home — escalating a REPEATED failure to a mechanical gate (a compliance-canary drift probe) instead of more prose. For high-stakes or contested results it dispatches a separate, preferably cross-vendor, verifier agent (Claude ↔ GPT-via-Codex ↔ Gemini) for independent review + root-cause. |
| [loop-engineering](loop-engineering/SKILL.md) | Use BEFORE building any multi-step agentic loop, generator→verifier pipeline, fan-out/fleet, or iterate-until-correct/retry loop — INCLUDING an automated / unattended / scheduled / nightly process that regenerates, revises, or rebuilds artifacts and keeps retrying each until it passes a check, any self-correcting or "keep going until it's good enough" automation, and any build-and-verify or generate-and-grade pipeline. If the task is "set up something that runs repeatedly and fixes its own output", this skill applies. Picks the loop shape (open/closed · inner/outer · single/fleet), pairs a generator with a SEPARATE verifier, and forces a concrete gate + stop + budget cap up front. Ships loop_lint.py to refuse no-gate / self-grading / unbounded specs. Override with ONE SHOT. |
| [eval-gate](eval-gate/SKILL.md) | Score AI output against a written rubric before it ships — an LLM-as-judge quality gate for content output (drafts, posts, answers) and product output (an agent's reply, an extraction, a generated payload). Use when asked "is this good enough", "score/grade this", "would this pass", to gate output on quality, to regression-check a prompt/model/pipeline change, or to turn a flagged bad output into a permanent test case. Returns 0-5 + reason; exit code gates. Opt-in until N≥50 verified. |
| [requirements-ledger](requirements-ledger/SKILL.md) | Use whenever the user states anything carrying intent — an ask, a question, a constraint, a preference, a compound "do X, Y, and Z" (one row per conjunct), or an implicit ask embedded in prose. Maintains a USER-VISIBLE markdown ledger as the hard source of truth so nothing the user said is ever silently dropped; mirrors open items into the native task list on Claude Code; reconciles every item and ASKS before closing. Fires on every substantive user turn and before any completion claim. |
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
