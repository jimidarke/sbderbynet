"""Direct SQLite access to tenant databases.

simctl runs in a container with the derbynet_data volume mounted at
/var/lib/derbynet, so tenant DBs are plain files:
    /var/lib/derbynet/tenants/<slug>/derbynet.sqlite3

Reads open the DB in SQLite read-only mode (mode=ro) so a verifier can never
write.  The pool/tenant tooling in tenantpool.py is the only writer.
"""

import os
import sqlite3
from typing import List

TENANTS_DIR = os.getenv("DERBYNET_TENANTS_DIR", "/var/lib/derbynet/tenants")


def tenant_db_path(slug: str) -> str:
    return os.path.join(TENANTS_DIR, slug, "derbynet.sqlite3")


def connect_ro(slug: str) -> sqlite3.Connection:
    path = tenant_db_path(slug)
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def rows(slug: str, sql: str, params=()) -> List[dict]:
    with connect_ro(slug) as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def one(slug: str, sql: str, params=()):
    result = rows(slug, sql, params)
    return result[0] if result else None


# ---------- canned reads used by the verifier/orchestrator ----------

def classes_with_tournaments(slug: str) -> List[dict]:
    return rows(slug, """
        SELECT et.tournament_id, et.classid, c.class AS class_name,
               et.config_file, et.age_group_key, et.current_round,
               et.total_rounds, et.active
        FROM EliminationTournaments et
        JOIN Classes c ON c.classid = et.classid
        WHERE et.active = 1
        ORDER BY et.classid""")


def rounds_for_class(slug: str, classid: int) -> List[dict]:
    return rows(slug, """
        SELECT roundid, round, roundname, classid
        FROM Rounds WHERE classid = ? ORDER BY round""", (classid,))


def roster_racerids(slug: str, roundid: int) -> List[int]:
    return [r["racerid"] for r in rows(
        slug, "SELECT racerid FROM Roster WHERE roundid = ?", (roundid,))]


def race_chart(slug: str, roundid: int) -> List[dict]:
    return rows(slug, """
        SELECT roundid, heat, lane, racerid, finishtime, finishplace, completed
        FROM RaceChart WHERE roundid = ? ORDER BY heat, lane""", (roundid,))


def advancement_rows(slug: str, tournament_id: int) -> List[dict]:
    return rows(slug, """
        SELECT from_round, to_round, racerid, rank_in_round, score, advanced
        FROM EliminationAdvancement
        WHERE tournament_id = ?
        ORDER BY from_round, rank_in_round, racerid""", (tournament_id,))


def racers(slug: str) -> List[dict]:
    return rows(slug, """
        SELECT racerid, carnumber, classid, passedinspection, exclude
        FROM RegistrationInfo ORDER BY racerid""")


def raceinfo(slug: str) -> dict:
    return {r["itemkey"]: r["itemvalue"]
            for r in rows(slug, "SELECT itemkey, itemvalue FROM RaceInfo")}


def awards_assigned(slug: str) -> List[dict]:
    return rows(slug, """
        SELECT awardid, awardname, awardtypeid, classid, rankid, racerid, sort
        FROM Awards ORDER BY awardid""")
