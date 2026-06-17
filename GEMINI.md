# Brainer

Skills catalog: see [`skills/SKILLS_INDEX.md`](skills/SKILLS_INDEX.md).

Each skill loads on its own trigger; full bodies are not in the boot context. Run `./install.sh` to wire skills into the current host.

<!-- brainer:skills-catalog:start -->
## Repo-local trigger skills (resident at boot)

Skill bodies under `skills/<name>/` lazy-load on trigger. The names + 1-line
descriptions below are kept in this resident doc so a freshly booted (or
post-compaction) agent still knows what's available — so a model-invokable
trigger (e.g. `wiki-memory` for "have we done X") is recognised on sight
rather than re-derived from scratch.

### Slash-triggered (user types literally; model cannot auto-invoke)

These are literal text tokens you recognise yourself — NOT host-registered
commands. When the user's message starts with one of these tokens, load
`skills/<name>/SKILL.md` and follow it yourself, even if this host has no such
command installed (e.g. Codex, Antigravity) or shows an "unknown command"
error. Treat the rest of the message as the task. Don't improvise a hand-rolled
equivalent:

- `/think` — How an agent should think and approach problems — first-principles, reduce/simplify before adding, research-and-borrow before building, experiment-and-falsify, never hallucinate or flatter

### Model-invokable (host fires on matching context)

You don't need to dispatch these manually — but knowing they exist helps you
notice when context matches one (e.g. `wiki-memory` for "have we done X").

- `baci-template-fit-repair` — Use when working on tasks/baci-door, Baci door SVG template-fit, hex holes, hole-section scars, or image-generation repairs that must preserve a Screenery door template while fixing local cutout artifacts.
- `cache-lint` — Audit a Claude Code project for prompt-cache hygiene against Anthropic's six cache rules (ordering, dynamic-content injection, tool stability, model switching, breakpoint sizing, fork safety)
- `caveman-ultra` — Terse output style
- `compliance-canary` — Use when a long session drifts — the single always-on drift watcher: one UserPromptSubmit hook combining a periodic skill-rule re-anchor (every N turns) with symptomatic per-skill drift probes (filler creep, word-count growth, unverified done-claims, looping tool errors, rule fade)
- `context-keeper` — PreCompact hook that extracts structured state (files, commands, errors, numbers, decisions, failures) from the transcript before compaction
- `eval-gate` — Score AI output against a written rubric before it ships — an LLM-as-judge quality gate for content output (drafts, posts, answers) and product output (an agent's reply, an extraction, a generated payload)
- `index-first` — Prefer pre-built indexes over chains of grep/read/scan
- `lean-execution` — Prune plans, process, context, and delegation to the smallest safe path
- `loop-engineering` — Use BEFORE building any multi-step agentic loop, generator→verifier pipeline, fan-out/fleet, or iterate-until-correct/retry loop
- `output-filter` — Use when terminal output is noisy with ANSI / progress bars / duplicate lines and you want to keep the agent's eyes on signal
- `plan-first-execute` — Plan before executing non-trivial tasks
- `prompt-triage` — Use on every UserPromptSubmit (pre-model hook) to classify the prompt and emit a directive telling the main model which subagent/model should handle it
- `reference-style-packet` — Use when reference images must be turned into a visual style packet for image-generation agents, especially when previous outputs matched geometry but missed the actual art style.
- `semantic-diff` — AST-node-level diff for file re-reads
- `skyline-template-illustration` — Use when generating Screenery skyline or city-scape collections for the three-panel skyline template, including landmark allocation, saloon-door arch planning, run-through elements, top-contour adaptation, and vision review.
- `svg-geometry-style-illustration` — Use when an agent must produce an SVG-template-constrained illustration that both fits exact contour/cutout geometry and adapts to the actual attached reference image style.
- `svg-template-illustration` — Use when a user gives an SVG template, dieline, contour, cutout layout, or Screenery panel plus style/color references and wants generated artwork to fit exactly inside the SVG contour while avoiding internal cutouts and keep-clear areas.
- `svg-template-review-judge` — Use when judging, reviewing, scoring, or deciding whether to accept, patch, or restart SVG-template-constrained illustration candidates.
- `svg-template-style-agent` — Use for agents that generate or transform visual elements from a reference-style packet before SVG geometry placement
- `task-retrospective` — Use at the end of any non-trivial task (after the work is verified, before the final report), when the user gives a corrective message mid-task, or when the user types /retro
- `verify-before-completion` — Use before claiming work is done, fixed, passing, committed, or ready
- `wiki-memory` — Repo-local markdown wiki with progressive retrieval (search → timeline → fetch) and gated writes (verified facts only)
- `wiki-refresh` — Reconcile wiki-memory pages against the current codebase — Keep / Update / Consolidate / Replace / Delete drifted ones
- `write-gate` — Decide whether a candidate fact deserves persistent memory

### Durable memory store (`wiki/`)

This repo carries a curated knowledge store at `wiki/` — the *why/decision/
failure-lesson* layer (rationale, trade-offs, incidents, procedures), distinct
from auto-extracted code structure. Relevant when the task references past work,
prior decisions, or "have we done X". Query it before re-deriving: read
`wiki/L1_index.md` first, then `python3 skills/wiki-memory/tools/wiki.py search "<q>"`
→ `timeline` → `fetch`. Maintained by `wiki-memory` (write) and `wiki-refresh`
(reconcile vs code).

_Auto-generated by `./install.sh` — do not hand-edit between sentinels._
<!-- brainer:skills-catalog:end -->
