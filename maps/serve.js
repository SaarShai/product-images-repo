// Local app server for the process-maps dashboard.
// Source of truth = maps-data/ (markdown). build.js regenerates maps/data.js after each write.
// API: ping, events(SSE), doc, export, save, add, rename, archive, pos, edge(add/del), map-add, link.
// Run: node maps/serve.js [port]
'use strict';
const http = require('http');
const fs = require('fs');
const path = require('path');
const { execFile } = require('child_process');
const { build } = require('./build.js');   // call the SOLE parser in-process (no per-mutation `node` spawn → fast, and no concurrent-build torn-write race)

process.on('uncaughtException', e => console.error('[serve] uncaught (kept alive):', e && (e.stack || e.message || e)));   // a dev server must survive one bad async throw, not die mid-session
process.on('unhandledRejection', e => console.error('[serve] unhandled rejection:', e && (e.message || e)));

const DASH = __dirname;                         // maps/
const ROOT = path.resolve(DASH, '..');          // repo root
const SRC = path.join(ROOT, 'maps-data');       // markdown source
const ARCHIVE = path.join(SRC, '.archive');
const PORT = Number(process.argv[2]) || Number(process.env.PORT) || 8780;
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.md': 'text/plain' };
const slugify = s => String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');

function json(res, o, code) { res.writeHead(code || 200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(o)); }
function rebuild() { return build(); }   // synchronous, in-process; returns {order, maps}

const sseClients = new Set();
let changedSlug = null;   // set by the POST wrapper to the single map a mutation touched (null = multi-map/unknown → send full)
function broadcast(maps, slug) {
  // single-map edit → ship only that map (other SSE clients merge it); multi-map/unknown → full snapshot. The acting client already has full state from the POST reply.
  const payload = (slug && maps.maps[slug]) ? { t: 'patch', slug, order: maps.order, map: maps.maps[slug], issues: maps.issues } : { t: 'full', maps };   // carry build issues so a single-map edit refreshes the global lint badge
  const msg = 'data:' + JSON.stringify(payload) + '\n\n';
  sseClients.forEach(res => { try { res.write(msg); } catch (e) { sseClients.delete(res); } });
}
// rebuild then push fresh window.MAPS to all clients; reply to the caller too
function rebuildAndReply(res, extra) {
  let maps;
  try { maps = build(); } catch (e) { changedSlug = null; return json(res, { ok: false, error: 'build failed: ' + (e.message || e) }, 500); }   // in-process build returns the object directly (no re-read of data.js → no torn-read race)
  broadcast(maps, changedSlug); changedSlug = null;
  json(res, Object.assign({ ok: true, maps }, extra || {}));
}

// confine a repo-relative path to maps-data/
function safeSrc(rel) {
  if (!rel) return null;
  const abs = path.resolve(ROOT, rel);
  if (abs !== SRC && !abs.startsWith(SRC + path.sep)) return null;
  return abs;
}
const mapIndex = mapSlug => path.join(SRC, mapSlug, 'index.md');
const mapDirOf = absNode => path.dirname(absNode);
const mapSlugOf = absNode => path.basename(path.dirname(absNode));

