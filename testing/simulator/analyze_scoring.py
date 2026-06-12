#!/usr/bin/env python3
"""Aggregate std-vs-dropslowest impact across a campaign.

For every seed present under both configs, compares the oracle-expected
progression and reports:
  * prelim advancers changed (count + % of cut) per class
  * how often the FINALS FIELD differs (any SF->finals diff)
  * how often the podium (top 3 of finals) differs
  * DNF involvement: of racers who advance only under drop_slowest, how many
    carried a DNF in that round (the forgiveness effect) vs none (the
    consistency-vs-peak effect)

Usage: analyze_scoring.py <campaign_dir>
"""

import glob
import json
import os
import sys
from collections import defaultdict

DNF = 99.999 - 0.0005


def main(campaign_dir):
    arts = {}
    for path in glob.glob(os.path.join(campaign_dir, "v*", "artifact.json")):
        a = json.load(open(path))
        if a.get("expected"):
            arts[(a["seed"], a["config"])] = a

    seeds = sorted({s for s, c in arts if (s, "std") in arts
                    and (s, "dropslowest") in arts})
    print(f"paired seeds: {len(seeds)}")

    prelim_changed = defaultdict(list)   # classid -> [n changed]
    cut_size = {}
    finals_field_diff = 0
    podium_diff = 0
    podium_total = 0
    forgiveness = 0   # drop-only advancers who carried a DNF that round
    peak_effect = 0   # drop-only advancers with no DNF at all

    for seed in seeds:
        std, drop = arts[(seed, "std")], arts[(seed, "dropslowest")]
        finals_differs = False
        podium_differs = False
        for cid in std["expected"]:
            srounds = std["expected"][cid]["rounds"]
            drounds = drop["expected"].get(cid, {}).get("rounds", {})
            # prelim = round 1
            s1 = set(srounds.get("1", {}).get("advancing", []))
            d1 = set(drounds.get("1", {}).get("advancing", []))
            if s1 and d1:
                prelim_changed[cid].append(len(s1 ^ d1) // 2)
                cut_size[cid] = len(s1)
                # DNF involvement for drop-only advancers
                dnf_racers = {e["racerid"] for e in drop["run_log"]
                              if str(e["classid"]) == cid
                              and e["round_seq"] == 1 and e["time"] >= DNF}
                for rid in d1 - s1:
                    if rid in dnf_racers:
                        forgiveness += 1
                    else:
                        peak_effect += 1
            # finals field = advancing out of the second-to-last round
            seqs = sorted(srounds, key=int)
            if len(seqs) >= 2:
                pre_final = seqs[-2]
                sf = set(srounds.get(pre_final, {}).get("advancing", []))
                df = set(drounds.get(pre_final, {}).get("advancing", []))
                if sf and df and sf != df:
                    finals_differs = True
            spod = [r["racerid"] for r in
                    std["expected"][cid].get("final_results", [])[:3]]
            dpod = [r["racerid"] for r in
                    drop["expected"].get(cid, {}).get("final_results", [])[:3]]
            if spod and dpod:
                podium_total += 1
                if spod != dpod:
                    podium_differs = True
        if finals_differs:
            finals_field_diff += 1
        if podium_differs:
            podium_diff += 1

    print("\nprelim advancers changed (per class, mean over seeds):")
    for cid in sorted(prelim_changed):
        vals = prelim_changed[cid]
        mean = sum(vals) / len(vals)
        print(f"  class {cid}: mean {mean:.1f} of {cut_size[cid]} advancing "
              f"({100*mean/cut_size[cid]:.0f}%), max {max(vals)}")
    print(f"\nseeds where the FINALS FIELD differs: {finals_field_diff}/{len(seeds)}")
    print(f"seeds where a PODIUM differs:          {podium_diff}/{len(seeds)}")
    print(f"\ndrop-only advancers carrying a DNF (forgiveness): {forgiveness}")
    print(f"drop-only advancers with no DNF (peak-vs-consistency): {peak_effect}")


if __name__ == "__main__":
    main(sys.argv[1])
