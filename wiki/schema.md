# Brainer Wiki Schema

Purpose: a repo-local markdown LLM wiki for durable agent memory in the current target project.

## Layers
- `raw/`: immutable sources. Never rewrite.
- `concepts/`, `patterns/`, `projects/`, `people/`, `queries/`: synthesized target-project pages.
- `index.md`: compact catalog. Read first.
- `log.md`: append-only operation timeline.
- `L0_rules.md`: stable rules loaded at startup.
- `L1_index.md`: compact pointer index loaded at startup.
- `L2_facts/`: verified durable facts.
- `L3_sops/`: solved-task playbooks.
- `L4_archive/`: cold session archives.

## Frontmatter v2 for new pages
```yaml
---
schema_version: 2
title: Example
type: entity|summary|decision|source-summary|procedure|concept|pattern|project|query|fact|sop|raw|person|handoff
domain: framework|tools|patterns|experiments|project
tier: working|episodic|semantic|procedural
confidence: 0.0
created: YYYY-MM-DD
updated: YYYY-MM-DD
verified: YYYY-MM-DD
sources: []
resource: path/or/uri        # optional: the ONE live artifact this page documents
supersedes: []
superseded-by:
contradicts: []
tags: []
---
```

`contradicts:` is optional. Use `[[other-page]]` entries to flag two pages that make incompatible claims about the same subject. Lint surfaces these so an agent resolves them rather than retrieving both as truth.

`resource:` is optional and single-valued (OKF-aligned): the canonical URI/path of the one live artifact a page documents (a code file, a skill dir, a PR). Unlike the overloaded `sources:` provenance list it is existence-checkable — strict lint flags a `broken_resource`, and `audit-refs` resolves it. Use a `[[?stub]]` wikilink (leading `?`) to intentionally point at not-yet-written knowledge without tripping the broken-link error.

Legacy v1 pages remain readable. Strict lint emits migration warnings for v1 pages and enforces v2 fields on v2/template-generated pages.

## Workflows
- Ingest: source -> `raw/` note -> update synthesized pages -> backlinks -> `index.md`/`log.md`.
- Query: search -> timeline -> fetch only relevant pages -> cite paths -> file answer in `queries/` when it will be reused.
- Lint: stale claims, orphan pages, broken links, contradictions, supersession candidates.
- Crystallize: successful verified work -> `L3_sops/` and durable lessons.

## Imported Wiki Completeness
- Imported projects must be self-contained in this working folder.
- Treat any previous project wiki as source evidence only; adapt its useful information into repo-local pages.
- `index.md` and `L1_index.md` must point to local wiki pages and local commands only.
- After import, agents must not use home-directory rules, external wikis, or source-wiki paths for project facts.
- Validate imported projects with `./te wiki import-audit --manifest raw/<date>-import-manifest.md`.
