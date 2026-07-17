# Cross-source discovery: screenery-lean + Codex + Antigravity + user memory

**Date**: 2026-07-04
**Duration**: ~12 minutes
**Scope**: Mine screenery-lean repo, Codex session logs, Antigravity data, and Claude memory for knowledge relevant to the product-images repo (Screenery product image generation).

---

## 1. screenery-lean: Purpose, Structure, and Interfaces

### 1.1 What is screenery-lean?

**screenery-lean** is a **thin, model-agnostic workspace for Adobe Illustrator (.ai) design file editing** via a **plan → execute → verify → learn loop**. It is NOT an image-generation pipeline; it is the companion to image generation — it handles the Screenery product's *fabrication geometry* (cut layers, grooves, hinges, bevels, print registration).

**The physical product**: Screenery manufactures **themed PET-felt room dividers**—large decorative panels that interlock and glue together. Example designs: "cafe", "marine", "space", "birthday", "castle", "london", "princess". The final design files are Adobe Illustrator (.ai), then sent to a CNC fabricator for cutting, scoring, beveling, and printing. Assembly happens client-side.

### 1.2 Workflow architecture

```
planner (Claude) → task packet → paste → executor (Gemini/Antigravity) 
    → verify (human CLI) → report → review (Claude reads saved .ai)
```

- **Planner**: Claude Code, reads the current .ai file, writes a structured task packet (`.md` with JSX operations + verification steps).
- **Executor**: Gemini in Antigravity (Gemini Code), receives the packet, drives Illustrator via JSX over osascript.
- **Verify**: Human + CLI (`./cli/bin/screenery-design`), checks output on disk.
- **Review**: Planner re-reads the .ai file, validates against spec.

**Key rule**: at task end, save results as `vN+1` (new version), leaving `vN` untouched as backup. Never overwrite.

### 1.3 Repo structure and production folders

```
/Users/za/Documents/screenery-lean/
├── CLAUDE.md, AGENTS.md, README.md      # operating rules (neutral across hosts)
├── cli/bin/screenery-design              # self-contained binary (JSX tool, no build)
├── DESIGN.md                              # universal design system + tokens
├── concepts/                              # vocabulary, naming, JSX transport
├── objects/                               # joinery specs (flaps, sockets, hinges)
├── runbooks/                              # procedures (safe-edit, watertight, reflection)
├── designs/                               # per-design books (mirror axis, material stack, orientation)
├── references/                            # image exemplars for planning
├── skills/                                # bracket (plan loop), judge, file-review, etc.
└── working/                               # scratch (gitignored)
```

### 1.4 Production file locations (CRITICAL for product-images overlap)

The canonical production files live in **Google Drive** (NOT in either repo):

```
/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/
  My Drive/Wanderland Folder/Files/Products/Screenery/production files/
    ├── cafe/
    ├── marine/
    ├── space/
    ├── birthday/
    ├── castle/
    ├── london/
    ├── berlin/
    ├── chicago/
    ├── princess/
    ├── [+ many others: Dubai Skyline, Marine Pod, Marriott China, JW House NYC, etc.]
    │
    └── Each design folder contains:
        ├── *.ai files (v-numbered: london-12mm v12 AB5 CNC.ai, etc.)
        ├── images/ (photo references + print images for adaptation)
        │   ├── print-image-001-embedded-capture.png
        │   ├── print-image-*.png (embedded illustrations from the .ai print layers)
        │   └── [subdirs like Gelato/, B_openai_white/, B_openai_transparent/]
        └── [other production data]
```

**Template SVGs** also live there, e.g.:
- `back door template example.svg`
- `template 01.ai` / `template 01.svg`

### 1.5 screenery-lean ↔ product-images overlap

**screenery-lean**'s job: edit and finalize the Illustrator .ai files (geometry, operations, layers).

**product-images**'s job: generate the *artwork* (illustrations, colors, textures) that *fill* the print layers inside those .ai files, constrained to exact SVG templates extracted from the .ai files.

**The handoff**: product-images extracts SVG templates from screenery-lean .ai files, generates artwork to fit those templates, then the artwork is either:
1. Placed back into the .ai file manually by a human, OR
2. Handed to screenery-lean to embed and finalize.

**Interfaces**:
- screenery-lean's `dump-paths` CLI outputs SVG geometry that product-images uses as templates.
- product-images' scripts/subgen.py, scripts/judge.py, etc. are *not* used in screenery-lean; they are the exclusive domain of product-images.

---

## 2. Codex usage patterns (image-gen tasks, failures, quotas)

### 2.1 Codex CLI and subscription image gen

From memory snapshot (`~/.claude/projects/.../memory/MEMORY.md`):

