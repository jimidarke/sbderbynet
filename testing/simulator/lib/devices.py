"""Mock timer hardware at the MQTT layer.

Publishes the same topics/payloads as the real devices:

  * finish timers (extras/soapbox/infra/finishtimer/files/finishtimer.py):
      derbynet[/t/<slug>]/device/<hwid>/{state,telemetry,status}
      state payload: {toggle, timestamp, publish_ts, seq, hwid, dip, lane,
                      correlation_id}
  * start timer (extras/soapbox/infra/starttimer/src/main.py):
      derbynet[/t/<slug>]/device/starttimer/{state,telemetry,status}
      state payload: {state: "GO", timestamp, publish_ts, hwid, correlation_id}

Fast mode backdates: GO carries timestamp T0 in the recent past and each
finish carries T0 + planned_time, all published immediately.  derbyRace
v0.9.1 computes race_time from these device timestamps, so recorded times
equal the plan without wall-clock waits.  Realtime mode publishes the same
payloads at the actual moments instead.
"""

import json
import os
import threading
import time
from typing import Dict, Optional

import paho.mqtt.client as mqtt

from .util import make_logger

logger = make_logger("sim.devices")

QOS_CRITICAL = 2
QOS_NORMAL = 1

# Must match derbyRace.getDIPName()
DIP_SWITCH_MAP = {1: "1000", 2: "1001", 3: "1010", 4: "1011"}


class MqttSession:
    """Authenticated broker connection shared by all mock devices of one
    tenant, tracking race/state and the retained heat correlation id."""

    def __init__(self, tenant: str, client_id: str | None = None):
        self.tenant = tenant
        self.race_state = None
        self.correlation_id = None
        self._state_event = threading.Event()
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id or f"simctl-{tenant}-{os.getpid()}")
        user = os.getenv("MQTT_USER", "")
        if user:
            self.client.username_pw_set(user, os.getenv("MQTT_PASS", ""))
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self._connected = threading.Event()

    def topic(self, *parts) -> str:
        if self.tenant:
            return "/".join(("derbynet", "t", self.tenant) + tuple(map(str, parts)))
        return "/".join(("derbynet",) + tuple(map(str, parts)))

    def connect(self, timeout: float = 10) -> None:
        broker = os.getenv("MQTT_BROKER", "mqtt")
        port = int(os.getenv("MQTT_PORT", "1883"))
        self.client.connect(broker, port, keepalive=30)
        self.client.loop_start()
        if not self._connected.wait(timeout):
            raise RuntimeError(f"MQTT connect to {broker}:{port} timed out")

    def close(self) -> None:
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self._connected.set()
            client.subscribe(self.topic("race", "state"))
            client.subscribe(self.topic("race", "heat", "correlation"))
        else:
            logger.error("MQTT connect failed rc=%s", rc)

    def _on_message(self, client, userdata, msg):
        payload = msg.payload.decode("utf-8", errors="replace")
        if msg.topic.endswith("race/state"):
            self.race_state = payload.strip().strip('"')
            self._state_event.set()
        elif msg.topic.endswith("race/heat/correlation"):
            self.correlation_id = payload.strip()
            self._state_event.set()

    def wait_for_race_state(self, wanted, timeout: float) -> bool:
        """Wait until race/state matches one of `wanted` (str or set)."""
        if isinstance(wanted, str):
            wanted = {wanted}
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.race_state in wanted:
                return True
            self._state_event.wait(0.2)
            self._state_event.clear()
        return self.race_state in wanted

    def wait_for_heat_staged(self, roundid: int, heat: int,
                             timeout: float) -> bool:
        """Wait until the race-server has staged THIS heat: the retained
        correlation id is minted per heat ('heat-{roundid}-{heat}-{ms}') on
        the transition to STAGING.  race/state alone is unreliable here —
        it's retained, so the PREVIOUS heat's STAGING can satisfy a naive
        check before the server has reset for the new heat (its startRace
        refuses a GO until the prior race's state clears)."""
        prefix = f"heat-{roundid}-{heat}-"
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if (self.correlation_id or "").startswith(prefix) and \
                    self.race_state == "STAGING":
                return True
            self._state_event.wait(0.2)
            self._state_event.clear()
        return False

    def publish(self, topic: str, payload, qos: int = QOS_NORMAL,
                retain: bool = False) -> None:
        if not isinstance(payload, str):
            payload = json.dumps(payload)
        self.client.publish(topic, payload, qos=qos, retain=retain)


