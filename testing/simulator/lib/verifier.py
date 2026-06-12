"""Diffs the oracle's expected tournament against what the live system
actually recorded in the tenant DB."""

from typing import List

from . import dbread
from .util import DNF_TIME, SCORE_EPSILON, make_logger, scores_equal

logger = make_logger("sim.verifier")

FAST_TOLERANCE = 0.0015      # fast mode: device timestamps are exact
REALTIME_TOLERANCE = 0.15    # realtime: sleep + edge scheduling jitter


class Check:
    def __init__(self, name: str):
        self.name = name
        self.ok = True
        self.details: List[str] = []

    def fail(self, msg: str) -> None:
        self.ok = False
        self.details.append(msg)
        if len(self.details) > 50:
            del self.details[10:-10]

    def note(self, msg: str) -> None:
        self.details.append(msg)

    def as_dict(self) -> dict:
        return {"name": self.name, "ok": self.ok, "details": self.details}


def verify(artifact: dict) -> dict:
    tenant = artifact["tenant"]
    tolerance = FAST_TOLERANCE if artifact["mode"] == "fast" else REALTIME_TOLERANCE
    checks: List[Check] = []

    checks.append(_check_times(tenant, artifact, tolerance))
    checks.append(_check_dnf_values(tenant, artifact))
    advancement_checks, dropout_findings = _check_advancement(
        tenant, artifact, score_tolerance=tolerance * 4)
    checks.extend(advancement_checks)
    checks.append(_check_terminal_round(tenant, artifact))
    checks.append(_check_final_standings(tenant, artifact))
    checks.append(_check_awards(tenant, artifact))

    passed = all(c.ok for c in checks) and artifact["status"] == "completed"
    return {
        "tenant": tenant,
        "seed": artifact["seed"],
        "config": artifact["config"],
        "passed": passed,
        "status": artifact["status"],
        "checks": [c.as_dict() for c in checks],
        "dropout_eligibility_findings": dropout_findings,
        "anomalies": artifact.get("anomalies", []),
    }


# ---------------------------------------------------------------------- #

def _chart_by_key(tenant: str, roundids) -> dict:
    out = {}
    for roundid in roundids:
        for row in dbread.race_chart(tenant, roundid):
            out[(row["roundid"], row["heat"], row["lane"])] = row
    return out


def _check_times(tenant, artifact, tolerance) -> Check:
    check = Check("racechart_times_match_injected")
    roundids = {e["roundid"] for e in artifact["run_log"]}
    chart = _chart_by_key(tenant, roundids)
    for entry in artifact["run_log"]:
        key = (entry["roundid"], entry["heat"], entry["lane"])
        row = chart.get(key)
        if row is None:
            check.fail(f"no RaceChart row for {key}")
            continue
        if row["racerid"] != entry["racerid"]:
            check.fail(f"{key}: racer {row['racerid']} != injected "
                       f"{entry['racerid']}")
            continue
        actual = row["finishtime"]
        if actual is None:
            check.fail(f"{key}: no finishtime recorded")
        elif abs(float(actual) - entry["time"]) > tolerance:
            check.fail(f"{key}: recorded {actual} vs injected "
                       f"{entry['time']} (>{tolerance})")
    check.note(f"{len(artifact['run_log'])} injected results compared")
    return check


def _check_dnf_values(tenant, artifact) -> Check:
    check = Check("dnf_rows_exact_sentinel")
    roundids = {e["roundid"] for e in artifact["run_log"]}
    chart = _chart_by_key(tenant, roundids)
    count = 0
    for entry in artifact["run_log"]:
        if entry["via"] != "racer.dnf":
            continue
        count += 1
        row = chart.get((entry["roundid"], entry["heat"], entry["lane"]))
        if row is None or row["finishtime"] is None:
            check.fail(f"DNF row missing for {entry}")
        elif abs(float(row["finishtime"]) - DNF_TIME) > 1e-6:
            check.fail(f"DNF recorded as {row['finishtime']} not {DNF_TIME}")
    check.note(f"{count} DNFs checked")
    return check


