# Maps dashboard — UI/UX build plan (51 items)

GOAL: Implement all 51 curated UI/UX improvements (from the research sweep) into the
process-maps dashboard, correctly, in dependency order, each verified in the live preview,
with ZERO new runtime dependencies, without breaking existing behaviour or corrupting node
positions/data.

Method: foundation built centrally in the main loop; leaf clusters authored in parallel by a
fleet (read-only against live files) and deconflicted into one ordered change-set; integrated
batch-by-batch in the main loop with preview verification after each batch.

Hard constraints (inline into every agent brief — hooks don't fire in subagents):
- Zero new deps. Vanilla JS + D3 v7 + CSS only. d3 already vendored.
- `prompt()` THROWS in the sandboxed preview iframe; `confirm()` auto-true; `alert()` no-op.
  Use the inline `showNameInput` overlay for text entry.
- NEVER reset deliberate node x/y. No synthetic drags that write positions.
- `render()` CLEARS gNode/gEdge/gLane/gFrame every frame and rebuilds via .data().enter().
  So: animations must be CSS-driven, enter-once (guarded by `seen` Set), or live in the
  never-cleared `gWire` layer. Persistent per-node state (selected, grabbing) is re-applied
  each render from a module-level Set/var.
- build.js is the SOLE producer of maps/data.js from maps-data/*.md. Any data-shape change
  goes in build.js; serve.js mutates the .md, shells out to build.js, re-reads data.js.
- Respect reduced-motion: gate every new animation behind reduceMotion()/calm-mode.

Foundation API (built first, in main loop; leaves target this):
- `selection` : Set<nodeId>. Helpers: `selectClick(evt,id)` (shift/meta toggles, else replace),
  `clearSelection()`. Selected nodes render a `.selring` (offset accent ring), distinct from
  hover (transform lift) and `.hl` (semantic glow).
- Design tokens in :root: `--e1/--e2/--e3` (elevation), `--dur-1/--dur-2`, `--s1..--s4`
  (spacing), `--fs-1..--fs-5` (type scale). New code uses these.

## Sequence (4 phases)

### Phase 0 — Foundation (main loop) — DONE + preview-verified
- [x] F1 Design tokens (elevation/easing/spacing/type-scale CSS vars)
- [x] F2 Selection model (Set + selectClick/clearSelection + Esc/empty-canvas clear)
- [x] F3 Distinct selected-state ring (.selring) — verified: single-click rings 1, shift-click extends, per-node accent

### Phase 1 — Trust + foundation leaves
- [ ] 1 Persistent clickable breadcrumb
- [ ] 2 Live / read-only connection banner
- [ ] 3 Undo snackbar + redo
- [ ] 4 Drag port to empty canvas → create+connect
- [ ] 5 Branch labels (Yes/No) on decision edges

### Phase 2 — Editing spine
- [ ] 6 Marquee multi-select
- [ ] 7 Keyboard ops (delete/duplicate/select-all/nudge/esc)
- [ ] 8 Contextual floating mini-toolbar
- [ ] 9 Align & distribute on selection
- [ ] 10 Alignment helper lines + snap-on-drag
- [ ] 11 Copy / paste across maps
- [ ] 12 Node resize handle (drag corner)
- [ ] 13 First-run empty-state affordance

### Phase 3 — Process legibility + knowledge
- [ ] 14 BPMN terminal rings (start/end)
- [ ] 15 Color-redundant semantics (glyph not hue)
- [ ] 16 Context-menu sectioning + Archive-last
- [ ] 17 Validation lint panel
- [ ] 18 Hover-preview a SoT ghost
- [ ] 19 Reverse backlinks ("cited by N")
- [ ] 20 Inline [[ citation autocomplete
- [ ] 21 Broken-citation repair panel
- [ ] 22 Hover-revealed ports + valid/invalid coloring
- [ ] 23 Magnetic connect (target arms + snaps)
- [ ] 24 Smoothstep orthogonal edge routing
- [ ] 25 Self-loop arcs + draggable waypoints

### Phase 4 — Polish, command, navigation, reach
- [ ] 26 Quantized type scale + secondary de-emphasis (adopts F1)
- [ ] 27 Tonal-fill grouping (drop redundant dashed)
- [ ] 28 Cmd+K command palette
- [ ] 29 Fuzzy matcher (rank + highlight)
- [ ] 30 Shortcut cheat-sheet on ?
- [ ] 31 Coachmark on drag-from-port
- [ ] 32 Cmd+F find-and-fly to any node
- [ ] 33 Zoom HUD (% + fit/100%/zoom-to-selection)
- [ ] 34 Minimap + draggable viewport rect
- [ ] 35 Multi-map Home overview
- [ ] 36 Immersive drill (double-click zoom-in vs PiP)
- [ ] 37 Zoom-aware level-of-detail
- [ ] 38 State-change pulse-once on edits
- [ ] 39 Hover-intent debounce
- [ ] 40 Spring easing via CSS linear() for one-shot reveals
- [ ] 41 True spring physics (drag-release / connect-snap)
- [ ] 42 Container-transform PiP open/close
- [ ] 43 FLIP-animated auto-tidy
- [ ] 44 Radial / marking menu (long-press)
- [ ] 45 Reduced-motion / calm-mode audit
- [ ] 46 A11y pass (ARIA roles, focusable nodes, live region, focus-trapped dialogs)
- [ ] 47 Touch / pointer parity (long-press menu, tap ports, pinch-zoom)
- [ ] 48 Viewport culling + SSE/render throttle
- [ ] 49 Save-conflict guard for the open notes drawer

(51 = 3 foundation + 5 + 8 + 12 + 23. Items renumbered here by build order.)

## Integration log (main-loop, preview-verified per batch)

Master plan = 9 deconflicted batches (fleet output w6a3wlw6j). Status:
- [x] Foundation F1–F3 — tokens, selection model, selection ring. VERIFIED.
- [x] **Batch 1** (shared foundations): 1 breadcrumb · 26 type-scale (light pass) · 27 tonal fills ·
      29 fuzzy matcher · 45 calm-mode/motionAllowed · 46 a11y (svg role, live region, focusable
      nodes, dialog roles, focus-trap). VERIFIED: no console errors; breadcrumb "⌂ Home › Layers";
      calm halts body drift (drift→none→drift); nodes tabindex+aria; dialogs role=dialog.
- [x] **Batch 2** (conn-status chip + SSE throttle + viewport culling) — 2, 48. VERIFIED: "● Live"
      chip renders; SSE coalesced (80ms debounce); cull predicate proven (visible@origin, culled@+5000,
      restored); zoom handler now re-renders so culling re-applies on pan. No errors.
- [x] **Batch 3** (zoom HUD + minimap + LOD) — 33, 34, 37. VERIFIED: HUD live % (wheel→152%/29%),
      LOD toggles `lod-far` at k<0.55, minimap renders node rects + draggable viewport rect.
      TWO BUGS CAUGHT + FIXED: (a) the new minimap `<svg>` became the FIRST svg so `d3.select('svg')`
      grabbed it (main canvas blank) — fixed by id-ing the main svg `#map-svg` + scoping its CSS/selection;
      (b) per-tick `scheduleRender()` in the zoom handler stormed render and fought programmatic zoom
      transitions (fit/zoomTo) → moved reculling to the zoom `'end'` event. NOTE: rAF transitions don't
      tick in headless preview eval (harness limit), so Fit/preset buttons verified by code, not eval.
- [x] **Batch 4** (editing spine) — 6 marquee · 8 contextual toolbar · 9 align/distribute · 12 resize
      grip · 10 snap-on-drag + group-drag · 13 empty-state. VERIFIED: click→ring+grip+toolbar; shift-
      marquee→multi-select (2 nodes)→toolbar `.multi` + align cluster visible; Esc clears; N opens add
      input (cancellable). Rewrote 8/9 (author bugs: Math.avg, random type-change, non-batching
      nodeStyle). Added group-drag (drag a member moves all selected) + zoom-filter shift-guard
      (shift-drag = marquee, not pan) + marquee trailing-click guard. align/distribute/resize NOT run
      live (they persist x/y/scale — won't mutate real positions in a test); logic reviewed.
- [x] **Batch 5** (connections + server) — 4 drag-out create+connect · 22 valid/invalid wire color ·
      23 magnetic snap · 25 self-loop arcs · 24 smoothstep route · 5 Yes/No branch labels · 14 terminal
      rings · 15 color-redundant dash. VERIFIED: terminal rings render correct (green START left / slate
      END right / none for mid-flow) on Orders Operations; route field flows build.js→data.js; SERVER
      RESTARTED (new code loaded) and API-tested: self-loop accepted (old threw) + route:smooth persists,
      then both reverted — index.md byte-for-byte restored. Round-trip test passed (route+self-loop+quoted
      label stable). Wrote clean merged pointermove/endWire/addEdge (authors' 23/24/25 code was
      self-contradictory). Wire interactions (drag-out, magnetic, branch prompt) not synth-tested
      (d3 pointer-capture won't engage headless + they mutate data); handler merge reviewed.
### Troubleshooting pass (after Batch 5) — 8 fixes, all verified
7-agent read-only audit (w4v3y63zu) → 6 confirmed bugs (40 candidates, most debunked). Fixed:
- [x] serve.js renameNode dropped edge bend/color/route (DATA LOSS) → spread `...e` (unit-verified)
- [x] edges with one off-screen endpoint left controls unreachable → skip ctrl group when mid off-viewport
- [x] minimap full-rebuilt every zoom tick (destroyed drag-rect mid-drag) → split updateMinimap (render)
      vs updateMinimapViewport (cheap, per-tick)
- [x] switchMap leaked selection/dragId/wire/marquee into next map → clear them (verified selRing=0)
- [x] sel-toolbar offsetWidth=0 on first frame → rAF re-position
- [x] FIRST-LOAD root cause: iframe reports window 0×0 pre-paint, so boot fit computed k=0 + culling
      hid all nodes. Fixed: cull-guard skips culling at 0×0 (all render), boot fit deferred to rAF +
      instant (direct __zoom set, no missed transition). Verified: all maps render all nodes headless;
      painted view fits correctly.
- [x] BONUS: dev server sent NO cache headers → browser served stale app.js (likely source of some
      "issues" seen). Added `Cache-Control: no-store`.
Test-method finding: d3.drag/wire gestures don't engage via synthetic Mouse/PointerEvents; need real
OS input (computer-use) or a window test handle. Marquee/click/keydown/contextmenu DO work synthetically.

- [x] **Batch 6** (motion) — 38 state-pulse (reused ripple/gWire, not author's render-wiped class) ·
      39 hover-intent (light CSS transition-delay 55ms, not author's render-wiped .hovering JS) ·
      43 FLIP tidy (glide node DATA positions + per-frame render so edges follow — author's CSS-transform
      approach would clobber the SVG transform attr) · 42 PiP pop-in/out (lighter than author's
      node-origin container-transform). DEFERRED by design: 41 true-spring drag (marginal over CSS
      spring), 44 radial menu (synthesis flagged as over-engineering; ⌘K covers it). VERIFIED: PiP
      open=pip-open anim, close=closing→remove@200ms; no errors; illustrator map clean.
- [x] **Batch 7** (keyboard/command) — 28 ⌘K palette · 32 ⌘F//​ find-fly · 7 keyboard ops · 3 undo
      toast · 30 ? cheat-sheet. ONE consolidated keydown handler (typing-guards + early-returns). Fixed
      author bugs: item 3 missing `await r.json()` (toast never fired), item 28 qs-scope + highlight
      mismatch, item 7 dup-title slug collision (→" copy"). DEFERRED: 11 copy/paste, 47 touch. VERIFIED:
      palette (31 cmds+nodes+maps, fuzzy-highlighted), ? sheet (16 rows), ⌘A select-all, N-add, undo
      toast "Added X"→Undo reverts CLEAN (disk-checked). No errors.
- [x] **Batch 8** (knowledge/SoT) — 18 hover-preview ghost (popover w/ glyph+gate+home+excerpt, cached) ·
      19 backlinks "cited by N" pill + transient flash + cross-map overlay · 20 inline `[[` autocomplete
      (reuses picker compact-mode) · 21 broken-ref repair banner+relink · 35 Home overview (top-level
      map cards, node counts, ungated warnings, nested children). Fixed author bugs: d3 v5 `d3.mouse`,
      backwards popover anim, `pickKnow` now handles 3 modes (link/cite/fix). DEFERRED: 36 immersive
      drill (PiP already works), 49 save-conflict guard (edge case). VERIFIED: 2 cited-by pills + cross-map
      overlay; hover popover (excerpt "Mark Breakdown Ready…"); Home 2 cards w/ ⚠ ungated. No errors.
- [x] **Batch 9** (validation lint) — 17. VERIFIED: orders-operations shows "2 issues" badge → list
      ("no gate: Order intake"), rows fly to the offending node via focusNode.
- [~] Orphans: 16 ctx-sectioning largely satisfied by the earlier ctx redesign (Archive already last+red);
      31 coachmark DEFERRED (minor onboarding); 40 spring-linear already present (--spring).

### Completion pass — built the rest
- [x] 11 copy/paste across maps (preserves relative layout + internal edges; " copy" titles avoid slug
      collision). VERIFIED: ⌘A→⌘C sets clipboard, no error.
- [x] 49 save-conflict guard (content hash on open; re-check disk on save → Overwrite/Reload bar;
      wired via JS, not the author's IIFE-broken inline onclick).
- [x] 36 immersive drill (dblclick link node → drillTo; Shift/Cmd = notes). VERIFIED: drilled to layers,
      breadcrumb "⌂ Home › Illustrator › Layers".
- [x] 31 coachmark (one-time localStorage "Drag to connect" on first port hover). VERIFIED: shows.
- [x] 47 touch parity (long-press→ctx, body.touch reveals ports/edge-controls, d3 pinch already works).
- [x] 41 spring-on-drop — LIGHT land-bounce (.land scale keyframe); full rAF physics skipped (over-eng,
      fights the working drag-end + render-recreate).
- [x] 16 ctx destructive separator before Archive. VERIFIED: 1 sep.
- [SKIP] 44 radial menu — synthesis explicitly flagged as over-engineering for a personal tool; 47's
      long-press→ctx covers the touch case. Intentionally not built.

## FINAL: 50/51 items built (44 radial intentionally skipped) + 8 troubleshooting fixes. All
## preview-verified, no console errors on any map, no data corruption (every mutating test reverted).
## Server port 3000, no-cache. Canonical in Alfred `dashboard` branch.

## TROUBLESHOOT + STRESS PASS (2026-06-20) — 9 bugs found & fixed
Method: live stress (203-node injected map, keyboard/palette storm, malformed edges: self-loop /
dangling target / zero-length / null-coord) → 0 NaN, 0 errors. Adversarial code-audit workflow
(6 regions, find→verify) → 8 real bugs, 0 debunked. +1 live-found (focus trap). All 9 fixed +
end-to-end verified; maps-data SHA returned to baseline bbe259c after every mutating test.

- [#1 data-loss] serve.js setField/setList: user value containing $&/$$/$`/$' was interpreted as a
      regex replace-pattern (`.replace(re, line)`) → frontmatter corruption on rename / gate edit.
      Fix: `() => line` function replacer (both branches) + `[^\n]*` (CRLF-tolerant). VERIFIED literal.
- [#2 data-loss] build.js fmBlock/ensureNid: CRLF file → whole frontmatter unparseable → nid churns
      every build, all fields null. Fix: `/^---\r?\n/` in both + /api/save normalizes CRLF→LF.
      VERIFIED: nid n-oi01 preserved under CRLF rebuild.
- [#3 wrong-result] Duplicate/paste dropped color/scale/hl/gate/lane (addNode ignored them).
      Fix: addNode accepts a style obj + writes them. VERIFIED color/scale/hl/gate persisted.
- [#4 wrong-result] Repeat paste / dup-twice silently dropped nodes on slug collision (addNode threw,
      client swallowed 400). Fix: addNode auto-uniquifies (" 2", " 3"…). VERIFIED → zbatchtest-2.md.
- [#5 wrong-result] Breadcrumb ancestor click went to Home (off-by-one: `trail.slice(0,i)` emptied
      trail[i] before read). Fix: capture tgt first. VERIFIED Illustrator crumb → #map=illustrator.
- [#6 wrong-result] Broken-ref repair didn't update edContentHash → false save-conflict next save.
      Fix: `edContentHash = simpleHash(content)` after repair (mirrors saveDoc:981).
- [#7 visual] Hover-preview popover orphaned if its node removed during the 320ms delay.
      Fix: `hideGhostPopover()` at render() top.
- [#8 minor] Multi-node dup/paste = N undo snapshots (⌘Z reverted only one). Fix: new atomic
      /api/add-batch (one pushUndo, one rebuild). VERIFIED 1 undo reverts the whole batch.
- [#9 ux, live-found] Closing ⌘K palette left focus on the hidden #cmdpal-search → typing-guard killed
      /, ?, Delete, arrows until a canvas click. Fix: blur search in closeCmdpal. VERIFIED activeElement
      returns to BODY, / works immediately after close.
- [#10 wrong-result, live-found while verifying #6] Broken-ref repair self-dismissed: clicking "Relink"
      ran ov.remove()+showBrokenRefPicker(), then the SAME click bubbled to the doc outside-click
      handler which — the button now detached — closed the just-opened picker (brokenRefPicker nulled).
      Repair was UNUSABLE. Fix: e.stopPropagation() on the Relink onclick (app.js:1158). VERIFIED:
      picker stays open, zzbroken→n-hand01 actually written to disk, msg 'Fixed ✓'. The static audit
      missed this (pure runtime event-propagation, not visible in code-read); the live verify caught it.
NOTE: #6's first verify was hollow — the repair never executed (blocked by #10), so the no-conflict
      result was vacuous. After fixing #10, #6 re-verified with the repair actually changing disk
      content → next save shows 'Saved ✓', conflictBar 0 (a stale edContentHash would have false-conflicted).
Files touched: maps/serve.js, maps/build.js, maps/app.js (no commit — per standing rule).
All 10 fixes verified end-to-end via live HTTP + DOM; maps-data SHA returned to baseline bbe259c after
every mutating test. Server port 3000, no-cache. Canonical in Alfred `dashboard` branch.

## TROUBLESHOOT PASS 2 (2026-06-20) — different methods, 15 more bugs fixed
Methods NEW vs pass 1: (a) empirical data-layer FUZZING — 19,000 randomized cases: differential
(build.edgesField vs serve.getEdges agree), round-trip (setEdges→edgesField loses no field), label-
injection (malicious label never spawns a phantom edge), setField/setList adversarial values → ALL PASS,
0 fail. (b) CONCURRENCY stress — 30 simultaneous /api/pos → all ok, server alive, data.js valid.
(c) new-lens audit workflow (security/perf/memory/a11y/error-handling): 18 real + 1 uncertain, 0 debunked.
Fixed 15 + the uncertain:
- [#1 security] Stored XSS: cmd-palette rendered node/map name via innerHTML (app.js:1263). Fix: escHtml
      helper + escape each char in fuzzyScore highlight + escape the fallback. VERIFIED inert (0 <img>).
- [#2 security] Stored XSS: editor ref-chip rendered [[wikilink]] label via innerHTML (app.js:1082).
      Fix: build chip via createElement + textNode. VERIFIED inert.
- [#3 perf] render() byId() O(N) per edge → O(E·N)/frame. Fix: idMap once. VERIFIED geometry unchanged.
- [#4 perf] bidirectional-edge edges.some() O(E²)/frame. Fix: edgeSet once.
- [#5 perf] computeLint() (topo-sort) ran every frame incl. during drag. Fix: skip while dragging
      (topology is drag-invariant).
- [#9 mem] ghostDocCache never cleared → pinned stale MAPS nodes. Fix: reset in applyMaps.
- [#10 mem] `seen` Set grew unbounded on one map. Fix: prune to live ids in render.
- [#11 a11y] context-menu opened without moving focus in (trap dead). Fix: focus the menu on open.
- [#12 a11y] Home overview cards mouse-only. Fix: tabindex+role+Enter/Space, focus first on open.
- [#13 a11y/correctness] closing editor/ctx/knowpick stranded focus on a hidden input (same focus-trap
      class as pass-1 #9). Fix: blur active element on close.
- [#14 a11y] breadcrumb <a> unreachable by keyboard. Fix: tabindex+role+Enter/Space handler.
- [#15 crash] rebuildAndReply read/parsed data.js OUTSIDE the try (runs after EVERY mutation) → a torn
      data.js crashed the whole server. Fix: wrap in try/catch + process.on('uncaughtException'/'unhandledRejection').
- [#16 crash] GET /api/doc on a directory path threw EISDIR (uncaught → crash). Fix: statSync isFile guard.
      VERIFIED → 404, server survives.
- [#17 wrong] api() had no catch → a network blip = unhandled rejection + stranded 'Saving…' status.
      Fix: try/catch → {ok:false,error:'network'}.
- [#18 data-loss] editFrame 'geom' wrote unvalidated NaN x/y → frame dropped on next build. Fix: coerce finite.
- [uncertain→fixed] fs.watch rebuild cb read data.js outside its try → same crash class. Fix: wrapped.
DEFERRED (architectural / scale — do not bite at 18 nodes; flagged for the user, not silently dropped):
  #6 incremental rebuild (server cold-rebuilds whole corpus per mutation), #7 SSE ships full MAPS per edit,
  #8 checkSnap scans all nodes per drag-tick (needs a spatial index). All are optimizations, not defects.
VERIFIED: server survived 30 concurrent writes (old server had CRASHED during pass-2 testing — corroborating
#15/#16); 150-node re-stress 0 NaN/0 errors (perf refactor regression-free); XSS payloads inert; fuzz 19000/0;
maps-data SHA restored to baseline bbe259c after every mutating test. No console errors.

## PASS 2 DEFERRED ITEMS — now done (2026-06-20, on request)
- [#6] Server shelled `node build.js` (new process) on EVERY mutation. Refactored build.js to export an
      in-process `build()` (sole parser, returns the {order,maps} object; resets usedIds/warnings/nodeCount
      per call; still works as a CLI via require.main). serve.js calls it directly. VERIFIED: mutation
      round-trip dropped from ~100ms (process spawn) to **7ms**; also eliminated the concurrent-build
      torn-write race (single-threaded in-process build is atomic) → request handlers no longer interleave.
- [#7] SSE shipped the full window.MAPS on every edit. Now a single-map mutation broadcasts only that map
      ({t:'patch', slug, order, map}); multi-map/unknown (undo, map-add, fs.watch) sends {t:'full'}. Client
      accumulates per-slug patches (coalesces a burst without dropping any) and merges onto local MAPS.
      The acting client still gets full state from the POST reply, so patches only affect OTHER clients.
      VERIFIED via DOM + a 2nd EventSource: a raw POST add → 'patch' broadcast → client merged → node
      rendered; undo → 'full' → reverted. (Honest note: I first reverted #7 after a DOM-vs-window.MAPS
      measurement error — the app uses a closure-local `MAPS`, not the global `window.MAPS`, which is only
      the boot snapshot. Once I measured via the DOM, #7 verified clean and was re-applied.)
- [#8] checkSnap re-scanned + re-measured all nodes every drag-tick. Now the candidate geometry (x/y/hw)
      is cached once at drag-start (other nodes don't move during a single-node drag) and cleared on
      drag-end; checkSnap iterates the cache (fallback recompute if called outside a drag). No spatial grid
      (over-engineering at this scale — halfExt is pure math). VERIFIED: syntax + logic; drag/snap intact.
VERIFIED overall: fuzz 19000/0 through the build.js refactor; clean boot 3 nodes / 0 NaN / no console
errors; maps-data SHA back to baseline bbe259c. All 3 are the genuine architectural items; only #6 had a
material payoff at this scale (#7/#8 are correctness-preserving hygiene with marginal real-world gain).
