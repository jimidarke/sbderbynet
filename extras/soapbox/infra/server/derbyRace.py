'''
Main program to handle the Derby race.

File location: /var/lib/infra/app/derbyRace.py
Service file: /etc/systemd/system/derbyrace.service

Version History:
- 0.8.2 - Jan 14, 2026 - Added direct SQLite database access for race results
    * New derbydb.py module for direct DB writes (eliminates HTTP latency)
    * Race results written directly to SQLite with WAL mode
    * Falls back to HTTP API if direct DB unavailable
    * Sub-millisecond race result persistence
- 0.8.1 - Jan 14, 2026 - Added thread synchronization for race state (enterprise readiness)
    * Added _race_lock for lane_times, lanesFinished, start_time, race_state
    * Added _heartbeat_lock for timer_heartbeats dictionary
    * Protected laneFinish(), laneDNF(), startRace(), stopRace() with race_lock
    * Protected timerHeartbeat(), cleanup_offline_timers(), send_heartbeat_to_api() with heartbeat_lock
    * Prevents race conditions from concurrent MQTT message handling
- 0.8.0 - Dec 12, 2025 - Standardized version across all soapbox components
- 0.7.3 - Dec 09, 2025 - DNF button integration fix: derbyapi.py now passes finishtime for detection
- 0.7.2 - Dec 09, 2025 - Fixed lane LEDs not resetting after race; changed lane finish color to red
- 0.7.1 - Dec 09, 2025 - Fixed stale race data bug: reset lane tracking on state transitions
- 0.7.0 - Dec 09, 2025 - Fixed premature race finish bug, added lane completion guard
- 0.6.3 - Dec 09, 2025 - Added UNCONFIGURED state for pre-setup, aligned state constants
- 0.5.0 - May 19, 2025 - Standardized version schema across all components
- 0.4.0 - May 10, 2025 - Added service discovery via mDNS
- 0.3.0 - April 22, 2025 - Added remote syslogging and improved error handling
- 0.2.0 - April 15, 2025 - Added telemetry and watchdog timers
- 0.1.0 - April 4, 2025 - Added MQTT communication protocols
- 0.0.1 - March 31, 2025 - Initial implementation
'''


import logging
from serverlogger import ServerLogger
from derbyapi import DerbyNetClient, LoginError
from datetime import datetime, timedelta
import os
import subprocess
import time
import uuid
import paho.mqtt.client as mqtt # type: ignore
import random
import re
import json
import threading
import queue
import psutil # type: ignore
import sys

# Direct database access for race-critical operations (eliminates HTTP latency)
try:
    from derbydb import DerbyDatabase
    DIRECT_DB_AVAILABLE = True
except ImportError:
    DIRECT_DB_AVAILABLE = False

# Alert handler for critical error notifications
try:
    from alerthandler import AlertHandler
    ALERT_HANDLER_AVAILABLE = True
except ImportError:
    ALERT_HANDLER_AVAILABLE = False

# LED sign content generator for BetaBrite displays
try:
    import ledsign_content
    LEDSIGN_AVAILABLE = True
except ImportError:
    LEDSIGN_AVAILABLE = False

# Version information
VERSION = "0.8.3"  # Added unified logging and alerting framework

logger = ServerLogger(
    name='DERBYSERVER', # Name of the logger, can be anything like 'finishtimer', 'derbydisplay', etc.
    log_file='/var/log/derbynet.log', # Default
    level=logging.INFO,  # Default log level
).get_logger()

# MQTT setup - Support environment variables for Docker deployment
MQTT_BROKER             = os.getenv('MQTT_BROKER', 'localhost')
MQTT_PORT               = int(os.getenv('MQTT_PORT', '1883'))
# Cloud broker has allow_anonymous=false; the Pi broker is currently
# anonymous, so empty creds remain valid there. Mirrors the derbyTime.py
# fix in commit 840dcfd0 — that commit's message claimed derbyRace already
# had auth, but it didn't (broker logged "Client derbysvr ... not
# authorised" on every reconnect attempt).
MQTT_USER               = os.getenv('MQTT_USER', '')
MQTT_PASS               = os.getenv('MQTT_PASS', '')
MQTT_QOS_CRITICAL       = 2     # QoS level for critical race messages
MQTT_QOS_NORMAL         = 1     # QoS level for normal operational messages

# Tenant routing mode (cloud only). When 'multi', the race-server runs as a
# dispatcher: one MQTT connection subscribes derbynet/t/+/... and routes each
# message to a per-tenant derbyRace context. When unset / 'single' (Pi), the
# legacy single-tenant flow is preserved exactly — topics stay unprefixed and
# DERBYNET_TENANT (if set) names the one bound DB.
DERBYNET_TENANT_MODE    = os.getenv('DERBYNET_TENANT_MODE', '').lower()

# Slug regex must match website/inc/cloud-tenant.inc::TENANT_SLUG_RE.
# Keep these in sync — both sides validate the same shape so one cannot
# accept a slug the other rejects.
TENANT_SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9-]{0,31}$')


def _valid_tenant_slug(slug):
    return isinstance(slug, str) and bool(TENANT_SLUG_RE.match(slug))


def _tenant_db_path(slug):
    """Mirror of website/inc/cloud-tenant.inc::tenant_db_path()."""
    base = os.getenv('DERBYNET_DB_PATH', '/var/lib/derbynet')
    return os.path.join(base, 'tenants', slug, 'derbynet.sqlite3')


##### Subscribe Topics — single-tenant (Pi) #####
MQTT_TOPIC_RACESTATE    = "derbynet/race/state"
MQTT_TOPIC_TELEMETRY    = "derbynet/device/+/telemetry"
MQTT_TOPIC_STATE        = "derbynet/device/+/state"
##### Subscribe Topics — multi-tenant (cloud dispatcher) #####
MQTT_TOPIC_TELEMETRY_MT = "derbynet/t/+/device/+/telemetry"
MQTT_TOPIC_STATE_MT     = "derbynet/t/+/device/+/state"
##### LED Sign Topics #####
MQTT_TOPIC_LEDSIGN_PREFIX = "derbynet/ledsign"

# Race timing and reliability settings
# IMPORTANT: These values should align with PHP heartbeat-config.inc for state consistency
LANE_FINISH_TIMEOUT     = 90    # seconds to wait for all lanes to finish before auto-completion
HEARTBEAT_TIMEOUT       = 3     # seconds to consider a timer offline (aligned with TIMER_RECENT_THRESHOLD)
HEARTBEAT_PULSE         = 1     # seconds to wait between heartbeat pulses
# Start timer publishes telemetry every ~10s (vs. 1s for finish timers), so it
# needs a more generous offline window to avoid flapping between heartbeats.
STARTER_HEARTBEAT_TIMEOUT = 25  # seconds to consider the start timer offline
RACE_TIMEOUT            = 70    # seconds maximum race time before marking DNF
DNF_TIME               = 99.999 # DNF (Did Not Finish) time value

