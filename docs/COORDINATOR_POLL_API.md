# Coordinator Poll API Documentation

This document explains how to poll for production race status using the DerbyNet coordinator polling endpoint.

## Endpoint

```
GET http://<server>/derbynet/action.php?query=poll.coordinator
```

## Basic Usage

### Minimal Request

```bash
curl -s 'http://192.168.100.10/derbynet/action.php?query=poll.coordinator' \
  -H 'Accept: */*' \
  -H 'X-Requested-With: XMLHttpRequest' \
  --insecure
```

### With Current Heat Context

Pass `roundid` and `heat` parameters to get heat-specific results (e.g., to see results from a specific heat):

```bash
curl -s 'http://192.168.100.10/derbynet/action.php?query=poll.coordinator&roundid=6&heat=2' \
  -H 'Accept: */*' \
  -H 'X-Requested-With: XMLHttpRequest' \
  --insecure
```

### Cache-Busting Request

For real-time polling, add a timestamp parameter to prevent caching:

```bash
curl -s "http://192.168.100.10/derbynet/action.php?query=poll.coordinator&_=$(date +%s)000" \
  -H 'Accept: */*' \
  -H 'Cache-Control: no-cache' \
  -H 'Pragma: no-cache' \
  -H 'X-Requested-With: XMLHttpRequest' \
  --insecure
```

## Response Structure

The endpoint returns a JSON object with the following top-level keys:

### `current-heat`

Information about the currently active heat:

```json
{
  "current-heat": {
    "now_racing": true,           // Whether racing mode is active
    "use_master_sched": false,    // Whether using interleaved master schedule
    "use_points": false,          // Whether racing by points (vs times)
    "classid": 1,                 // Current class ID
    "roundid": 6,                 // Current round ID
    "round": 1,                   // Round number within the class
    "tbodyid": 6,                 // Table body ID for UI grouping
    "heat": 2,                    // Current heat number
    "number-of-heats": 3,         // Total heats in this round
    "class": ""                   // Class name (if using groups)
  }
}
```

### `racers`

Array of racers in the current heat:

```json
{
  "racers": [
    {
      "lane": 1,                  // Lane number (1-indexed)
      "racerid": 11,              // Unique racer ID
      "name": "Quinton Gaines",   // Racer's full name
      "carname": "",              // Optional car name
      "carnumber": 11,            // Car number
      "note": "",                 // Optional note
      "photo": "",                // Photo URL (if configured)
      "finishtime": "",           // Finish time (empty if not finished)
      "finishplace": ""           // Finish place (empty if not finished)
    }
  ]
}
```

> **Bye lanes:** `racers` contains only the **populated** lanes for the heat.
> An empty "bye" lane (from a pull-forward withdrawal or an odd racer count) has
> no `RaceChart` row, so it is **absent** from this array — the lane numbers are
> not guaranteed contiguous (e.g. a middle bye yields lanes `[1, 3]`). Consumers
> that drive a per-lane display must NOT infer the track's lane count from
> `racers.length`; use `race_info.lane_count` (below) for the physical count and
> blank any lane not present in `racers`.

### `race_info`

Track-level configuration. Added so the race server can publish a pinny to every
**physical** lane each heat (blanking bye lanes with `"----"`) and count only
populated lanes for race completion.

```json
{
  "race_info": {
    "lane_count": 3             // Physical lanes on the track (RaceInfo.lane_count)
  }
}
```

### `timer-state`

Status of the timer hardware and system health:

```json
{
  "timer-state": {
    "lanes": 3,                           // Number of racing lanes
    "last-contact": 1765325539,           // Unix timestamp of last timer contact
    "state": 7,                           // Internal timer state code
    "icon": "img/status/unknown.png",     // Status icon path
    "remote-start": false,                // Whether remote start is enabled
    "message": "UNCONFIRMED",             // Human-readable status message
    "timers": [                           // Array of individual timer statuses
      {
        "lane": 1,                        // Lane number (0 = start timer)
        "timerID": "L1",                  // Timer identifier
        "last_heartbeat": 1765325539,     // Unix timestamp of last heartbeat
        "ready": false,                   // Whether timer is ready to race
        "is_starter": false,              // True if this is the start gate timer
        "is_online": true,                // Whether timer is online
        "seconds_ago": 1                  // Seconds since last heartbeat
      }
    ],
    "server_time": 1765325540,            // Current server time (Unix timestamp)
    "timers_online": 3,                   // Count of online finish timers
    "timers_ready": 0,                    // Count of ready finish timers
    "timers_required": 3,                 // Minimum timers required for racing
    "health_status": "warning",           // Overall health: healthy|degraded|warning|critical
    "health_message": "Some timers not ready (0/3)"  // Health status description
  }
}
```