def _check_advancement(tenant, artifact, score_tolerance=SCORE_EPSILON):
    checks, findings = [], []
    expected = artifact.get("expected") or {}
    for classid_s, info in artifact["classes"].items():
        classid = int(classid_s)
        exp_class = expected.get(classid_s, {})
        tournament_id = info["tournament_id"]
        adv_rows = dbread.advancement_rows(tenant, tournament_id)
        n_rounds = len(info["rounds_db"])

        for seq in range(1, n_rounds):
            check = Check(f"advancement_class{classid}_round{seq}")
            exp = (exp_class.get("rounds") or {}).get(str(seq)) or {}
            exp_set = set(exp.get("advancing", []))
            actual = [r for r in adv_rows if r["from_round"] == seq]
            actual_set = {r["racerid"] for r in actual}

            if not exp_set and not actual_set:
                checks.append(check)
                continue
            if actual_set == exp_set:
                check.note(f"{len(exp_set)} advancing racers match")
                _check_ranks(check, actual, exp.get("advancing_rows", []),
                             score_tolerance)
            elif actual_set == set(exp.get("advancing_ignoring_withdrawn", [])):
                check.fail(
                    "advancement matches the WITHDRAWN-INCLUDED set: a "
                    "pull-forward dropout advanced on a partial-run "
                    f"aggregate (diff={sorted(actual_set - exp_set)})")
                findings.append({"classid": classid, "round": seq,
                                 "type": "dropout_advanced"})
            else:
                check.fail(f"advancing set mismatch: "
                           f"expected {sorted(exp_set)}, "
                           f"actual {sorted(actual_set)}")

            # roster of next round must equal the actual advancing set
            next_roundid = info["rounds_db"].get(str(seq + 1)) or \
                info["rounds_db"].get(seq + 1)
            if next_roundid:
                roster = set(dbread.roster_racerids(tenant, next_roundid))
                if roster and roster != actual_set:
                    check.fail(f"next-round roster {sorted(roster)} != "
                               f"advancement {sorted(actual_set)}")
            checks.append(check)
    return checks, findings


def _check_ranks(check: Check, actual_rows, expected_rows,
                 score_tolerance=SCORE_EPSILON) -> None:
    """Score comparison uses the mode's time tolerance scaled for multi-run
    aggregates: realtime recorded times legitimately differ from the plan by
    up to ~0.15s each."""
    exp_by_racer = {r["racerid"]: r for r in expected_rows}
    for row in actual_rows:
        exp = exp_by_racer.get(row["racerid"])
        if not exp:
            continue
        if row["rank_in_round"] != exp.get("rank"):
            check.fail(f"racer {row['racerid']}: rank {row['rank_in_round']} "
                       f"!= expected {exp.get('rank')}")
        if exp.get("score") is not None and row["score"] is not None and \
                abs(float(row["score"]) - float(exp["score"])) > score_tolerance:
            check.fail(f"racer {row['racerid']}: score {row['score']} != "
                       f"expected {exp['score']} (tol {score_tolerance})")


def _check_terminal_round(tenant, artifact) -> Check:
    check = Check("tournament_reached_final_round")
    tournaments = {t["classid"]: t
                   for t in dbread.classes_with_tournaments(tenant)}
    for classid_s, info in artifact["classes"].items():
        classid = int(classid_s)
        t = tournaments.get(classid)
        total = len(info["rounds_db"])
        if not t:
            check.fail(f"class {classid}: no active tournament row")
        elif int(t["current_round"]) != total:
            check.fail(f"class {classid}: current_round "
                       f"{t['current_round']} != total rounds {total}")
    return check


def _check_final_standings(tenant, artifact) -> Check:
    check = Check("final_standings_match_oracle")
    expected = artifact.get("expected") or {}
    for classid_s, info in artifact["classes"].items():
        exp_finals = (expected.get(classid_s) or {}).get("final_results") or []
        if not exp_finals:
            continue
        rounds_db = info["rounds_db"]
        last_seq = max(int(k) for k in rounds_db)
        roundid = rounds_db.get(str(last_seq)) or rounds_db.get(last_seq)
        chart = dbread.race_chart(tenant, roundid)
        # Order actual finalists by (place, time); compare top-3 order.
        finishers = sorted(
            (r for r in chart if r["finishtime"] is not None
             and float(r["finishtime"]) < DNF_TIME - SCORE_EPSILON),
            key=lambda r: (r["finishplace"] if r["finishplace"] else 99,
                           float(r["finishtime"])))
        actual_order = []
        for r in finishers:
            if r["racerid"] not in actual_order:
                actual_order.append(r["racerid"])
        expected_order = [r["racerid"] for r in exp_finals
                          if r.get("best_time", 0) < DNF_TIME - SCORE_EPSILON]
        if actual_order[:3] != expected_order[:3]:
            check.fail(f"class {classid_s} podium: actual {actual_order[:3]} "
                       f"!= expected {expected_order[:3]}")
    return check


def _check_awards(tenant, artifact) -> Check:
    """Soft check: only enforced when speed awards are actually assigned in
    the tenant DB (the cloned official DB may or may not have them set up)."""
    check = Check("awards_match_oracle")
    try:
        awards = dbread.awards_assigned(tenant)
    except Exception as e:
        check.note(f"awards table unreadable ({e}); skipped")
        return check
    assigned = [a for a in awards if a.get("racerid")]
    if not assigned:
        check.note("no assigned awards in tenant; skipped")
        return check
    expected = artifact.get("expected") or {}
    for classid_s in artifact["classes"]:
        exp = {a["place"]: a["racerid"]
               for a in (expected.get(classid_s) or {}).get("awards", [])}
        got = {}
        for a in assigned:
            if a.get("classid") == int(classid_s) and 1 <= (a.get("sort") or 0) <= 3:
                got[a["sort"]] = a["racerid"]
        for place, racerid in got.items():
            if place in exp and exp[place] != racerid:
                check.fail(f"class {classid_s} award place {place}: "
                           f"{racerid} != expected {exp[place]}")
    return check
