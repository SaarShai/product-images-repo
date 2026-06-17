# Brainer Skills Installed

This repo uses a small selected subset of the local Brainer catalog from:

```text
/Users/za/Documents/Brainer
```

The full Brainer installer was intentionally not used. The repo instead links
only the skills that are useful for this image-generation workflow, avoiding the
larger hook-heavy/default catalog.

## Installed For Codex

Symlinks live under:

```text
.codex/skills/
```

These workspace-local symlinks are ignored by Git because they point to the
user's local Brainer checkout. Recreate them with the command below after a new
clone if this repo needs the same local agent skills.

## Installed For Gemini / Antigravity CLI

Workspace-scoped Gemini skill links live under:

```text
.gemini/skills/
```

Gemini discovery was verified with:

```bash
gemini skills list --all
```

## Selected Skills

- `plan-first-execute`: useful for multi-step asset/prompt/test workflows.
- `lean-execution`: keeps prompt iteration and repo maintenance scoped.
- `verify-before-completion`: requires fresh verification before done-claims.
- `wiki-memory`: creates a repo-local `wiki/` for durable task learnings.
- `write-gate`: helps decide what deserves persistent wiki/docs updates.
- `think`: manual-only planning aid for open-ended prompt/workflow design.
- `index-first`: useful once this repo has indexed docs or repeated lookups.
- `output-filter`: useful if batch generation or CLI logs become noisy.

## Project-Local Skills

- `.codex/skills/svg-geometry-style-illustration/SKILL.md`: orchestration skill
  for SVG template to geometry to reference-style-adapted illustration. Use it
  first when both exact contour/cutout fit and actual reference-image style
  adaptation matter.
- `.codex/skills/baci-template-fit-repair/SKILL.md`: a tracked custom skill
  created from the 2026-06-16 Baci-door sessions. Use it for `tasks/baci-door`
  template-fit repairs where exact SVG polygon cutouts and visual hole-section
  cleanup both matter.

External Brainer skill links under `.codex/skills/` remain ignored. The custom
Baci skill is intentionally unignored in `.gitignore` because it is repo-specific
project knowledge, not a symlink to the user's local Brainer checkout.

## Skills Not Installed

- `prompt-triage`, `skill-pulse`, `compliance-canary`, and `context-keeper`
  were skipped because they are hook-oriented and add hidden/background behavior.
- `semantic-diff` and full `graphify` setup were skipped because this repo is
  currently asset/prompt-heavy, not codebase-analysis-heavy.
- `cache-lint` can be added later if this repo grows more agent policy or hook
  configuration.

## Recreate Links

```bash
cd "/Users/za/Documents/product images repo"
mkdir -p .codex/skills .gemini/skills
for skill in plan-first-execute lean-execution verify-before-completion wiki-memory write-gate think index-first output-filter; do
  ln -sfn "/Users/za/Documents/Brainer/skills/$skill" ".codex/skills/$skill"
  gemini skills link --scope workspace --consent "/Users/za/Documents/Brainer/skills/$skill"
done
for skill in svg-geometry-style-illustration baci-template-fit-repair reference-style-packet svg-template-style-agent svg-template-illustration svg-template-review-judge skyline-template-illustration; do
  ln -sfn "../../skills/$skill" ".codex/skills/$skill"
  ln -sfn "../../skills/$skill" ".gemini/skills/$skill"
done
python3 .codex/skills/wiki-memory/tools/wiki.py init
```
