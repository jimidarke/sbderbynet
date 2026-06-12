"""Deterministic scenario planner.

Every injected result is a pure function of (seed, racerid, round, run), so a
variant is fully reproducible from its seed.  Targeted events (boundary ties,
all-DNF heats, pull-forward dropouts) are layered on top as overrides.

The planner never predicts the schedule: the orchestrator asks for a result
whenever a (racer, round, run) actually comes up on track.
"""

import random
from typing import Dict, List

from .util import DNF_TIME, t3

DNF = "DNF"


def _rng(*key) -> random.Random:
    return random.Random("|".join(str(k) for k in key))


def quantize(value: float, resolution: float) -> float:
    steps = round(value / resolution)
    return t3(steps * resolution)


class Planner:
    """
    classes: {classid: {"age_group_key": str,
                        "racerids": [int, ...],
                        "rounds": [round-config dicts from the elimination
                                   JSON, in sequence order]}}
    scenario: parsed scenario JSON (see scenarios/*.json)
    """

    def __init__(self, seed: int, scenario: dict, classes: Dict[int, dict]):
        self.seed = seed
        self.scenario = scenario
        self.classes = classes
        tm = scenario.get("time_model", {})
        self.t_min = float(tm.get("min", 10.0))
        self.t_max = float(tm.get("max", 30.0))
        self.resolution = float(tm.get("resolution", 0.001))
        self.dnf_probability = float(scenario.get("dnf_probability", 0.0))

        # (classid, racerid, round_seq, run_idx) -> time | DNF
        self.overrides: dict = {}
        # resolved targeted events, keyed by kind
        self.heat_events: List[dict] = []      # dnf_all_lanes
        self.pullforward_events: List[dict] = []
        self.tie_groups: List[dict] = []       # for reporting
        self.all_dnf_racers: List[dict] = []   # for reporting

        self._resolve_events()

    # ------------------------------------------------------------------ #

    def planned_result(self, classid: int, racerid: int, round_seq: int,
                       run_idx: int):
        """Return the planned time (float, quantized) or DNF."""
        key = (classid, racerid, round_seq, run_idx)
        if key in self.overrides:
            return self.overrides[key]
        if self.dnf_probability > 0:
            if _rng(self.seed, "dnf", *key).random() < self.dnf_probability:
                return DNF
        return self._base_time(*key)

    def _base_time(self, classid, racerid, round_seq, run_idx) -> float:
        r = _rng(self.seed, "time", classid, racerid, round_seq, run_idx)
        return quantize(r.uniform(self.t_min, self.t_max), self.resolution)

    def choose(self, key: str, candidates: list):
        """Deterministic pick used by the orchestrator for runtime choices
        (e.g. which eligible racer drops out)."""
        if not candidates:
            return None
        return _rng(self.seed, "choose", key).choice(sorted(candidates))

    # ------------------------------------------------------------------ #

    def _classid_for_group(self, age_group_key: str):
        for cid, info in self.classes.items():
            if info["age_group_key"] == age_group_key:
                return cid
        return None

    def _resolve_events(self) -> None:
        for i, ev in enumerate(self.scenario.get("targeted_events", [])):
            kind = ev.get("type")
            classid = self._classid_for_group(ev.get("age_group", ""))
            if classid is None:
                continue
            if kind == "racer_all_dnf":
                self._apply_racer_all_dnf(i, classid)
            elif kind == "tie_at_cutoff":
                self._apply_tie_at_cutoff(i, classid,
                                          int(ev.get("width", 2)),
                                          int(ev.get("round", 1)))
            elif kind == "dnf_all_lanes":
                self.heat_events.append({
                    "type": "dnf_all_lanes",
                    "classid": classid,
                    "round_seq": int(ev.get("round", 1)),
                    "heat_fraction": float(ev.get("heat_fraction", 0.5)),
                })
            elif kind == "pullforward":
                self.pullforward_events.append({
                    "type": "pullforward",
                    "classid": classid,
                    "round_seq": int(ev.get("round", 1)),
                    "after_heat_fraction": float(ev.get("after_heat_fraction", 0.4)),
                    "dropouts": int(ev.get("dropouts", 1)),
                    "undo_first": bool(ev.get("undo_first", False)),
                })

    def _apply_racer_all_dnf(self, idx: int, classid: int) -> None:
        info = self.classes[classid]
        racerid = _rng(self.seed, "alldnf", idx).choice(sorted(info["racerids"]))
        runs = int(info["rounds"][0].get("races_per_racer", 1))
        for run_idx in range(runs):
            self.overrides[(classid, racerid, 1, run_idx)] = DNF
        self.all_dnf_racers.append({"classid": classid, "racerid": racerid})

    def _apply_tie_at_cutoff(self, idx: int, classid: int, width: int,
                             round_seq: int) -> None:
        """Force `width` racers to share the exact score at the advancement
        cutoff of the given round (round 1 only — later-round fields depend
        on results)."""
        if round_seq != 1:
            return
        info = self.classes[classid]
        round_cfg = info["rounds"][0]
        advance = int(round_cfg.get("advance_count", 0))
        runs = int(round_cfg.get("races_per_racer", 1))
        if advance <= 0 or advance >= len(info["racerids"]):
            return

        # Rank racers by their would-be aggregate under this round's scoring.
        method = round_cfg.get("scoring_method", "total_time")
        scored = []
        for racerid in sorted(info["racerids"]):
            times = []
            for run_idx in range(runs):
                v = self.planned_result(classid, racerid, round_seq, run_idx)
                times.append(DNF_TIME if v == DNF else v)
            scored.append((self._aggregate(method, times), racerid))
        scored.sort()

        anchor_score, anchor = scored[advance - 1]
        group = [anchor]
        for offset in range(width - 1):
            pos = advance + offset
            if pos >= len(scored):
                break
            _, racerid = scored[pos]
            # Copy the anchor's exact run times: equal aggregates under every
            # scoring method, so the tie survives a std/dropslowest re-run.
            for run_idx in range(runs):
                self.overrides[(classid, racerid, round_seq, run_idx)] = \
                    self.planned_result(classid, anchor, round_seq, run_idx)
            group.append(racerid)
        self.tie_groups.append({"classid": classid, "round_seq": round_seq,
                                "racerids": group, "cutoff": advance,
                                "score": anchor_score})

    @staticmethod
    def _aggregate(method: str, times: List[float]) -> float:
        if not times:
            return float("inf")
        if method == "total_time":
            return sum(times)
        if method == "best_time":
            return min(times)
        if method == "average_time":
            return sum(times) / len(times)
        if method == "drop_slowest":
            if len(times) == 1:
                return times[0]
            return (sum(times) - max(times)) / (len(times) - 1)
        raise ValueError(f"unknown scoring method {method}")

    # ------------------------------------------------------------------ #

    def describe(self) -> dict:
        """JSON-able summary stored in the variant artifact."""
        return {
            "seed": self.seed,
            "scenario": self.scenario,
            "tie_groups": self.tie_groups,
            "all_dnf_racers": self.all_dnf_racers,
            "heat_events": self.heat_events,
            "pullforward_events": self.pullforward_events,
            "override_count": len(self.overrides),
        }
