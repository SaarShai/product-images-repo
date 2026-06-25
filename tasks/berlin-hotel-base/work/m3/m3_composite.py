import numpy as np
from PIL import Image
SRC='tasks/berlin-hotel-base/work/src.png'
TILED='tasks/berlin-hotel-base/work/m3/_tiled_gf.png'
TX0,TX1=3162,4082
RY0,RY1=2582,2828
FEATH=6  # feather only INSIDE the region's top edge to avoid a hard line; keep outside byte-exact

src=np.asarray(Image.open(SRC).convert('RGB')).astype(np.float32)
til=np.asarray(Image.open(TILED).convert('RGB')).astype(np.float32)
out=src.copy()
# region-only paste
out[RY0:RY1, TX0:TX1]=til[RY0:RY1, TX0:TX1]
# feather the TOP boundary blend within the first FEATH rows of the region (still inside region -> outside stays byte-exact)
for i in range(FEATH):
    a=(i+1)/(FEATH+1)
    y=RY0+i
    out[y,TX0:TX1]=src[y,TX0:TX1]*(1-a)+til[y,TX0:TX1]*a
out=np.clip(out,0,255).astype(np.uint8)
Image.fromarray(out).save('tasks/berlin-hotel-base/work/m3/m3_composited.png')

# verify outside-region delta == 0
o=out.astype(np.int32); s=src.astype(np.int32)
mask=np.zeros(o.shape[:2],bool); mask[RY0:RY1,TX0:TX1]=True
outside=np.abs(o-s).sum(axis=2); outside[mask]=0
print('OUTSIDE max abs delta:',int(outside.max()),' nonzero px:',int((outside>0).sum()))
# zoom
Image.fromarray(out).crop((3060,2480,4120,2900)).save('tasks/berlin-hotel-base/work/m3/m3_zoom.png')
print('composited + zoom saved')