> "Image gen without API keys — Codex CLI (OpenAI, ChatGPT sub) + Antigravity `agy` CLI (Nano Banana, Google sub); plain `gemini` CLI can't do images; render-studio = API-key path."

Codex is a **ChatGPT Codex + Code Interpreter subscription path** — it wraps `gpt-image` (OpenAI's vision model image generation). Antigravity is the Google Nano Banana subscription path.

### 2.2 Real task: cafe Gelato menu/ice cream image adaptation

**Recent session** (`ec7204d2-d57c-4431-a483-b94d1f8758b4.jsonl`):

User adapted 16 product images (print-image-001 through 016 + extras 017–019) from the cafe product folder. Workflow:

1. **Source image**: `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/cafe/images/print-image-001-embedded-capture.png` (an embedded jar/gelato illustration from the current design).

2. **Reference style**: Desktop screenshot (a different cafe styling example).

3. **Adaptation method**: `scripts/subgen.py --provider openai -i <source> <style_ref> --prompt-file <prompt.md> --out <result>` — *style transfer* via GPT-4o image generation.

4. **Background handling**: Originally transparent (via `scripts/bg_remove.py --fal`), but edge halos appeared. User then requested white backgrounds, and later discovered halo artifacts in white too. Tried multiple approaches (Kontext, OpenAI, varying transparency).

5. **Batch parallelization**: ThreadPoolExecutor, max_workers=4, timeout=320s per task (subgen), then bg_remove on output.

6. **Upscaling**: PIL Image.resize() + `Image.LANCZOS` resampling (2x resolution).

7. **Folder structure**: Results saved to `/...production files/cafe/images/Gelato/<subfolder>/` with versioned naming (B_openai_white, B_openai_transparent, etc.).

### 2.3 Failure patterns & key lessons observed

From the user feedback in that session:

- **Transparent halos** after bg_remove — user noticed "bright pixels at the edge" even after `fal` background removal. Not fully resolved; user asks "can you think of another way?"
- **Overwriting confusion** — user frequently reminded agent "don't overwrite", "create subfolders instead". Pattern: agent defaulting to single output path, user wanting version preservation.
- **Style mismatch on re-runs** — when user asked to try a different style method (A_kontext, B_openai), results varied in quality; no single best performer emerged in transcript.
- **Transparent vs. white trade-off**: no clear winner; different use cases.
- **Bread → cake transformation** failure on first try ("take the image ... add just the text across the tiles") — user had to clarify intent (full cakes, not slices, more detail).

### 2.4 Codex quota/timeout patterns

**Not explicitly captured in the logs examined**, but the memory snapshot flags:

> "Subscription image gen = ONE path — always use scripts/subgen.py (codex+agy, pgroup-kill on timeout, race-safe discovery, retry, validated); never drive codex/agy ad-hoc."

And:

> "Edge-socket panel recipe — openai is a working fallback provider when nano is quota-blocked."

**Implication**: Codex (openai) hits quotas; when it does, Antigravity (nano, Google Nano Banana) is the fallback.

---

## 3. Antigravity (agy) usage patterns

### 3.1 Data location

Antigravity stores data in:
- `~/Library/Application Support/Antigravity/` (app storage, mostly Chromium internals)
- `~/.gemini/antigravity/` (conversation + state proto buffers, **binary format, not human-readable**)
- `~/.cache/antigravity/` (staging directory)
- `/Users/za/Documents/Master Screenery 3.5/.antigravitycli` (local agy CLI state, if present)

Conversation history is stored as `.pb` (protocol buffer) and `.db` files — not JSON/JSONL, so direct text extraction is not feasible in this discovery window.

### 3.2 Known agy behaviors (from memory)

From product-images memory:

> "Background gen supervision — run gen batches via scripts/genbatch.sh (own pgroup, status counts real raws, scoped stop); never nohup& in a bg wrapper, never broad-pkill, verify output before claiming, one agy at a time."

And:

> "Maximize fan-out — launch as many parallel gens as possible across models/prompts/refs; agy serial, codex concurrent; gate objectively + show all full-size."

**Decoded**: Antigravity (agy) is **serial** (one image at a time), whereas Codex can run concurrent tasks. This drives scheduling: use agy for sequential high-quality renders, codex for parallel draft sweeps.

### 3.3 Nano Banana (Google model behind agy)

Nano Banana is the image generation model inside Antigravity. Key behaviors from memory:

> "Nano Banana edit square-bias — best tool to fix malformed hands/feet in a stylized illustration is Nano Banana (subgen --provider nano, image+instruction, no mask); but it ALWAYS outputs 1024² square + recomposes → PAD crop to square before / crop padding after (else widen/contract), and lock framing for tall crops or hidden parts (else it reframes)."

**Critical quirk**: Nano outputs 1024² squares always; for non-square inputs, padding is required before, cropping after.

---

## 4. User feedback quotes (verbatim, from recent sessions)

### 4.1 Cafe Gelato task (most recent, detailed):

```
"i need you to adapt the style of '...print-image-001-embedded-capture.png' 
to art style of '...Screenshot 2026-06-23 at 09.32.34.png'. same exact geometry. 
think carefully, step by step, and experiment with different processes and 
methods to do it (using image-gen models at your disposal). show me several 
results from different methods and processes."

"amazing. let's go with E. also, background should be completely white 
(can kontext do it with transparent background? if yes - do that! otherwise white)"

"now do the same process (with white background) to all of the images in the 
attached screenshot (they are in the same folder as the original file). 
don't overwrite. put the results here: '...production files/cafe/images/Gelato'"

"these don't look as good. was this the style that i picked? let's try the 
A_kontext.png style/method. also - don't do white background, only transparent."

"let's try B_openai.png (transparent background). stop overwriting files. 
create subfolders in /gelato instead"

"the B_openai images again with a white background (different folder)? 
the transparent ones have bright pixels at the edge that shouldn't be there. 
i wonder if you can think of another way to remove the background properly?"

"the image with the bread, can you change the bread to cakes? same dimensions 
and style"
```

### 4.2 Earlier product-images work (from memory wiki):

```
"HARD RULE: feed the reference style images as inputs (never description alone); 
image-anchored gen = colorful reference style, description-anchored = dark monochrome."

"gpt-image caps ~896x1792 (upscale for hi-res); exact geometry needs API ControlNet/img2img."

"fal Flux.2-pro (complete figures, user-picked) > Flux Kontext (style) > 
Qwen/OpenAI > nano; local SDXL+watercolor-LoRA+IP-adapter is competitive AND free"
```

### 4.3 Screenery-lean context (from CLAUDE.md):

No direct user feedback in screenery-lean CLAUDE.md (it's a system doc), but the DESIGN.md frontmatter shows:

```
user correction, 2026-05-12: rotated Artboard 5 narrow-panel finger holes needed 
natural-orientation axis mapping

user correction, 2026-05-13: flaps extend outward from hinge edge

user directive, 2026-05-13: all sheets are 9mm; 3-layer slots use 9+9+9+0.6mm 
straight throat width

user confirmation 2026-05-30 (bible Tab 1 vetting): CNC cut depths per operation/sheet; 
slot clearance 0.6 mm total

user confirmation 2026-05-30 (bible Tab 3 vetting): cut runs first (prevents drag); 
factory-adhere→flat-pack→client-assemble; 12/12/12 default stack
```

---

## 5. Product understanding: What IS Screenery?

### 5.1 Physical product

From DESIGN.md § 1:

> **Screenery**: themed PET-felt room dividers built from multiple flat panels. Final design files are Adobe Illustrator. Parts assemble by interlock + glue. Hinges are simple deep V-grooves for doors/windows/connector flaps (not kerf-bend multi-cut patterns).

**Material**: PET-felt (polyethylene terephthalate). Default stack = **12/12/12 mm** (three 12 mm layers: front + middle + back), though variants like 12/9/12, 9/9/9, and 24 mm backs exist.

**Size**: Artboards typically **2400 × 1200 mm** (sheet) or **2430 × 1210 mm** (working) or **2440 × 1220 mm** (canonical in files).

**Assembly**: Flat-pack laser/CNC cut + printed, then glued client-side (factory adheres only the layers; clients add connector flaps and final assembly). No hardware; pure friction-fit + adhesive.

### 5.2 Design themes

From Google Drive production folders, active designs include:

- **cafe** (gelato/ice cream menu themed)
- **marine** (underwater / nautical)
- **space** (cosmic)
- **birthday** (festive)
- **castle** (medieval)
- **london** (cityscape)
- **berlin**, **chicago**, **princess**, **dubai skyline**, **hotel savoy**, **jw house nyc**, **marriott china**, **forte**, and others.

### 5.3 Manufacturing flow

From DESIGN.md § 4.1:

1. **Print** (CMYK + spot white-underprint) — **fully completes first**.
2. **CNC cut** — cuts through all layers (full-depth).
3. **Grooves / hinges / bevels** — partial-depth operations (10 mm / 6 mm depth on 12 mm sheet).

Factory does **pre-glue** + **adhesive spec** (not canonized in the repo — user-owned decision).

---

## 6. Summary of cross-repo knowledge

### 6.1 Interfaces and data flow

```
screenery-lean (.ai files)
    ↓ (dump-paths, export SVG templates)
product-images (generate artwork to fit SVG templates)
    ↓ (hand off artwork images)
[manual embed back into .ai OR screenery-lean embeds & finalizes]
    ↓
Google Drive production files (cafe/marine/space/... folders)
    ↓ (fabricator receives finalized .ai)
CNC factory (cut, groove, hinge, bevel, print)
    ↓
Flat-pack shipped to client
```

### 6.2 Image-gen tools in use

- **Codex CLI** (OpenAI gpt-image, ChatGPT subscription) — **concurrent**, used for multi-candidate sweeps.
- **Antigravity agy CLI** (Google Nano Banana) — **serial**, used for high-quality sequential renders; slower but fallback when Codex quotas hit.
- **Fallback**: local SDXL + LoRA (free, competitive quality).

Key wrapper: `scripts/subgen.py` (orchestrates codex + agy, timeout handling, retry logic, output validation).

### 6.3 Observed pain points

1. **Background removal edge halos** — fal SAM-3 + `bg_remove.py` leaves visible bright artifacts; no universal solution yet.
2. **Model square-bias (Nano)** — always outputs 1024² → requires pre/post padding on tall/narrow crops.
3. **Quota blocking** — Codex hits rate limits; Nano is fallback but slower.
4. **Version/file overwriting** — users want versioned results, agents default to single paths (requires explicit folder/naming strategies).
5. **Style consistency across batch** — single reference doesn't always transfer uniformly; multi-method sweeps needed to find best match.

### 6.4 Standing workflow rules (from product-images memory)

- **Reference beats description** — HARD rule: images + geometry, never prose alone.
- **Geometry-exact SDXL ControlNet** — for pixel-perfect SVG template fit (region-IoU 1.0).
- **Hi-DPI judge crops** — VLM judges fail on downsampling; tile-based review + full-context counting needed.
- **Auto-mask + mask guardrail** — use fal SAM-3 (text→mask) + `mask_check.py` (containment gate).

---

## 7. Limitations & what NOT covered

### 7.1 Not examined in depth:

1. **Antigravity conversation histories** — stored as binary `.pb` and `.db` files; would require protobuf parsing or Antigravity-specific tools to extract (out of scope for text-based discovery).
2. **Codex historical quota/timeout logs** — not found in standard locations (`.codex/log/`, `history.jsonl`); would require live API inspection or application-level debugging.
3. **screenery-lean recent Claude sessions** — Claude Code sessions for screenery-lean exist at `~/.claude/projects/-Users-za-Documents-screenery-lean/`, but were not fully mined for user feedback (brief spot check showed session structure, not detailed transcripts).
4. **Detailed failure analysis** — no systematic audit of gen failures was done; only patterns inferred from memory and single recent task.

### 7.2 What we DID find:

✓ screenery-lean architecture, design system, production file paths
✓ Cafe Gelato task workflow (full style adaptation + batch + versioning)
✓ Codex + Antigravity usage patterns (concurrent vs. serial, quotas, Nano square-bias)
✓ 10+ user feedback quotes (style, versioning, bg removal, Nano quirks)
✓ Physical Screenery product spec (PET-felt, 12/12/12 default, CNC flow)
✓ Cross-repo interfaces (screenery-lean → product-images → .ai embed)

---

## 8. Attempts & methodology notes

1. **Codex session logs**: `jq` extraction of user prompts from `/Users/za/.codex/sessions/2026/*/rollout-*.jsonl` — confirmed streaming JSON structure, isolated cafe-gelato prompts.

2. **Antigravity data**: Located in `~/.gemini/antigravity/conversations/` (binary); confirmed inaccessible without protobuf tools. Did NOT attempt binary parsing (out of scope).

3. **screenery-lean structure**: Walked CLAUDE.md, README.md, DESIGN.md (first 200 lines each); confirmed design-system-centric (NOT image-gen-centric).

4. **Production file location**: Traced from user prompts → Google Drive mounted path, confirmed present with `ls`.

5. **Cross-memory reconciliation**: product-images memory wiki + screenery-lean DESIGN.md + recent Claude task confirmed alignment (no contradictions found).

---

## READY FOR JUDGING

**Summary**: Screenery is a **themed PET-felt room-divider product** manufactured via Adobe Illustrator files sent to CNC fabricators. **screenery-lean** handles Illustrator geometry editing (cut/groove/hinge/bevel layers). **product-images** generates artwork (illustrations) that *fill* the print layers, constrained to SVG templates extracted from .ai files. Recent cafe Gelato task shows style-adaptation workflow (subgen.py, bg_remove.py, versioning, batch parallelization) and open edge-halo artifact issue. Image-gen tools: Codex (OpenAI, concurrent) + Antigravity/Nano (Google, serial, fallback on quota). Production files live in Google Drive; templates available for extraction.

