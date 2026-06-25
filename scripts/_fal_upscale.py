import sys, base64, io, requests
from pathlib import Path
from PIL import Image
sys.path.insert(0,"scripts"); from falgen import load_key
mode, inp, out = sys.argv[1], sys.argv[2], sys.argv[3]
im=Image.open(inp).convert("RGB")
b=io.BytesIO(); im.save(b,"PNG"); uri="data:image/png;base64,"+base64.b64encode(b.getvalue()).decode()
EP={"crisp":"fal-ai/recraft/upscale/crisp","vectorize":"fal-ai/recraft/vectorize"}
body={"image_url":uri}
k=load_key()
r=requests.post(f"https://fal.run/{EP[mode]}",headers={"Authorization":f"Key {k}","Content-Type":"application/json"},json=body,timeout=300)
if r.status_code!=200: print("ERR",r.status_code,r.text[:500]); sys.exit(1)
j=r.json()
img=j.get("image") or (j.get("images") or [None])[0]
u=img["url"] if isinstance(img,dict) else img
data=requests.get(u,timeout=180).content
Path(out).write_bytes(data); print(f"OK {mode} -> {out} ({len(data)} bytes)")
