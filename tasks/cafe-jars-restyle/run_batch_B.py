import subprocess, os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
SRC="/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/cafe/images"
OUT=os.path.join(SRC,"Gelato","B_openai_transparent")
D="tasks/cafe-jars-restyle"; PROMPT=D+"/inputs/style_A.md"; STYLE=D+"/inputs/style_ref.png"
TMP=D+"/inputs/_batchB"; Path(TMP).mkdir(parents=True,exist_ok=True); Path(OUT).mkdir(parents=True,exist_ok=True)
NUMS=[f"{i:03d}" for i in range(1,17)]
def run(c,t=320):
    r=subprocess.run(c,capture_output=True,text=True,timeout=t); return r.returncode,(r.stdout+r.stderr)[-300:]
def prep(n):
    s=Image.open(f"{SRC}/print-image-{n}-embedded-capture.png").convert("RGBA")
    w,h=s.size; r=1280/max(w,h)
    if r<1: s=s.resize((round(w*r),round(h*r)),Image.LANCZOS)
    bg=Image.new("RGB",s.size,(255,255,255)); bg.paste(s,(0,0),s)
    p=f"{TMP}/p{n}.png"; bg.save(p); return p
def proc(n):
    try:
        pin=prep(n); wtmp=f"{TMP}/w{n}.png"
        rc,log=run(["python3","scripts/subgen.py","--provider","openai","-i",pin,STYLE,
                    "--prompt-file",PROMPT,"--out",wtmp])
        if rc!=0 or not os.path.exists(wtmp): return n,"FAIL openai",log
        trans=f"{OUT}/print-image-{n}-gelato-transparent.png"
        rc,log=run(["python3","scripts/bg_remove.py","--image",wtmp,"--out",trans,"--fal"])
        if rc!=0: return n,"FAIL bg",log
        return n,"OK",""
    except Exception as e: return n,"EXC",str(e)[:120]
res={}
with ThreadPoolExecutor(max_workers=4) as ex:
    for f in as_completed({ex.submit(proc,n):n for n in NUMS}):
        n,st,log=f.result(); res[n]=st; print(f"[{n}] {st} {log[:90]}",flush=True)
ok=sum(v=="OK" for v in res.values()); print(f"\n{ok}/{len(NUMS)} OK",{k:v for k,v in res.items() if v!='OK'})
