import subprocess, sys, os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

SRC="<DRIVE_ROOT>/Wanderland Folder/Files/Products/Screenery/production files/cafe/images"
OUT=os.path.join(SRC,"Gelato")
D="tasks/cafe-jars-restyle"
PROMPT=D+"/inputs/style_white.md"
TMP=D+"/inputs/_batch"; Path(TMP).mkdir(parents=True, exist_ok=True)
Path(OUT).mkdir(parents=True, exist_ok=True)
NUMS=[f"{i:03d}" for i in range(1,17)]

def prep(n):
    src=f"{SRC}/print-image-{n}-embedded-capture.png"
    s=Image.open(src).convert("RGBA"); w,h=s.size; r=1280/max(w,h)
    if r<1: s=s.resize((round(w*r),round(h*r)),Image.LANCZOS)
    bg=Image.new("RGB",s.size,(255,255,255)); bg.paste(s,(0,0),s)
    p=f"{TMP}/p{n}.png"; bg.save(p); return p

def run(cmd):
    r=subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout+r.stderr)[-400:]

def proc(n):
    try:
        pin=prep(n)
        white=f"{OUT}/print-image-{n}-gelato-white.png"
        rc,log=run(["python3","scripts/falgen.py","--mode","kontext","--image",pin,
                    "--out",white,"--prompt-file",PROMPT,"--maxside","1280"])
        if rc!=0: return n,"FAIL kontext",log
        trans=f"{OUT}/print-image-{n}-gelato-transparent.png"
        rc,log=run(["python3","scripts/bg_remove.py","--image",white,"--out",trans,"--fal"])
        if rc!=0: return n,"FAIL bgremove",log
        return n,"OK",""
    except Exception as e:
        return n,"EXC",str(e)

res={}
with ThreadPoolExecutor(max_workers=5) as ex:
    futs={ex.submit(proc,n):n for n in NUMS}
    for f in as_completed(futs):
        n,st,log=f.result(); res[n]=st; print(f"[{n}] {st} {log[:120]}",flush=True)
print("\nSUMMARY:", {k:res[k] for k in sorted(res)})
ok=sum(1 for v in res.values() if v=="OK"); print(f"{ok}/{len(NUMS)} OK")
