#!/usr/bin/env python3
"""
derby-chronology — merge per-component logs into a single per-heat timeline.

Sources:
  - /var/log/derbynet.jsonl           (live JSONL from derbylogger)
  - /var/lib/derbynet/logs/archive/*  (rotated *.jsonl.gz, opt-in)
  - /var/log/mosquitto/mosquitto.log  (broker connect/disconnect anchors, opt-in)

Usage:
  derby-chronology --heat heat-3-7-1716230400123       # exact correlation_id
  derby-chronology --heat 3/7                          # round/heat shorthand
  derby-chronology --since "2026-05-20 09:00" --until "2026-05-20 09:30"
  derby-chronology --heat 3/7 --format md > heat-3-7.md
  derby-chronology --heat 3/7 --format jsonl > heat-3-7.jsonl

Output:
  - Header block: devices present, NTP-sync anchors, start-event device/server
    offset, finishtimer GPIO-edge→publish latency per lane.
  - Merged stream sorted by `ts`, columns: ts  device  level  code  msg.

Pure stdlib. No external deps. Runs on the race-server Pi.
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import gzip
import json
import os
import re
import sys
from typing import Iterable, Iterator, Optional

DEFAULT_JSONL = "/var/log/derbynet.jsonl"
DEFAULT_ARCHIVE_GLOB = "/var/lib/derbynet/logs/archive/derby-*.jsonl.gz"
DEFAULT_MQTT_LOG = "/var/log/mosquitto/mosquitto.log"


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_iso(ts: str) -> Optional[dt.datetime]:
    """Parse derbylogger ISO8601 timestamps. Tolerant of `Z` and offset forms."""
    if not ts:
        return None
    try:
        if ts.endswith("Z"):
            return dt.datetime.fromisoformat(ts[:-1]).replace(tzinfo=dt.timezone.utc)
        return dt.datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


def _parse_user_dt(s: str) -> dt.datetime:
    """Parse a user-supplied date string into a tz-aware datetime."""
    # Accept the same shapes derbyvps.sh accepts: "2026-05-20", "2026-05-20 09:00",
    # full ISO. If naive, assume local time.
    s = s.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            naive = dt.datetime.strptime(s, fmt)
            return naive.astimezone()
        except ValueError:
            continue
    parsed = _parse_iso(s)
    if parsed is None:
        raise argparse.ArgumentTypeError(f"Unrecognized datetime: {s!r}")
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def _open_maybe_gz(path: str):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "rt", encoding="utf-8", errors="replace")


def _iter_jsonl(path: str) -> Iterator[dict]:
    if not os.path.exists(path):
        return
    with _open_maybe_gz(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                # Survive corrupted lines (rsyslog truncation, partial writes)
                continue


# ---------------------------------------------------------------------------
# Source loading
# ---------------------------------------------------------------------------

def _load_sources(args) -> list[dict]:
    """Collect all candidate log entries from the requested sources."""
    entries: list[dict] = []

    paths = [args.jsonl]
    if args.include_archives:
        paths.extend(sorted(glob.glob(args.archive_glob)))

    for p in paths:
        for entry in _iter_jsonl(p):
            entries.append(entry)

    if args.mqtt_log:
        for entry in _iter_mosquitto(args.mqtt_log):
            entries.append(entry)

    return entries


_MOSQ_RE = re.compile(r"^(?P<epoch>\d+):\s(?P<msg>.*)$")


def _iter_mosquitto(path: str) -> Iterator[dict]:
    """Convert mosquitto.log lines into derbylogger-shaped entries so they
    interleave cleanly. mosquitto's default format is `<epoch>: <msg>`."""
    if not os.path.exists(path):
        return
    with _open_maybe_gz(path) as fh:
        for line in fh:
            m = _MOSQ_RE.match(line.strip())
            if not m:
                continue
            try:
                ts = dt.datetime.fromtimestamp(int(m.group("epoch")), tz=dt.timezone.utc)
            except (ValueError, OSError):
                continue
            yield {
                "ts": ts.isoformat(),
                "level": "INFO",
                "device": "MQTT",
                "component": "mosquitto",
                "msg": m.group("msg"),
                "_source": "mosquitto",
            }


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def _heat_predicate(args) -> Optional[callable]:
    if not args.heat:
        return None
    # Accept either "heat-{round}-{heat}-{epoch_ms}" (exact match) or
    # "round/heat" (matches any correlation_id with that prefix).
    if "/" in args.heat:
        try:
            round_id, heat_id = args.heat.split("/", 1)
            int(round_id); int(heat_id)
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"Bad --heat shorthand {args.heat!r}; want 'round/heat' or full id")
        prefix = f"heat-{round_id}-{heat_id}-"
        return lambda cid: bool(cid) and cid.startswith(prefix)
    target = args.heat
    return lambda cid: cid == target


def _filter(entries: list[dict], args) -> list[dict]:
    heat_match = _heat_predicate(args)
    devices = set(args.device) if args.device else None
    since = args.since
    until = args.until

    out = []
    for e in entries:
        if heat_match is not None and not heat_match(e.get("corr_id")):
            continue
        if devices is not None and e.get("device") not in devices:
            continue
        ts = _parse_iso(e.get("ts", ""))
        if ts is None:
            continue
        if since and ts < since:
            continue
        if until and ts > until:
            continue
        e["_ts_parsed"] = ts
        out.append(e)
    out.sort(key=lambda e: (e["_ts_parsed"], e.get("seq", 0)))
    return out


# ---------------------------------------------------------------------------
# Analysis (header block)
# ---------------------------------------------------------------------------

