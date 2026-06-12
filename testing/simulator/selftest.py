#!/usr/bin/env python3
"""Offline self-test for the simulator's planner and oracle.

No server, broker, or DB required — run anywhere:
    python3 testing/simulator/selftest.py

Ladder:
  1. Oracle vs the HAND-COMPUTED micro6 fixture (both scoring methods,
     tie-at-cutoff, DNF handling, withdrawn exclusion, finals placement).
  2. Planner determinism: same seed twice -> identical results.
  3. Planner tie injection really produces an exact tie at the cutoff.
  4. Different seeds -> different times (sanity).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.oracle import Oracle, aggregate, competition_ranks   # noqa: E402
from lib.planner import DNF, Planner                          # noqa: E402
from lib.util import DNF_TIME, load_json, scores_equal        # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}  {detail}")
        FAILURES.append(name)


def micro6_run_log(fixture, scoring_method):
    classid = fixture["classid"]
    log = []
    for rid_s, times in fixture["prelim_times"].items():
        for run_idx, t in enumerate(times):
            log.append({"classid": classid, "round_seq": 1, "heat": 0,
                        "racerid": int(rid_s),
                        "time": DNF_TIME if t == "DNF" else float(t)})
    # finals entries only for the advancing set of the method under test
    advancing = set(load_json(os.path.join(
        HERE, "fixtures/micro6/expected.json"))[scoring_method]["advancing"])
    for heat_s, entries in fixture["finals_heats"].items():
        for rid_s, t in entries.items():
            if int(rid_s) in advancing:
                log.append({"classid": classid, "round_seq": 2,
                            "heat": int(heat_s), "racerid": int(rid_s),
                            "time": float(t)})
    return log


def micro6_classes(fixture, scoring_method):
    rounds = [dict(r) for r in fixture["rounds"]]
    rounds[0]["scoring_method"] = scoring_method
    return {fixture["classid"]: {"rounds": rounds}}


def test_micro6():
    print("== micro6 fixture vs oracle ==")
    fixture = load_json(os.path.join(HERE, "fixtures/micro6/fixture.json"))
    expected = load_json(os.path.join(HERE, "fixtures/micro6/expected.json"))
    classid = fixture["classid"]

    for method in ("total_time", "drop_slowest"):
        oracle = Oracle(micro6_run_log(fixture, method),
                        micro6_classes(fixture, method))
        exp = expected[method]

        standings = oracle.round_standings(classid, 1)
        scores = {str(r["racerid"]): r["score"] for r in standings}
        ranks = {str(r["racerid"]): r["rank"] for r in standings}
        for rid, want in exp["prelim_scores"].items():
            check(f"{method}: score[{rid}]",
                  rid in scores and scores_equal(scores[rid], want),
                  f"got {scores.get(rid)} want {want}")
        for rid, want in exp["prelim_ranks"].items():
            check(f"{method}: rank[{rid}]", ranks.get(rid) == want,
                  f"got {ranks.get(rid)} want {want}")

        adv = oracle.advancement(classid, 1)
        check(f"{method}: advancing set",
              sorted(adv["advancing"]) == sorted(exp["advancing"]),
              f"got {sorted(adv['advancing'])} want {exp['advancing']}")

    # withdrawn exclusion: 904 pulls out -> total_time cut becomes 901,902,903
    fixture_w = load_json(os.path.join(HERE, "fixtures/micro6/fixture.json"))
    oracle_w = Oracle(micro6_run_log(fixture_w, "total_time"),
                      micro6_classes(fixture_w, "total_time"),
                      withdrawn={classid: [904]})
    adv_w = oracle_w.advancement(classid, 1)
    want_w = expected["with_904_withdrawn"]["advancing_total_time"]
    check("withdrawn 904 excluded from advancement",
          sorted(adv_w["advancing"]) == sorted(want_w),
          f"got {sorted(adv_w['advancing'])} want {want_w}")
    check("naive (withdrawn-included) set still reported",
          904 in adv_w["advancing_ignoring_withdrawn"])

    # finals placement + awards (independent of prelim method given the
    # std advancing set raced the finals heats in the fixture)
    oracle = Oracle(micro6_run_log(fixture, "total_time"),
                    micro6_classes(fixture, "total_time"))
    finals = [r["racerid"] for r in oracle.final_results(classid)]
    check("finals order", finals == expected["finals_order"],
          f"got {finals} want {expected['finals_order']}")
    awards = [a["racerid"] for a in oracle.awards(classid)]
    check("awards top3", awards == expected["awards"],
          f"got {awards} want {expected['awards']}")


def test_primitives():
    print("== scoring primitives ==")
    check("drop_slowest drops the DNF",
          scores_equal(aggregate("drop_slowest", [13.0, DNF_TIME]), 13.0))
    check("drop_slowest single run", scores_equal(
        aggregate("drop_slowest", [17.5]), 17.5))
    check("drop_slowest 3 runs", scores_equal(
        aggregate("drop_slowest", [10.0, 12.0, 11.0]), 10.5))
    check("total includes DNF", scores_equal(
        aggregate("total_time", [13.0, DNF_TIME]), 112.999))
    check("competition ranks",
          competition_ranks([10.0, 10.0, 11.0, 11.0, 12.0]) == [1, 1, 3, 3, 5])


def fake_classes():
    rounds = [
        {"round_sequence": 1, "round_name": "1 Preliminary",
         "races_per_racer": 3, "advance_count": 5,
         "scoring_method": "total_time"},
        {"round_sequence": 2, "round_name": "2 Finals",
         "races_per_racer": 1, "advance_count": 0,
         "scoring_method": "placement"},
    ]
    return {7: {"age_group_key": "ages_6_8",
                "racerids": list(range(101, 116)),  # 15 racers
                "rounds": rounds}}


def test_planner():
    print("== planner determinism & tie injection ==")
    scenario = {"name": "t", "dnf_probability": 0.05,
                "time_model": {"min": 10, "max": 30, "resolution": 0.001},
                "targeted_events": [
                    {"type": "tie_at_cutoff", "age_group": "ages_6_8",
                     "width": 2}]}
    a = Planner(42, scenario, fake_classes())
    b = Planner(42, scenario, fake_classes())
    series_a = [a.planned_result(7, rid, 1, run)
                for rid in range(101, 116) for run in range(3)]
    series_b = [b.planned_result(7, rid, 1, run)
                for rid in range(101, 116) for run in range(3)]
    check("same seed reproduces identical results", series_a == series_b)

    c = Planner(43, scenario, fake_classes())
    series_c = [c.planned_result(7, rid, 1, run)
                for rid in range(101, 116) for run in range(3)]
    check("different seed differs", series_a != series_c)

    # the tie group must produce an exact aggregate tie at the cutoff
    check("tie group recorded", len(a.tie_groups) == 1, a.tie_groups)
    if a.tie_groups:
        group = a.tie_groups[0]["racerids"]
        def total(planner, rid):
            return sum(DNF_TIME if planner.planned_result(7, rid, 1, r) == DNF
                       else planner.planned_result(7, rid, 1, r)
                       for r in range(3))
        totals = [total(a, rid) for rid in group]
        check("tie group aggregates equal",
              all(scores_equal(t, totals[0]) for t in totals), totals)
        ranked = sorted(total(a, rid) for rid in range(101, 116))
        check("tie sits at the cutoff (rank 5 == rank 6)",
              scores_equal(ranked[4], ranked[5]), ranked[3:7])

    dnfs = [v for v in series_a if v == DNF]
    check("random DNFs occur at ~5%", 0 < len(dnfs) <= 9,
          f"{len(dnfs)}/45 runs")


if __name__ == "__main__":
    test_primitives()
    test_micro6()
    test_planner()
    print()
    if FAILURES:
        print(f"SELFTEST FAILED: {len(FAILURES)} failure(s): {FAILURES}")
        sys.exit(1)
    print("SELFTEST PASSED")
