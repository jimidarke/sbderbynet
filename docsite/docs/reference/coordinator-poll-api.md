# Coordinator Poll API

The endpoint the coordinator UI polls every second. Read-only, unauthenticated. JSON response describes the current heat, racers, timer health, replay state, classes, and rounds.

## Endpoint

```
GET http://<server>/derbynet/action.php?query=poll.coordinator
```

Optional parameters:

- `roundid` + `heat` — heat-specific results
- `_=<timestamp>` — cache-buster

Common headers:

```
Accept: */*
X-Requested-With: XMLHttpRequest
```

## Sample request

```bash
curl -s 'http://192.168.100.10/derbynet/action.php?query=poll.coordinator' \
     -H 'Accept: */*' \
     -H 'X-Requested-With: XMLHttpRequest'
```

---

## Response shape

### `current-heat`

```json
{
  "now_racing": true,
  "use_master_sched": false,
  "use_points": false,
  "classid": 1,
  "roundid": 6,
  "round": 1,
  "tbodyid": 6,
  "heat": 2,
  "number-of-heats": 3,
  "class": ""
}
```

### `racers` (array)

```json
{
  "lane": 1,
  "racerid": 11,
  "name": "Quinton Gaines",
  "carname": "",
  "carnumber": 11,
  "note": "",
  "photo": "",
  "finishtime": "",
  "finishplace": ""
}
```

### `timer-state`

```json
{
  "lanes": 3,
  "last-contact": 1765325539,
  "state": 7,
  "icon": "img/status/unknown.png",
  "remote-start": false,
  "message": "UNCONFIRMED",
  "timers": [
    {
      "lane": 1,
      "timerID": "L1",
      "last_heartbeat": 1765325539,
      "ready": false,
      "is_starter": false,
      "is_online": true,
      "seconds_ago": 1
    }
  ],
  "server_time": 1765325540,
  "timers_online": 3,
  "timers_ready": 0,
  "timers_required": 3,
  "health_status": "warning",
  "health_message": "Some timers not ready (0/3)"
}
```

**`message`**: `CONNECTED` / `Staging` / `Race` / `UNCONFIGURED` / `UNCONFIRMED`.

**`health_status`** (see [Race State Engine](../architecture/race-state-engine.md)):

- `healthy` — all timers online and ready
- `degraded` — some offline, not racing
- `warning` — some not ready during active race
- `critical` — insufficient timers online during active race

### `replay-state`

```json
{
  "last_contact": 0,
  "state": 1,
  "icon": "img/status/not_connected.png",
  "connected": false,
  "message": "NOT CONNECTED"
}
```

### `heat-results` (array, possibly empty)

```json
{ "lane": 1, "time": "3.456", "place": 1 }
```

### `classes` (array)

```json
{
  "classid": 1,
  "count": 12,
  "nrounds": 4,
  "ntrophies": -1,
  "name": "Ages 6-8",
  "subgroups": [{ "rankid": 1, "count": 12, "name": "Ages 6-8" }]
}
```

### `rounds` (array)

```json
{
  "roundid": 6,
  "classid": 1,
  "class": "Ages 6-8",
  "round": "4 Finals",
  "aggregate": false,
  "roster_size": 3,
  "passed": 3,
  "registered": 3,
  "unscheduled": 0,
  "adjustments": [],
  "heats_scheduled": 3,
  "heats_run": 1,
  "name": "Ages 6-8, 4 Finals",
  "roundname": "Ages 6-8, 4 Finals",
  "next-round": true
}
```

### Misc

```json
{
  "last-heat": "available",
  "refused-results": 0,
  "current-scene": 4,
  "ready-aggregate": [],
  "race-integrity": { "status": "ok", "code": "ok", "message": "" }
}
```

---

## Polling

- Polled every **1 s** by the coordinator UI:
  ```js
  setInterval(coordinator_poll, 1000);
  ```
- Use a `pollPending` flag to avoid overlapping requests.

```js
let pollPending = false;
function poll() {
  if (pollPending) return;
  pollPending = true;
  fetch('action.php?query=poll.coordinator')
    .then(r => r.json())
    .finally(() => { pollPending = false; });
}
```

---

## Authentication

`query=poll.coordinator` is **read-only and does not require auth**. To act on the system (write results, change heats), log in:

```
POST /derbynet/action.php
Content-Type: application/x-www-form-urlencoded

action=role.login&name=RaceCoordinator&password=<pw>
```

Success:

```json
{ "outcome": { "summary": "success", "code": "success", "description": "" }, "role": "RaceCoordinator" }
```

DerbyNet uses PHP sessions (`PHPSESSID` cookie). With curl: `-c cookies.txt` to save, `-b cookies.txt` to send.

To log out: post `role.login` with empty `name` and `password`.

Roles are configured in `local/config-roles.inc`. Common: `RaceCoordinator`, `Timer`, `RaceCrew`.

| Action | Auth required |
|---|---|
| `query=poll.coordinator` | no |
| `query=poll.now-racing` | no |
| `action=result.write` | yes |
| `action=heat.select` | yes |
| `action=schedule.generate` | yes |

---

## Python example

```python
import requests, time

BASE = "http://192.168.100.10/derbynet/action.php"
session = requests.Session()

def login(role, password):
    r = session.post(BASE, data={
        "action": "role.login", "name": role, "password": password
    }, headers={"X-Requested-With": "XMLHttpRequest"})
    return r.json().get("outcome", {}).get("summary") == "success"

def poll(roundid=None, heat=None):
    params = {"query": "poll.coordinator"}
    if roundid: params["roundid"] = roundid
    if heat: params["heat"] = heat
    return session.get(BASE, params=params,
        headers={"X-Requested-With": "XMLHttpRequest"}).json()

while True:
    d = poll()
    ch = d["current-heat"]
    print(f"Heat {ch['heat']}/{ch['number-of-heats']}  "
          f"timer={d['timer-state']['message']} "
          f"({d['timer-state']['health_status']})")
    time.sleep(2)
```

---

## Related endpoints

| Endpoint | Purpose |
|---|---|
| `query=poll.coordinator` | full coordinator status |
| `query=poll.now-racing` | simplified status for now-racing displays |
| `action=role.login` | establish session |
| `action=result.write` | submit results (auth) |
| `action=heat.select` | change current heat (auth) |

All times are Unix seconds. Finish times are formatted decimal strings (e.g. `"3.4567"`).
