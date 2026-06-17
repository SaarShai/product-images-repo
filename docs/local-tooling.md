# Local Tooling

## Python

The helper scripts currently use Python 3 and the standard library, except
`scripts/crop_nonwhite.py`, which uses Pillow. Pillow is already available in
this environment.

## Gemini CLI

Gemini CLI is installed at:

```text
/Users/za/.local/node/bin/gemini
```

Verified version during setup:

```text
0.46.0
```

Workspace Brainer skills are visible to Gemini with `gemini skills list --all`.

## Antigravity CLI

Antigravity Desktop is installed at:

```text
/Applications/Antigravity.app
```

The `agy` CLI was installed at:

```text
/Users/za/.local/bin/agy
```

Verified version during setup:

```text
1.0.8
```

Verified model access:

```bash
agy models
agy -p "Say hello in one short sentence and report the active model label if available."
```

The verified text-model list included Gemini 3.5 Flash, Gemini 3.1 Pro, Claude
Sonnet 4.6, Claude Opus 4.6, and GPT-OSS 120B variants. Nano Banana is **not** a
top-level model in `agy models`; image generation is a built-in agent **tool** —
drive it headlessly with `agy --print`. See
[`image-generation.md`](image-generation.md) for the exact image-generation
commands (Codex for OpenAI "image 2"; `agy` for Nano Banana), both
subscription-only / no API keys.

## SVG Preview

The authoritative template SVG is:

```text
assets/templates/two-panel-template.svg
```

The cropped preview for visual prompt/reference use is:

```text
assets/templates/previews/two-panel-template-cropped.png
```
