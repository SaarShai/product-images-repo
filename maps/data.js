window.MAPS = {
  "order": [
    "pipeline",
    "family-a-panel",
    "family-b-skyline",
    "stage-0-intake",
    "stage-1a-style-packet",
    "stage-1b-geometry-panel",
    "stage-1b-geometry-skyline",
    "stage-2-generation-panel",
    "stage-2-generation-skyline",
    "stage-3-select",
    "stage-4-repair",
    "stage-5-export"
  ],
  "maps": {
    "pipeline": {
      "slug": "pipeline",
      "id": "mpiegl",
      "title": "Pipeline",
      "kind": "process",
      "url": "../maps-data/pipeline/index.md",
      "nodes": [
        {
          "id": "n95ye3",
          "slug": "family-a",
          "name": "Family A — SVG panel",
          "type": "subprocess-link",
          "summary": "SVG die-cut product panel pipeline",
          "icon": "🅰",
          "tags": [],
          "status": null,
          "refs": [
            {
              "target": "family-a-panel",
              "label": "family-a-panel"
            }
          ],
          "refsCollapsed": false,
          "x": 240,
          "y": 220,
          "lane": null,
          "link_map": "family-a-panel",
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/pipeline/family-a.md"
        },
        {
          "id": "nfldga",
          "slug": "family-b",
          "name": "Family B — Skyline",
          "type": "subprocess-link",
          "summary": "Skyline / multi-panel pipeline",
          "icon": "🅱",
          "tags": [],
          "status": null,
          "refs": [
            {
              "target": "family-b-skyline",
              "label": "family-b-skyline"
            }
          ],
          "refsCollapsed": false,
          "x": 240,
          "y": 420,
          "lane": null,
          "link_map": "family-b-skyline",
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/pipeline/family-b.md"
        }
      ],
      "edges": [],
      "frames": []
    },
    "family-a-panel": {
      "slug": "family-a-panel",
      "id": "metgr1",
      "title": "Family A — SVG die-cut panel",
      "kind": "process",
      "url": "../maps-data/family-a-panel/index.md",
      "nodes": [
        {
          "id": "nur808",
          "slug": "s0-intake",
          "name": "0 · Intake & Plan",
          "type": "subprocess-link",
          "summary": "Classify family, inventory refs, emit BRIEF+PLAN",
          "icon": "📋",
          "tags": [],
          "status": "draft",
          "refs": [
            {
              "target": "stage-0-intake",
              "label": "stage-0-intake"
            }
          ],
          "refsCollapsed": false,
          "x": 140,
          "y": 320,
          "lane": null,
          "link_map": "stage-0-intake",
          "gate": "human reviews plan + refs before spend",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/family-a-panel/s0-intake.md"
        },
        {
          "id": "n0plgk",
          "slug": "s1a-style",
          "name": "1a · Style Packet",
          "type": "subprocess-link",
          "summary": "References → attachable visual style evidence",
          "icon": "🎨",
          "tags": [],
          "status": "draft",
          "refs": [
            {
              "target": "stage-1a-style-packet",
              "label": "stage-1a-style-packet"
            }
          ],
          "refsCollapsed": false,
          "x": 380,
          "y": 190,
          "lane": null,
          "link_map": "stage-1a-style-packet",
          "gate": "packet captures real style (vocab/line/light)",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/family-a-panel/s1a-style.md"
        },
        {
          "id": "nfdggc",
          "slug": "s1b-geometry",
          "name": "1b · Geometry",
          "type": "subprocess-link",
          "summary": "SVG → role-classified contract + geometry guide",
          "icon": "📐",
          "tags": [],
          "status": "draft",
          "refs": [
            {
              "target": "stage-1b-geometry-panel",
              "label": "stage-1b-geometry-panel"
            }
          ],
          "refsCollapsed": false,
          "x": 380,
          "y": 450,
          "lane": null,
          "link_map": "stage-1b-geometry-panel",
          "gate": "guide aspect == panel; cutout coords verified",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/family-a-panel/s1b-geometry.md"
        },
        {
          "id": "nnczrn",
          "slug": "s2-generation",
          "name": "2 · Generation",
          "type": "subprocess-link",
          "summary": "Multi-model × multi-prompt × ≥3 attempts/variant",
          "icon": "🖼",
          "tags": [],
          "status": "draft",
          "refs": [
            {
              "target": "stage-2-generation-panel",
              "label": "stage-2-generation-panel"
            }
          ],
          "refsCollapsed": false,
          "x": 640,
          "y": 320,
          "lane": null,
          "link_map": "stage-2-generation-panel",
          "gate": "deterministic gates (geom/text) pass",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/family-a-panel/s2-generation.md"
        },
        {
          "id": "n7f664",
          "slug": "s3-select",
          "name": "3 · Select",
          "type": "subprocess-link",
          "summary": "Vision judge + full-size board → you pick",
          "icon": "⚖",
          "tags": [],
          "status": "draft",
          "refs": [
            {
              "target": "stage-3-select",
              "label": "stage-3-select"
            }
          ],
          "refsCollapsed": false,
          "x": 900,
          "y": 320,
          "lane": null,
          "link_map": "stage-3-select",
          "gate": "metric + vision judge + your pick",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/family-a-panel/s3-select.md"
        },
        {
          "id": "ngwgj6",
          "slug": "s4-repair",
          "name": "4 · Repair / Refine",
          "type": "subprocess-link",
          "summary": "Fix elements, remove ghosts, harmonize, upscale",
          "icon": "🔧",
          "tags": [],
          "status": "draft",
          "refs": [
            {
              "target": "stage-4-repair",
              "label": "stage-4-repair"
            }
          ],
          "refsCollapsed": false,
          "x": 1160,
          "y": 320,
          "lane": null,
          "link_map": "stage-4-repair",
          "gate": "outside-mask delta==0; leak<0.06; judge",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/family-a-panel/s4-repair.md"
        },
        {
          "id": "nol8yd",
          "slug": "s5-export",
          "name": "5 · Finalize/Export",
          "type": "subprocess-link",
          "summary": "Composite to template exactly; verify; log",
          "icon": "📦",
          "tags": [],
          "status": "draft",
          "refs": [
            {
              "target": "stage-5-export",
              "label": "stage-5-export"
            }
          ],
          "refsCollapsed": false,
          "x": 1420,
          "y": 320,
          "lane": null,
          "link_map": "stage-5-export",
          "gate": "0 px outside masks; results synced",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/family-a-panel/s5-export.md"
        }
      ],
      "edges": [
        {
          "from": "nur808",
          "to": "n0plgk",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nur808",
          "to": "nfdggc",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "n0plgk",
          "to": "nnczrn",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nfdggc",
          "to": "nnczrn",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nnczrn",
          "to": "n7f664",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "n7f664",
          "to": "ngwgj6",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "ngwgj6",
          "to": "nol8yd",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        }
      ],
      "frames": []
    },
    "family-b-skyline": {
      "slug": "family-b-skyline",
      "id": "myyoxw",
      "title": "Family B — Skyline / multi-panel",
      "kind": "process",
      "url": "../maps-data/family-b-skyline/index.md",
      "nodes": [
        {
          "id": "n1cid6",
          "slug": "s0-intake",
          "name": "0 · Intake & Plan",
          "type": "subprocess-link",
          "summary": "Classify family, inventory refs, emit BRIEF+PLAN",
          "icon": "📋",
          "tags": [],
          "status": "draft",
          "refs": [
            {
              "target": "stage-0-intake",
              "label": "stage-0-intake"
            }
          ],
          "refsCollapsed": false,
          "x": 140,
          "y": 320,
          "lane": null,
          "link_map": "stage-0-intake",
          "gate": "human reviews plan + refs before spend",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/family-b-skyline/s0-intake.md"
        },
        {
          "id": "nuikqu",
          "slug": "s1a-style",
          "name": "1a · Style Packet",
          "type": "subprocess-link",
          "summary": "References → attachable visual style evidence",
          "icon": "🎨",
          "tags": [],
          "status": "draft",
          "refs": [
            {
              "target": "stage-1a-style-packet",
              "label": "stage-1a-style-packet"
            }
          ],
          "refsCollapsed": false,
          "x": 380,
          "y": 190,
          "lane": null,
          "link_map": "stage-1a-style-packet",
          "gate": "packet captures real style (vocab/line/light)",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/family-b-skyline/s1a-style.md"
        },
        {
          "id": "nudjd9",
          "slug": "s1b-geometry",
          "name": "1b · Geometry",
          "type": "subprocess-link",
          "summary": "SVG → role-classified contract + geometry guide",
          "icon": "📐",
          "tags": [],
          "status": "draft",
          "refs": [
            {
              "target": "stage-1b-geometry-skyline",
              "label": "stage-1b-geometry-skyline"
            }
          ],
          "refsCollapsed": false,
          "x": 380,
          "y": 450,
          "lane": null,
          "link_map": "stage-1b-geometry-skyline",
          "gate": "guide aspect == panel; cutout coords verified",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/family-b-skyline/s1b-geometry.md"
        },
        {
          "id": "n2m5nu",
          "slug": "s2-generation",
          "name": "2 · Generation",
          "type": "subprocess-link",
          "summary": "Multi-model × multi-prompt × ≥3 attempts/variant",
          "icon": "🖼",
          "tags": [],
          "status": "draft",
          "refs": [
            {
              "target": "stage-2-generation-skyline",
              "label": "stage-2-generation-skyline"
            }
          ],
          "refsCollapsed": false,
          "x": 640,
          "y": 320,
          "lane": null,
          "link_map": "stage-2-generation-skyline",
          "gate": "deterministic gates (geom/text) pass",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/family-b-skyline/s2-generation.md"
        },
        {
          "id": "nw62tt",
          "slug": "s3-select",
          "name": "3 · Select",
          "type": "subprocess-link",
          "summary": "Vision judge + full-size board → you pick",
          "icon": "⚖",
          "tags": [],
          "status": "draft",
          "refs": [
            {
              "target": "stage-3-select",
              "label": "stage-3-select"
            }
          ],
          "refsCollapsed": false,
          "x": 900,
          "y": 320,
          "lane": null,
          "link_map": "stage-3-select",
          "gate": "metric + vision judge + your pick",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/family-b-skyline/s3-select.md"
        },
        {
          "id": "nr2v3m",
          "slug": "s4-repair",
          "name": "4 · Repair / Refine",
          "type": "subprocess-link",
          "summary": "Fix elements, remove ghosts, harmonize, upscale",
          "icon": "🔧",
          "tags": [],
          "status": "draft",
          "refs": [
            {
              "target": "stage-4-repair",
              "label": "stage-4-repair"
            }
          ],
          "refsCollapsed": false,
          "x": 1160,
          "y": 320,
          "lane": null,
          "link_map": "stage-4-repair",
          "gate": "outside-mask delta==0; leak<0.06; judge",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/family-b-skyline/s4-repair.md"
        },
        {
          "id": "n79x29",
          "slug": "s5-export",
          "name": "5 · Finalize/Export",
          "type": "subprocess-link",
          "summary": "Composite to template exactly; verify; log",
          "icon": "📦",
          "tags": [],
          "status": "draft",
          "refs": [
            {
              "target": "stage-5-export",
              "label": "stage-5-export"
            }
          ],
          "refsCollapsed": false,
          "x": 1420,
          "y": 320,
          "lane": null,
          "link_map": "stage-5-export",
          "gate": "0 px outside masks; results synced",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/family-b-skyline/s5-export.md"
        }
      ],
      "edges": [
        {
          "from": "n1cid6",
          "to": "nuikqu",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "n1cid6",
          "to": "nudjd9",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nuikqu",
          "to": "n2m5nu",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nudjd9",
          "to": "n2m5nu",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "n2m5nu",
          "to": "nw62tt",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nw62tt",
          "to": "nr2v3m",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nr2v3m",
          "to": "n79x29",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        }
      ],
      "frames": []
    },
    "stage-0-intake": {
      "slug": "stage-0-intake",
      "id": "ml4oym",
      "title": "Stage 0 — Intake & Plan",
      "kind": "process",
      "url": "../maps-data/stage-0-intake/index.md",
      "nodes": [
        {
          "id": "n9f3o6",
          "slug": "receive-brief",
          "name": "Receive brief",
          "type": "step",
          "summary": "Take in the task: description + references (+ optional SVG / base image)",
          "icon": "📥",
          "tags": [
            "intake",
            "brief"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "classify-family",
              "label": "classify-family"
            },
            {
              "target": "pipeline-spine",
              "label": "docs/PIPELINE.md"
            }
          ],
          "refsCollapsed": false,
          "x": 140,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-0-intake/receive-brief.md"
        },
        {
          "id": "n2z879",
          "slug": "classify-family",
          "name": "Classify family",
          "type": "step",
          "summary": "Run intake.py — classify task family A–F + which stages apply",
          "icon": "🗂️",
          "tags": [
            "intake",
            "router"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "intake-py",
              "label": "scripts/intake.py"
            },
            {
              "target": "inventory-refs",
              "label": "inventory-refs"
            }
          ],
          "refsCollapsed": false,
          "x": 400,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "family + applicable stages determined",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-0-intake/classify-family.md"
        },
        {
          "id": "n21rlw",
          "slug": "inventory-refs",
          "name": "Inventory references",
          "type": "step",
          "summary": "Validate every named reference exists + read its dimensions",
          "icon": "🔎",
          "tags": [
            "intake",
            "references"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "refs-complete",
              "label": "refs-complete"
            }
          ],
          "refsCollapsed": false,
          "x": 660,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "all named references present & readable",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-0-intake/inventory-refs.md"
        },
        {
          "id": "na5ug8",
          "slug": "refs-complete",
          "name": "All references exist?",
          "type": "decision",
          "summary": "Branch on whether every needed reference is present",
          "icon": "❓",
          "tags": [
            "decision",
            "references"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "inventory-refs",
              "label": "inventory-refs"
            },
            {
              "target": "generate-missing-ref",
              "label": "generate-missing-ref"
            },
            {
              "target": "emit-packet",
              "label": "emit-packet"
            }
          ],
          "refsCollapsed": false,
          "x": 920,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-0-intake/refs-complete.md"
        },
        {
          "id": "napff7",
          "slug": "generate-missing-ref",
          "name": "Generate missing reference",
          "type": "step",
          "summary": "Precursor: generate a needed reference first (stage 1c)",
          "icon": "🪄",
          "tags": [
            "precursor",
            "references",
            "stage-1c"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "refs-complete",
              "label": "refs-complete"
            },
            {
              "target": "emit-packet",
              "label": "emit-packet"
            }
          ],
          "refsCollapsed": false,
          "x": 1180,
          "y": 180,
          "lane": null,
          "link_map": null,
          "gate": "user approves precursor",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-0-intake/generate-missing-ref.md"
        },
        {
          "id": "n2wyi1",
          "slug": "emit-packet",
          "name": "Emit plan packet",
          "type": "step",
          "summary": "Write BRIEF.md + PLAN.md + asset-manifest.json",
          "icon": "📦",
          "tags": [
            "intake",
            "artifact"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "classify-family",
              "label": "classify-family"
            },
            {
              "target": "generate-missing-ref",
              "label": "generate-missing-ref"
            },
            {
              "target": "plan-review",
              "label": "plan-review"
            },
            {
              "target": "intake-py",
              "label": "scripts/intake.py"
            }
          ],
          "refsCollapsed": false,
          "x": 1180,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "BRIEF + PLAN + manifest written",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-0-intake/emit-packet.md"
        },
        {
          "id": "nbcote",
          "slug": "plan-review",
          "name": "Plan review (human gate)",
          "type": "decision",
          "summary": "Human reviews plan + reference inventory BEFORE any spend",
          "icon": "🛂",
          "tags": [
            "gate",
            "human",
            "review"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "emit-packet",
              "label": "emit-packet"
            },
            {
              "target": "pipeline-spine",
              "label": "docs/PIPELINE.md"
            }
          ],
          "refsCollapsed": false,
          "x": 1440,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "human reviews plan + reference inventory BEFORE any spend",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-0-intake/plan-review.md"
        },
        {
          "id": "nkhrad",
          "slug": "intake-py",
          "name": "intake.py",
          "type": "reference",
          "summary": "scripts/intake.py — universal intake: classify family, inventory inputs, emit packet",
          "icon": "🛠️",
          "tags": [
            "tool",
            "script"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "classify-family",
              "label": "classify-family"
            },
            {
              "target": "inventory-refs",
              "label": "inventory-refs"
            },
            {
              "target": "emit-packet",
              "label": "emit-packet"
            },
            {
              "target": "pipeline-spine",
              "label": "docs/PIPELINE.md"
            }
          ],
          "refsCollapsed": false,
          "x": 400,
          "y": 450,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-0-intake/intake-py.md"
        },
        {
          "id": "nobcae",
          "slug": "pipeline-spine",
          "name": "PIPELINE spine",
          "type": "reference",
          "summary": "docs/PIPELINE.md — the end-to-end lifecycle spine + Stage 0 contract",
          "icon": "📜",
          "tags": [
            "doc",
            "source-of-truth"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "receive-brief",
              "label": "this map"
            }
          ],
          "refsCollapsed": false,
          "x": 140,
          "y": 450,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-0-intake/pipeline-spine.md"
        }
      ],
      "edges": [
        {
          "from": "n9f3o6",
          "to": "n2z879",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "n2z879",
          "to": "n21rlw",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "n21rlw",
          "to": "na5ug8",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "na5ug8",
          "to": "napff7",
          "label": "No",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "na5ug8",
          "to": "n2wyi1",
          "label": "Yes",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "napff7",
          "to": "n2wyi1",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "n2wyi1",
          "to": "nbcote",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "n9f3o6",
          "to": "nobcae",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "smoothstep"
        },
        {
          "from": "n2z879",
          "to": "nkhrad",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "smoothstep"
        }
      ],
      "frames": []
    },
    "stage-1a-style-packet": {
      "slug": "stage-1a-style-packet",
      "id": "mv60tf",
      "title": "Stage 1a — References → Style Packet",
      "kind": "process",
      "url": "../maps-data/stage-1a-style-packet/index.md",
      "nodes": [
        {
          "id": "nfzhkv",
          "slug": "gather-references",
          "name": "Gather references",
          "type": "step",
          "summary": "Collect reference images into the task's refs/",
          "icon": "🖼️",
          "tags": [
            "style-packet",
            "references"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "build-packet",
              "label": "build-packet"
            },
            {
              "target": "law-reference-beats-prose",
              "label": "reference beats prose"
            }
          ],
          "refsCollapsed": false,
          "x": 140,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-1a-style-packet/gather-references.md"
        },
        {
          "id": "nmsij2",
          "slug": "build-packet",
          "name": "Build packet",
          "type": "step",
          "summary": "Run build_reference_style_packet.py; emit contact + exemplar sheets",
          "icon": "📦",
          "tags": [
            "style-packet",
            "tooling"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "build-reference-style-packet-py",
              "label": "build_reference_style_packet.py"
            },
            {
              "target": "gather-references",
              "label": "gather-references"
            },
            {
              "target": "re-curate",
              "label": "re-curate"
            },
            {
              "target": "inspect-packet",
              "label": "inspect-packet"
            }
          ],
          "refsCollapsed": false,
          "x": 400,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "style-packet/ built (contact + exemplar sheets)",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-1a-style-packet/build-packet.md"
        },
        {
          "id": "nyd8ax",
          "slug": "inspect-packet",
          "name": "Inspect packet",
          "type": "decision",
          "summary": "Does the packet capture the REAL art style, not just palette?",
          "icon": "🔍",
          "tags": [
            "style-packet",
            "review",
            "gate"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "re-curate",
              "label": "re-curate"
            },
            {
              "target": "packet-approved",
              "label": "packet-approved"
            }
          ],
          "refsCollapsed": false,
          "x": 660,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-1a-style-packet/inspect-packet.md"
        },
        {
          "id": "n40scw",
          "slug": "re-curate",
          "name": "Re-curate refs",
          "type": "step",
          "summary": "Add or swap reference images to fix the captured-style gap",
          "icon": "🔁",
          "tags": [
            "style-packet",
            "references"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "inspect-packet",
              "label": "inspect-packet"
            },
            {
              "target": "build-packet",
              "label": "build-packet"
            }
          ],
          "refsCollapsed": false,
          "x": 660,
          "y": 180,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-1a-style-packet/re-curate.md"
        },
        {
          "id": "nhar1l",
          "slug": "packet-approved",
          "name": "Packet approved",
          "type": "step",
          "summary": "Style packet captures the real art style; cleared for Stage 2",
          "icon": "✅",
          "tags": [
            "style-packet",
            "gate"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "inspect-packet",
              "label": "inspect-packet"
            }
          ],
          "refsCollapsed": false,
          "x": 920,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "packet captures the REAL art style; user confirms",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-1a-style-packet/packet-approved.md"
        },
        {
          "id": "nmysrb",
          "slug": "build-reference-style-packet-py",
          "name": "build_reference_style_packet.py",
          "type": "reference",
          "summary": "Tool: refs/ → style-packet/ (contact + exemplar sheets)",
          "icon": "🛠️",
          "tags": [
            "tool",
            "style-packet"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "build-packet",
              "label": "build-packet"
            }
          ],
          "refsCollapsed": false,
          "x": 400,
          "y": 450,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-1a-style-packet/build-reference-style-packet-py.md"
        },
        {
          "id": "nybhps",
          "slug": "law-reference-beats-prose",
          "name": "LAW: reference beats prose",
          "type": "reference",
          "summary": "Core law 1: drive generation with reference IMAGES, never description alone",
          "icon": "⚖️",
          "tags": [
            "law",
            "references"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "gather-references",
              "label": "gather-references"
            }
          ],
          "refsCollapsed": false,
          "x": 140,
          "y": 450,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-1a-style-packet/law-reference-beats-prose.md"
        }
      ],
      "edges": [
        {
          "from": "nfzhkv",
          "to": "nmsij2",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nmsij2",
          "to": "nyd8ax",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nyd8ax",
          "to": "n40scw",
          "label": "No",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "n40scw",
          "to": "nmsij2",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nyd8ax",
          "to": "nhar1l",
          "label": "Yes",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nfzhkv",
          "to": "nybhps",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "smoothstep"
        },
        {
          "from": "nmsij2",
          "to": "nmysrb",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "smoothstep"
        }
      ],
      "frames": []
    },
    "stage-1b-geometry-panel": {
      "slug": "stage-1b-geometry-panel",
      "id": "m8s3b4",
      "title": "Stage 1b — Geometry (SVG die-cut panel)",
      "kind": "process",
      "url": "../maps-data/stage-1b-geometry-panel/index.md",
      "nodes": [
        {
          "id": "nb8tyk",
          "slug": "parse-svg",
          "name": "Parse SVG",
          "type": "step",
          "summary": "Run svg_geometry_report.py → report of contour, cutouts, keep-clear",
          "icon": "📐",
          "tags": [
            "svg",
            "geometry",
            "parse"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "svg-geometry-report-py",
              "label": "scripts/svg_geometry_report.py"
            },
            {
              "target": "classify-roles",
              "label": "classify-roles"
            }
          ],
          "refsCollapsed": false,
          "x": 140,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "outer contour + cutouts + keep-clear zones identified",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-1b-geometry-panel/parse-svg.md"
        },
        {
          "id": "nis03s",
          "slug": "classify-roles",
          "name": "Classify roles",
          "type": "step",
          "summary": "Fill template-manifest.json — contour, cutouts, slots, safe areas",
          "icon": "🗂️",
          "tags": [
            "svg",
            "geometry",
            "manifest"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "parse-svg",
              "label": "parse-svg"
            },
            {
              "target": "build-guide",
              "label": "build-guide"
            }
          ],
          "refsCollapsed": false,
          "x": 400,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "all geometry roles assigned (no ambiguous roles)",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-1b-geometry-panel/classify-roles.md"
        },
        {
          "id": "n0n5mt",
          "slug": "build-guide",
          "name": "Build guide",
          "type": "step",
          "summary": "build_trueaspect_base.py → true-aspect geometry-guide PNG for the model",
          "icon": "🖼️",
          "tags": [
            "svg",
            "geometry",
            "guide"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "svg-template-workflow",
              "label": "docs/svg-template-illustration-workflow.md"
            },
            {
              "target": "outset-needed",
              "label": "outset-needed"
            }
          ],
          "refsCollapsed": false,
          "x": 660,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "guide aspect == panel aspect",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-1b-geometry-panel/build-guide.md"
        },
        {
          "id": "nx2x3p",
          "slug": "outset-needed",
          "name": "outset-needed?",
          "type": "decision",
          "summary": "cut-drift risk on tight cutouts?",
          "icon": null,
          "tags": [],
          "status": "draft",
          "refs": [
            {
              "target": "outset-cutouts",
              "label": "outset-cutouts"
            },
            {
              "target": "verify-coords",
              "label": "verify-coords"
            }
          ],
          "refsCollapsed": false,
          "x": 920,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-1b-geometry-panel/outset-needed.md"
        },
        {
          "id": "ntf9uk",
          "slug": "outset-cutouts",
          "name": "outset-cutouts",
          "type": "step",
          "summary": "buffer internal cutouts outward to absorb drift",
          "icon": null,
          "tags": [],
          "status": "draft",
          "refs": [
            {
              "target": "verify-coords",
              "label": "verify-coords"
            }
          ],
          "refsCollapsed": false,
          "x": 1180,
          "y": 180,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-1b-geometry-panel/outset-cutouts.md"
        },
        {
          "id": "nax51r",
          "slug": "verify-coords",
          "name": "verify-coords",
          "type": "step",
          "summary": "final geometry gate before generation",
          "icon": null,
          "tags": [],
          "status": "draft",
          "refs": [],
          "refsCollapsed": false,
          "x": 1440,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "cutout coords verified vs SVG; guide aspect == panel aspect",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-1b-geometry-panel/verify-coords.md"
        },
        {
          "id": "ngoy5l",
          "slug": "svg-geometry-report-py",
          "name": "scripts/svg_geometry_report.py",
          "type": "reference",
          "summary": "SVG → role-classified geometry report",
          "icon": null,
          "tags": [],
          "status": "draft",
          "refs": [
            {
              "target": "parse-svg",
              "label": "parse-svg"
            }
          ],
          "refsCollapsed": false,
          "x": 140,
          "y": 450,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-1b-geometry-panel/svg-geometry-report-py.md"
        },
        {
          "id": "nr5mce",
          "slug": "svg-template-workflow",
          "name": "docs/svg-template-illustration-workflow.md",
          "type": "reference",
          "summary": "canonical SVG-template workflow",
          "icon": null,
          "tags": [],
          "status": "draft",
          "refs": [
            {
              "target": "build-guide",
              "label": "build-guide"
            }
          ],
          "refsCollapsed": false,
          "x": 660,
          "y": 450,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-1b-geometry-panel/svg-template-workflow.md"
        }
      ],
      "edges": [
        {
          "from": "nb8tyk",
          "to": "nis03s",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nis03s",
          "to": "n0n5mt",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "n0n5mt",
          "to": "nx2x3p",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nx2x3p",
          "to": "ntf9uk",
          "label": "Yes",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "ntf9uk",
          "to": "nax51r",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nx2x3p",
          "to": "nax51r",
          "label": "No",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nb8tyk",
          "to": "ngoy5l",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "smoothstep"
        },
        {
          "from": "n0n5mt",
          "to": "nr5mce",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "smoothstep"
        }
      ],
      "frames": []
    },
    "stage-1b-geometry-skyline": {
      "slug": "stage-1b-geometry-skyline",
      "id": "mqieox",
      "title": "Stage 1b — Geometry (Skyline / multi-panel)",
      "kind": "process",
      "url": "../maps-data/stage-1b-geometry-skyline/index.md",
      "nodes": [
        {
          "id": "nm2ayh",
          "slug": "parse-3panel-svg",
          "name": "Parse 3-panel SVG",
          "type": "step",
          "summary": "skyline_panel.py spec → per-panel .spec.json (widths/aspects from SVG viewBox)",
          "icon": "📐",
          "tags": [
            "svg",
            "geometry",
            "skyline"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "skyline-panel-py",
              "label": "scripts/skyline_panel.py"
            },
            {
              "target": "allocate-landmarks",
              "label": "allocate-landmarks"
            }
          ],
          "refsCollapsed": false,
          "x": 140,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "panel widths/aspects derived from SVG viewBox",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-1b-geometry-skyline/parse-3panel-svg.md"
        },
        {
          "id": "n0xqhm",
          "slug": "allocate-landmarks",
          "name": "Allocate landmarks",
          "type": "step",
          "summary": "Assign landmarks to panels — each landmark whole within one panel",
          "icon": "🏛️",
          "tags": [
            "skyline",
            "landmarks",
            "composition"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "plan-saloon-arch",
              "label": "plan-saloon-arch"
            },
            {
              "target": "skyline-workflow",
              "label": "docs/skyline-template-illustration-workflow.md"
            }
          ],
          "refsCollapsed": false,
          "x": 400,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "no landmark split across a panel boundary",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-1b-geometry-skyline/allocate-landmarks.md"
        },
        {
          "id": "nbrbdq",
          "slug": "plan-saloon-arch",
          "name": "Plan saloon-door arch",
          "type": "step",
          "summary": "Treat the saloon arch as a compositional opportunity, never forced architecture",
          "icon": "🌉",
          "tags": [
            "skyline",
            "saloon-arch",
            "composition"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "adapt-top-contour",
              "label": "adapt-top-contour"
            }
          ],
          "refsCollapsed": false,
          "x": 660,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "arch placement is optional/quiet, not forcing awkward architecture",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-1b-geometry-skyline/plan-saloon-arch.md"
        },
        {
          "id": "nniok0",
          "slug": "adapt-top-contour",
          "name": "Adapt top contour",
          "type": "step",
          "summary": "Trace the chosen skyline silhouette; the green contour is only a placeholder",
          "icon": "🏙️",
          "tags": [
            "skyline",
            "top-contour",
            "silhouette"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "safe-pocket-plan",
              "label": "safe-pocket-plan"
            }
          ],
          "refsCollapsed": false,
          "x": 920,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "no fragile detail above the contour",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-1b-geometry-skyline/adapt-top-contour.md"
        },
        {
          "id": "ny86gb",
          "slug": "safe-pocket-plan",
          "name": "Safe-pocket plan (gate)",
          "type": "step",
          "summary": "GATE — guide aspect == panel; red zones hold only quiet/infrastructure",
          "icon": "🚦",
          "tags": [
            "skyline",
            "gate",
            "keep-clear",
            "preflight"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "skyline-panel-py",
              "label": "scripts/skyline_panel.py"
            }
          ],
          "refsCollapsed": false,
          "x": 1180,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "guide aspect == panel; red zones contain only quiet/infrastructure",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-1b-geometry-skyline/safe-pocket-plan.md"
        },
        {
          "id": "nimr3m",
          "slug": "skyline-panel-py",
          "name": "skyline_panel.py",
          "type": "reference",
          "summary": "scripts/skyline_panel.py — spec → per-panel .spec.json, guide build, panel checks",
          "icon": "🛠️",
          "tags": [
            "tool",
            "script",
            "skyline"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "parse-3panel-svg",
              "label": "parse-3panel-svg"
            },
            {
              "target": "safe-pocket-plan",
              "label": "safe-pocket-plan"
            },
            {
              "target": "skyline-workflow",
              "label": "docs/skyline-template-illustration-workflow.md"
            }
          ],
          "refsCollapsed": false,
          "x": 140,
          "y": 450,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-1b-geometry-skyline/skyline-panel-py.md"
        },
        {
          "id": "nuooka",
          "slug": "skyline-workflow",
          "name": "skyline workflow",
          "type": "reference",
          "summary": "docs/skyline-template-illustration-workflow.md — skyline rules source of truth",
          "icon": "📄",
          "tags": [
            "doc",
            "workflow",
            "skyline"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "allocate-landmarks",
              "label": "allocate-landmarks"
            },
            {
              "target": "plan-saloon-arch",
              "label": "plan-saloon-arch"
            },
            {
              "target": "adapt-top-contour",
              "label": "adapt-top-contour"
            },
            {
              "target": "safe-pocket-plan",
              "label": "safe-pocket-plan"
            },
            {
              "target": "skyline-panel-py",
              "label": "scripts/skyline_panel.py"
            }
          ],
          "refsCollapsed": false,
          "x": 400,
          "y": 450,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-1b-geometry-skyline/skyline-workflow.md"
        }
      ],
      "edges": [
        {
          "from": "nm2ayh",
          "to": "n0xqhm",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "n0xqhm",
          "to": "nbrbdq",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nbrbdq",
          "to": "nniok0",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nniok0",
          "to": "ny86gb",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nm2ayh",
          "to": "nimr3m",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "smoothstep"
        },
        {
          "from": "n0xqhm",
          "to": "nuooka",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "smoothstep"
        }
      ],
      "frames": []
    },
    "stage-2-generation-panel": {
      "slug": "stage-2-generation-panel",
      "id": "m9xic3",
      "title": "Stage 2 — Generation (SVG die-cut panel)",
      "kind": "process",
      "url": "../maps-data/stage-2-generation-panel/index.md",
      "nodes": [
        {
          "id": "nfunjz",
          "slug": "assemble-inputs",
          "name": "Assemble inputs",
          "type": "step",
          "summary": "Build the prompt (no geometry words) + attach style-packet refs + geometry guide",
          "icon": "🧩",
          "tags": [
            "generation",
            "prompt",
            "references"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "exact-geometry",
              "label": "exact-geometry"
            }
          ],
          "refsCollapsed": false,
          "x": 140,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "NO geometry words (SVG/contour/red zone/arch) in prompt; refs + geometry guide attached",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-2-generation-panel/assemble-inputs.md"
        },
        {
          "id": "nzbn3n",
          "slug": "exact-geometry",
          "name": "Need pixel-exact contour fit?",
          "type": "decision",
          "summary": "Branch on whether the panel needs pixel-exact contour fit",
          "icon": "❓",
          "tags": [
            "decision",
            "geometry"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "controlnet-lane",
              "label": "controlnet-lane"
            },
            {
              "target": "subscription-lane",
              "label": "subscription-lane"
            },
            {
              "target": "fan-out",
              "label": "fan-out"
            }
          ],
          "refsCollapsed": false,
          "x": 400,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-2-generation-panel/exact-geometry.md"
        },
        {
          "id": "n4j6uv",
          "slug": "controlnet-lane",
          "name": "ControlNet lane",
          "type": "step",
          "summary": "controlnet_sdxl_gen.py — SDXL + lineart ControlNet, geometry-exact",
          "icon": "📐",
          "tags": [
            "generation",
            "controlnet",
            "geometry"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "controlnet-sdxl-gen-py",
              "label": "scripts/controlnet_sdxl_gen.py"
            },
            {
              "target": "fan-out",
              "label": "fan-out"
            }
          ],
          "refsCollapsed": false,
          "x": 660,
          "y": 180,
          "lane": null,
          "link_map": null,
          "gate": "region-IoU ≥ 0.85",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-2-generation-panel/controlnet-lane.md"
        },
        {
          "id": "ns21f0",
          "slug": "subscription-lane",
          "name": "Subscription lane",
          "type": "step",
          "summary": "subgen.py / falgen.py — multi-model candidates",
          "icon": "🎨",
          "tags": [
            "generation",
            "subscription",
            "models"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "subgen-py",
              "label": "scripts/subgen.py"
            },
            {
              "target": "fan-out",
              "label": "fan-out"
            }
          ],
          "refsCollapsed": false,
          "x": 660,
          "y": 420,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-2-generation-panel/subscription-lane.md"
        },
        {
          "id": "nijb53",
          "slug": "fan-out",
          "name": "Fan out",
          "type": "step",
          "summary": "run_matrix.py + falbatch.py — multi-model × multi-prompt × ≥3 attempts/variant",
          "icon": "🔀",
          "tags": [
            "generation",
            "fanout",
            "matrix"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "deterministic-gate",
              "label": "deterministic-gate"
            }
          ],
          "refsCollapsed": false,
          "x": 920,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "≥3 attempts per input variation; spread over one-shot",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-2-generation-panel/fan-out.md"
        },
        {
          "id": "n6681i",
          "slug": "deterministic-gate",
          "name": "Deterministic gate",
          "type": "step",
          "summary": "geom_gate + text_gate — deterministic hard gate, hands to Stage 3",
          "icon": "🚦",
          "tags": [
            "generation",
            "gate",
            "handoff"
          ],
          "status": "draft",
          "refs": [],
          "refsCollapsed": false,
          "x": 1180,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "geom_gate + text_gate pass",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-2-generation-panel/deterministic-gate.md"
        },
        {
          "id": "nk66ob",
          "slug": "subgen-py",
          "name": "subgen.py",
          "type": "reference",
          "summary": "scripts/subgen.py — subscription image gen (OpenAI + Nano Banana)",
          "icon": "🛠️",
          "tags": [
            "tool",
            "script"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "subscription-lane",
              "label": "subscription-lane"
            }
          ],
          "refsCollapsed": false,
          "x": 660,
          "y": 570,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-2-generation-panel/subgen-py.md"
        },
        {
          "id": "n5dk4t",
          "slug": "controlnet-sdxl-gen-py",
          "name": "controlnet_sdxl_gen.py",
          "type": "reference",
          "summary": "scripts/controlnet_sdxl_gen.py — SDXL inpaint + lineart ControlNet, geometry-exact",
          "icon": "🛠️",
          "tags": [
            "tool",
            "script"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "controlnet-lane",
              "label": "controlnet-lane"
            }
          ],
          "refsCollapsed": false,
          "x": 660,
          "y": 30,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-2-generation-panel/controlnet-sdxl-gen-py.md"
        }
      ],
      "edges": [
        {
          "from": "nfunjz",
          "to": "nzbn3n",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nzbn3n",
          "to": "n4j6uv",
          "label": "Yes",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nzbn3n",
          "to": "ns21f0",
          "label": "No",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "n4j6uv",
          "to": "nijb53",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "ns21f0",
          "to": "nijb53",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nijb53",
          "to": "n6681i",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "ns21f0",
          "to": "nk66ob",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "smoothstep"
        },
        {
          "from": "n4j6uv",
          "to": "n5dk4t",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "smoothstep"
        }
      ],
      "frames": []
    },
    "stage-2-generation-skyline": {
      "slug": "stage-2-generation-skyline",
      "id": "mqy62v",
      "title": "Stage 2 — Generation (skyline / multi-panel)",
      "kind": "process",
      "url": "../maps-data/stage-2-generation-skyline/index.md",
      "nodes": [
        {
          "id": "nco1he",
          "slug": "scout",
          "name": "Scout (proof-before-spend)",
          "type": "step",
          "summary": "Generate 2–3 cheap low-res scouts with DISTINCT prompt strategies",
          "icon": "🔭",
          "tags": [
            "generation",
            "scout",
            "skyline"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "subgen-py",
              "label": "scripts/subgen.py"
            },
            {
              "target": "skyline-workflow",
              "label": "docs/skyline-template-illustration-workflow.md"
            },
            {
              "target": "choose-strategy",
              "label": "choose-strategy"
            }
          ],
          "refsCollapsed": false,
          "x": 140,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "scouts show distinct hierarchy; landmarks whole within panels; red zones quiet",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-2-generation-skyline/scout.md"
        },
        {
          "id": "n1tsfu",
          "slug": "choose-strategy",
          "name": "Which scout reads best?",
          "type": "decision",
          "summary": "Pick the one scout strategy whose hierarchy + route reads best",
          "icon": "🧭",
          "tags": [
            "decision",
            "scout",
            "skyline"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "scout",
              "label": "scout"
            },
            {
              "target": "polish",
              "label": "polish"
            }
          ],
          "refsCollapsed": false,
          "x": 400,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-2-generation-skyline/choose-strategy.md"
        },
        {
          "id": "nlrn41",
          "slug": "polish",
          "name": "Polish chosen strategy",
          "type": "step",
          "summary": "Full-res, ≥3 attempts of the chosen strategy, references + geometry guide fed",
          "icon": "🎨",
          "tags": [
            "generation",
            "polish",
            "skyline"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "choose-strategy",
              "label": "choose-strategy"
            },
            {
              "target": "subgen-py",
              "label": "scripts/subgen.py"
            },
            {
              "target": "overlay-check",
              "label": "overlay-check"
            }
          ],
          "refsCollapsed": false,
          "x": 660,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "≥3 attempts of the chosen strategy",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-2-generation-skyline/polish.md"
        },
        {
          "id": "nwtke1",
          "slug": "overlay-check",
          "name": "Overlay geometry check (gate)",
          "type": "step",
          "summary": "scripts/skyline_panel.py check — overlay the real SVG and measure",
          "icon": "📐",
          "tags": [
            "gate",
            "geometry",
            "skyline"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "polish",
              "label": "polish"
            },
            {
              "target": "skyline-workflow",
              "label": "docs/skyline-template-illustration-workflow.md"
            }
          ],
          "refsCollapsed": false,
          "x": 920,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "panels whole within boundaries; red zones contain only quiet/infrastructure",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-2-generation-skyline/overlay-check.md"
        },
        {
          "id": "nmyevj",
          "slug": "subgen-py",
          "name": "subgen.py",
          "type": "reference",
          "summary": "scripts/subgen.py — subscription image gen (OpenAI + Nano Banana), the single gen path",
          "icon": "🛠️",
          "tags": [
            "tool",
            "script"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "scout",
              "label": "scout"
            },
            {
              "target": "polish",
              "label": "polish"
            },
            {
              "target": "skyline-workflow",
              "label": "docs/skyline-template-illustration-workflow.md"
            }
          ],
          "refsCollapsed": false,
          "x": 660,
          "y": 450,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-2-generation-skyline/subgen-py.md"
        },
        {
          "id": "ngeboc",
          "slug": "skyline-workflow",
          "name": "skyline workflow",
          "type": "reference",
          "summary": "docs/skyline-template-illustration-workflow.md — skyline generation source of truth",
          "icon": "📄",
          "tags": [
            "doc",
            "workflow",
            "skyline"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "scout",
              "label": "scout"
            },
            {
              "target": "choose-strategy",
              "label": "choose-strategy"
            },
            {
              "target": "polish",
              "label": "polish"
            },
            {
              "target": "overlay-check",
              "label": "overlay-check"
            },
            {
              "target": "subgen-py",
              "label": "scripts/subgen.py"
            }
          ],
          "refsCollapsed": false,
          "x": 140,
          "y": 450,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-2-generation-skyline/skyline-workflow.md"
        }
      ],
      "edges": [
        {
          "from": "nco1he",
          "to": "n1tsfu",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "n1tsfu",
          "to": "nlrn41",
          "label": "best scout",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nlrn41",
          "to": "nwtke1",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nco1he",
          "to": "ngeboc",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "smoothstep"
        },
        {
          "from": "nlrn41",
          "to": "nmyevj",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "smoothstep"
        }
      ],
      "frames": []
    },
    "stage-3-select": {
      "slug": "stage-3-select",
      "id": "mbnlo7",
      "title": "Stage 3 — Select / Gate",
      "kind": "process",
      "url": "../maps-data/stage-3-select/index.md",
      "nodes": [
        {
          "id": "ndqnns",
          "slug": "deterministic-gates",
          "name": "Deterministic gates",
          "type": "step",
          "summary": "Hard machine gates: geom_gate + text_gate before any human or vision spend",
          "icon": "📏",
          "tags": [
            "gate",
            "deterministic",
            "geometry",
            "text"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "pass",
              "label": "pass"
            }
          ],
          "refsCollapsed": false,
          "x": 140,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "region-IoU≥0.85 (template) OR outside-mask delta==0 (edit); text-gate clean",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-3-select/deterministic-gates.md"
        },
        {
          "id": "ntmgsn",
          "slug": "pass",
          "name": "Deterministic gates pass?",
          "type": "decision",
          "summary": "Branch on whether a candidate cleared the deterministic hard-gates",
          "icon": "❓",
          "tags": [
            "decision",
            "gate"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "deterministic-gates",
              "label": "deterministic-gates"
            },
            {
              "target": "back-to-generation",
              "label": "back-to-generation"
            },
            {
              "target": "vision-judge",
              "label": "vision-judge"
            }
          ],
          "refsCollapsed": false,
          "x": 400,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-3-select/pass.md"
        },
        {
          "id": "n371rw",
          "slug": "back-to-generation",
          "name": "Back to generation",
          "type": "step",
          "summary": "Failed candidates return to Stage 2 to regenerate",
          "icon": "↩️",
          "tags": [
            "reject",
            "regenerate"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "pass",
              "label": "pass"
            }
          ],
          "refsCollapsed": false,
          "x": 400,
          "y": 180,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-3-select/back-to-generation.md"
        },
        {
          "id": "nd7j6t",
          "slug": "vision-judge",
          "name": "Vision judge",
          "type": "step",
          "summary": "≥3 VLM judges over the SVG overlay + duplicate count on whole-panel context",
          "icon": "👁️",
          "tags": [
            "judge",
            "vision",
            "vlm"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "judge-py",
              "label": "scripts/judge.py"
            },
            {
              "target": "result-vision-judge-skill",
              "label": "skills/result-vision-judge"
            },
            {
              "target": "build-board",
              "label": "build-board"
            }
          ],
          "refsCollapsed": false,
          "x": 660,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "≥3 judges; judged on the overlay, not the metric alone",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-3-select/vision-judge.md"
        },
        {
          "id": "nibedt",
          "slug": "build-board",
          "name": "Build comparison board",
          "type": "step",
          "summary": "style_board.py: full-size side-by-side of ALL candidates (never low-res)",
          "icon": "🖼️",
          "tags": [
            "board",
            "review",
            "fullsize"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "human-pick",
              "label": "human-pick"
            }
          ],
          "refsCollapsed": false,
          "x": 920,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "ALL candidates shown at full size (never a low-res board)",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-3-select/build-board.md"
        },
        {
          "id": "nckchw",
          "slug": "human-pick",
          "name": "Human pick (gate)",
          "type": "step",
          "summary": "User picks the winner from the full-size board",
          "icon": "🛂",
          "tags": [
            "gate",
            "human",
            "pick"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "build-board",
              "label": "build-board"
            }
          ],
          "refsCollapsed": false,
          "x": 1180,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "user picks the winner from the full-size board",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-3-select/human-pick.md"
        },
        {
          "id": "n8x7vw",
          "slug": "judge-py",
          "name": "judge.py",
          "type": "reference",
          "summary": "scripts/judge.py — VLM judge over the SVG overlay; ≥3 judges, hi-DPI crops",
          "icon": "🛠️",
          "tags": [
            "tool",
            "script",
            "judge"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "vision-judge",
              "label": "vision-judge"
            },
            {
              "target": "result-vision-judge-skill",
              "label": "skills/result-vision-judge"
            }
          ],
          "refsCollapsed": false,
          "x": 660,
          "y": 450,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-3-select/judge-py.md"
        },
        {
          "id": "nyt5xa",
          "slug": "result-vision-judge-skill",
          "name": "result-vision-judge skill",
          "type": "reference",
          "summary": "skills/result-vision-judge — SOP: judge vision + geometry together, never one alone",
          "icon": "📚",
          "tags": [
            "skill",
            "judge",
            "sop"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "vision-judge",
              "label": "vision-judge"
            },
            {
              "target": "judge-py",
              "label": "scripts/judge.py"
            }
          ],
          "refsCollapsed": false,
          "x": 660,
          "y": 600,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-3-select/result-vision-judge-skill.md"
        }
      ],
      "edges": [
        {
          "from": "ndqnns",
          "to": "ntmgsn",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "ntmgsn",
          "to": "n371rw",
          "label": "No",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "ntmgsn",
          "to": "nd7j6t",
          "label": "Yes",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nd7j6t",
          "to": "nibedt",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nibedt",
          "to": "nckchw",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nd7j6t",
          "to": "n8x7vw",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "smoothstep"
        },
        {
          "from": "nd7j6t",
          "to": "nyt5xa",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "smoothstep"
        }
      ],
      "frames": []
    },
    "stage-4-repair": {
      "slug": "stage-4-repair",
      "id": "mn7bij",
      "title": "Stage 4 — Repair / Refine",
      "kind": "process",
      "url": "../maps-data/stage-4-repair/index.md",
      "nodes": [
        {
          "id": "nktq35",
          "slug": "diagnose-defect",
          "name": "Diagnose defect",
          "type": "step",
          "summary": "Classify the defect so the right repair engine is chosen",
          "icon": "🩺",
          "tags": [
            "repair",
            "triage"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "edit-py",
              "label": "scripts/edit.py"
            },
            {
              "target": "route-engine",
              "label": "route to the engine"
            }
          ],
          "refsCollapsed": false,
          "x": 140,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-4-repair/diagnose-defect.md"
        },
        {
          "id": "nsbr6x",
          "slug": "route-engine",
          "name": "Route engine",
          "type": "decision",
          "summary": "Branch to the repair engine that matches the operation",
          "icon": "🔀",
          "tags": [
            "repair",
            "routing",
            "gate"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "use-eraser",
              "label": "Bria eraser"
            },
            {
              "target": "flux-fill",
              "label": "Flux Fill"
            },
            {
              "target": "donor",
              "label": "mask-bounded external redraw donor"
            },
            {
              "target": "sharpen",
              "label": "adaptive sharpen / reupscale"
            }
          ],
          "refsCollapsed": false,
          "x": 400,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-4-repair/route-engine.md"
        },
        {
          "id": "nvtuvv",
          "slug": "use-eraser",
          "name": "Use eraser",
          "type": "step",
          "summary": "Bria eraser removes an element and reconstructs the background in-style",
          "icon": "🧽",
          "tags": [
            "repair",
            "remove",
            "eraser"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "mask",
              "label": "auto-mask + guardrail"
            }
          ],
          "refsCollapsed": false,
          "x": 660,
          "y": 180,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-4-repair/use-eraser.md"
        },
        {
          "id": "nlbq6c",
          "slug": "flux-fill",
          "name": "Flux Fill",
          "type": "step",
          "summary": "Flux Fill masked inpaint to redraw one element in place",
          "icon": "🖌️",
          "tags": [
            "repair",
            "redraw",
            "inpaint"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "mask",
              "label": "auto-mask + guardrail"
            }
          ],
          "refsCollapsed": false,
          "x": 660,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-4-repair/flux-fill.md"
        },
        {
          "id": "npr53s",
          "slug": "donor",
          "name": "Donor (external redraw)",
          "type": "step",
          "summary": "Mask-bounded external redraw donor for broad ghost/haze/occlusion in a busy scene",
          "icon": "👻",
          "tags": [
            "repair",
            "ghost",
            "donor"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "mask-bounded-donor",
              "label": "the mask-bounded donor concept"
            },
            {
              "target": "mask",
              "label": "auto-mask + guardrail"
            }
          ],
          "refsCollapsed": false,
          "x": 660,
          "y": 420,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-4-repair/donor.md"
        },
        {
          "id": "n2mop1",
          "slug": "sharpen",
          "name": "Sharpen",
          "type": "step",
          "summary": "Adaptive sharpen / reupscale to fix blur and melt",
          "icon": "🔪",
          "tags": [
            "repair",
            "blur",
            "sharpen",
            "upscale"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "composite",
              "label": "composite"
            }
          ],
          "refsCollapsed": false,
          "x": 660,
          "y": 540,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-4-repair/sharpen.md"
        },
        {
          "id": "n291gl",
          "slug": "mask",
          "name": "Mask + guardrail",
          "type": "step",
          "summary": "Auto-mask the target, then guardrail it before any spend",
          "icon": "🎯",
          "tags": [
            "repair",
            "mask",
            "gate"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "composite",
              "label": "composite"
            }
          ],
          "refsCollapsed": false,
          "x": 920,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "mask contains target, no leak (mask_check exit 0)",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-4-repair/mask.md"
        },
        {
          "id": "nogil7",
          "slug": "composite",
          "name": "Composite",
          "type": "step",
          "summary": "Diff-mask composite — blend the edit back, keep the rest byte-exact",
          "icon": "🧩",
          "tags": [
            "repair",
            "composite",
            "gate"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "verify",
              "label": "verify"
            }
          ],
          "refsCollapsed": false,
          "x": 1180,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "outside-mask pixel delta == 0",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-4-repair/composite.md"
        },
        {
          "id": "nm42po",
          "slug": "verify",
          "name": "Verify",
          "type": "step",
          "summary": "Measured gate — delta, leak, vision judge, human accept",
          "icon": "✅",
          "tags": [
            "repair",
            "verify",
            "gate"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "open-problems",
              "label": "open problems"
            }
          ],
          "refsCollapsed": false,
          "x": 1440,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "outside delta==0; leak_metric<0.06; vision judge; user accepts",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-4-repair/verify.md"
        },
        {
          "id": "nnbjj3",
          "slug": "edit-py",
          "name": "edit.py",
          "type": "reference",
          "summary": "Tool: one-command self-healing edit dispatcher",
          "icon": "🛠️",
          "tags": [
            "tool",
            "repair"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "diagnose-defect",
              "label": "diagnose"
            },
            {
              "target": "mask",
              "label": "mask"
            },
            {
              "target": "composite",
              "label": "composite"
            },
            {
              "target": "verify",
              "label": "verify"
            }
          ],
          "refsCollapsed": false,
          "x": 140,
          "y": 450,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-4-repair/edit-py.md"
        },
        {
          "id": "n97dj2",
          "slug": "mask-bounded-donor",
          "name": "Mask-bounded donor",
          "type": "reference",
          "summary": "Concept: external redraw donor with separate generation- and blend-masks",
          "icon": "📄",
          "tags": [
            "concept",
            "donor",
            "repair"
          ],
          "status": "draft",
          "refs": [
            {
              "target": "donor",
              "label": "donor"
            }
          ],
          "refsCollapsed": false,
          "x": 660,
          "y": 570,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-4-repair/mask-bounded-donor.md"
        },
        {
          "id": "ne0z88",
          "slug": "open-problems",
          "name": "OPEN PROBLEMS",
          "type": "reference",
          "summary": "What is STILL open in Stage 4 repair, with active pilots",
          "icon": "🚧",
          "tags": [
            "open-problem",
            "repair"
          ],
          "status": "blocked",
          "refs": [
            {
              "target": "verify",
              "label": "verify"
            }
          ],
          "refsCollapsed": false,
          "x": 1440,
          "y": 450,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-4-repair/open-problems.md"
        }
      ],
      "edges": [
        {
          "from": "nktq35",
          "to": "nsbr6x",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nsbr6x",
          "to": "nvtuvv",
          "label": "remove",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nsbr6x",
          "to": "nlbq6c",
          "label": "redraw",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nsbr6x",
          "to": "npr53s",
          "label": "ghost",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nsbr6x",
          "to": "n2mop1",
          "label": "blur",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nvtuvv",
          "to": "n291gl",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nlbq6c",
          "to": "n291gl",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "npr53s",
          "to": "n291gl",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "n291gl",
          "to": "nogil7",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "n2mop1",
          "to": "nogil7",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nogil7",
          "to": "nm42po",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nktq35",
          "to": "nnbjj3",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "smoothstep"
        },
        {
          "from": "npr53s",
          "to": "n97dj2",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "smoothstep"
        },
        {
          "from": "nm42po",
          "to": "ne0z88",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "smoothstep"
        }
      ],
      "frames": []
    },
    "stage-5-export": {
      "slug": "stage-5-export",
      "id": "momj93",
      "title": "Stage 5 — Finalize / Export",
      "kind": "process",
      "url": "../maps-data/stage-5-export/index.md",
      "nodes": [
        {
          "id": "nz0h0d",
          "slug": "keep-raw",
          "name": "keep-raw",
          "type": "step",
          "summary": "bank the approved raw first",
          "icon": null,
          "tags": [],
          "status": "draft",
          "refs": [
            {
              "target": "law-never-ruin-raw",
              "label": "the law"
            }
          ],
          "refsCollapsed": false,
          "x": 140,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "approved raw checkpointed before any composite",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-5-export/keep-raw.md"
        },
        {
          "id": "n2vfkn",
          "slug": "composite-to-template",
          "name": "composite-to-template",
          "type": "step",
          "summary": "clip artwork into SVG paths at exact coords",
          "icon": null,
          "tags": [],
          "status": "draft",
          "refs": [
            {
              "target": "export-fit-py",
              "label": "the tool"
            }
          ],
          "refsCollapsed": false,
          "x": 400,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "0 painted pixels outside template / cutout masks",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-5-export/composite-to-template.md"
        },
        {
          "id": "nl74mz",
          "slug": "raw-vs-exact",
          "name": "raw-vs-exact?",
          "type": "decision",
          "summary": "does the exact composite degrade the raw?",
          "icon": null,
          "tags": [],
          "status": "draft",
          "refs": [
            {
              "target": "deliver-raw",
              "label": "deliver the raw"
            },
            {
              "target": "deliver-composite",
              "label": "deliver the composite"
            }
          ],
          "refsCollapsed": false,
          "x": 660,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-5-export/raw-vs-exact.md"
        },
        {
          "id": "nfuuu0",
          "slug": "deliver-raw",
          "name": "deliver-raw",
          "type": "step",
          "summary": "keep raw as deliverable (composite would ruin it)",
          "icon": null,
          "tags": [],
          "status": "draft",
          "refs": [
            {
              "target": "register",
              "label": "register"
            }
          ],
          "refsCollapsed": false,
          "x": 920,
          "y": 180,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-5-export/deliver-raw.md"
        },
        {
          "id": "n9x2p9",
          "slug": "deliver-composite",
          "name": "deliver-composite",
          "type": "step",
          "summary": "use the exact composite",
          "icon": null,
          "tags": [],
          "status": "draft",
          "refs": [
            {
              "target": "register",
              "label": "register"
            }
          ],
          "refsCollapsed": false,
          "x": 920,
          "y": 420,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-5-export/deliver-composite.md"
        },
        {
          "id": "njhdzs",
          "slug": "register",
          "name": "register",
          "type": "step",
          "summary": "record result + reconcile from disk",
          "icon": null,
          "tags": [],
          "status": "draft",
          "refs": [],
          "refsCollapsed": false,
          "x": 1180,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "result row recorded",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-5-export/register.md"
        },
        {
          "id": "nftg1i",
          "slug": "sync-library",
          "name": "sync-library",
          "type": "step",
          "summary": "sync every result image",
          "icon": null,
          "tags": [],
          "status": "draft",
          "refs": [],
          "refsCollapsed": false,
          "x": 1440,
          "y": 300,
          "lane": null,
          "link_map": null,
          "gate": "ALL result images (raw+exact+overlays) synced to central library",
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-5-export/sync-library.md"
        },
        {
          "id": "nl6biz",
          "slug": "export-fit-py",
          "name": "scripts/export_svg_template_fit.py",
          "type": "reference",
          "summary": "clip artwork into SVG template + verify fit",
          "icon": null,
          "tags": [],
          "status": "draft",
          "refs": [],
          "refsCollapsed": false,
          "x": 400,
          "y": 450,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-5-export/export-fit-py.md"
        },
        {
          "id": "nd6e86",
          "slug": "law-never-ruin-raw",
          "name": "LAW: never ruin a good raw",
          "type": "reference",
          "summary": "keep best-so-far raw; composite is last resort",
          "icon": null,
          "tags": [],
          "status": "draft",
          "refs": [],
          "refsCollapsed": false,
          "x": 140,
          "y": 450,
          "lane": null,
          "link_map": null,
          "gate": null,
          "scale": 1,
          "hl": false,
          "color": null,
          "url": "../maps-data/stage-5-export/law-never-ruin-raw.md"
        }
      ],
      "edges": [
        {
          "from": "nz0h0d",
          "to": "n2vfkn",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "n2vfkn",
          "to": "nl74mz",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nl74mz",
          "to": "nfuuu0",
          "label": "Yes",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nl74mz",
          "to": "n9x2p9",
          "label": "No",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nfuuu0",
          "to": "njhdzs",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "n9x2p9",
          "to": "njhdzs",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "njhdzs",
          "to": "nftg1i",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "bezier"
        },
        {
          "from": "nz0h0d",
          "to": "nd6e86",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "smoothstep"
        },
        {
          "from": "n2vfkn",
          "to": "nl6biz",
          "label": "",
          "bend": 0,
          "color": null,
          "route": "smoothstep"
        }
      ],
      "frames": []
    }
  },
  "issues": []
};
