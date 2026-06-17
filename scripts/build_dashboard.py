#!/usr/bin/env python3
"""build_dashboard.py — render the results library as a browsable HTML dashboard.

Reads RESULTS/results.jsonl and writes RESULTS/dashboard.html: a filterable,
sortable card grid (thumbnail + geometry overlay on hover + region-IoU + vision-judge
geometry/style/overall scores + verdict + method). Open the HTML in a browser.
Re-run any time to refresh (idempotent). Image paths are made relative to the html.
"""
from __future__ import annotations
import json, os, html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT / "tasks" / "space-np01-front-bottom-02"
RESULTS = TASK / "RESULTS"
JSONL = RESULTS / "results.jsonl"
OUT = RESULTS / "dashboard.html"


def relurl(p: str | None) -> str:
    if not p or p in ("unknown", "n/a"):
        return ""
    ap = Path(p)
    if not ap.is_absolute():
        ap = ROOT / ap
    try:
        return os.path.relpath(ap, RESULTS)
    except Exception:
        return str(ap)


def overlay_for(img_repo_rel: str) -> str:
    if not img_repo_rel or img_repo_rel in ("unknown", "n/a"):
        return ""
    d = (ROOT / img_repo_rel).parent
    ov = d / "region_overlay.png"
    return relurl(str(ov)) if ov.exists() else ""


def num(v):
    return v if isinstance(v, (int, float)) else None


def main() -> int:
    rows = [json.loads(l) for l in JSONL.read_text().splitlines() if l.strip()]
    cards = []
    methods = set()
    for r in rows:
        img = relurl(r.get("image_path_raw")) or relurl(r.get("image_path_exact"))
        ov = overlay_for(r.get("image_path_raw") or r.get("image_path_exact") or "")
        method = r.get("method", "unknown"); methods.add(method)
        riou = num(r.get("region_iou"))
        jg, js, jo = r.get("judge_geometry"), r.get("judge_style"), r.get("judge_overall")
        verdict = r.get("verdict", "?")
        jverdict = r.get("judge_verdict", "")
        cards.append({
            "id": r.get("id", "?"), "method": method, "model": r.get("model", "?"),
            "img": img, "ov": ov,
            "riou": riou if riou is not None else -1,
            "riou_s": f"{riou:.3f}" if riou is not None else str(r.get("region_iou", "—")),
            "jg": jg if isinstance(jg, (int, float)) else "—",
            "js": js if isinstance(js, (int, float)) else "—",
            "jo": jo if isinstance(jo, (int, float)) else "—",
            "verdict": verdict, "jverdict": jverdict,
            "notes": (r.get("notes") or "")[:240],
            "judge_summary": (r.get("judge_summary") or "")[:240],
            "ts": r.get("timestamp", ""),
        })
    cards.sort(key=lambda c: c["riou"], reverse=True)

    npass = sum(1 for c in cards if c["verdict"] == "PASS")
    nwithimg = sum(1 for c in cards if c["img"])
    judged = sum(1 for c in cards if c["jo"] != "—")
    data = json.dumps(cards)
    method_chips = "".join(f'<button class="chip" data-m="{html.escape(m)}">{html.escape(m)}</button>' for m in sorted(methods))

    doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>Results dashboard — space-np01-front-bottom-02</title>