**Timer State Messages:**
- `CONNECTED` - Timer system ready
- `Staging` - Preparing for race start
- `Race` - Race in progress
- `UNCONFIGURED` - Timer not configured
- `UNCONFIRMED` - Timer state unknown

**Health Status Values:**
- `healthy` - All systems operational
- `degraded` - Some timers offline (not racing)
- `warning` - Some timers not ready during active race
- `critical` - Insufficient timers online during active race

### `replay-state`

Status of the replay camera system:

```json
{
  "replay-state": {
    "last_contact": 0,                    // Unix timestamp of last contact
    "state": 1,                           // Replay state code
    "icon": "img/status/not_connected.png", // Status icon
    "connected": false,                   // Whether replay is connected
    "message": "NOT CONNECTED"            // Status message
  }
}
```

### `heat-results`

Array of results from the previous/specified heat (empty if no results):

```json
{
  "heat-results": [
    {
      "lane": 1,
      "time": "3.456",           // Finish time
      "place": 1                  // Finish place
    }
  ]
}
```

### `classes`

Array of all racing classes:

```json
{
  "classes": [
    {
      "classid": 1,
      "count": 12,                // Number of racers
      "nrounds": 4,               // Number of rounds
      "ntrophies": -1,            // Number of trophies (-1 = default)
      "name": "Ages 6-8",
      "subgroups": [              // Subgroup breakdown
        {
          "rankid": 1,
          "count": 12,
          "name": "Ages 6-8"
        }
      ]
    }
  ]
}
```

### `rounds`

Array of all rounds with progress information:

```json
{
  "rounds": [
    {
      "roundid": 6,
      "classid": 1,
      "class": "Ages 6-8",
      "round": "4 Finals",
      "aggregate": false,           // Whether this is an aggregate round
      "roster_size": 3,             // Total racers in roster
      "passed": 3,                  // Racers who passed inspection
      "registered": 3,              // Racers registered
      "unscheduled": 0,             // Racers not yet scheduled
      "adjustments": [],            // Schedule adjustments needed
      "heats_scheduled": 3,         // Total heats scheduled
      "heats_run": 1,               // Heats completed
      "name": "Ages 6-8, 4 Finals",
      "roundname": "Ages 6-8, 4 Finals",
      "next-round": true            // Present if this is the next round in playlist
    }
  ]
}
```

### Other Fields

```json
{
  "last-heat": "available",       // Status: "available", "recoverable", "none"
  "refused-results": 0,           // Count of rejected timer results
  "current-scene": 4,             // Current display scene ID
  "ready-aggregate": [],          // Aggregate classes ready to populate
  "race-integrity": {             // Race state integrity check
    "status": "ok",               // "ok", "warn", or "error"
    "code": "ok",
    "message": ""
  }
}
```

## Polling Best Practices

### 1. Recommended Polling Interval

The coordinator page polls every **1 second** for real-time updates:

```javascript
setInterval(coordinator_poll, 1000);
```

### 2. Prevent Concurrent Requests

Use a flag to avoid overlapping requests:

```javascript
let pollPending = false;

function poll() {
  if (pollPending) return;
  pollPending = true;

  fetch('action.php?query=poll.coordinator')
    .then(response => response.json())
    .then(data => {
      // Process data
    })
    .finally(() => {
      pollPending = false;
    });
}
```

### 3. Handle Session

If using features that require authentication, include the session cookie:

```bash
curl -s 'http://192.168.100.10/derbynet/action.php?query=poll.coordinator' \
  -H 'Accept: */*' \
  -H 'X-Requested-With: XMLHttpRequest' \
  -b 'PHPSESSID=your_session_id' \
  --insecure
```

## Example Python Script

