---
nid: nfzhkv
title: "Gather references"
type: step
x: 140
y: 300
icon: "🖼️"
summary: "Collect reference images into the task's refs/"
status: draft
tags: [style-packet, references]
---
# Gather references

Collect the reference images that anchor the target art style and drop them into the
task's `refs/` directory (`tasks/<task>/refs/`). These are the raw visual evidence the
whole pipeline leans on — under core law 1, generation is driven by reference IMAGES,
not by a written style description, so this is where that anchor is assembled.

Curate deliberately: pick refs that together show the object vocabulary, line weight,
density, lighting, and material of the intended style — not just a color palette. A thin
or palette-only ref set is the most common cause of a packet that later fails inspection.

Feeds [[build-packet|build-packet]]. Governed by [[law-reference-beats-prose|reference beats prose]].
