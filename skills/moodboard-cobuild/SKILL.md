---
name: moodboard-cobuild
description: "Co-build a collection's STYLE BIBLE with the user: harvest exemplars from existing assets, compose an axis-by-axis choice board (medium/palette/illustration-style required, plus COMPLETE-BUILDING and GEOMETRY-EMBRACE), run forced-choice verdicts, lock bible v1 with a style handle (medium_ref/palette_ref/style_ref), then validate uncertain axes with one cheap probe-tile round. Use at collection intake or whenever style ground truth is unset/disputed."
status: proposed
effort: medium
---

# moodboard-cobuild — style ground truth WITH the user, not for them

Born from the Marriott record: 15 rounds oscillated (felt→glossy→anemic) because style
was assumed from references instead of locked with the user. The one spec-driven round
(r16) beat all 15 (ledger S54). This skill front-loads the user's taste into a locked,
versioned bible BEFORE panel spend.

## The loop (zero-spend first, generative only for what's still uncertain)

1. **HARVEST (agent, zero spend).** From existing assets only — collection refs, prior
   rounds (approved AND rejected), sibling collections' approved finals — cut labeled
   crops per style axis: medium, finish, palette, line, shape language, detail density,
   texture, light. Every crop keeps its provenance path. Rejected-round crops are
   harvested too — they become anti-examples and calibration bads.
2. **BOARD v0 (compose, zero spend).** One ROW per axis; per row 2–4 crop options
   labeled A/B/C + one "none of these" slot. Options must ACTUALLY differ on that axis
   and be as-alike-as-possible on others (else the choice measures two things).
   Roles annotated on the board itself (architecture / medium / palette / content /
   anti) — the r15 lesson rides on the artifact, not in prose.
3. **FORCED-CHOICE PASS (user, ~2 min).** Verdict form (scripts/verdict_form.py):
   per axis "A/B/C/none + one optional word", plus sliders (literal↔abstract,
   muted↔saturated, simple↔detailed, matte↔glossy), plus mood words keep/kill.
   Never free-prose-only; never more than ~8 questions.
4. **BIBLE DRAFT (agent).** Answers → bible-v1.yaml fields (schemas/style-bible.schema.json,
   bible_lint clean). Unanswered axes = my best inference, marked `confidence: low`.
5. **PROBE TILES (generative, ~$1–2, ONLY low-confidence axes).** For each uncertain
   axis: 2 small tiles (≤512px) varying that axis alone, generated with the draft bible's
   refs-by-role. A/B verdict per pair → axis locked, confidence raised.
6. **LOCK + VERSION.** bible v1 committed; the board JPG goes to REVIEW/<task>/ with the
   filled verdict form beside it. Later corrections arrive as verdict-form entries →
   bible_version += 1. The bible is the ONLY style source prompts compile from.

## Hard rules
- Style refs are IMAGE inputs with ONE role each; prose never anchors style (LAW 0).
- The target panel's OWN prior art is never its style ref (hold-out rule).
- Anti-examples appear ON the board with reason labels — the user confirms the
  rejections too (a drift class dies only when its exemplar is officially anti).
- Board crops are text-free / frame-free / substrate-free (Rule 0: dirty crops teach
  text and felt).
- **REQUIRED axes, always on the board.** medium, palette, and illustration-style are
  not optional rows among many — every board carries all three, forced-choice, before
  bible draft. Each locked axis compiles to its OWN reference-image slot in a style
  handle: `medium_ref`, `palette_ref`, `style_ref`. These are separate FILES fed to
  models one role at a time (LAW 0 — never merged, never described in prose); the
  contact sheet that lays medium/palette/style crops side by side is for HUMAN review
  only and is never itself a model input.
- **COMPLETE-BUILDING axis.** Every panel reads as one COMPLETE, intentional building,
  never a cropped fragment — slight detail overhang past the silhouette is a plus,
  a hard flat-cut edge is a fail. Board and verdict form carry this as its own
  forced choice, not folded into shape language.