<style>
 body{{font:13px -apple-system,Helvetica,Arial,sans-serif;background:#14161a;color:#e6e6e6;margin:0;padding:16px}}
 h1{{font-size:17px;margin:0 0 4px}} .sub{{color:#9aa;margin-bottom:12px}}
 .bar{{position:sticky;top:0;background:#14161a;padding:8px 0;z-index:5;border-bottom:1px solid #2a2e35}}
 .chip,select,input{{background:#222730;color:#ddd;border:1px solid #39404a;border-radius:6px;padding:5px 9px;margin:2px;cursor:pointer;font-size:12px}}
 .chip.on{{background:#3a6df0;border-color:#3a6df0;color:#fff}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;margin-top:12px}}
 .card{{background:#1c2026;border:1px solid #2a2e35;border-radius:8px;overflow:hidden;display:flex;flex-direction:column}}
 .imw{{position:relative;background:#0d0f12;aspect-ratio:1/2.2;display:flex;align-items:center;justify-content:center;overflow:hidden}}
 .imw img{{max-width:100%;max-height:100%;object-fit:contain}}
 .imw .ov{{position:absolute;inset:0;opacity:0;transition:.15s}} .imw:hover .ov{{opacity:1}}
 .meta{{padding:7px 8px;font-size:11px}} .id{{font-weight:600;font-size:12px;word-break:break-all}}
 .badges{{display:flex;flex-wrap:wrap;gap:4px;margin:5px 0}}
 .b{{padding:1px 6px;border-radius:4px;background:#2a2e35}} .b.geo{{background:#1f3a52}} .b.sty{{background:#3a2a52}} .b.ov{{background:#143a26}}
 .PASS{{color:#5fd07a}} .FAIL{{color:#e06a6a}} .unknown{{color:#9aa}}
 .note{{color:#9aa;font-size:10.5px;margin-top:4px;line-height:1.35}}
 .hint{{color:#778}}
</style></head><body>
<h1>Results library — space-np01-front-bottom-02</h1>
<div class="sub">{len(cards)} records · {nwithimg} with image · {judged} vision-judged · {npass} gate-PASS (region-IoU≥0.85). Hover a card to see the geometry overlay (green=opening hit, red=miss).</div>
<div class="bar">
 sort <select id="sort"><option value="riou">region-IoU</option><option value="jo">judge overall</option><option value="js">judge style</option><option value="jg">judge geometry</option></select>
 <input id="q" placeholder="search id / method / notes" size="22">
 <button class="chip on" data-m="__all">all</button>{method_chips}
</div>
<div class="grid" id="grid"></div>
<script>
const DATA={data};
let activeM="__all", q="", sortK="riou";
const grid=document.getElementById('grid');
function badge(label,val,cls){{return `<span class="b ${{cls}}">${{label}} ${{val}}</span>`}}
function render(){{
 let rows=DATA.filter(c=>(activeM==="__all"||c.method===activeM));
 if(q){{const t=q.toLowerCase();rows=rows.filter(c=>(c.id+c.method+c.notes+c.judge_summary).toLowerCase().includes(t));}}
 rows.sort((a,b)=>{{const av=a[sortK]===("—")?-1:a[sortK],bv=b[sortK]===("—")?-1:b[sortK];return bv-av}});
 grid.innerHTML=rows.map(c=>`<div class="card">
   <div class="imw">${{c.img?`<img loading=lazy src="${{c.img}}">`:'<span class=hint>no image</span>'}}${{c.ov?`<img class=ov loading=lazy src="${{c.ov}}">`:''}}</div>
   <div class="meta"><div class="id">${{c.id}}</div>
   <div class="hint">${{c.method}} · ${{c.model}}</div>
   <div class="badges"><span class="b">rIoU ${{c.riou_s}}</span>${{badge('G',c.jg,'geo')}}${{badge('S',c.js,'sty')}}${{badge('O',c.jo,'ov')}}<span class="b ${{c.verdict}}">${{c.verdict}}</span>${{c.jverdict&&c.jverdict!=='unjudged'?`<span class="b">${{c.jverdict}}</span>`:''}}</div>
   <div class="note">${{(c.judge_summary&&c.judge_summary!=='unjudged')?c.judge_summary:c.notes}}</div>
   </div></div>`).join('');
}}
document.getElementById('sort').onchange=e=>{{sortK=e.target.value;render()}};
document.getElementById('q').oninput=e=>{{q=e.target.value;render()}};
document.querySelectorAll('.chip').forEach(b=>b.onclick=()=>{{document.querySelectorAll('.chip').forEach(x=>x.classList.remove('on'));b.classList.add('on');activeM=b.dataset.m;render()}});
render();
</script></body></html>"""
    OUT.write_text(doc)
    print(f"wrote {OUT.relative_to(ROOT)} — {len(cards)} cards, {nwithimg} with images, {judged} judged, {npass} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
