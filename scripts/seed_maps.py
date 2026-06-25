#!/usr/bin/env python3
"""Seed the maps-data/ scaffold for the image-gen pipeline (PROMPTER maps format).

Writes the registry + a landing map + the Family A / Family B top maps (7 stage
nodes each, as subprocess-link nodes with gate/status/summary/icon). SKIP-IF-EXISTS:
never overwrites a file that's already there, so it's safe to re-run and never
clobbers dashboard/hand edits. Child stage maps are authored separately.

Run: python3 scripts/seed_maps.py   then   node maps/build.js
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "maps-data"

# 7 pipeline stages: (node-slug, title, icon, summary, gate, x, y)
# 1a/1b are parallel constraint-prep → branch off s0, rejoin at s2.
STAGES = [
    ("s0-intake",     "0 · Intake & Plan",  "📋", "Classify family, inventory refs, emit BRIEF+PLAN", "human reviews plan + refs before spend", 140, 320),
    ("s1a-style",     "1a · Style Packet",  "🎨", "References → attachable visual style evidence",     "packet captures real style (vocab/line/light)", 380, 190),
    ("s1b-geometry",  "1b · Geometry",      "📐", "SVG → role-classified contract + geometry guide",   "guide aspect == panel; cutout coords verified", 380, 450),
    ("s2-generation", "2 · Generation",     "🖼", "Multi-model × multi-prompt × ≥3 attempts/variant",  "deterministic gates (geom/text) pass",          640, 320),
    ("s3-select",     "3 · Select",         "⚖", "Vision judge + full-size board → you pick",         "metric + vision judge + your pick",             900, 320),
    ("s4-repair",     "4 · Repair / Refine","🔧", "Fix elements, remove ghosts, harmonize, upscale",   "outside-mask delta==0; leak<0.06; judge",      1160, 320),
    ("s5-export",     "5 · Finalize/Export","📦", "Composite to template exactly; verify; log",        "0 px outside masks; results synced",           1420, 320),
]

EDGES = [
    ("s0-intake", "s1a-style", ""),
    ("s0-intake", "s1b-geometry", ""),
    ("s1a-style", "s2-generation", ""),
    ("s1b-geometry", "s2-generation", ""),
    ("s2-generation", "s3-select", ""),
    ("s3-select", "s4-repair", ""),
    ("s4-repair", "s5-export", ""),
]

# per-family child-map slug each stage node links into (shared where identical)
FAM = {
    "family-a-panel": {
        "title": "Family A — SVG die-cut panel",
        "links": {
            "s0-intake": "stage-0-intake", "s1a-style": "stage-1a-style-packet",
            "s1b-geometry": "stage-1b-geometry-panel", "s2-generation": "stage-2-generation-panel",
            "s3-select": "stage-3-select", "s4-repair": "stage-4-repair", "s5-export": "stage-5-export",
        },
        "intro": "Top map for **Family A** (SVG die-cut product panels). Stages run left→right; "
                 "1a/1b are parallel constraint-prep. Each node drills into its child map. "
                 "Spine: `docs/PIPELINE.md`.",
    },
    "family-b-skyline": {
        "title": "Family B — Skyline / multi-panel",
        "links": {
            "s0-intake": "stage-0-intake", "s1a-style": "stage-1a-style-packet",
            "s1b-geometry": "stage-1b-geometry-skyline", "s2-generation": "stage-2-generation-skyline",
            "s3-select": "stage-3-select", "s4-repair": "stage-4-repair", "s5-export": "stage-5-export",
        },
        "intro": "Top map for **Family B** (skyline / multi-panel). Same stage spine as A; "
                 "geometry (1b) + generation (2) are skyline-specialized. Spine: `docs/PIPELINE.md`.",
    },
}

REGISTRY = ["pipeline", "family-a-panel", "family-b-skyline",
            "stage-0-intake", "stage-1a-style-packet",
            "stage-1b-geometry-panel", "stage-1b-geometry-skyline",
            "stage-2-generation-panel", "stage-2-generation-skyline",
            "stage-3-select", "stage-4-repair", "stage-5-export"]

wrote, skipped = [], []


def w(rel: str, text: str):
    p = SRC / rel
    if p.exists():
        skipped.append(rel)
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    wrote.append(rel)


def fm(d: dict) -> str:
    lines = ["---"]
    for k, v in d.items():
        if v is None:
            continue
        if k in ("title", "gate", "summary", "icon"):
            lines.append(f'{k}: {json.dumps(v)}')
        elif k == "nodes":
            lines.append(f'nodes: [{", ".join(v)}]')
        elif k == "edges":
            lines.append("edges:")
            for e in v:
                lines.append(f'  - {{from: {e[0]}, to: {e[1]}, label: {json.dumps(e[2])}}}')
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


def main():
    # registry
    w("index.md", fm({"title": "Product-Image Pipeline Maps", "type": "maps-root", "nodes": REGISTRY})
      .replace("nodes:", "maps:") + "\n\n# Product-Image Pipeline Maps\n\n"
      "Process maps for the image-generation pipeline (`docs/PIPELINE.md`).\n"
      "Family A = SVG die-cut panel; Family B = skyline/multi-panel. Top maps drill into per-stage child maps.\n")

    # landing
    w("pipeline/index.md", fm({"title": "Pipeline", "type": "map",
        "nodes": ["family-a", "family-b"],
        "edges": []}) + "\n\n# Pipeline\n\nLanding map. Pick a family.\n")
    w("pipeline/family-a.md", fm({"title": "Family A — SVG panel", "type": "subprocess-link",
        "link_map": "family-a-panel", "x": 240, "y": 220, "icon": "🅰",
        "summary": "SVG die-cut product panel pipeline"}) + "\n\n# Family A\n\nSee [[family-a-panel]].\n")
    w("pipeline/family-b.md", fm({"title": "Family B — Skyline", "type": "subprocess-link",
        "link_map": "family-b-skyline", "x": 240, "y": 420, "icon": "🅱",
        "summary": "Skyline / multi-panel pipeline"}) + "\n\n# Family B\n\nSee [[family-b-skyline]].\n")

    # family top maps
    for slug, cfg in FAM.items():
        node_slugs = [s[0] for s in STAGES]
        w(f"{slug}/index.md", fm({"title": cfg["title"], "type": "map",
            "nodes": node_slugs, "edges": EDGES}) + f"\n\n# {cfg['title']}\n\n{cfg['intro']}\n")
        for nslug, title, icon, summary, gate, x, y in STAGES:
            body = (f"\n\n# {title}\n\n{summary}\n\n"
                    f"**Gate:** {gate}\n\n"
                    f"Drills into `[[{cfg['links'][nslug]}]]`. Detail: `docs/PIPELINE.md`.\n")
            w(f"{slug}/{nslug}.md", fm({"title": title, "type": "subprocess-link",
                "link_map": cfg["links"][nslug], "x": x, "y": y, "icon": icon,
                "summary": summary, "gate": gate, "status": "draft"}) + body)

    print(f"wrote {len(wrote)} file(s), skipped {len(skipped)} existing")
    for r in wrote:
        print("  +", r)
    if skipped:
        print("skipped:", ", ".join(skipped))


if __name__ == "__main__":
    main()
