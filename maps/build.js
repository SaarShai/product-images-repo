#!/usr/bin/env node
// Build the process-maps dashboard data by walking maps-data/ (source of truth).
//   maps-data/index.md            -> registry: `maps: [slug, ...]` (menu order)
//   maps-data/<map>/index.md      -> a map: `nodes: [slug,...]` + `edges:` list
//   maps-data/<map>/<node>.md     -> a node: title, type, x, y, lane?, link_map?
// Output: maps/data.js  (window.MAPS = { order:[...], maps:{ slug:{...} } })
// Node identity is a stable `nid:` (minted + written back), like the pursuits build.
// No deps. Offline. Run: node maps/build.js
'use strict';
const fs = require('fs');
const path = require('path');

const MAPS = __dirname;                       // maps/
const ROOT = path.resolve(MAPS, '..');        // repo root
const SRC = path.join(ROOT, 'maps-data');
const OUT = path.join(MAPS, 'data.js');

const issues = [];   // structured, surfaced in window.MAPS.issues (was a flat `warnings` string[])
function issue(map, msg, level, node) { issues.push({ map: map || null, node: node || null, level: level || 'warn', msg: msg }); }
let nodeCount = 0;

// tolerant validation — canonical node types + the aliases hand/LLM edits commonly produce.
// An unknown type/status is normalized (or cleared) and logged, never left to silently mis-render.
const TYPE_CANON = ['step', 'decision', 'subprocess-link', 'reference'];
const TYPE_ALIASES = { task: 'step', process: 'step', action: 'step', activity: 'step', state: 'step', branch: 'decision', condition: 'decision', choice: 'decision', if: 'decision', gateway: 'decision', link: 'subprocess-link', subprocess: 'subprocess-link', submap: 'subprocess-link', 'sub-map': 'subprocess-link', sublink: 'subprocess-link', ref: 'reference', source: 'reference', sot: 'reference', doc: 'reference', document: 'reference' };
const STATUS_CANON = ['draft', 'active', 'blocked', 'done'];
const STATUS_ALIASES = { draft: 'draft', todo: 'draft', planned: 'draft', backlog: 'draft', active: 'active', wip: 'active', 'in-progress': 'active', inprogress: 'active', doing: 'active', current: 'active', blocked: 'blocked', stuck: 'blocked', waiting: 'blocked', onhold: 'blocked', 'on-hold': 'blocked', done: 'done', complete: 'done', completed: 'done', shipped: 'done' };

// unquote a frontmatter scalar. JSON.stringify'd values (title:/gate:) decode via JSON.parse; bare values strip one quote pair.
function clean(s) { if (s == null) return null; s = String(s).trim(); if (/^".*"$/s.test(s)) { try { return JSON.parse(s); } catch (_) {} } return s.replace(/^["']|["']$/g, ''); }
// decode a label group captured WITH its surrounding quotes (JSON string); tolerates legacy/hand-edited values.
function jparse(s) { if (s == null) return ''; try { return JSON.parse(s); } catch (_) { return String(s).replace(/^"|"$/g, ''); } }
function fmBlock(txt) { const m = txt.match(/^---\r?\n([\s\S]*?)\r?\n---/); return m ? m[1] : ''; }   // \r? tolerates CRLF: else the whole block fails to parse and nid/title/x/y all read null
function field(fm, key) { const m = fm.match(new RegExp('^' + key + ':\\s*(.+)$', 'm')); return m ? clean(m[1]) : null; }
function listField(fm, key) {
  const m = fm.match(new RegExp('^' + key + ':\\s*\\[(.*)\\]\\s*$', 'm'));
  if (m) return m[1].split(',').map(s => s.trim()).filter(Boolean);
  // also accept a YAML block list: `key:` then indented `- item` lines (hand/LLM edits commonly produce this)
  const b = fm.match(new RegExp('^' + key + ':\\s*\\r?\\n((?:[ \\t]*-[ \\t]*[^\\n]+\\r?\\n?)+)', 'm'));
  if (b) return b[1].split(/\r?\n/).map(s => s.replace(/^[ \t]*-[ \t]*/, '').trim()).filter(Boolean);
  return [];
}
// parse the `edges:` block: a sequence of `- {from: a, to: b, label: "..."}` lines
function edgesField(fm) {
  const out = [];
  const re = /\{\s*from:\s*([^,}]+?)\s*,\s*to:\s*([^,}]+?)\s*(?:,\s*label:\s*("(?:[^"\\]|\\.)*"))?\s*(?:,\s*bend:\s*(-?\d+))?\s*(?:,\s*color:\s*(\d+))?\s*(?:,\s*route:\s*([a-z]+))?\s*\}/g;
  let m;
  while ((m = re.exec(fm))) out.push({ from: clean(m[1]), to: clean(m[2]), label: jparse(m[3]), bend: m[4] != null ? +m[4] : 0, color: m[5] != null ? +m[5] : null, route: m[6] || 'bezier' });
  return out;
}
// citations in a node body: [[nid|label]] — same syntax as the wiki. Skips [[?stub]] (not-yet-written).
function refsOf(body) {
  const out = [], seen = new Set(), re = /\[\[([^\]]+)\]\]/g;
  let m; while ((m = re.exec(body))) {
    const parts = m[1].split('|'), tgt = (parts[0] || '').trim();
    if (!tgt || tgt.startsWith('?') || seen.has(tgt)) continue;
    seen.add(tgt); out.push({ target: tgt, label: (parts[1] || parts[0] || '').trim() });
  }
  return out;
}
// parse the `frames:` block: `- {id: f1, label: "..", x: N, y: N, w: N, h: N, color: N}` (background boxes)
function framesField(fm) {
  const out = [];
  const re = /\{\s*id:\s*([^,}]+?)\s*,\s*label:\s*("(?:[^"\\]|\\.)*")\s*,\s*x:\s*(-?\d+)\s*,\s*y:\s*(-?\d+)\s*,\s*w:\s*(\d+)\s*,\s*h:\s*(\d+)\s*(?:,\s*color:\s*(\d+))?\s*\}/g;
  let m;
  while ((m = re.exec(fm))) out.push({ id: clean(m[1]), label: jparse(m[2]), x: +m[3], y: +m[4], w: +m[5], h: +m[6], color: m[7] != null ? +m[7] : 0 });
  return out;
}