# Race state constants - aligned with derbyapi.py and coordinator-poll.js
# See RACINGSTATEENGINE.md for complete state documentation
RACE_STATE_UNCONFIGURED = "UNCONFIGURED"  # API unavailable / no database configured (LED: yellow)
RACE_STATE_STOPPED      = "STOPPED"       # Race not active (LED: red)
RACE_STATE_STAGING      = "STAGING"       # Race active, waiting for start (LED: blue)
RACE_STATE_RACING       = "RACING"        # Race in progress (LED: green)
RACE_STATE_FINISHED     = "FINISHED"      # All lanes complete (transient, returns to STOPPED)
class derbyRace:
    def __init__(self, lane_count=3, slug='', mqtt_client=None):
        """Per-tenant race-state machine.

        Pi / single-tenant mode: call with `slug=''` and `mqtt_client=None`.
        The class owns its own MQTT client, publishes to legacy unprefixed
        topics (`derbynet/...`), and behaves exactly as it did before the
        multi-tenant refactor.

        Cloud / multi-tenant mode: `RaceServer` constructs one instance per
        active tenant, passes its `slug` and the shared MQTT client. All
        publishes from this instance land under `derbynet/t/<slug>/...` so
        sibling sandboxes never collide on the broker. The shared client is
        owned by `RaceServer`, not by us.
        """
        logger.info(f"Initializing DerbyRace v{VERSION}"
                    + (f" [tenant={slug}]" if slug else ""))
        self.boottime = datetime.now()
        self.slug = slug or ''

        # Thread synchronization locks
        # race_lock: Protects race state variables (race_state, lane_times, lanesFinished, start_time)
        # heartbeat_lock: Protects timer_heartbeats dictionary
        self._race_lock = threading.Lock()
        self._heartbeat_lock = threading.Lock()

        if mqtt_client is not None:
            # Shared client owned by RaceServer (multi-tenant mode). Don't
            # bind on_message/on_connect — RaceServer routes for us.
            self.client = mqtt_client
            self._owns_client = False
        else:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "derbysvr")
            if MQTT_USER:
                self.client.username_pw_set(MQTT_USER, MQTT_PASS)
            # LWT remains on the unscoped legacy topic in single-tenant mode;
            # operators read this as "race-server is down" regardless of any
            # tenant routing.
            self.client.will_set("derbynet/status", payload="offline", qos=1, retain=True)
            self.client.on_message = self.on_message
            self.client.on_connect = self.on_connect
            self.client.connect(MQTT_BROKER, MQTT_PORT, 90)
            self.client.loop_start()
            self._owns_client = True

        # API client carries the tenant header pair (X-DerbyNet-Tenant +
        # X-DerbyNet-Internal-Token) when slug is set, so HTTP fallback writes
        # land in the right sandbox DB on the cloud.
        api_host = os.getenv('DERBYNET_API_HOST', 'localhost')
        self.api = DerbyNetClient(api_host, tenant_slug=(self.slug or None))

        # Initialize direct database access for race-critical operations
        # This eliminates HTTP latency for writing race results
        self.db = None
        if DIRECT_DB_AVAILABLE:
            # Cloud (multi or single-with-DERBYNET_TENANT): per-tenant SQLite
            # under /var/lib/derbynet/tenants/<slug>/. Pi: legacy single DB.
            db_tenant = self.slug or os.getenv('DERBYNET_TENANT', '')
            if db_tenant:
                db_path = _tenant_db_path(db_tenant)
            else:
                db_path = os.getenv('DERBYNET_DB_PATH')
            if db_path and os.path.exists(db_path):
                try:
                    self.db = DerbyDatabase(db_path)
                    logger.info(f"Direct database access enabled: {db_path}")
                except Exception as e:
                    logger.warning(f"Failed to initialize direct DB, falling back to HTTP: {e}")
            else:
                logger.info("DERBYNET_DB_PATH not set or file not found, using HTTP API for results")
        else:
            logger.info("derbydb module not available, using HTTP API for results")

        # Initialize alert handler for critical error notifications. Each
        # tenant gets its own handler so alerts publish under the correct
        # `derbynet/t/<slug>/alerts/...` prefix.
        self.alert_handler = None
        if ALERT_HANDLER_AVAILABLE:
            try:
                self.alert_handler = AlertHandler(self.client, tenant_slug=(self.slug or None))
                logger.info("Alert handler initialized - critical errors will publish to "
                            + (f"derbynet/t/{self.slug}/alerts" if self.slug else "derbynet/alerts"))
            except Exception as e:
                logger.warning(f"Failed to initialize alert handler: {e}")

        self.start_time = 0
        self.lane_times = {}
        self.lanesFinished = 0
        self.lane_count = lane_count
        self.roundid = 0
        self.heatid = 0
        self.class_name = ""
        self.led = "red"
        self.lanePinny = {}
        self.race_state = RACE_STATE_UNCONFIGURED  # Start unconfigured until API responds
        self.timer_heartbeats = {} # stores the last heartbeat and isready status for each lane
        # Start timer (latched switch) heartbeat is tracked separately from
        # finish-timer lanes — it has no DIP/lane number and its readiness
        # semantics differ (HIGH = Active, LOW = Standby; latched, not armed).
        self.starter_heartbeat = None  # {'time': float, 'isReady': bool, 'timerID': str}
        self.firstupdated = False
        self.last_heartbeat = 0 # updates to unix time when the last heartbeat was sent
        if self._owns_client:
            self.updateFromDerbyAPI()

    def _t(self, *parts):
        """Build an MQTT topic. In multi-tenant mode prefixes with
        `derbynet/t/<slug>/...`; in single-tenant (Pi) mode keeps the
        legacy unprefixed `derbynet/...` shape so real Pi firmware and the
        Pi race-server keep talking on the same topics they always have."""
        if self.slug:
            return '/'.join(('derbynet', 't', self.slug) + tuple(str(p) for p in parts))
        return '/'.join(('derbynet',) + tuple(str(p) for p in parts))

    def on_connect(self, client, userdata, flags, rc, properties=None): # callback for mqtt connection
        self.mqtt_connected = True
        logger.debug(f"Connected to MQTT broker with result code {rc}")
        # Single-tenant (Pi) mode: subscribe to legacy unprefixed topics.
        # Multi-tenant mode owns its subscriptions in RaceServer.on_connect,
        # so this method only ever runs when self._owns_client is True.
        client.subscribe(MQTT_TOPIC_TELEMETRY)
        logger.info(f"Subscribed to {MQTT_TOPIC_TELEMETRY}")
        client.subscribe(MQTT_TOPIC_STATE)
        logger.info(f"Subscribed to {MQTT_TOPIC_STATE}")
        # Publish status message with high QoS
        client.publish("derbynet/status", payload="online", qos=MQTT_QOS_CRITICAL, retain=True)
        
    def on_disconnect(self, client, userdata, rc):
        self.mqtt_connected = False
        if rc != 0:
            logger.critical(f"Unexpected MQTT disconnection with code {rc}, initiating reconnection")
            self.send_alert('ERR-NET-301', f"MQTT broker disconnected unexpectedly (rc={rc})", {'rc': rc})
            # Schedule reconnection attempt
            threading.Timer(5, self.connect_with_retry).start()

    def send_alert(self, error_code: str, message: str, context: dict = None):
        """
        Send an alert for critical errors via the alert handler.

        Args:
            error_code: Standardized error code (e.g., 'ERR-HW-301')
            message: Human-readable error message
            context: Optional context dictionary
        """
        if self.alert_handler:
            try:
                self.alert_handler.check_and_alert({
                    'level': 'CRITICAL',
                    'code': error_code,
                    'msg': message,
                    'device': 'SERVER',
                    'component': 'derbyrace',
                    'ctx': context or {}
                })
            except Exception as e:
                logger.warning(f"Failed to send alert: {e}")
    
    def on_message(self, client, userdata, message): # callback for mqtt messages
        # Pi-mode entry point. Multi-tenant mode goes through
        # RaceServer.on_message → derbyRace._handle_message instead.
        self._handle_message(message.topic, message.payload.decode("utf-8"))

    def _handle_message(self, topic, payload):
        """Process one MQTT message. `topic` may be either a full legacy
        topic (`derbynet/device/<dip>/state`) or the tenant-stripped suffix
        (`device/<dip>/state`); the substring checks below accept both."""
        logger.debug(f"Received message on {topic} {payload}")

        # Validate message format first
        try:
            payload_data = json.loads(payload)

            # Extract device identification
            dip = payload_data.get("dip", "")
            hwid = payload_data.get("hwid", None)
            lane = self.getDIPName(dip)  # get the lane number from the dip switch

            ########### Trigger for START RACE ###########
            if "state" in topic:
                logger.info(f"Received state message on {topic}: toggle={payload_data.get('toggle')}, lane={lane}, race_state={self.race_state}")

                val = payload_data.get("state", False)
                if val == "GO" and self.race_state != RACE_STATE_RACING:
                    self.startRace()
                    self.api.send_start()
            
            ########### Trigger for LANE FINISH ###########
                if self.race_state == RACE_STATE_RACING and lane > 0:
                    # Extract toggle state and validate
                    # Switch DOWN (car crosses finish) sends toggle=False
                    toggle = payload_data.get("toggle", None)
                    logger.info(f"Lane {lane} toggle check: toggle={toggle}, type={type(toggle).__name__}")
                    if toggle is False:  # explicit False check - switch DOWN = car crossed finish
                        # Only count finish if this lane hasn't already finished in this race
                        if lane not in self.lane_times:
                            logger.info(f"Lane {lane} FINISH TRIGGERED!")
                            self.laneFinish(lane)
                        else:
                            logger.warning(f"Lane {lane} finish ignored - already finished this race with time {self.lane_times[lane]}s")
                
            ########### Trigger for DEVICE TELEMETRY ###########
            if "telemetry" in topic:
                # ALWAYS update heartbeats - even during racing
                # This keeps PHP informed that timers are still connected
                # Without this, PHP times out after TIMER_DISCONNECT_THRESHOLD (10s) and resets state
                isReady = payload_data.get("readyToRace", False)
                if lane > 0:
                    self.timerHeartbeat(lane, isReady)
                    logger.debug(f"Updated heartbeat for lane {lane}, ready: {isReady}")
                elif hwid == "START" or "starttimer" in topic:
                    # Start timer reports the latched switch level in `state`
                    # (1 = HIGH = Active, 0 = LOW = Standby). Map that to
                    # the ready flag so the coordinator UI can show it.
                    starter_ready = bool(payload_data.get("state", 0))
                    self.starterHeartbeat(starter_ready, hwid or "STARTER_001")
                    logger.debug(f"Updated starter heartbeat, ready: {starter_ready}")

                # Only forward full device telemetry when NOT racing (for timing accuracy)
                if self.race_state != RACE_STATE_RACING:
                    required_fields = ["hostname", "hwid", "uptime", "ip", "mac"]
                    if all(field in payload_data for field in required_fields):
                        success = self.api.send_device_status(payload_data)
                        if not success:
                            logger.warning(f"Failed to send device telemetry for {hwid}")
                    else:
                        logger.error(f"Incomplete telemetry data from {hwid}: missing required fields")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for message on {topic}: {e}")
        except Exception as e:
            logger.error(f"Error processing message on {topic}: {e}")

    def updateFromDerbyAPI(self):
        # sets online
        self.client.publish(self._t('status'), payload="online", qos=1, retain=True)
        # called frequently once a second to update the finish timers and led colours
        racestats = self.api.get_race_status()
        if not racestats or not isinstance(racestats, dict):
            logger.warning("Failed to get race status from DerbyNet API")
            # Set UNCONFIGURED state when API unavailable (e.g., no database selected)
            if self.race_state != RACE_STATE_UNCONFIGURED:
                prev_state = self.race_state
                self.race_state = RACE_STATE_UNCONFIGURED
                self.led = "yellow"
                self.updateLED("yellow")  # Yellow = needs configuration
                self.client.publish(self._t('race', 'state'), self.race_state, qos=1, retain=True)
                logger.info(f"Race state changed: {prev_state} -> {self.race_state} (API unavailable)")
            return
        self.roundid = racestats.get("roundid",0)
        self.heatid = racestats.get("heat",0)
        self.class_name = racestats.get("class","")
        lanes = racestats.get("lanes",[])

        # Update lane count from actual racers (only when not racing)
        # This allows supporting heats with different numbers of racers
        if self.race_state != RACE_STATE_RACING and len(lanes) > 0:
            actual_lane_count = len(lanes)
            if actual_lane_count != self.lane_count:
                logger.info(f"Lane count updated: {self.lane_count} -> {actual_lane_count}")
                self.lane_count = actual_lane_count

        # During active racing, check for DNF from coordinator page
        # This detects when coordinator marks a lane as DNF (finishtime = 99.999)
        if self.race_state == RACE_STATE_RACING:
            for lane_data in lanes:
                lane_num = lane_data.get("lane")
                finishtime_str = lane_data.get("finishtime", "")

                # Detect DNF set from coordinator (99.999 seconds)
                # Note: API returns formatted string like "99.999", not float
                if finishtime_str and lane_num not in self.lane_times:
                    try:
                        finishtime = float(finishtime_str)
                        if finishtime >= DNF_TIME:  # 99.999 or higher = DNF
                            logger.info(f"Lane {lane_num} DNF detected from coordinator (time={finishtime})")
                            self.laneDNF(lane_num)
                    except (ValueError, TypeError):
                        pass  # Not a valid time value

        self.setLEDFromRaceStat(racestats)
        logger.debug(f"Race Stats: {racestats}")
        for lane in lanes:
            self.setLanePinny(lane["lane"],lane["racerid"])
        # publish racestate
        racestate_topic = self._t('race', 'state')
        result = self.client.publish(racestate_topic, self.race_state, qos=1)
        if result.rc != 0:
            logger.error(f"Error publishing to {racestate_topic} with rc {result.rc} and error {mqtt.error_string(result.rc)}")

    def setLanePinny(self, lane, pinny):
        pinny = str(pinny).zfill(4)
        if self.lanePinny.get(str(lane),None) == pinny:
            return
        self.lanePinny[str(lane)] = pinny
        topic = self._t('lane', lane, 'pinny')
        result = self.client.publish(topic, pinny, qos=2, retain=True)
        if result.rc != 0:
            logger.error(f"Error publishing to {topic} with rc {result.rc} and error {mqtt.error_string(result.rc)}")
        logger.info(f"Set Lane {lane} to Pinny {pinny}")
        self.updateLedSigns()

    def setLEDFromRaceStat(self, racestats):
        """Update LED and race state based on API response (thread-safe).

        Uses _race_lock to protect state transitions. Lock is released before
        network calls (API, MQTT) to avoid blocking other threads.
        """
        led = None
        raceActive = racestats.get("active", None)
        timer_state_string = racestats.get("timer-state-string", "")
        should_call_staging = False
        state_changed = False
        should_update_led = False
        should_reset_leds = False

        with self._race_lock:
            prev_race_state = self.race_state

            # GUARD: If we're racing and not all lanes finished, stay in RACING
            # regardless of what PHP reports (physical race cannot be stopped)
            if (self.race_state == RACE_STATE_RACING and
                self.start_time > 0 and
                self.lanesFinished < self.lane_count):
                logger.debug(f"Race guard: staying RACING ({self.lanesFinished}/{self.lane_count} lanes finished)")
                return  # Exit early, don't change state

            if raceActive == True:
                # Race is active - determine proper state
                if timer_state_string == "Race running":
                    self.race_state = RACE_STATE_RACING
                    led = "green"
                else:
                    # Race is active but not running - we're staging
                    self.race_state = RACE_STATE_STAGING
                    led = "blue"
                    # Only call set_staging if we're transitioning from a different state
                    if prev_race_state in [RACE_STATE_FINISHED, RACE_STATE_STOPPED, RACE_STATE_UNCONFIGURED, ""]:
                        logger.info(f"Transitioning from {prev_race_state} to {RACE_STATE_STAGING}")
                        # CRITICAL: Reset race tracking state when entering STAGING
                        if self.lanesFinished > 0 or len(self.lane_times) > 0 or self.start_time > 0:
                            logger.warning(f"Clearing stale race data on STAGING transition: "
                                          f"lanesFinished={self.lanesFinished}, lane_times={self.lane_times}, "
                                          f"start_time={self.start_time}")
                            self.lanesFinished = 0
                            self.lane_times = {}
                            self.start_time = 0
                        self.led = led
                        should_reset_leds = True
                        should_call_staging = True
            else:
                # Race is not active
                led = "red"
                # CRITICAL: Reset race tracking state when entering STOPPED
                if prev_race_state not in [RACE_STATE_STOPPED, ""]:
                    if self.lanesFinished > 0 or len(self.lane_times) > 0 or self.start_time > 0:
                        logger.warning(f"Clearing stale race data on STOPPED transition: "
                                      f"lanesFinished={self.lanesFinished}, lane_times={self.lane_times}, "
                                      f"start_time={self.start_time}")
                        self.lanesFinished = 0
                        self.lane_times = {}
                        self.start_time = 0
                    self.led = led
                    should_reset_leds = True
                self.race_state = RACE_STATE_STOPPED

            # Check for state change
            if prev_race_state != self.race_state:
                state_changed = True

            # Check if LED needs update
            if led is not None and led != self.led:
                self.led = led
                should_update_led = True

        # Perform actions outside lock (network calls)
        if should_reset_leds:
            self.updateLED(led)
            logger.info(f"Reset all lane LEDs to {led} on state transition")

        if should_call_staging:
            self.api.set_staging()

        if state_changed:
            logger.info(f"Race state changed: {prev_race_state} -> {self.race_state}")
            self.force_heartbeat_update()
            self.updateLedSigns()

        if should_update_led and not should_reset_leds:
            self.updateLED(led)
            logger.info(f"Set RACE LED to {led}")

    def updateLED(self,led,lane="all"):
        if lane == "all":
            for i in range(1,self.lane_count+1):
                topic = self._t('lane', i, 'led')
                result = self.client.publish(topic, led, qos=2, retain=True)
                if result.rc != 0:
                    logger.error(f"Error publishing to {topic} with rc {result.rc} and error {mqtt.error_string(result.rc)}")
        else:
            topic = self._t('lane', lane, 'led')
            result = self.client.publish(topic, led, qos=2, retain=True)
            if result.rc != 0:
                logger.error(f"Error publishing to {topic} with rc {result.rc} and error {mqtt.error_string(result.rc)}")
    
    def updateLedSigns(self):
        """Publish LED sign content for all zones based on current race state."""
        if not LEDSIGN_AVAILABLE:
            return
        try:
            # Lane signs (usher-lane1, usher-lane2, usher-lane3)
            for lane_num in range(1, self.lane_count + 1):
                pinny = self.lanePinny.get(str(lane_num), "----")
                msg = ledsign_content.lane_sign_message(pinny, self.race_state)
                topic = self._t('ledsign', f'usher-lane{lane_num}', 'message')
                self.client.publish(topic, json.dumps(msg), qos=1, retain=True)

            # Starter sign
            msg = ledsign_content.starter_sign_message(self.race_state)
            topic = self._t('ledsign', 'starter', 'message')
            self.client.publish(topic, json.dumps(msg), qos=1, retain=True)
        except Exception as e:
            logger.error(f"Error updating LED signs: {e}")

    def getRaceStatus(self):
        payload = {
            "state":self.race_state,
            "roundid":self.roundid,
            "heatid":self.heatid,
            "class":self.class_name,
            "lanetimes":self.lane_times
        }
        return payload

    def startRace(self, timer=None):
        """Initialize a new race with start time (thread-safe).

        Includes integrity validation to detect state mismatches between
        Python server and PHP backend. Logs warnings but proceeds since
        physical start actuator cannot be blocked once triggered.

        Uses _race_lock to ensure atomic state transitions.

        IMPORTANT: Always resets lane tracking state to prevent stale data
        from a previous aborted/incomplete race from affecting the new race.
        """
        if timer is None:  # set to current timestamp
            timer = time.time()

        with self._race_lock:
            # Check if we're already in an active race
            if self.start_time > 0:
                logger.warning(f"startRace() called but race already in progress (start_time={self.start_time})")
                logger.warning(f"Current state: lanesFinished={self.lanesFinished}, lane_times={self.lane_times}")
                return  # Don't reset an active race

            # ALWAYS reset race state for a new race
            # This prevents stale lane data from a previous aborted race from affecting results
            if self.lanesFinished > 0 or len(self.lane_times) > 0:
                logger.warning(f"Clearing stale race data: lanesFinished={self.lanesFinished}, lane_times={self.lane_times}")
            self.lanesFinished = 0
            self.lane_times = {}
            self.start_time = timer
            self.race_state = RACE_STATE_RACING

        # Validate state with PHP backend (outside lock - network call)
        # This helps detect edge cases but doesn't block (can't stop physical actuator)
        try:
            api_status = self.api.get_race_status()
            if api_status and not api_status.get('active'):
                logger.warning("START detected but DerbyNet NowRacingState is OFF - recording anyway")
                logger.warning("This may indicate a state synchronization issue")
        except Exception as e:
            logger.error(f"Could not validate start with DerbyNet API: {e}")

        logger.info(f"RACE STARTED {datetime.fromtimestamp(timer).strftime('%H:%M:%S.%f')[:-3]} ({timer})")
        self.updateLED("green")

        # Immediately publish race state change to MQTT for faster propagation
        self.client.publish(self._t('race', 'state'), self.race_state, qos=1, retain=True)

        # Update LED signs with GO!
        self.updateLedSigns()

        # Notify PHP of physical start
        self.api.send_start()
        
    def stopRace(self, timer=None):
        """End the current race and submit results (thread-safe).

        Uses _race_lock to ensure atomic state transition and prevents
        race conditions during finish submission.
        """
        if timer is None:  # set to utc timestamp
            timer = time.time()

        with self._race_lock:
            self.race_state = RACE_STATE_FINISHED
            # Copy values for API call outside lock
            roundid = self.roundid
            heatid = self.heatid
            lane_times_copy = dict(self.lane_times)
            # Reset race tracking state
            self.lanesFinished = 0
            self.lane_times = {}
            self.start_time = 0

        logger.info(f"RACE FINISHED {datetime.fromtimestamp(timer).strftime('%H:%M:%S.%f')[:-3]} ({timer})")
        logger.info(lane_times_copy)

        # Immediately publish race state change to MQTT for faster propagation
        self.client.publish(self._t('race', 'state'), self.race_state, qos=1, retain=True)

        # Update LED signs with FINISHED
        self.updateLedSigns()

        # Write race results - prefer direct DB for minimal latency
        if self.db:
            try:
                success = self.db.write_race_results(roundid, heatid, lane_times_copy)
                if success:
                    logger.info(f"Race results written directly to database (round={roundid}, heat={heatid})")
                else:
                    logger.warning("Direct DB write failed, falling back to HTTP API")
                    self.api.send_finish(roundid, heatid, lane_times_copy)
            except Exception as e:
                logger.error(f"Direct DB error: {e}, falling back to HTTP API")
                self.api.send_finish(roundid, heatid, lane_times_copy)
        else:
            # Fallback to HTTP API (outside lock - network call)
            self.api.send_finish(roundid, heatid, lane_times_copy)
        
    def laneFinish(self, lane, timer=None):
        """Record lane finish time with thread-safe state updates.

        Uses _race_lock to ensure atomic check-and-modify of lane_times
        and lanesFinished counter. This prevents race conditions when
        multiple MQTT finish messages arrive simultaneously.
        """
        if timer is None:
            timer = time.time()

        with self._race_lock:
            # Double-check lane hasn't already finished (atomic with lock held)
            if lane in self.lane_times:
                logger.warning(f"Lane {lane} finish ignored (already recorded) - thread-safe check")
                return False

            # Calculate race time
            if self.start_time > 0:
                race_time = round(timer - self.start_time, 3)  # Increased precision to 3 decimal places
            else:
                logger.warning(f"Lane {lane} finish detected but no valid start time recorded, using current time")
                race_time = 0.0

            # Record the finish time (atomic with check above)
            self.lane_times[lane] = race_time
            self.lanesFinished += 1
            lanes_done = self.lanesFinished
            total_lanes = self.lane_count

        # Log the finish with detailed information (outside lock)
        logger.info(f"Lane {lane} finished at {timer} with time {race_time}s (#{lanes_done} to finish) of total {total_lanes} lanes")
        logger.debug(f"LaneFinishTimes: {self.lane_times}")

        # Update LED to indicate finish
        self.updateLED("red", lane)  # red for finished (lane stopped)

        # Check if race is complete
        if lanes_done == total_lanes:
            self.stopRace(timer)
            return True
        return False

    def laneDNF(self, lane):
        """Mark a specific lane as DNF (Did Not Finish) with thread-safe state updates.

        Called when coordinator clicks DNF button for a lane, either:
        - For an unfinished lane during active race
        - For an already-finished lane (e.g., failed video review)

        Uses _race_lock to ensure atomic modification of lane_times and lanesFinished.

        Args:
            lane: Lane number (1-based)

        Returns:
            True if this DNF completed the race, False otherwise
        """
        with self._race_lock:
            if self.race_state != RACE_STATE_RACING:
                logger.warning(f"Cannot DNF lane {lane} - race not in progress (state={self.race_state})")
                return False

            # Check if lane was already recorded (either finished or DNF'd)
            already_recorded = lane in self.lane_times

            if already_recorded:
                logger.info(f"Lane {lane} already finished with time {self.lane_times[lane]}s, updating to DNF")
            else:
                # New DNF - increment finished count
                self.lanesFinished += 1

            # Set DNF time
            self.lane_times[lane] = DNF_TIME
            lanes_done = self.lanesFinished
            total_lanes = self.lane_count

        # Update LED to red for DNF (outside lock)
        self.updateLED("red", lane)
        logger.info(f"Lane {lane} marked as DNF ({lanes_done}/{total_lanes} lanes complete)")

        # Check if race is now complete
        if lanes_done >= total_lanes:
            self.stopRace()
            return True
        return False

    def checkRaceTimeout(self):
        """Check if race has exceeded maximum time and mark unfinished lanes as DNF"""
        if self.race_state != RACE_STATE_RACING or self.start_time == 0:
            return False
            
        current_time = time.time()
        race_duration = current_time - self.start_time
        
        # Check if race has exceeded timeout
        if race_duration > RACE_TIMEOUT:
            dnf_lanes = []
            # Mark unfinished lanes as DNF
            for lane in range(1, self.lane_count + 1):
                if lane not in self.lane_times:
                    self.lane_times[lane] = DNF_TIME
                    self.lanesFinished += 1
                    dnf_lanes.append(lane)
                    # Update LED to indicate DNF
                    self.updateLED("red", lane)  # red for DNF
                    
            if dnf_lanes:
                logger.warning(f"Race timeout after {race_duration:.1f}s - marked lanes {dnf_lanes} as DNF with time {DNF_TIME}s")
                self.send_alert('ERR-RACE-301', f"Race timeout - lanes {dnf_lanes} marked DNF", {
                    'dnf_lanes': dnf_lanes,
                    'race_duration': race_duration,
                    'timeout_threshold': RACE_TIMEOUT
                })

                # Stop race if all lanes are now finished
                if self.lanesFinished >= self.lane_count:
                    self.stopRace(current_time)
                    return True
                    
        return False

    def check_race_integrity(self):
        """Check race state integrity between Python server and PHP backend.

        Detects edge cases where state might be inconsistent:
        - Python racing but PHP not active
        - PHP shows running but Python not racing
        - Racing without valid start time

        Returns dict with 'valid' bool and 'issues' list.
        """
        issues = []

        try:
            api_status = self.api.get_race_status()
            if not api_status:
                return {'valid': True, 'issues': ['Could not fetch API status']}

            # Check 1: Python racing but PHP not active
            if self.race_state == RACE_STATE_RACING and not api_status.get('active'):
                issues.append("Python racing but PHP NowRacingState is OFF")

            # Check 2: PHP shows running but Python not racing
            timer_state_string = api_status.get('timer-state-string', '')
            if 'running' in timer_state_string.lower() and self.race_state != RACE_STATE_RACING:
                issues.append("PHP timer shows running but Python not racing")

            # Check 3: Racing state without valid start time
            if self.race_state == RACE_STATE_RACING and self.start_time == 0:
                issues.append("Racing state without valid start time")

            # Check 4: Round/heat mismatch
            if (self.roundid != api_status.get('roundid', 0) or
                self.heatid != api_status.get('heat', 0)):
                if self.race_state == RACE_STATE_RACING:
                    issues.append(f"Heat mismatch during race: Python={self.roundid}/{self.heatid}, PHP={api_status.get('roundid')}/{api_status.get('heat')}")

        except Exception as e:
            logger.error(f"Error checking race integrity: {e}")
            return {'valid': True, 'issues': [f'Error: {e}']}

        if issues:
            for issue in issues:
                logger.warning(f"Race integrity issue: {issue}")

        return {'valid': len(issues) == 0, 'issues': issues}

    def timerHeartbeat(self, lane, isReady=False):
        """Update timer heartbeat timestamp and check status (thread-safe).

        Uses _heartbeat_lock to protect timer_heartbeats dictionary from
        concurrent modification by multiple MQTT message handlers.
        """
        current_time = time.time()
        force_immediate_heartbeat = False

        with self._heartbeat_lock:
            prev_heartbeat = self.timer_heartbeats.get(lane, {})

            # Update heartbeat for this specific lane
            self.timer_heartbeats[lane] = {'time': current_time, 'isReady': isReady}

            # If this is the first heartbeat or reconnection after timeout
            lastheartbeat = prev_heartbeat.get('time', 0)

            if lastheartbeat == 0 or (current_time - lastheartbeat) > HEARTBEAT_TIMEOUT:
                logger.info(f"Timer for lane {lane} is online (reconnected)")
                force_immediate_heartbeat = True

            if prev_heartbeat.get('isReady', None) != isReady:
                logger.info(f"Timer for lane {lane} ready state changed to: {isReady}")
                force_immediate_heartbeat = True

        # Clean up offline timers (has its own lock acquisition)
        self.cleanup_offline_timers(current_time)

        # Send heartbeat to API every second, or immediately if there's a state change
        # This ensures DerbyNet always knows we're alive and gets current status
        if force_immediate_heartbeat or (current_time - self.last_heartbeat) >= HEARTBEAT_PULSE:
            self.send_heartbeat_to_api(current_time)
    
    def starterHeartbeat(self, isReady, timerID="STARTER_001"):
        """Update the start-timer heartbeat (thread-safe).

        The start timer has no DIP-derived lane and its readiness is the
        latched switch level rather than an arming flag, so it lives in its
        own slot rather than the per-lane dict.
        """
        current_time = time.time()
        force_immediate_heartbeat = False

        with self._heartbeat_lock:
            prev = self.starter_heartbeat or {}
            self.starter_heartbeat = {
                'time': current_time,
                'isReady': isReady,
                'timerID': timerID,
            }
            last = prev.get('time', 0)
            if last == 0 or (current_time - last) > HEARTBEAT_TIMEOUT:
                logger.info("Start timer is online (reconnected)")
                force_immediate_heartbeat = True
            if prev.get('isReady', None) != isReady:
                logger.info(f"Start timer ready state changed to: {isReady}")
                force_immediate_heartbeat = True

        self.cleanup_offline_timers(current_time)

        if force_immediate_heartbeat or (current_time - self.last_heartbeat) >= HEARTBEAT_PULSE:
            self.send_heartbeat_to_api(current_time)

    def cleanup_offline_timers(self, current_time):
        """Remove timers that haven't sent heartbeats within timeout period (thread-safe).

        Uses _heartbeat_lock to safely iterate and modify timer_heartbeats dictionary.
        """
        offline_timers = []
        starter_offline = False
        with self._heartbeat_lock:
            for lane_num in list(self.timer_heartbeats.keys()):
                time_since_heartbeat = current_time - self.timer_heartbeats[lane_num]['time']
                if time_since_heartbeat > HEARTBEAT_TIMEOUT:
                    offline_timers.append(lane_num)
                    del self.timer_heartbeats[lane_num]
            # Start timer publishes telemetry every ~10s; use a more lenient
            # offline window so we don't flap between heartbeats.
            if self.starter_heartbeat is not None:
                age = current_time - self.starter_heartbeat['time']
                if age > STARTER_HEARTBEAT_TIMEOUT:
                    self.starter_heartbeat = None
                    starter_offline = True

        # Log and alert outside lock
        for lane_num in offline_timers:
            logger.warning(f"Timer for lane {lane_num} is offline (no heartbeat within {HEARTBEAT_TIMEOUT}s)")
            self.send_alert('ERR-HW-301', f"Timer for lane {lane_num} is offline", {
                'lane': lane_num,
                'timeout_seconds': HEARTBEAT_TIMEOUT
            })

        if starter_offline:
            logger.warning(f"Start timer is offline (no heartbeat within {STARTER_HEARTBEAT_TIMEOUT}s)")

        return offline_timers
    
    def send_heartbeat_to_api(self, current_time):
        """Send heartbeat to DerbyNet API with current timer status (thread-safe).

        Uses _heartbeat_lock to safely copy timer_heartbeats for API call.
        """
        self.last_heartbeat = current_time

        # Copy heartbeats under lock for thread safety
        with self._heartbeat_lock:
            heartbeats_copy = dict(self.timer_heartbeats)
            starter_copy = dict(self.starter_heartbeat) if self.starter_heartbeat else None

        # Log current timer status (outside lock)
        online_timers = list(heartbeats_copy.keys())
        ready_timers = [lane for lane, data in heartbeats_copy.items() if data.get('isReady', False)]

        logger.debug(f"Heartbeat: Online={online_timers}, Ready={ready_timers}")

        if len(online_timers) < self.lane_count:
            missing = [i for i in range(1, self.lane_count + 1) if i not in online_timers]
            logger.warning(f"Missing timers for lanes: {missing}")

        # Send heartbeat to API - this will determine confirmation based on current status
        success = self.api.send_timer_heartbeat(heartbeats_copy, starter_copy)
        if not success:
            logger.error("Failed to send timer heartbeat to API")
    
    def force_heartbeat_update(self):
        """Force an immediate heartbeat update - useful when state changes"""
        current_time = time.time()
        self.last_heartbeat = 0  # Reset to force immediate send
        self.send_heartbeat_to_api(current_time)
        logger.debug("Forced immediate heartbeat update")
        

    def close(self,graceful = False):
        # Send offline status
        try:
            if hasattr(self, 'mqtt_connected') and self.mqtt_connected:
                self.client.publish(self._t('status'), payload="offline", qos=MQTT_QOS_CRITICAL, retain=True)
        except Exception as e:
            logger.error(f"Error sending offline status: {e}")

        # Clean up MQTT only if we own the client. In multi-tenant mode the
        # client is owned by RaceServer and shutting it down here would tear
        # down every other tenant's session too.
        if self._owns_client:
            self.client.loop_stop()
            self.client.disconnect()
        logger.warning("DerbyRace Closed"
                       + (f" [tenant={self.slug}]" if self.slug else ""))

        # Exit with appropriate code (single-tenant entrypoint only —
        # RaceServer never calls close() this way).
        if self._owns_client:
            if not graceful:
                exit(1)
            else:
                exit(0)
            
    def connect_with_retry(self):
        """Connect to MQTT broker with retry mechanism"""
        try:
            logger.info(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            self.mqtt_connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            logger.info("Will retry connection in 5 seconds")
            threading.Timer(5, self.connect_with_retry).start()
            return False
    
    @staticmethod
    def getDIPName(dip):
        name = 0
        if dip == "1000": #lane1 
            name = 1
        elif dip == "1001": #lane2
            name = 2
        elif dip == "1010": #lane3
            name = 3
        elif dip == "1011": #lane4
            name = 4
        return name
    
    def sendServerTelemetry(self):
        '''
        "device_name": payload.get("hostname","UNKNOWN"),
        "serial": payload.get("hwid",""),
        "uptime": payload.get("uptime",0),
        "ip_address": payload.get("ip",""),
        "mac_address": payload.get("mac",""),
        "wifi_signal": self.getWiFiPercentFromRSSI(payload.get("wifi_rssi",0)),
        "battery": payload.get("battery_level",0),
        "temperature": payload.get("cpu_temp",0),
        "memory": payload.get("memory_usage",0),
        "disk": payload.get("disk",0),
        "cpu": payload.get("cpu_usage",0)}
        '''
        #self.boottime
        uptime = int((time.time() - self.boottime.timestamp()) ) # uptime in seconds
        # `hostname -I` is GNU coreutils (works on the Pi). Alpine ships
        # BusyBox hostname which doesn't have -I. Fall back to socket
        # introspection so the cloud twin doesn't crash on telemetry.
        try:
            cmd = "hostname -I | cut -d' ' -f1"
            ipaddr = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode("utf-8").strip()
            if not ipaddr: raise RuntimeError("empty")
        except Exception:
            try:
                import socket
                ipaddr = socket.gethostbyname(socket.gethostname())
            except Exception:
                ipaddr = "0.0.0.0"
        macaddr = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)])
        # vcgencmd is Raspberry-Pi-only. Default to 0 on cloud / non-Pi.
        try:
            tempraw = subprocess.check_output("vcgencmd measure_temp", shell=True, stderr=subprocess.DEVNULL).decode("utf-8")
            temp = float(tempraw.replace("temp=", "").replace("'C\n", ""))
        except Exception:
            temp = 0.0
        memusage = psutil.virtual_memory().percent
        cpuusage = psutil.cpu_percent()
        diskusage = psutil.disk_usage('/').percent
        payload = {
            "hostname": "derbynetpi",
            "hwid": "derbyRace",
            "version": VERSION,
            "uptime": uptime,
            "ip": ipaddr,
            "mac": macaddr,
            "wifi_rssi": str(random.randint(-40, -30)),  # Simulated RSSI value
            "battery_level": 100,
            "cpu_temp": str(temp),
            "memory_usage": str(memusage),
            "disk": str(diskusage),
            "cpu_usage": str(cpuusage)
        }
        logger.debug(f"Telemetry: {payload}")
        self.api.send_device_status(payload)

