#!/usr/bin/env python3
"""Remove a PURE-WHITE background from a flat illustration without the ML-matting
halo. Border-connected near-white flood -> transparent; interior whites kept;
erode the fringe ring + feather for clean AA. Deterministic, no model."""
import argparse, numpy as np
from PIL import Image, ImageFilter
from collections import deque

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--image",required=True); ap.add_argument("--out",required=True)
    ap.add_argument("--thresh",type=int,default=238,help="min RGB to count as background-white")
    ap.add_argument("--sat",type=int,default=18,help="max (max-min) channel spread for white")
    ap.add_argument("--erode",type=int,default=2,help="px to erode fg to kill bright fringe")
    ap.add_argument("--feather",type=float,default=0.8)
    ap.add_argument("--check",action="store_true")
    a=ap.parse_args()
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
