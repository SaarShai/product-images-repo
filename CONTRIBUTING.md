# Contributing & Multi-Device Workflow

This repo is developed across more than one machine and person. To keep parallel
work from colliding, we use a **branch-per-workstream** model with **pull
requests into `main`**.

## Branch model

- **`main`** — integration baseline. Keep it green. Update it via PRs (or
  fast-forward merges of completed branches). Avoid long-lived work directly on
  `main`.
- **`skyline-skill`** — the `skyline-template-illustration` skill, its workflow
  build-out, and the Berlin live-example close-out. See
  [`tasks/skyline-skill-buildout/`](tasks/skyline-skill-buildout/) and
  [`tasks/berlin-skyline-live-example/berlin-handoff.md`](tasks/berlin-skyline-live-example/berlin-handoff.md).
- **`svg-geometry-*`** — SVG-geometry / template-cleanup work.
- One branch per workstream; name it for the work, not the person.

## Working on another device / as another collaborator

1. **Access:** the repo owner adds you as a collaborator on
   `github.com/SaarShai/product-images-repo` (private repo → Settings →
   Collaborators), or you fork it and PR from the fork.
2. `git clone https://github.com/SaarShai/product-images-repo.git && cd product-images-repo`
3. Run `./install.sh` once — it symlinks the central `skills/` into the
   per-machine host dirs (`.codex/skills`, `.gemini/skills`, `.claude/skills`,
   `.cursor/…`). Those host dirs are **gitignored**; never commit them.
4. Branch from the latest `main`:
   `git checkout main && git pull && git checkout -b <branch>`
5. Commit progress; `git push -u origin <branch>`.
6. Open a **Pull Request into `main`**. Keep each PR scoped to one workstream.

## Before you push

- `git pull --rebase origin <branch>` first — multiple devices push here, so
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
