"""Sim tenant template + pool management.

Template build snapshots the official tenant READ-ONLY via the SQLite backup
API, then sanitizes the copy into a clean pre-race state.  Pool tenants
(sim-01, sim-02, ...) are provisioned on the filesystem exactly the way
cloud-tenant.inc lays them out (DB file + media subdirs); PHP discovers
tenants by directory, so no API call is needed.

GUARDRAILS: every mutating entry point refuses any slug that is not
^sim-\\d+$, and nothing here ever opens the official DB writable.
"""

import os
import re
import shutil
import sqlite3
import stat
from typing import List

from .util import OFFICIAL_TENANT, TENANT_SLUG_RE, make_logger
from . import dbread

logger = make_logger("sim.tenantpool")

TENANTS_DIR = dbread.TENANTS_DIR
TEMPLATE_DIR = os.getenv("SIM_TEMPLATE_DIR", "/var/lib/derbynet/sim-template")
TEMPLATE_DB = os.path.join(TEMPLATE_DIR, "derbynet.sqlite3")
MEDIA_SUBDIRS = ("racers", "cars", "videos", "logs", "imagery", "slides")
TENANT_MAX = 50

SANITIZE_SQL = """
-- strip all race results and schedules: each variant schedules fresh
DELETE FROM RaceChart;
DELETE FROM EliminationAdvancement;
UPDATE EliminationTournaments SET current_round = 1 WHERE active = 1;
-- keep only round-1 rosters (later rounds are repopulated by advancement)
DELETE FROM Roster WHERE roundid NOT IN
    (SELECT roundid FROM Rounds WHERE round = 1);
-- clear the live heat pointer / racing state
DELETE FROM RaceInfo WHERE itemkey IN
    ('ClassID', 'RoundID', 'Heat', 'NowRacingState',
     'last-heat-roundid', 'last-heat-heat', 'last-heat-status');
-- everyone is checked in and racing
UPDATE RegistrationInfo SET passedinspection = 1, exclude = 0;
"""


def _assert_sim_slug(slug: str) -> None:
    if not re.match(TENANT_SLUG_RE, slug):
        raise ValueError(
            f"refusing to touch tenant '{slug}': only sim-NN tenants may be "
            f"created/reset/deleted by the simulator")


def official_db_path() -> str:
    return dbread.tenant_db_path(OFFICIAL_TENANT)


def official_db_sha256() -> str:
    import hashlib
    h = hashlib.sha256()
    with open(official_db_path(), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------- #
# Template

def build_template(source_slug: str = OFFICIAL_TENANT) -> dict:
    """Snapshot source tenant -> sanitized template.  Source is opened
    read-only; the backup API is safe against concurrent writers."""
    os.makedirs(TEMPLATE_DIR, exist_ok=True)
    src_path = dbread.tenant_db_path(source_slug)

    src = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True, timeout=30)
    try:
        if os.path.exists(TEMPLATE_DB):
            os.unlink(TEMPLATE_DB)
        dst = sqlite3.connect(TEMPLATE_DB)
        with dst:
            src.backup(dst)
        dst.executescript(SANITIZE_SQL)
        dst.commit()
        dst.execute("VACUUM")
        dst.close()
    finally:
        src.close()

    _match_ownership(TEMPLATE_DB, src_path)
    fp = template_fingerprint()
    logger.info("template built from %s: %s", source_slug, fp)
    return fp