_START_OFFSET_RE = re.compile(
    r"START event:\s+device_ts=(?P<dev>[\d.]+)\s+"
    r"server_recv_ts=(?P<srv>[\d.]+)\s+offset_ms=(?P<offset>[+\-\d.]+)"
)


def _summarize(entries: list[dict]) -> list[str]:
    """Build the header block: devices, NTP anchors, start offset, latencies."""
    if not entries:
        return ["(no entries match)"]

    devices: dict[str, int] = {}
    ntp_anchors: list[str] = []
    start_offsets: list[str] = []
    gpio_to_publish: dict[str, list[float]] = {}

    for e in entries:
        dev = e.get("device") or "?"
        devices[dev] = devices.get(dev, 0) + 1

        msg = e.get("msg") or ""
        if "ntp-synced" in msg or "Time synchronized" in msg:
            ntp_anchors.append(f"  {e.get('ts')}  {dev}  {msg}")

        m = _START_OFFSET_RE.search(msg)
        if m:
            start_offsets.append(
                f"  {e.get('ts')}  device_ts={m.group('dev')}  "
                f"server_recv_ts={m.group('srv')}  offset_ms={m.group('offset')}"
            )

        # Finishtimer GPIO-edge→publish latency lives in the ctx of the
        # finishtimer's "Sending Toggle" debug line; tolerate missing.
        ctx = e.get("ctx") or {}
        edge = ctx.get("timestamp")
        publish = ctx.get("publish_ts")
        if isinstance(edge, (int, float)) and isinstance(publish, (int, float)):
            gpio_to_publish.setdefault(dev, []).append((publish - edge) * 1000.0)

    lines = ["# Race-day chronology", ""]
    lines.append(f"Entries:   {len(entries)}")
    first = entries[0]["_ts_parsed"]
    last = entries[-1]["_ts_parsed"]
    lines.append(f"Window:    {first.isoformat()}  →  {last.isoformat()}")
    lines.append(f"Span:      {(last - first).total_seconds():.1f}s")
    lines.append("")
    lines.append("Devices seen:")
    for dev, count in sorted(devices.items(), key=lambda kv: -kv[1]):
        lines.append(f"  {dev:<12}  {count:>6} entries")
    lines.append("")

    if ntp_anchors:
        lines.append("NTP-sync anchors:")
        lines.extend(ntp_anchors)
        lines.append("")

    if start_offsets:
        lines.append("Start-event device/server offset:")
        lines.extend(start_offsets)
        lines.append("")

    if gpio_to_publish:
        lines.append("Finishtimer GPIO-edge → publish latency (ms):")
        for dev, vals in sorted(gpio_to_publish.items()):
            lines.append(
                f"  {dev:<12}  count={len(vals)}  "
                f"min={min(vals):.0f}  median={sorted(vals)[len(vals)//2]:.0f}  "
                f"max={max(vals):.0f}"
            )
        lines.append("")

    return lines


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _render_txt(entries: list[dict], header: list[str]) -> str:
    out = list(header)
    out.append("ts                                 device        level    code           msg")
    out.append("-" * 110)
    for e in entries:
        out.append(
            f"{e.get('ts', ''):<32}  "
            f"{(e.get('device') or '?'):<12}  "
            f"{(e.get('level') or ''):<8}  "
            f"{(e.get('code') or ''):<14}  "
            f"{e.get('msg', '')}"
        )
    return "\n".join(out) + "\n"


def _render_md(entries: list[dict], header: list[str]) -> str:
    out = list(header)
    out.append("")
    out.append("| ts | device | level | code | msg |")
    out.append("|---|---|---|---|---|")
    for e in entries:
        msg = (e.get("msg") or "").replace("|", "\\|")
        out.append(
            f"| {e.get('ts','')} | {e.get('device','?')} | "
            f"{e.get('level','')} | {e.get('code','')} | {msg} |"
        )
    return "\n".join(out) + "\n"


def _render_jsonl(entries: list[dict], _header) -> str:
    out_lines = []
    for e in entries:
        clean = {k: v for k, v in e.items() if not k.startswith("_")}
        out_lines.append(json.dumps(clean, separators=(",", ":")))
    return "\n".join(out_lines) + "\n"


_RENDERERS = {"txt": _render_txt, "md": _render_md, "jsonl": _render_jsonl}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(
        prog="derby-chronology",
        description="Merge race-day per-component logs into a single timeline.",
    )
    p.add_argument("--heat", help="Heat correlation_id or 'round/heat' shorthand.")
    p.add_argument("--since", type=_parse_user_dt, help="Start of window.")
    p.add_argument("--until", type=_parse_user_dt, help="End of window.")
    p.add_argument(
        "--device", action="append", default=[],
        help="Restrict to one or more devices (repeatable).")
    p.add_argument(
        "--jsonl", default=DEFAULT_JSONL,
        help=f"Path to live JSONL (default: {DEFAULT_JSONL}).")
    p.add_argument(
        "--include-archives", action="store_true",
        help="Also scan rotated gz archives.")
    p.add_argument(
        "--archive-glob", default=DEFAULT_ARCHIVE_GLOB,
        help=f"Archive glob (default: {DEFAULT_ARCHIVE_GLOB}).")
    p.add_argument(
        "--mqtt-log", nargs="?", const=DEFAULT_MQTT_LOG, default=None,
        help=f"Include mosquitto log (default path: {DEFAULT_MQTT_LOG}).")
    p.add_argument(
        "--format", choices=list(_RENDERERS), default="txt",
        help="Output format.")
    args = p.parse_args(argv)

    entries = _load_sources(args)
    filtered = _filter(entries, args)
    header = _summarize(filtered) if args.format != "jsonl" else []
    sys.stdout.write(_RENDERERS[args.format](filtered, header))
    return 0


if __name__ == "__main__":
    sys.exit(main())
