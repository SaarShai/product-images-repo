# Handoff packet — festive gingerbread sessions

**Purpose:** Self-contained evidence pack so another model can run `/task-retrospective` + `/learn-skill` (or decide drop/wiki/skill) **without searching transcripts, wiki, or the repo**.

**Created:** 2026-07-09  
**Repo:** `/Users/za/Documents/product images repo`  
**Status:** Evidence + existing memory only. **No new skills/wiki writes were performed in this packet-building pass.**

---

## Start here (read order)

| Order | File | Why |
|------:|------|-----|
| 0 | [ORIGINAL_ASK.md](ORIGINAL_ASK.md) | What the user wanted done with this evidence |
| 1 | [HOW_TO_USE.md](HOW_TO_USE.md) | How to navigate; what is / isn’t inlined |
| 2 | [CANDIDATE_LESSONS.md](CANDIDATE_LESSONS.md) | Pre-sieved lesson candidates (not yet gated/written) |
| 3 | [01-cursor-chimney-tree/](01-cursor-chimney-tree/) | Cursor session digest (“Chimney bricks + tree cutout” + later upscale) |
| 4 | [02-codex-gingerbread-style/](02-codex-gingerbread-style/) | Codex session digest (“Explore gingerbread style options”) |
| 5 | [03-existing-project-memory/](03-existing-project-memory/) | Already-persisted gates, retros, skill, diagnosis |
| 6 | [04-wiki-pages/](04-wiki-pages/) | Wiki pages + key prompts already in project memory |

---

## Session map

### A. Cursor — “Chimney bricks + tree cutout”

| Field | Value |
|-------|-------|
| Session id | `5b86a89c-f70b-4e8c-aade-33cf2cb73529` |
| Transcript | `~/.cursor/projects/Users-za-Documents-product-images-repo/agent-transcripts/5b86a89c-…/5b86a89c-….jsonl` |
| Span | 2026-07-08 ~13:10 → 2026-07-09 ~02:30 (UTC-7) |
| Digest | [01-cursor-chimney-tree/](01-cursor-chimney-tree/) |
| Evidence quality | High for user text / corrections; artifact bytes not re-verified |

**Phases (see TIMELINE.md):** icing trails → holly on edge-v4 → chimney bricks + tree → tree mask fix → upscale research → magenta 8× → detail C → candy-creative fail → artifact rebuild → downloads batch.

### B. Codex — “Explore gingerbread style options”

| Field | Value |
|-------|-------|
| Session id | `019f42e2-a53d-7b73-933d-eeab76bca988` |
| Rollout | `~/.codex/sessions/2026/07/08/rollout-2026-07-08T10-59-37-019f42e2-….jsonl` (~245 MB) |
| Confidence | **0.93** (Chronicle title + content match; see SESSION_ID.md) |
| Digest | [02-codex-gingerbread-style/](02-codex-gingerbread-style/) |
| Human prompts extracted | 23 |

**Core corrections:** no houses inside cutouts; procedural ≠ styled; edge-v4 = base; Styled V1 peppermint = foreground motif; AB5 geometry vs style; unmasked artwork needed.

---

## Folder index

```text
handoff-packet/
├── README.md                 ← you are here
├── ORIGINAL_ASK.md
├── HOW_TO_USE.md
├── CANDIDATE_LESSONS.md
├── MANIFEST.json
├── 01-cursor-chimney-tree/
│   ├── USER_MESSAGES.md      # U01… full user text
│   ├── CORRECTIONS.md        # approvals / rejections
│   ├── TIMELINE.md
│   ├── KEY_ARTIFACTS.md
│   ├── ASSISTANT_CLAIMS.md   # fal clarity params, methods
│   └── session-meta.json
├── 02-codex-gingerbread-style/
│   ├── SESSION_ID.md
│   ├── USER_MESSAGES.md
│   ├── CORRECTIONS.md
│   ├── TIMELINE.md
│   ├── KEY_ARTIFACTS.md
│   ├── METHODS_AND_FAILURES.md
│   └── session-meta.json
├── 03-existing-project-memory/
│   ├── INDEX.md
│   ├── CORRECTION-GATE.md
│   ├── RETROSPECTIVE-styled-oversight.md
│   ├── skill-styled-candidate-proof-gate-SKILL.md
│   ├── upscale-research-DIAGNOSIS.md
│   ├── ARTIFACT_TREE.md
│   ├── RELATED_SKILLS.md
│   └── WIKI_HITS.md
└── 04-wiki-pages/
    ├── INDEX.md
    ├── concepts-gingerbread-panel-cutouts-decoration-slots.md
    ├── concepts-illustrated-product-upscale-and-background-removal-workflow.md
    └── prompts/              # brick/tree + styled prompts + style-packet
```

---

## What is NOT in this packet

1. **Binary images** (PNG/JPG) — only absolute paths. Open paths on disk if visual review is required.
2. **Raw 245 MB Codex JSONL / full Cursor JSONL** — digests only (user messages + corrections + methods).
3. **Implemented durable writes** from the original ask — deferred to the receiving model.

---

## Quick facts the receiving model must not rediscover

1. Cutouts = **decoration slots**, not miniature house scenes → already in `CORRECTION-GATE.md` + wiki concept.
2. **Styled** requires reference-attached image generation → already `styled-candidate-proof-gate` (proposed) + retrospective.
3. Approved upscale path: **cream paper + fal clarity**; detail C = `1.5× / creat 0.5 / res 0.7` → `DIAGNOSIS.md`.
4. Candy-creative (`creat 0.65`) was user-loved once then **rejected** for magenta/neon artifacts → restart from clean sources, don’t heal bad outputs.
5. Tree cutout: user wanted **green tree + candy + icing border**, then asked to restore **original geometry-matched tree unmasked** (mask/crop was the defect).
6. Chimney: **biscuit brick pattern** in top-right cutouts (edge-v8 approved).
