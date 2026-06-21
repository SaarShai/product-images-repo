#!/usr/bin/env python3
"""sweep.py — pick the best of N candidate edits: dedup (perceptual hash) -> pairwise
tournament via the VLM judge. Operationalizes the standing rule "maximize fan-out, gate
objectively". Pair with falbatch.py to GENERATE the candidates in parallel first.

Usage:
  python3 scripts/sweep.py --candidates a.png b.png c.png --criterion "cleanest, best-formed yellow taxi in watercolor+ink style, no text"
Prints the ranking and the winner path; exit 0.
"""
import argparse, json, subprocess, sys
from pathlib import Path

R = Path(__file__).resolve().parent
PY = sys.executable


def dedup(paths, hash_size=16, thresh=5):
    try:
        import imagehash
        from PIL import Image
    except Exception:
        return paths, []  # no imagehash -> skip dedup
    kept, hashes, dropped = [], [], []
    for p in paths:
        h = imagehash.phash(Image.open(p).convert("RGB"), hash_size=hash_size)
        dup_of = next((k for k, hh in zip(kept, hashes) if (h - hh) <= thresh), None)
        if dup_of:
            dropped.append((p, dup_of))
        else:
            kept.append(p); hashes.append(h)
    return kept, dropped


def pairwise(a, b, criterion):
    r = subprocess.run([str(PY), str(R/"judge.py"), "--mode", "pairwise", "--image", a,
                        "--ref", b, "--criterion", criterion], capture_output=True, text=True)
    try:
        out = json.loads(r.stdout)
        return out.get("winner"), out.get("consistent")
    except Exception:
        return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", nargs="+", required=True)
    ap.add_argument("--criterion", default="overall quality and watercolor style match, no text/defects")
    ap.add_argument("--hash-thresh", type=int, default=5)
    a = ap.parse_args()

    kept, dropped = dedup(a.candidates, thresh=a.hash_thresh)
    for p, k in dropped:
        print(f"  dedup: drop {Path(p).name} (near-dup of {Path(k).name})")
    if len(kept) == 1:
        print(f"\n[sweep] only 1 unique candidate -> WINNER {kept[0]}"); return

    champ = kept[0]; log = []
    for chal in kept[1:]:
        w, cons = pairwise(champ, chal, a.criterion)
        winner = champ if w == "A" else (chal if w == "B" else champ)
        log.append(f"{Path(champ).name} vs {Path(chal).name} -> {Path(winner).name}"
                   f"{'' if cons else ' (inconsistent)'}")
        champ = winner
    print("\n[sweep] tournament:")
    for l in log:
        print("  " + l)
    print(f"\n[sweep] WINNER: {champ}")


if __name__ == "__main__":
    main()
