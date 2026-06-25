---
nid: na5ug8
title: "All references exist?"
type: decision
x: 920
y: 300
icon: "❓"
summary: "Branch on whether every needed reference is present"
status: draft
tags: [decision, references]
---
# All references exist?

Branch on the inventory verdict from [[inventory-refs|inventory-refs]].

- **No** — at least one needed reference is missing → go generate it first at
  [[generate-missing-ref|generate-missing-ref]] (precursor, stage 1c). This realizes
  law 0: a missing reference is generated, never substituted with prose.
- **Yes** — every needed reference is present → straight to
  [[emit-packet|emit-packet]].

Both branches converge on emit-packet so the plan is always written.
