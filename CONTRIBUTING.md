# Contributing & Multi-Device Workflow

This repo is developed across more than one machine, signed in with the **same
GitHub + subscription account**. To keep parallel work from colliding, we use a
**branch-per-workstream** model and **always pull before pushing**. Pull requests
are optional (handy for review/history, not required since it's one account).

## Branch model

- **`main`** — integration baseline. Keep it green. Update it by merging
  completed branches (PR optional). Avoid long-lived work directly on `main`.
- **`skyline-skill`** — the `skyline-template-illustration` skill, its workflow
  build-out, and the Berlin live-example close-out. See
  [`tasks/skyline-skill-buildout/`](tasks/skyline-skill-buildout/) and
  [`tasks/berlin-skyline-live-example/berlin-handoff.md`](tasks/berlin-skyline-live-example/berlin-handoff.md).
- **`svg-geometry-*`** — SVG-geometry / template-cleanup work.
- One branch per workstream; name it for the work, not the person.

## Working on another device

Same account, second machine — **no collaborator setup needed**; you have full
push access.

1. `git clone https://github.com/SaarShai/product-images-repo.git && cd product-images-repo`
2. Run `./install.sh` once — it symlinks the central `skills/` into the
   per-machine host dirs (`.codex/skills`, `.gemini/skills`, `.claude/skills`,
   `.cursor/…`). Those host dirs are **gitignored**; never commit them.
3. Sign in to the tools you'll use: GitHub (same account), and for image
   generation the Codex (ChatGPT) and Antigravity (Google) subscriptions — see
   [`docs/image-generation.md`](docs/image-generation.md). One account means one
   **shared usage quota** across devices.
4. Branch per workstream from the latest `main`:
   `git checkout main && git pull && git checkout -b <branch>`.
5. Commit and `git push -u origin <branch>`. Open a PR into `main` only if you
   want review/history — otherwise merge when the workstream is done.

## Before you push

- `git pull --rebase` first — the other device pushes here too (same account), so
  avoid non-fast-forward rejects.
- Don't force-push shared branches.

## Generated images & large files

- Curated task artifacts (input refs, review overlays, accepted candidates) **are
  committed** — they're the evidence trail for each task.
- Throwaway generations under `tasks/*/outputs/generated/` are **gitignored**
  (except `.gitkeep`). Promote a keeper by moving it into `refs/` or
  `outputs/reviews/`.

## Image generation (subscription-only)

Skyline image generation uses **subscription routes only** — OpenAI via the
Codex CLI (priority) and Nano Banana via `agy` (testing). No API-key path. See
the skill's Generation Tools section and
[`tasks/skyline-skill-buildout/PROPOSAL.md`](tasks/skyline-skill-buildout/PROPOSAL.md).