- **GEOMETRY-EMBRACE axis.** Cutouts are integrated features, not tolerated holes:
  each gets a painted frame around a clean, unpainted void, drawn with solid strokes
  only (dashed guide lines leak into finals as painted dots — never dashes in any
  guide or board asset); the outer silhouette gets its own rim treatment so the
  die-cut edge reads as designed, not as a crop.
- **User-gating: VISUAL only.** The user reviews boards, diagrams, and rendered
  results — never raw YAML/spec text. Any axis still open when a round ships gets
  the agent's own best default (marked `confidence: low` per step 4), and that
  default is validated on the NEXT visual round, not by asking the user to read spec.

## B1 — SCENE BRAINSTORM (runs BEFORE the board; 2026-07-05, user brief + R1 prior art)

Features are DECIDED here, cheaply, not repaired later (every late correction on
record — extra crosses, boring details, vetoed awning — was a feature never
deliberately chosen). Per COLLECTION (mini-pass per panel type when roles differ,
e.g. narrows = independent buildings):
1. FEATURE MENU (~25–35, text, zero spend) from three generators: (a) TRANSPOSE the
   family's toy DNA (police siren → hospital cross-beacon; watchtower → nurse-lookout
   dome) — exaggerate role-signifiers, never add realism; (b) the theme's own
   signifiers; (c) mini-narratives / kid-findables (open-ended story hooks, no plot,
   no text). SCAMPER pass on must-haves (magnify / combine / simplify / rearrange) +
   ≤1 forced-association wildcard. Refuse the obvious first batch.
2. USER = DECIDER, always: M/N/X inline per feature + own additions + density slider.
   Agent proposes, user disposes (note-and-vote shape, ~5 min).
3. LAYOUT ROUTES: agent names 3–4 composition routes (e.g. SIREN_ROOF /
   BADGE_FACADE / GARAGE_PLAYSET / STORYBOOK_CIVIC); user picks primary + backup.
4. TOP-CONTOUR ROUTES: agent names 3–4 architectural top shapes that fill the
   template's top bound — dome is the default, tower/gable/turret are variations.
   The bound is a fill target, not a mandate (no sky fill); user picks primary + backup
   alongside the layout route.
5. BUILDABILITY GATE: demote anything too tiny / text-dependent / realism-dependent /
   cutout-conflicting; user may rescue ONE by making it bigger/simpler.

## B3 — FEATURE CALLOUT SHEET (the bridge to geometry)

After the board locks: one YAML row per accepted feature —
  {feature_id, name, why_toy_like, role_signifier, signature_exaggeration,
   style_reference_target, feature_refs, zone_bbox_frac, relative_size, layer, count,
   must|nice, open_ended_story_hook, avoid, geometry_notes}
plus a rendered human diagram: labeled feature boxes ON the v3 panel contour with
forbidden stripes visible (placement respects keep-clear by construction).
`feature_refs` are IMAGE inputs depicting the feature in its TARGET in-panel
state/pose (a cross-beacon lit and mounted, not a generic catalog shot) — same
LAW 0 discipline as the style handle: reference over description.
Budget: ≤3 MUST per panel (geometry protects these first), 2–4 supporting,
1–2 story details, ≥1 negative callout. Compiles into: prompt clauses ordered by
zone; emblem_gate allowed_zones + motif cards; the rough-gate checklist.

## Outputs
- REVIEW/<task>/FEATURE-MENU-<theme>.md (B1 menu; user marks M/N/X inline)
- REVIEW/<task>/MOOD-BOARD-v<N>.jpg (axis rows + CHOSEN-features row, labeled)
- REVIEW/<task>/VERDICT-moodboard-v<N>.md (generated form; user fills inline)
- tasks/<task>/style-spec/bible-v<N>.yaml (lint-clean)
- tasks/<task>/style-spec/feature-callouts-v<N>.yaml + annotated diagram (B3)
