# MQTT Race Captures

JSONL captures of real-hardware MQTT sessions, used by `testing/replay-real-race.py`
to drive deterministic replays against the cloud twin.

## Capture a session (on the local Pi)

```sh
mosquitto_sub -h 192.168.100.10 -p 1883 \
  -u derbynet -P "$MQTT_PASS" \
  -t 'derbynet/#' -v -F '{"t":%I,"topic":"%t","payload":%j}' \
  > "real-race-$(date +%Y-%m-%d-%H%M).jsonl"
```

The `-F` format produces one JSON object per line: `{t, topic, payload}`.
Each capture is self-contained — replays don't need the original broker.

## Replay (against the cloud twin)

```sh
python testing/replay-real-race.py captures/real-race-2026-05-15.jsonl \
  --broker localhost --port 1883 \
  --user derbynet --pass "$MQTT_PASS"
```

The replayer preserves inter-message timing (within a configurable speed
multiplier) and exits non-zero if any publish fails.

## What lives here

Capture files are typically large and event-specific; treat them as test
fixtures, not durable data. Keep one or two known-good baselines committed;
the rest can stay local.
