---
schema_version: 2
title: "Playwright CDP over real Chrome drives ChatGPT Plus web image gen (bot-block-proof)"
type: concept
domain: "image-gen"
tier: semantic
confidence: 0.7
trust: asserted
scope: this-repo
created: "2026-07-12"
updated: "2026-07-12"
verified: "2026-07-12"
sources:
  - "/Users/za/Downloads/Wanderland-Packet-2026-07-11/06-notes/chatgpt-playwright-pipeline.md"
  - "/Users/za/Downloads/Wanderland-Packet-2026-07-11/05-scripts-and-logs/work-log_readable.md"
supersedes: []
superseded-by:
contradicts: []
tags: [chatgpt-web, playwright, cdp, subscription-gen, browser-automation]
---

# Playwright CDP over real Chrome drives ChatGPT Plus web image gen (bot-block-proof)

## Summary

Trigger/symptom: need scripted/batch ChatGPT-web image generation (subscription, no API billing) — or Playwright-driven ChatGPT getting Cloudflare-blocked.

A PROVEN scriptable driver for ChatGPT Plus web image gen exists (Wanderland sibling project, verified 2026-07-04, ran a week of production gens): Playwright Python attached over CDP to the user's REAL Google Chrome — not Playwright's own Chromium, because Chromium-as-automation gets Cloudflare bot-blocked while real Chrome with a real human session does not (work-log ~862: "The detection problem is worst when Playwright launches its own browser").

Recipe: launch real Chrome with `--remote-debugging-port=9222` and a persistent `--user-data-dir` profile (login done by hand once, then sticks across sessions); `p.chromium.connect_over_cdp("http://localhost:9222")`; type into `div[contenteditable='true']` and press Enter; stop-button present = still generating (~20–60s); download by finding the largest `<img>` with src starting `https://chatgpt.com/backend-api/estuary/content?id=...` and fetching its bytes via in-page `fetch()` (auth cookies apply), base64 back to disk. Native output ~1024x1536; upscale is a separate step. Known flake: the CDP connection drops mid-session — restart Chrome cleanly and retry, don't debug the script. Helper-script pattern: pw_shot.py, pw_generate.py, pw_poll.py, pw_download.py.

**Status in THIS repo: reference, not a competing procedure.** The banked HARD rule stays subscription-image-gen-one-path (scripts/subgen.py is the single entry point) and chatgpt-app-browser-gen-protocol covers the manual browser path. This page exists so that when we want batch/scripted ChatGPT-web gens, we integrate CDP-over-real-Chrome into the existing single path instead of rediscovering the bot-detection failure mode.

## Evidence

- /Users/za/Downloads/Wanderland-Packet-2026-07-11/06-notes/chatgpt-playwright-pipeline.md (verified working setup, 2026-07-04).
- Work log ~860–1010: first successful gen loop ("It works! Full browser-automation loop succeeded").

## Related

- [[fixed-cut-composite-flexible-cut-art-derived]]
- [[semantic-color-region-map-locks-proportions]]

## Open Questions

- Whether estuary in-page fetch still works after ChatGPT UI changes; re-verify before integrating into subgen.py.