// stable per-node/map id, persists across renames; minted + written back into the file
const usedIds = new Set();
function genId(prefix) { let id; do { id = prefix + Math.random().toString(36).slice(2, 7); } while (usedIds.has(id)); usedIds.add(id); return id; }
function ensureNid(file, fm, prefix) {
  const existing = field(fm, 'nid');
  if (existing) { usedIds.add(existing); return existing; }
  const nid = genId(prefix);
  fs.writeFileSync(file, fs.readFileSync(file, 'utf8').replace(/^---\r?\n/, () => '---\nnid: ' + nid + '\n'));   // \r? so the write-back actually lands on CRLF files (else the nid churns every build)
  return nid;
}

function readNode(mapSlug, nodeSlug) {
  const file = path.join(SRC, mapSlug, nodeSlug + '.md');
  if (!fs.existsSync(file)) { issue(mapSlug, 'missing node "' + nodeSlug + '"', 'warn', nodeSlug); return null; }
  const txt = fs.readFileSync(file, 'utf8');
  const fm = fmBlock(txt);
  const nid = ensureNid(file, fm, 'n');
  const h1 = (txt.match(/^#\s+(.+)$/m) || [])[1];
  const x = Number(field(fm, 'x')); const y = Number(field(fm, 'y'));
  const scale = Number(field(fm, 'scale')); const color = field(fm, 'color');
  const body = txt.replace(/^---\n[\s\S]*?\n---\n?/, '');   // body sans frontmatter — for [[wiki]] citations

  // ---- tolerant field normalization (drop-broken-keep-rest) ----
  let type = field(fm, 'type') || 'step';
  if (type !== 'step') {
    const lc = String(type).toLowerCase();
    if (TYPE_CANON.includes(lc)) type = lc;
    else if (TYPE_ALIASES[lc]) { issue(mapSlug, nodeSlug + ': type "' + type + '" → "' + TYPE_ALIASES[lc] + '"', 'fixed', nodeSlug); type = TYPE_ALIASES[lc]; }
    else { issue(mapSlug, nodeSlug + ': unknown type "' + type + '" → "step"', 'fixed', nodeSlug); type = 'step'; }
  }
  let status = field(fm, 'status');
  if (status) { const s = STATUS_ALIASES[String(status).toLowerCase()]; if (s) status = s; else { issue(mapSlug, nodeSlug + ': unknown status "' + status + '" → cleared', 'fixed', nodeSlug); status = null; } }
  const tags = listField(fm, 'tags').map(t => t.trim().toLowerCase()).filter(Boolean);
  const summary = field(fm, 'summary') || null;
  let colorIx = null;   // palette-index override of lane/type accent
  if (color != null && color !== '') { const c = Math.trunc(+color); if (Number.isFinite(c) && c >= 0) colorIx = c; else issue(mapSlug, nodeSlug + ': bad color "' + color + '" → cleared', 'fixed', nodeSlug); }
  const sc = Number.isFinite(scale) && scale > 0 ? Math.min(4, scale) : 1;   // clamp upper so a corrupt scale can't blow up layout

  nodeCount++;
  return {
    id: nid,
    slug: nodeSlug,
    name: field(fm, 'title') || (h1 && h1.trim()) || nodeSlug,
    type,
    summary,                                     // 1-line purpose (NodeInfo panel + tooltip)
    icon: field(fm, 'icon') || null,             // optional emoji/char shown on the card for at-a-glance distinction
    tags,                                        // lowercase-hyphenated keywords (search / filter)
    status,                                      // draft | active | blocked | done (or null)
    refs: refsOf(body),                          // [{target,label}] — knowledge this node cites (rendered as a tray below it)
    refsCollapsed: field(fm, 'refs_collapsed') === 'true',   // tray box collapsed?

    x: Number.isFinite(x) ? x : null,
    y: Number.isFinite(y) ? y : null,
    lane: field(fm, 'lane') || null,
    link_map: field(fm, 'link_map') || null,
    gate: field(fm, 'gate') || null,            // per-stage pass/fail check (for the loop-spec export)
    scale: sc,
    hl: field(fm, 'hl') === 'true',
    color: colorIx,
    url: path.relative(MAPS, file),
  };
}

function readMap(mapSlug) {
  const idx = path.join(SRC, mapSlug, 'index.md');
  if (!fs.existsSync(idx)) { issue(mapSlug, 'missing map index', 'warn'); return null; }
  const txt = fs.readFileSync(idx, 'utf8');
  const fm = fmBlock(txt);
  const mid = ensureNid(idx, fm, 'm');
  const nodeSlugs = listField(fm, 'nodes');
  const nodes = nodeSlugs.map(s => readNode(mapSlug, s)).filter(Boolean);
  const bySlug = {}; nodes.forEach(n => { bySlug[n.slug] = n.id; });
  // seed any node missing x/y onto a simple staggered grid so it's never stacked at origin
  let gi = 0;
  nodes.forEach(n => { if (n.x == null || n.y == null) { n.x = 120 + (gi % 5) * 240; n.y = 120 + Math.floor(gi / 5) * 160; gi++; } });
  const seenEdge = new Set();
  const edges = edgesField(fm).map(e => {
    const from = bySlug[e.from], to = bySlug[e.to];
    if (!from) issue(mapSlug, 'edge from unknown node "' + e.from + '" — dropped', 'warn');
    if (!to) issue(mapSlug, 'edge to unknown node "' + e.to + '" — dropped', 'warn');
    if (!from || !to) return null;                         // drop-broken-keep-rest: a dangling edge never breaks the map
    const k = from + '>' + to;
    if (seenEdge.has(k)) { issue(mapSlug, 'duplicate edge ' + e.from + ' → ' + e.to + ' — dropped', 'fixed'); return null; }
    seenEdge.add(k);
    return { from, to, label: e.label || '', bend: e.bend || 0, color: e.color != null ? e.color : null, route: e.route || 'bezier' };
  }).filter(Boolean);
  const frames = framesField(fm);
  const kind = field(fm, 'kind') || 'process';   // 'reference' = a SoT library map (no flow / workflow)
  return { slug: mapSlug, id: mid, title: field(fm, 'title') || mapSlug, kind, url: path.relative(MAPS, idx), nodes, edges, frames };
}

// Build maps/data.js from maps-data/. Callable in-process (serve.js) AND as a CLI.
// Returns { order, maps, issues } so the server can broadcast it without re-reading data.js.
function build() {
  issues.length = 0; nodeCount = 0; usedIds.clear();   // reset module state → repeated in-process builds are independent
  const registry = path.join(SRC, 'index.md');
  if (!fs.existsSync(registry)) throw new Error('missing maps-data/index.md');
  const order = listField(fmBlock(fs.readFileSync(registry, 'utf8')), 'maps');
  const maps = {};
  order.forEach(slug => { const m = readMap(slug); if (m) maps[slug] = m; });
  const out = { order: order.filter(s => maps[s]), maps, issues: issues.slice() };   // issues → surfaced in the dashboard lint panel
  fs.writeFileSync(OUT, 'window.MAPS = ' + JSON.stringify(out, null, 2) + ';\n');
  return out;
}

module.exports = { build };

if (require.main === module) {   // CLI: node build.js
  const out = build();
  console.log('wrote ' + path.relative(process.cwd(), OUT) + '  (' + out.order.length + ' maps, ' + nodeCount + ' nodes)');
  if (out.issues.length) { console.log('ISSUES:'); out.issues.forEach(i => console.log('  - [' + i.level + '] ' + (i.map ? i.map + '/' : '') + i.msg)); }
}
