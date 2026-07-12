#!/usr/bin/env python3
"""Strip faint regular 254/246 NEUTRAL checkerboard -> true alpha.
bg = strictly-neutral & bright (isolates the two exact greys; colored art protected).
Binary mask + connectivity guard + thin AA feather."""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage

def strip(path, out, chroma_max=6, bright_min=242, min_hole=48, feather=1.2):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    mx = a.max(2); mn = a.min(2); chroma = mx - mn
    bg = (chroma <= chroma_max) & (mn >= bright_min)     # the neutral checker greys
    # connectivity: keep border-connected bg + large enclosed neutral gaps; drop tiny interior specks
    lbl, num = ndimage.label(bg)
    if num:
        border_ids = set(np.unique(np.concatenate([lbl[0,:],lbl[-1,:],lbl[:,0],lbl[:,-1]]))) - {0}
        sizes = ndimage.sum(np.ones_like(lbl), lbl, index=np.arange(1,num+1))
        keep = np.zeros_like(bg)
        for i in range(1,num+1):
            if i in border_ids or sizes[i-1] >= min_hole:
                keep[lbl==i] = True
        bg = keep
    alpha = np.where(bg, 0.0, 255.0)
    # thin feather at boundary for clean AA (blur alpha, then keep hard interior)
    from scipy.ndimage import gaussian_filter
    af = gaussian_filter(alpha, feather)
    # only apply feather within 2px of a boundary
    edge = (ndimage.binary_dilation(bg, iterations=2) & ndimage.binary_dilation(~bg, iterations=2))
    alpha = np.where(edge, af, alpha)
    # unmix the AA ring: recover foreground color F = (C - (1-a)*K)/a with K=250 (checker mean)
    al = np.clip(alpha/255.0, 0, 1)[...,None]
    K = 250.0
    ring = edge[...,None] & (al > 0.02) & (al < 0.98)
    F = np.where(ring, np.clip((a - (1-al)*K)/np.maximum(al,0.15), 0, 255), a)
    # POST-CLEAN 1: kill bright-neutral halo in the AA ring (checker AA, not art)
    ch_all = a.max(2)-a.min(2)
    halo = (alpha>2)&(alpha<253)&(ch_all<8)&(a.min(2)>=236)
    alpha[halo]=0.0
    # POST-CLEAN 2: remove tiny isolated opaque specks (leftover checker islands)
    op = alpha>128
    l2,n2 = ndimage.label(op)
    if n2:
        sz = ndimage.sum(np.ones_like(l2), l2, index=np.arange(1,n2+1))
        for i in range(1,n2+1):
            if sz[i-1] < 14:
                alpha[l2==i]=0.0
    out_rgba = np.dstack([F, alpha]).astype(np.uint8)
    Image.fromarray(out_rgba, "RGBA").save(out)
    alv = alpha/255.0
    return dict(transp=round(100*(alv<0.02).mean(),1), semi=round(100*((alv>=0.02)&(alv<=0.98)).mean(),2),
                opaque=round(100*(alv>0.98).mean(),1))

if __name__ == "__main__":
    print(strip(sys.argv[1], sys.argv[2]))
