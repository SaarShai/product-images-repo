#!/usr/bin/env python3
"""Remove a PURE-WHITE background from a flat illustration without the ML-matting
halo. Border-connected near-white flood -> transparent; interior whites kept;
erode the fringe ring + feather for clean AA. Deterministic, no model.

--reopen-interior additionally reopens *trapped* background: enclosed near-white
regions that the border flood can't reach (gaps between coral branches, holes in
the composition). A region is reopened only if it is (a) big enough and (b) made
of the same flat PURE white as the background; tinted interior whites (cream/blush
art highlights) lack a pure-white core and are protected."""
import argparse, numpy as np
from PIL import Image, ImageFilter
from collections import deque

def _label_components(mask):
    """4-connected component labels over a boolean mask (no scipy). Returns
    (labels int32 array, count). Same BFS idiom as the border flood; only the
    True pixels are visited, so it is cheap on the sparse interior-white mask."""
    h,w=mask.shape
    labels=np.zeros((h,w),np.int32); cur=0
    ys,xs=np.where(mask)
    for y0,x0 in zip(ys.tolist(),xs.tolist()):
        if labels[y0,x0]: continue
        cur+=1; labels[y0,x0]=cur; dq=deque([(y0,x0)])
        while dq:
            y,x=dq.popleft()
            for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
                ny,nx=y+dy,x+dx
                if 0<=ny<h and 0<=nx<w and mask[ny,nx] and not labels[ny,nx]:
                    labels[ny,nx]=cur; dq.append((ny,nx))
    return labels,cur

def reopen_interior(arr,whiteish,bg,ithresh,isat,min_area_frac,purity):
    """Return (interior_bg mask, stats). interior_bg = trapped-background regions
    that should join the transparent background."""
    h,w,_=arr.shape
    mx=arr.max(2); mn=arr.min(2)
    strict=(mn>=ithresh)&((mx-mn)<=isat)          # unmistakably the flat bg white
    loose=whiteish&~bg                            # near-white but not border-reached
    labels,n=_label_components(loose)
    if n==0: return np.zeros((h,w),bool),[]
    sizes=np.bincount(labels.ravel(),minlength=n+1)
    pure=np.bincount(labels.ravel(),weights=strict.ravel().astype(np.int64),minlength=n+1)
    min_area=max(1,int(round(min_area_frac*h*w)))
    qual=[c for c in range(1,n+1) if sizes[c]>=min_area and pure[c]/sizes[c]>=purity]
    if not qual: return np.zeros((h,w),bool),[]
    interior=np.isin(labels,np.array(qual,dtype=np.int32))
    stats=[(int(sizes[c]),pure[c]/sizes[c]) for c in qual]
    return interior,stats

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--image",required=True); ap.add_argument("--out",required=True)
    ap.add_argument("--thresh",type=int,default=238,help="min RGB to count as background-white")
    ap.add_argument("--sat",type=int,default=18,help="max (max-min) channel spread for white")
    ap.add_argument("--erode",type=int,default=2,help="px to erode fg to kill bright fringe")
    ap.add_argument("--preset",choices=["gi2"],default=None,
                     help="named parameter set; gi2 = thresh=246 erode=0 (gpt-image-2 art: erode>0 at thresh<248 eats pure-white rim highlights)")
    ap.add_argument("--feather",type=float,default=0.8)
    ap.add_argument("--reopen-interior",action="store_true",help="also reopen trapped (enclosed) near-white background regions")
    ap.add_argument("--interior-thresh",type=int,default=250,help="min RGB for a pixel to count as flat PURE background white (reopen seed)")
    ap.add_argument("--interior-sat",type=int,default=8,help="max channel spread for flat PURE white (reopen seed)")
    ap.add_argument("--interior-min-area",type=float,default=0.0001,help="min trapped-region area as a FRACTION of image to reopen (protects tiny glints)")
    ap.add_argument("--interior-purity",type=float,default=0.35,help="min fraction of a trapped region that is flat pure white (protects tinted cream/blush highlights)")
    ap.add_argument("--check",action="store_true")
    a=ap.parse_args()
    if a.preset=="gi2":
        a.thresh=246; a.erode=0
    if a.erode>0 and a.thresh<248:
        print(f"[white_key] WARNING: erode={a.erode} with thresh={a.thresh} (<248) can eat pure-white "
              f"rim/highlight pixels on gpt-image-2 art; consider --preset gi2 (thresh=246 erode=0)")
    im=Image.open(a.image).convert("RGB"); arr=np.asarray(im); h,w,_=arr.shape
    mx=arr.max(2); mn=arr.min(2)
    whiteish=(mn>=a.thresh)&((mx-mn)<=a.sat)           # near-pure-white pixels
    # flood from border over whiteish -> background
    bg=np.zeros((h,w),bool); seen=np.zeros((h,w),bool); dq=deque()
    for x in range(w):
        for y in (0,h-1):
            if whiteish[y,x] and not seen[y,x]: seen[y,x]=True; dq.append((y,x))
    for y in range(h):
        for x in (0,w-1):
            if whiteish[y,x] and not seen[y,x]: seen[y,x]=True; dq.append((y,x))
    while dq:
        y,x=dq.popleft(); bg[y,x]=True
        for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
            ny,nx=y+dy,x+dx
            if 0<=ny<h and 0<=nx<w and not seen[ny,nx] and whiteish[ny,nx]:
                seen[ny,nx]=True; dq.append((ny,nx))
    if a.reopen_interior:
        interior,stats=reopen_interior(arr,whiteish,bg,a.interior_thresh,a.interior_sat,a.interior_min_area,a.interior_purity)
        bg=bg|interior
        print(f"[white_key] reopened {len(stats)} interior region(s), {int(interior.sum())} px")
    fg=~bg
    alpha=Image.fromarray((fg*255).astype("uint8"),"L")
    if a.erode>0:
        alpha=alpha.filter(ImageFilter.MinFilter(a.erode*2+1))   # erode fg -> remove fringe ring
    if a.feather>0:
        alpha=alpha.filter(ImageFilter.GaussianBlur(a.feather))
    out=Image.merge("RGBA",(*im.split(),alpha))
    out.save(a.out)
    al=np.asarray(alpha); print(f"[white_key] {a.out} transparent={100*(al<8).mean():.1f}% fg={100*(al>247).mean():.1f}%")
    if a.check:
        c=Image.new("RGB",out.size,(255,0,255)); c.paste(out,(0,0),out)
        c.save(a.out.replace(".png","_magenta.png"))

if __name__=="__main__": main()
