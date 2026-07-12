# Brainer

Skills catalog: see [`skills/SKILLS_INDEX.md`](skills/SKILLS_INDEX.md).

Each skill loads on its own trigger; full bodies are not in the boot context. Run `./install.sh` to wire skills into the current host.

<!-- brainer:skills-catalog:start -->
## Repo-local trigger skills (resident at boot)

Skill bodies under `skills/<name>/` lazy-load on trigger; the 1-line
descriptions below stay resident so a freshly booted (or post-compaction)
agent still recognises a trigger on sight instead of re-deriving it.

### Slash-triggered (user types literally; model cannot auto-invoke)

Literal tokens you recognise yourself — NOT host-registered commands. If the
user's message starts with one, load `skills/<name>/SKILL.md` and follow it
yourself even if this host has no such command (e.g. Codex, Antigravity) or
shows "unknown command". Treat the rest of the message as the task; don't
improvise a hand-rolled equivalent:

- `/baton` — Drop/grab a verified session-handoff file — pass in-progress work to the next agent (future session, another window, codex) via .brainer/baton/
- `/brainer-audit` — Use when the user explicitly activates Brainer audit mode, asks to audit this session, audit Brainer use, or track Brainer skill usage
- `/styled-candidate-proof-gate` — Gate styled generated image claims
- `/task-retrospective` — Use only when the user explicitly arms task audit mode: /retro, asks for task-retrospective, says this task will repeat and should be learned from, or requests an after-the-fact task learning audit
- `/think` — How an agent should think and approach problems — first-principles, reduce/simplify before adding, research-and-borrow before building, experiment-and-falsify, never hallucinate or flatter
- `/transparent-product-image-gen` — Use when a product needs a NEW transparent-background (RGBA) illustration, an EXISTING illustration may be semantically regenerated with native alpha, or an existing raster must keep its exact pixels while its white/paper background is removed

### Model-invokable (host fires on matching context)

No manual dispatch needed — but knowing these exist helps you notice a
context match (e.g. `wiki-memory` for "have we done X").