// ---- frontmatter helpers (regex, matches build.js) ----
function jparse(s) { if (s == null) return ''; try { return JSON.parse(s); } catch (_) { return String(s).replace(/^"|"$/g, ''); } }   // decode a label captured WITH quotes
function titleOf(txt) {
  const t = (txt.match(/^title:\s*(.+)$/m) || [])[1];
  if (t) { const s = t.trim(); if (/^".*"$/s.test(s)) { try { return JSON.parse(s); } catch (_) {} } return s.replace(/^["']|["']$/g, ''); }
  const h = (txt.match(/^#\s+(.+)$/m) || [])[1];
  return h ? h.trim() : null;
}
// scope a mutation to the frontmatter block only, so a body line starting with the same key is never touched
function inFrontmatter(txt, mutate) {
  const fmEnd = txt.indexOf('\n---', 3);                       // newline before the closing fence
  if (fmEnd === -1) return mutate(txt);                        // fence-less file → whole-file fallback
  return mutate(txt.slice(0, fmEnd)) + txt.slice(fmEnd);
}
function setField(txt, key, val) {
  const line = key + ': ' + val, re = new RegExp('^' + key + ':[^\\n]*', 'm');   // [^\n]* (not .*$) tolerates a trailing \r on CRLF lines
  return inFrontmatter(txt, head => re.test(head) ? head.replace(re, () => line) : head.replace(/^---\r?\n/, () => '---\n' + line + '\n'));   // () => line replacer: a literal $ in val is never treated as a $&/$`/$$ replace-pattern
}
function removeField(txt, key) {
  const re = new RegExp('^' + key + ':.*\\n', 'm');
  return inFrontmatter(txt, head => head.replace(re, ''));
}
function getList(txt, key) {
  const l = (txt.match(new RegExp('^' + key + ':\\s*\\[(.*)\\]\\s*$', 'm')) || [])[1];
  return l ? l.split(',').map(s => s.trim()).filter(Boolean) : [];
}
function setList(txt, key, arr) {
  const line = key + ': [' + arr.join(', ') + ']', re = new RegExp('^' + key + ':\\s*\\[[^\\n]*\\]', 'm');
  return inFrontmatter(txt, head => re.test(head) ? head.replace(re, () => line) : head.replace(/^---\r?\n/, () => '---\n' + line + '\n'));
}
function getEdges(txt) {
  const out = [];
  const re = /\{\s*from:\s*([^,}]+?)\s*,\s*to:\s*([^,}]+?)\s*(?:,\s*label:\s*("(?:[^"\\]|\\.)*"))?\s*(?:,\s*bend:\s*(-?\d+))?\s*(?:,\s*color:\s*(\d+))?\s*(?:,\s*route:\s*([a-z]+))?\s*\}/g;
  let m; while ((m = re.exec(txt))) out.push({ from: m[1].trim(), to: m[2].trim(), label: jparse(m[3]), bend: m[4] != null ? +m[4] : 0, color: m[5] != null ? +m[5] : null, route: m[6] || 'bezier' });
  return out;
}
function setEdges(txt, arr) {
  txt = txt.replace(/^edges:[^\n]*(?:\n[ \t]+[^\n]*)*\n?/m, '');   // strip old block
  const block = 'edges:\n' + arr.map(e => {
    let s = '  - {from: ' + e.from + ', to: ' + e.to + ', label: ' + JSON.stringify(e.label || '');
    if (e.bend) s += ', bend: ' + Math.round(e.bend);
    if (e.color != null && e.color !== '') s += ', color: ' + e.color;
    if (e.route && e.route !== 'bezier') s += ', route: ' + e.route;
    return s + '}';
  }).join('\n') + '\n';
  const close = txt.indexOf('\n---', 3);                            // before closing fence
  if (close === -1) return txt;
  return txt.slice(0, close + 1) + (arr.length ? block : '') + txt.slice(close + 1);
}
// background-box frames (same block idiom as edges)
function getFrames(txt) {
  const out = [];
  const re = /\{\s*id:\s*([^,}]+?)\s*,\s*label:\s*("(?:[^"\\]|\\.)*")\s*,\s*x:\s*(-?\d+)\s*,\s*y:\s*(-?\d+)\s*,\s*w:\s*(\d+)\s*,\s*h:\s*(\d+)\s*(?:,\s*color:\s*(\d+))?\s*\}/g;
  let m; while ((m = re.exec(txt))) out.push({ id: m[1].trim(), label: jparse(m[2]), x: +m[3], y: +m[4], w: +m[5], h: +m[6], color: m[7] != null ? +m[7] : 0 });
  return out;
}
function setFrames(txt, arr) {
  txt = txt.replace(/^frames:[^\n]*(?:\n[ \t]+[^\n]*)*\n?/m, '');
  const block = 'frames:\n' + arr.map(f => '  - {id: ' + f.id + ', label: ' + JSON.stringify(f.label || '') + ', x: ' + Math.round(f.x) + ', y: ' + Math.round(f.y) + ', w: ' + Math.round(f.w) + ', h: ' + Math.round(f.h) + ', color: ' + (f.color || 0) + '}').join('\n') + '\n';
  const close = txt.indexOf('\n---', 3);
  if (close === -1) return txt;
  return txt.slice(0, close + 1) + (arr.length ? block : '') + txt.slice(close + 1);
}
function editFrame(mapSlug, op, f) {
  const idx = mapIndex(mapSlug);
  if (!fs.existsSync(idx)) throw new Error('unknown map');
  let it = fs.readFileSync(idx, 'utf8');
  let frames = getFrames(it);
  if (op === 'add') {
    let id, n = 0; do { id = 'fr' + Math.random().toString(36).slice(2, 7); } while (frames.some(x => x.id === id) && ++n < 50);
    frames.push({ id, label: f.label || 'Group', x: f.x || 0, y: f.y || 0, w: f.w || 360, h: f.h || 240, color: f.color || 0 });
  } else {
    const t = frames.find(x => x.id === f.id);
    if (!t) throw new Error('unknown frame');
    if (op === 'del') frames = frames.filter(x => x.id !== f.id);
    else if (op === 'geom') { const num = (v, d) => Number.isFinite(+v) ? +v : d; t.x = num(f.x, t.x); t.y = num(f.y, t.y); t.w = Math.max(80, num(f.w, t.w)); t.h = Math.max(60, num(f.h, t.h)); }   // coerce finite: a NaN x/y silently drops the frame on next build
    else if (op === 'set') { if (f.label != null) t.label = f.label; if (f.color != null) t.color = f.color; }
  }
  fs.writeFileSync(idx, setFrames(it, frames));
}

// append a [[nid|label]] citation to a node body (idempotent — skips if it already cites that target)
function appendRef(rel, target, label) {
  const abs = safeSrc(rel);
  if (!abs || !fs.existsSync(abs) || path.basename(abs) === 'index.md') throw new Error('not a node');
  if (!target) throw new Error('no ref target');
  let txt = fs.readFileSync(abs, 'utf8');
  if (new RegExp('\\[\\[' + target.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(\\||\\])').test(txt)) return;   // already cites it
  const link = '[[' + target + (label ? '|' + label : '') + ']]';
  fs.writeFileSync(abs, txt.replace(/\s*$/, '') + '\n\nRef: ' + link + '\n');
}
function setMapKind(mapSlug, kind) {
  const idx = mapIndex(mapSlug);
  if (!fs.existsSync(idx)) throw new Error('unknown map');
  let it = fs.readFileSync(idx, 'utf8');
  it = (kind && kind !== 'process') ? setField(it, 'kind', kind) : removeField(it, 'kind');
  fs.writeFileSync(idx, it);
}

// ---- node ops ----
function addNode(mapSlug, title, type, x, y, note, linkMap, style) {
  const idx = mapIndex(mapSlug);
  if (!fs.existsSync(idx)) throw new Error('unknown map');
  const dir = path.dirname(idx);
  let base = (title || '').trim() || 'Untitled', slug = slugify(base);
  if (!slug) throw new Error('title has no usable slug characters');
  for (let n = 2; fs.existsSync(path.join(dir, slug + '.md')); n++) { base = ((title || '').trim() || 'Untitled') + ' ' + n; slug = slugify(base); }   // auto-uniquify instead of failing → repeated paste/duplicate keep working
  title = base;
  let fm = '---\ntitle: ' + JSON.stringify(title) + '\ntype: ' + (type || 'step') +
    '\nx: ' + Math.round(x || 120) + '\ny: ' + Math.round(y || 120) + '\n';
  if (linkMap) fm += 'link_map: ' + linkMap + '\n';
  if (style) {   // carry styling on duplicate/paste so the copy isn't reset to a plain default node
    if (style.lane) fm += 'lane: ' + style.lane + '\n';
    if (style.scale != null && +style.scale && +style.scale !== 1) fm += 'scale: ' + (+style.scale) + '\n';
    if (style.hl) fm += 'hl: true\n';
    if (style.color != null && style.color !== '') fm += 'color: ' + (+style.color) + '\n';
    if (style.gate && String(style.gate).trim()) fm += 'gate: ' + JSON.stringify(String(style.gate).trim()) + '\n';
    if (style.summary && String(style.summary).trim()) fm += 'summary: ' + JSON.stringify(String(style.summary).trim()) + '\n';
    if (style.status && String(style.status).trim()) fm += 'status: ' + String(style.status).trim().toLowerCase() + '\n';
    if (Array.isArray(style.tags) && style.tags.length) { const tg = style.tags.map(t => String(t).trim().toLowerCase().replace(/,/g, '')).filter(Boolean); if (tg.length) fm += 'tags: [' + tg.join(', ') + ']\n'; }
  }
  fm += '---\n\n# ' + title + '\n\n' + (note && note.trim() ? note.trim() + '\n' : '_(empty node — edit me)_\n');
  fs.writeFileSync(path.join(dir, slug + '.md'), fm);
  let it = fs.readFileSync(idx, 'utf8');
  const nodes = getList(it, 'nodes'); nodes.push(slug);
  fs.writeFileSync(idx, setList(it, 'nodes', nodes));
  return path.relative(ROOT, path.join(dir, slug + '.md'));
}
function renameNode(rel, title) {
  const abs = safeSrc(rel);
  if (!abs || !fs.existsSync(abs) || path.basename(abs) === 'index.md') throw new Error('not a node');
  const newTitle = (title || '').trim();
  if (!newTitle) throw new Error('title required');
  const newSlug = slugify(newTitle);
  if (!newSlug) throw new Error('title has no usable slug characters');
  const oldSlug = path.basename(abs, '.md');
  const dir = mapDirOf(abs), idx = path.join(dir, 'index.md');
  fs.writeFileSync(abs, setField(fs.readFileSync(abs, 'utf8'), 'title', JSON.stringify(newTitle)));
  if (newSlug === oldSlug) return rel;
  if (fs.existsSync(path.join(dir, newSlug + '.md'))) throw new Error('a node named "' + newSlug + '" already exists in this map');
  fs.renameSync(abs, path.join(dir, newSlug + '.md'));
  // update the map index: nodes list + any edges referencing the old slug
  let it = fs.readFileSync(idx, 'utf8');
  it = setList(it, 'nodes', getList(it, 'nodes').map(s => s === oldSlug ? newSlug : s));
  it = setEdges(it, getEdges(it).map(e => ({ ...e, from: e.from === oldSlug ? newSlug : e.from, to: e.to === oldSlug ? newSlug : e.to })));   // keep bend/color/route on rename
  fs.writeFileSync(idx, it);
  return path.relative(ROOT, path.join(dir, newSlug + '.md'));
}
function archiveNode(rel) {
  const abs = safeSrc(rel);
  if (!abs || !fs.existsSync(abs) || path.basename(abs) === 'index.md') throw new Error('not a node');
  const slug = path.basename(abs, '.md'), dir = mapDirOf(abs), mapSlug = mapSlugOf(abs), idx = path.join(dir, 'index.md');
  fs.mkdirSync(ARCHIVE, { recursive: true });
  let dest = path.join(ARCHIVE, mapSlug + '__' + slug + '.md'), n = 2;
  while (fs.existsSync(dest)) dest = path.join(ARCHIVE, mapSlug + '__' + slug + '-' + (n++) + '.md');
  fs.renameSync(abs, dest);
  let it = fs.readFileSync(idx, 'utf8');
  it = setList(it, 'nodes', getList(it, 'nodes').filter(s => s !== slug));
  it = setEdges(it, getEdges(it).filter(e => e.from !== slug && e.to !== slug));
  fs.writeFileSync(idx, it);
}
function setPos(rel, x, y) {
  const abs = safeSrc(rel);
  if (!abs || !fs.existsSync(abs)) throw new Error('not found');
  let txt = setField(fs.readFileSync(abs, 'utf8'), 'x', Math.round(x));
  txt = setField(txt, 'y', Math.round(y));
  fs.writeFileSync(abs, txt);
}
function setLink(rel, linkMap) {
  const abs = safeSrc(rel);
  if (!abs || !fs.existsSync(abs) || path.basename(abs) === 'index.md') throw new Error('not a node');
  let txt = fs.readFileSync(abs, 'utf8');
  if (linkMap) { txt = setField(txt, 'link_map', linkMap); txt = setField(txt, 'type', 'subprocess-link'); }
  else { txt = removeField(txt, 'link_map'); txt = setField(txt, 'type', 'step'); }
  fs.writeFileSync(abs, txt);
}
function setType(rel, type) {
  const abs = safeSrc(rel);
  if (!abs || !fs.existsSync(abs) || path.basename(abs) === 'index.md') throw new Error('not a node');
  if (!['step', 'decision', 'subprocess-link', 'reference'].includes(type)) throw new Error('bad type');
  let txt = setField(fs.readFileSync(abs, 'utf8'), 'type', type);
  if (type !== 'subprocess-link') txt = removeField(txt, 'link_map');   // a non-link node keeps no dangling link
  fs.writeFileSync(abs, txt);
}
// size / highlight / color overrides on a node
function setNodeStyle(rel, d) {
  const abs = safeSrc(rel);
  if (!abs || !fs.existsSync(abs) || path.basename(abs) === 'index.md') throw new Error('not a node');
  let txt = fs.readFileSync(abs, 'utf8');
  if (d.scale !== undefined) txt = (d.scale && d.scale !== 1 ? setField(txt, 'scale', d.scale) : removeField(txt, 'scale'));
  if (d.hl !== undefined) txt = (d.hl ? setField(txt, 'hl', 'true') : removeField(txt, 'hl'));
  if (d.color !== undefined) txt = (d.color === null || d.color === '' ? removeField(txt, 'color') : setField(txt, 'color', d.color));
  if (d.gate !== undefined) txt = (d.gate && String(d.gate).trim() ? setField(txt, 'gate', JSON.stringify(String(d.gate).trim())) : removeField(txt, 'gate'));
  if (d.refsCollapsed !== undefined) txt = (d.refsCollapsed ? setField(txt, 'refs_collapsed', 'true') : removeField(txt, 'refs_collapsed'));
  if (d.summary !== undefined) txt = (d.summary && String(d.summary).trim() ? setField(txt, 'summary', JSON.stringify(String(d.summary).trim())) : removeField(txt, 'summary'));   // 1-line purpose
  if (d.icon !== undefined) txt = (d.icon && String(d.icon).trim() ? setField(txt, 'icon', JSON.stringify(String(d.icon).trim())) : removeField(txt, 'icon'));   // emoji/char card badge
  if (d.status !== undefined) txt = (d.status && String(d.status).trim() ? setField(txt, 'status', String(d.status).trim().toLowerCase()) : removeField(txt, 'status'));   // draft|active|blocked|done
  if (d.tags !== undefined) { const tg = (Array.isArray(d.tags) ? d.tags : []).map(t => String(t).trim().toLowerCase().replace(/,/g, '')).filter(Boolean); txt = (tg.length ? setList(txt, 'tags', tg) : removeField(txt, 'tags')); }   // strip commas so the [a, b] list round-trips
  fs.writeFileSync(abs, txt);
}
// remove a [[target…]] citation (and a leading "Ref: " label line if that's all that's left) from a node body
function removeRef(rel, target) {
  const abs = safeSrc(rel);
  if (!abs || !fs.existsSync(abs) || path.basename(abs) === 'index.md') throw new Error('not a node');
  const esc = target.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  let txt = fs.readFileSync(abs, 'utf8');
  txt = txt.replace(new RegExp('^Ref:\\s*\\[\\[' + esc + '(?:\\|[^\\]]*)?\\]\\]\\s*\\n?', 'm'), '');   // whole "Ref: [[…]]" line
  txt = txt.replace(new RegExp('\\[\\[' + esc + '(?:\\|[^\\]]*)?\\]\\]', 'g'), '');                      // any remaining inline mention
  fs.writeFileSync(abs, txt);
}

// ---- workflow export: a map → a loop-engineering loop spec + agent-followable Markdown ----
// A map is a directed graph of stages. We topologically order it, derive the loop
// spec (gate/stop/budget/generator≠verifier), and flag graph problems the agent
// must fix (no terminal, a stage with no gate, a cycle that needs a real budget).
function readMaps() {
  const raw = fs.readFileSync(path.join(DASH, 'data.js'), 'utf8').replace(/^window\.MAPS = /, '').replace(/;\s*$/, '');
  return JSON.parse(raw);
}
function nodeBody(url) {                       // the stage's prose (file body, minus frontmatter + H1)
  try {
    const abs = path.resolve(DASH, url);
    if (abs !== SRC && !abs.startsWith(SRC + path.sep)) return '';   // contain to maps-data/ (sibling-prefix safe)
    let t = fs.readFileSync(abs, 'utf8').replace(/^---\n[\s\S]*?\n---\n?/, '').replace(/^#\s+.*\n?/, '').trim();
    return t.length > 360 ? t.slice(0, 360) + '…' : t;
  } catch (_) { return ''; }
}
function buildWorkflow(slug) {
  const M = readMaps(); const map = M.maps[slug];
  if (!map) throw new Error('unknown map');
  const nodes = map.nodes || [], edges = (map.edges || []).filter(e => e.from !== e.to);
  const byId = {}; nodes.forEach(n => byId[n.id] = n);
  const out = {}, indeg = {}; nodes.forEach(n => { out[n.id] = []; indeg[n.id] = 0; });
  edges.forEach(e => { if (byId[e.from] && byId[e.to]) { out[e.from].push(e); indeg[e.to]++; } });
  const starts = nodes.filter(n => indeg[n.id] === 0);
  const terminals = nodes.filter(n => out[n.id].length === 0);
  // Kahn topological order; leftover nodes ⇒ a cycle
  const deg = {}; nodes.forEach(n => deg[n.id] = indeg[n.id]);
  const q = starts.map(n => n.id), order = [];
  while (q.length) { const id = q.shift(); order.push(id); out[id].forEach(e => { if (--deg[e.to] === 0) q.push(e.to); }); }
  const cyclic = order.length !== nodes.length;
  const reachable = new Set(order);
  const ordered = cyclic ? nodes : order.map(id => byId[id]);

  const issues = [];
  if (!nodes.length) issues.push('map has no stages');
  if (nodes.length && starts.length === 0) issues.push('no start stage — every node has an incoming edge (a cycle at the entry)');
  if (starts.length > 1) issues.push('multiple start stages (' + starts.map(n => n.name).join(', ') + ') — a workflow should have one entry');
  if (nodes.length && terminals.length === 0) issues.push('no terminal stage — nothing ends the workflow (every node has an outgoing edge)');
  if (cyclic) issues.push('cycle detected — this is a LOOP, not a once-through pipeline: set a real iteration budget and a convergence gate (see loop-engineering)');
  nodes.forEach(n => { if (!cyclic && !reachable.has(n.id)) issues.push('unreachable stage: ' + n.name); });
  nodes.filter(n => out[n.id].length > 0 && !(n.gate && n.gate.trim())).forEach(n => issues.push('stage "' + n.name + '" has no gate — add a pass/fail check before the next stage (right-click → Gate)'));

  const gateCmds = ordered.filter(n => n.gate && n.gate.trim()).map(n => n.gate.trim());
  const spec = [
    'name: ' + slug + '-workflow',
    'topology: closed · inner · single',
    'generator: agent runs each stage in topological order, one stage at a time',
    "verifier: each stage's gate, run after the stage by a separate check (not the stage's producer)",
    'gate: ' + (gateCmds.length ? gateCmds.join(' && ') : '(no stage gates defined — add a gate to each stage)'),
    'stop: reach terminal stage' + (terminals.length === 1 ? '' : 's') + ': ' + (terminals.map(n => n.name).join(', ') || '(none defined)'),
    'budget: ' + (cyclic ? 'max_iterations=20' : 'max_iterations=1'),
  ].join('\n');

  const md = ['# Workflow: ' + map.title, '',
    'Auto-generated from the "' + map.title + '" process map. Follow the stages in order; each stage must pass its **gate** before the next begins.', ''];
  ordered.forEach((n, i) => {
    md.push('## ' + (i + 1) + '. ' + n.name);
    const b = nodeBody(n.url); if (b) md.push(b);
    md.push('');
    md.push('- **Gate:** ' + (n.gate && n.gate.trim() ? '`' + n.gate.trim() + '`' : '⚠ none defined — add one before running'));
    if (n.link_map) md.push('- **Sub-workflow:** drill into map `' + n.link_map + '`');
    const o = out[n.id];
    if (o.length) o.forEach(e => md.push('- **Then:** ' + (e.label ? 'if _' + e.label + '_ → ' : '→ ') + ((byId[e.to] || {}).name || e.to)));
    else md.push('- **End of workflow.**');
    md.push('');
  });
  md.push('---', '', 'Loop spec (validate with `loop_lint.py`):', '', '```loop', spec, '```', '');
  return { spec, markdown: md.join('\n'), issues };
}
// ---- edge ops (slugs, in the map index). d = {from,to,label?,bend?,color?,remove?} ----
function editEdge(mapSlug, d) {
  const { from, to, remove } = d;
  const idx = mapIndex(mapSlug);
  if (!fs.existsSync(idx)) throw new Error('unknown map');
  // self-loops are allowed (feedback / retry steps — common in process & agent-loop maps)
  let it = fs.readFileSync(idx, 'utf8');
  const all = getEdges(it);
  const ex = all.find(e => e.from === from && e.to === to);
  let edges = all.filter(e => !(e.from === from && e.to === to));   // drop any existing same pair
  if (!remove) edges.push({
    from, to,
    label: (d.label !== undefined && d.label !== null) ? d.label : ((ex && ex.label) || ''),  // omitted ⇒ keep on reconnect
    bend: d.bend !== undefined ? d.bend : (ex ? ex.bend : 0) || 0,
    color: d.color !== undefined ? d.color : (ex ? ex.color : null),
    route: d.route !== undefined ? d.route : (ex ? ex.route : 'bezier'),
  });
  fs.writeFileSync(idx, setEdges(it, edges));
}
function addMap(title) {
  const slug = slugify(title);
  if (!slug) throw new Error('title has no usable slug characters');
  const dir = path.join(SRC, slug);
  if (fs.existsSync(dir)) throw new Error('a map named "' + slug + '" already exists');
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'index.md'),
    '---\ntitle: ' + JSON.stringify(title) + '\ntype: map\nnodes: []\n---\n\n# ' + title + '\n');
  const reg = path.join(SRC, 'index.md');
  let r = fs.readFileSync(reg, 'utf8');
  const maps = getList(r, 'maps'); maps.push(slug);
  fs.writeFileSync(reg, setList(r, 'maps', maps));
  return slug;
}

function archiveMap(slug) {
  if (!slug || /[\\/]/.test(slug)) throw new Error('bad slug');
  const dir = path.join(SRC, slug);
  if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) throw new Error('no such map');
  fs.mkdirSync(ARCHIVE, { recursive: true });
  let dest = path.join(ARCHIVE, slug + '__map'), n = 2;
  while (fs.existsSync(dest)) dest = path.join(ARCHIVE, slug + '__map-' + (n++));
  fs.renameSync(dir, dest);
  const reg = path.join(SRC, 'index.md');
  let r = fs.readFileSync(reg, 'utf8');
  fs.writeFileSync(reg, setList(r, 'maps', getList(r, 'maps').filter(s => s !== slug)));
}

function body(req, cb) { let b = ''; req.on('data', c => b += c); req.on('end', () => { try { cb(JSON.parse(b || '{}')); } catch (e) { cb(null); } }); }

// ---- undo: snapshot a map's whole .md file set before each mutation; /api/undo restores the top ----
const undoStack = [];
const umap = d => { const a = d.path && safeSrc(d.path); return d.map || (a ? mapSlugOf(a) : null); };   // null (not throw) on a rejected path
function snapshotMap(mapSlug) {
  if (!mapSlug) return null;
  const dir = path.join(SRC, mapSlug);
  if (!fs.existsSync(dir)) return null;
  const files = {};
  for (const name of fs.readdirSync(dir)) if (name.endsWith('.md')) files[name] = fs.readFileSync(path.join(dir, name), 'utf8');
  return { mapSlug, files };
}
function pushUndo(mapSlug) { const s = snapshotMap(mapSlug); if (s) { undoStack.push(s); if (undoStack.length > 60) undoStack.shift(); } }
function restoreSnap(s) {
  const dir = path.join(SRC, s.mapSlug);
  fs.mkdirSync(dir, { recursive: true });
  const current = new Set(fs.readdirSync(dir).filter(n => n.endsWith('.md')));
  for (const [name, content] of Object.entries(s.files)) { fs.writeFileSync(path.join(dir, name), content); current.delete(name); }
  for (const name of current) fs.unlinkSync(path.join(dir, name));   // remove files created after the snapshot
}

http.createServer((req, res) => {
  const u = new URL(req.url, 'http://x');
  const p = decodeURIComponent(u.pathname);

  if (p === '/api/ping') return json(res, { ok: true });
  if (p === '/api/events') {
    res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', Connection: 'keep-alive' });
    res.write(':\n\n'); sseClients.add(res); req.on('close', () => sseClients.delete(res));
    return;
  }
  if (p === '/api/open') {
    const abs = safeSrc(u.searchParams.get('path'));
    if (!abs || !fs.existsSync(abs)) return json(res, { ok: false, error: 'not found' }, 404);
    execFile('open', [abs], () => {}); return json(res, { ok: true });
  }
  if (p === '/api/doc') {
    const abs = safeSrc(u.searchParams.get('path'));
    if (!abs || !fs.existsSync(abs) || !fs.statSync(abs).isFile()) return json(res, { ok: false, error: 'not found' }, 404);   // isFile guard: readFileSync on a dir throws EISDIR (uncaught → crash)
    const content = fs.readFileSync(abs, 'utf8');
    return json(res, { ok: true, content, title: titleOf(content) });
  }
  if (p === '/api/export') {                     // map → loop spec + agent Markdown, validated by loop_lint.py
    let wf; try { wf = buildWorkflow(u.searchParams.get('map')); } catch (e) { return json(res, { ok: false, error: String(e.message || e) }, 400); }
    const lintPath = path.join(ROOT, 'skills', 'loop-engineering', 'tools', 'loop_lint.py');
    if (!fs.existsSync(lintPath)) return json(res, { ok: true, spec: wf.spec, markdown: wf.markdown, issues: wf.issues, lint: { code: null, output: 'loop_lint.py not found (install Brainer skills)' } });
    const child = execFile('python3', [lintPath, '-'], { cwd: ROOT }, (err, stdout, stderr) => {
      const code = err ? (typeof err.code === 'number' ? err.code : null) : 0;
      json(res, { ok: true, map: u.searchParams.get('map'), spec: wf.spec, markdown: wf.markdown, issues: wf.issues, lint: { code, output: (stdout || '') + (stderr || '') || (err && err.message) || '' } });
    });
    try { child.stdin.write('```loop\n' + wf.spec + '\n```\n'); child.stdin.end(); } catch (_) {}
    return;
  }

  const POST = (route, fn) => { if (p === route && req.method === 'POST') { body(req, d => { if (!d) return json(res, { ok: false, error: 'bad json' }, 400); changedSlug = (d.map || umap(d)) || null; try { fn(d); } catch (e) { changedSlug = null; json(res, { ok: false, error: String(e.message || e) }, 400); } }); return true; } return false; };

  if (POST('/api/save', d => {
    const abs = safeSrc(d.path);
    if (!abs || !fs.existsSync(abs)) return json(res, { ok: false, error: 'not found' }, 404);
    if (typeof d.content !== 'string') return json(res, { ok: false, error: 'no content' }, 400);
    pushUndo(umap(d)); fs.writeFileSync(abs, d.content.replace(/\r\n/g, '\n')); rebuildAndReply(res, { title: titleOf(d.content) });   // normalize CRLF→LF so the build's frontmatter regexes (bare \n) never break
  })) return;
  if (POST('/api/save-body', d => {   // replace ONLY the body, preserving the frontmatter on disk (editor shows the body; nid/type/x/y are managed elsewhere and must not be clobbered)
    const abs = safeSrc(d.path);
    if (!abs || !fs.existsSync(abs)) return json(res, { ok: false, error: 'not found' }, 404);
    if (typeof d.body !== 'string') return json(res, { ok: false, error: 'no body' }, 400);
    const cur = fs.readFileSync(abs, 'utf8'); const m = cur.match(/^---\r?\n[\s\S]*?\r?\n---\r?\n?/);
    let fm = (m ? m[0] : '').replace(/\r\n/g, '\n'); if (fm && !fm.endsWith('\n')) fm += '\n';
    const out = fm + (fm ? '\n' : '') + d.body.replace(/\r\n/g, '\n').replace(/\s+$/, '') + '\n';
    pushUndo(umap(d)); fs.writeFileSync(abs, out); rebuildAndReply(res);
  })) return;
  if (POST('/api/add', d => { pushUndo(d.map); const created = addNode(d.map, d.title, d.type, d.x, d.y, d.note, d.link_map, d); rebuildAndReply(res, { created }); })) return;
  if (POST('/api/add-batch', d => { pushUndo(d.map); const created = (d.nodes || []).map(n => addNode(d.map, n.title, n.type, n.x, n.y, n.note, n.link_map, n)); rebuildAndReply(res, { created }); })) return;   // duplicate/paste N nodes atomically: ONE undo snapshot, ONE rebuild
  if (POST('/api/rename', d => { pushUndo(umap(d)); const np = renameNode(d.path, d.title); rebuildAndReply(res, { path: np }); })) return;
  if (POST('/api/archive', d => { pushUndo(umap(d)); archiveNode(d.path); rebuildAndReply(res); })) return;
  if (POST('/api/pos', d => { pushUndo(umap(d)); setPos(d.path, d.x, d.y); rebuildAndReply(res); })) return;
  if (POST('/api/poslist', d => { pushUndo(d.map); (d.positions || []).forEach(p => setPos(p.path, p.x, p.y)); rebuildAndReply(res); })) return;   // batch move (auto-tidy): one undo, one rebuild
  if (POST('/api/link', d => { pushUndo(umap(d)); setLink(d.path, d.link_map || ''); rebuildAndReply(res); })) return;
  if (POST('/api/type', d => { pushUndo(umap(d)); setType(d.path, d.type); rebuildAndReply(res); })) return;
  if (POST('/api/node-style', d => { pushUndo(umap(d)); setNodeStyle(d.path, d); rebuildAndReply(res); })) return;
  if (POST('/api/edge', d => { pushUndo(d.map); editEdge(d.map, d); rebuildAndReply(res); })) return;
  if (POST('/api/frame', d => { pushUndo(d.map); editFrame(d.map, d.op, d); rebuildAndReply(res); })) return;
  if (POST('/api/link-knowledge', d => { pushUndo(umap(d)); appendRef(d.path, d.ref, d.label); rebuildAndReply(res); })) return;   // cite a SoT node → a ghost auto-appears in its tray
  if (POST('/api/unlink-knowledge', d => { pushUndo(umap(d)); removeRef(d.path, d.ref); rebuildAndReply(res); })) return;
  if (POST('/api/map-kind', d => { pushUndo(d.map); setMapKind(d.map, d.kind); rebuildAndReply(res); })) return;
  if (POST('/api/map-add', d => { const slug = addMap(d.title); rebuildAndReply(res, { slug }); })) return;
  if (POST('/api/map-archive', d => { pushUndo(d.map); archiveMap(d.map); rebuildAndReply(res); })) return;
  if (POST('/api/undo', () => { const s = undoStack.pop(); if (!s) return json(res, { ok: false, error: 'nothing to undo' }, 400); restoreSnap(s); rebuildAndReply(res); })) return;

  // static (maps/ only)
  let f = (p === '/' || p === '') ? '/index.html' : p;
  const file = path.join(DASH, path.normalize(f).replace(/^(\.\.[/\\])+/, ''));
  if (!file.startsWith(DASH)) { res.writeHead(403); return res.end('forbidden'); }
  fs.readFile(file, (err, buf) => {
    if (err) { res.writeHead(404); return res.end('not found'); }
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-store' });   // dev server: never cache, so edits always load fresh
    res.end(buf);
  });
}).listen(PORT, () => {
  try { build(); } catch (e) { console.error('[serve] initial build failed:', e && (e.message || e)); }
  const url = 'http://localhost:' + PORT;
  console.log('maps dashboard on ' + url + '  (Ctrl-C to stop)');
  if (!process.env.NO_OPEN) { try { execFile('open', [url], () => {}); } catch (e) {} }
});

let watchTimer = null;
try {
  fs.watch(SRC, { recursive: true }, () => {
    clearTimeout(watchTimer);
    watchTimer = setTimeout(() => { try { broadcast(build()); } catch (_) {} }, 300);   // external .md edit → in-process rebuild + push
  });
} catch (e) { /* maps-data/ may not exist yet on first boot */ }
