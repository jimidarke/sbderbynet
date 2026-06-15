#!/usr/bin/env python3
"""test-derbydb-cloud-push.py — Unit test for derbydb.DerbyDatabase.request_cloud_push.

Exercises the REAL method (not a copy) for the three behaviours the race server
depends on:
  1. no-op when the trigger file is absent (non-Pi host) — never raises;
  2. fires os.utime(trigger, None) when the file is present;
  3. swallows OSError (e.g. read-only fs) — never propagates into the caller.

The method is intentionally self-contained (touches a tmpfs flag, never the DB),
so we bypass DerbyDatabase.__init__ (which would open a real DB) and call the
bound method directly. Run from anywhere:

    python3 testing/test-derbydb-cloud-push.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "extras", "soapbox", "infra", "server"))

import derbydb  # noqa: E402

TRIGGER = "/run/derbynet-cloud-sync.trigger"
passed = failed = 0


def ok(msg):
    global passed
    passed += 1
    print(f"  PASS: {msg}")


def bad(msg):
    global failed
    failed += 1
    print(f"  FAIL: {msg}")


d = object.__new__(derbydb.DerbyDatabase)  # skip __init__ (needs a live DB/logger)
real_exists, real_utime = os.path.exists, os.utime

# 1. Absent trigger → no-op, no raise.
os.path.exists = lambda p: False
try:
    d.request_cloud_push()
    ok("no-op when trigger absent (no raise)")
except Exception as e:  # noqa: BLE001
    bad(f"raised when absent: {e}")
finally:
    os.path.exists = real_exists

# 2. Present trigger → os.utime(trigger, None) called exactly once.
calls = []
os.path.exists = lambda p: True
os.utime = lambda p, t: calls.append((p, t))
try:
    d.request_cloud_push()
finally:
    os.path.exists, os.utime = real_exists, real_utime
if calls == [(TRIGGER, None)]:
    ok("fires os.utime(trigger, None) when present")
else:
    bad(f"unexpected utime calls: {calls}")

# 3. utime raises OSError → swallowed, never propagates.
os.path.exists = lambda p: True


def _boom(p, t):
    raise OSError("read-only file system")


os.utime = _boom
try:
    d.request_cloud_push()
    ok("swallows OSError (never raises into caller)")
except Exception as e:  # noqa: BLE001
    bad(f"propagated OSError: {e}")
finally:
    os.path.exists, os.utime = real_exists, real_utime

print(f"\nderbydb request_cloud_push: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
