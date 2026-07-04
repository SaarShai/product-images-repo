import subprocess, os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
SRC="<DRIVE_ROOT>/Wanderland Folder/Files/Products/Screenery/production files/cafe/images"
OUT=os.path.join(SRC,"Gelato")
D="tasks/cafe-jars-restyle"; PROMPT=D+"/inputs/style_A.md"
TMP=D+"/inputs/_batchA"; Path(TMP).mkdir(parents=True,exist_ok=True)
NUMS=[f"{i:03d}" for i in range(1,17)]
def run(c):
    r=subprocess.run(c,capture_output=True,text=True); return r.returncode,(r.stdout+r.stderr)[-300:]
def prep(n):
    s=Image.open(f"{SRC}/print-image-{n}-embedded-capture.png").convert("RGBA")
    w,h=s.size; r=1280/max(w,h)
    if r<1: s=s.resize((round(w*r),round(h*r)),Image.LANCZOS)
    bg=Image.new("RGB",s.size,(255,255,255)); bg.paste(s,(0,0),s)
    p=f"{TMP}/p{n}.png"; bg.save(p); return p
def proc(n):
    try:
        pin=prep(n)
        wtmp=f"{TMP}/w{n}.png"  # white render kept in TMP, not Gelato
        rc,log=run(["python3","scripts/falgen.py","--mode","kontext","--image",pin,
                    "--out",wtmp,"--prompt-file",PROMPT,"--maxside","1280"])
        if rc!=0: return n,"FAIL kontext",log
        trans=f"{OUT}/print-image-{n}-gelato-transparent.png"
        rc,log=run(["python3","scripts/bg_remove.py","--image",wtmp,"--out",trans,"--fal"])
        if rc!=0: return n,"FAIL bg",log
        return n,"OK",""
    except Exception as e: return n,"EXC",str(e)
res={}
with ThreadPoolExecutor(max_workers=5) as ex:
    for f in as_completed({ex.submit(proc,n):n for n in NUMS}):
        n,st,log=f.result(); res[n]=st; print(f"[{n}] {st} {log[:100]}",flush=True)
ok=sum(v=="OK" for v in res.values()); print(f"\n{ok}/{len(NUMS)} OK",{k:v for k,v in res.items() if v!='OK'})
