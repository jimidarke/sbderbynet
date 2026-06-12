"""HTTP client for the DerbyNet PHP app, tenant-aware.

Runs inside the docker network (local twin or VPS) and talks straight to the
web container.  Tenant routing uses the X-DerbyNet-Tenant header gated by
X-DerbyNet-Internal-Token, same as the race-server does — Caddy strips these
from external traffic, which is one of the reasons the simulator runs
on-network.
"""

import os
import re
import time

import requests

from .util import make_logger

logger = make_logger("sim.api")

CONFIG_ROLES_PATH = os.getenv(
    "SIM_CONFIG_ROLES", "/var/lib/derbynet/config-roles.inc")


def discover_role_password(role: str) -> str:
    """Pull a role's password out of the deployed config-roles.inc.

    The file is PHP, but the shape is stable:
        'RaceCoordinator' => array('password' => 'secret',
    Never logged; never persisted in artifacts.
    """
    override = os.getenv("SIM_ROLE_PASS")
    if override is not None and os.getenv("SIM_ROLE_USER", role) == role:
        return override
    try:
        with open(CONFIG_ROLES_PATH) as f:
            text = f.read()
    except OSError:
        return ""
    m = re.search(
        r"'" + re.escape(role) + r"'\s*=>\s*array\s*\(\s*'password'\s*=>\s*'([^']*)'",
        text)
    return m.group(1) if m else ""


class DerbyApi:
    def __init__(self, tenant: str, base_url: str | None = None):
        self.tenant = tenant
        self.base_url = (base_url or os.getenv(
            "DERBYNET_API_BASE", "http://derbynet-web")).rstrip("/")
        self.session = requests.Session()
        token = os.getenv("DERBYNET_INTERNAL_TOKEN", "")
        if tenant:
            self.session.headers["X-DerbyNet-Tenant"] = tenant
            if token:
                self.session.headers["X-DerbyNet-Internal-Token"] = token

    # ---------- plumbing ----------

    def action(self, _action: str, timeout: float = 15, **params) -> dict:
        data = {"action": _action}
        data.update({k: v for k, v in params.items() if v is not None})
        r = self.session.post(f"{self.base_url}/action.php", data=data,
                              timeout=timeout)
        r.raise_for_status()
        return self._json(r, f"action={_action}")

    def query(self, _query: str, timeout: float = 15, **params) -> dict:
        q = {"query": _query}
        q.update({k: v for k, v in params.items() if v is not None})
        r = self.session.get(f"{self.base_url}/action.php", params=q,
                             timeout=timeout)
        r.raise_for_status()
        return self._json(r, f"query={_query}")

    @staticmethod
    def _json(response, what: str) -> dict:
        try:
            return response.json()
        except ValueError:
            snippet = response.text[:400]
            raise RuntimeError(f"Non-JSON response for {what}: {snippet}")

    @staticmethod
    def ok(payload: dict) -> bool:
        outcome = payload.get("outcome", {})
        return outcome.get("summary") == "success" or payload.get("success") is True

    def must(self, payload: dict, what: str) -> dict:
        if not self.ok(payload):
            raise RuntimeError(f"{what} failed: {payload}")
        return payload

    # ---------- auth ----------

    def login(self, role: str | None = None, password: str | None = None) -> None:
        role = role or os.getenv("SIM_ROLE_USER", "RaceCoordinator")
        if password is None:
            password = discover_role_password(role)
        payload = self.action("role.login", name=role, password=password)
        if not self.ok(payload):
            # A stack with no config-roles.inc deployed (fresh local twin)
            # grants the anonymous role full permissions, so a failed login
            # is fine as long as actions actually work.  Probe with a
            # harmless query and continue if it succeeds.
            if not os.path.exists(CONFIG_ROLES_PATH):
                self.query("tenant-list.nodata")
                logger.warning(
                    "no %s and role.login failed; relying on anonymous "
                    "full-permission fallback (local twin)", CONFIG_ROLES_PATH)
                return
            raise RuntimeError(
                f"login as {role} (tenant {self.tenant}) failed: {payload}")
        logger.info("logged in as %s on tenant %s", role, self.tenant)

    def tenant_select(self, slug: str) -> dict:
        return self.action("tenant-select.nodata", slug=slug)

    # ---------- tenant management (slug-less actions run un-tenanted) ----------

    def tenant_create(self, slug: str) -> dict:
        return self.action("tenant-create.nodata", slug=slug)

    def tenant_list(self) -> dict:
        return self.query("tenant-list.nodata")

    # ---------- race flow ----------

    def poll_coordinator(self, **params) -> dict:
        return self.query("poll.coordinator", **params)

    def poll_results(self, roundid=None) -> dict:
        return self.query("poll.results", roundid=roundid)

    def heat_select(self, roundid=None, heat=None, now_racing=None) -> dict:
        return self.action("heat.select", roundid=roundid, heat=heat,
                           now_racing=now_racing)

    def schedule_generate(self, roundid: int) -> dict:
        return self.action("schedule.generate", roundid=roundid, timeout=120)

    def racer_dnf(self, racerid: int, roundid: int, heat: int) -> dict:
        return self.action("racer.dnf", racerid=racerid, roundid=roundid,
                           heat=heat)

    def pull_forward(self, roundid: int, dropout_racerid: int,
                     dry_run: bool = False) -> dict:
        params = {"roundid": roundid, "dropout_racerid": dropout_racerid}
        if dry_run:
            params["dry-run"] = 1
        return self.action("schedule.pullforward", **params)

    def pull_forward_undo(self, roundid: int) -> dict:
        return self.action("schedule.pullforward.undo", roundid=roundid)

    def tournament_advance(self, classid: int, force: bool = False) -> dict:
        return self.action("elimination.tournament.advance", classid=classid,
                           force=1 if force else None)

    def tournament_status(self, classid: int) -> dict:
        return self.query("elimination.tournament.status", classid=classid)

    def award_list(self) -> dict:
        return self.query("award.list", adhoc=1)

    # ---------- waiting ----------

    def wait_for(self, predicate, timeout: float, interval: float = 0.4,
                 what: str = "condition"):
        """Poll poll.coordinator until predicate(payload) is truthy."""
        deadline = time.monotonic() + timeout
        last = None
        while time.monotonic() < deadline:
            last = self.poll_coordinator()
            result = predicate(last)
            if result:
                return result
            time.sleep(interval)
        raise TimeoutError(f"timed out after {timeout}s waiting for {what}; "
                           f"last current-heat={last.get('current-heat') if last else None}")
