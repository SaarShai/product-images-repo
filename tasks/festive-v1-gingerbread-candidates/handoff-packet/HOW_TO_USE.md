# How to use this packet

## Navigation rules

1. **Do not re-search** Cursor transcripts, Codex rollouts, or wiki unless a path in this packet is missing on disk.
2. Treat `01-*/USER_MESSAGES.md` and `02-*/USER_MESSAGES.md` as the authoritative user-text corpus.
3. Treat `*/CORRECTIONS.md` as the authoritative approval/rejection ledger.
4. Treat `03-existing-project-memory/` as **already banked** project memory — update, don’t duplicate.
5. Treat `04-wiki-pages/` as inlined wiki + key prompts — fetch only if you need pages not listed in `04-wiki-pages/INDEX.md`.

## Recommended workflow for the receiving model

```text
1. Read ORIGINAL_ASK.md + CANDIDATE_LESSONS.md
2. Skim both CORRECTIONS.md files (01 + 02)
3. Skim METHODS_AND_FAILURES.md (02) + ASSISTANT_CLAIMS.md (01) + DIAGNOSIS.md (03)
4. Dedup: for each candidate lesson, check CORRECTION-GATE, styled-candidate-proof-gate, wiki concepts
5. Arm task-retrospective recorder (optional) and decide destinations
6. For procedure-shaped lessons: route-probe → /learn if skill; else wiki
7. write-gate → write → read-back → report
```

## Absolute paths you may need (not copied as binaries)

### Task root
`/Users/za/Documents/product images repo/tasks/festive-v1-gingerbread-candidates/`

### Production festive images (Google Drive)
`/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/festive/images/`

### NEW Festive candidates / gingerboy
`/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/new cutting files/NEW Festive/images/`

### Related task folders
- `tasks/festive-edge-v4-peppermint-overlay/`
- `tasks/festive-magenta-m5-upscale/`
- `tasks/festive-upscale-blur-research/`
- `skills/styled-candidate-proof-gate/SKILL.md`

### Image generation route (repo)
- `docs/image-generation.md`
- `scripts/subgen.py`
- `scripts/reupscale.py`

## Evidence quality notes

| Source | Quality | Caveat |
|--------|---------|--------|
| Cursor user messages | High | Subagent boilerplate stripped |
| Codex user messages | High | Streamed from 245MB; AGENTS injections excluded |
| Assistant method claims | Medium–High | Params from transcript claims; cross-check DIAGNOSIS.md |
| Artifact existence | Medium | Digests cite paths; bytes not re-hashed in packet build |
| Session title match (Codex) | High (0.93) | Title from Chronicle + content, not sqlite title index |

## Skills the receiving model should load (bodies not all inlined)

Load from repo when writing:

- `skills/task-retrospective/SKILL.md`
- `skills/learn-skill/SKILL.md`
- `skills/write-gate/SKILL.md`
- `skills/wiki-memory/SKILL.md`
- `skills/think/SKILL.md` (optional framing)
- `skills/styled-candidate-proof-gate/SKILL.md` (already copied in 03/)