class MockFinishTimer:
    def __init__(self, session: MqttSession, lane: int):
        self.session = session
        self.lane = lane
        self.dip = DIP_SWITCH_MAP[lane]
        self.hwid = f"SIM_FINISH_{lane}"
        self.seq = 0
        self.is_ready = False
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # -- telemetry ----------------------------------------------------------

    def start_telemetry(self, interval: float = 1.0) -> None:
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, args=(interval,), daemon=True)
        self._thread.start()

    def stop_telemetry(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self, interval: float) -> None:
        while self._running:
            self.send_telemetry()
            time.sleep(interval)

    def send_telemetry(self) -> None:
        now = time.time()
        self.session.publish(
            self.session.topic("device", self.hwid, "telemetry"),
            {
                "hostname": f"simfinish{self.lane}",
                "hwid": self.hwid,
                "dip": self.dip,
                "lane": self.lane,
                "ip": f"192.168.100.{100 + self.lane}",
                "mac": f"AA:BB:CC:DD:EE:{self.lane:02X}",
                "wifi_rssi": -45,
                "battery_level": 100,
                "cpu_temp": 41.0,
                "memory_usage": 25.0,
                "disk": 20.0,
                "cpu_usage": 8.0,
                "uptime": int(now) % 86400,
                "readyToRace": self.is_ready,
                "toggle": self.is_ready,
                "sent_timestamp": now,
                "correlation_id": self.session.correlation_id,
            })
        self.session.publish(
            self.session.topic("device", self.hwid, "status"), "online",
            retain=True)

    # -- state --------------------------------------------------------------

    def set_ready(self, ready: bool = True) -> None:
        self.is_ready = ready
        self.seq += 1
        self.session.publish(
            self.session.topic("device", self.hwid, "state"),
            {
                "toggle": ready,
                "timestamp": time.time(),
                "publish_ts": time.time(),
                "seq": self.seq,
                "hwid": self.hwid,
                "dip": self.dip,
                "lane": self.lane,
                "correlation_id": self.session.correlation_id,
            }, qos=QOS_CRITICAL)
        self.send_telemetry()

    def trigger_finish(self, at_ts: float) -> None:
        """Car crosses the line: toggle False, GPIO-edge timestamp at_ts.
        In fast mode at_ts is in the recent past; in realtime mode it is
        (approximately) now."""
        self.seq += 1
        self.is_ready = False
        self.session.publish(
            self.session.topic("device", self.hwid, "state"),
            {
                "toggle": False,
                "timestamp": at_ts,
                "publish_ts": time.time(),
                "seq": self.seq,
                "hwid": self.hwid,
                "dip": self.dip,
                "lane": self.lane,
                "correlation_id": self.session.correlation_id,
            }, qos=QOS_CRITICAL)
        logger.debug("lane %d finish published (ts=%.3f)", self.lane, at_ts)


class MockStartTimer:
    def __init__(self, session: MqttSession):
        self.session = session
        self.hwid = "START"
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start_telemetry(self, interval: float = 5.0) -> None:
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, args=(interval,), daemon=True)
        self._thread.start()

    def stop_telemetry(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self, interval: float) -> None:
        while self._running:
            self.send_telemetry()
            time.sleep(interval)

    def send_telemetry(self) -> None:
        now = time.time()
        self.session.publish(
            self.session.topic("device", "starttimer", "telemetry"),
            {
                "hostname": "Starter",
                "hwid": self.hwid,
                "ip": "192.168.100.99",
                "mac": "AA:BB:CC:DD:EE:99",
                "wifi_rssi": -50,
                "battery_level": 100,
                "uptime": int(now) % 86400,
                "timestamp": now,
                "state": 1,  # latched HIGH = armed/ready
                "correlation_id": self.session.correlation_id,
                "version": "sim",
            })
        self.session.publish(
            self.session.topic("device", "starttimer", "status"), "online",
            retain=True)

    def send_go(self, at_ts: float) -> None:
        """Gate release with GPIO-edge timestamp at_ts (backdated in fast
        mode).  No `dip` field, exactly like the real start timer, so the
        race-server never mistakes this for a lane finish."""
        self.session.publish(
            self.session.topic("device", "starttimer", "state"),
            {
                "state": "GO",
                "timestamp": at_ts,
                "publish_ts": time.time(),
                "ntp_sync_ts": at_ts - 3600,
                "hwid": self.hwid,
                "correlation_id": self.session.correlation_id,
            }, qos=QOS_CRITICAL)
        logger.debug("GO published (ts=%.3f)", at_ts)


class MockTrack:
    """One tenant's full set of mock hardware."""

    def __init__(self, tenant: str, lane_count: int = 3):
        self.session = MqttSession(tenant)
        self.lane_count = lane_count
        self.finish: Dict[int, MockFinishTimer] = {}
        self.start = MockStartTimer(self.session)

    def up(self) -> None:
        self.session.connect()
        for lane in range(1, self.lane_count + 1):
            timer = MockFinishTimer(self.session, lane)
            timer.start_telemetry()
            self.finish[lane] = timer
        self.start.start_telemetry()

    def down(self) -> None:
        for timer in self.finish.values():
            timer.stop_telemetry()
        self.start.stop_telemetry()
        self.session.close()

    def stage_all(self) -> None:
        for timer in self.finish.values():
            timer.set_ready(True)
