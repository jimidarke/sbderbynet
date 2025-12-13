#!/usr/bin/env python3
"""
Racing Event Simulation Script - MQTT-Based Hardware Simulation

This script simulates complete racing events by emulating the actual hardware
devices (finish timers, start timer) at the MQTT layer. This tests the full
stack: MQTT -> derbyRace.py -> DerbyNet API.

Architecture:
    SimulatedFinishTimer (x3) -> MQTT telemetry + state messages
    SimulatedStartTimer       -> MQTT GO signal
    RaceSimulator             -> Orchestrates race cycles

Flow:
    1. Detect STAGING state from API
    2. All finish timers send "ready" heartbeats
    3. Wait configurable delay, then send START (GO) signal
    4. Each finish timer waits random time, then sends toggle=False
    5. Race completes when all lanes finish
    6. Wait between races, repeat

File location: /var/lib/infra/app/simulate_racing.py
Usage: python3 simulate_racing.py [options]

Version History:
- 0.8.0 - Dec 12, 2025 - Standardized version across all soapbox components
- 0.2.0 - December 2025 - Complete rewrite with MQTT-based hardware simulation
- 0.1.0 - January 2025 - Initial implementation (deprecated - bypassed MQTT layer)
"""

import argparse
import json
import random
import time
import logging
import sys
import signal
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional
import paho.mqtt.client as mqtt
from derbyapi import DerbyNetClient
from serverlogger import ServerLogger

# Version information
VERSION = "0.8.0"

# Initialize logging
logger = ServerLogger(
    name='RACESIM',
    log_file='/var/log/derbynet.log',
    level=logging.INFO,
).get_logger()

# ANSI color codes for console output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'

def console_print(msg: str, color: str = "", bold: bool = False):
    """Print to console with optional color"""
    prefix = Colors.BOLD if bold else ""
    print(f"{prefix}{color}{msg}{Colors.RESET}", flush=True)

# MQTT Configuration - matches derbyRace.py
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_QOS_CRITICAL = 2
MQTT_QOS_NORMAL = 1

# DIP switch mappings (must match derbyRace.getDIPName)
DIP_SWITCH_MAP = {
    1: "1000",  # Lane 1
    2: "1001",  # Lane 2
    3: "1010",  # Lane 3
    4: "1011",  # Lane 4
}


@dataclass
class SimulationConfig:
    """Configuration parameters for race simulation"""
    # Race timing
    min_race_time: float = 4.0      # Minimum time for fastest finisher (seconds)
    max_race_time: float = 8.0      # Maximum time for slowest finisher (seconds)
    finish_spread: float = 2.0      # Max spread between fastest and slowest

    # Delays
    start_delay_min: float = 1.0    # Min delay after staging before start
    start_delay_max: float = 3.0    # Max delay after staging before start
    between_race_min: float = 2.0   # Min delay between races
    between_race_max: float = 5.0   # Max delay between races

    # Hardware simulation
    lane_count: int = 3             # Number of lanes to simulate
    telemetry_interval: float = 1.0 # Heartbeat interval (seconds)

    # Behavior
    max_races: int = 0              # 0 = unlimited
    dry_run: bool = False           # If True, don't actually send MQTT messages
    fast_mode: bool = False         # If True, inject times directly instead of waiting


