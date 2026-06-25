/* Process-maps dashboard — multiple directed maps, free node placement, drill-down links.
   Data: window.MAPS = { order:[slug...], maps:{ slug:{id,title,url,nodes:[...],edges:[...]} } }
   Connections: chord-tangent bezier; drag from a node's right-edge port to connect;
   double-click a link to rename it; hover a link for ×. Positions are committed map content. */
'use strict';
(function () {
  let MAPS = window.MAPS || { order: [], maps: {} };
  let cur = MAPS.order[0] || null;
  let trail = [];
  let SERVER = false;
  let wire = null;                                   // active drag-to-connect (drag from a node's right-edge port)
  let dragMoved = false;                              // did the current node-drag actually move? (a plain click fires d3 start→end with no move → no bounce/save)
  let showLanes = false;
  let pendingMaps = null;                            // SSE queued during a gesture
  let clickTimer = null;                             // single-click navigation, debounced against double-tap
  let lastTapId = null, lastTapAt = 0, suppressClick = false;   // double-tap (→ edit) detected on pointerdown (capture, stable svg) by id+timing — robust against render() recreating the node element
  let portArmed = false;                             // true only while a port actually started a wire — so a plain port tap doesn't swallow the node click
  let dragId = null;                                 // id of the node currently being dragged (re-applies the 'grabbing' lift across render()'s per-tick rebuild)
  let dragging = false;                              // node-move in progress (guards mid-drag SSE)
  const seen = new Set();                            // node ids already animated-in (so enter fires once)
  let selection = new Set();                          // currently-selected node ids (re-applied each render, like dragId; foundation for marquee/batch ops)
  let cmdpalReg = [], cmdpalSel = 0;                  // command-palette registry + highlighted row
  let toastTimeout = null, nudgeTimer = null, clipboard = null, coachTimeout = null, landId = null;
  const SHORTCUTS = [['⌘K', 'Command palette'], ['⌘F  /  /', 'Find & fly to a node'], ['N', 'Add a node'], ['Double-click node', 'Open notes'], ['Right-click node', 'Context menu'], ['Drag from port', 'Connect (drop on canvas = create)'], ['Shift-drag', 'Marquee multi-select'], ['Backspace / Delete', 'Archive selection'], ['⌘D', 'Duplicate selection'], ['⌘A', 'Select all'], ['Arrows', 'Nudge selection (⇧ = bigger)'], ['Shift+1', 'Fit to view'], ['⌘Z', 'Undo'], ['⌘S', 'Save notes'], ['Esc', 'Close / deselect'], ['?', 'This help']];
  const EMBED = new URLSearchParams(location.search).has('embed');   // true when shown inside a floating sub-map window
  if (EMBED) document.body.classList.add('embed');

  const NS = 'http://www.w3.org/2000/svg';
  const TYPE_COLOR = { step: 'var(--step)', decision: 'var(--decision)', 'subprocess-link': 'var(--link)', reference: 'var(--ref)' };
  const WIKILINK_RE = /\[\[([^\]]+)\]\]/g;   // [[nid|label]] — same syntax as the wiki
  const LANE_VARS = ['--l0', '--l1', '--l2', '--l3', '--l4', '--l5', '--l6'];
  const PAL_HEX = ['#0d9488', '#4f46e5', '#64748b', '#d97706', '#a855f7', '#0ea5e9', '#e11d48',   // matches --l0..--l6
    '#16a34a', '#111827', '#eab308', '#d946ef'];   // + green, black, yellow, magenta

  const svg = d3.select('#map-svg').attr('role', 'application').attr('aria-label', 'Process map editor');
  const svgN = svg.node();
  const canvas = svg.append('g');
  const gFrame = canvas.append('g');                  // background boxes (behind everything)
  const gLane = canvas.append('g');
  const gEdge = canvas.append('g');
  const gNode = canvas.append('g');
  const gWire = canvas.append('g');                   // NEVER cleared by render()
  const wirePath = gWire.append('path').attr('id', 'wire-preview').attr('d', '');
  const FRAME_PAL = ['--l0', '--l1', '--l2', '--l3', '--l4', '--l5', '--l6'];
  const zoom = d3.zoom().scaleExtent([0.2, 2.5]).filter(e => (e.type === 'wheel' || !e.shiftKey) && !e.target.closest('.node') && !e.target.closest('.frame-grab'))   // shift-drag is reserved for marquee select, not pan
    .on('zoom', e => {
      let t = e.transform;
      if (!isFinite(t.x) || !isFinite(t.y) || !isFinite(t.k)) {   // self-heal a corrupted (NaN) transform so pan never dies
        t = d3.zoomIdentity.translate(isFinite(t.x) ? t.x : 0, isFinite(t.y) ? t.y : 0).scale(isFinite(t.k) && t.k > 0 ? t.k : 1);
        svgN.__zoom = t;
      }
      canvas.attr('transform', t);
      document.body.classList.toggle('lod-far', t.k < 0.55);   // live level-of-detail toggle (cheap, no rebuild)
    })
    .on('end', () => scheduleRender());   // re-cull to the SETTLED viewport once the pan/zoom/transition completes (per-tick render storms fight programmatic zoom transitions)
  svg.call(zoom);
  const defs = svg.append('defs');
  const edgeCol = getComputedStyle(document.documentElement).getPropertyValue('--edge').trim();
  const mk = (id, fill) => '<marker id="' + id + '" markerWidth="13" markerHeight="13" refX="10" refY="5" orient="auto" markerUnits="userSpaceOnUse"><path d="M0,0 L10,5 L0,10 L3,5 Z" fill="' + fill + '"/></marker>';
  defs.html(mk('ah', edgeCol) + PAL_HEX.map((h, i) => mk('ah' + i, h)).join('') +   // default + per-palette colored arrowheads
    '<linearGradient id="edgeGrad" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#6366f1"/><stop offset="1" stop-color="#10b981"/></linearGradient>' +
    '<linearGradient id="glass" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff" stop-opacity="0.55"/><stop offset="0.45" stop-color="#ffffff" stop-opacity="0.08"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></linearGradient>');

  const map = () => MAPS.maps[cur];
  const nidSlug = () => { const m = {}; (map() ? map().nodes : []).forEach(n => m[n.id] = n.slug); return m; };
  const byId = id => (map() ? map().nodes : []).find(n => n.id === id);
  const repoRel = u => (u || '').replace(/^(\.\.\/)+/, '');
  const escHtml = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');   // for the few innerHTML paths (cmd-palette highlight); a node named "<img onerror>" must not execute
  const inputOpen = () => !document.getElementById('name-input').hidden || !document.getElementById('edge-label-input').hidden;

  const TOASTY = { '/api/archive': b => 'Archived "' + ((b.path || '').split('/').pop().replace(/\.md$/, '')) + '"', '/api/add': b => 'Added "' + (b.title || 'node') + '"', '/api/edge': b => b.remove ? 'Deleted connection' : null, '/api/frame': b => b.op === 'del' ? 'Deleted box' : null };
  async function api(path, b) {
    let j;
    try {
      const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) });
      j = await r.json();
    } catch (e) { return { ok: false, error: 'network' }; }   // a blip/500 must return a falsy result, not reject — callers check j.ok and would otherwise strand 'Saving…/Fixing…' on an unhandled rejection
    if (j && j.ok && TOASTY[path]) { const label = TOASTY[path](b); if (label) showUndoToast(label); }   // surface undo for destructive/creative actions
    return j;
  }
  function applyMaps(m) {
    clearTimeout(sseBounceTimer); ssePending = null;     // a direct apply supersedes any queued SSE snapshot
    if ((wire && wire.active) || dragging || inputOpen()) { pendingMaps = m; return; }  // don't tear down mid-gesture
    pendingMaps = null;                                  // applying authoritative state — drop any stale queued snapshot
    // Skip the full teardown+rebuild when the VISIBLE map is byte-identical (the echo of your own edit + the fs.watch echo).
    // render() recreates every element; doing so while the cursor is over a node/edge replays its :hover transition → jitter.
    const curSame = !!(MAPS && cur && m.maps && m.maps[cur] && JSON.stringify(MAPS.maps[cur]) === JSON.stringify(m.maps[cur]) && (MAPS.order || []).join() === (m.order || []).join());
    MAPS = m; _nidIx = null; _backlinkIx = null; ghostDocCache = {};   // new MAPS object → drop the memoized nid + backlink indexes + hover-doc cache (else it pins stale node objects)
    if (!MAPS.maps[cur]) { cur = MAPS.order[0] || null; trail = []; }
    if (edPath) revalidateEditor();                      // open notes drawer: re-check the node still exists
    fillMapSelect(); if (!curSame) render();             // no visible change → keep the existing DOM (no recreation → no hover-jitter)
  }
  function flushPending() { if (pendingMaps && !(wire && wire.active) && !dragging && !inputOpen()) { const m = pendingMaps; pendingMaps = null; applyMaps(m); } }
  let rafPending = false;                              // coalesce burst pointermoves (120Hz trackpads) into one render per frame
  function scheduleRender() { if (rafPending) return; rafPending = true; requestAnimationFrame(() => { rafPending = false; render(); }); }
  let sseBounceTimer = null, ssePending = null;        // ssePending: accumulator { full, patches:{slug:map}, order } so a burst of per-map patches coalesces without dropping any
  function debounceSse(fn, delay) { clearTimeout(sseBounceTimer); sseBounceTimer = setTimeout(fn, delay); }
  function queueSse(d) {
    if (!ssePending) ssePending = { full: null, patches: {}, order: null, issues: undefined };
    if (d && d.t === 'patch') { ssePending.patches[d.slug] = d.map; ssePending.order = d.order; if (d.issues !== undefined) ssePending.issues = d.issues; }
    else { ssePending.full = (d && d.t === 'full') ? d.maps : d; ssePending.patches = {}; ssePending.issues = (d && d.t === 'full' && d.maps) ? d.maps.issues : (d ? d.issues : undefined); }   // a full snapshot supersedes any queued patches
  }
  function flushSse() {
    const q = ssePending; ssePending = null;
    if (!q) return;
    let m;
    if (q.full) { m = q.full; if (Object.keys(q.patches).length) m = { order: q.order || m.order, maps: Object.assign({}, m.maps, q.patches), issues: m.issues }; }
    else { if (!MAPS) return; m = { order: q.order || MAPS.order, maps: Object.assign({}, MAPS.maps, q.patches) }; }   // merge patched map(s) onto the maps we already hold
    if (q.issues !== undefined) m.issues = q.issues; else if (m.issues === undefined && MAPS) m.issues = MAPS.issues;   // carry build issues (a patch payload omits the full maps obj)
    applyMaps(m);
  }
  // (minimap + zoom-% HUD removed per feedback)

  // ---- geometry ----
  const isDiamond = n => n.type === 'decision';
  function baseHalf(n) {   // unscaled extents, used for DRAWING the shape
    if (isDiamond(n)) return { hw: Math.max(150, Math.min(300, (n.name || '').length * 8 + 70)) / 2, hh: 35 };
    return { hw: Math.max(120, Math.min(260, (n.name || '').length * 8 + 48)) / 2, hh: 23 };
  }
  function halfExt(n) {   // SCALED extents, used for edge/port canvas-coordinate math
    const b = baseHalf(n), s = n.scale || 1;
    return { hw: b.hw * s, hh: b.hh * s };
  }
  function edgePt(n, tx, ty) {
    const { hw, hh } = halfExt(n);
    const dx = tx - n.x, dy = ty - n.y;
    if (!dx && !dy) return { x: n.x, y: n.y };
    if (isDiamond(n)) { const s = 1 / (Math.abs(dx) / hw + Math.abs(dy) / hh); return { x: n.x + dx * s, y: n.y + dy * s }; }  // rhombus boundary, not AABB
    const s = Math.min(dx ? (hw + 2) / Math.abs(dx) : Infinity, dy ? (hh + 2) / Math.abs(dy) : Infinity);
    return { x: n.x + dx * s, y: n.y + dy * s };
  }
  // edges leave the source's right side and enter the target's left side (n8n / React-Flow style)
  const rightPort = n => ({ x: n.x + halfExt(n).hw, y: n.y });
  const leftPort = n => ({ x: n.x - halfExt(n).hw, y: n.y });
  const bottomPort = n => ({ x: n.x, y: n.y + halfExt(n).hh });   // knowledge-link anchor (bottom = the knowledge axis)
  // smooth HORIZONTAL-tangent cubic bezier — big horizontal control handles = pronounced S-curve.
  // bow = vertical offset that separates a bidirectional A<->B pair.
  function edgePath(p1, p2, bow) {
    const dx = Math.abs(p2.x - p1.x), dy = Math.abs(p2.y - p1.y);
    const taper = dx / (dx + dy * 0.6 + 1);                  // →1 for a normal L→R run (full S), →small for a mostly-vertical/reversed edge (kills the backward loop)
    const k = Math.max(24, Math.max(45, dx * 0.5) * taper + 24);
    const c1 = { x: p1.x + k, y: p1.y + (bow || 0) };
    const c2 = { x: p2.x - k, y: p2.y + (bow || 0) };
    return { d: 'M' + p1.x + ',' + p1.y + ' C' + c1.x + ',' + c1.y + ' ' + c2.x + ',' + c2.y + ' ' + p2.x + ',' + p2.y, c1, c2 };
  }
  const cubicMid = (p1, c1, c2, p2) => ({ x: .125 * p1.x + .375 * c1.x + .375 * c2.x + .125 * p2.x, y: .125 * p1.y + .375 * c1.y + .375 * c2.y + .125 * p2.y });
  function orthStepPath(p1, p2) {   // rounded right-angle "smoothstep" routing — reads as a clean flowchart in dense maps
    const dx = p2.x - p1.x, dy = p2.y - p1.y, r = 12;
    const bendX = Math.max(p1.x + r, Math.min((p1.x + p2.x) / 2, p2.x - r));
    const sy = Math.sign(dy || 1), sx = Math.sign(dx || 1);
    const d = 'M' + p1.x + ',' + p1.y + ' L' + (bendX - r) + ',' + p1.y +
      ' Q' + bendX + ',' + p1.y + ' ' + bendX + ',' + (p1.y + sy * r) +
      ' L' + bendX + ',' + (p2.y - sy * r) +
      ' Q' + bendX + ',' + p2.y + ' ' + (bendX + r * sx) + ',' + p2.y +
      ' L' + p2.x + ',' + p2.y;
    return { d, c1: { x: bendX, y: p1.y }, c2: { x: bendX, y: p2.y } };
  }
  function selfLoopPath(n, bend) {   // teardrop loop off the node's right side (feedback / retry edge)
    const { hw, hh } = halfExt(n), sx = n.x + hw, sy = n.y;
    const w = Math.max(46, hh * 2), h = (Math.abs(bend) || hh * 2.2), dir = bend < 0 ? 1 : -1;
    const d = 'M' + sx + ',' + sy + ' C' + (sx + w) + ',' + (sy + dir * h) + ' ' + (sx + w) + ',' + (sy + dir * h) + ' ' + sx + ',' + (sy + dir * 12);
    return { d, c1: { x: sx + w * 0.72, y: sy + dir * h }, c2: { x: sx + w * 0.72, y: sy + dir * h } };
  }

  // lane → stable color (sorted distinct lanes in current map)
  function laneColorMap() {
    const lanes = [...new Set((map() ? map().nodes : []).map(n => n.lane).filter(Boolean))].sort();
    const m = {}; lanes.forEach((l, i) => m[l] = 'var(' + LANE_VARS[i % LANE_VARS.length] + ')'); return m;
  }
  let LANE_COLORS = {};
  const accent = n => (n.color != null ? PAL_HEX[n.color % PAL_HEX.length] : null) || (n.lane && LANE_COLORS[n.lane]) || TYPE_COLOR[n.type] || TYPE_COLOR.step;
  const reduceMotion = () => window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const motionAllowed = () => !reduceMotion() && !document.body.classList.contains('calm');   // gate EVERY new animation through this (reduced-motion + calm-mode audit)
  function announce(msg) { const el = document.getElementById('status-msg'); if (el) el.textContent = msg; }   // a11y: push status to the live region
  // fuzzy subsequence scorer — rewards consecutive + word-start matches; returns {score, highlighted}. Used by the picker + command palette.
  function fuzzyScore(str, query) {
    const s = (str || '').toLowerCase(), q = (query || '').toLowerCase();
    if (!q) return { score: 0, highlighted: str };
    if (!s) return { score: -1, highlighted: str };
    let qi = 0, si = 0, score = 0, last = -1; const marked = [];
    while (si < s.length && qi < q.length) {
      if (s[si] === q[qi]) { const wordStart = si === 0 || /[^a-z0-9]/.test(s[si - 1]); score += (last === si - 1) ? 3 : wordStart ? 2 : 1; marked.push(si); last = si; qi++; }
      si++;
    }
    if (qi < q.length) return { score: -1, highlighted: escHtml(str) };
    const set = new Set(marked); let out = '', span = false;
    for (let i = 0; i < str.length; i++) { const c = escHtml(str[i]); if (set.has(i)) { if (!span) { out += '<mark>'; span = true; } out += c; } else { if (span) { out += '</mark>'; span = false; } out += c; } }   // escape each char so the <mark> wrapper stays the only live HTML
    if (span) out += '</mark>';
    return { score, highlighted: out };
  }
  function fadeOut(el) {   // play the .exiting menu-out animation, then hide — state resets stay synchronous at the call site
    if (!el || el.hidden) return;
    if (reduceMotion()) { el.hidden = true; return; }
    el.classList.add('exiting');
    const fin = () => { if (!el.classList.contains('exiting')) return; el.classList.remove('exiting'); el.hidden = true; };   // a reopen clears 'exiting' first, cancelling this hide
    el.addEventListener('animationend', fin, { once: true });
    setTimeout(fin, 220);
  }
  function fitText(sel, maxW) {   // trim an SVG <text> with an ellipsis so it never overruns maxW (px)
    const node = sel.node(); if (!node || maxW <= 0) return;
    if (node.getComputedTextLength() <= maxW) return;
    let t = sel.text();
    while (t.length > 1 && node.getComputedTextLength() > maxW) { t = t.slice(0, -1); sel.text(t + '…'); }
  }

  function dragMoveEdges(ids) {   // recompute the `d` of edges touching any dragged node, without a full render() (keeps drag cheap)
    const m = map(); if (!m) return;
    const pos = new Map();
    gNode.selectAll('g.node').each(function (n) { pos.set(n.id, n); });   // read positions from the RENDERED nodes' bound data — the exact objects the drag handler mutates (byId may return a different object after an SSE rebuild → edge would lag)
    gEdge.selectAll('g.edgegrp').each(function (e) {
      if (!e || (!ids.has(e.from) && !ids.has(e.to))) return;
      const a = pos.get(e.from) || byId(e.from), b = pos.get(e.to) || byId(e.to); if (!a || !b) return;
      let d;
      if (e.from === e.to) { ({ d } = selfLoopPath(a, e.bend)); }
      else {
        const p1 = rightPort(a), p2 = leftPort(b);
        const hasReverse = m.edges.some(x => x.from === e.to && x.to === e.from);
        const bow = e.bend ? e.bend : (hasReverse ? (e.from < e.to ? 22 : -22) : 0);
        ({ d } = (e.route === 'smooth') ? orthStepPath(p1, p2) : edgePath(p1, p2, bow));
      }
      d3.select(this).selectAll('path.edge').attr('d', d);
    });
  }

  function render() {
    LANE_COLORS = laneColorMap();
    hideGhostPopover();   // a rebuild (SSE refresh, drag end, map switch) can remove the hovered node mid-delay → cancel its armed timer / stray popover
    gFrame.selectAll('*').remove(); gLane.selectAll('*').remove(); gEdge.selectAll('*').remove(); gNode.selectAll('*').remove();
    if (!map()) { updateBreadcrumb(); return; }
    const edges = map().edges;
    const t = d3.zoomTransform(svgN);   // viewport culling: only build geometry for nodes near the visible rect (all nodes still live in MAPS — visual only)
    const vpL = (0 - t.x) / t.k, vpT = (0 - t.y) / t.k, vpR = (window.innerWidth - t.x) / t.k, vpB = (window.innerHeight - t.y) / t.k, cullPad = 240;
    const culled = d => { if (!window.innerWidth) return false; const h = halfExt(d); return d.x - h.hw - cullPad > vpR || d.x + h.hw + cullPad < vpL || d.y - h.hh - cullPad > vpB || d.y + h.hh + cullPad < vpT; };   // never cull before the viewport is laid out (iframe 0×0 pre-paint) → render all
    const allNodes = map().nodes, nodes = allNodes.filter(n => !culled(n)), visibleNodeIds = new Set(nodes.map(n => n.id));
    const hasOut = new Set(edges.filter(e => e.from !== e.to).map(e => e.from));   // node ids that are a stage (have an outgoing edge) — used for gate-status badges (computed over ALL edges)
    const hasIn = new Set(edges.filter(e => e.from !== e.to).map(e => e.to));      // node ids with an incoming edge → for START/END terminal rings

    // ---- background boxes (frames) — drawn first, behind everything; body is click-through ----
    (map().frames || []).forEach(f => {
      const col = 'var(' + FRAME_PAL[(f.color || 0) % FRAME_PAL.length] + ')';
      const g = gFrame.append('g').attr('class', 'frame').attr('transform', 'translate(' + f.x + ',' + f.y + ')').style('--fc', col);
      g.append('rect').attr('class', 'frame-bg').attr('width', f.w).attr('height', f.h).attr('rx', 18);
      const head = g.append('g').attr('class', 'frame-grab').attr('transform', 'translate(0,0)');
      head.append('rect').attr('class', 'frame-head').attr('width', f.w).attr('height', 26).attr('rx', 13);
      head.append('text').attr('class', 'frame-label').attr('x', 14).attr('y', 14).text(f.label);
      head.on('dblclick', (e) => { e.stopPropagation(); renameFrame(f); })
        .call(d3.drag().clickDistance(4).container(() => gFrame.node())   // gFrame persists across render(); the per-frame g does not
          .on('start', function (e) { e.sourceEvent.stopPropagation(); })
          .on('drag', function (e) { f.x += e.dx; f.y += e.dy; scheduleRender(); })
          .on('end', function () { if (SERVER) api('/api/frame', { map: cur, op: 'geom', id: f.id, x: f.x, y: f.y, w: f.w, h: f.h }).then(flushPending); }));
      const cyc = g.append('g').attr('class', 'frame-cyc').attr('transform', 'translate(' + (f.w - 34) + ',13)').on('click', (e) => { e.stopPropagation(); cycleFrameColor(f); });
      cyc.append('circle').attr('r', 6).attr('fill', col);
      const del = g.append('g').attr('class', 'frame-del').attr('transform', 'translate(' + (f.w - 14) + ',13)').on('click', (e) => { e.stopPropagation(); delFrame(f); });
      del.append('circle').attr('r', 8).attr('fill', '#e11d48');
      del.append('path').attr('d', 'M-3,-3 L3,3 M3,-3 L-3,3').attr('stroke', '#fff').attr('stroke-width', 1.6).attr('stroke-linecap', 'round');
      const rz = g.append('g').attr('class', 'frame-grab frame-resize').attr('transform', 'translate(' + f.w + ',' + f.h + ')');
      rz.append('rect').attr('x', -18).attr('y', -18).attr('width', 18).attr('height', 18).attr('fill', 'transparent').style('cursor', 'nwse-resize');
      rz.append('path').attr('d', 'M-4,-13 L-13,-4 M-4,-8 L-8,-4').attr('stroke', col).attr('stroke-width', 1.8).attr('stroke-linecap', 'round').attr('opacity', .7);
      rz.call(d3.drag().container(() => gFrame.node())
        .on('start', function (e) { e.sourceEvent.stopPropagation(); })
        .on('drag', function (e) { f.w = Math.max(80, f.w + e.dx); f.h = Math.max(60, f.h + e.dy); scheduleRender(); })
        .on('end', function () { if (SERVER) api('/api/frame', { map: cur, op: 'geom', id: f.id, x: f.x, y: f.y, w: f.w, h: f.h }).then(flushPending); }));
    });

    // ---- lane bands (optional) ----
    if (showLanes) {
      const lanes = {};
      nodes.forEach(n => { if (!n.lane) return; const { hw, hh } = halfExt(n); (lanes[n.lane] = lanes[n.lane] || []).push({ x0: n.x - hw, x1: n.x + hw, y0: n.y - hh, y1: n.y + hh }); });
      Object.keys(lanes).forEach(lane => {
        const b = lanes[lane], minX = Math.min(...b.map(o => o.x0)), maxX = Math.max(...b.map(o => o.x1)), minY = Math.min(...b.map(o => o.y0)), maxY = Math.max(...b.map(o => o.y1));
        gLane.append('rect').attr('class', 'laneband').attr('x', minX - 40).attr('y', minY - 18).attr('width', maxX - minX + 80).attr('height', maxY - minY + 36).attr('rx', 16).attr('fill', LANE_COLORS[lane]);
        gLane.append('text').attr('class', 'lanelabel').attr('x', minX - 30).attr('y', minY - 24).attr('fill', LANE_COLORS[lane]).text(lane);
      });
    }

    // ---- edges ----
    const idMap = new Map(allNodes.map(n => [n.id, n]));                       // O(1) node lookup (was byId() O(N) per edge → O(E·N)/frame)
    const edgeSet = new Set(edges.map(e => e.from + '\u0000' + e.to));         // O(1) reverse-edge test (was edges.some() O(E) per edge → O(E²)/frame)
    edges.forEach(e => {
      const a = idMap.get(e.from), b = idMap.get(e.to); if (!a || !b) return;
      if (!visibleNodeIds.has(a.id) && !visibleNodeIds.has(b.id)) return;   // cull edges with both endpoints off-screen
      const selfLoop = e.from === e.to;
      let p1, p2, c1, c2, d, mid;
      if (selfLoop) { ({ d, c1, c2 } = selfLoopPath(a, e.bend)); mid = c1; p1 = mid; p2 = mid; }   // feedback / retry edge
      else {
        p1 = rightPort(a); p2 = leftPort(b);
        const hasReverse = edgeSet.has(e.to + '\u0000' + e.from);
        const bow = e.bend ? e.bend : (hasReverse ? (e.from < e.to ? 22 : -22) : 0);   // manual bend overrides the auto bidirectional bow
        ({ d, c1, c2 } = (e.route === 'smooth') ? orthStepPath(p1, p2) : edgePath(p1, p2, bow));
        mid = cubicMid(p1, c1, c2, p2);
      }
      const stroke = e.color != null ? PAL_HEX[e.color % PAL_HEX.length] : null;
      const g = gEdge.append('g').datum(e).attr('class', 'edgegrp');   // datum lets dragMoveEdges() recompute just the connected edges live during a drag
      const vis = g.append('path').attr('class', 'edge' + (selfLoop ? ' self-loop' : '')).attr('d', d).attr('marker-end', e.color != null ? 'url(#ah' + (e.color % PAL_HEX.length) + ')' : 'url(#ah)');
      if (stroke) vis.style('stroke', stroke);
      if (e.color != null) { const dp = ['', '8,4', '4,6', '12,3', '3,8', '6,5', '10,3', '5,5', '9,3', '2,6', '7,4'], pat = dp[e.color % dp.length]; if (pat) vis.style('stroke-dasharray', pat); }   // colorblind / mono-export redundancy
      if (!stroke && !selfLoop) g.append('path').attr('class', 'edge flow').attr('d', d);   // gradient marching-ants only on default-color edges
      g.append('path').attr('class', 'edge hit').attr('d', d).on('dblclick', (ev) => { ev.stopPropagation(); editEdgeLabel(e, p1, c1, c2, p2); });
      if (e.label) {
        const t = g.append('text').attr('class', 'elabel').attr('x', mid.x).attr('y', mid.y).text(e.label);
        const bb = t.node().getBBox();
        g.insert('rect', 'text.elabel').attr('class', 'elabel-bg').attr('x', bb.x - 6).attr('y', bb.y - 3).attr('width', bb.width + 12).attr('height', bb.height + 6).attr('rx', 6);
      }
      if (mid.x < vpL || mid.x > vpR || mid.y < vpT || mid.y > vpB) return;   // edge midpoint off-screen (one endpoint far off-canvas) → skip the unreachable hover controls
      // hover controls: bend grab (at midpoint), color cycle + route toggle (above), delete (below)
      const ctrl = g.append('g').attr('class', 'edge-ctrl');
      ctrl.append('circle').attr('class', 'edge-bend').attr('cx', mid.x).attr('cy', mid.y).attr('r', 9)
        .call(d3.drag().container(() => canvas.node())     // canvas persists across render()
          .on('start', ev => ev.sourceEvent.stopPropagation())
          .on('drag', ev => { e.bend = (e.bend || 0) + ev.dy; scheduleRender(); })
          .on('end', () => { if (SERVER) { const n = nidSlug(); api('/api/edge', { map: cur, from: n[e.from], to: n[e.to], bend: Math.round(e.bend || 0) }).then(flushPending); } }));
      // (edge color-cycle + route-toggle circles removed per feedback — set edge color via right-click, route via the command palette)
      const del = ctrl.append('g').attr('transform', 'translate(' + mid.x + ',' + (mid.y + 20) + ')').style('cursor', 'pointer').on('click', (ev) => { ev.stopPropagation(); deleteEdge(e); });
      del.append('circle').attr('r', 7).attr('fill', '#e11d48');
      del.append('path').attr('d', 'M-2.5,-2.5 L2.5,2.5 M2.5,-2.5 L-2.5,2.5').attr('stroke', '#fff').attr('stroke-width', 1.5).attr('stroke-linecap', 'round');
    });

    // ---- nodes ----
    const sel = gNode.selectAll('g.node').data(nodes, d => d.id).enter().append('g')
      .attr('class', d => 'node' + (d.link_map ? ' linkable' : '') + (d.hl ? ' hl' : '') + (dragId === d.id ? ' grabbing' : '') + ((!dragging && !seen.has(d.id)) ? ' enter' : '') + ((hasOut.has(d.id) && !hasIn.has(d.id)) ? ' start' : '') + ((hasIn.has(d.id) && !hasOut.has(d.id)) ? ' end' : '') + (flashIds.has(d.id) ? ' flash' : ''))   // enter fires once; start/end = flow terminals; flash = backlink highlight
      .style('--accent', d => accent(d))
      .attr('transform', d => 'translate(' + d.x + ',' + d.y + ') scale(' + (d.scale || 1) + ')')
      .attr('tabindex', 0).attr('role', 'button').attr('aria-label', d => 'Node: ' + d.name + ' (' + d.type + ')')   // a11y: focusable + labelled
      .on('keydown', (e, d) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); selectClick(e, d.id); render(); onNodeOpen(d); } })   // keyboard activate = open
      .on('click', (e, d) => {
        if (suppressClick) { suppressClick = false; return; }   // trailing click(s) of a double-tap — editor already opening
        ripple(d.x, d.y, accent(d)); selectClick(e, d.id); render();
        clearTimeout(clickTimer); clickTimer = setTimeout(() => { clickTimer = null; onNodeClick(d); }, 430);   // defer single-click navigation PAST the 400ms double-tap window so a double-tap (handled on pointerdown) reliably pre-empts it
      })
      .on('dblclick', (e) => { e.preventDefault(); e.stopPropagation(); })   // double-tap handled on svgN pointerdown (capture) — native dblclick is unreliable (element recreated between clicks)
      .on('contextmenu', (e, d) => { e.preventDefault(); clearTimeout(clickTimer); clickTimer = null; openCtx(e, d); })
      .call(d3.drag().clickDistance(5)
        .on('start', function (e, d) { if (wire && wire.active) return; if (!selection.has(d.id)) { selection.clear(); selection.add(d.id); } dragging = true; dragMoved = false; dragId = d.id; document.body.classList.add('dragging'); d3.select(this).classed('grabbing', true); e.sourceEvent.stopPropagation(); })   // no render() on grab — apply the pick-up state directly so the dragged <g> is never recreated mid-gesture (render() runs once on drop)
        .on('drag', function (e, d) { if (wire && wire.active) return; dragMoved = true; let ids; if (selection.has(d.id) && selection.size > 1) { ids = new Set(selection); selNodes().forEach(n => { n.x += e.dx; n.y += e.dy; }); } else { ids = new Set([d.id]); d.x = e.x; d.y = e.y; } gNode.selectAll('g.node').filter(n => ids.has(n.id)).attr('transform', n => 'translate(' + n.x + ',' + n.y + ') scale(' + (n.scale || 1) + ')'); dragMoveEdges(ids); })   // live drag: move just the node <g>(s) + their edges directly — NO full render() per frame (a webview throttles that → lag). render() runs once on drop.
        .on('end', function (e, d) { if (wire && wire.active) return; const group = selection.has(d.id) && selection.size > 1; if (dragMoved && !group) { d.x = Math.round(d.x); d.y = Math.round(d.y); } if (snapGuide) { snapGuide.remove(); snapGuide = null; } dragging = false; dragId = null; document.body.classList.remove('dragging'); render(); if (dragMoved && SERVER) { if (group) persistPos(selNodes()); else api('/api/pos', { path: repoRel(d.url), x: Math.round(d.x), y: Math.round(d.y) }).then(flushPending); } else flushPending(); }));   // drop exactly where released; save only on a real move; round to whole px to match the server

    sel.each(function (d) {
      const g = d3.select(this), { hw, hh } = baseHalf(d), col = accent(d);   // draw at base size; the node g carries scale()
      const inner = g.append('g').attr('class', 'node-inner');   // hover lift/scale live here so they never fight d3.drag's transform on .node
      if (isDiamond(d)) {
        const pts = [[0, -hh], [hw, 0], [0, hh], [-hw, 0]].map(p => p.join(',')).join(' ');
        inner.append('polygon').attr('class', 'shape').attr('points', pts).attr('fill', 'var(--card-glass)').attr('stroke', col).attr('stroke-width', 2.2);
        inner.append('polygon').attr('class', 'sheen').attr('points', pts).attr('fill', 'url(#glass)');
      } else {
        inner.append('rect').attr('class', 'shape').attr('x', -hw).attr('y', -hh).attr('width', hw * 2).attr('height', hh * 2).attr('rx', 11).attr('fill', 'var(--card-glass)').attr('stroke', col).attr('stroke-width', 2.2);
        inner.append('rect').attr('class', 'sheen').attr('x', -hw).attr('y', -hh).attr('width', hw * 2).attr('height', hh * 2).attr('rx', 11).attr('fill', 'url(#glass)');
      }
      inner.append('text').attr('class', 'label').text((d.icon ? d.icon + '  ' : '') + d.name);   // optional emoji/char prefix for at-a-glance distinction
      if (d.type === 'subprocess-link' || d.type === 'reference') {
        const bd = inner.append('g').attr('transform', 'translate(' + (-hw + 2) + ',' + (-hh + 2) + ')');
        bd.append('circle').attr('r', 9).attr('fill', col);
        bd.append('text').attr('class', 'typeglyph').text(d.type === 'reference' ? '§' : '▸');
      }
      // gate-status badge (top-right): ✓ = gated · ! = a stage with no gate (would FAIL the workflow export)
      // reference nodes are source-of-truth, not stages — never flag them for a missing gate
      const gated = d.gate && String(d.gate).trim();
      if (gated || (hasOut.has(d.id) && d.type !== 'reference')) {
        const gb = inner.append('g').attr('class', 'gatebadge' + (gated ? '' : ' pulse')).attr('transform', 'translate(' + (hw - 2) + ',' + (-hh + 2) + ')');
        gb.append('circle').attr('r', 8).attr('fill', gated ? 'var(--link)' : 'var(--decision)');
        gb.append('text').attr('class', 'typeglyph').attr('font-size', '11px').text(gated ? '✓' : '!');
        gb.append('title').text(gated ? 'gate: ' + gated : 'stage has no gate — add one (right-click → Gate) before the workflow can run');
      }
      // ("cited by N" backlink pill removed per feedback)
      if (selection.has(d.id)) {   // selection ring on the outer g (stable under the hover lift); base extents +5px
        if (isDiamond(d)) g.append('polygon').attr('class', 'selring').attr('points', [[0, -(hh + 5)], [hw + 5, 0], [0, hh + 5], [-(hw + 5), 0]].map(p => p.join(',')).join(' '));
        else g.append('rect').attr('class', 'selring').attr('x', -(hw + 5)).attr('y', -(hh + 5)).attr('width', (hw + 5) * 2).attr('height', (hh + 5) * 2).attr('rx', 14);
      }   // (corner resize grip removed per feedback — scale via right-click → Size ±)
      // BPMN terminal rings — START (green, left edge) · END (slate, thicker, right edge); derived from flow topology
      if (hasOut.has(d.id) && !hasIn.has(d.id)) g.append('circle').attr('class', 'terminal start').attr('cx', -hw - 12).attr('cy', 0).attr('r', 6).append('title').text('START — no incoming edge');
      if (hasIn.has(d.id) && !hasOut.has(d.id)) g.append('circle').attr('class', 'terminal end').attr('cx', hw + 12).attr('cy', 0).attr('r', 7).append('title').text('END — no outgoing edge');
      // connection port (right edge) — on the outer group so the hover lift doesn't move the wire anchor
      g.append('circle').attr('class', 'port').attr('cx', hw).attr('cy', 0).attr('r', 5);
      g.append('circle').attr('class', 'port-hit').attr('cx', hw).attr('cy', 0).attr('r', 14)
        .on('pointerdown', (e) => beginWire(e, d))
        .on('pointerenter', () => { const t = d3.zoomTransform(svgN), pt = t.apply([d.x + hw + 16, d.y - 26]); showDragPortCoach(pt[0], pt[1]); })   // one-time "drag to connect" coachmark
        .on('click', (e) => { if (portArmed) e.stopPropagation(); portArmed = false; });   // only swallow the click that began a wire; otherwise let it reach the node
      // knowledge port (bottom edge) — drag out to cite a source-of-truth node (ghost appears in the tray below)
      if (d.type !== 'reference') {
        g.append('circle').attr('class', 'port port-know').attr('cx', 0).attr('cy', hh).attr('r', 5);
        g.append('circle').attr('class', 'port-hit port-know-hit').attr('cx', 0).attr('cy', hh).attr('r', 14)
          .on('pointerdown', (e) => beginKnowWire(e, d))
          .on('click', (e) => { if (portArmed) e.stopPropagation(); portArmed = false; });
      }
    });
    // staggered deal-in: freshly-entering nodes pop left→right in a wave (delay only; reuses the pop keyframe, capped so 30 nodes stay snappy)
    const entering = sel.filter(d => !dragging && !seen.has(d.id));
    if (!entering.empty()) {
      const rank = new Map(entering.data().slice().sort((a, b) => a.x - b.x).map((d, i) => [d.id, i]));
      entering.select('.node-inner').style('animation-delay', d => Math.min((rank.get(d.id) || 0) * 38, 380) + 'ms');
    }
    allNodes.forEach(n => seen.add(n.id));   // mark ALL (incl. culled) seen so panning a node into view doesn't replay its enter animation
    if (seen.size > allNodes.length) { const live = new Set(allNodes.map(n => n.id)); for (const id of seen) if (!live.has(id)) seen.delete(id); }   // prune archived/removed ids so `seen` can't grow unbounded across a long single-map session

    // ---- knowledge trays: a node's [[…]] citations hang BELOW it (bottom = the knowledge axis, distinct from L→R flow) ----
    nodes.forEach(n => {
      const resolved = (n.refs || []).map(rf => { const hit = resolveRef(rf.target); return hit ? { ref: rf.target, name: hit.node.name, home: (MAPS.maps[hit.map] || {}).title || hit.map } : null; }).filter(Boolean);
      if (!resolved.length) return;
      const { hh } = baseHalf(n), ax = n.x, ay = n.y + hh, gap = 16;
      const tray = gNode.append('g').attr('class', 'tray');

      if (resolved.length === 1) {                                  // one source → a lone ghost mirror below the node
        const r = resolved[0], gw = Math.max(120, Math.min(220, r.name.length * 8 + 56)) / 2, gh = 21, cy = ay + gap + gh;
        tray.append('path').attr('class', 'ref-conn').attr('d', 'M' + ax + ',' + ay + ' L' + ax + ',' + (cy - gh));
        const g = tray.append('g').attr('class', 'ghost').attr('transform', 'translate(' + ax + ',' + cy + ')').on('click', e => { e.stopPropagation(); gotoRef(r.ref); }).on('mouseenter', e => showGhostPopover(r.ref, e.clientX, e.clientY)).on('mouseleave', hideGhostPopover);
        g.append('rect').attr('class', 'ghost-shape').attr('x', -gw).attr('y', -gh).attr('width', gw * 2).attr('height', gh * 2).attr('rx', 10);
        { const lab = g.append('text').attr('class', 'ghost-label').text(r.name); if (!dragging) fitText(lab, gw * 2 - 20); }
        const bd = g.append('g').attr('transform', 'translate(' + (-gw + 2) + ',' + (-gh + 2) + ')');
        bd.append('circle').attr('r', 8).attr('fill', 'var(--ref)'); bd.append('text').attr('class', 'typeglyph').attr('font-size', '10px').text('§');
        g.append('title').text('Source of truth — "' + r.name + '" in ' + r.home + '. Click to open.');
      } else {                                                       // several sources → a collapsible box of ghosts
        const boxW = 210, boxX = ax - boxW / 2, boxY = ay + gap, headerH = 26, rowH = 24, collapsed = !!n.refsCollapsed;
        const boxH = headerH + (collapsed ? 0 : resolved.length * rowH + 6);
        tray.append('path').attr('class', 'ref-conn').attr('d', 'M' + ax + ',' + ay + ' L' + ax + ',' + boxY);
        const box = tray.append('g').attr('transform', 'translate(' + boxX + ',' + boxY + ')');
        box.append('rect').attr('class', 'tray-box').attr('width', boxW).attr('height', boxH).attr('rx', 11);
        const head = box.append('g').style('cursor', 'pointer').on('click', e => { e.stopPropagation(); toggleRefs(n); });
        head.append('rect').attr('width', boxW).attr('height', headerH).attr('rx', 11).attr('fill', 'transparent');
        head.append('text').attr('class', 'tray-caret').attr('x', 12).attr('y', headerH / 2).text(collapsed ? '▸' : '▾');
        head.append('text').attr('class', 'tray-title').attr('x', 26).attr('y', headerH / 2).text('§ ' + resolved.length + ' sources');
        if (!collapsed) resolved.forEach((r, i) => {
          const row = box.append('g').attr('transform', 'translate(0,' + (headerH + i * rowH) + ')').style('cursor', 'pointer').on('click', e => { e.stopPropagation(); gotoRef(r.ref); }).on('mouseenter', e => showGhostPopover(r.ref, e.clientX, e.clientY)).on('mouseleave', hideGhostPopover);
          row.append('rect').attr('class', 'tray-row').attr('width', boxW).attr('height', rowH);
          row.append('circle').attr('cx', 16).attr('cy', rowH / 2).attr('r', 7).attr('fill', 'var(--ref)');
          row.append('text').attr('class', 'typeglyph').attr('x', 16).attr('y', rowH / 2).attr('font-size', '9px').text('§');
          const nameSel = row.append('text').attr('class', 'tray-name').attr('x', 30).attr('y', rowH / 2).text(r.name);
          if (!dragging) fitText(nameSel, boxW - 30 - 12);   // no ↗home label → name gets the full row width
        });
      }
    });

    updateBreadcrumb();
    syncLibToggle();
    // (selection toolbar + minimap removed per feedback — right-click context menu covers color/type/gate/link/archive)
    { const eb = document.getElementById('empty-state'); if (eb) eb.hidden = !(map() && !map().nodes.length); }   // first-run hint on an empty map
    renderLint();   // live validation badge
    renderNodeInfo();   // node info panel (single-select) — last tail consumer
  }

  function ripple(x, y, col) {   // transient pulse in the never-cleared gWire so render() can't kill it mid-animation
    const c = gWire.append('circle').attr('class', 'ripple').attr('cx', x).attr('cy', y).attr('r', 8);
    if (col) c.style('stroke', col);
    const node = c.node();
    node.addEventListener('animationend', () => c.remove());
    setTimeout(() => { try { c.remove(); } catch (_) {} }, 800);   // fallback so they never accumulate
  }
  function pulseNode(id) { const n = byId(id); if (n && motionAllowed()) ripple(n.x, n.y, accent(n)); }   // one-shot "this changed" confirmation on a style/type edit (gWire → survives render, gated by motionAllowed)
  function traceEdge(a, b) {   // one-shot tracer that draws itself along a new edge's curve on a successful connect (gWire = never cleared)
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const p = gWire.append('path').attr('class', 'edge-trace').attr('d', edgePath(rightPort(a), leftPort(b), 0).d);
    const L = p.node().getTotalLength();
    p.style('stroke-dasharray', L).style('stroke-dashoffset', L).style('stroke', accent(b));
    p.node().addEventListener('animationend', () => p.remove());
    setTimeout(() => { try { p.remove(); } catch (_) {} }, 900);
  }

  function selectClick(e, id) {   // shift/cmd/ctrl-click extends the selection; a plain click replaces it
    if (e && (e.shiftKey || e.metaKey || e.ctrlKey)) { if (selection.has(id)) selection.delete(id); else selection.add(id); }
    else { selection.clear(); selection.add(id); }
  }
  function clearSelection() { const had = selection.size || niOpenId; niOpenId = null; infoStack.length = 0; selection.clear(); if (had) render(); }   // deselect also closes the info panel
  function selNodes() { return (map() ? map().nodes : []).filter(n => selection.has(n.id)); }
  function persistPos(nodes) { if (SERVER) api('/api/poslist', { map: cur, positions: nodes.map(n => ({ path: repoRel(n.url), x: Math.round(n.x), y: Math.round(n.y) })) }).then(flushPending); }
  function copySelection() {   // serialize selected nodes + their internal edges (item 11)
    const ns = selNodes(); if (!ns.length) { clipboard = null; return; }
    const ids = new Set(ns.map(n => n.id));
    const edges = (map() ? map().edges : []).filter(e => ids.has(e.from) && ids.has(e.to));
    clipboard = { nodes: ns.map(n => ({ name: n.name, type: n.type, scale: n.scale, hl: n.hl, color: n.color, gate: n.gate, lane: n.lane, link_map: n.link_map, summary: n.summary, tags: n.tags, status: n.status, x: n.x, y: n.y })), edges: edges.map(e => ({ from: ns.findIndex(n => n.id === e.from), to: ns.findIndex(n => n.id === e.to), label: e.label, bend: e.bend, color: e.color, route: e.route })) };
  }
  async function pasteSelection() {   // re-create nodes (preserving relative layout) then re-wire internal edges — one atomic batch: single undo, single rebuild, styling preserved
    if (!clipboard || !clipboard.nodes.length || !cur || !SERVER) return;
    const cn = clipboard.nodes, minX = Math.min(...cn.map(n => n.x)), minY = Math.min(...cn.map(n => n.y));
    const center = viewCenter(), dx = center.x - minX + 30, dy = center.y - minY + 30;
    const j = await api('/api/add-batch', { map: cur, nodes: cn.map(n => ({ title: n.name + ' copy', type: n.type, x: Math.round(n.x + dx), y: Math.round(n.y + dy), note: '', scale: n.scale, hl: n.hl, color: n.color, gate: n.gate, lane: n.lane, link_map: n.link_map, summary: n.summary, tags: n.tags, status: n.status })) });
    const slugs = (j.ok && j.created) ? j.created.map(c => c.split('/').pop().replace(/\.md$/, '')) : [];
    for (const e of clipboard.edges) { const fs = slugs[e.from], ts = slugs[e.to]; if (fs && ts) await api('/api/edge', { map: cur, from: fs, to: ts, label: e.label, bend: e.bend, color: e.color, route: e.route }); }
    flushPending();
  }

  // ---- marquee (shift-drag empty canvas) → multi-select ----
  let marqueeStart = null, marqueeRect = null;
  function startMarquee(e) {
    if (!e.shiftKey || e.target.closest('.node') || e.target.closest('.edgegrp') || e.target.closest('.frame-grab')) return;
    const [mx, my] = d3.pointer(e, canvas.node());
    selection.clear();
    marqueeStart = { x: mx, y: my };
    marqueeRect = gWire.append('rect').attr('class', 'marquee').attr('x', mx).attr('y', my).attr('width', 0).attr('height', 0);
  }
  function updateMarquee(e) {
    if (!marqueeStart || !marqueeRect) return;
    const [mx, my] = d3.pointer(e, canvas.node());
    marqueeRect.attr('x', Math.min(marqueeStart.x, mx)).attr('y', Math.min(marqueeStart.y, my)).attr('width', Math.abs(mx - marqueeStart.x)).attr('height', Math.abs(my - marqueeStart.y));
  }
  function endMarquee(e) {
    if (!marqueeStart) return;
    const [mx, my] = d3.pointer(e, canvas.node());
    const x1 = Math.min(marqueeStart.x, mx), x2 = Math.max(marqueeStart.x, mx), y1 = Math.min(marqueeStart.y, my), y2 = Math.max(marqueeStart.y, my);
    (map() ? map().nodes : []).forEach(n => { if (n.x >= x1 && n.x <= x2 && n.y >= y1 && n.y <= y2) selection.add(n.id); });
    if (marqueeRect) { marqueeRect.remove(); marqueeRect = null; }
    marqueeStart = null; render();
  }

  // ---- contextual mini-toolbar over the selection (items 8/9) ----
  let selToolbar = null;
  function positionSelToolbar() {
    if (dragging || !selection.size || !map()) { if (selToolbar) selToolbar.hidden = true; return; }
    const nodes = selNodes(); if (!nodes.length) { if (selToolbar) selToolbar.hidden = true; return; }
    if (!selToolbar) createSelToolbar();
    selToolbar.classList.toggle('multi', nodes.length >= 2);
    let minX = Infinity, maxX = -Infinity, minY = Infinity;
    nodes.forEach(n => { const { hw, hh } = halfExt(n); minX = Math.min(minX, n.x - hw); maxX = Math.max(maxX, n.x + hw); minY = Math.min(minY, n.y - hh); });
    const pt = d3.zoomTransform(svgN).apply([(minX + maxX) / 2, minY]);
    const w = selToolbar.offsetWidth || 240;
    selToolbar.hidden = false;
    selToolbar.style.left = Math.max(8, Math.min(window.innerWidth - w - 8, pt[0] - w / 2)) + 'px';
    selToolbar.style.top = Math.max(48, pt[1] - 52) + 'px';
  }
  function createSelToolbar() {
    selToolbar = document.createElement('div'); selToolbar.id = 'sel-toolbar';
    selToolbar.innerHTML = '<div class="sel-bar">' +
      '<button data-a="color" title="Cycle color">⬤</button>' +
      '<button data-a="type" title="Cycle type / shape">◇</button>' +
      '<button data-a="gate" title="Set gate for all selected">✓</button>' +
      '<button data-a="link" title="Link knowledge">§</button>' +
      '<span class="sel-sep"></span>' +
      '<span class="sel-align">' +
        '<button data-a="al" title="Align left">⇤</button><button data-a="ac" title="Align center (x)">↔</button><button data-a="ar" title="Align right">⇥</button>' +
        '<button data-a="at" title="Align top">⤒</button><button data-a="am" title="Align middle (y)">↕</button><button data-a="ab" title="Align bottom">⤓</button>' +
        '<button data-a="dx" title="Distribute horizontally">⇿</button><button data-a="dy" title="Distribute vertically">⤧</button>' +
      '</span>' +
      '<span class="sel-sep"></span>' +
      '<button data-a="archive" class="arch" title="Archive selection">−</button>' +
      '</div>';
    document.body.appendChild(selToolbar);
    requestAnimationFrame(() => positionSelToolbar());   // re-place once layout has settled (offsetWidth is 0 on the creation frame)
    selToolbar.querySelectorAll('button').forEach(b => b.onclick = () => selAction(b.dataset.a));
  }
  function selAction(a) {
    const nodes = selNodes(); if (!nodes.length) return;
    if (a === 'color') { const nx = nodes[0].color == null ? 0 : (nodes[0].color + 1 >= PAL_HEX.length ? null : nodes[0].color + 1); nodes.forEach(n => { n.color = nx; if (SERVER) api('/api/node-style', { path: repoRel(n.url), color: nx }).then(flushPending); }); render(); }
    else if (a === 'type') { const order = ['step', 'decision', 'subprocess-link', 'reference']; const nx = order[(order.indexOf(nodes[0].type) + 1) % order.length]; nodes.forEach(n => { n.type = nx; if (SERVER) api('/api/type', { path: repoRel(n.url), type: nx }).then(flushPending); }); render(); }
    else if (a === 'gate') { const pt = d3.zoomTransform(svgN).apply([nodes[0].x, nodes[0].y - halfExt(nodes[0]).hh]); showNameInput(pt[0], pt[1], nodes[0].gate || '', v => { nodes.forEach(n => { n.gate = v; if (SERVER) api('/api/node-style', { path: repoRel(n.url), gate: v }).then(flushPending); }); render(); }); }
    else if (a === 'link') openKnowPick(nodes[0]);
    else if (a === 'archive') archiveSel(nodes);
    else if (a[0] === 'a') alignSel(a);
    else if (a[0] === 'd') distributeSel(a === 'dx' ? 'x' : 'y');
  }
  async function archiveSel(nodes) {
    if (!SERVER || !nodes.length) return;
    if (!confirm('Archive ' + nodes.length + ' node' + (nodes.length === 1 ? '' : 's') + '?')) return;
    for (const n of nodes) { const j = await api('/api/archive', { path: repoRel(n.url) }); if (j.ok) applyMaps(j.maps); }
    selection.clear(); render();
  }
  function alignSel(a) {
    const nodes = selNodes(); if (nodes.length < 2) return;
    const avg = arr => arr.reduce((s, v) => s + v, 0) / arr.length;
    if (a === 'al') { const r = Math.min(...nodes.map(n => n.x - halfExt(n).hw)); nodes.forEach(n => n.x = r + halfExt(n).hw); }
    else if (a === 'ac') { const r = avg(nodes.map(n => n.x)); nodes.forEach(n => n.x = r); }
    else if (a === 'ar') { const r = Math.max(...nodes.map(n => n.x + halfExt(n).hw)); nodes.forEach(n => n.x = r - halfExt(n).hw); }
    else if (a === 'at') { const r = Math.min(...nodes.map(n => n.y - halfExt(n).hh)); nodes.forEach(n => n.y = r + halfExt(n).hh); }
    else if (a === 'am') { const r = avg(nodes.map(n => n.y)); nodes.forEach(n => n.y = r); }
    else if (a === 'ab') { const r = Math.max(...nodes.map(n => n.y + halfExt(n).hh)); nodes.forEach(n => n.y = r - halfExt(n).hh); }
    persistPos(nodes); render();
  }
  function distributeSel(axis) {
    const nodes = selNodes().sort((p, q) => axis === 'x' ? p.x - q.x : p.y - q.y); if (nodes.length < 3) return;
    const key = axis === 'x' ? 'x' : 'y';
    const mn = Math.min(...nodes.map(n => n[key])), mx = Math.max(...nodes.map(n => n[key])), gap = (mx - mn) / (nodes.length - 1);
    nodes.forEach((n, i) => n[key] = mn + gap * i);
    persistPos(nodes); render();
  }

  // ---- snap-on-drag + alignment guides (item 10) ----
  let snapGuide = null; const SNAP_DIST = 16;
  let snapCands = null;   // candidate node geometry, cached once per drag-start (other nodes don't move during a single-node drag) instead of re-scanning + re-measuring every tick
  function snapCandsFor(d) { return (map() ? map().nodes : []).filter(n => n.id !== d.id).map(n => ({ x: n.x, y: n.y, hw: halfExt(n).hw })); }
  function checkSnap(d) {
    const k = d3.zoomTransform(svgN).k, thr = SNAP_DIST / k, dhw = halfExt(d).hw;
    let bestX = null, bestY = null;
    (snapCands || snapCandsFor(d)).forEach(n => {
      const nhw = n.hw;
      if (Math.abs(d.x - n.x) < thr) bestX = n.x;
      else if (Math.abs((d.x + dhw) - (n.x - nhw)) < thr) bestX = n.x - nhw - dhw;
      else if (Math.abs((d.x - dhw) - (n.x + nhw)) < thr) bestX = n.x + nhw + dhw;
      if (Math.abs(d.y - n.y) < thr) bestY = n.y;
    });
    if (snapGuide) { snapGuide.remove(); snapGuide = null; }
    if (bestX === null && bestY === null) return null;
    if (motionAllowed()) {
      snapGuide = gWire.append('g').attr('class', 'snap-guides');
      if (bestX !== null) snapGuide.append('line').attr('x1', bestX).attr('y1', d.y - 60).attr('x2', bestX).attr('y2', d.y + 60);
      if (bestY !== null) snapGuide.append('line').attr('x1', d.x - 60).attr('y1', bestY).attr('x2', d.x + 60).attr('y2', bestY);
    }
    return { x: bestX !== null ? bestX : d.x, y: bestY !== null ? bestY : d.y };
  }
  function onNodeClick(d) {   // single-click (deferred): a link node navigates into its sub-map; a plain node already got its ripple
    const live = byId(d.id); if (!live) return; d = live;   // re-resolve against the CURRENT map: a debounced click can fire after a map switch / SSE moved the node
    if (d.link_map) { if (EMBED) drillTo(d.link_map); else openPip(d.link_map); }   // top level: float a window; inside a window: drill in place
  }
  function onNodeOpen(d, ev) {   // open = NodeInfo panel (left) + editor drawer (right), together
    const live = byId(d.id); if (!live) return; d = live;
    closeCtx(); openNodeInfo(d); openEditor(d);
  }

  // ---- drag-to-connect ----
  function beginWire(e, d) {
    if (!SERVER) return;
    e.stopPropagation(); e.preventDefault();
    try { svgN.setPointerCapture(e.pointerId); } catch (_) {}
    const { hw } = halfExt(d);
    wire = { fromId: d.id, x0: d.x + hw, y0: d.y, moved: false };
    portArmed = true;
  }
  function beginKnowWire(e, d) {   // drag from the bottom port → cite a source-of-truth node
    if (!SERVER) return;
    e.stopPropagation(); e.preventDefault();
    try { svgN.setPointerCapture(e.pointerId); } catch (_) {}
    const bp = bottomPort(d);
    wire = { fromId: d.id, kind: 'know', x0: bp.x, y0: bp.y, moved: false };
    portArmed = true;
  }
  svgN.addEventListener('pointermove', e => {
    if (!wire || !wire.active && !wire.fromId) return;
    const [mx, my] = d3.pointer(e, canvas.node());
    if (!wire.moved && Math.hypot(mx - wire.x0, my - wire.y0) < 4) return;   // threshold
    wire.active = true; wire.moved = true;
    wire.dropX = mx; wire.dropY = my; wire.screenX = e.clientX; wire.screenY = e.clientY;   // remember drop coords
    const src = byId(wire.fromId); if (!src) return;
    if (wire.kind === 'know') {   // knowledge-link drag: magnetic to nearest not-yet-cited node; dashed line in the ref color
      const cited = new Set((src.refs || []).map(r => r.target));
      const MAG = 64; let nearest = null, nd = Infinity;
      (map() ? map().nodes : []).forEach(n => { if (n.id === wire.fromId || cited.has(n.id)) return; const dist = Math.hypot(mx - n.x, my - n.y); if (dist < MAG && dist < nd) { nearest = n; nd = dist; } });
      let tgt = nearest || dropTarget(e);
      if (tgt && (tgt.id === wire.fromId || cited.has(tgt.id))) tgt = null;   // can't cite self or an already-cited node
      const endPt = tgt ? { x: tgt.x, y: tgt.y - baseHalf(tgt).hh } : { x: mx, y: my };
      wirePath.attr('d', edgePath(bottomPort(src), endPt, 0).d).style('stroke', 'var(--ref)').style('stroke-dasharray', '5 4');
      wire.targetId = tgt ? tgt.id : null; wire.valid = !!tgt;
      gNode.selectAll('g.node').classed('attracting', n => nearest && n.id === nearest.id).classed('drop-ok', n => tgt && n.id === tgt.id);
      return;
    }
    const edges = map() ? map().edges : [];
    const dup = id => edges.some(ed => (ed.from === wire.fromId && ed.to === id) || (ed.from === id && ed.to === wire.fromId));
    const MAG = 60; let nearest = null, nd = Infinity;   // magnetic: snap to the nearest valid target within radius
    (map() ? map().nodes : []).forEach(n => { if (n.id === wire.fromId) return; const lp = leftPort(n), dist = Math.hypot(mx - lp.x, my - lp.y); if (dist < MAG && dist < nd && !dup(n.id)) { nearest = n; nd = dist; } });
    const pointed = dropTarget(e), tgt = nearest || pointed;
    let col = 'var(--link)', valid = true;
    if (tgt) {
      if (tgt.id === wire.fromId) valid = !edges.some(ed => ed.from === tgt.id && ed.to === tgt.id);   // self-loop ok if none exists yet
      else valid = !dup(tgt.id);
      if (!valid) col = '#e11d48';
    }
    const endPt = nearest ? leftPort(nearest) : { x: mx, y: my };
    wirePath.attr('d', edgePath(rightPort(src), endPt, 0).d).style('stroke', col).style('stroke-dasharray', null);   // green = valid · red = self/duplicate
    wire.targetId = tgt ? tgt.id : null; wire.valid = valid;
    gNode.selectAll('g.node').classed('attracting', d => nearest && d.id === nearest.id).classed('drop-ok', d => tgt && d.id === tgt.id && valid);
  });
  function endWire(e, cancelled) {
    if (!wire) return;
    const was = wire, fromId = wire.fromId, dropX = wire.dropX, dropY = wire.dropY;
    wirePath.attr('d', '').style('stroke', '').style('stroke-dasharray', null); gNode.selectAll('g.node').classed('drop-ok', false).classed('attracting', false);
    try { svgN.releasePointerCapture(e.pointerId); } catch (_) {}
    portArmed = false;                                    // pointerup precedes any click; a finished/aborted wire never swallows the next tap
    wire = null;                                          // clear BEFORE addEdge/flushPending so guards release
    if (cancelled || !was.active) { flushPending(); return; }
    if (was.kind === 'know') {                            // knowledge-link drop: cite the target node (or open the picker on empty)
      const src = byId(fromId);
      if (was.targetId) { const tgt = byId(was.targetId); if (src && tgt) { ripple(tgt.x, tgt.y, 'var(--ref)'); api('/api/link-knowledge', { map: cur, path: repoRel(src.url), ref: tgt.id, label: tgt.name }).then(j => { if (j && j.ok) applyMaps(j.maps); else flushPending(); }); } else flushPending(); }
      else if (src) openKnowPick(src);                    // dropped on empty → search the SoT library
      else flushPending();
      return;
    }
    const fs = nidSlug()[fromId]; if (!fs) { flushPending(); return; }
    if (was.targetId && was.valid) {                      // connect to an existing node (or self-loop)
      const ts = nidSlug()[was.targetId], tgt = byId(was.targetId), src = byId(fromId);
      if (ts) { if (tgt && tgt.id !== fromId) { ripple(tgt.x, tgt.y, accent(tgt)); if (src) traceEdge(src, tgt); } addEdge(fs, ts); } else flushPending();
    } else if (!was.targetId && dropX != null) {          // drop on empty canvas → create a node here + wire it in one step
      showNameInput(was.screenX || window.innerWidth / 2, was.screenY || window.innerHeight / 2, '', async title => {
        if (!title) { flushPending(); return; }
        const j = await api('/api/add', { map: cur, title, type: 'step', x: Math.round(dropX), y: Math.round(dropY), note: '' });
        if (!j.ok) { alert('Add: ' + j.error); flushPending(); return; }
        const newSlug = j.created ? j.created.split('/').pop().replace(/\.md$/, '') : null;
        applyMaps(j.maps);
        if (newSlug) addEdge(fs, newSlug); else flushPending();
      });
    } else flushPending();
  }
  svgN.addEventListener('pointerup', e => endWire(e, false));
  svgN.addEventListener('pointercancel', e => endWire(e, true));   // touch palm-reject / gesture takeover
  svgN.addEventListener('lostpointercapture', e => { if (wire) endWire(e, true); });
  let longPressTimer = null;   // touch: long-press a node → context menu (item 47)
  svgN.addEventListener('pointerdown', e => {
    const nodeEl = e.target.closest && e.target.closest('.node');
    if (!nodeEl || (e.target.closest && e.target.closest('.port-hit'))) return;
    const dd = d3.select(nodeEl).datum();
    if (dd) {   // DOUBLE-TAP a node → open the edit panel. Detected here (stable svg, capture phase) by id+timing, before render() can recreate the element.
      if (lastTapId === dd.id && (e.timeStamp - lastTapAt) < 400) {
        lastTapId = null; lastTapAt = 0;
        suppressClick = true; setTimeout(() => { suppressClick = false; }, 450);   // eat the trailing click(s); auto-clear so it can't get stuck if no click fires
        clearTimeout(clickTimer); clickTimer = null; clearTimeout(longPressTimer); longPressTimer = null;
        closeCtx(); const dn = byId(dd.id) || dd;
        if (dn.link_map) { if (EMBED) drillTo(dn.link_map); else openPip(dn.link_map); }   // linked node → open the sub-map instead of the editor
        else { openNodeInfo(dn); openEditor(dn); }   // double-tap opens BOTH: the NodeInfo panel (left) + the editor drawer (right)
        return;
      }
      lastTapId = dd.id; lastTapAt = e.timeStamp;
    }
    longPressTimer = setTimeout(() => { longPressTimer = null; const d = d3.select(nodeEl).datum(); if (d) { clearTimeout(clickTimer); clickTimer = null; openCtx({ clientX: e.clientX, clientY: e.clientY, preventDefault() {} }, d); } }, 500);
  }, true);
  ['pointermove', 'pointerup', 'pointercancel'].forEach(t => svgN.addEventListener(t, () => { if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null; } }));
  function dropTarget(e) {
    const el = document.elementFromPoint(e.clientX, e.clientY);
    const g = el && el.closest && el.closest('g.node');
    return g ? d3.select(g).datum() : null;
  }

  // ---- edge ops ----
  async function addEdge(fromSlug, toSlug) {   // omit label → server keeps existing on reconnect
    if (!SERVER || !fromSlug || !toSlug) { flushPending(); return; }
    const j = await api('/api/edge', { map: cur, from: fromSlug, to: toSlug });
    if (!j.ok) { alert('Edge: ' + j.error); flushPending(); return; }
    applyMaps(j.maps);
    const src = (map() ? map().nodes : []).find(n => n.slug === fromSlug);
    if (src && src.type === 'decision' && fromSlug !== toSlug) promptDecisionLabel(fromSlug, toSlug);   // a decision branch needs a Yes/No label
    else flushPending();
  }
  function promptDecisionLabel(fromSlug, toSlug) {   // inline overlay: type a label, or press Y (Yes/green) / N (No/red)
    const inp = document.getElementById('edge-label-input');
    inp.style.left = (window.innerWidth / 2) + 'px'; inp.style.top = (window.innerHeight / 2 - 40) + 'px';
    inp.value = ''; inp.placeholder = 'branch label — or Y = Yes · N = No'; inp.hidden = false; inp.focus();
    const apply = async (label, color) => {
      inp.onkeydown = null; inp.onblur = null; inp.hidden = true; inp.placeholder = 'label…';
      if (SERVER && label) { const k = await api('/api/edge', { map: cur, from: fromSlug, to: toSlug, label, color }); if (k.ok) applyMaps(k.maps); }
      flushPending();
    };
    inp.onkeydown = ev => {
      if (ev.key === 'Enter') apply(inp.value.trim(), null);
      else if (ev.key === 'Escape') { inp.onkeydown = null; inp.onblur = null; inp.hidden = true; inp.placeholder = 'label…'; flushPending(); }
      else if (ev.key.toLowerCase() === 'y' && !inp.value) { ev.preventDefault(); apply('Yes', 7); }   // PAL_HEX[7] = green
      else if (ev.key.toLowerCase() === 'n' && !inp.value) { ev.preventDefault(); apply('No', 6); }    // PAL_HEX[6] = red
    };
    inp.onblur = () => apply(inp.value.trim(), null);
  }
  async function cycleEdgeRoute(e) { if (!SERVER) return; const next = (e.route || 'bezier') === 'bezier' ? 'smooth' : 'bezier'; const ns = nidSlug(); const j = await api('/api/edge', { map: cur, from: ns[e.from], to: ns[e.to], route: next }); if (j.ok) applyMaps(j.maps); }
  async function deleteEdge(e) { if (!SERVER) return; if (!confirm('Delete this connection?')) return; const ns = nidSlug(); const j = await api('/api/edge', { map: cur, from: ns[e.from], to: ns[e.to], remove: true }); if (j.ok) applyMaps(j.maps); }
  async function cycleEdgeColor(e) { if (!SERVER) return; const next = e.color == null ? 0 : (e.color + 1 >= PAL_HEX.length ? null : e.color + 1); const ns = nidSlug(); const j = await api('/api/edge', { map: cur, from: ns[e.from], to: ns[e.to], color: next }); if (j.ok) applyMaps(j.maps); }
  function editEdgeLabel(e, p1, c1, c2, p2) {
    const inp = document.getElementById('edge-label-input');
    const mid = cubicMid(p1, c1, c2, p2), t = d3.zoomTransform(svgN), pt = t.apply([mid.x, mid.y]);
    const sx = Math.max(70, Math.min(window.innerWidth - 70, pt[0])), sy = Math.max(16, Math.min(window.innerHeight - 16, pt[1]));
    inp.style.left = sx + 'px'; inp.style.top = sy + 'px'; inp.value = e.label || ''; inp.hidden = false; inp.focus(); inp.select();
    const ns = nidSlug();
    const commit = async (save) => {
      inp.onkeydown = null; inp.onblur = null; inp.hidden = true;
      if (save && SERVER) { const j = await api('/api/edge', { map: cur, from: ns[e.from], to: ns[e.to], label: inp.value.trim() }); if (j.ok) applyMaps(j.maps); }
      flushPending();
    };
    inp.onkeydown = ev => { if (ev.key === 'Enter') commit(true); else if (ev.key === 'Escape') commit(false); };
    inp.onblur = () => commit(true);
  }

  // ---- node create / rename (inline) ----
  function showNameInput(sx, sy, value, onCommit) {
    const inp = document.getElementById('name-input');
    sx = Math.max(80, Math.min(window.innerWidth - 80, sx)); sy = Math.max(16, Math.min(window.innerHeight - 16, sy));   // keep on-screen
    inp.style.left = sx + 'px'; inp.style.top = sy + 'px'; inp.value = value || ''; inp.hidden = false; inp.focus(); inp.select();
    const done = (save) => { inp.onkeydown = null; inp.onblur = null; inp.hidden = true; if (save) onCommit(inp.value.trim()); flushPending(); };
    inp.onkeydown = ev => { if (ev.key === 'Enter') done(true); else if (ev.key === 'Escape') done(false); };
    inp.onblur = () => done(true);
  }
  function quickAdd(canvasX, canvasY, sx, sy) {
    if (!SERVER || !cur) return;
    showNameInput(sx, sy, '', async title => {
      if (!title) return;
      const j = await api('/api/add', { map: cur, title, type: 'step', x: canvasX, y: canvasY, note: '' });
      if (j.ok) applyMaps(j.maps); else alert('Add: ' + j.error);
    });
  }
  function openRename(d) {
    if (!SERVER) return; closeCtx();
    const t = d3.zoomTransform(svgN), [sx, sy] = t.apply([d.x, d.y]);
    showNameInput(sx, sy, d.name, async title => {
      if (!title || title === d.name) return;
      const j = await api('/api/rename', { path: repoRel(d.url), title }); if (j.ok) { applyMaps(j.maps); resyncEditorAfterRename(d.id, j.path, title); } else alert('Rename: ' + j.error);
    });
  }

  // ---- context menu (right-click): type · size · highlight · color · link · archive ----
  let ctxNode = null;
  function openCtx(e, d) {
    ctxNode = d; closeEditor();
    document.getElementById('ctx-title').textContent = d.name;
    document.querySelectorAll('#ctx-types button').forEach(b => b.classList.toggle('sel', b.dataset.t === d.type));
    document.getElementById('ctx-size').textContent = Math.round((d.scale || 1) * 100) + '%';
    document.getElementById('ctx-hl').classList.toggle('on', !!d.hl);
    fillSwatches(d);
    fillLinkSelect(); document.getElementById('ctx-linkmap').value = d.link_map || '';
    document.getElementById('ctx-gate').value = d.gate || '';
    const m = document.getElementById('ctx');
    m.style.left = '-9999px'; m.style.top = '0px'; m.hidden = false;   // unhide off-screen so we can measure actual height before clamping
    const r = m.getBoundingClientRect();
    m.style.left = Math.max(8, Math.min(window.innerWidth - r.width - 8, e.clientX)) + 'px';
    m.style.top = Math.max(8, Math.min(window.innerHeight - r.height - 8, e.clientY)) + 'px';
    m.tabIndex = -1; m.focus();   // move focus into the menu so its Tab focus-trap works and a keyboard user isn't stranded
  }
  function closeCtx() { const m = document.getElementById('ctx'); const ae = document.activeElement; if (ae && m.contains(ae)) ae.blur(); m.hidden = true; ctxNode = null; }   // blur so focus leaves the hidden menu → keyboard shortcuts stay alive
  function fillSwatches(d) {
    const box = document.getElementById('ctx-colors'); box.innerHTML = '';
    const clear = document.createElement('div'); clear.className = 'sw clear' + (d.color == null ? ' sel' : ''); clear.textContent = '○'; clear.title = 'Default (lane/type)';
    clear.onclick = () => ctxColor(null); box.appendChild(clear);
    PAL_HEX.forEach((hex, i) => { const s = document.createElement('div'); s.className = 'sw' + (d.color === i ? ' sel' : ''); s.style.background = hex; s.onclick = () => ctxColor(i); box.appendChild(s); });
  }
  async function nodeStyle(patch) { if (!ctxNode || !SERVER) return; const id = ctxNode.id; const j = await api('/api/node-style', Object.assign({ path: repoRel(ctxNode.url) }, patch)); if (j.ok) { applyMaps(j.maps); pulseNode(id); } else alert(j.error); }
  async function ctxType(t) { if (!ctxNode || !SERVER) return; const p = repoRel(ctxNode.url), id = ctxNode.id; closeCtx(); const j = await api('/api/type', { path: p, type: t }); if (j.ok) { applyMaps(j.maps); pulseNode(id); } else alert(j.error); }
  function ctxSize(dir) { if (!ctxNode) return; const s = Math.max(0.5, Math.min(2.5, (ctxNode.scale || 1) * (dir > 0 ? 1.15 : 1 / 1.15))); document.getElementById('ctx-size').textContent = Math.round(s * 100) + '%'; ctxNode.scale = s; nodeStyle({ scale: +s.toFixed(3) }); }
  function ctxHighlight() { if (!ctxNode) return; const hl = !ctxNode.hl; ctxNode.hl = hl; document.getElementById('ctx-hl').classList.toggle('on', hl); nodeStyle({ hl }); }
  function ctxColor(i) { if (!ctxNode) return; ctxNode.color = i; fillSwatches(ctxNode); nodeStyle({ color: i }); }
  async function ctxLink(slug) { if (!ctxNode || !SERVER) return; const p = repoRel(ctxNode.url); closeCtx(); const j = await api('/api/link', { path: p, link_map: slug }); if (j.ok) applyMaps(j.maps); else alert(j.error); }
  async function ctxArchive() { if (!ctxNode || !SERVER) return; const n = ctxNode; closeCtx(); if (!confirm('Archive "' + n.name + '"?\nMoves the file to maps-data/.archive/ and removes it + its edges from this map.')) return; const j = await api('/api/archive', { path: repoRel(n.url) }); if (j.ok) applyMaps(j.maps); else alert('Archive: ' + j.error); }
  async function doUndo() { if (!SERVER) return; const j = await api('/api/undo', {}); if (j.ok) applyMaps(j.maps); }

  // ---- map switching + breadcrumb + hash ----
  let suppressHash = false;
  function setHash(slug) { suppressHash = true; location.hash = 'map=' + slug; setTimeout(() => suppressHash = false, 0); }
  function switchMap(slug, noHash) {
    if (!MAPS.maps[slug]) return;
    if (clickTimer) { clearTimeout(clickTimer); clickTimer = null; }
    selection.clear(); infoStack.length = 0; niOpenId = null; dragId = null; portArmed = false;                              // don't leak gesture/selection/back-stack/info-panel state into the next map
    if (wire) { wirePath.attr('d', '').style('stroke', ''); wire = null; }
    if (marqueeRect) { marqueeRect.remove(); marqueeRect = null; } marqueeStart = null;
    cur = slug; seen.clear(); document.getElementById('mapsel').value = slug; if (!noHash) setHash(slug);
    fit(true); render();   // instant-fit the new map, then render — no inter-map flash
  }
  function jumpMap(slug) { trail = []; switchMap(slug); }
  function drillTo(slug) { if (!MAPS.maps[slug]) { alert('Linked map "' + slug + '" not found.'); return; } trail.push(cur); switchMap(slug); }

  // ---- floating sub-map windows (picture-in-picture): a link node opens its map as a draggable/resizable iframe over the top map ----
  let pipZ = 0, pipCount = 0;
  const openPips = {};                                // slug -> window el (one window per map; re-focus if already open)
  function openPip(slug) {
    if (!MAPS.maps[slug]) { alert('Linked map "' + slug + '" not found.'); return; }
    if (openPips[slug]) { raisePip(openPips[slug]); return; }
    const host = document.getElementById('pips');
    const win = document.createElement('div'); win.className = 'pip';
    const off = (pipCount++ % 6) * 26, w = 480, h = 340;
    win.style.left = Math.max(16, (window.innerWidth - w) / 2 + off) + 'px';
    win.style.top = Math.max(64, (window.innerHeight - h) / 2 - 30 + off) + 'px';
    win.style.width = w + 'px'; win.style.height = h + 'px'; win.style.zIndex = ++pipZ;
    win.innerHTML =
      '<div class="pip-bar"><span class="pip-title"></span>' +
      '<button class="pip-max" title="Maximize — open this map full-screen">⤢</button>' +
      '<button class="pip-close" title="Close">✕</button></div>' +
      '<div class="pip-body"><iframe></iframe><div class="pip-cover"></div></div>' +
      '<div class="pip-resize"></div>';
    win.querySelector('.pip-title').textContent = (MAPS.maps[slug] || {}).title || slug;
    win.querySelector('iframe').src = '?embed=1#map=' + encodeURIComponent(slug);
    host.appendChild(win); openPips[slug] = win;
    win.addEventListener('pointerdown', () => raisePip(win), true);
    win.querySelector('.pip-close').onclick = () => closePip(slug);
    win.querySelector('.pip-max').onclick = () => { closePip(slug); drillTo(slug); };
    dragPip(win, win.querySelector('.pip-bar'), false);
    dragPip(win, win.querySelector('.pip-resize'), true);
  }
  function raisePip(win) { win.style.zIndex = ++pipZ; }
  function closePip(slug) { const w = openPips[slug]; if (!w) return; if (motionAllowed() && !w.classList.contains('closing')) { w.classList.add('closing'); setTimeout(() => { w.remove(); delete openPips[slug]; }, 200); } else { w.remove(); delete openPips[slug]; } }

  // ---- auto-tidy: lay nodes out left-to-right by flow order (longest-path layering) ----
  async function tidyLayout() {
    if (!SERVER) return;
    const m = map(); if (!m || !m.nodes.length) return;
    const nodes = m.nodes, edges = (m.edges || []).filter(e => e.from !== e.to);
    const oldPos = {}; nodes.forEach(n => oldPos[n.id] = { x: n.x, y: n.y });   // FLIP: remember where they were before re-layout
    const byid = {}; nodes.forEach(n => byid[n.id] = n);
    const out = {}, indeg = {}; nodes.forEach(n => { out[n.id] = []; indeg[n.id] = 0; });
    edges.forEach(e => { if (byid[e.from] && byid[e.to]) { out[e.from].push(e.to); indeg[e.to]++; } });
    const q = nodes.filter(n => indeg[n.id] === 0).map(n => n.id), order = [], deg = Object.assign({}, indeg);
    while (q.length) { const id = q.shift(); order.push(id); out[id].forEach(t => { if (--deg[t] === 0) q.push(t); }); }
    const layer = {}; nodes.forEach(n => layer[n.id] = 0);
    order.forEach(id => out[id].forEach(t => { layer[t] = Math.max(layer[t], layer[id] + 1); }));
    let maxL = 0; Object.values(layer).forEach(l => maxL = Math.max(maxL, l));
    const placed = new Set(order); nodes.forEach(n => { if (!placed.has(n.id)) layer[n.id] = maxL + 1; });   // cyclic leftovers → trailing column
    const cols = {}; nodes.forEach(n => (cols[layer[n.id]] = cols[layer[n.id]] || []).push(n));
    const COLGAP = 280, ROWGAP = 150, X0 = 160, CY = 320;
    Object.keys(cols).map(Number).sort((a, b) => a - b).forEach(L => {
      cols[L].forEach((n, i) => { n.x = X0 + L * COLGAP; n.y = CY + (i - (cols[L].length - 1) / 2) * ROWGAP; });
    });
    const target = {}; nodes.forEach(n => target[n.id] = { x: n.x, y: n.y });   // the new tidy positions
    if (motionAllowed()) {
      nodes.forEach(n => { n.x = oldPos[n.id].x; n.y = oldPos[n.id].y; });        // rewind to old, then glide
      const dur = 480, t0 = performance.now();
      const step = now => {
        const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 3);      // easeOutCubic
        nodes.forEach(n => { n.x = oldPos[n.id].x + (target[n.id].x - oldPos[n.id].x) * e; n.y = oldPos[n.id].y + (target[n.id].y - oldPos[n.id].y) * e; });
        render();                                                                 // nodes AND edges redraw from interpolated positions → they glide together
        if (p < 1) requestAnimationFrame(step); else { nodes.forEach(n => { n.x = target[n.id].x; n.y = target[n.id].y; }); render(); fit(true); }
      };
      requestAnimationFrame(step);
    } else { render(); fit(true); }
    api('/api/poslist', { map: cur, positions: nodes.map(n => ({ path: repoRel(n.url), x: Math.round(target[n.id].x), y: Math.round(target[n.id].y) })) }).then(flushPending);
  }
  function dragPip(win, handle, resize) {
    handle.addEventListener('pointerdown', e => {
      if (!resize && e.target.closest('button')) return;
      e.preventDefault(); e.stopPropagation(); raisePip(win); win.classList.add('busy');
      const sx = e.clientX, sy = e.clientY, ox = win.offsetLeft, oy = win.offsetTop, ow = win.offsetWidth, oh = win.offsetHeight;
      const mv = ev => {
        if (resize) { win.style.width = Math.max(240, ow + ev.clientX - sx) + 'px'; win.style.height = Math.max(170, oh + ev.clientY - sy) + 'px'; }
        else { win.style.left = Math.max(0, ox + ev.clientX - sx) + 'px'; win.style.top = Math.max(0, oy + ev.clientY - sy) + 'px'; }
      };
      const up = () => { win.classList.remove('busy'); window.removeEventListener('pointermove', mv); window.removeEventListener('pointerup', up); };
      window.addEventListener('pointermove', mv); window.addEventListener('pointerup', up);
    });
  }
  window.addEventListener('hashchange', () => { if (suppressHash) return; const m = (location.hash.match(/map=([^&]+)/) || [])[1]; if (m && MAPS.maps[m] && m !== cur) { trail = []; switchMap(m, true); } });
  function updateBreadcrumb() {   // always-visible path: ⌂ Home › parent › … › current (parents clickable; climbs the trail)
    const bc = document.getElementById('bcrumb'); bc.innerHTML = '';
    const crumb = (text, fn) => { const a = document.createElement('a'); a.textContent = text; a.tabIndex = 0; a.setAttribute('role', 'link'); a.onclick = fn; a.onkeydown = ev => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); fn(); } }; return a; };   // keyboard-accessible crumbs (were <a> with onclick, unreachable by Tab)
    bc.appendChild(crumb('⌂ Home', () => { trail = []; jumpMap(MAPS.order[0] || null); }));
    if (trail.length || cur) { const s = document.createElement('span'); s.className = 'sep'; s.textContent = '›'; bc.appendChild(s); }
    trail.forEach((slug, i) => {
      bc.appendChild(crumb((MAPS.maps[slug] || {}).title || slug, () => { const tgt = trail[i]; trail = trail.slice(0, i); switchMap(tgt || MAPS.order[0] || null); }));   // capture tgt BEFORE the slice empties trail[i], else every ancestor click lands on Home
      if (i < trail.length - 1 || cur) { const s = document.createElement('span'); s.className = 'sep'; s.textContent = '›'; bc.appendChild(s); }
    });
    if (cur) { const span = document.createElement('span'); span.textContent = (map() || {}).title || cur; bc.appendChild(span); }
  }
  // parent→child map relationships, derived from subprocess-link nodes (node.link_map points at a child map)
  function mapParents() {
    const parentOf = {};                                   // childSlug -> parentSlug (first referencing parent wins)
    MAPS.order.forEach(slug => {
      const m = MAPS.maps[slug]; if (!m) return;
      (m.nodes || []).forEach(n => { if (n.link_map && MAPS.maps[n.link_map] && n.link_map !== slug && !parentOf[n.link_map]) parentOf[n.link_map] = slug; });
    });
    return parentOf;
  }
  function fillMapSelect() {
    const s = document.getElementById('mapsel'); s.innerHTML = '';
    const parentOf = mapParents(), shown = new Set();
    const emit = (slug, depth) => {
      if (shown.has(slug) || !MAPS.maps[slug]) return; shown.add(slug);
      const o = document.createElement('option'); o.value = slug;
      o.textContent = (depth ? '  '.repeat(depth) + '└ ' : '') + ((MAPS.maps[slug] || {}).title || slug);
      s.appendChild(o);
      MAPS.order.forEach(c => { if (parentOf[c] === slug) emit(c, depth + 1); });   // children nest under parent, keep registry order
    };
    MAPS.order.forEach(slug => { if (!parentOf[slug]) emit(slug, 0); });   // top-level maps (not anyone's child)
    MAPS.order.forEach(slug => emit(slug, 0));                             // leftovers (cyclic link refs) — never drop a map
    if (cur) s.value = cur;
  }
  function fillLinkSelect() { const s = document.getElementById('ctx-linkmap'); s.innerHTML = ''; const o0 = document.createElement('option'); o0.value = ''; o0.textContent = 'Link to map…'; s.appendChild(o0); MAPS.order.filter(sl => sl !== cur).forEach(slug => { const o = document.createElement('option'); o.value = slug; o.textContent = '→ ' + ((MAPS.maps[slug] || {}).title || slug); s.appendChild(o); }); }

  function fit(instant) {
    if (!map() || !map().nodes.length || !window.innerWidth) return;   // bail if the viewport isn't laid out yet (iframe reports 0×0 pre-paint)
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    map().nodes.forEach(n => { const { hw, hh } = halfExt(n); minX = Math.min(minX, n.x - hw); maxX = Math.max(maxX, n.x + hw); minY = Math.min(minY, n.y - hh); maxY = Math.max(maxY, n.y + hh); });
    const w = window.innerWidth, h = window.innerHeight, k = Math.min(1.6, Math.min(w / (maxX - minX + 200), h / (maxY - minY + 220)));
    const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2;
    if (!isFinite(k) || k <= 0 || !isFinite(cx) || !isFinite(cy)) return;   // never push a NaN/degenerate transform
    const t = d3.zoomIdentity.translate(w / 2 - k * cx, h / 2 - k * cy).scale(k);
    if (instant) { svgN.__zoom = t; canvas.attr('transform', t); document.body.classList.toggle('lod-far', t.k < 0.55); }   // set d3 zoom state directly (reliable, synchronous) so the very next render() culls to the fitted viewport
    else svg.transition().duration(400).call(zoom.transform, t);   // animated for the Fit button
  }
  function zoomTo(scale) {   // zoom to an absolute level, keeping the current viewport center
    const w = window.innerWidth, h = window.innerHeight, t = d3.zoomTransform(svgN);
    const cx = (w / 2 - t.x) / t.k, cy = (h / 2 - t.y) / t.k;
    svg.transition().duration(300).call(zoom.transform, d3.zoomIdentity.translate(w / 2 - scale * cx, h / 2 - scale * cy).scale(scale));
  }
  function zoomToSelection() {
    if (!selection.size) { fit(); return; }
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    selection.forEach(id => { const n = byId(id); if (!n) return; const { hw, hh } = halfExt(n); minX = Math.min(minX, n.x - hw); maxX = Math.max(maxX, n.x + hw); minY = Math.min(minY, n.y - hh); maxY = Math.max(maxY, n.y + hh); });
    if (!isFinite(minX)) return;
    const w = window.innerWidth, h = window.innerHeight, k = Math.min(1.6, Math.min(w / (maxX - minX + 200), h / (maxY - minY + 220)));
    const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2;
    if (!isFinite(k) || k <= 0) return;
    svg.transition().duration(400).call(zoom.transform, d3.zoomIdentity.translate(w / 2 - k * cx, h / 2 - k * cy).scale(k));
  }
  function viewCenter() { const t = d3.zoomTransform(svgN); return { x: (window.innerWidth / 2 - t.x) / t.k, y: (window.innerHeight / 2 - t.y) / t.k }; }

  // ---- background boxes (frames) ----
  async function addFrame() {
    if (!SERVER || !cur) { alert('Create a map first.'); return; }
    const c = viewCenter();
    const j = await api('/api/frame', { map: cur, op: 'add', x: Math.round(c.x - 180), y: Math.round(c.y - 120), w: 360, h: 240, label: 'Group' });
    if (j.ok) applyMaps(j.maps); else alert('Box: ' + j.error);
  }
  function renameFrame(f) {
    if (!SERVER) return;
    const t = d3.zoomTransform(svgN), pt = t.apply([f.x + 80, f.y + 13]);
    showNameInput(pt[0], pt[1], f.label, async label => { const j = await api('/api/frame', { map: cur, op: 'set', id: f.id, label }); if (j.ok) applyMaps(j.maps); });
  }
  async function delFrame(f) {
    if (!SERVER) return;
    if (!confirm('Delete the box "' + f.label + '"?  (nodes inside are not affected)')) return;
    const j = await api('/api/frame', { map: cur, op: 'del', id: f.id }); if (j.ok) applyMaps(j.maps);
  }
  async function cycleFrameColor(f) {
    if (!SERVER) return;
    const j = await api('/api/frame', { map: cur, op: 'set', id: f.id, color: ((f.color || 0) + 1) % FRAME_PAL.length }); if (j.ok) applyMaps(j.maps);
  }

  // ---- notes drawer ----
  let edPath = null, edNode = null, edContentHash = null;
  function simpleHash(s) { let h = 0; const n = (s || '').replace(/\s+$/, ''); for (let i = 0; i < n.length; i++) h = ((h << 5) - h + n.charCodeAt(i)) | 0; return h.toString(16); }
  function stripFM(t) { const m = (t || '').match(/^---\r?\n[\s\S]*?\r?\n---\r?\n?/); return (m ? t.slice(m[0].length) : t).replace(/^\s*\n/, ''); }   // editor shows only the body (notes + H1); frontmatter is metadata, managed by the panel/drag/rename
  // rename title+slug by double-clicking the title in the drawer
  function renameFromDrawer(d) {
    const r = document.getElementById('ed-title').getBoundingClientRect();
    showNameInput(r.left + r.width / 2, r.top + 12, d.name, async title => {
      if (!title || title === d.name) return;
      const j = await api('/api/rename', { path: repoRel(d.url), title });
      if (j.ok) { applyMaps(j.maps); resyncEditorAfterRename(d.id, j.path, title); }
      else alert('Rename: ' + j.error);
    });
  }
  async function openEditor(d) {
    document.getElementById('exportpanel').hidden = true;
    edPath = repoRel(d.url); edNode = d;
    document.getElementById('ed-title').textContent = d.name; document.getElementById('ed-path').textContent = edPath;
    document.getElementById('ed-msg').textContent = 'Loading…'; document.getElementById('ed-text').value = ''; { const ed = document.getElementById('editor'); ed.classList.remove('exiting'); ed.hidden = false; const f = ed.querySelector('button,input,textarea'); if (f) f.focus(); }
    try { const r = await fetch('/api/doc?path=' + encodeURIComponent(edPath)); const j = await r.json();
      if (!j.ok) { document.getElementById('ed-msg').textContent = 'Error: ' + j.error; return; }
      const body = stripFM(j.content); document.getElementById('ed-text').value = body; edContentHash = simpleHash(body); document.getElementById('ed-msg').textContent = ''; renderRefs(body);
    } catch (e) { document.getElementById('ed-msg').textContent = 'Error: ' + e.message; }
  }
  async function resyncEditorAfterRename(nid, newPath, newTitle) {   // a rename rewrites the file's title: on disk — if the editor is open for that node, refresh its path + body so a later save can't revert the rename (stale editor content == old title)
    if (!edNode || edNode.id !== nid) return;
    if (newPath) { edPath = newPath; edNode.url = '../' + newPath; const ep = document.getElementById('ed-path'); if (ep) ep.textContent = newPath; }
    const et = document.getElementById('ed-title'); if (et && newTitle) et.textContent = newTitle;
    try { const r = await fetch('/api/doc?path=' + encodeURIComponent(edPath)); const j = await r.json(); if (j.ok) { const body = stripFM(j.content); document.getElementById('ed-text').value = body; edContentHash = simpleHash(body); renderRefs(body); } } catch (_) {}
  }
  function closeEditor() { edPath = null; edNode = null; edContentHash = null; const ed = document.getElementById('editor'); const ae = document.activeElement; if (ae && ed.contains(ae)) ae.blur(); document.getElementById('ed-refs').hidden = true; fadeOut(ed); renderNodeInfo(); }   // blur so focus leaves the hidden editor; re-show the info panel if the node is still selected
  function revalidateEditor() {   // an SSE re-render may have archived/renamed the open node
    if (!edPath) return;
    const node = (map() ? map().nodes : []).find(n => repoRel(n.url) === edPath);
    if (node) document.getElementById('ed-title').textContent = node.name;
    else document.getElementById('ed-msg').textContent = 'This node was changed or removed elsewhere — reopen to edit.';
  }
  async function saveDoc() {
    const msg = document.getElementById('ed-msg'), text = document.getElementById('ed-text').value;
    if (edContentHash !== null && edPath) {   // detect an external change before overwriting (item 49) — compare the BODY only (frontmatter is owned by the panel/drag, not the editor)
      try { const r = await fetch('/api/doc?path=' + encodeURIComponent(edPath)); const k = await r.json(); if (k.ok && simpleHash(stripFM(k.content)) !== edContentHash) { showSaveConflict(stripFM(k.content)); return; } } catch (_) {}
    }
    msg.textContent = 'Saving…'; const j = await api('/api/save-body', { path: edPath, body: text });
    if (!j.ok) { msg.textContent = 'Error: ' + j.error; announce('Save failed: ' + j.error); return; }
    edContentHash = simpleHash(text); msg.textContent = 'Saved ✓'; announce('Saved'); if (j.maps) applyMaps(j.maps);
  }
  function showSaveConflict(diskContent) {
    document.querySelectorAll('.save-conflict').forEach(el => el.remove());
    const bar = document.createElement('div'); bar.className = 'save-conflict';
    const t = document.createElement('span'); t.textContent = 'Changed on disk —'; bar.appendChild(t);
    const ow = document.createElement('button'); ow.textContent = 'Overwrite'; ow.onclick = async () => { bar.remove(); edContentHash = null; await saveDoc(); }; bar.appendChild(ow);
    const rl = document.createElement('button'); rl.textContent = 'Reload'; rl.onclick = () => { bar.remove(); document.getElementById('ed-text').value = diskContent; edContentHash = simpleHash(diskContent); renderRefs(diskContent); document.getElementById('ed-msg').textContent = 'Reloaded from disk'; announce('Reloaded from disk'); }; bar.appendChild(rl);
    document.body.appendChild(bar); document.getElementById('ed-msg').textContent = 'Conflict — file changed elsewhere';
  }

  // ---- cross-map wiki references: a node body may cite [[nid|label]] (any map) — same syntax as the wiki ----
  let _nidIx = null;                                  // memoized across a render; invalidated on applyMaps (so trays don't rebuild it per ref per frame)
  function nidIndex() {   // nid -> {map, node} across ALL maps
    if (_nidIx) return _nidIx;
    const ix = {};
    MAPS.order.forEach(slug => { const m = MAPS.maps[slug]; if (!m) return; (m.nodes || []).forEach(n => { if (n.id && !ix[n.id]) ix[n.id] = { map: slug, node: n }; }); });
    return (_nidIx = ix);
  }
  function resolveRef(target) {   // by nid first (rename-safe), then fall back to slug/name
    const ix = nidIndex(); if (ix[target]) return ix[target];
    let hit = null; MAPS.order.some(slug => { const n = (MAPS.maps[slug].nodes || []).find(x => x.slug === target || x.name === target); if (n) { hit = { map: slug, node: n }; return true; } return false; });
    return hit;
  }
  let _backlinkIx = null;                              // memoized inverse citation graph: cited-nid -> [{citerId,citerName,citerMap}]
  function backlinkIndex() {
    if (_backlinkIx) return _backlinkIx;
    const ix = {};
    MAPS.order.forEach(slug => { const m = MAPS.maps[slug]; if (!m) return; (m.nodes || []).forEach(n => { (n.refs || []).forEach(rf => { (ix[rf.target] = ix[rf.target] || []).push({ citerId: n.id, citerName: n.name, citerMap: slug }); }); }); });
    return (_backlinkIx = ix);
  }
  let flashIds = new Set(), flashTimer = null;
  function flashBacklinks(citers) {   // transient highlight of the nodes that cite this source (real .hl untouched)
    const here = citers.filter(c => c.citerMap === cur), elsewhere = citers.filter(c => c.citerMap !== cur);
    flashIds = new Set(here.map(c => c.citerId)); render();
    clearTimeout(flashTimer); flashTimer = setTimeout(() => { flashIds.clear(); render(); }, 2200);
    document.querySelectorAll('.backlink-list').forEach(el => el.remove());
    if (elsewhere.length) {
      const box = document.createElement('div'); box.className = 'backlink-list';
      const h = document.createElement('div'); h.className = 'bl-head'; h.textContent = 'Also cited in:'; box.appendChild(h);
      elsewhere.slice(0, 10).forEach(c => { const it = document.createElement('div'); it.className = 'bl-row'; it.textContent = '↗ ' + c.citerName + ' — ' + ((MAPS.maps[c.citerMap] || {}).title || c.citerMap); it.onclick = () => { box.remove(); trail = []; switchMap(c.citerMap, true); setTimeout(() => { const n = byId(c.citerId); if (n) focusNode(n); }, 120); }; box.appendChild(it); });
      document.body.appendChild(box); setTimeout(() => { if (box.parentNode) box.remove(); }, 7000);
    }
  }
  // ---- hover-preview a Source-of-Truth ghost: popover with the cited node's glyph, gate, home, excerpt ----
  let ghostHoverTimer = null, ghostPopover = null, ghostDocCache = {};   // ghostDocCache reset in applyMaps so it can't pin stale (pre-refresh) MAPS node objects
  function hideGhostPopover() { clearTimeout(ghostHoverTimer); if (ghostPopover) { ghostPopover.remove(); ghostPopover = null; } }
  async function fetchGhostDoc(nid) {
    if (ghostDocCache[nid] !== undefined) return ghostDocCache[nid];
    const hit = resolveRef(nid); if (!hit) return (ghostDocCache[nid] = null);
    try {
      const r = await fetch('/api/doc?path=' + encodeURIComponent(repoRel(hit.node.url))); const j = await r.json();
      if (!j.ok) return (ghostDocCache[nid] = null);
      const excerpt = (j.content || '').replace(/^---\n[\s\S]*?\n---\n?/, '').replace(/^#\s+.*\n?/, '').trim().split('\n').filter(Boolean).slice(0, 2).join(' ').slice(0, 150);
      return (ghostDocCache[nid] = { node: hit.node, home: (MAPS.maps[hit.map] || {}).title || hit.map, excerpt });
    } catch (_) { return (ghostDocCache[nid] = null); }
  }
  function showGhostPopover(nid, x, y) {
    hideGhostPopover();
    ghostHoverTimer = setTimeout(async () => {
      const doc = await fetchGhostDoc(nid); if (!doc) return;
      const n = doc.node, pop = document.createElement('div'); pop.className = 'ghost-popover' + (motionAllowed() ? ' anim' : '');
      const head = document.createElement('div'); head.className = 'gp-head';
      const gl = document.createElement('span'); gl.className = 'gp-glyph'; gl.style.background = accent(n); gl.textContent = n.type === 'reference' ? '§' : n.type === 'subprocess-link' ? '▸' : n.type === 'decision' ? '◇' : '▭'; head.appendChild(gl);
      const nm = document.createElement('span'); nm.className = 'gp-name'; nm.textContent = n.name; head.appendChild(nm);
      if (n.gate) { const g = document.createElement('span'); g.className = 'gp-gate'; g.textContent = '✓ gate'; head.appendChild(g); }
      pop.appendChild(head);
      const sub = document.createElement('div'); sub.className = 'gp-sub'; sub.textContent = '↗ ' + doc.home; pop.appendChild(sub);
      if (doc.excerpt) { const b = document.createElement('div'); b.className = 'gp-body'; b.textContent = doc.excerpt; pop.appendChild(b); }
      pop.style.left = Math.max(8, Math.min(window.innerWidth - 224, x + 12)) + 'px';
      pop.style.top = Math.max(8, Math.min(window.innerHeight - 140, y + 12)) + 'px';
      document.body.appendChild(pop); ghostPopover = pop;
    }, 320);
  }
  function focusNode(n) {   // center the viewport on one node (supersedes fit's transition since it starts later)
    const w = window.innerWidth, h = window.innerHeight, k = Math.min(1.4, d3.zoomTransform(svgN).k || 1);
    svg.transition().duration(420).ease(d3.easeCubicOut).call(zoom.transform, d3.zoomIdentity.translate(w / 2 - k * n.x, h / 2 - k * n.y).scale(k));   // leap-then-settle: 'brought the node to you'
  }
  function toggleRefs(n) {   // collapse/expand a node's knowledge tray (persists via refs_collapsed frontmatter)
    const v = !n.refsCollapsed; n.refsCollapsed = v; render();   // optimistic
    if (SERVER) api('/api/node-style', { path: repoRel(n.url), refsCollapsed: v }).then(j => { if (j && j.ok) applyMaps(j.maps); });
  }
  function gotoRef(target) {
    const hit = resolveRef(target); if (!hit) return false;
    const open = () => { const n = (MAPS.maps[hit.map].nodes || []).find(x => x.id === hit.node.id) || hit.node; focusNode(n); openEditor(n); };
    if (hit.map !== cur) { trail = []; switchMap(hit.map); setTimeout(open, 120); } else open();
    return true;
  }
  function renderRefs(text) {
    const box = document.getElementById('ed-refs'); box.innerHTML = '';
    const links = []; let m; WIKILINK_RE.lastIndex = 0;
    while ((m = WIKILINK_RE.exec(text || ''))) { const parts = m[1].split('|'); links.push({ target: (parts[0] || '').trim(), label: (parts[1] || parts[0] || '').trim() }); }
    if (!links.length) { box.hidden = true; return; }
    box.hidden = false;
    const broken = links.filter(l => !l.target.startsWith('?') && !resolveRef(l.target));   // unresolved (not stub) → repair banner
    if (broken.length) { const b = document.createElement('div'); b.className = 'broken-refs-banner'; b.textContent = '⚠ ' + broken.length + ' broken reference' + (broken.length === 1 ? '' : 's') + ' — fix'; b.onclick = () => showBrokenRefsOverlay(broken); box.appendChild(b); }
    const lab = document.createElement('span'); lab.className = 'lbl'; lab.textContent = 'References'; box.appendChild(lab);
    links.forEach(l => {
      const stub = l.target.startsWith('?'), tgt = stub ? l.target.slice(1) : l.target;
      const hit = stub ? null : resolveRef(tgt);
      const chip = document.createElement('span');
      chip.className = 'refchip' + (hit || stub ? '' : ' broken');
      { const ic = document.createElement('span'); ic.className = 'ic'; ic.textContent = '§'; chip.append(ic, document.createTextNode(l.label || tgt)); }   // DOM build, not innerHTML — a [[id|<img onerror>]] label must not execute
      if (hit) { chip.title = '→ ' + (hit.node.name || tgt) + '  (' + hit.map + ')'; chip.onclick = () => gotoRef(tgt); }
      else if (stub) { chip.title = 'Not written yet (stub)'; chip.style.opacity = '.55'; chip.style.cursor = 'default'; }
      else { chip.title = 'Unresolved: ' + tgt; }
      box.appendChild(chip);
    });
  }

  // ---- knowledge picker: cite a SoT node from the right-clicked node + pin a ghost of it here ----
  let kpCiting = null, kpAll = [], citationPicker = null, brokenRefPicker = null;
  function openKnowPick(d) {
    if (!SERVER) return; kpCiting = d; closeCtx();
    kpAll = [];
    MAPS.order.forEach(slug => { const m = MAPS.maps[slug]; if (!m) return; (m.nodes || []).forEach(n => { if (n.id === d.id) return; kpAll.push({ id: n.id, name: n.name, type: n.type, mapTitle: m.title || slug }); }); });
    kpAll.sort((a, b) => (a.type === 'reference' ? 0 : 1) - (b.type === 'reference' ? 0 : 1) || a.name.localeCompare(b.name));   // SoT nodes first
    document.getElementById('kp-search').value = ''; renderKpList('');
    { const kp = document.getElementById('knowpick'); kp.classList.remove('exiting'); kp.hidden = false; }
    setTimeout(() => document.getElementById('kp-search').focus(), 0);
  }
  function renderKpList(q) {
    const box = document.getElementById('kp-list'); box.innerHTML = '';
    const ql = q.trim().toLowerCase();
    const items = kpAll.filter(it => !ql || it.name.toLowerCase().includes(ql) || it.mapTitle.toLowerCase().includes(ql)).slice(0, 60);
    if (!items.length) { const e = document.createElement('div'); e.className = 'kp-foot'; e.textContent = 'No matches.'; box.appendChild(e); return; }
    items.forEach(it => {
      const row = document.createElement('div'); row.className = 'kp-item';
      const col = it.type === 'reference' ? 'var(--ref)' : (TYPE_COLOR[it.type] || TYPE_COLOR.step);
      const g = document.createElement('span'); g.className = 'kp-glyph'; g.style.background = col; g.textContent = it.type === 'reference' ? '§' : '•';
      const nm = document.createElement('span'); nm.className = 'kp-name'; nm.textContent = it.name;
      const mp = document.createElement('span'); mp.className = 'kp-map'; mp.textContent = it.mapTitle;
      row.append(g, nm, mp); row.onclick = () => pickKnow(it); box.appendChild(row);
    });
  }
  async function pickKnow(it) {
    if (citationPicker) { insertCitation(it.id, it.name); return; }                          // inline [[ autocomplete
    if (brokenRefPicker) {                                                                    // broken-ref repair: rewrite the dead [[…]] in the body
      const tgt = brokenRefPicker; brokenRefPicker = null; closeKnowPick();
      const ta = document.getElementById('ed-text'); if (!edPath || !SERVER) return;
      const esc = tgt.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const content = ta.value.replace(new RegExp('\\[\\[' + esc + '(\\|[^\\]]*)?\\]\\]'), '[[' + it.id + '|' + it.name + ']]');
      const msg = document.getElementById('ed-msg'); msg.textContent = 'Fixing…';
      const j = await api('/api/save-body', { path: edPath, body: content }); if (j.ok) { ta.value = content; edContentHash = simpleHash(content); renderRefs(content); msg.textContent = 'Fixed ✓'; if (j.maps) applyMaps(j.maps); } else msg.textContent = 'Error: ' + j.error;   // body-only save preserves frontmatter; resync hash to the saved body
      return;
    }
    if (!kpCiting || !SERVER) return;
    const d = kpCiting; closeKnowPick();
    const j = await api('/api/link-knowledge', { map: cur, path: repoRel(d.url), ref: it.id, label: it.name });   // ghost auto-appears in d's tray
    if (j.ok) applyMaps(j.maps); else alert('Link: ' + j.error);
  }
  function closeKnowPick() { kpCiting = null; brokenRefPicker = null; const kp = document.getElementById('knowpick'); const ae = document.activeElement; if (ae && kp.contains(ae)) ae.blur(); closeCitationPicker(); fadeOut(kp); }   // blur so focus leaves the hidden picker
  // ---- inline [[ citation autocomplete (20) + broken-ref repair (21): both reuse this picker ----
  function buildKpAll() { kpAll = []; MAPS.order.forEach(slug => { const m = MAPS.maps[slug]; if (!m) return; (m.nodes || []).forEach(n => kpAll.push({ id: n.id, name: n.name, type: n.type, mapTitle: m.title || slug })); }); kpAll.sort((a, b) => (a.type === 'reference' ? 0 : 1) - (b.type === 'reference' ? 0 : 1) || a.name.localeCompare(b.name)); }
  function openCitationPicker(ta, caretPos) {
    buildKpAll(); citationPicker = { ta, pos: caretPos };
    const kp = document.getElementById('knowpick'); kp.classList.remove('exiting'); kp.classList.add('compact-picker'); kp.hidden = false;
    const r = ta.getBoundingClientRect(); kp.style.left = Math.max(8, r.left) + 'px'; kp.style.top = Math.min(window.innerHeight - 220, r.top + 30) + 'px'; kp.style.width = Math.min(340, r.width) + 'px';
    document.getElementById('kp-search').value = ''; renderKpList(''); setTimeout(() => document.getElementById('kp-search').focus(), 0);
  }
  function closeCitationPicker() { const kp = document.getElementById('knowpick'); if (kp.classList.contains('compact-picker')) { kp.classList.remove('compact-picker'); kp.style.left = kp.style.top = kp.style.width = ''; if (!kp.hidden) fadeOut(kp); } citationPicker = null; }
  function insertCitation(id, label) {
    const c = citationPicker; closeCitationPicker(); if (!c || !c.ta) return;
    const ta = c.ta, text = ta.value, pos = ta.selectionStart, before = text.slice(0, pos), bi = before.lastIndexOf('[[');
    if (bi === -1) { ta.focus(); return; }
    const ins = '[[' + id + '|' + label + ']]';
    ta.value = text.slice(0, bi) + ins + text.slice(pos); ta.selectionStart = ta.selectionEnd = bi + ins.length;
    ta.focus(); ta.dispatchEvent(new Event('input', { bubbles: true }));
  }
  function showBrokenRefPicker(target) {
    brokenRefPicker = target; buildKpAll();
    const kp = document.getElementById('knowpick'); kp.classList.remove('exiting'); kp.hidden = false;
    document.getElementById('kp-search').value = target; renderKpList(target); setTimeout(() => document.getElementById('kp-search').focus(), 0);
  }
  function showBrokenRefsOverlay(broken) {
    document.querySelectorAll('.broken-overlay').forEach(el => el.remove());
    const ov = document.createElement('div'); ov.className = 'broken-overlay';
    const h = document.createElement('div'); h.className = 'bo-head'; h.textContent = 'Fix broken references'; ov.appendChild(h);
    broken.forEach(br => { const row = document.createElement('div'); row.className = 'bo-row'; const lab = document.createElement('span'); lab.className = 'bo-lab'; lab.textContent = '[[' + br.target + ']]'; const btn = document.createElement('button'); btn.className = 'primary'; btn.textContent = 'Relink'; btn.onclick = e => { e.stopPropagation(); ov.remove(); showBrokenRefPicker(br.target); }; row.append(lab, btn); ov.appendChild(row); });   // stopPropagation: else this same click bubbles to the doc 'outside-click' handler, which (the button now detached) treats it as outside the just-opened picker and dismisses it
    const x = document.createElement('button'); x.className = 'bo-x'; x.textContent = '✕'; x.onclick = () => ov.remove(); ov.appendChild(x);
    document.body.appendChild(ov);
  }
  // mark/unmark the current map as a SoT library (kind: reference)
  function syncLibToggle() { const m = map(), on = !!(m && m.kind === 'reference'); document.getElementById('libtoggle').classList.toggle('on', on); document.body.classList.toggle('libmap', on); }
  async function toggleLibrary() {
    if (!SERVER || !cur) return; const m = map();
    const j = await api('/api/map-kind', { map: cur, kind: (m && m.kind === 'reference') ? 'process' : 'reference' });
    if (j.ok) applyMaps(j.maps); else alert(j.error);
  }

  // inline (not prompt(): blocked in sandboxed preview iframes) — new top-level map, then switch to it
  function addMapPrompt() {
    if (!SERVER) return;
    showNameInput(window.innerWidth / 2, 70, '', async title => {
      if (!title) return;
      const j = await api('/api/map-add', { title });
      if (!j.ok) { alert('Map: ' + j.error); return; }
      trail = []; cur = j.slug; applyMaps(j.maps); setHash(j.slug);
    });
  }
  // turn a node into a sub-process: create a new map and link this node to it in one step
  function ctxNewSubmap() {
    if (!ctxNode || !SERVER) return;
    const d = ctxNode, t = d3.zoomTransform(svgN), [sx, sy] = t.apply([d.x, d.y]);
    closeCtx();
    showNameInput(sx, sy - 30, d.name, async title => {       // default the sub-map name to the node's name
      if (!title) return;
      const j = await api('/api/map-add', { title });
      if (!j.ok) { alert('Map: ' + j.error); return; }
      const j2 = await api('/api/link', { path: repoRel(d.url), link_map: j.slug });
      if (j2.ok) applyMaps(j2.maps); else alert('Link: ' + j2.error);
    });
  }

  // ---- workflow export (map → loop spec + agent Markdown, validated by loop_lint.py) ----
  async function openExport() {
    if (!SERVER || !cur) return;
    closeEditor(); closeCtx();
    const $ = id => document.getElementById(id);
    $('ex-map').textContent = (map() || {}).title || cur;
    const v = $('ex-verdict'); v.className = 'ex-verdict'; v.textContent = 'Generating…';
    $('ex-issues').innerHTML = ''; $('ex-spec').textContent = ''; $('ex-md').textContent = ''; $('ex-msg').textContent = '';
    $('exportpanel').hidden = false; { const f = $('ex-copymd'); if (f) setTimeout(() => f.focus(), 10); }
    try {
      const r = await fetch('/api/export?map=' + encodeURIComponent(cur)); const j = await r.json();
      if (!j.ok) { v.className = 'ex-verdict fail'; v.textContent = 'Error: ' + j.error; return; }
      $('ex-spec').textContent = j.spec; $('ex-md').textContent = j.markdown;
      const code = j.lint && j.lint.code;
      if (code === 0) { v.className = 'ex-verdict pass'; v.textContent = '✓ loop_lint: valid workflow — gate · stop · budget · separate verifier'; }
      else if (code === 1) { v.className = 'ex-verdict warn'; v.textContent = '⚠ loop_lint: valid, with warnings'; }
      else if (code === 2) { v.className = 'ex-verdict fail'; v.textContent = '✗ loop_lint: not a runnable workflow yet — fix the issues below'; }
      else { v.className = 'ex-verdict warn'; v.textContent = 'Spec generated — loop_lint did not run'; }
      const ul = $('ex-issues');
      (j.issues || []).forEach(s => { const li = document.createElement('li'); li.textContent = s; ul.appendChild(li); });
      if (code && j.lint && j.lint.output) {
        const detail = j.lint.output.split('\n').filter(l => /\[(FAIL|WARN)\]/.test(l)).slice(0, 5).join(' · ');
        if (detail) { const li = document.createElement('li'); li.textContent = 'loop_lint → ' + detail; ul.appendChild(li); }
      }
    } catch (e) { v.className = 'ex-verdict fail'; v.textContent = 'Error: ' + e.message; }
  }
  async function copyText(t, what) { try { await navigator.clipboard.writeText(t); document.getElementById('ex-msg').textContent = 'Copied ' + what + ' ✓'; } catch (_) { document.getElementById('ex-msg').textContent = 'Copy failed — select the text manually'; } }

  // ---- command palette (⌘K): fuzzy-search every action + jump to any node/map ----
  function buildCmdpalReg() {
    cmdpalReg = [];
    if (SERVER) {
      cmdpalReg.push({ type: 'cmd', label: 'Add node', q: 'add node new', fn: () => { const c = viewCenter(); quickAdd(c.x, c.y, window.innerWidth / 2, window.innerHeight / 2); } });
      cmdpalReg.push({ type: 'cmd', label: 'Add map', q: 'add map new', fn: addMapPrompt });
      cmdpalReg.push({ type: 'cmd', label: 'Add box', q: 'add box frame group', fn: addFrame });
      cmdpalReg.push({ type: 'cmd', label: 'Tidy layout', q: 'tidy arrange layout', fn: tidyLayout });
      cmdpalReg.push({ type: 'cmd', label: 'Export workflow', q: 'export workflow loop spec', fn: openExport });
      cmdpalReg.push({ type: 'cmd', label: 'Undo', q: 'undo revert', fn: doUndo });
    }
    cmdpalReg.push({ type: 'cmd', label: 'Toggle lanes', q: 'lanes bands swimlanes', fn: () => { showLanes = !showLanes; document.getElementById('lanes').classList.toggle('on', showLanes); render(); } });
    cmdpalReg.push({ type: 'cmd', label: 'Fit to view', q: 'fit zoom view', fn: () => fit() });
    cmdpalReg.push({ type: 'cmd', label: 'Keyboard shortcuts', q: 'help shortcuts keys', fn: showShortcutsOverlay });
    MAPS.order.forEach(slug => { const m = MAPS.maps[slug]; if (!m) return;
      cmdpalReg.push({ type: 'map', label: m.title || slug, sub: 'Map', q: (m.title || slug), fn: () => jumpMap(slug) });
      (m.nodes || []).forEach(n => cmdpalReg.push({ type: 'node', label: n.name, sub: (m.title || slug), q: n.name + ' ' + (m.title || slug), fn: () => flyToNode(slug, n.id) }));
    });
  }
  function flyToNode(slug, id) { const go = () => { const n = byId(id); if (n) focusNode(n); }; if (slug !== cur) { trail = []; switchMap(slug, true); setTimeout(go, 90); } else go(); }
  function openCmdpal(nodesOnly) {
    buildCmdpalReg();
    if (nodesOnly) cmdpalReg = cmdpalReg.filter(it => it.type === 'node');
    cmdpalSel = 0;
    document.getElementById('cmdpal-search').value = ''; renderCmdpalList('');
    const cp = document.getElementById('cmdpal'); cp.classList.remove('exiting'); cp.hidden = false;
    setTimeout(() => document.getElementById('cmdpal-search').focus(), 0);
  }
  function openFind() { openCmdpal(true); }
  function closeCmdpal() { const s = document.getElementById('cmdpal-search'); if (s) s.blur(); fadeOut(document.getElementById('cmdpal')); }   // blur the (about-to-be-hidden) search so activeElement returns to body — else 'typing' stays true and /, ?, Delete, arrows go dead until a canvas click
  function renderCmdpalList(q) {
    const box = document.getElementById('cmdpal-list'); box.innerHTML = '';
    const qs = (q || '').trim();
    const results = cmdpalReg.map(it => { const m = fuzzyScore(it.q || it.label, qs), disp = fuzzyScore(it.label, qs); return Object.assign({}, it, { score: m.score, highlighted: disp.score > 0 ? disp.highlighted : escHtml(it.label) }); })
      .filter(it => !qs || it.score > 0).sort((a, b) => b.score - a.score).slice(0, 40);
    cmdpalSel = Math.max(0, Math.min(cmdpalSel, results.length - 1));
    if (!results.length) { const e = document.createElement('div'); e.className = 'kp-foot'; e.textContent = 'No matches.'; box.appendChild(e); return; }
    results.forEach((it, i) => {
      const row = document.createElement('div'); row.className = 'kp-item' + (i === cmdpalSel ? ' on' : '');
      const col = it.type === 'map' ? 'var(--step)' : it.type === 'node' ? 'var(--link)' : 'var(--edge)';
      const g = document.createElement('span'); g.className = 'kp-glyph'; g.style.background = col; g.textContent = it.type === 'cmd' ? '⌘' : it.type === 'map' ? '▦' : '◯';
      const nm = document.createElement('span'); nm.className = 'kp-name'; nm.innerHTML = it.highlighted || it.label;
      const sub = document.createElement('span'); sub.className = 'kp-map'; sub.textContent = it.sub || '';
      row.append(g, nm, sub); row.onclick = () => { closeCmdpal(); it.fn(); };
      box.appendChild(row);
    });
  }
  function cmdpalMove(dir) { const items = document.querySelectorAll('#cmdpal-list .kp-item'); if (!items.length) return; cmdpalSel = (cmdpalSel + dir + items.length) % items.length; items.forEach((el, i) => el.classList.toggle('on', i === cmdpalSel)); items[cmdpalSel].scrollIntoView({ block: 'nearest' }); }
  function cmdpalRun() { const items = document.querySelectorAll('#cmdpal-list .kp-item'); const el = items[cmdpalSel] || items[0]; if (el) el.click(); }
  // ---- shortcuts cheat-sheet (?) ----
  function showShortcutsOverlay() {
    const ov = document.getElementById('shortcuts'), body = ov.querySelector('.shortcuts-body'); body.innerHTML = '';
    SHORTCUTS.forEach(([k, d]) => { const row = document.createElement('div'); row.className = 'shortcuts-row'; const ke = document.createElement('div'); ke.className = 'shortcuts-key'; ke.textContent = k; const de = document.createElement('div'); de.className = 'shortcuts-desc'; de.textContent = d; row.append(ke, de); body.appendChild(row); });
    ov.classList.remove('exiting'); ov.hidden = false;
  }
  function closeShortcutsOverlay() { fadeOut(document.getElementById('shortcuts')); }
  // ---- undo toast (makes the existing server undo visible) ----
  function showDragPortCoach(x, y) {   // one-time "drag to connect" hint on first port hover (item 31)
    try { if (localStorage.getItem('coachmark.dragport')) return; localStorage.setItem('coachmark.dragport', '1'); } catch (_) { return; }
    const c = document.getElementById('coach-dragport'); if (!c) return;
    c.style.left = x + 'px'; c.style.top = y + 'px'; c.classList.remove('exiting'); c.hidden = false;
    clearTimeout(coachTimeout); coachTimeout = setTimeout(() => fadeOut(c), 3000);
  }
  function showUndoToast(label) {
    const toast = document.getElementById('toast-undo'); if (!toast) return;
    document.getElementById('toast-msg').textContent = label;
    toast.classList.remove('exiting'); toast.hidden = false;
    clearTimeout(toastTimeout); toastTimeout = setTimeout(() => fadeOut(toast), 4500);
  }

  // ---- validation lint panel (item 17): live issues for the current map, click to fly to the offender ----
  let lintOpen = false;
  function computeLint() {
    const m = map(); if (!m) return [];
    const nodes = m.nodes || [], edges = (m.edges || []).filter(e => e.from !== e.to);
    const byid = {}; nodes.forEach(n => byid[n.id] = n);
    const out = {}, indeg = {}; nodes.forEach(n => { out[n.id] = []; indeg[n.id] = 0; });
    edges.forEach(e => { if (byid[e.from] && byid[e.to]) { out[e.from].push(e); indeg[e.to]++; } });
    const issues = [], starts = nodes.filter(n => indeg[n.id] === 0), ends = nodes.filter(n => out[n.id].length === 0);
    if (nodes.length && edges.length) {
      if (!starts.length) issues.push({ msg: 'no START — a cycle at the entry', nodeId: null });
      else if (starts.length > 1) issues.push({ msg: starts.length + ' START nodes (expected 1)', nodeId: null });
      if (!ends.length) issues.push({ msg: 'no END — nothing terminates the flow', nodeId: null });
      const deg = {}; nodes.forEach(n => deg[n.id] = indeg[n.id]); const q = starts.map(n => n.id), seenL = [];
      while (q.length) { const id = q.shift(); seenL.push(id); out[id].forEach(e => { if (--deg[e.to] === 0) q.push(e.to); }); }
      if (seenL.length !== nodes.length) issues.push({ msg: 'cycle detected — not a clean pipeline', nodeId: null });
    }
    nodes.filter(n => out[n.id].length > 0 && n.type !== 'reference' && !(n.gate && String(n.gate).trim())).forEach(n => issues.push({ msg: 'no gate: ' + n.name, nodeId: n.id }));
    nodes.forEach(n => (n.refs || []).forEach(rf => { if (!resolveRef(rf.target)) issues.push({ msg: 'broken ref in ' + n.name, nodeId: n.id }); }));
    (MAPS.issues || []).forEach(bi => { if (bi.level !== 'warn') return; if (bi.map && bi.map !== cur) return; issues.push({ msg: bi.msg, nodeId: bi.node ? (nodes.find(n => n.slug === bi.node) || {}).id || null : null }); });   // surface build-time warnings (dropped dangling/dup edges, missing nodes)
    return issues;
  }
  function renderLint() {
    const panel = document.getElementById('lint-panel'); if (!panel) return;
    if (dragging) return;   // lint is graph-topology only; dragging changes positions, not topology → skip the O(V+E) topo-sort on every drag-tick render (refreshed on drag-end render)
    const issues = computeLint(), badge = panel.querySelector('.lint-badge');
    if (!issues.length) { badge.hidden = true; panel.classList.remove('open'); return; }
    badge.hidden = false; badge.querySelector('.lint-count').textContent = issues.length;
    const list = panel.querySelector('.lint-list'); list.innerHTML = '';
    issues.forEach(iss => { const row = document.createElement('div'); row.className = 'lint-row'; row.textContent = iss.msg; if (iss.nodeId) { const n = byId(iss.nodeId); if (n) { row.style.cursor = 'pointer'; row.title = 'Zoom to ' + n.name; row.onclick = () => focusNode(n); } } list.appendChild(row); });
  }
  function toggleLint() { lintOpen = !lintOpen; document.getElementById('lint-panel').classList.toggle('open', lintOpen); }

  // ---- node info panel (single-select): summary · tags · status · 1-hop connections (adopted from Understand-Anything's NodeInfo) ----
  let niId = null, niOpenId = null, infoStack = [], niFocusTag = false;   // niOpenId: the node the info panel is explicitly opened for (double-click) — decoupled from selection so a single-click select never opens it
  function openNodeInfo(d) { selection.clear(); selection.add(d.id); niOpenId = d.id; render(); }
  const STATUS_META = { draft: { label: 'Draft', color: 'var(--muted)' }, active: { label: 'Active', color: 'var(--link)' }, blocked: { label: 'Blocked', color: 'var(--decision)' }, done: { label: 'Done', color: 'var(--step)' } };
  const NODE_GLYPH = { step: '▭', decision: '◇', 'subprocess-link': '▸', reference: '§' };
  function niEl(tag, cls) { const e = document.createElement(tag); if (cls) e.className = cls; return e; }
  function showEmojiPalette(anchor, commit) {   // small click-to-pick emoji grid (works in the sandboxed preview where the OS picker isn't reachable)
    document.querySelectorAll('.emoji-pop').forEach(el => el.remove());
    const EMO = ['⚙️', '🔧', '✂️', '🎨', '🖌️', '🖨️', '📐', '📏', '🧩', '✅', '⚠️', '🚫', '🔍', '📦', '📤', '📥', '🗂️', '🏷️', '💡', '🔁', '▶️', '⏸️', '🟢', '🔴', '🔵', '📝', '🧪', '🚀', '⭐', '📌', '🔗', '🧱'];
    const pop = niEl('div', 'emoji-pop');
    EMO.forEach(em => { const b = niEl('button'); b.type = 'button'; b.textContent = em; b.onclick = ev => { ev.stopPropagation(); commit(em); pop.remove(); }; pop.appendChild(b); });
    const clr = niEl('button', 'emoji-clear'); clr.type = 'button'; clr.textContent = '✕'; clr.title = 'No icon'; clr.onclick = ev => { ev.stopPropagation(); commit(''); pop.remove(); }; pop.appendChild(clr);
    document.body.appendChild(pop);
    const r = anchor.getBoundingClientRect();
    pop.style.left = Math.max(8, Math.min(window.innerWidth - pop.offsetWidth - 8, r.left)) + 'px';
    pop.style.top = (r.bottom + 6) + 'px';
    const close = ev => { if (!pop.contains(ev.target) && ev.target !== anchor) { pop.remove(); document.removeEventListener('pointerdown', close, true); } };
    setTimeout(() => document.addEventListener('pointerdown', close, true), 0);
  }
  async function saveNodeMeta(node, patch) {   // persist summary/tags/status via the existing node-style endpoint
    if (!SERVER || !node) return;
    const j = await api('/api/node-style', Object.assign({ path: repoRel(node.url) }, patch));
    if (j && j.ok) applyMaps(j.maps);
  }
  function renderNodeInfo() {
    const panel = document.getElementById('nodeinfo'); if (!panel) return;
    const n = niOpenId ? byId(niOpenId) : null;   // shown only when explicitly opened via double-click (not on plain selection)
    if (!n || dragging) { panel.hidden = true; if (!n) { niId = null; niOpenId = null; } return; }   // hide while dragging, or when not explicitly open
    if (niId === n.id && !panel.hidden) return;   // already built for this node → don't clobber in-progress edits or focus
    niId = n.id; buildNodeInfo(panel, n);
  }
  function niConnSection(title, items) {
    const wrap = niEl('div', 'ni-conn'), h = niEl('div', 'ni-sec'); h.textContent = title; wrap.appendChild(h);
    items.forEach(it => {
      const t = byId(it.id); if (!t) return;
      const row = niEl('div', 'ni-connrow'); row.title = 'Go to "' + t.name + '"';
      const g = niEl('span', 'ni-connglyph'); g.style.background = accent(t); g.textContent = NODE_GLYPH[t.type] || '▭'; row.appendChild(g);
      const nm = niEl('span', 'ni-connname'); nm.textContent = t.name; row.appendChild(nm);
      if (it.label) { const lb = niEl('span', 'ni-connlbl'); lb.textContent = it.label; row.appendChild(lb); }
      row.onclick = () => { if (niId) infoStack.push(niId); selection.clear(); selection.add(t.id); niOpenId = t.id; render(); focusNode(t); };   // navigate + push back-stack (panel follows the jump)
      wrap.appendChild(row);
    });
    return wrap;
  }
  function buildNodeInfo(panel, n) {
    panel.hidden = false; panel.innerHTML = '';
    const col = accent(n);
    // header — glyph · name (dbl-click → rename) · close
    const head = niEl('div', 'ni-head');
    const gl = niEl('div', 'ni-glyph'); gl.style.background = col; gl.textContent = NODE_GLYPH[n.type] || '▭'; head.appendChild(gl);
    const nm = niEl('div', 'ni-name'); nm.textContent = n.name;
    if (SERVER) { nm.setAttribute('data-edit', '1'); nm.title = 'Double-click to rename'; nm.ondblclick = () => { const live = byId(n.id); if (live) openRename(live); }; }
    head.appendChild(nm);
    const x = niEl('button', 'ni-x'); x.textContent = '✕'; x.title = 'Close'; x.onclick = clearSelection; head.appendChild(x);
    panel.appendChild(head);
    // type (+ sub-map link target)
    const trow = niEl('div', 'ni-row'); const tl = niEl('span', 'ni-lbl'); tl.textContent = n.type === 'subprocess-link' ? 'link' : n.type; trow.appendChild(tl);
    if (n.link_map) { const ll = niEl('span', 'ni-connlbl'); ll.textContent = '▸ ' + ((MAPS.maps[n.link_map] || {}).title || n.link_map); trow.appendChild(ll); }
    if (SERVER) {   // icon — emoji/char shown on the card for at-a-glance distinction
      const il = niEl('button', 'ni-icon ni-edit'); il.type = 'button'; il.textContent = n.icon || '🙂'; if (!n.icon) il.classList.add('placeholder'); il.title = 'Card icon — click to pick an emoji';
      const commit = v => { const ns = byId(n.id); if (!ns) return; if ((ns.icon || '') !== v) { ns.icon = v || null; saveNodeMeta(ns, { icon: v }); render(); } il.textContent = v || '🙂'; il.classList.toggle('placeholder', !v); };   // render(): icon changes the card label, and applyMaps' curSame check would skip the redraw (optimistic local set already matches the server echo)
      il.onclick = e => { e.stopPropagation(); showEmojiPalette(il, commit); };
      trow.appendChild(il);
    }
    panel.appendChild(trow);
    // status — editable pills (server) or a read-only pill
    if (SERVER) {
      const srow = niEl('div', 'ni-row ni-edit'); const sl = niEl('span', 'ni-lbl'); sl.textContent = 'Status'; srow.appendChild(sl);
      ['draft', 'active', 'blocked', 'done'].forEach(s => {
        const b = niEl('button', 'ni-status'); b.textContent = STATUS_META[s].label;
        const on = n.status === s; b.style.background = on ? STATUS_META[s].color : 'rgba(65,64,76,.10)'; b.style.color = on ? '#fff' : 'var(--muted)';
        b.onclick = () => { const ns = byId(n.id); if (!ns) return; const nv = ns.status === s ? null : s; ns.status = nv; saveNodeMeta(ns, { status: nv || '' }); buildNodeInfo(panel, ns); };   // toggle off if already set
        srow.appendChild(b);
      });
      panel.appendChild(srow);
    } else if (n.status) {
      const srow = niEl('div', 'ni-row'); const sl = niEl('span', 'ni-lbl'); sl.textContent = 'Status'; const pill = niEl('span', 'ni-status'); const meta = STATUS_META[n.status] || { label: n.status, color: 'var(--muted)' }; pill.textContent = meta.label; pill.style.background = meta.color; pill.style.color = '#fff'; srow.append(sl, pill); panel.appendChild(srow);
    }
    // summary — editable line (save on blur) or read-only text
    if (SERVER) {
      const ta = niEl('textarea', 'ni-summary ni-edit'); ta.value = n.summary || ''; ta.placeholder = 'Add a one-line summary…'; ta.rows = 2;
      ta.onblur = () => { const ns = byId(n.id); if (!ns) return; const v = ta.value.trim(); if ((ns.summary || '') !== v) { ns.summary = v || null; saveNodeMeta(ns, { summary: v }); } };
      panel.appendChild(ta);
    } else if (n.summary) { const s = niEl('div', 'ni-summary'); s.style.background = 'transparent'; s.style.border = 'none'; s.textContent = n.summary; panel.appendChild(s); }
    // tags — chips (× to remove) + an add input
    const tagsWrap = niEl('div', 'ni-tags');
    (n.tags || []).forEach(t => {
      const chip = niEl('span', 'ni-tag'); chip.appendChild(document.createTextNode(t));   // textNode, not innerHTML — a tag must never execute
      if (SERVER) { const xb = niEl('b'); xb.textContent = '×'; xb.title = 'Remove tag'; xb.onclick = () => { const ns = byId(n.id); if (!ns) return; ns.tags = (ns.tags || []).filter(x => x !== t); saveNodeMeta(ns, { tags: ns.tags }); buildNodeInfo(panel, ns); }; chip.appendChild(xb); }
      tagsWrap.appendChild(chip);
    });
    if (SERVER) {
      const inp = niEl('input', 'ni-taginput ni-edit'); inp.placeholder = '+ tag'; inp.autocomplete = 'off'; inp.spellcheck = false;
      inp.onkeydown = e => {
        if (e.key === 'Enter') { e.preventDefault(); const v = inp.value.trim().toLowerCase().replace(/,/g, ''); if (!v) return; const ns = byId(n.id); if (!ns) return; ns.tags = [...(ns.tags || []), v].filter((x, i, a) => a.indexOf(x) === i); saveNodeMeta(ns, { tags: ns.tags }); niFocusTag = true; buildNodeInfo(panel, ns); }   // optimistic add; rebuild then refocus the input
        else if (e.key === 'Escape') { inp.blur(); }
      };
      tagsWrap.appendChild(inp);
    }
    if ((n.tags || []).length || SERVER) panel.appendChild(tagsWrap);
    if (niFocusTag) { niFocusTag = false; const ti = panel.querySelector('.ni-taginput'); if (ti) ti.focus(); }
    // connections — intra-map edges (skip self-loops)
    const edges = map() ? map().edges : [];
    const outE = edges.filter(e => e.from === n.id && e.from !== e.to);
    const inE = edges.filter(e => e.to === n.id && e.from !== e.to);
    if (outE.length) panel.appendChild(niConnSection('Leads to →', outE.map(e => ({ id: e.to, label: e.label }))));
    if (inE.length) panel.appendChild(niConnSection('← From', inE.map(e => ({ id: e.from, label: e.label }))));
    // footer — back-stack · open notes
    const foot = niEl('div', 'ni-foot');
    if (infoStack.length) { const bk = niEl('button', 'ni-back'); bk.textContent = '← Back'; bk.onclick = () => { const prev = infoStack.pop(); if (!prev) return; const pn = byId(prev); selection.clear(); selection.add(prev); niOpenId = prev; render(); if (pn) focusNode(pn); }; foot.appendChild(bk); }
    const notes = niEl('button', 'primary'); notes.textContent = '✐ Notes'; notes.onclick = () => { const nn = byId(n.id) || n; openEditor(nn); }; foot.appendChild(notes);
    panel.appendChild(foot);
  }

  // ---- multi-map Home overview (item 35) ----
  function openHomeOverlay() {
    const overlay = document.getElementById('home-overlay'), cards = document.getElementById('home-cards'); cards.innerHTML = '';
    const parentOf = mapParents();
    MAPS.order.forEach(slug => {
      if (parentOf[slug]) return;   // top-level maps only (children nest under them)
      const m = MAPS.maps[slug]; if (!m) return;
      const card = document.createElement('div'); card.className = 'home-card' + (slug === cur ? ' current' : ''); card.title = m.title || slug;
      const t = document.createElement('div'); t.className = 'hc-title'; t.textContent = m.title || slug; card.appendChild(t);
      const info = document.createElement('div'); info.className = 'hc-info';
      const c = document.createElement('span'); c.className = 'hc-count'; c.textContent = (m.nodes || []).length + ' nodes'; info.appendChild(c);
      const hasOut = new Set((m.edges || []).filter(e => e.from !== e.to).map(e => e.from));
      const ungated = (m.nodes || []).filter(n => hasOut.has(n.id) && n.type !== 'reference' && !(n.gate && String(n.gate).trim())).length;
      if (ungated) { const w = document.createElement('span'); w.className = 'hc-warning'; w.textContent = '⚠ ' + ungated + ' ungated'; info.appendChild(w); }
      if (m.kind === 'reference') { const r = document.createElement('span'); r.className = 'hc-warning'; r.style.background = 'rgba(107,114,128,.14)'; r.style.borderColor = 'rgba(107,114,128,.35)'; r.style.color = 'var(--ref)'; r.textContent = '§ library'; info.appendChild(r); }
      card.appendChild(info);
      const children = MAPS.order.filter(x => parentOf[x] === slug);
      if (children.length) { const ch = document.createElement('div'); ch.className = 'hc-children'; ch.textContent = '↳ ' + children.map(x => (MAPS.maps[x] || {}).title || x).join(', '); card.appendChild(ch); }
      const go = () => { closeHomeOverlay(); jumpMap(slug); };
      card.tabIndex = 0; card.setAttribute('role', 'button'); card.onclick = go;
      card.onkeydown = ev => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); go(); } };   // cards were mouse-only <div>s
      const arch = document.createElement('button'); arch.className = 'hc-archive'; arch.type = 'button'; arch.textContent = '✕'; arch.title = 'Archive this map';
      arch.onclick = async ev => { ev.stopPropagation(); if (!SERVER) return; const childTxt = children.length ? '\n\nChild maps (' + children.length + ') will be orphaned but kept.' : ''; if (!confirm('Archive map "' + (m.title || slug) + '"?\nMoves maps-data/' + slug + '/ to maps-data/.archive/.' + childTxt)) return; const j = await api('/api/map-archive', { map: slug }); if (j && j.ok) { if (slug === cur) { const fallback = MAPS.order.find(s => s !== slug); if (fallback) jumpMap(fallback); } applyMaps(j.maps); openHomeOverlay(); } else alert('Archive: ' + (j && j.error || 'failed')); };
      card.appendChild(arch);
      cards.appendChild(card);
    });
    overlay.classList.add('open');
    const first = cards.querySelector('.home-card'); if (first) first.focus();   // move focus into the overlay for keyboard users (Esc closes via the global handler)
  }
  function closeHomeOverlay() { document.getElementById('home-overlay').classList.remove('open'); }

  // ---- wire UI ----
  document.getElementById('mapsel').onchange = e => jumpMap(e.target.value);
  document.getElementById('fit').onclick = fit;
  document.getElementById('tidy').onclick = tidyLayout;
  document.getElementById('addnode').onclick = () => { const c = viewCenter(); quickAdd(c.x, c.y, window.innerWidth / 2, window.innerHeight / 2); };
  document.getElementById('addmap').onclick = addMapPrompt;
  document.getElementById('addbox').onclick = addFrame;
  document.getElementById('lanes').onclick = () => { showLanes = !showLanes; document.getElementById('lanes').classList.toggle('on', showLanes); render(); };
  document.getElementById('undo').onclick = doUndo;
  document.getElementById('export').onclick = openExport;
  document.getElementById('ex-close').onclick = () => document.getElementById('exportpanel').hidden = true;
  document.getElementById('ex-copyspec').onclick = () => copyText(document.getElementById('ex-spec').textContent, 'spec');
  document.getElementById('ex-copymd').onclick = () => copyText(document.getElementById('ex-md').textContent, 'workflow');
  { const cg = document.getElementById('ctx-gate');
    cg.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); cg.blur(); } };
    cg.onblur = () => { if (ctxNode) nodeStyle({ gate: cg.value.trim() }); }; }
  document.getElementById('ed-close').onclick = closeEditor;
  document.getElementById('ed-save').onclick = saveDoc;
  let autosaveTimer = null;
  document.getElementById('ed-text').addEventListener('input', e => {   // live ref chips + inline [[ autocomplete + debounced autosave
    renderRefs(e.target.value);
    const ta = e.target, pos = ta.selectionStart, before = ta.value.slice(0, pos);
    if (before.endsWith('[[')) openCitationPicker(ta, pos);
    else if (citationPicker) { const mm = before.match(/\[\[([^\]\n]*)$/); if (mm) renderKpList(mm[1]); else closeCitationPicker(); }
    if (edPath) { clearTimeout(autosaveTimer); document.getElementById('ed-msg').textContent = 'Saving…'; autosaveTimer = setTimeout(saveDoc, 800); }
  });
  document.getElementById('libtoggle').onclick = toggleLibrary;
  document.getElementById('kp-x').onclick = closeKnowPick;
  document.getElementById('cmdpal-x').onclick = closeCmdpal;
  document.getElementById('cmdpal-search').addEventListener('input', e => { cmdpalSel = 0; renderCmdpalList(e.target.value); });
  document.getElementById('shortcuts-close').onclick = closeShortcutsOverlay;
  document.getElementById('shortcuts').onclick = e => { if (e.target.id === 'shortcuts') closeShortcutsOverlay(); };
  document.getElementById('toast-undo-btn').onclick = () => { clearTimeout(toastTimeout); fadeOut(document.getElementById('toast-undo')); doUndo(); };
  document.getElementById('toast-close').onclick = () => { clearTimeout(toastTimeout); fadeOut(document.getElementById('toast-undo')); };
  document.querySelector('.lint-badge').onclick = toggleLint;
  document.getElementById('home').onclick = openHomeOverlay;
  document.getElementById('home-close').onclick = closeHomeOverlay;
  document.getElementById('home-overlay').onclick = e => { if (e.target.id === 'home-overlay') closeHomeOverlay(); };
  document.getElementById('kp-search').addEventListener('input', e => renderKpList(e.target.value));
  document.getElementById('ctx-linkknow').onclick = () => { if (ctxNode) openKnowPick(ctxNode); };
  document.getElementById('ed-openext').onclick = () => { if (edPath) fetch('/api/open?path=' + encodeURIComponent(edPath)).catch(() => {}); };
  document.getElementById('ed-title').ondblclick = () => { if (edNode) renameFromDrawer(edNode); };   // rename title+slug from the side panel
  document.getElementById('ctx-rename').onclick = () => { const d = ctxNode; closeCtx(); if (d) openRename(d); };
  document.getElementById('ctx-notes').onclick = () => { const d = ctxNode; closeCtx(); if (d) openEditor(d); };
  document.getElementById('ctx-smaller').onclick = () => ctxSize(-1);
  document.getElementById('ctx-bigger').onclick = () => ctxSize(1);
  document.getElementById('ctx-hl').onclick = ctxHighlight;
  document.getElementById('ctx-archive').onclick = ctxArchive;
  document.getElementById('ctx-newsub').onclick = ctxNewSubmap;
  document.getElementById('ctx-linkmap').onchange = e => ctxLink(e.target.value);
  document.querySelectorAll('#ctx-types button').forEach(b => b.onclick = () => ctxType(b.dataset.t));
  // double-click empty canvas → quick add
  svg.on('dblclick.add', e => { if (e.target.closest('.node') || e.target.closest('.edgegrp') || e.target.closest('.frame-grab')) return; const [mx, my] = d3.pointer(e, canvas.node()); quickAdd(mx, my, e.clientX, e.clientY); });
  svg.on('contextmenu.add', e => { if (e.target.closest('.node') || e.target.closest('.edgegrp') || e.target.closest('.frame-grab')) return; e.preventDefault(); closeCtx(); const [mx, my] = d3.pointer(e, canvas.node()); quickAdd(mx, my, e.clientX, e.clientY); });
  svg.on('click.sel', e => { if (e.shiftKey) return; if (!e.target.closest('.node') && !e.target.closest('.edgegrp') && !e.target.closest('.frame-grab')) { if (!document.getElementById('editor').hidden) closeEditor(); clearSelection(); } });   // click empty canvas → close editor + info panel, deselect (ignore the trailing click after a shift-marquee)
  svg.on('mousedown.marquee', startMarquee);
  window.addEventListener('mousemove', updateMarquee);
  window.addEventListener('mouseup', endMarquee);
  document.addEventListener('click', e => {
    const m = document.getElementById('ctx'); if (!m.hidden && !m.contains(e.target)) closeCtx();
    const kp = document.getElementById('knowpick');                                    // dismiss the picker on an outside click (ignoring the click that opened it)
    if (!kp.hidden && !kp.contains(e.target) && !e.target.closest('#ctx-linkknow')) closeKnowPick();
    const cp = document.getElementById('cmdpal'); if (!cp.hidden && !cp.contains(e.target)) closeCmdpal();
  });
  document.addEventListener('keydown', e => {
    const a = document.activeElement, typing = a && (a.tagName === 'INPUT' || a.tagName === 'TEXTAREA' || a.isContentEditable), cmd = e.metaKey || e.ctrlKey;
    if (!document.getElementById('cmdpal').hidden) {   // palette navigation wins while it's open
      if (e.key === 'ArrowDown') { e.preventDefault(); cmdpalMove(1); return; }
      if (e.key === 'ArrowUp') { e.preventDefault(); cmdpalMove(-1); return; }
      if (e.key === 'Enter') { e.preventDefault(); cmdpalRun(); return; }
      if (e.key === 'Escape') { e.preventDefault(); closeCmdpal(); return; }
    }
    if (cmd && e.key.toLowerCase() === 'k') { e.preventDefault(); const cp = document.getElementById('cmdpal'); if (cp.hidden) openCmdpal(); else closeCmdpal(); return; }
    if (cmd && e.key.toLowerCase() === 'f' && !typing) { e.preventDefault(); openFind(); return; }
    if (e.key === '/' && !typing) { e.preventDefault(); openFind(); return; }
    if (e.key === '?' && !typing) { e.preventDefault(); showShortcutsOverlay(); return; }
    if (e.key === 'Escape') { closeEditor(); closeCtx(); closeKnowPick(); closeCmdpal(); closeShortcutsOverlay(); closeHomeOverlay(); document.querySelectorAll('.broken-overlay,.backlink-list').forEach(el => el.remove()); document.getElementById('exportpanel').hidden = true; clearSelection(); return; }
    if (cmd && e.key.toLowerCase() === 's' && !document.getElementById('editor').hidden) { e.preventDefault(); saveDoc(); return; }
    if (cmd && e.key.toLowerCase() === 'z' && !typing) { e.preventDefault(); doUndo(); return; }   // redo deferred: server has single-level undo only
    if (typing) return;   // everything below is canvas-only
    if (e.shiftKey && (e.key === '1' || e.code === 'Digit1')) { e.preventDefault(); fit(); return; }   // Shift+1 = fit
    if ((e.key === 'n' || e.key === 'N') && !cmd && !e.shiftKey) { if (SERVER) { e.preventDefault(); const c = viewCenter(); quickAdd(c.x, c.y, window.innerWidth / 2, window.innerHeight / 2); } return; }   // N = add a node
    if (cmd && e.key.toLowerCase() === 'a' && map()) { e.preventDefault(); map().nodes.forEach(n => selection.add(n.id)); render(); return; }   // select all
    if (cmd && e.key.toLowerCase() === 'd' && selection.size && SERVER) { e.preventDefault(); api('/api/add-batch', { map: cur, nodes: selNodes().map(n => ({ title: n.name + ' copy', type: n.type, x: n.x + 28, y: n.y + 28, note: '', scale: n.scale, color: n.color, gate: n.gate, hl: n.hl, lane: n.lane, link_map: n.link_map, summary: n.summary, tags: n.tags, status: n.status })) }).then(flushPending); return; }   // duplicate (atomic batch → one undo, styling preserved)
    if (cmd && e.key.toLowerCase() === 'c' && selection.size) { e.preventDefault(); copySelection(); return; }   // copy
    if (cmd && e.key.toLowerCase() === 'v' && clipboard && clipboard.nodes.length) { e.preventDefault(); pasteSelection(); return; }   // paste (across maps)
    if ((e.key === 'Backspace' || e.key === 'Delete') && selection.size && SERVER) { e.preventDefault(); if (!confirm('Archive ' + selection.size + ' node' + (selection.size === 1 ? '' : 's') + '?')) return; selNodes().forEach(n => api('/api/archive', { path: repoRel(n.url) }).then(flushPending)); selection.clear(); render(); return; }   // archive selection
    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key) && selection.size) { e.preventDefault(); const d = e.shiftKey ? 24 : 4, dx = e.key === 'ArrowRight' ? d : e.key === 'ArrowLeft' ? -d : 0, dy = e.key === 'ArrowDown' ? d : e.key === 'ArrowUp' ? -d : 0; selNodes().forEach(n => { n.x += dx; n.y += dy; }); scheduleRender(); clearTimeout(nudgeTimer); nudgeTimer = setTimeout(() => persistPos(selNodes()), 350); return; }   // nudge selection (debounced persist)
  });
  ['ctx', 'editor', 'knowpick', 'exportpanel', 'cmdpal'].forEach(id => {   // a11y focus-trap — keep Tab within an open dialog (attached once, inert while hidden)
    const dlg = document.getElementById(id); if (!dlg) return;
    dlg.addEventListener('keydown', e => {
      if (e.key !== 'Tab' || dlg.hidden) return;
      const f = dlg.querySelectorAll('button,input,textarea,select,[tabindex]:not([tabindex="-1"])'); if (!f.length) return;
      const first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    });
  });

  // ---- boot ----
  const statusEl = document.getElementById('connstatus');
  function updateConnStatus(state) {
    if (!statusEl) return;
    statusEl.className = state === 'live' ? '' : state === 'readonly' ? 'readonly' : 'reconnecting';
    statusEl.textContent = state === 'live' ? '● Live' : state === 'readonly' ? '◌ Read-only' : '⟳ Reconnecting…';
  }
  let eventSource = null;
  function startEventSource() {
    if (eventSource) return;
    eventSource = new EventSource('/api/events');
    eventSource.onmessage = ev => { try { queueSse(JSON.parse(ev.data)); debounceSse(flushSse, 80); } catch (_) {} };   // coalesce SSE bursts → one applyMaps (per-slug patches merged)
    eventSource.onerror = () => { if (eventSource) eventSource.close(); eventSource = null; updateConnStatus('reconnecting'); setTimeout(startEventSource, 2000); };   // auto-reconnect w/ status
    eventSource.onopen = () => { if (SERVER) updateConnStatus('live'); };
  }
  fetch('/api/ping').then(r => r.ok).then(ok => {
    SERVER = !!ok;
    if (SERVER) { updateConnStatus('live'); startEventSource(); } else updateConnStatus('readonly');
  }).catch(() => { SERVER = false; updateConnStatus('readonly'); })
    .finally(() => { document.body.classList.toggle('server', SERVER); document.body.classList.add('checked'); });
  if (window.matchMedia && window.matchMedia('(pointer:coarse)').matches) document.body.classList.add('touch');   // touch device → reveal ports/edge-controls without hover

  const boot = (location.hash.match(/map=([^&]+)/) || [])[1];
  if (boot && MAPS.maps[boot]) cur = boot;
  try { fillMapSelect(); fillLinkSelect(); render(); document.body.classList.add('d3-canvas-ready'); }   // headless-test signal: boot render done — set synchronously (rAF is throttled/paused in bg iframes). tools/validate_canvas.py
  catch (e) { document.body.classList.add('d3-canvas-error'); throw e; }
  requestAnimationFrame(() => { fit(true); render(); });   // defer fit one frame so the iframe has real dimensions, then instant-fit + re-cull (no flash, no missed-transition)
})();