class RaceServer:
    """Multi-tenant dispatcher. Owns the single MQTT connection, parses the
    tenant slug out of every incoming topic, and forwards each message to the
    matching `derbyRace` context (lazily creating one on first sight of a
    valid tenant). Each context publishes back through the same shared client
    using its own `derbynet/t/<slug>/...` prefix, so cross-tenant collisions
    on the broker are impossible.

    Used only when DERBYNET_TENANT_MODE=multi. Pi keeps using the legacy
    single-class entrypoint below, where one `derbyRace` instance owns its
    own MQTT client and the topic prefix is always `derbynet/...`."""

    def __init__(self):
        logger.info(f"Initializing RaceServer (multi-tenant) v{VERSION}")
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "derbysvr")
        if MQTT_USER:
            self.client.username_pw_set(MQTT_USER, MQTT_PASS)
        # Server-level LWT is unscoped — operators read this as
        # "race-server is down" regardless of tenant. Per-tenant
        # `derbynet/t/<slug>/status` is owned by each context.
        self.client.will_set("derbynet/status", payload="offline", qos=1, retain=True)
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect
        self.client.connect(MQTT_BROKER, MQTT_PORT, 90)
        self.client.loop_start()

        self.contexts = {}
        self._contexts_lock = threading.Lock()

    def on_connect(self, client, userdata, flags, rc, properties=None):
        logger.info(f"RaceServer connected to MQTT broker (rc={rc})")
        client.subscribe(MQTT_TOPIC_TELEMETRY_MT)
        logger.info(f"Subscribed to {MQTT_TOPIC_TELEMETRY_MT}")
        client.subscribe(MQTT_TOPIC_STATE_MT)
        logger.info(f"Subscribed to {MQTT_TOPIC_STATE_MT}")
        client.publish("derbynet/status", payload="online",
                       qos=MQTT_QOS_CRITICAL, retain=True)

    def on_message(self, client, userdata, message):
        topic = message.topic
        parts = topic.split('/')
        # Expect: derbynet / t / <slug> / device / <hwid> / state|telemetry
        if len(parts) < 4 or parts[0] != 'derbynet' or parts[1] != 't':
            logger.debug(f"Ignoring non-tenant topic: {topic}")
            return
        slug = parts[2]
        if not _valid_tenant_slug(slug):
            logger.warning(f"Rejecting message with invalid slug in topic: {topic}")
            return
        ctx = self._get_or_create_context(slug)
        if ctx is None:
            return
        try:
            payload = message.payload.decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to decode payload on {topic}: {e}")
            return
        sub_topic = '/'.join(parts[3:])
        ctx._handle_message(sub_topic, payload)

    def _get_or_create_context(self, slug):
        with self._contexts_lock:
            ctx = self.contexts.get(slug)
            if ctx is not None:
                return ctx
        # Lazy validation: only spin up state for tenants whose DB exists.
        # Defends against typo'd slugs from a leaked browser cred.
        db_path = _tenant_db_path(slug)
        if not os.path.exists(db_path):
            logger.warning(f"Refusing to create context for unknown tenant {slug!r} "
                           f"(no DB at {db_path})")
            return None
        try:
            lane_count = int(os.getenv('LANE_COUNT', '3'))
        except (TypeError, ValueError):
            lane_count = 3
        ctx = derbyRace(lane_count=lane_count, slug=slug, mqtt_client=self.client)
        with self._contexts_lock:
            # Race: another thread may have created it between checks; keep
            # the first one.
            existing = self.contexts.get(slug)
            if existing is not None:
                return existing
            self.contexts[slug] = ctx
            logger.info(f"Created RaceContext for tenant {slug!r}")
            return ctx

    def tick(self):
        """Per-second update across every active tenant. Errors in one
        tenant's update never affect the others. LoginError specifically is
        downgraded to a warning — a tenant whose API is currently unreachable
        should not crash the dispatcher; it gets retried next tick."""
        with self._contexts_lock:
            ctxs = list(self.contexts.values())
        for ctx in ctxs:
            try:
                ctx.updateFromDerbyAPI()
            except LoginError as e:
                logger.warning(f"Tenant {ctx.slug!r} API login failed: {e} "
                               f"(will retry next tick)")
            except Exception as e:
                logger.error(f"Error updating tenant {ctx.slug!r}: {e}")

    def close(self):
        try:
            self.client.publish("derbynet/status", payload="offline",
                                qos=MQTT_QOS_CRITICAL, retain=True)
        except Exception as e:
            logger.error(f"Error sending server offline status: {e}")
        self.client.loop_stop()
        self.client.disconnect()


