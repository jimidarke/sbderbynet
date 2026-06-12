"""Drives one full simulated tournament variant against a sim tenant.

Per heat, the flow mirrors race day exactly:
  coordinator selects heat (now_racing=1)
  -> race-server polls PHP, goes STAGING, publishes correlation id
  -> mock finish timers report ready, mock start timer publishes GO
  -> mock finish timers publish toggle=false finishes (device timestamps)
  -> race-server computes times, writes results direct to the tenant DB
  -> the mock kiosk's poll.results call triggers PHP heat auto-advance
DNFs go through the coordinator path (action=racer.dnf) and are picked up by
the race-server's 1s API tick, identical to the real DNF button.

Fast mode backdates device timestamps so no wall-clock waiting happens;
realtime mode actually waits out each race.
"""

import json
import os
import time
from typing import Dict, List, Optional

from . import dbread, tenantpool
from .api import DerbyApi
from .devices import MockTrack
from .kiosk import KioskPoller
from .oracle import Oracle
from .planner import DNF, Planner
from .util import DNF_TIME, find_configs_dir, load_json, make_logger, t3

logger = make_logger("sim.orchestrator")

CONFIG_FILES = {
    "std": "soapbox-derby-elimination.json",
    "dropslowest": "soapbox-derby-elimination-dropslowest.json",
}


class VariantError(RuntimeError):
    pass


