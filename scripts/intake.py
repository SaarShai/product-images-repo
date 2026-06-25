#!/usr/bin/env python3
"""Stage 0 — universal intake & plan.

Classify ANY image task (not just SVG-template), inventory inputs, and emit a
reviewable BRIEF.md + PLAN.md + asset-manifest.json. The plan lists only the
stages that apply to the detected family (see docs/PIPELINE.md router).

Generator only: the gate is the human reviewing the emitted plan/refs.

Examples:
  # SVG die-cut panel
  python3 scripts/intake.py space-np03 --svg path/to.svg --refs a.png b.png --desc "..."
  # finished-illustration repair (no template)
  python3 scripts/intake.py berlin-fix --base berlin.png --intent repair \\
      --desc "fix ghost pillar + harmonize sharpness"
  # edit ONE element, keep rest byte-exact
  python3 scripts/intake.py taxi-rm --base scene.png --element "the yellow taxi" --intent element-edit
  # new free illustration from references
  python3 scripts/intake.py poster --refs r1.png r2.png --desc "watercolor city poster"
  # upscale only
  python3 scripts/intake.py up --base small.png --intent upscale
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# family -> (label, ordered stage keys, workflow doc, skill)
FAMILIES = {
    "A": ("SVG-template / die-cut panel", ["0", "1a", "1b", "2", "3", "4", "5"],
          "docs/svg-template-illustration-workflow.md", "svg-geometry-style-illustration"),
    "B": ("Skyline / multi-panel", ["0", "1a", "1b", "2", "3", "4", "5"],
          "docs/skyline-template-illustration-workflow.md", "skyline-template-illustration"),
    "C": ("Free illustration (no template)", ["0", "1a", "1c?", "2", "3", "4?"],
          "docs/PIPELINE.md", "reference-style-packet"),
    "D": ("Finished-illustration repair/refine", ["0", "1a?", "4", "3?"],
          "wiki/concepts/mask-bounded-external-redraw-donor.md", "element-edit"),
    "E": ("Element-edit (one element, rest byte-exact)", ["0", "4"],
          "docs/IMPROVED-PIPELINE.md", "element-edit"),
    "F": ("Upscale / enhance only", ["0", "4-upscale"],
          "docs/PIPELINE.md", None),
}

STAGE_LINES = {
    "0":   "0 INTAKE & PLAN — this packet. GATE: you review plan + refs before spend.",
    "1a":  "1a STYLE PACKET — build_reference_style_packet.py. GATE: packet captures real style.",
    "1a?": "1a STYLE PACKET (if redrawing in-style) — build_reference_style_packet.py.",
    "1b":  "1b GEOMETRY — svg_geometry_report.py + guide. GATE: guide aspect==panel, coords verified.",
    "1c":  "1c MISSING-REF PRECURSOR — generate a needed reference first. GATE: you approve it.",
    "1c?": "1c MISSING-REF PRECURSOR (if a needed reference doesn't exist) — generate it first.",
    "2":   "2 GENERATION — multi-model x multi-prompt x >=3 attempts/variant, ref+geom-fed. GATE: deterministic gates.",
    "3":   "3 SELECT — judge.py + full-size board. GATE: metric + vision judge + your pick.",
    "3?":  "3 SELECT (if multiple candidates) — full-size board, your pick.",
    "4":   "4 REPAIR/REFINE — edit.py / mask-bounded donor. GATE: outside-mask delta==0, leak<0.06, judge.",
    "4?":  "4 REPAIR/REFINE (if needed) — edit.py. GATE: outside-mask delta==0.",
    "4-upscale": "4 UPSCALE — upscale.py / reupscale.py / adaptive_sharpen.py. GATE: no melt, style kept.",
    "5":   "5 FINALIZE/EXPORT — export_svg_template_fit.py --require-pass + sync_results. GATE: 0 px outside masks.",
}

REPAIR_HINT = re.compile(r"\b(fix|repair|ghost|sharpen|sharpness|clean|artifact|seam|blur|harmoni[sz]e|refine)\b", re.I)
UPSCALE_HINT = re.compile(r"\b(upscale|enhance|super.?res|resolution)\b", re.I)
SKYLINE_HINT = re.compile(r"\b(skyline|cityscape|city.?scape)\b", re.I)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "image-task"


def rel_or_abs(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def img_dims(path: Path) -> str:
    try:
        from PIL import Image  # noqa
        with Image.open(path) as im:
            w, h = im.size
            return f"{w}x{h} (aspect {w/h:.3f})"
    except Exception:
        return "?"


def classify(svg, base, element, intent, desc, title, slug) -> str:
    if intent and intent != "auto":
        return {"new": None, "repair": "D", "element-edit": "E",
                "upscale": "F", "skyline": "B"}.get(intent) or (
            "B" if svg and SKYLINE_HINT.search(f"{slug}{title}{desc}") else
            "A" if svg else "C")
    text = f"{slug} {title} {desc}"
    if svg:
        return "B" if SKYLINE_HINT.search(text) else "A"
    if base:
        if element:
            return "E"
        if UPSCALE_HINT.search(text) and not REPAIR_HINT.search(text):
            return "F"
        return "D"
    return "C"


def copy_unique(source: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    cand = dest_dir / source.name
    if cand.exists():
        for i in range(2, 1000):
            alt = dest_dir / f"{cand.stem}-{i}{cand.suffix}"
            if not alt.exists():
                cand = alt
                break
    shutil.copy2(source, cand)
    return cand


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("task")
    p.add_argument("--desc", default="", help="Free-text description of the goal")
    p.add_argument("--refs", nargs="*", type=Path, default=[], help="Reference images")
    p.add_argument("--svg", type=Path, help="Authoritative SVG template (template families)")
    p.add_argument("--base", type=Path, help="Base image to edit/repair/upscale")
    p.add_argument("--element", help="Named element (element-edit family)")
    p.add_argument("--intent", default="auto",
                   choices=["auto", "new", "repair", "element-edit", "upscale", "skyline"])
    p.add_argument("--title")
    p.add_argument("--no-copy", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    slug = slugify(a.task)
    title = a.title or slug.replace("-", " ").title()
    task_dir = ROOT / "tasks" / slug
    if task_dir.exists() and not a.dry_run:
        raise SystemExit(f"Task already exists: {rel_or_abs(task_dir)}")

    svg = a.svg.expanduser().resolve() if a.svg else None
    base = a.base.expanduser().resolve() if a.base else None
    refs = [r.expanduser().resolve() for r in a.refs]
    missing = [str(x) for x in [svg, base, *refs] if x and not x.exists()]
    if missing:
        raise SystemExit("Missing input file(s):\n" + "\n".join(f"- {m}" for m in missing))

    fam = classify(svg, base, a.element, a.intent, a.desc, title, slug)
    label, stages, workflow, skill = FAMILIES[fam]

    dirs = [task_dir / "source", task_dir / "refs", task_dir / "style-packet",
            task_dir / "prompts", task_dir / "outputs" / "generated",
            task_dir / "outputs" / "reviews", task_dir / "outputs" / "final"]
    if fam in ("A", "B"):
        dirs.append(task_dir / "geometry")

    def w(path: Path, content: str):
        if a.dry_run:
            print(f"would write {rel_or_abs(path)}")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    if a.dry_run:
        for d in dirs:
            print(f"would create {rel_or_abs(d)}")
    else:
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    # copy assets
    def stash(src, sub):
        if not src:
            return None
        if a.no_copy:
            return src
        if a.dry_run:
            print(f"would copy {src} -> tasks/{slug}/{sub}/")
            return task_dir / sub / src.name
        return copy_unique(src, task_dir / sub)

    t_svg = stash(svg, "source")
    t_base = stash(base, "source")
    t_refs = [stash(r, "refs") for r in refs]

    ref_lines = "\n".join(f"- `{rel_or_abs(r)}` — {img_dims(r)}" for r in t_refs if r) or "- (none yet — see 1c if a reference is needed)"
    stage_lines = "\n".join(f"- [ ] {STAGE_LINES[s]}" for s in stages)

    manifest = {
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "task": slug, "title": title,
        "family": fam, "family_label": label, "stages": stages,
        "intent": a.intent, "element": a.element,
        "svg": rel_or_abs(t_svg) if t_svg else None,
        "base_image": rel_or_abs(t_base) if t_base else None,
        "refs": [rel_or_abs(r) for r in t_refs if r],
        "refs_original": [str(r) for r in refs],
        "workflow": workflow, "skill": skill,
        "review_checklist": "docs/review-judge-checklist.md",
        "spine": "docs/PIPELINE.md",
    }

    brief = f"""# {title} — BRIEF

