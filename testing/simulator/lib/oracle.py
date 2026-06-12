"""Independent expected-results computation.

Consumes the orchestrator's run log (every result actually injected, keyed by
racer/round/run) and recomputes scores, rankings, advancement sets, finals
placement, and awards — entirely outside PHP.  The verifier diffs this
against what the live system recorded.

Semantics (the agreed truth):
  * DNF == 99.999 exactly and participates in every aggregate.
  * drop_slowest = the single time when n == 1, else (sum - max) / (n - 1);
    note a DNF is usually the max, so one DNF gets erased by the drop.
  * Ranking ascending by score; competition ranking (1,2,2,4) with scores
    compared at SCORE_EPSILON.
  * Advancement = top advance_count plus everyone tied with the
    advance_count-th score.  Pull-forward dropouts are ineligible (a
    withdrawn racer must not advance on a partial-run aggregate).
  * Finals (placement): place per heat by ascending time (DNFs unplaced);
    racer score = best place across finals heats, tiebreak by best time.
  * Awards: finals placement order, top 3 per class.
"""

from typing import Dict, List

from .util import DNF_TIME, SCORE_EPSILON, scores_equal


def aggregate(method: str, times: List[float]) -> float:
    if not times:
        return float("inf")
    if method == "total_time":
        return sum(times)
    if method == "average_time":
        return sum(times) / len(times)
    if method == "best_time":
        return min(times)
    if method == "drop_slowest":
        if len(times) == 1:
            return times[0]
        return (sum(times) - max(times)) / (len(times) - 1)
    raise ValueError(f"unknown scoring method: {method}")


def competition_ranks(sorted_scores: List[float]) -> List[int]:
    """[10.0, 10.0, 11.0] -> [1, 1, 3]"""
    ranks = []
    for i, score in enumerate(sorted_scores):
        if i > 0 and scores_equal(score, sorted_scores[i - 1]):
            ranks.append(ranks[-1])
        else:
            ranks.append(i + 1)
    return ranks


class Oracle:
    """
    run_log: list of dicts, one per injected result:
        {classid, round_seq, racerid, time}   # time == 99.999 for DNF
    classes: {classid: {"rounds": [round configs in sequence order]}}
    withdrawn: {classid: [racerid, ...]} pull-forward dropouts
    """

    def __init__(self, run_log: List[dict], classes: Dict[int, dict],
                 withdrawn: Dict[int, List[int]] | None = None):
        self.run_log = run_log
        self.classes = classes
        self.withdrawn = withdrawn or {}

    def times_for(self, classid: int, round_seq: int) -> Dict[int, List[float]]:
        out: Dict[int, List[float]] = {}
        for entry in self.run_log:
            if entry["classid"] == classid and entry["round_seq"] == round_seq:
                out.setdefault(entry["racerid"], []).append(float(entry["time"]))
        return out

    # ------------------------------------------------------------------ #

    def round_standings(self, classid: int, round_seq: int) -> List[dict]:
        """Ranked standings for one round: [{racerid, score, rank, times}]."""
        cfg = self.classes[classid]["rounds"][round_seq - 1]
        method = cfg["scoring_method"]
        per_racer = self.times_for(classid, round_seq)
        if method == "placement":
            return self._finals_standings(classid, round_seq)
        rows = [{"racerid": rid, "times": sorted(ts),
                 "score": round(aggregate(method, ts), 6)}
                for rid, ts in per_racer.items()]
        rows.sort(key=lambda r: (r["score"], r["racerid"]))
        for rank, row in zip(competition_ranks([r["score"] for r in rows]), rows):
            row["rank"] = rank
        return rows

    def _finals_standings(self, classid: int, round_seq: int) -> List[dict]:
        """Placement scoring.  The run log carries (heat) for finals entries
        so places can be computed per heat."""
        heats: Dict[int, List[dict]] = {}
        for entry in self.run_log:
            if entry["classid"] == classid and entry["round_seq"] == round_seq:
                heats.setdefault(entry.get("heat", 1), []).append(entry)

        best_place: Dict[int, int] = {}
        best_time: Dict[int, float] = {}
        for heat_entries in heats.values():
            finishers = sorted(
                (e for e in heat_entries
                 if float(e["time"]) < DNF_TIME - SCORE_EPSILON),
                key=lambda e: float(e["time"]))
            for place, e in enumerate(finishers, 1):
                rid = e["racerid"]
                if place < best_place.get(rid, 99):
                    best_place[rid] = place
                best_time[rid] = min(best_time.get(rid, 999.0), float(e["time"]))
            for e in heat_entries:  # DNF-only racers: unplaced, time DNF
                rid = e["racerid"]
                best_place.setdefault(rid, 99)
                best_time.setdefault(rid, DNF_TIME)

        rows = [{"racerid": rid, "score": best_place[rid],
                 "times": [best_time[rid]],
                 "best_time": best_time[rid]}
                for rid in best_place]
        rows.sort(key=lambda r: (r["score"], r["best_time"], r["racerid"]))
        for rank, row in enumerate(rows, 1):
            row["rank"] = rank
        return rows

    # ------------------------------------------------------------------ #

    def advancement(self, classid: int, round_seq: int) -> dict:
        """Expected advancing set out of a round (tie-inclusive, dropouts
        excluded).  Also reports what the set would be WITHOUT the dropout
        exclusion so the verifier can classify a PHP mismatch precisely."""
        cfg = self.classes[classid]["rounds"][round_seq - 1]
        advance = int(cfg.get("advance_count", 0))
        standings = self.round_standings(classid, round_seq)
        if advance <= 0:
            return {"advancing": [], "standings": standings}

        def cut(rows) -> List[dict]:
            if len(rows) <= advance:
                return list(rows)
            cutoff = rows[advance - 1]["score"]
            return [r for i, r in enumerate(rows)
                    if i < advance or scores_equal(r["score"], cutoff)]

        withdrawn = set(self.withdrawn.get(classid, []))
        # Withdrawn racers hold no rank: the engine excludes them from the
        # ranking query entirely, so re-rank the eligible field 1..N before
        # cutting (a dropout's partial-run aggregate must not displace rank
        # numbers of real contenders).
        eligible = [dict(r) for r in standings if r["racerid"] not in withdrawn]
        for rank, row in zip(competition_ranks([r["score"] for r in eligible]),
                             eligible):
            row["rank"] = rank
        advancing = cut(eligible)
        naive = cut(standings)
        return {
            "advancing": [r["racerid"] for r in advancing],
            "advancing_rows": advancing,
            "advancing_ignoring_withdrawn": [r["racerid"] for r in naive],
            "standings": standings,
        }

    def final_results(self, classid: int) -> List[dict]:
        last_round = len(self.classes[classid]["rounds"])
        return self.round_standings(classid, last_round)

    def awards(self, classid: int, top_n: int = 3) -> List[dict]:
        finals = self.final_results(classid)
        return [{"place": i + 1, "racerid": row["racerid"]}
                for i, row in enumerate(finals[:top_n])]

    def expected(self) -> dict:
        """Full expected progression for every class, JSON-able."""
        out = {}
        for classid, info in self.classes.items():
            rounds = {}
            for seq in range(1, len(info["rounds"]) + 1):
                rounds[str(seq)] = self.advancement(classid, seq)
            out[str(classid)] = {
                "rounds": rounds,
                "final_results": self.final_results(classid),
                "awards": self.awards(classid),
            }
        return out
