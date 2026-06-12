#!/usr/bin/env python3
"""Compare two variant artifacts for reproducibility: identical injected
results (racer/round/run -> time), regardless of tenant or wall-clock.
Usage: compare_runs.py A/artifact.json B/artifact.json"""
import json
import sys

def keyed(path):
    a = json.load(open(path))
    return {(e["classid"], e["racerid"], e["round_seq"], e["run_idx"]): e["time"]
            for e in a["run_log"]}, a

ka, aa = keyed(sys.argv[1])
kb, ab = keyed(sys.argv[2])
if ka == kb:
    print(f"IDENTICAL: {len(ka)} injected results match exactly "
          f"(seeds {aa['seed']}/{ab['seed']}, tenants {aa['tenant']}/{ab['tenant']})")
    sys.exit(0)
only_a = set(ka) - set(kb)
only_b = set(kb) - set(ka)
diff = {k for k in set(ka) & set(kb) if ka[k] != kb[k]}
print(f"MISMATCH: only_a={len(only_a)} only_b={len(only_b)} differing={len(diff)}")
for k in sorted(diff)[:10]:
    print(f"  {k}: {ka[k]} vs {kb[k]}")
sys.exit(1)