def _run_single_tenant():
    """Pi entrypoint — preserved verbatim from the pre-refactor behaviour."""
    logger.info("DerbyRace Server Started (single-tenant)")
    derby = derbyRace()
    while True:
        try:
            derby.updateFromDerbyAPI()
            derby.sendServerTelemetry()
            # Check for race timeout during active racing
            # COMMENTED OUT: DNF decisions are now made only from coordinator page
            # if derby.race_state == "RACING":
            #     derby.checkRaceTimeout()
        except KeyboardInterrupt:
            derby.close()
        except LoginError as e:
            # On Pi, the API and race-server are co-located; a sustained
            # login failure usually means PHP/DB is down. Log and keep ticking
            # — we'd rather race-server stay up and recover than crash the
            # service every time the web app restarts.
            logger.warning(f"DerbyNet API login failed: {e} (will retry next tick)")
        except Exception as e:
            logger.error(f"Error in DerbyRace: {e}")
            derby.close()
            exit(1)
        time.sleep(1)


def _run_multi_tenant():
    """Cloud entrypoint — one MQTT client, per-tenant contexts on demand."""
    logger.info("DerbyRace Server Started (multi-tenant)")
    server = RaceServer()
    while True:
        try:
            server.tick()
        except KeyboardInterrupt:
            server.close()
            return
        except LoginError as e:
            # Should already be caught inside tick(), but defence-in-depth:
            # the dispatcher must NEVER die from one tenant's auth issue.
            logger.warning(f"LoginError reached _run_multi_tenant: {e}")
        except Exception as e:
            logger.error(f"Error in RaceServer tick: {e}")
        time.sleep(1)


if __name__ == "__main__":
    if DERBYNET_TENANT_MODE == 'multi':
        _run_multi_tenant()
    else:
        _run_single_tenant()