```python
import requests
import time
import json

DERBYNET_URL = "http://192.168.100.10/derbynet/action.php"

def poll_coordinator(roundid=None, heat=None):
    """Poll the coordinator endpoint for current race status."""
    params = {"query": "poll.coordinator"}
    if roundid:
        params["roundid"] = roundid
    if heat:
        params["heat"] = heat

    response = requests.get(
        DERBYNET_URL,
        params=params,
        headers={
            "Accept": "*/*",
            "X-Requested-With": "XMLHttpRequest"
        },
        verify=False  # Skip SSL verification for local network
    )
    return response.json()

def main():
    """Continuously poll and display race status."""
    while True:
        try:
            data = poll_coordinator()

            current = data.get("current-heat", {})
            print(f"\n--- Race Status ---")
            print(f"Racing: {current.get('now_racing', False)}")
            print(f"Round: {current.get('roundid')} Heat: {current.get('heat')}/{current.get('number-of-heats')}")

            racers = data.get("racers", [])
            print(f"\nRacers in current heat:")
            for r in racers:
                result = r.get('finishtime') or r.get('finishplace') or '-'
                print(f"  Lane {r['lane']}: #{r['carnumber']} {r['name']} - {result}")

            timer = data.get("timer-state", {})
            print(f"\nTimer: {timer.get('message')} ({timer.get('health_status')})")

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(2)

if __name__ == "__main__":
    main()
```

## Example Bash Monitoring Script

```bash
#!/bin/bash

DERBYNET_URL="http://192.168.100.10/derbynet/action.php"

while true; do
    clear
    echo "=== DerbyNet Race Status ==="
    echo ""

    response=$(curl -s "${DERBYNET_URL}?query=poll.coordinator" \
        -H 'Accept: */*' \
        -H 'X-Requested-With: XMLHttpRequest' \
        --insecure)

    # Extract key fields using jq
    now_racing=$(echo "$response" | jq -r '.["current-heat"].now_racing')
    roundid=$(echo "$response" | jq -r '.["current-heat"].roundid')
    heat=$(echo "$response" | jq -r '.["current-heat"].heat')
    max_heat=$(echo "$response" | jq -r '.["current-heat"]["number-of-heats"]')
    timer_msg=$(echo "$response" | jq -r '.["timer-state"].message')
    health=$(echo "$response" | jq -r '.["timer-state"].health_status')

    echo "Racing Mode: $now_racing"
    echo "Round: $roundid | Heat: $heat of $max_heat"
    echo "Timer: $timer_msg ($health)"
    echo ""
    echo "Racers:"
    echo "$response" | jq -r '.racers[] | "  Lane \(.lane): #\(.carnumber) \(.name) - \(.finishtime // .finishplace // "-")"'

    sleep 2
done
```

## Authentication

The coordinator poll endpoint (`query=poll.coordinator`) is read-only and **does not require authentication**. However, if you need to perform actions (like writing results or selecting heats), you must first authenticate.

### How Sessions Work

DerbyNet uses PHP sessions with the `PHPSESSID` cookie. When you log in:
1. The server creates a session and stores `role` and `permissions`
2. The session ID is returned as a cookie
3. Subsequent requests with that cookie have access to authenticated features

### Login Endpoint

```
POST http://<server>/derbynet/action.php
Content-Type: application/x-www-form-urlencoded

action=role.login&name=<role>&password=<password>
```

**Parameters:**
- `action`: Must be `role.login`
- `name`: The role name (e.g., "RaceCoordinator", "Timer", etc.)
- `password`: The password for that role

**Success Response:**
```json
{
  "action": {"action": "role.login", "name": "RaceCoordinator", "password": "..."},
  "outcome": {"summary": "success", "code": "success", "description": ""},
  "timecheck": "2025-06-12T14:30:00-0500",
  "role": "RaceCoordinator"
}
```

**Failure Response:**
```json
{
  "action": {"action": "role.login", "name": "RaceCoordinator", "password": "..."},
  "outcome": {"summary": "failure", "code": "login", "description": "Incorrect password"}
}
```

### Login Example with curl

```bash
# Login and save the session cookie
curl -s 'http://192.168.100.10/derbynet/action.php' \
  -X POST \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -H 'X-Requested-With: XMLHttpRequest' \
  -d 'action=role.login&name=RaceCoordinator&password=your_password' \
  -c /tmp/derbynet_cookies.txt \
  --insecure

# Use the session for subsequent requests
curl -s 'http://192.168.100.10/derbynet/action.php?query=poll.coordinator' \
  -H 'Accept: */*' \
  -H 'X-Requested-With: XMLHttpRequest' \
  -b /tmp/derbynet_cookies.txt \
  --insecure
```

