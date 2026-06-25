---
nid: mv60tf
title: "Stage 1a — References → Style Packet"
type: map
kind: process
nodes:
  - gather-references
  - build-packet
  - inspect-packet
  - re-curate
  - packet-approved
  - build-reference-style-packet-py
  - law-reference-beats-prose
edges:
  - {from: gather-references, to: build-packet, label: ""}
  - {from: build-packet, to: inspect-packet, label: ""}
  - {from: inspect-packet, to: re-curate, label: "No"}
  - {from: re-curate, to: build-packet, label: ""}
  - {from: inspect-packet, to: packet-approved, label: "Yes"}
  - {from: gather-references, to: law-reference-beats-prose, label: "", route: smoothstep}
  - {from: build-packet, to: build-reference-style-packet-py, label: "", route: smoothstep}
---
# Stage 1a — References → Style Packet

Turn raw reference images into **attachable visual evidence** — contact + exemplar
sheets that an image-generation agent feeds to the model alongside the prompt. This
realizes core law 1 (reference beats prose): style is carried by IMAGES, not by a
written description. Runs in almost every task family.

Flow: [[gather-references|gather references]] into the task's `refs/`, then
[[build-packet|build the packet]] with [[build-reference-style-packet-py|build_reference_style_packet.py]].
A human [[inspect-packet|inspects]] whether the packet captured the *real* art style
(object vocabulary, line weight, density, lighting, material — not just palette). If
not, [[re-curate|re-curate]] the refs and rebuild; once it does,
[[packet-approved|the packet is approved]] and feeds Stage 2.

Governing law: [[law-reference-beats-prose|reference beats prose]] (`docs/PIPELINE.md`).
