export const meta = {
  name: 'princess-restyle-fanout',
  description: 'Restyle narrow02 to the watercolor refs (exact layout, fix faces/fingers/toes), fan out + judge + hi-res',
  phases: [
    { title: 'Generate', detail: 'guide-fade x style-order matrix via subgen openai' },
    { title: 'Judge', detail: 'Claude + GLM score style-match / composition / anatomy' },
    { title: 'HiRes', detail: 'top-2 regenerated at the 1.8x structure guide' },
  ],
}

const ROOT = '/Users/za/Documents/product images repo'
const SRC = `${ROOT}/tasks/princess-restyle/src`
const SUB = `${ROOT}/tasks/princess-restyle/sub`
const PROMPT = `${ROOT}/tasks/princess-restyle/prompt-restyle-v2.md`
const STYLE1 = `${SRC}/style01.png`, STYLE2 = `${SRC}/style02.png`
const TARGET = `${SRC}/narrow02-target.png`

// guide fade level x style-ref order matrix
const GUIDES = [
  { g: `${SRC}/sg-015.png`, tag: 'sg015' },
  { g: `${SRC}/structure-guide.png`, tag: 'sg030' },
  { g: `${SRC}/sg-045.png`, tag: 'sg045' },
]
const ORDERS = [
  { refs: `${STYLE1} ${STYLE2}`, tag: 'o12' },
  { refs: `${STYLE2} ${STYLE1}`, tag: 'o21' },
]
const MATRIX = []
for (const gd of GUIDES) for (const o of ORDERS) MATRIX.push({ name: `WF-${gd.tag}-${o.tag}`, guide: gd.g, refs: o.refs })

const GEN_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    name: { type: 'string' }, path: { type: 'string' },
    width: { type: 'integer' }, height: { type: 'integer' }, ok: { type: 'boolean' },
  }, required: ['name', 'path', 'ok'],
}
const JUDGE_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    style_match: { type: 'integer', description: '0-5: matches the loose airy watercolor of the style refs (NOT dense/saturated)' },
    composition_fidelity: { type: 'integer', description: '0-5: same castle layout/silhouette/door/fairy positions as the target' },
    anatomy: { type: 'integer', description: '0-5: faces/fingers/toes clean & well-formed (5=perfect, 0=melted)' },
    defects: { type: 'array', items: { type: 'string' } },
    verdict: { type: 'string' },
  }, required: ['style_match', 'composition_fidelity', 'anatomy', 'defects', 'verdict'],
}

function genCmd(guide, refs, out) {
  return `cd ${JSON.stringify(ROOT)} && python3 scripts/subgen.py --provider openai --prompt-file ${JSON.stringify(PROMPT)} --out ${JSON.stringify(out)} -i ${guide} ${refs} 2>&1 | tail -1 && python3 -c "from PIL import Image;im=Image.open('${out}');print('DIMS',im.size)"`
}

phase('Generate')
const gens = await parallel(MATRIX.map(m => () =>
  agent(
    `Run EXACTLY this bash command (it generates one image via the subscription path). Wait for it to finish.\n\n` +
    genCmd(m.guide, m.refs, `${SUB}/${m.name}.png`) +
    `\n\nThen verify the file ${SUB}/${m.name}.png exists and is a valid PNG >100KB. Return name="${m.name}", path, width, height (from the DIMS line), ok=true only if the file is a valid image.`,
    { label: `gen:${m.name}`, phase: 'Generate', schema: GEN_SCHEMA }
  )
))
const good = gens.filter(Boolean).filter(g => g.ok)
log(`generated ${good.length}/${MATRIX.length} candidates`)

// also judge the candidates I already made inline (don't waste them)
const PRE = [
  { name: 'n02-v2a', path: `${SUB}/n02-v2a.png` },
  { name: 'n02-v2b', path: `${SUB}/n02-v2b.png` },
  { name: 'n02-restyle-s2', path: `${SUB}/n02-restyle-s2.png` },
]
const ALL = [...good.map(g => ({ name: g.name, path: g.path })), ...PRE]

phase('Judge')
const judgeOne = (c, model, who) =>
  agent(
    `You are judging a RESTYLE candidate for a die-cut castle panel.\n` +
    `Candidate: ${c.path}\nStyle reference 1: ${STYLE1}\nStyle reference 2: ${STYLE2}\nOriginal target (layout source, WRONG style): ${TARGET}\n\n` +
    `View ALL four. Score the candidate ONLY:\n` +
    `- style_match (0-5): does it match the LOOSE, SOFT, AIRY watercolor + pastel palette + white space of the style refs? (dense/saturated/decoupage = low)\n` +
    `- composition_fidelity (0-5): same castle silhouette, tower layout, lower-left arched door, fairy positions, flower beds as the target?\n` +
    `- anatomy (0-5): zoom into every fairy — are FACES, FINGERS (exactly 5, distinct), and TOES clean and well-formed? melted/merged/extra = low. List each defect you see in defects[].\n` +
    `Return the structured verdict.`,
    { label: `judge:${who}:${c.name}`, phase: 'Judge', schema: JUDGE_SCHEMA, agentType: model }
  ).then(v => v && ({ ...v, name: c.name, path: c.path, judge: who })).catch(() => null)

const judged = await parallel(ALL.flatMap(c => [
  () => judgeOne(c, undefined, 'claude'),
  () => judgeOne(c, 'glm-executor', 'glm'),
]))
const verds = judged.filter(Boolean)

// aggregate per candidate: median-ish (avg) across judges; combined = style*2 + anatomy*2 + composition
const byName = {}
for (const v of verds) (byName[v.name] ||= { name: v.name, path: v.path, rows: [] }).rows.push(v)
const scored = Object.values(byName).map(c => {
  const avg = k => c.rows.reduce((s, r) => s + (r[k] || 0), 0) / c.rows.length
  const sm = avg('style_match'), cf = avg('composition_fidelity'), an = avg('anatomy')
  return { name: c.name, path: c.path, style_match: +sm.toFixed(2), composition: +cf.toFixed(2), anatomy: +an.toFixed(2), combined: +(sm * 2 + an * 2 + cf).toFixed(2), defects: c.rows.flatMap(r => r.defects || []) }
}).sort((a, b) => b.combined - a.combined)
log(`scored ${scored.length}; leader ${scored[0]?.name} combined=${scored[0]?.combined}`)

phase('HiRes')
// gpt-image caps native ~896x1792 (proven: feeding a 1.8x guide still output 874x1799),
// so high-res = UPSCALE the winners (cv2 Lanczos + unsharp), not regen.
const top2 = scored.slice(0, 2)
const hires = await parallel(top2.map((c) => () =>
  agent(
    `Upscale the winning restyle to high resolution. Run EXACTLY this bash command and wait:\n\n` +
    `cd ${JSON.stringify(ROOT)} && python3 scripts/upscale.py ${JSON.stringify(c.path)} ${JSON.stringify(`${SUB}/HIRES-${c.name}.png`)} --factor 2.5 && python3 -c "from PIL import Image;im=Image.open('${SUB}/HIRES-${c.name}.png');print('DIMS',im.size)"\n\n` +
    `Verify ${SUB}/HIRES-${c.name}.png is a valid PNG and report path + dimensions (ok=true only if valid).`,
    { label: `hires:${c.name}`, phase: 'HiRes', schema: GEN_SCHEMA }
  )
))

return {
  ranking: scored,
  top2: top2.map(c => c.name),
  hires: hires.filter(Boolean),
  note: 'style_match + anatomy weighted x2; composition x1. HiRes = cv2 2.5x upscale (gpt-image native cap ~896x1792).',
}
