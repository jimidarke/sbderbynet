#!/usr/bin/env python3
"""replay-real-race.py — replay a captured MQTT session.

Reads a JSONL capture (one {t, topic, payload} object per line, as produced
by `mosquitto_sub -F '{"t":%I,"topic":"%t","payload":%j}'`) and republishes
the timeline against a target MQTT broker.

The cloud twin uses this for deterministic regression: capture a known-good
race-day session from the local Pi, replay it on the cloud broker, and
assert the race server's state machine reaches the expected end state.

Usage:
    python replay-real-race.py CAPTURE.jsonl \\
        --broker HOST --port 1883 --user U --pass P [--speed 1.0]

Exit codes:
    0  all messages replayed
    1  capture file or broker error
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Iterator

import paho.mqtt.client as mqtt


def iter_capture(path: str) -> Iterator[dict]:
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                sys.stderr.write(f"{path}:{lineno}: skip ({e})\n")


def replay(args) -> int:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         client_id=f"replay-{int(time.time())}")
    if args.user:
        client.username_pw_set(args.user, args.password or "")

    connected = []

    def on_connect(c, u, flags, rc, props=None):
        if rc == 0:
            connected.append(True)
        else:
            sys.stderr.write(f"connect rc={rc}\n")

    client.on_connect = on_connect
    client.connect(args.broker, args.port, keepalive=60)
    client.loop_start()

    deadline = time.time() + 10
    while not connected and time.time() < deadline:
        time.sleep(0.05)
    if not connected:
        sys.stderr.write("broker connect timed out\n")
        return 1

    msgs = list(iter_capture(args.capture))
    if not msgs:
        sys.stderr.write("empty capture\n")
        return 1

    base_t = msgs[0].get("t", 0)
    start = time.time()
    sent = 0
    for entry in msgs:
        t = entry.get("t", base_t)
        topic = entry.get("topic")
        payload = entry.get("payload")
        if topic is None:
            continue

        # Re-encode JSON payloads, leave strings as-is
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload)
        elif payload is None:
            payload = ""

        # Pace based on capture timeline (seconds since first message)
        target = start + ((t - base_t) / args.speed)
        delay = target - time.time()
        if delay > 0:
            time.sleep(delay)

        info = client.publish(topic, payload, qos=args.qos, retain=False)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            sys.stderr.write(f"publish failed: rc={info.rc} topic={topic}\n")
            return 1
        sent += 1

    # Drain
    client.loop_stop()
    client.disconnect()
    print(f"replayed {sent} messages over {(time.time() - start):.1f}s")
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("capture", help="JSONL capture file")
    p.add_argument("--broker", default="localhost")
    p.add_argument("--port", type=int, default=1883)
    p.add_argument("--user", default=None)
    p.add_argument("--pass", dest="password", default=None)
    p.add_argument("--speed", type=float, default=1.0,
                   help="playback speed multiplier (>1 = faster)")
    p.add_argument("--qos", type=int, default=1, choices=(0, 1, 2))
    return p.parse_args()


if __name__ == "__main__":
    sys.exit(replay(parse_args()))