> Stage-0 intake. Family **{fam} — {label}**. Spine: `docs/PIPELINE.md`.
> Workflow: `{workflow}`{f" · Skill: `{skill}`" if skill else ""}

## Goal
{a.desc or "(fill in: what to produce/fix, in one paragraph)"}

## Inputs
- SVG template: {f"`{rel_or_abs(t_svg)}`" if t_svg else "n/a"}
- Base image: {f"`{rel_or_abs(t_base)}` — {img_dims(t_base)}" if t_base else "n/a"}
- Named element: {f"`{a.element}`" if a.element else "n/a"}
- References:
{ref_lines}

## Constraints (fill before spend — keep tight; vague briefs cause rework)
- Format / dimensions:
- Style (object vocabulary, line weight, density, lighting, material — not just palette):
- Hard rules (what must NOT change / appear): no reframe · no hallucinated text ·
- Region scope (edit/repair only): outside-mask delta must be 0.

## Laws in force (docs/PIPELINE.md)
reference>prose · geometry-by-construction · SVG=authority · metrics lie→look ·
never ruin a good raw · show full-size all candidates · separate gen-mask from blend-mask.

## Decisions
- Pending.
"""

    plan = f"""# PLAN — {title}

Family **{fam} — {label}**. Run stages in order; each emits a reviewable artifact
and passes its gate before the next. Per-stage detail: `docs/PIPELINE.md`.

## Stages
{stage_lines}

## Multiplicity rule (Stage 2)
For every input variation: >=3 attempts, >=2 models/prompts where it applies.
Prioritize a spread of candidates over a one-shot. Show all at full size.

## Gate ledger
- [ ] Stage 0 plan + refs reviewed by user
{chr(10).join(f"- [ ] {STAGE_LINES[s].split(' GATE:')[0].strip()} — gate met" for s in stages if s != "0")}
"""

    w(task_dir / "asset-manifest.json", json.dumps(manifest, indent=2) + "\n")
    w(task_dir / "BRIEF.md", brief)
    w(task_dir / "PLAN.md", plan)
    for keep in ["outputs/generated", "outputs/reviews", "outputs/final", "style-packet", "prompts"]:
        w(task_dir / keep / ".gitkeep", "")
    if fam in ("A", "B"):
        w(task_dir / "geometry" / ".gitkeep", "")

    print(f"family {fam} ({label})")
    print(f"stages {' '.join(stages)}")
    if not a.dry_run:
        print(rel_or_abs(task_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