def template_fingerprint() -> dict:
    conn = sqlite3.connect(f"file:{TEMPLATE_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        classes = [dict(r) for r in conn.execute("""
            SELECT c.classid, c.class, et.age_group_key, et.config_file,
                   COUNT(ri.racerid) AS racer_count
            FROM Classes c
            LEFT JOIN EliminationTournaments et
                   ON et.classid = c.classid AND et.active = 1
            LEFT JOIN RegistrationInfo ri ON ri.classid = c.classid
            GROUP BY c.classid ORDER BY c.classid""")]
        chart = conn.execute("SELECT COUNT(*) FROM RaceChart").fetchone()[0]
        adv = conn.execute(
            "SELECT COUNT(*) FROM EliminationAdvancement").fetchone()[0]
        return {"classes": classes, "racechart_rows": chart,
                "advancement_rows": adv,
                "size_bytes": os.path.getsize(TEMPLATE_DB)}
    finally:
        conn.close()


# ---------------------------------------------------------------------- #
# Pool

def _match_ownership(path: str, reference: str) -> None:
    """Make the file/dir usable by the web container (match the official
    tenant's uid/gid when we're running as root; best-effort otherwise).
    Locally there is no official tenant — fall back to the tenants dir."""
    if not os.path.exists(reference):
        reference = TENANTS_DIR if os.path.isdir(TENANTS_DIR) else None
        if reference is None:
            return
    try:
        ref = os.stat(reference)
        os.chown(path, ref.st_uid, ref.st_gid)
        os.chmod(path, stat.S_IMODE(ref.st_mode) or 0o664)
    except PermissionError:
        pass


def pool_slugs(count: int) -> List[str]:
    return [f"sim-{i:02d}" for i in range(1, count + 1)]


def list_pool() -> List[str]:
    if not os.path.isdir(TENANTS_DIR):
        return []
    return sorted(d for d in os.listdir(TENANTS_DIR)
                  if re.match(TENANT_SLUG_RE, d))


def init_pool(count: int) -> List[str]:
    existing_total = len([d for d in os.listdir(TENANTS_DIR)
                          if os.path.isdir(os.path.join(TENANTS_DIR, d))])
    slugs = pool_slugs(count)
    new = [s for s in slugs if not os.path.isdir(os.path.join(TENANTS_DIR, s))]
    if existing_total + len(new) > TENANT_MAX:
        raise RuntimeError(
            f"pool of {count} would exceed the {TENANT_MAX}-tenant cap "
            f"({existing_total} tenants exist)")
    for slug in slugs:
        provision(slug)
    return slugs


def provision(slug: str) -> None:
    _assert_sim_slug(slug)
    tenant_dir = os.path.join(TENANTS_DIR, slug)
    ref_dir = os.path.join(TENANTS_DIR, OFFICIAL_TENANT)
    os.makedirs(tenant_dir, exist_ok=True)
    _match_ownership(tenant_dir, ref_dir)
    for sub in MEDIA_SUBDIRS:
        subdir = os.path.join(tenant_dir, sub)
        os.makedirs(subdir, exist_ok=True)
        _match_ownership(subdir, ref_dir)
    reset(slug)


def reset(slug: str) -> None:
    """Re-copy the sanitized template over the tenant DB."""
    _assert_sim_slug(slug)
    if not os.path.exists(TEMPLATE_DB):
        raise RuntimeError("no template built; run `simctl template build` first")
    db_path = dbread.tenant_db_path(slug)
    # Remove stale WAL/SHM so the new file isn't mixed with old journal state.
    for suffix in ("", "-wal", "-shm"):
        p = db_path + suffix
        if os.path.exists(p):
            os.unlink(p)
    shutil.copyfile(TEMPLATE_DB, db_path)
    _match_ownership(db_path, official_db_path())
    logger.info("tenant %s reset from template", slug)


def set_tournament_config(slug: str, config_file: str) -> None:
    """Point every active tournament in a sim tenant at a different
    elimination config (e.g. the drop-slowest variant)."""
    _assert_sim_slug(slug)
    conn = sqlite3.connect(dbread.tenant_db_path(slug), timeout=10)
    try:
        with conn:
            conn.execute(
                "UPDATE EliminationTournaments SET config_file = ? "
                "WHERE active = 1", (config_file,))
    finally:
        conn.close()


def delete(slug: str) -> None:
    _assert_sim_slug(slug)
    tenant_dir = os.path.join(TENANTS_DIR, slug)
    if os.path.isdir(tenant_dir):
        shutil.rmtree(tenant_dir)
        logger.info("tenant %s deleted", slug)
