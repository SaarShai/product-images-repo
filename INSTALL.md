# Installation Guide

This document guides new installers through setting up the product images repository on their machine.

## Prerequisites

- **macOS or Linux** (tested on macOS 12+)
- **Python 3.10 or later** (check with `python3 --version`)
- **git** (for cloning the repository)

The repository has Python dependencies listed in `requirements.txt`:
- Pillow (image processing)
- numpy (numerical operations)
- opencv-python (computer vision tasks)

The `install.sh` script will build isolated Python virtual environments for different workloads (image generation, background removal, OCR, etc.) and install these dependencies into them.

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/SaarShai/product-images-repo.git
cd product-images-repo
./install.sh
```

The `install.sh` script:
- Creates multiple isolated Python venvs (`.venv-gen`, `.venv-bg`, `.venv-ocr`, `.venv-metric`, etc.)
- Installs `requirements.txt` into each venv
- Sets up helper scripts and symbolic links

### 2. Verify Setup

```bash
python3 scripts/verify_setup.py
```

This script checks:
- Python version ≥ 3.10
- Required Python packages installed
- Virtual environment venvs are functional
- Optional: presence of API keys (see below)

## Configuration: API Keys & Optional Services

The repository can function in degraded mode if API keys are not configured. Each script documents which keys it requires.

### a. fal.ai (FAL_KEY) — Optional

Used by image generation and manipulation scripts (`falgen.py`, `automask.py`, `qwen_edit.py`, `reupscale.py`, `falbatch.py`).

**Setup:**
```bash
# Option 1: Set environment variable
export FAL_KEY="your-fal-api-key"

# Option 2: Store in .secrets/fal.env (mode 600)
echo "FAL_KEY=your-fal-api-key" > .secrets/fal.env
chmod 600 .secrets/fal.env
```

The `.secrets/` directory is git-ignored; never commit keys there.

### b. OpenAI (OPENAI_API_KEY) — Optional

Used by OpenAI-based scripts (`judge.py`, `openai_edit.py`).

**Setup:**
```bash
# Option 1: Set environment variable
export OPENAI_API_KEY="your-openai-api-key"

# Option 2: Store in .secrets/openai.env (mode 600)
echo "OPENAI_API_KEY=your-openai-api-key" > .secrets/openai.env
chmod 600 .secrets/openai.env
```

### c. z.ai / GLM (ZAI_API_KEY) — Optional

Used by GLM-5.2 reasoning tasks delegated to z.ai.

**Setup:**
Store in `~/.config/zai/key` (mode 600, user home directory):
```bash
mkdir -p ~/.config/zai
echo "your-zai-api-key" > ~/.config/zai/key
chmod 600 ~/.config/zai/key
```

### d. Gemini / Antigravity — Optional

Interactive sign-in (browser-based). Credentials stored by the system; no manual setup required. Run any Gemini-dependent script and follow prompts if needed.

### e. Brainer Repo (BRAINER_REPO) — Optional

For transcript mining (`scripts/mine_transcripts.py`), set the path to the canonical Brainer repository:

```bash
export BRAINER_REPO="/path/to/Brainer"
```

Default: `~/Documents/Brainer`. Only required if you have the sibling Brainer repository at a non-standard location.

## Verification Output

After running `python3 scripts/verify_setup.py`, expect output like:

```
✓ Python 3.10+
✓ Pillow installed
✓ numpy installed
✓ opencv-python installed
✓ .venv-gen active
✓ .venv-bg active
...
⚠ FAL_KEY not set (falgen, automask, etc. will fail; set env or .secrets/fal.env)
⚠ OPENAI_API_KEY not set (judge, openai_edit will fail; set env or .secrets/openai.env)
✓ z.ai key found (~/.config/zai/key)
```

Scripts document their dependencies in their `--help` output and file headers.

## Never Commit

Always use `.gitignore` to protect secrets:
- `.secrets/` (API keys in files)
- `HANDOFF.md` (session handoff state)
- Any file containing credentials or sensitive data

These are already in `.gitignore`; verify with `git status`.

## Troubleshooting

- **"Python 3.10 not found"**: Install Python 3.10+ via brew (`brew install python@3.10`) or conda.
- **"No module named PIL"**: Run `./install.sh` again to rebuild venvs.
- **"FAL_KEY: no such environment variable"**: Set it (see above) or run a script that doesn't require it.
- **venv activation fails**: The venvs are managed by wrapper scripts; do not manually activate them.

## Next Steps

- Read `README.md` for the project overview
- Read `AGENTS.md` for workflow rules
- Check `INTEROP.md` for integration points with screenery-lean
- Explore `scripts/` and run `--help` on any script of interest
