import subprocess, os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
SRC="/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/cafe/images"
OUT=os.path.join(SRC,"Gelato")
NUMS=[f"{i:03d}" for i in range(1,17)]
def run(cmd):
    r=subprocess.run(cmd,capture_output=True,text=True); return r.returncode,(r.stdout+r.stderr)[-300:]
def proc(n):
    white=f"{OUT}/print-image-{n}-gelato-white.png"
    rc,log=run(["python3","scripts/_fal_upscale.py","crisp",white,white])  # overwrite white w/ hi-res
    if rc!=0: return n,"FAIL crisp",log
    trans=f"{OUT}/print-image-{n}-gelato-transparent.png"
    rc,log=run(["python3","scripts/bg_remove.py","--image",white,"--out",trans,"--fal"])
    if rc!=0: return n,"FAIL bg",log
    return n,"OK",""
res={}
with ThreadPoolExecutor(max_workers=4) as ex:
    for f in as_completed({ex.submit(proc,n):n for n in NUMS}):
        n,st,log=f.result(); res[n]=st; print(f"[{n}] {st} {log[:100]}",flush=True)
ok=sum(v=="OK" for v in res.values()); print(f"\n{ok}/{len(NUMS)} OK", {k:res[k] for k in sorted(res) if res[k]!='OK'})
