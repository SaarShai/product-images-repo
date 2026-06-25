import sys, base64, requests, io
from pathlib import Path
from PIL import Image
sys.path.insert(0, "scripts")
from falgen import load_key
def uri(p):
    im=Image.open(p).convert("RGB"); w,h=im.size; r=1280/max(w,h)
    if r<1: im=im.resize((round(w*r),round(h*r)),Image.LANCZOS)
    b=io.BytesIO(); im.save(b,"PNG"); return "data:image/png;base64,"+base64.b64encode(b.getvalue()).decode()
out=sys.argv[1]; prompt=Path(sys.argv[2]).read_text(); imgs=sys.argv[3:]
body={"prompt":prompt,"image_urls":[uri(p) for p in imgs],"output_format":"png","num_images":1,
      "enable_safety_checker":False,"safety_tolerance":"5"}
k=load_key()
r=requests.post("https://fal.run/fal-ai/flux-2-pro/edit",headers={"Authorization":f"Key {k}","Content-Type":"application/json"},json=body,timeout=300)
if r.status_code!=200: print("ERR",r.status_code,r.text[:400]); sys.exit(1)
j=r.json(); u=j["images"][0]["url"]
Path(out).write_bytes(requests.get(u,timeout=120).content); print("OK ->",out,"seed",j.get("seed"))