class SimulatedFinishTimer:
    """
    Simulates a single finish timer device at the MQTT layer.

    Each finish timer:
    - Sends periodic telemetry with readyToRace status
    - Sends state messages when toggle changes (ready/finish)
    """

    def __init__(self, lane: int, mqtt_client: mqtt.Client, config: SimulationConfig):
        self.lane = lane
        self.client = mqtt_client
        self.config = config
        self.dip = DIP_SWITCH_MAP.get(lane, "0000")
        self.hwid = f"SIM_FINISH_{lane}"
        self.hostname = f"simfinish{lane}"

        # State
        self.is_ready = False       # Toggle flipped to ready position
        self.has_finished = False   # Car has crossed finish line this race
        self.telemetry_thread: Optional[threading.Thread] = None
        self.running = False

        logger.info(f"SimulatedFinishTimer Lane {lane} initialized (DIP={self.dip})")

    def start_telemetry(self):
        """Start sending periodic telemetry messages"""
        self.running = True
        self.telemetry_thread = threading.Thread(target=self._telemetry_loop, daemon=True)
        self.telemetry_thread.start()

    def stop_telemetry(self):
        """Stop telemetry thread"""
        self.running = False
        if self.telemetry_thread:
            self.telemetry_thread.join(timeout=2)

    def _telemetry_loop(self):
        """Background thread sending telemetry at configured interval"""
        while self.running:
            self._send_telemetry()
            time.sleep(self.config.telemetry_interval)

    def _send_telemetry(self):
        """Send telemetry message mimicking real finish timer"""
        if self.config.dry_run:
            logger.debug(f"[DRY RUN] Lane {self.lane} telemetry: ready={self.is_ready}")
            return

        topic = f"derbynet/device/{self.dip}/telemetry"
        payload = {
            "hostname": self.hostname,
            "hwid": self.hwid,
            "dip": self.dip,
            "uptime": int(time.time()) % 86400,  # Simulated uptime
            "ip": f"192.168.100.{100 + self.lane}",
            "mac": f"AA:BB:CC:DD:EE:{self.lane:02X}",
            "wifi_rssi": random.randint(-50, -35),
            "battery_level": 100,
            "cpu_temp": random.uniform(35, 45),
            "memory_usage": random.uniform(20, 40),
            "disk": random.uniform(10, 30),
            "cpu_usage": random.uniform(5, 15),
            "readyToRace": self.is_ready,
            "toggle": self.is_ready and not self.has_finished
        }

        self.client.publish(topic, json.dumps(payload), qos=MQTT_QOS_NORMAL)
        logger.debug(f"Lane {self.lane} telemetry sent: ready={self.is_ready}")

    def set_ready(self, ready: bool = True):
        """
        Set the ready state (toggle flipped to staging position).
        Sends state message to notify derbyRace.py.
        """
        self.is_ready = ready
        self.has_finished = False  # Reset finish state when going ready

        if self.config.dry_run:
            logger.info(f"[DRY RUN] Lane {self.lane} ready={ready}")
            return

        # Send state message with toggle status
        topic = f"derbynet/device/{self.dip}/state"
        payload = {
            "hwid": self.hwid,
            "dip": self.dip,
            "state": "READY" if ready else "IDLE",
            "toggle": ready
        }

        self.client.publish(topic, json.dumps(payload), qos=MQTT_QOS_CRITICAL)
        logger.info(f"Lane {self.lane} set ready={ready}")

    def trigger_finish(self) -> float:
        """
        Simulate car crossing finish line (toggle goes False).
        Returns the finish timestamp.
        """
        if self.has_finished:
            logger.warning(f"Lane {self.lane} finish triggered but already finished")
            return 0.0

        self.has_finished = True
        finish_time = time.time()

        if self.config.dry_run:
            logger.info(f"[DRY RUN] Lane {self.lane} FINISH at {finish_time}")
            return finish_time

        # Send state message with toggle=False (switch DOWN = car crossed)
        topic = f"derbynet/device/{self.dip}/state"
        payload = {
            "hwid": self.hwid,
            "dip": self.dip,
            "state": "GO",  # Match what real device sends
            "toggle": False  # Switch DOWN = car crossed finish line
        }

        self.client.publish(topic, json.dumps(payload), qos=MQTT_QOS_CRITICAL)
        logger.info(f"Lane {self.lane} FINISH triggered at {datetime.fromtimestamp(finish_time).strftime('%H:%M:%S.%f')[:-3]}")

        return finish_time

    def reset_for_race(self):
        """Reset state for a new race"""
        self.has_finished = False
        # Keep is_ready as-is; it should be set during staging