- `baci-template-fit-repair` — Use when working on tasks/baci-door, Baci door SVG template-fit, hex holes, hole-section scars, or image-generation repairs that must preserve a Screenery door template while fixing local cutout artifacts.
- `cache-lint` — Audit a Claude Code project for prompt-cache hygiene against Anthropic's six cache rules (ordering, dynamic-content injection, tool stability, model switching, breakpoint sizing, fork safety), plus a rule-7 tool-surface audit (resident-but-unused MCP servers)
- `caveman-ultra` — Terse output style
- `compliance-canary` — Use when a long session drifts — the single always-on drift watcher: one UserPromptSubmit hook combining symptomatic per-skill drift probes (filler creep, verbosity growth, unverified done-claims, looping tool errors), a periodic skill-rule re-anchor, a request ledger that keeps every user request OPEN until completed or user-closed, and a correction ledger that keeps every user correction OPEN (LEARNING_CONTRACT §2) until it is banked or user-closed
- `context-keeper` — PreCompact hook that extracts structured state (files, commands, errors, numbers, decisions, failures) from the transcript before compaction, so the summarizer can't silently drop facts; a SessionEnd hook also archives the raw transcript to .brainer/sessions/raw/ (git-ignored)
- `element-edit` — Use when editing ONE element of a finished illustration while keeping the rest byte-identical — redraw / remove / restyle / reshape / move a single element inside finished watercolor+ink art (or any fixed image)
- `eval-gate` — Score AI output against a written rubric before it ships — an LLM-as-judge quality gate for content output (drafts, posts, answers) and product output (an agent's reply, an extraction, a generated payload)
- `fable-mode` — Use PROACTIVELY the moment you notice a task has many layers - multiple dependent steps, unknowns that could change the approach, debugging where the first theory might be wrong, or anything that needs verification before handoff
- `impact-of-change` — Use before committing or claiming work done to map a code edit to its blast radius — which symbols depend on the changed ones, plus a LOW/MEDIUM/HIGH/UNKNOWN risk score
- `index-first` — Prefer pre-built indexes over chains of grep/read/scan
- `lean-execution` — Prune plans, process, context, and delegation to the smallest safe path
- `learn-skill` — Turn a pointed-at source (local dir, doc URL, a workflow you just did, or pasted notes) into a reusable Brainer skill
- `loop-engineering` — Use BEFORE building any multi-step agentic loop, generator→verifier pipeline, fan-out/fleet, or iterate-until-correct/retry loop — including any unattended / scheduled / nightly process that regenerates artifacts and retries until a check passes, and any build-and-verify or generate-and-grade pipeline
- `moodboard-cobuild` — Co-build a collection's STYLE BIBLE with the user: harvest exemplars from existing assets, compose an axis-by-axis choice board (medium/palette/illustration-style required, plus COMPLETE-BUILDING and GEOMETRY-EMBRACE), run forced-choice verdicts, lock bible v1 with a style handle (medium_ref/palette_ref/style_ref), then validate uncertain axes with one cheap probe-tile round
- `output-filter` — Use when terminal output is noisy with ANSI / progress bars / duplicate lines and you want to keep the agent's eyes on signal
- `plan-first-execute` — Plan before executing non-trivial or spec-worthy tasks
- `prompt-triage` — Use on every UserPromptSubmit (pre-model hook) to classify the prompt and emit a directive telling the main model which subagent/model should handle it
- `propagate` — Use when the user asks to propagate, sync, roll out, or push Brainer skill changes to the sibling/consumer repos (screenery-lean, product images repo, farey-hecke, PROMPTER, …) after work in the canonical Brainer repo, or asks to harvest lessons, reap lessons, or bring learnings back from a sibling
- `reference-style-packet` — Use when reference images must be turned into a visual style packet for image-generation agents, especially when previous outputs matched geometry but missed the actual art style.
- `region-map-guide` — Use when a generation must place several distinct elements in specific zones of a fixed die-cut/template panel, when per-element proportions keep coming back wrong (repeated regen/registration mismatch, art stretching, elements drifting), or when the user gives zone requirements ("door here, lamps there, nothing near the knobs") — build a semantic color-region map PNG (each flat color = one element's placement, avoid-zones as prohibitions) plus its auto-matched color→meaning legend prompt, feed map as image-1 + style ref + legend to the generator
- `requirements-ledger` — Use whenever the user states anything carrying intent — an ask, a question, a constraint, a preference, a compound "do X, Y, and Z" (one row per conjunct), or an implicit ask embedded in prose
- `result-vision-judge` — Use whenever judging/reviewing a generated illustration against a geometry template — by YOU or a sub-agent
- `security-oversight` — Use before committing or claiming work done to triage a code edit for INTRODUCED security risk — leaked secrets, dangerous sinks, untrusted deps, risky auth logic
- `semantic-diff` — AST-node-level diff for file re-reads
- `skyline-template-illustration` — Use when generating Screenery skyline or city-scape collections for the three-panel skyline template, including landmark allocation, saloon-door arch planning, run-through elements, top-contour adaptation, and vision review.
- `standing-orders` — Auto-arm standing directives on matching prompts — ORCH tier (goal, lanes, cheapest delegation, other-vendor advisor, end-to-end) on decomposable work; DEEP tier (blindspot pass, lesson capture) on high-level tasks
- `style-prompt-engineer` — Turn a requested art style (named by the user, or embodied in a reference image) into the best generation prompt sections + the right reference-image inputs
- `svg-geometry-style-illustration` — Use when an agent must produce an SVG-template-constrained illustration that both fits exact contour/cutout geometry and adapts to the actual attached reference image style
- `svg-template-illustration` — Use when a user gives an SVG template, dieline, contour, cutout layout, or Screenery panel plus style/color references and wants generated artwork to fit exactly inside the SVG contour while avoiding internal cutouts and keep-clear areas.
- `svg-template-review-judge` — Use when judging, reviewing, scoring, or deciding whether to accept, patch, or restart SVG-template-constrained illustration candidates.
- `svg-template-style-agent` — Use for agents that generate or transform visual elements from a reference-style packet before SVG geometry placement
- `team-lead` — Use when the user says lead, orchestrate, use your team, use builders — or marks a task important/challenging while the session model is ANY top-tier frontier model (Fable-class, Opus-class, GPT-5.x/Codex, or peer)
- `verify-before-completion` — Use before claiming work is done, fixed, passing, committed, or ready
- `wiki-memory` — Repo-local markdown wiki with progressive retrieval (search → timeline → fetch) and gated writes (verified facts only)
- `wiki-refresh` — Reconcile wiki-memory pages against the current codebase — Keep / Update / Consolidate / Replace / Delete drifted ones
- `write-gate` — Decide whether a candidate fact deserves persistent memory

### Durable memory store (`wiki/`)

Curated why/decision/failure-lesson layer at `wiki/`. Query before re-deriving
(e.g. "have we done X"): read `wiki/L1_index.md`, then
`python3 skills/wiki-memory/tools/wiki.py search "<q>"` → `timeline` → `fetch`.
Maintained by `wiki-memory` (write) / `wiki-refresh` (reconcile vs code).

### Code-craft directives (resident at boot)

Always-on rules for writing code — they apply on every coding turn, not only when
a skill happens to trigger:

- **Surgical diffs.** Smallest reversible change; touch only what the ask needs;
  match local style; never reformat code you didn't change. Justify every changed
  line by the task — revert "while I was in there" edits. (`lean-execution` covers
  this when invoked; this is the always-on copy. The `whitespace_only_edit` +
  `dependency-manifest-changed` `compliance-canary` probes enforce it mechanically.)
- **Failure-mode interrupt.** If mid-task you slide into scope-creep (Kitchen
  Sink), premature abstraction (abstract only on the 3rd repeat — rule of three),
  happy-path-only (error path ignored), or a fix cascading across files (Runaway
  Refactor) — STOP, restate the goal, narrow scope.

### Host capability matrix (honest degradation)

Host capability & degradation matrix (claude/codex/gemini): see
`docs/HOST_CAPABILITY_MATRIX.md` — the RULE still binds on a host lacking a
hook; enforce it manually.

_Auto-generated by `./install.sh` — do not hand-edit between sentinels._
<!-- brainer:skills-catalog:end -->

## Project rules (hand-maintained)

- **Image output location.** ALWAYS save/copy result images to an `Images/` subfolder
  inside the folder the user points to — typically the production folder where the `.ai`
  and/or `.svg` template lives (e.g. `…/production files/<product>/Images/`), organized as
  `Images/finals/` + `Images/candidates/`. The repo `tasks/<task>/outputs/` is the working
  copy only and need not hold images unless one is used as a doc example. (user rule, 2026-06-24)
