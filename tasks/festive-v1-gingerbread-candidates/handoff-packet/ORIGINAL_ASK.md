# Original ask (verbatim intent)

The user asked (2026-07-09) to:

1. Review **two recent sessions**:
   - **"Chimney bricks + tree cutout"** (Cursor)
   - **"Explore gingerbread style options"** (Codex)
2. Gather logs, results, user feedback, etc., and **learn as much as possible**.
3. **Implement learning** in this project/repo (create or update skills).
4. Use `/task-retrospective`, `/think`, `/learn-skill` as relevant.
5. Write goals and spawn parallel agents; be economical; use weaker models for extraction; prefer GPT-5.5 via Codex plugin for cheaper work.

## Follow-up redirect (this packet)

Before that learning was implemented, the user redirected:

> Continue but **instead of actually performing the task**, gather all information/files/references into a **packet** another model can use so it **doesn't need to search or fetch anything**.

This directory is that packet.

## What the receiving model should do

1. Read `README.md` → `HOW_TO_USE.md` → `CANDIDATE_LESSONS.md`.
2. Run `/task-retrospective` (after-the-fact) using digests in `01-` and `02-` as evidence.
3. Dedup against `03-existing-project-memory/` and `04-wiki-pages/` before writing.
4. Route each accepted lesson: drop / wiki / skill (`/learn`) / always-on rule.
5. Run write-gate + route-probe; read back before claiming persistence.
6. Deliver the task-retrospective report format from the skill.
