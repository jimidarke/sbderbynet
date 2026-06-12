"""Mock kiosk poller.

Empirical finding (local twin, Phase 0): on the CLOUD stack the race-server
has no derbydb module, so results go via HTTP `action=timer-message`
message=FINISHED — and THAT request is what runs PHP's heat auto-advance
and, on round completion, the elimination advancement engine.  poll.results
itself only reads (it includes autoadvance.inc but never calls
advance_heat).  The kiosk poller is kept anyway: it reproduces race-day
read load and exercises the poll endpoint per heat, and its stats let the
report show the polling cadence the spectator pages will generate.
"""

import threading
import time

from .api import DerbyApi
from .util import make_logger

logger = make_logger("sim.kiosk")


class KioskPoller:
    def __init__(self, tenant: str, interval: float = 0.5):
        self.api = DerbyApi(tenant)
        self.interval = interval
        self.polls = 0
        self.errors = 0
        self._running = False
        self._thread = None

    def start(self) -> None:
        self.api.login()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    def _loop(self) -> None:
        while self._running:
            try:
                self.api.poll_results()
                self.polls += 1
            except Exception as e:  # tolerate transient errors; count them
                self.errors += 1
                logger.debug("poll.results error: %s", e)
            time.sleep(self.interval)

    def stats(self) -> dict:
        return {"polls": self.polls, "errors": self.errors}
