"""Build a local stand-in for the official tenant (local twin only).

The VPS clones st-albert-2026-official; the local twin has no such tenant,
so this seeds one with the same structure: full-size age-group classes and
initialized elimination tournaments.  The result becomes the template source
for `simctl template build --source <slug>`.
"""

import os

from .api import DerbyApi
from .util import find_configs_dir, load_json, make_logger

logger = make_logger("sim.seedlocal")

# expected_racers per age group, matching the official event shape
DEFAULT_SIZES = {"ages_6_8": 73, "ages_9_11": 62, "ages_12_14": 23, "vip": 15}
PINNY_BASE = {"ages_6_8": 100, "ages_9_11": 200, "ages_12_14": 300, "vip": 900}


def seed(slug: str, config_file: str = "soapbox-derby-elimination.json",
         sizes: dict | None = None) -> dict:
    sizes = sizes or DEFAULT_SIZES
    config = load_json(os.path.join(find_configs_dir(), config_file))

    root = DerbyApi(tenant="")
    created = root.tenant_create(slug)
    if not root.ok(created) and \
            created.get("outcome", {}).get("code") != "already-exists":
        raise RuntimeError(f"tenant-create {slug} failed: {created}")

    api = DerbyApi(slug)
    api.login()

    racer_count = 0
    for key, count in sizes.items():
        group = config["age_groups"][key]
        partition = group["name"]
        base = PINNY_BASE.get(key, 500)
        for i in range(1, count + 1):
            payload = api.action(
                "racer.import",
                firstname="Sim", lastname=f"{key.replace('_', '')}-{i:03d}",
                partition=partition, carnumber=base + i)
            api.must(payload, f"racer.import {partition} #{i}")
            racer_count += 1
    logger.info("imported %d racers across %d groups", racer_count, len(sizes))

    # check everyone in (fresh tenant: racerids are 1..N)
    for racerid in range(1, racer_count + 1):
        api.must(api.action("racer.pass", racer=racerid, value=1),
                 f"racer.pass {racerid}")

    # initialize a tournament per class
    listing = api.query("class.list")
    classes = {c["name"]: c["classid"] for c in listing.get("classes", [])}
    initialized = []
    for key in sizes:
        name = config["age_groups"][key]["name"]
        classid = classes.get(name)
        if classid is None:
            raise RuntimeError(f"class {name!r} not found after import: "
                               f"{sorted(classes)}")
        payload = api.action("elimination.tournament.initialize",
                             classid=classid, config_file=config_file,
                             age_group_key=key)
        api.must(payload, f"tournament init {name}")
        initialized.append({"classid": classid, "age_group_key": key,
                            "name": name, "racers": sizes[key]})

    logger.info("seeded tenant %s: %s", slug, initialized)
    return {"slug": slug, "racers": racer_count, "classes": initialized}
