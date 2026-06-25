import numpy as np, math
from PIL import Image

SRC='tasks/berlin-hotel-base/work/src.png'
OUTDIR='tasks/berlin-hotel-base/work/m3/'

# Geometry
TX0,TX1=3162,4082          # tower footprint x
RY0,RY1=2582,2828          # base region to replace (the only editable band)
P=87.1                     # refined floor period
PHI=84.75                  # bright floor-line at y=PHI+k*P
# Lowest CLEAN full floor donor: from one floor-line up to the next, just above the boundary
DON_TOP=2523.4-P           # ~2436.3 (a floor-line)
DON_BOT=2523.4             # next floor-line (clean, above boundary)

src=Image.open(SRC).convert('RGB')
A=np.asarray(src).astype(np.float32)
H,W,_=A.shape

def sample_row(y):
    # bilinear vertical sample of full-width tower columns at fractional y
    y0=int(math.floor(y)); f=y-y0
    r0=A[y0, TX0:TX1]; r1=A[min(y0+1,H-1), TX0:TX1]
    return r0*(1-f)+r1*f

# Build the donor floor as a stack of rows (height = round(P)) sampled at floor resolution
DH=int(round(P))
donor=np.zeros((DH, TX1-TX0, 3), np.float32)
for i in range(DH):
    donor[i]=sample_row(DON_TOP+i)

# Tile: for each output y in region, map to donor via phase.
# We want a floor-line (donor local row 0 corresponds to DON_TOP, a floor-line) to land at PHI+k*P.
# donor local coordinate for output y: t = (y - PHI) mod P  -> but DON_TOP is itself a floor-line (== PHI+k*P), so phase aligns.
out=A.copy()
rng=np.random.default_rng(42)

# Per-floor variation: assign jitter per floor index k
def floor_index(y): return math.floor((y-PHI)/P)
floors=sorted(set(floor_index(y) for y in range(RY0,RY1+1)))
jitter={}
for k in floors:
    bri=1.0+rng.uniform(-0.018,0.018)      # +-1.8% brightness
    hue=rng.uniform(-3,3)                   # tiny warm/cool shift on R-B
    xoff=rng.uniform(-1.5,1.5)             # tiny horizontal offset px
    jitter[k]=(bri,hue,xoff)

# Perspective foreshortening: facade narrows slightly with height? It's flat near-frontal -> almost none.
# Apply a very subtle vertical compression increasing downward is wrong (frontal). Skip warp; keep flat.

Wt=TX1-TX0
for y in range(RY0,RY1):
    t=((y-PHI)%P)                # 0..P along the floor
    # bilinear in donor stack
    ti=t*(DH/P)
    t0=int(math.floor(ti))%DH; t1=(t0+1)%DH; ff=ti-math.floor(ti)
    row=donor[t0]*(1-ff)+donor[t1]*ff
    k=floor_index(y)
    bri,hue,xoff=jitter[k]
    # horizontal offset via roll with sub-px (simple integer roll + frac blend)
    xi=int(round(xoff))
    row=np.roll(row,xi,axis=0)
    row=row*bri
    row[:,0]+=hue; row[:,2]-=hue
    out[y,TX0:TX1]=row

out=np.clip(out,0,255).astype(np.uint8)
Image.fromarray(out).save(OUTDIR+'_tiled_flat.png')
print('tiled flat saved; floors',floors)
print('donor', DON_TOP, DON_BOT)

# ---- GROUND-FLOOR TREATMENT ----
# Reload flat tiled result and rework the bottom floor into a taller ground floor + plinth.
flat=np.asarray(Image.open(OUTDIR+'_tiled_flat.png').convert('RGB')).astype(np.float32)
out2=flat.copy()
limestone=np.array([236.6,227.7,210.9])

# Last interior floor-line above quay: 2784.7. Quay top = 2828.
GF_TOP=int(round(2784.7))      # 2785 - ground floor begins here
GF_BOT=RY1                     # 2828
PLINTH_H=14                    # solid limestone base band height
gf_h=GF_BOT-GF_TOP             # ground-floor band height (~43)

# Donor: take the upper portion of a clean floor (pier + tall window) from 2436.3..2436.3+ (window zone)
# Build a tall ground-floor window by vertically stretching the window portion of donor floor.
# Window zone within a floor: roughly mid floor. Use donor rows that contain the window (dark band).
win_src_top=2455   # within clean floor 2436-2523, the tall window band
win_src_bot=2510
win=A[win_src_top:win_src_bot, TX0:TX1]   # the tall-window strip
# target: stretch to fill GF_TOP..(GF_BOT-PLINTH_H)
tgt_h=(GF_BOT-PLINTH_H)-GF_TOP
winI=Image.fromarray(np.clip(win,0,255).astype(np.uint8)).resize((TX1-TX0,tgt_h),Image.LANCZOS)
out2[GF_TOP:GF_BOT-PLINTH_H, TX0:TX1]=np.asarray(winI).astype(np.float32)

# Plinth: muted limestone base band, slightly cooler/darker (in shadow at water level),
# with faint top ink line and a subtle downward darkening toward the quay.
plinth_base=limestone*0.93 + np.array([0.,0.,4.])
col_tone=A[2440:2520, TX0:TX1].mean(axis=0).mean(axis=1)
col_tone=0.96+0.04*(col_tone-col_tone.mean())/(col_tone.std()+1e-6)
col_tone=np.clip(col_tone,0.93,1.03)
for j in range(PLINTH_H):
    yy=GF_BOT-PLINTH_H+j
    shade=1.0-0.07*(j/PLINTH_H)            # darken toward quay (settling into shadow)
    row=(plinth_base*shade)[None,:]*col_tone[:,None]
    row=row+rng.normal(0,1.2,row.shape)    # tiny grain
    out2[yy,TX0:TX1]=np.clip(row,0,255)
# faint top edge ink line + soft cast shadow under ground-floor windows
out2[GF_BOT-PLINTH_H, TX0:TX1]*=0.82
out2[GF_BOT-PLINTH_H+1, TX0:TX1]*=0.90

# Re-carry pier verticals through the ground floor so piers stay continuous:
# Build a pier mask from the clean facade (bright columns) and overlay piers darker-edged.
clean=A[2440:2520, TX0:TX1]; cb=clean.mean(axis=0).mean(axis=1)
pier_bright=cb>np.percentile(cb,60)   # columns that are bright (piers/limestone)
# slim ink edges at pier transitions
edge=np.zeros(TX1-TX0,bool)
for x in range(1,len(pier_bright)):
    if pier_bright[x]!=pier_bright[x-1]: edge[x]=True
for x in np.where(edge)[0]:
    out2[GF_TOP:GF_BOT-PLINTH_H, TX0+x]*=0.8

out2=np.clip(out2,0,255).astype(np.uint8)
Image.fromarray(out2).save(OUTDIR+'_tiled_gf.png')
print('ground floor done GF_TOP',GF_TOP,'tgt_h',tgt_h)
