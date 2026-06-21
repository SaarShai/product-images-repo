#!/usr/bin/env python3
"""Cheap near-duplicate detector to prune candidate sets before the VLM judge.

The pairwise VLM judge is expensive. Before paying for it, collapse obvious
near-duplicates with perceptual hashing (pHash): images that are visually the
same (re-saves, trivial recompressions, minor edits) hash to nearly the same
value, so their Hamming distance is small. Cluster anything within --threshold
and emit one representative per cluster as the deduped list.

Method
------
* Compute a perceptual hash per image (imagehash.phash, DCT-based, robust to
  small pixel changes / resaves).
* Union-find: union any pair whose Hamming distance <= threshold. This makes
  duplicate detection transitive within a cluster.
* The first-listed image in each cluster (by input order) is the keeper.

Deps: imagehash (light, new), PIL.

CLI
---
python3 scripts/dup_prefilter.py --images a.png b.png ... [--threshold 5]
        [--hash phash|ahash|dhash] [--hash-size 8]
Exit code: 0 always (reporting tool); 2 on bad input.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import imagehash
from PIL import Image

HASH_FNS = {
    "phash": imagehash.phash,
    "ahash": imagehash.average_hash,
    "dhash": imagehash.dhash,
}


class UnionFind:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)  # bias root to lower index


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--images", nargs="+", required=True)
    ap.add_argument("--threshold", type=int, default=5,
                    help="max Hamming distance to count as near-duplicate")
    ap.add_argument("--hash", choices=list(HASH_FNS), default="phash")
    # 16 (not the library default 8): an 8x8 DCT pHash is too coarse to tell a
    # local edit (e.g. erased text on an otherwise-identical image) from a true
    # duplicate -- it collapsed L2_ctx vs L2_erased to distance 4. At size 16
    # that pair is distance ~32 while exact copies stay at 0, so identicals
    # still cluster and local edits are kept separate.
    ap.add_argument("--hash-size", type=int, default=16)
    args = ap.parse_args(argv)

    paths = [Path(p) for p in args.images]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        print("ERROR: missing image(s): " + ", ".join(missing), file=sys.stderr)
        return 2

    hfn = HASH_FNS[args.hash]
    hashes = []
    for p in paths:
        with Image.open(p) as im:
            hashes.append(hfn(im.convert("RGB"), hash_size=args.hash_size))

    n = len(paths)
    uf = UnionFind(n)
    pair_dists = []
    for i in range(n):
        for j in range(i + 1, n):
            d = hashes[i] - hashes[j]  # Hamming distance
            pair_dists.append((i, j, d))
            if d <= args.threshold:
                uf.union(i, j)

    # Group indices by cluster root, preserving input order.
    clusters = {}
    for idx in range(n):
        clusters.setdefault(uf.find(idx), []).append(idx)
    ordered = sorted(clusters.values(), key=lambda g: g[0])

    print(f"hash={args.hash} size={args.hash_size} threshold={args.threshold} "
          f"images={n} clusters={len(ordered)}")
    print("--- pairwise Hamming ---")
    for i, j, d in pair_dists:
        mark = "  DUP" if d <= args.threshold else ""
        print(f"  {paths[i].name} <-> {paths[j].name}: {d}{mark}")

    print("--- clusters ---")
    deduped = []
    for ci, group in enumerate(ordered, 1):
        names = [paths[g].name for g in group]
        keeper = paths[group[0]]
        deduped.append(keeper)
        tag = "(near-dupes)" if len(group) > 1 else "(unique)"
        print(f"  cluster {ci} {tag}: {names}  -> keep {keeper.name}")

    print("--- deduped list ---")
    for p in deduped:
        print(f"  {p}")
    print(f"kept {len(deduped)} of {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