class VariantRunner:
    def __init__(self, tenant: str, seed: int, scenario: dict,
                 config_name: str = "std", mode: str = "fast",
                 age_groups: Optional[List[str]] = None,
                 lane_count: int = 3):
        if mode not in ("fast", "realtime"):
            raise ValueError(f"unknown mode {mode}")
        self.tenant = tenant
        self.seed = seed
        self.scenario = scenario
        self.config_name = config_name
        self.mode = mode
        self.age_groups_filter = age_groups
        self.lane_count = lane_count

        self.api = DerbyApi(tenant)
        self.track = MockTrack(tenant, lane_count)
        self.kiosk = KioskPoller(tenant)
        self.planner: Optional[Planner] = None
        self.classes: Dict[int, dict] = {}

        self.run_log: List[dict] = []
        self.lineups: List[dict] = []
        self.anomalies: List[dict] = []
        self.withdrawn: Dict[int, List[int]] = {}
        self.pullforward_log: List[dict] = []
        self.timings = {"heats": 0, "started": None, "finished": None}

        # fast mode waits; realtime gets generous multiples
        speed = 1 if mode == "fast" else 10
        self.staging_timeout = 20 * speed
        self.results_timeout = 30 * speed
        self.advance_timeout = 15 * speed

    # ------------------------------------------------------------------ #
    # setup

    def setup(self) -> None:
        tenantpool.reset(self.tenant)
        config_file = CONFIG_FILES[self.config_name]
        if self.config_name != "std":
            tenantpool.set_tournament_config(self.tenant, config_file)

        config = load_json(os.path.join(find_configs_dir(), config_file))
        tournaments = dbread.classes_with_tournaments(self.tenant)
        racer_rows = dbread.racers(self.tenant)

        for t in tournaments:
            key = t["age_group_key"]
            if self.age_groups_filter and key not in self.age_groups_filter:
                continue
            classid = t["classid"]
            rounds_db = dbread.rounds_for_class(self.tenant, classid)
            self.classes[classid] = {
                "age_group_key": key,
                "class_name": t["class_name"],
                "tournament_id": t["tournament_id"],
                "rounds": config["age_groups"][key]["rounds"],
                "rounds_db": {int(r["round"]): r["roundid"] for r in rounds_db},
                "racerids": [r["racerid"] for r in racer_rows
                             if r["classid"] == classid and not r["exclude"]],
            }
        if not self.classes:
            raise VariantError("no tournament classes found in tenant")

        self.planner = Planner(self.seed, self.scenario, self.classes)
        self.api.login()
        self.track.up()
        self.kiosk.start()
        self.timings["started"] = time.time()
        logger.info("variant seed=%s config=%s mode=%s tenant=%s classes=%s",
                    self.seed, self.config_name, self.mode, self.tenant,
                    {c: i["age_group_key"] for c, i in self.classes.items()})

    def teardown(self) -> None:
        self.timings["finished"] = time.time()
        try:
            self.kiosk.stop()
        finally:
            self.track.down()

    # ------------------------------------------------------------------ #
    # main flow

    def run(self) -> dict:
        try:
            self.setup()
            for classid in sorted(self.classes):
                self._run_class(classid)
            return self.artifact(status="completed")
        except Exception as e:
            logger.exception("variant failed: %s", e)
            self.anomalies.append({"type": "fatal", "error": str(e)})
            return self.artifact(status="failed")
        finally:
            self.teardown()

    def _run_class(self, classid: int) -> None:
        info = self.classes[classid]
        total_rounds = len(info["rounds"])
        logger.info("=== class %s (%s): %d rounds ===",
                    classid, info["class_name"], total_rounds)
        for round_seq in range(1, total_rounds + 1):
            self._run_round(classid, round_seq)

    def _run_round(self, classid: int, round_seq: int) -> None:
        info = self.classes[classid]
        roundid = info["rounds_db"].get(round_seq)
        if roundid is None:
            raise VariantError(
                f"class {classid} round {round_seq} missing from Rounds table")

        if round_seq > 1 and not dbread.roster_racerids(self.tenant, roundid):
            raise VariantError(
                f"class {classid} round {round_seq} roster empty — "
                f"advancement did not populate it")

        self.api.must(self.api.schedule_generate(roundid),
                      f"schedule.generate round {roundid}")
        chart = dbread.race_chart(self.tenant, roundid)
        heats = sorted({r["heat"] for r in chart})
        logger.info("class %s round %s (roundid %s): %d heats",
                    classid, round_seq, roundid, len(heats))

        all_dnf_heats = self._resolve_heat_events(classid, round_seq, len(heats))
        pf_events = self._resolve_pf_events(classid, round_seq, len(heats))

        self.api.must(self.api.heat_select(roundid=roundid, heat=heats[0],
                                           now_racing=1),
                      "heat.select start of round")

        run_idx: Dict[int, int] = {}
        raced_heats = 0
        guard = 0
        while raced_heats < len(heats):
            guard += 1
            if guard > len(heats) * 3 + 10:
                raise VariantError("runaway heat loop")

            current = self._wait_current_heat(roundid)
            if current is None:
                break  # round ended early (now_racing off and all complete)
            heat = current["heat"]
            lineup = current["lineup"]

            force_all_dnf = heat in all_dnf_heats
            self._drive_heat(classid, round_seq, roundid, heat, lineup,
                             run_idx, force_all_dnf)
            raced_heats += 1
            self.timings["heats"] += 1

            self._await_heat_advance(roundid, heat, raced_heats == len(heats))

            for ev in pf_events:
                if ev["after_heat"] == raced_heats and not ev.get("applied"):
                    self._apply_pullforward(classid, roundid, ev)
                    # schedule changed: re-read the chart/heat list
                    chart = dbread.race_chart(self.tenant, roundid)
                    heats = sorted({r["heat"] for r in chart})

        self._verify_round_complete(classid, round_seq, roundid)
        if round_seq < len(info["rounds"]):
            self._await_advancement(classid, round_seq)

    # ------------------------------------------------------------------ #
    # heat driving

    def _wait_current_heat(self, roundid: int) -> Optional[dict]:
        def ready(payload):
            ch = payload.get("current-heat", {})
            if not ch.get("now_racing"):
                return "stopped"
            if int(ch.get("roundid", -1)) != roundid:
                return "other-round"
            racers = [r for r in payload.get("racers", [])
                      if r.get("racerid")]
            if not racers:
                return None
            return {"heat": int(ch["heat"]),
                    "lineup": [{"lane": int(r["lane"]),
                                "racerid": int(r["racerid"]),
                                "carnumber": r.get("carnumber")}
                               for r in racers]}
        result = self.api.wait_for(ready, self.staging_timeout,
                                   what=f"current heat of round {roundid}")
        if result in ("stopped", "other-round"):
            return None
        return result

    def _drive_heat(self, classid, round_seq, roundid, heat, lineup,
                    run_idx, force_all_dnf) -> None:
        # Decide results
        results = []
        for entry in lineup:
            rid = entry["racerid"]
            idx = run_idx.get(rid, 0)
            planned = (DNF if force_all_dnf else
                       self.planner.planned_result(classid, rid, round_seq, idx))
            results.append({**entry, "planned": planned, "run_idx": idx})
            run_idx[rid] = idx + 1

        self.lineups.append({"classid": classid, "round_seq": round_seq,
                             "roundid": roundid, "heat": heat,
                             "lineup": lineup})

        # Wait for the race-server to stage THIS heat (per-heat correlation
        # id), not just any retained STAGING from the previous heat — its
        # startRace refuses a GO until the prior race state has cleared.
        if not self.track.session.wait_for_heat_staged(
                roundid, heat, self.staging_timeout):
            self.anomalies.append({
                "type": "staging_timeout", "roundid": roundid, "heat": heat,
                "race_state": self.track.session.race_state,
                "correlation": self.track.session.correlation_id})
        self.track.stage_all()
        time.sleep(0.3 if self.mode == "fast" else 1.5)

        finish_lanes = [r for r in results if r["planned"] != DNF]
        dnf_lanes = [r for r in results if r["planned"] == DNF]
        max_time = max([r["planned"] for r in finish_lanes], default=5.0)

        attempts = 2 if self.mode == "fast" else 1
        for attempt in range(1, attempts + 1):
            if self.mode == "fast":
                t0 = time.time() - (max_time + 2.0)
                self.track.start.send_go(t0)
                for r in sorted(finish_lanes, key=lambda x: x["planned"]):
                    self.track.finish[r["lane"]].trigger_finish(t0 + r["planned"])
            else:
                self.track.start.send_go(time.time())
                t0 = time.time()

            # DNFs via the coordinator button path, after GO.  Re-posting on
            # a retry just rewrites the same 99.999.
            self.track.session.wait_for_race_state(
                {"RACING", "FINISHED", "STOPPED"}, 10)
            for r in dnf_lanes:
                self.api.must(self.api.racer_dnf(r["racerid"], roundid, heat),
                              f"racer.dnf {r['racerid']} heat {heat}")

            if self.mode == "realtime":
                for r in sorted(finish_lanes, key=lambda x: x["planned"]):
                    delay = t0 + r["planned"] - time.time()
                    if delay > 0:
                        time.sleep(delay)
                    self.track.finish[r["lane"]].trigger_finish(time.time())

            try:
                self._await_results(roundid, heat, results)
                break
            except VariantError:
                if attempt == attempts:
                    raise
                self.anomalies.append({
                    "type": "heat_retry", "roundid": roundid, "heat": heat,
                    "race_state": self.track.session.race_state})
                logger.warning("heat %s results missing; retrying GO/finish "
                               "sequence once", heat)

        for r in results:
            self.run_log.append({
                "classid": classid, "round_seq": round_seq,
                "roundid": roundid, "heat": heat, "lane": r["lane"],
                "racerid": r["racerid"], "run_idx": r["run_idx"],
                "time": DNF_TIME if r["planned"] == DNF else t3(r["planned"]),
                "via": "racer.dnf" if r["planned"] == DNF else "mqtt",
            })

    def _await_results(self, roundid, heat, results) -> None:
        deadline = time.monotonic() + self.results_timeout
        wanted = {r["lane"] for r in results}
        while time.monotonic() < deadline:
            rows = [r for r in dbread.race_chart(self.tenant, roundid)
                    if r["heat"] == heat and r["lane"] in wanted]
            if rows and all(r["finishtime"] is not None for r in rows):
                return
            time.sleep(0.25)
        raise VariantError(
            f"results for roundid {roundid} heat {heat} never landed "
            f"(race_state={self.track.session.race_state})")

    def _await_heat_advance(self, roundid, finished_heat, was_last) -> None:
        def moved(payload):
            ch = payload.get("current-heat", {})
            if not ch.get("now_racing"):
                return "stopped"
            if int(ch.get("roundid", -1)) != roundid:
                return "moved-round"
            if int(ch.get("heat", -1)) != finished_heat:
                return "moved-heat"
            return None
        try:
            self.api.wait_for(moved, self.advance_timeout,
                              what=f"heat advance past {finished_heat}")
        except TimeoutError:
            self.anomalies.append({
                "type": "advance_fallback", "roundid": roundid,
                "heat": finished_heat, "was_last": was_last})
            logger.warning("kiosk-poll did not advance heat %s; forcing",
                           finished_heat)
            if not was_last:
                self.api.heat_select(roundid=roundid, heat=finished_heat + 1,
                                     now_racing=1)

    # ------------------------------------------------------------------ #
    # events

    def _resolve_heat_events(self, classid, round_seq, n_heats) -> set:
        out = set()
        for ev in self.planner.heat_events:
            if ev["classid"] == classid and ev["round_seq"] == round_seq:
                heat = max(1, min(n_heats,
                                  round(ev["heat_fraction"] * n_heats)))
                out.add(heat)
        return out

    def _resolve_pf_events(self, classid, round_seq, n_heats) -> List[dict]:
        out = []
        for ev in self.planner.pullforward_events:
            if ev["classid"] == classid and ev["round_seq"] == round_seq:
                out.append({**ev,
                            "after_heat": max(1, min(
                                n_heats - 2,
                                round(ev["after_heat_fraction"] * n_heats)))})
        return out

    def _apply_pullforward(self, classid, roundid, ev) -> None:
        chart = dbread.race_chart(self.tenant, roundid)
        remaining = [r for r in chart if r["finishtime"] is None]
        candidates = sorted({r["racerid"] for r in remaining})
        for n in range(ev["dropouts"]):
            dropout = self.planner.choose(
                f"pf:{classid}:{roundid}:{n}", candidates)
            if dropout is None:
                return
            candidates.remove(dropout)

            dry = self.api.pull_forward(roundid, dropout, dry_run=True)
            self.api.must(dry, "pullforward dry-run")
            applied = self.api.pull_forward(roundid, dropout)
            self.api.must(applied, "pullforward apply")

            if ev.get("undo_first") and n == 0:
                undo = self.api.pull_forward_undo(roundid)
                self.api.must(undo, "pullforward undo")
                applied = self.api.pull_forward(roundid, dropout)
                self.api.must(applied, "pullforward re-apply")

            self.withdrawn.setdefault(classid, []).append(dropout)
            self.pullforward_log.append({
                "classid": classid, "roundid": roundid, "dropout": dropout,
                "dry_run": dry.get("proposal"),
                "applied": applied.get("proposal"),
                "undone_once": bool(ev.get("undo_first") and n == 0),
            })
            ev["applied"] = True
            logger.info("pull-forward applied: class %s dropout racer %s",
                        classid, dropout)

        # When the adjuster squeezes out an emptied heat of the running
        # round it pauses racing (set_racing_state(false)) so the operator
        # confirms the renumbered schedule.  Mirror the operator: resume at
        # the current pointer.
        status = self.api.poll_coordinator()
        ch = status.get("current-heat", {})
        if not ch.get("now_racing"):
            self.api.must(
                self.api.heat_select(roundid=roundid, heat=ch.get("heat"),
                                     now_racing=1),
                "resume racing after pull-forward")
            logger.info("racing resumed after pull-forward (heat %s)",
                        ch.get("heat"))

    # ------------------------------------------------------------------ #
    # round / tournament bookkeeping

    def _verify_round_complete(self, classid, round_seq, roundid) -> None:
        chart = dbread.race_chart(self.tenant, roundid)
        missing = [r for r in chart if r["finishtime"] is None
                   and r["finishplace"] is None and r["racerid"]]
        if missing:
            raise VariantError(
                f"round {round_seq} of class {classid} has "
                f"{len(missing)} unraced chart rows after the heat loop")

    def _await_advancement(self, classid, round_seq) -> None:
        """Round complete: the heat auto-advance path should have invoked
        elimination advancement.  Fall back to the explicit action."""
        deadline = time.monotonic() + self.advance_timeout
        target = round_seq + 1
        while time.monotonic() < deadline:
            t = [t for t in dbread.classes_with_tournaments(self.tenant)
                 if t["classid"] == classid]
            if t and int(t[0]["current_round"]) >= target:
                return
            time.sleep(0.5)
        self.anomalies.append({"type": "advancement_fallback",
                               "classid": classid, "from_round": round_seq})
        logger.warning("auto-advancement did not fire for class %s round %s; "
                       "calling elimination.tournament.advance", classid, round_seq)
        self.api.must(self.api.tournament_advance(classid),
                      f"tournament advance class {classid}")

    # ------------------------------------------------------------------ #

    def oracle(self) -> Oracle:
        return Oracle(self.run_log, self.classes, self.withdrawn)

    def artifact(self, status: str) -> dict:
        expected = None
        try:
            expected = self.oracle().expected()
        except Exception as e:
            self.anomalies.append({"type": "oracle_error", "error": str(e)})
        return {
            "tenant": self.tenant,
            "seed": self.seed,
            "config": self.config_name,
            "mode": self.mode,
            "status": status,
            "plan": self.planner.describe() if self.planner else None,
            "classes": {
                str(c): {k: v for k, v in i.items() if k != "rounds"}
                for c, i in self.classes.items()},
            "run_log": self.run_log,
            "lineups": self.lineups,
            "withdrawn": self.withdrawn,
            "pullforward_log": self.pullforward_log,
            "anomalies": self.anomalies,
            "kiosk": self.kiosk.stats(),
            "timings": self.timings,
            "expected": expected,
        }
