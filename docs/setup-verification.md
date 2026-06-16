# Setup Verification

Run:

```bash
python3 scripts/verify_setup.py
```

Expected checks:

- Git repo exists.
- Core docs and helper scripts exist.
- Current castle-panel status and system-plan docs exist.
- Reference image assets exist.
- Authoritative SVG template exists and parses.
- Cropped SVG preview exists.
- Selected Brainer skills are linked for Codex.
- Selected Brainer skills are linked for Gemini.
- Repo-local wiki files exist.
- `gemini` and `agy` CLIs are present.
- The template-fit scorer command is available.

Generated image PNGs under `tasks/*/outputs/generated/` are ignored by Git by
default. Keep curated review notes and metadata in `tasks/*/outputs/reviews/`.