class SimulatedStartTimer:
    """
    Simulates the start timer device at the MQTT layer.

    The start timer sends a GO signal when the gate releases.
    """

    def __init__(self, mqtt_client: mqtt.Client, config: SimulationConfig):
        self.client = mqtt_client
        self.config = config
        self.hwid = "SIM_START"
        self.dip = "0001"  # Start timer DIP

        logger.info("SimulatedStartTimer initialized")

    def send_go(self) -> float:
        """
        Send GO signal simulating gate release.
        Returns the start timestamp.
        """
        start_time = time.time()

        if self.config.dry_run:
            logger.info(f"[DRY RUN] START GO at {start_time}")
            return start_time

        # Send via the state topic that derbyRace.py listens to
        # Using lane 1's DIP with state=GO triggers startRace()
        topic = f"derbynet/device/{DIP_SWITCH_MAP[1]}/state"
        payload = {
            "hwid": self.hwid,
            "dip": self.dip,
            "state": "GO",
            "toggle": True
        }

        self.client.publish(topic, json.dumps(payload), qos=MQTT_QOS_CRITICAL)
        logger.info(f"START GO sent at {datetime.fromtimestamp(start_time).strftime('%H:%M:%S.%f')[:-3]}")

        return start_time


class RaceSimulator:
    """
    Main orchestrator for race simulation.

    Manages the complete race cycle:
    1. Wait for STAGING state
    2. Set all finish timers to ready
    3. Delay, then trigger start
    4. Trigger finish for each lane with random timing
    5. Wait for race completion
    6. Repeat
    """

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.shutdown_requested = False

        # Initialize MQTT client
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, f"racesim_{int(time.time())}")
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_connected = False

        # Initialize API client
        self.api_client = DerbyNetClient("localhost")

        # Initialize simulated devices
        self.finish_timers: Dict[int, SimulatedFinishTimer] = {}
        self.start_timer: Optional[SimulatedStartTimer] = None

        # Race tracking
        self.race_count = 0
        self.current_race_start = 0.0

        # Heartbeat thread control
        self.heartbeat_running = False
        self.heartbeat_thread: Optional[threading.Thread] = None

        logger.info(f"RaceSimulator v{VERSION} initialized with config: "
                   f"lanes={config.lane_count}, race_time={config.min_race_time}-{config.max_race_time}s")

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """MQTT connection callback"""
        if rc == 0:
            self.mqtt_connected = True
            logger.info("MQTT connected successfully")
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def setup(self) -> bool:
        """Initialize connections and devices"""
        console_print("\n[SETUP] Initializing simulator...", Colors.CYAN, bold=True)

        # Connect MQTT
        try:
            console_print("  - Connecting to MQTT broker...", Colors.DIM)
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
            time.sleep(1)  # Allow connection to establish

            if not self.mqtt_connected:
                console_print("  - MQTT connection FAILED", Colors.RED)
                logger.error("MQTT connection not established")
                return False
            console_print("  - MQTT connected", Colors.GREEN)
        except Exception as e:
            console_print(f"  - MQTT connection FAILED: {e}", Colors.RED)
            logger.critical(f"Failed to connect to MQTT broker: {e}")
            return False

        # Login to DerbyNet API
        console_print("  - Connecting to DerbyNet API...", Colors.DIM)
        if not self.api_client.login():
            console_print("  - DerbyNet API login FAILED", Colors.RED)
            logger.critical("Failed to login to DerbyNet API")
            return False

        console_print("  - DerbyNet API connected", Colors.GREEN)
        logger.info("Successfully connected to DerbyNet API")

        # Create simulated devices
        self.start_timer = SimulatedStartTimer(self.mqtt_client, self.config)

        for lane in range(1, self.config.lane_count + 1):
            self.finish_timers[lane] = SimulatedFinishTimer(
                lane, self.mqtt_client, self.config
            )
            self.finish_timers[lane].start_telemetry()

        console_print(f"  - Created {len(self.finish_timers)} simulated finish timers", Colors.GREEN)

        # Start background heartbeat thread to keep timers appearing online
        self.heartbeat_running = True
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        console_print("  - Started heartbeat thread (timers will appear online)", Colors.GREEN)

        console_print("[SETUP] Complete!\n", Colors.CYAN, bold=True)
        logger.info(f"Created {len(self.finish_timers)} simulated finish timers")
        return True

    def _heartbeat_loop(self):
        """Background thread to send periodic heartbeats to DerbyNet API"""
        while self.heartbeat_running and not self.shutdown_requested:
            try:
                self._send_api_heartbeat()
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
            time.sleep(2)  # Send heartbeat every 2 seconds

    def _send_api_heartbeat(self):
        """Send heartbeat to DerbyNet API to keep timers appearing online"""
        current_time = time.time()
        timer_heartbeats = {}

        for lane, timer in self.finish_timers.items():
            timer_heartbeats[lane] = {
                'time': current_time,
                'isReady': timer.is_ready
            }

        # Send heartbeat via DerbyNet API
        self.api_client.send_timer_heartbeat(timer_heartbeats)

    def get_race_state(self) -> Optional[str]:
        """Get current race state from API"""
        try:
            status = self.api_client.get_race_status()
            if not status:
                return None

            # 'timer-state-string' contains the message like "Staging", "Race running", "UNCONFIRMED"
            state_msg = status.get('timer-state-string', '').lower().strip()
            # Check if now_racing is set (active racing mode)
            now_racing = status.get('active', False)
            # Check if there are racers staged
            has_racers = len(status.get('lanes', [])) > 0
            heat = status.get('heat', 0)

            # Debug output
            logger.debug(f"Race state check: now_racing={now_racing}, has_racers={has_racers}, heat={heat}, msg={state_msg}")

            # Map to simplified states for simulator
            if 'staging' in state_msg:
                return 'staging'
            elif 'race' in state_msg and 'running' in state_msg:
                return 'race running'
            elif now_racing and has_racers and heat > 0:
                # System is in racing mode with racers staged - treat as staging
                # This handles cases where timer-state-string is "UNCONFIRMED" but racing is active
                return 'staging'
            else:
                return state_msg if state_msg else 'unknown'
        except Exception as e:
            logger.error(f"Error getting race state: {e}")
            return None

    def wait_for_staging(self, timeout: float = 300) -> bool:
        """
        Wait for system to enter STAGING state.
        Returns True when staging, False on timeout or shutdown.
        """
        logger.info("Waiting for STAGING state...")
        console_print("[WAITING] Waiting for STAGING state...", Colors.YELLOW)
        start_wait = time.time()
        last_state = None
        dots = 0

        while not self.shutdown_requested:
            state = self.get_race_state()

            if state == 'staging':
                console_print(f"\r[STAGING] System ready to race!          ", Colors.GREEN, bold=True)
                logger.info("System is in STAGING state")
                return True
            elif state == 'race running':
                if last_state != state:
                    console_print(f"\r[WAITING] Race in progress, waiting...   ", Colors.YELLOW)
                logger.warning("Race already running, waiting for completion...")
            else:
                # Show waiting animation
                dots = (dots + 1) % 4
                dot_str = "." * dots + " " * (3 - dots)
                elapsed = int(time.time() - start_wait)
                print(f"\r[WAITING] State: {state or 'unknown'} ({elapsed}s){dot_str}    ", end="", flush=True)
                logger.debug(f"Current state: {state}")

            last_state = state

            if (time.time() - start_wait) > timeout:
                console_print(f"\n[TIMEOUT] Waited {timeout}s for staging", Colors.RED)
                logger.error(f"Timeout waiting for staging ({timeout}s)")
                return False

            time.sleep(1)

        return False

    def stage_all_timers(self):
        """Set all finish timers to ready state"""
        console_print("  [STAGE] Setting timers to READY...", Colors.CYAN)
        logger.info("Setting all finish timers to READY...")

        for lane, timer in self.finish_timers.items():
            timer.reset_for_race()
            timer.set_ready(True)
            time.sleep(0.1)  # Small delay between messages

        # Send immediate heartbeat to update DerbyNet
        self._send_api_heartbeat()

        # Give DerbyNet time to process heartbeats
        time.sleep(2)
        logger.info("All finish timers are ready")

    def simulate_single_race(self) -> bool:
        """
        Execute a single race simulation.
        Returns True if race completed successfully.

        In fast_mode, injects calculated times directly via API instead of
        waiting real-time for MQTT finish triggers.
        """
        try:
            # Get race info for logging
            status = self.api_client.get_race_status()
            roundid = status.get('roundid', 0)
            heat = status.get('heat', 0)
            class_name = status.get('class', 'Unknown')
            round_name = status.get('round', 'Unknown')

            console_print(f"\n{'='*60}", Colors.HEADER)
            console_print(f"  RACE #{self.race_count}: {class_name}", Colors.HEADER, bold=True)
            console_print(f"  Round: {round_name} | Heat: {heat}", Colors.HEADER)
            console_print(f"{'='*60}", Colors.HEADER)

            logger.info(f"=== Starting Race: {class_name} Round {roundid} Heat {heat} ===")

            # Generate random finish times for all lanes
            lanes = list(range(1, self.config.lane_count + 1))
            random.shuffle(lanes)

            # First finisher time
            first_finish_time = random.uniform(
                self.config.min_race_time,
                self.config.max_race_time - self.config.finish_spread
            )

            # Calculate all lane times
            lane_times = {}
            for i, lane in enumerate(lanes):
                if i == 0:
                    lane_times[lane] = round(first_finish_time, 3)
                else:
                    lane_times[lane] = round(first_finish_time + random.uniform(
                        0.3 * i,
                        min(self.config.finish_spread, 0.5 * i + 1.5)
                    ), 3)

            # Show planned times
            console_print(f"  Target times: ", Colors.DIM, bold=False)
            for lane in sorted(lane_times.keys()):
                console_print(f"    Lane {lane}: {lane_times[lane]:.3f}s", Colors.DIM)

            logger.info(f"Generated times: {lane_times}")

            if self.config.fast_mode:
                # FAST MODE: Inject times directly via API
                return self._fast_mode_race(roundid, heat, lane_times)
            else:
                # NORMAL MODE: Real-time MQTT simulation
                return self._realtime_race(roundid, heat, lane_times)

        except Exception as e:
            console_print(f"[ERROR] Race simulation failed: {e}", Colors.RED)
            logger.error(f"Error during race simulation: {e}")
            return False

    def _fast_mode_race(self, roundid: int, heat: int, lane_times: Dict[int, float]) -> bool:
        """
        Fast mode: Send start signal then inject finish times via API.
        Includes 5s delay after start to allow kiosk displays to update.
        """
        console_print("  [FAST MODE] Staging timers...", Colors.CYAN)
        logger.info("[FAST MODE] Injecting race times directly")

        # Stage timers briefly (needed for DerbyNet state machine)
        self.stage_all_timers()
        time.sleep(0.5)

        # Send START signal
        console_print("  [FAST MODE] GO! Race started", Colors.GREEN, bold=True)
        self.start_timer.send_go()

        # Wait 5 seconds to allow displays to update and show race in progress
        console_print("  [FAST MODE] Waiting 5s for displays...", Colors.DIM)
        logger.info("[FAST MODE] Waiting 5s for displays to update...")
        for i in range(5, 0, -1):
            print(f"\r  [FAST MODE] Injecting results in {i}s...   ", end="", flush=True)
            time.sleep(1)
        print("\r  [FAST MODE] Injecting results now!      ", flush=True)

        # Directly send finish results to API (bypassing MQTT finish triggers)
        if not self.api_client.send_finish(roundid, heat, lane_times):
            console_print("  [ERROR] Failed to send results via API", Colors.RED)
            logger.error("Failed to send finish results via API")
            return False

        # Show results
        console_print("  [RESULTS]", Colors.GREEN, bold=True)
        sorted_lanes = sorted(lane_times.items(), key=lambda x: x[1])
        for place, (lane, time_val) in enumerate(sorted_lanes, 1):
            place_color = Colors.YELLOW if place == 1 else Colors.RESET
            console_print(f"    {place}. Lane {lane}: {time_val:.3f}s", place_color)

        logger.info(f"[FAST MODE] Race completed. Results: {lane_times}")

        # Brief delay for DerbyNet to process results
        time.sleep(0.5)
        return True

    def _realtime_race(self, roundid: int, heat: int, lane_times: Dict[int, float]) -> bool:
        """
        Real-time mode: Wait actual time and trigger MQTT finish messages.
        Tests full timing accuracy of the stack.
        """
        # Stage all timers
        self.stage_all_timers()

        # Random delay before start
        start_delay = random.uniform(self.config.start_delay_min, self.config.start_delay_max)
        logger.info(f"Waiting {start_delay:.2f}s before start...")

        for _ in range(int(start_delay * 10)):
            if self.shutdown_requested:
                return False
            time.sleep(0.1)

        # Send START signal
        self.current_race_start = self.start_timer.send_go()

        # Sort lanes by finish time
        finish_schedule = sorted(lane_times.items(), key=lambda x: x[1])
        logger.info(f"Finish schedule: {[(f'L{l}', f'{t:.2f}s') for l, t in finish_schedule]}")

        # Wait for start signal to be processed
        time.sleep(0.5)

        # Execute finish sequence in real-time
        race_start = time.time()
        results = {}

        for lane, target_time in finish_schedule:
            if self.shutdown_requested:
                logger.warning("Shutdown during race - aborting")
                return False

            # Wait until it's time for this lane to finish
            elapsed = time.time() - race_start
            wait_time = target_time - elapsed

            if wait_time > 0:
                time.sleep(wait_time)

            # Trigger finish via MQTT
            finish_time = self.finish_timers[lane].trigger_finish()
            race_time = finish_time - self.current_race_start
            results[lane] = race_time

            logger.info(f"Lane {lane} finished: {race_time:.3f}s")

        # Wait for race to complete in DerbyNet
        time.sleep(1)

        # Verify race completed
        final_state = self.get_race_state()
        if final_state and 'running' in final_state:
            logger.warning("Race may not have completed properly in DerbyNet")

        logger.info(f"Race completed. Results: {results}")
        return True

    def run(self):
        """Main simulation loop"""
        console_print(f"\n[RUN] Starting race simulation", Colors.CYAN, bold=True)
        console_print(f"  Max races: {self.config.max_races or 'unlimited'}", Colors.DIM)
        console_print(f"  Mode: {'FAST (API injection)' if self.config.fast_mode else 'Real-time (MQTT)'}", Colors.DIM)
        console_print(f"  Press Ctrl+C to stop\n", Colors.DIM)
        logger.info(f"Starting race simulation (max_races={self.config.max_races or 'unlimited'})")

        try:
            while not self.shutdown_requested:
                # Check max races
                if self.config.max_races > 0 and self.race_count >= self.config.max_races:
                    console_print(f"\n[DONE] Completed {self.config.max_races} races", Colors.GREEN, bold=True)
                    logger.info(f"Reached max races ({self.config.max_races})")
                    break

                # Wait for staging
                if not self.wait_for_staging():
                    if self.shutdown_requested:
                        break
                    console_print("[ERROR] Failed to reach staging state, retrying...", Colors.RED)
                    logger.error("Failed to reach staging state")
                    continue

                # Run race
                self.race_count += 1
                logger.info(f"=== Race Simulation #{self.race_count} ===")

                if self.simulate_single_race():
                    console_print(f"  [OK] Race #{self.race_count} complete", Colors.GREEN)
                    logger.info(f"Race #{self.race_count} completed successfully")
                else:
                    console_print(f"  [FAIL] Race #{self.race_count} failed", Colors.RED)
                    logger.error(f"Race #{self.race_count} failed")
                    if self.shutdown_requested:
                        break

                # Delay between races
                if not self.shutdown_requested:
                    if self.config.fast_mode:
                        delay = 5.0  # Fixed 5s delay in fast mode for display updates
                    else:
                        delay = random.uniform(
                            self.config.between_race_min,
                            self.config.between_race_max
                        )
                    console_print(f"\n[PAUSE] Next race in {delay:.1f}s...", Colors.DIM)
                    logger.info(f"Waiting {delay:.2f}s before next race...")
                    time.sleep(delay)

        except KeyboardInterrupt:
            console_print("\n\n[INTERRUPT] Stopping simulation...", Colors.YELLOW)
            logger.info("Keyboard interrupt received")
        except Exception as e:
            console_print(f"\n[ERROR] Unexpected error: {e}", Colors.RED)
            logger.error(f"Unexpected error in simulation loop: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        console_print("\n[CLEANUP] Shutting down...", Colors.CYAN)
        logger.info("Cleaning up simulation...")

        # Stop heartbeat thread
        self.heartbeat_running = False
        if hasattr(self, 'heartbeat_thread') and self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=3)

        # Stop telemetry threads
        for timer in self.finish_timers.values():
            timer.stop_telemetry()

        # Disconnect MQTT
        try:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting MQTT: {e}")

        console_print(f"[SUMMARY] Completed {self.race_count} race(s)", Colors.GREEN, bold=True)
        logger.info(f"Simulation ended after {self.race_count} races")

    def request_shutdown(self):
        """Request graceful shutdown"""
        logger.info("Shutdown requested, finishing current operation...")
        self.shutdown_requested = True


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Race Simulation - MQTT-based hardware simulation',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Race timing
    parser.add_argument('--min-race-time', type=float, default=4.0,
                       help='Minimum race time for fastest finisher (seconds)')
    parser.add_argument('--max-race-time', type=float, default=8.0,
                       help='Maximum race time for slowest finisher (seconds)')
    parser.add_argument('--finish-spread', type=float, default=2.0,
                       help='Maximum time spread between fastest and slowest')

    # Delays
    parser.add_argument('--start-delay-min', type=float, default=1.0,
                       help='Minimum delay after staging before start')
    parser.add_argument('--start-delay-max', type=float, default=3.0,
                       help='Maximum delay after staging before start')
    parser.add_argument('--between-race-min', type=float, default=2.0,
                       help='Minimum delay between races')
    parser.add_argument('--between-race-max', type=float, default=5.0,
                       help='Maximum delay between races')

    # Hardware
    parser.add_argument('--lanes', type=int, default=3,
                       help='Number of lanes to simulate')
    parser.add_argument('--telemetry-interval', type=float, default=1.0,
                       help='Telemetry/heartbeat interval in seconds')

    # Behavior
    parser.add_argument('--max-races', type=int, default=0,
                       help='Maximum races to run (0=unlimited)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Dry run mode - log actions without sending MQTT')
    parser.add_argument('--fast', '-f', action='store_true',
                       help='Fast mode - inject times via API (~1s/race) instead of real-time MQTT')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose logging (DEBUG level)')

    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()

    # Adjust log level if verbose
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Print startup banner
    console_print(f"""
{Colors.CYAN}{'='*60}
  Derby Race Simulator v{VERSION}
  MQTT-based hardware simulation for DerbyNet
{'='*60}{Colors.RESET}
""", bold=True)

    logger.info(f"Derby Race Simulator v{VERSION} starting...")

    # Build configuration from arguments
    config = SimulationConfig(
        min_race_time=args.min_race_time,
        max_race_time=args.max_race_time,
        finish_spread=args.finish_spread,
        start_delay_min=args.start_delay_min,
        start_delay_max=args.start_delay_max,
        between_race_min=args.between_race_min,
        between_race_max=args.between_race_max,
        lane_count=args.lanes,
        telemetry_interval=args.telemetry_interval,
        max_races=args.max_races,
        dry_run=args.dry_run,
        fast_mode=args.fast,
    )

    # Create simulator
    simulator = RaceSimulator(config)

    # Set up signal handlers
    def signal_handler(signum, frame):
        simulator.request_shutdown()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Initialize connections
    if not simulator.setup():
        logger.critical("Failed to initialize simulator")
        sys.exit(1)

    # Run simulation
    simulator.run()

    logger.info("Derby Race Simulator shutdown complete")


if __name__ == "__main__":
    main()