### Login Example with Python

```python
import requests

DERBYNET_URL = "http://192.168.100.10/derbynet/action.php"

# Create a session to persist cookies
session = requests.Session()

def login(role, password):
    """Authenticate with DerbyNet and establish a session."""
    response = session.post(
        DERBYNET_URL,
        data={
            "action": "role.login",
            "name": role,
            "password": password
        },
        headers={"X-Requested-With": "XMLHttpRequest"},
        verify=False
    )
    result = response.json()
    if result.get("outcome", {}).get("summary") == "success":
        print(f"Logged in as: {result.get('role')}")
        return True
    else:
        print(f"Login failed: {result.get('outcome', {}).get('description')}")
        return False

def poll_coordinator():
    """Poll coordinator using the authenticated session."""
    response = session.get(
        DERBYNET_URL,
        params={"query": "poll.coordinator"},
        headers={
            "Accept": "*/*",
            "X-Requested-With": "XMLHttpRequest"
        },
        verify=False
    )
    return response.json()

# Usage
if login("RaceCoordinator", "your_password"):
    data = poll_coordinator()
    print(data)
```

### Logout

To log out, call the login endpoint with empty credentials:

```bash
curl -s 'http://192.168.100.10/derbynet/action.php' \
  -X POST \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -H 'X-Requested-With: XMLHttpRequest' \
  -d 'action=role.login&name=&password=' \
  -b /tmp/derbynet_cookies.txt \
  --insecure
```

### Available Roles

Roles are configured in `local/config-roles.inc` on the server. Common roles include:
- **RaceCoordinator** - Full access to manage races
- **Timer** - Timer hardware integration
- **RaceCrew** - Limited race management
- (Check your server's configuration for the exact roles available)

### When Authentication is Required

| Action | Auth Required |
|--------|---------------|
| `query=poll.coordinator` | No |
| `query=poll.now-racing` | No |
| `action=result.write` | Yes |
| `action=heat.select` | Yes |
| `action=schedule.generate` | Yes |

## Related Endpoints

| Endpoint | Purpose |
|----------|---------|
| `query=poll.coordinator` | Full coordinator status (this document) |
| `query=poll.now-racing` | Simplified status for now-racing displays |
| `query=poll.results` | Per-result outcomes + per-racer summaries (results-by-racer kiosk) |
| `action=role.login` | Authenticate and establish session |
| `action=result.write` | Submit race results (requires auth) |
| `action=heat.select` | Change current heat (requires auth) |

### `query=poll.results` — racer summaries

The results-by-racer kiosk paginator (`js/results-by-racer-paginator.js`)
consumes a `racer_summaries` block on this endpoint. Computed server-side
in `ajax/query.poll.results.inc` from the current running round; emitted
in addition to the existing `results[]` patch list.

```json
{
  "racer_summaries": {
    "roundid": 12,
    "time_format": "%.3f",
    "racers": [
      {
        "racerid": 47,
        "carnumber": "42",
        "name": "Alex Kowalski",
        "photo": "/derbynet/photo.php?...",
        "roundid": 12,
        "runs_total": 3,
        "runs_done": 2,
        "best_ms": 4221,
        "avg_ms": 4327,
        "runs": [
          { "lane": 1, "heat": 3, "time_ms": 4314, "place": 1, "finished": true },
          { "lane": 2, "heat": 7, "time_ms": 4221, "place": 1, "finished": true },
          { "lane": 3, "heat": 11, "time_ms": null, "place": null, "finished": false }
        ]
      }
    ]
  }
}
```

Times are integer milliseconds; the kiosk formats them via `time_format`.
Sort order is left to the client (the paginator sorts by `carnumber`).

## Notes

- The endpoint is designed for frequent polling (every 1 second)
- No authentication required for read-only polling
- Use `X-Requested-With: XMLHttpRequest` header for proper AJAX handling
- The `_` timestamp parameter is optional but recommended to bypass caches
- All times are in Unix timestamp format (seconds since epoch)
- Finish times are formatted strings (e.g., "3.4567" for 4-decimal precision)
