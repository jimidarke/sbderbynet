#!/usr/bin/env python3
"""simctl — race simulation control CLI.

Runs INSIDE the docker network (local twin or VPS) with the derbynet_data
volume mounted at /var/lib/derbynet.  See deploy/run-on-vps.sh and
deploy/run-local.sh for the container invocations.

Commands:
  doctor                              stack health + guardrail snapshot
  template build [--source SLUG]      snapshot official -> sanitized template
  template verify                     print template fingerprint
  pool init --count N                 provision sim-01..sim-NN
  pool reset (--all | SLUG)           re-copy template over pool tenants
  pool status                         list sim tenants
  run --seed S [--scenario F] [--config std|dropslowest]
      --tenant SLUG [--mode fast|realtime] [--age-groups k1,k2]
      [--out DIR]                     run + verify one variant
  campaign run --plan FILE --pool N [--out DIR]   run a variant matrix
  report --campaign-dir DIR           render aggregate markdown
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib import dbread, tenantpool                       # noqa: E402
from lib.api import DerbyApi                             # noqa: E402
from lib.devices import MqttSession                      # noqa: E402
from lib.orchestrator import VariantRunner               # noqa: E402
from lib.report import render_markdown                   # noqa: E402
from lib.util import (OFFICIAL_TENANT, load_json,        # noqa: E402
                      make_logger, save_json)
from lib.verifier import verify                          # noqa: E402

logger = make_logger("simctl")

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.getenv("SIM_ARTIFACTS_DIR", os.path.join(HERE, "artifacts"))


def scenario_path(name: str) -> str:
    if os.path.exists(name):
        return name
    return os.path.join(HERE, "scenarios", f"{name}.json")


# ---------------------------------------------------------------------- #

def cmd_doctor(args) -> int:
    ok = True

    print("== web app ==")
    try:
        api = DerbyApi(tenant="")
        listing = api.tenant_list()
        slugs = [t.get("slug") for t in listing.get("tenants", [])]
        print(f"  reachable; {len(slugs)} tenants: {slugs}")
        if OFFICIAL_TENANT not in slugs:
            print(f"  WARNING: official tenant {OFFICIAL_TENANT} not listed")
    except Exception as e:
        ok = False
        print(f"  FAIL: {e}")

    print("== tenant login (first sim tenant or official read paths) ==")
    pool = tenantpool.list_pool()
    probe = pool[0] if pool else None
    if probe:
        try:
            api = DerbyApi(probe)
            api.login()
            api.poll_coordinator()
            print(f"  login + poll.coordinator OK on {probe}")
        except Exception as e:
            ok = False
            print(f"  FAIL on {probe}: {e}")
    else:
        print("  no sim tenants yet (run pool init)")

    print("== mqtt ==")
    try:
        session = MqttSession(probe or "doctor")
        session.connect(timeout=8)
        session.publish(session.topic("device", "DOCTOR", "telemetry"),
                        {"hwid": "DOCTOR", "ts": time.time()})
        session.close()
        print("  connect + publish OK")
    except Exception as e:
        ok = False
        print(f"  FAIL: {e}")

    print("== filesystem ==")
    try:
        sha = tenantpool.official_db_sha256()
        print(f"  official DB readable; sha256={sha[:16]}…")
        print(f"  tenants dir: {tenantpool.TENANTS_DIR}")
        print(f"  template: "
              f"{'present' if os.path.exists(tenantpool.TEMPLATE_DB) else 'NOT BUILT'}")
    except Exception as e:
        ok = False
        print(f"  FAIL: {e}")

    print("== stats-gen isolation ==")
    print("  stats-gen reads /var/lib/derbynet/derbynet.sqlite3 (compose-pinned);"
          " sim tenants live under tenants/ and cannot leak to spectator pages.")

    print(f"\ndoctor: {'OK' if ok else 'PROBLEMS FOUND'}")
    return 0 if ok else 1


def cmd_seedlocal(args) -> int:
    from lib import seedlocal
    sizes = None
    if args.small:
        sizes = {"ages_6_8": 8, "ages_9_11": 7, "ages_12_14": 5, "vip": 5}
    result = seedlocal.seed(args.slug, sizes=sizes)
    print(json.dumps(result, indent=2))
    return 0


def cmd_template(args) -> int:
    if args.template_cmd == "build":
        fp = tenantpool.build_template(args.source)
        print(json.dumps(fp, indent=2))
    else:
        print(json.dumps(tenantpool.template_fingerprint(), indent=2))
    return 0


def cmd_pool(args) -> int:
    if args.pool_cmd == "init":
        slugs = tenantpool.init_pool(args.count)
        print(f"pool ready: {slugs}")
    elif args.pool_cmd == "reset":
        targets = tenantpool.list_pool() if args.all else [args.slug]
        for slug in targets:
            tenantpool.reset(slug)
        print(f"reset: {targets}")
    else:
        print(tenantpool.list_pool())
    return 0


def run_one(seed: int, scenario_file: str, config: str, tenant: str,
            mode: str, age_groups, out_dir: str) -> dict:
    scenario = load_json(scenario_path(scenario_file))
    runner = VariantRunner(tenant, seed, scenario, config_name=config,
                           mode=mode, age_groups=age_groups)
    artifact = runner.run()
    verdict = verify(artifact)

    vdir = os.path.join(
        out_dir, f"v{seed:05d}-{scenario.get('name', 'scenario')}-{config}-{mode}")
    save_json(os.path.join(vdir, "artifact.json"), artifact)
    save_json(os.path.join(vdir, "verdict.json"), verdict)
    logger.info("variant seed=%s config=%s -> %s (%s)",
                seed, config, "PASS" if verdict["passed"] else "FAIL", vdir)
    return verdict


def cmd_run(args) -> int:
    age_groups = args.age_groups.split(",") if args.age_groups else None
    verdict = run_one(args.seed, args.scenario, args.config, args.tenant,
                      args.mode, age_groups, args.out)
    print(json.dumps({k: verdict[k] for k in
                      ("seed", "config", "passed", "status")}, indent=2))
    for check in verdict["checks"]:
        mark = "ok " if check["ok"] else "FAIL"
        print(f"  [{mark}] {check['name']}")
        for d in check["details"][:5]:
            print(f"        {d}")
    return 0 if verdict["passed"] else 1


def cmd_campaign(args) -> int:
    plan = load_json(args.plan)
    out_dir = args.out or os.path.join(
        DEFAULT_OUT, f"campaign-{plan.get('name', 'unnamed')}")
    pool = tenantpool.list_pool()
    if args.pool:
        pool = pool[:args.pool]
    if not pool:
        print("no sim tenants; run `simctl pool init --count N` first")
        return 1

    jobs = []
    for block in plan["variants"]:
        seeds = block.get("seeds") or list(
            range(block["seed_start"], block["seed_start"] + block["count"]))
        for seed in seeds:
            for config in block.get("configs", ["std"]):
                jobs.append({"seed": seed,
                             "scenario": block["scenario"],
                             "config": config,
                             "mode": block.get("mode", "fast"),
                             "age_groups": block.get("age_groups")})

    print(f"campaign: {len(jobs)} variants over {len(pool)} tenant(s) "
          f"-> {out_dir}")
    failures = 0
    if len(pool) == 1 or args.serial:
        for i, job in enumerate(jobs):
            tenant = pool[i % len(pool)]
            verdict = run_one(job["seed"], job["scenario"], job["config"],
                              tenant, job["mode"], job["age_groups"], out_dir)
            failures += 0 if verdict["passed"] else 1
    else:
        from concurrent.futures import ThreadPoolExecutor
        def work(item):
            i, job = item
            tenant = pool[i % len(pool)]
            return run_one(job["seed"], job["scenario"], job["config"],
                           tenant, job["mode"], job["age_groups"], out_dir)
        # one in-flight variant per tenant: tenants are the unit of isolation
        with ThreadPoolExecutor(max_workers=len(pool)) as pool_exec:
            # chunk so each tenant runs its own sequential stream
            streams = {t: [] for t in pool}
            for i, job in enumerate(jobs):
                streams[pool[i % len(pool)]].append(job)
            def run_stream(tenant_jobs):
                tenant, jlist = tenant_jobs
                results = []
                for job in jlist:
                    results.append(run_one(
                        job["seed"], job["scenario"], job["config"], tenant,
                        job["mode"], job["age_groups"], out_dir))
                return results
            for results in pool_exec.map(run_stream, streams.items()):
                failures += sum(0 if v["passed"] else 1 for v in results)

    report = render_markdown(out_dir)
    report_path = os.path.join(out_dir, "REPORT.md")
    with open(report_path, "w") as f:
        f.write(report)
    print(f"report: {report_path}")
    print(f"campaign done: {len(jobs) - failures}/{len(jobs)} passed")
    return 0 if failures == 0 else 1


def cmd_report(args) -> int:
    print(render_markdown(args.campaign_dir))
    return 0


# ---------------------------------------------------------------------- #

def main() -> int:
    p = argparse.ArgumentParser(prog="simctl", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor")

    ps = sub.add_parser("seedlocal",
                        help="seed a full-size official-shaped tenant "
                             "(local twin only)")
    ps.add_argument("--slug", default="localseed")
    ps.add_argument("--small", action="store_true",
                    help="tiny roster for quick iteration")

    pt = sub.add_parser("template")
    pt.add_argument("template_cmd", choices=["build", "verify"])
    pt.add_argument("--source", default=OFFICIAL_TENANT)

    pp = sub.add_parser("pool")
    pp.add_argument("pool_cmd", choices=["init", "reset", "status"])
    pp.add_argument("slug", nargs="?")
    pp.add_argument("--count", type=int, default=4)
    pp.add_argument("--all", action="store_true")

    pr = sub.add_parser("run")
    pr.add_argument("--seed", type=int, required=True)
    pr.add_argument("--scenario", default="happy_path")
    pr.add_argument("--config", choices=["std", "dropslowest"], default="std")
    pr.add_argument("--tenant", required=True)
    pr.add_argument("--mode", choices=["fast", "realtime"], default="fast")
    pr.add_argument("--age-groups", help="comma-separated age_group keys")
    pr.add_argument("--out", default=DEFAULT_OUT)

    pc = sub.add_parser("campaign")
    pc.add_argument("campaign_cmd", choices=["run"])
    pc.add_argument("--plan", required=True)
    pc.add_argument("--pool", type=int, help="use first N pool tenants")
    pc.add_argument("--serial", action="store_true")
    pc.add_argument("--out")

    pq = sub.add_parser("report")
    pq.add_argument("--campaign-dir", required=True)

    args = p.parse_args()
    return {
        "doctor": cmd_doctor,
        "seedlocal": cmd_seedlocal,
        "template": cmd_template,
        "pool": cmd_pool,
        "run": cmd_run,
        "campaign": cmd_campaign,
        "report": cmd_report,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
