#!/usr/bin/env python3
"""Ingest Marriott r3 results into the central v2 results library."""
import sys, pathlib
sys.path.insert(0, "/Users/za/Documents/product images repo")
from studio.library import add_result, query

ROOT = pathlib.Path("/Users/za/Documents/product images repo")
LIB = ROOT / "studio/library_store"
OUT = ROOT / "tasks/marriott-hospital/outputs"

IOU = {"door_s1":0.986,"door_s2":0.975,"door_s3":0.984,
       "left_s1":0.985,"left_s2":0.984,"left_s3":0.985,
       "right_s1":0.976,"right_s2":0.983,"right_s3":0.985}
WINNERS = {"door":"door_s1","left":"left_s3","right":"right_s3"}
REJECT = {"right_s1"}  # near-empty; vision-gate fail

n = 0
# candidates
for panel in ("door","left","right"):
    for i in (1,2,3):
        key = f"{panel}_s{i}"
        src = OUT / f"r3_{key}.png"
        verdict = ("winner" if WINNERS[panel]==key else
                   "reject-empty" if key in REJECT else "candidate")
        add_result(LIB, src, {
            "task":"marriott-hospital","panel":panel,"round":"r3","kind":"candidate",
            "route":"flux-control-lora-canny+MRCH","control_lora_scale":0.35,"lora_scale":1.05,
            "iou":IOU[key],"signage":"blank","verdict":verdict})
        n += 1
# finished winners
for panel,key in WINNERS.items():
    add_result(LIB, OUT / f"r3_{panel}_final.png", {
        "task":"marriott-hospital","panel":panel,"round":"r3","kind":"final",
        "route":"flux-control-lora-canny+MRCH","finish":"clarity0.5/0.6->dehalo->white_key",
        "from_candidate":key,"iou":IOU[key],"signage":"blank","verdict":"winner"})
    n += 1
# assembled screen
add_result(LIB, OUT / "r3-screen-preview.png", {
    "task":"marriott-hospital","round":"r3","kind":"assembly","panels":"door+left+right",
    "signage":"blank","verdict":"delivered-candidate"})
n += 1

print(f"ingested {n} records", flush=True)
print("winners in library:", [r["meta"]["panel"] for r in query(LIB, task="marriott-hospital", kind="final")], flush=True)
print("rejects:", [r["orig_name"] for r in query(LIB, task="marriott-hospital", verdict="reject-empty")], flush=True)
print("total marriott rows:", len(query(LIB, task="marriott-hospital")), flush=True)
