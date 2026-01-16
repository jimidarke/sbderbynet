"""
DerbyNet LED Sign Controller - Main Firmware

Single agnostic firmware for all LED sign controllers. Uses MAC address
as unique identifier. Zone assignment and configuration managed via MQTT.

Version: 1.0.0

Device States:
- UNCONFIGURED: Display MAC address, await zone assignment
- CONFIGURED: Display zone content, subscribed to zone topics
- OFFLINE: Display "CONNECTION LOST", attempt reconnection

Hardware:
- ESP32 DevKit
- BetaBrite LED sign via MAX3232 (Serial TX: GPIO17, RX: GPIO16)
"""

import gc
import time
import json
import machine
import network
import ubinascii

from umqtt.simple import MQTTClient

# Local imports
from config import (
    WIFI_SSID, WIFI_PASSWORD,
    DEFAULT_MQTT_BROKER, MQTT_PORT,
    TOPIC_PREFIX, DEVICE_TOPIC_PREFIX,
    SERIAL_BAUDRATE, SERIAL_TX_PIN, SERIAL_RX_PIN,
    TELEMETRY_INTERVAL, IDENTITY_INTERVAL, WATCHDOG_TIMEOUT, MAX_BACKOFF,
    PRIORITY_TIMEOUT,
    OTA_BASE_URL, OTA_FIRMWARE_FILE, OTA_BETABRITE_FILE,
    DEFAULT_MODE, DEFAULT_COLOR, DEFAULT_CHARSET, DEFAULT_POSITION, DEFAULT_SPEED,
    ERROR_MODE, ERROR_COLOR, ERROR_CHARSET,
    VERSION
)
from betabrite import BetaBrite, parse_display_config


# =============================================================================
# Device States
# =============================================================================

STATE_UNCONFIGURED = 'UNCONFIGURED'
STATE_CONFIGURED = 'CONFIGURED'
STATE_OFFLINE = 'OFFLINE'


# =============================================================================
# Global Variables
# =============================================================================

# Hardware
wdt = None  # Watchdog timer
uart = None  # Serial UART for BetaBrite
sign = None  # BetaBrite instance

# Network
wlan = None
mqtt_client = None
mqtt_broker = DEFAULT_MQTT_BROKER

# Device identity
mac_address = None
device_id = None

# Device state
device_state = STATE_UNCONFIGURED
assigned_zone = None
zone_display_name = None

# Timing
boot_time = 0
last_telemetry = 0
last_identity = 0

# Priority message handling
priority_active = False
priority_expires = 0

# Current display content (for returning after priority)
current_message = None
current_config = None


# =============================================================================
# Utility Functions
# =============================================================================

def get_mac_address():
    """Get MAC address as formatted string (AA:BB:CC:DD:EE:FF)"""
    mac_bytes = network.WLAN(network.STA_IF).config('mac')
    return ubinascii.hexlify(mac_bytes, ':').decode().upper()


def get_mac_short():
    """Get MAC address without colons for topic names"""
    return mac_address.replace(':', '')


def get_timestamp():
    """Get current Unix timestamp"""
    try:
        # MicroPython time is seconds since 2000-01-01
        # Add offset to get Unix timestamp (seconds since 1970-01-01)
        UNIX_EPOCH_OFFSET = 946684800
        return int(time.time()) + UNIX_EPOCH_OFFSET
    except Exception:
        return 0


def uptime_seconds():
    """Get uptime in seconds since boot"""
    return (time.ticks_ms() - boot_time) // 1000


def exponential_backoff(attempt):
    """Calculate exponential backoff delay"""
    delay = min(MAX_BACKOFF, (2 ** attempt))
    return delay


def log(message, level="INFO"):
    """Log message to console (and optionally syslog)"""
    timestamp = get_timestamp()
    print(f"[{level}] {timestamp} LEDSIGN: {message}")


# =============================================================================
# Hardware Initialization
# =============================================================================

def init_hardware():
    """Initialize hardware components"""
    global wdt, uart, sign, boot_time, mac_address, device_id

    boot_time = time.ticks_ms()

    # Initialize watchdog timer
    wdt = machine.WDT(timeout=WATCHDOG_TIMEOUT)
    log("Watchdog initialized")

    # Initialize UART for BetaBrite
    uart = machine.UART(2, baudrate=SERIAL_BAUDRATE, tx=SERIAL_TX_PIN, rx=SERIAL_RX_PIN)
    sign = BetaBrite(uart)
    log(f"UART initialized (TX:{SERIAL_TX_PIN}, RX:{SERIAL_RX_PIN}, {SERIAL_BAUDRATE}baud)")

    # Get MAC address
    mac_address = get_mac_address()
    device_id = get_mac_short()
    log(f"Device MAC: {mac_address}")

    # Show boot message on sign
    sign.write_text("BOOTING...", mode='hold', color='amber', charset='7high')

    wdt.feed()


# =============================================================================
# WiFi Connection
# =============================================================================

def connect_wifi():
    """Connect to WiFi network"""
    global wlan

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        log(f"Already connected to WiFi: {wlan.ifconfig()[0]}")
        return True

    log(f"Connecting to WiFi: {WIFI_SSID}")
    sign.write_text("WiFi...", mode='hold', color='amber', charset='7high')

    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    attempt = 0
    while not wlan.isconnected():
        wdt.feed()
        delay = exponential_backoff(attempt)
        log(f"Waiting for WiFi... (attempt {attempt + 1}, backoff {delay}s)")
        time.sleep(delay)
        attempt += 1

        if attempt > 10:
            log("WiFi connection failed after 10 attempts", "ERROR")
            sign.write_text("WiFi FAILED", mode='flash', color='red', charset='7high')
            time.sleep(5)
            machine.reset()

    ip = wlan.ifconfig()[0]
    log(f"WiFi connected: {ip}")
    sign.write_text(f"IP:{ip}", mode='hold', color='green', charset='5high')
    time.sleep(1)

    wdt.feed()
    return True


def check_wifi():
    """Check WiFi connection and reconnect if needed"""
    global wlan

    if wlan is None or not wlan.isconnected():
        log("WiFi disconnected, reconnecting...", "WARN")
        update_display_offline()
        connect_wifi()
        return False
    return True


# =============================================================================
# mDNS Service Discovery
# =============================================================================

def discover_mqtt_broker():
    """Attempt to discover MQTT broker via mDNS"""
    global mqtt_broker

    try:
        import mdns
        log("Attempting mDNS service discovery...")

        server = mdns.Server()
        services = server.query("_derbynet._tcp.local.")

        if services:
            service = services[0]
            mqtt_broker = service.ip()
            log(f"Discovered MQTT broker via mDNS: {mqtt_broker}")
            return True
        else:
            log("No mDNS services found, using default broker")
            return False

    except ImportError:
        log("mDNS library not available, using default broker")
        return False
    except Exception as e:
        log(f"mDNS discovery error: {e}", "ERROR")
        return False


# =============================================================================
# MQTT Connection and Handlers
# =============================================================================

def connect_mqtt():
    """Connect to MQTT broker"""
    global mqtt_client

    # Generate client ID
    client_id = f"ledsign-{device_id}"

    log(f"Connecting to MQTT broker: {mqtt_broker}:{MQTT_PORT}")
    sign.write_text("MQTT...", mode='hold', color='amber', charset='7high')

    attempt = 0
    while True:
        try:
            mqtt_client = MQTTClient(
                client_id,
                mqtt_broker,
                port=MQTT_PORT,
                keepalive=60
            )

            # Set callback for incoming messages
            mqtt_client.set_callback(on_mqtt_message)

            # Set Last Will Testament (offline status)
            lwt_topic = f"{DEVICE_TOPIC_PREFIX}/{device_id}/status"
            mqtt_client.set_last_will(lwt_topic, "offline", retain=True, qos=1)

            # Connect
            mqtt_client.connect()
            log("MQTT connected")

            # Subscribe to device-specific topics
            subscribe_device_topics()

            # Publish online status
            publish_status("online")

            # Publish identity for discovery
            publish_identity()

            wdt.feed()
            return True

        except Exception as e:
            log(f"MQTT connection failed: {e}", "ERROR")
            attempt += 1
            delay = exponential_backoff(attempt)

            if attempt > 10:
                log("MQTT connection failed after 10 attempts", "ERROR")
                sign.write_text("MQTT FAILED", mode='flash', color='red', charset='7high')
                time.sleep(5)
                machine.reset()

            # Try mDNS rediscovery every 3 attempts
            if attempt % 3 == 0:
                discover_mqtt_broker()

            time.sleep(delay)
            wdt.feed()


def subscribe_device_topics():
    """Subscribe to device-specific MQTT topics"""
    global mqtt_client

    # Topics all devices subscribe to (before zone assignment)
    topics = [
        f"{DEVICE_TOPIC_PREFIX}/{device_id}/config",    # Zone assignment
        f"{DEVICE_TOPIC_PREFIX}/{device_id}/message",   # Direct messages
        f"{DEVICE_TOPIC_PREFIX}/{device_id}/update",    # OTA updates
        f"{TOPIC_PREFIX}/broadcast",                     # Emergency broadcast
    ]

    for topic in topics:
        mqtt_client.subscribe(topic)
        log(f"Subscribed: {topic}")


def subscribe_zone_topics():
    """Subscribe to zone-specific topics after configuration"""
    global mqtt_client, assigned_zone

    if not assigned_zone:
        return

    # Zone message topic
    zone_topic = f"{TOPIC_PREFIX}/{assigned_zone}/message"
    mqtt_client.subscribe(zone_topic)
    log(f"Subscribed to zone: {zone_topic}")

    # Special subscriptions based on zone type
    if assigned_zone.startswith('usher-lane'):
        # Usher signs also subscribe to lane pinny topic
        lane_num = assigned_zone[-1]  # Get lane number
        pinny_topic = f"derbynet/lane/{lane_num}/pinny"
        mqtt_client.subscribe(pinny_topic)
        log(f"Subscribed to pinny: {pinny_topic}")

    if assigned_zone in ['registration', 'audience']:
        # These zones also get sponsor rotation
        sponsor_topic = f"{TOPIC_PREFIX}/sponsors/rotation"
        mqtt_client.subscribe(sponsor_topic)
        log(f"Subscribed to sponsors: {sponsor_topic}")


def on_mqtt_message(topic, msg):
    """Handle incoming MQTT messages"""
    global device_state, assigned_zone, zone_display_name
    global priority_active, priority_expires
    global current_message, current_config

    topic_str = topic.decode('utf-8')
    log(f"MQTT message on {topic_str}")

    try:
        # Parse JSON message (most messages are JSON)
        try:
            payload = json.loads(msg.decode('utf-8'))
        except (ValueError, UnicodeError):
            # Non-JSON payload (like pinny number)
            payload = msg.decode('utf-8')

        # Route message based on topic
        if topic_str.endswith('/config'):
            handle_config_message(payload)

        elif topic_str.endswith('/message') or topic_str == f"{TOPIC_PREFIX}/{assigned_zone}/message":
            handle_display_message(payload)

        elif topic_str == f"{TOPIC_PREFIX}/broadcast":
            handle_broadcast_message(payload)

        elif topic_str.endswith('/update'):
            handle_update_message(payload)

        elif topic_str.endswith('/pinny'):
            handle_pinny_message(payload)

        elif topic_str.endswith('/rotation'):
            handle_sponsor_rotation(payload)

        else:
            log(f"Unknown topic: {topic_str}", "WARN")

    except Exception as e:
        log(f"Error handling message: {e}", "ERROR")


def handle_config_message(payload):
    """Handle zone configuration message"""
    global device_state, assigned_zone, zone_display_name

    log(f"Config received: {payload}")

    if isinstance(payload, dict):
        new_zone = payload.get('zone')
        display_name = payload.get('display_name', new_zone)

        if new_zone:
            assigned_zone = new_zone
            zone_display_name = display_name
            device_state = STATE_CONFIGURED

            # Subscribe to zone-specific topics
            subscribe_zone_topics()

            # Show confirmation
            sign.write_text(f"CONFIGURED: {display_name}", mode='hold', color='green', charset='7high')
            log(f"Zone assigned: {assigned_zone} ({display_name})")
            time.sleep(2)

            # Publish updated identity
            publish_identity()

            # Show ready state for zone
            show_zone_ready()


def handle_display_message(payload):
    """Handle display message (zone or direct)"""
    global priority_active, priority_expires
    global current_message, current_config

    if not isinstance(payload, dict):
        # Simple text message
        sign.write_text(str(payload), mode=DEFAULT_MODE, color=DEFAULT_COLOR)
        return

    # Extract message components
    message = payload.get('message', '')
    priority = payload.get('priority', 2)
    display_config = payload.get('display_config', {})
    duration = display_config.get('duration', 0)

    # Check if this is a priority message
    is_priority = priority <= 1 or display_config.get('priority', False)

    if is_priority:
        # Priority message - use priority display
        priority_active = True
        if duration > 0:
            priority_expires = get_timestamp() + duration
        else:
            priority_expires = get_timestamp() + PRIORITY_TIMEOUT

        args = parse_display_config(display_config)
        sign.write_priority(message, **args)
        log(f"Priority message displayed: {message[:30]}...")

    else:
        # Normal message - store as current content
        current_message = message
        current_config = display_config

        # Only display if no active priority
        if not priority_active:
            args = parse_display_config(display_config)
            sign.write_text(message, **args)
            log(f"Display updated: {message[:30]}...")


def handle_broadcast_message(payload):
    """Handle emergency broadcast message"""
    global priority_active, priority_expires

    log("EMERGENCY BROADCAST RECEIVED", "WARN")

    if not isinstance(payload, dict):
        # Simple broadcast
        sign.write_priority(str(payload), mode='flash', color='red', charset='10high')
        priority_active = True
        priority_expires = 0  # No auto-expire for emergency
        return

    # Check for clear command
    if payload.get('clear', False) or not payload.get('message'):
        # Clear emergency broadcast
        sign.cancel_priority()
        priority_active = False
        log("Emergency broadcast cleared")

        # Return to normal display
        if current_message:
            args = parse_display_config(current_config or {})
            sign.write_text(current_message, **args)
        else:
            show_zone_ready()
        return

    # Display emergency message
    message = payload.get('message', 'EMERGENCY')
    display_config = payload.get('display_config', {})

    # Override with emergency defaults if not specified
    if 'mode' not in display_config and 'mode_code' not in display_config:
        display_config['mode'] = 'flash'
    if 'color' not in display_config and 'color_code' not in display_config:
        display_config['color'] = 'red'
    if 'charset' not in display_config and 'charset_code' not in display_config:
        display_config['charset'] = '10high'

    args = parse_display_config(display_config)
    sign.write_priority(message, **args)

    priority_active = True
    priority_expires = 0  # No auto-expire for emergency

    log(f"Emergency broadcast: {message}")


def handle_update_message(payload):
    """Handle OTA update request"""
    log("OTA update requested")
    sign.write_text("UPDATING...", mode='flash', color='amber', charset='7high')

    try:
        perform_ota_update()
    except Exception as e:
        log(f"OTA update failed: {e}", "ERROR")
        sign.write_text("UPDATE FAILED", mode='flash', color='red', charset='7high')
        time.sleep(3)


def handle_pinny_message(payload):
    """Handle pinny number update (for usher signs)"""
    global current_message, current_config

    pinny = str(payload).strip()
    log(f"Pinny update: {pinny}")

    # For usher signs, display the pinny number
    # The full racer info will come via zone message
    # This is just for quick updates
    if not priority_active:
        current_message = f"#{pinny}"
        current_config = {'mode': 'hold', 'color': 'green', 'charset': '10high'}
        sign.write_text(current_message, **current_config)


def handle_sponsor_rotation(payload):
    """Handle sponsor rotation content"""
    global current_message, current_config

    if not isinstance(payload, dict):
        return

    sponsors = payload.get('sponsors', [])
    if not sponsors:
        return

    # Store sponsors for rotation (simplified - just use first one for now)
    # Full rotation would need a separate timer/task
    sponsor = sponsors[0]
    message = sponsor.get('message', '')
    display_config = sponsor.get('display_config', {})

    # Only display if not in active race state and no priority
    if not priority_active and device_state == STATE_CONFIGURED:
        current_message = message
        current_config = display_config
        args = parse_display_config(display_config)
        sign.write_text(message, **args)
        log(f"Sponsor display: {message[:30]}...")


# =============================================================================
# MQTT Publishing
# =============================================================================

def publish_status(status):
    """Publish device status"""
    topic = f"{DEVICE_TOPIC_PREFIX}/{device_id}/status"
    mqtt_client.publish(topic, status, retain=True, qos=1)
    log(f"Status published: {status}")


def publish_identity():
    """Publish device identity for discovery"""
    global last_identity

    topic = f"{DEVICE_TOPIC_PREFIX}/{device_id}/identity"

    identity = {
        "mac": mac_address,
        "ip": wlan.ifconfig()[0] if wlan else "0.0.0.0",
        "version": VERSION,
        "uptime": uptime_seconds(),
        "configured": device_state == STATE_CONFIGURED,
        "zone": assigned_zone,
        "display_name": zone_display_name,
        "timestamp": get_timestamp()
    }

    payload = json.dumps(identity)
    mqtt_client.publish(topic, payload, retain=True, qos=1)
    last_identity = get_timestamp()
    log("Identity published")


def publish_telemetry():
    """Publish device telemetry"""
    global last_telemetry

    topic = f"{DEVICE_TOPIC_PREFIX}/{device_id}/telemetry"

    # Collect telemetry data
    telemetry = {
        "mac": mac_address,
        "hostname": f"ledsign-{device_id[-6:]}",
        "hwid": device_id,
        "version": VERSION,
        "uptime": uptime_seconds(),
        "ip": wlan.ifconfig()[0] if wlan else "0.0.0.0",
        "wifi_rssi": wlan.status('rssi') if wlan else 0,
        "memory_free": gc.mem_free(),
        "memory_usage": round((1 - gc.mem_free() / gc.mem_alloc()) * 100, 1) if gc.mem_alloc() > 0 else 0,
        "state": device_state,
        "zone": assigned_zone,
        "priority_active": priority_active,
        "timestamp": get_timestamp()
    }

    payload = json.dumps(telemetry)
    mqtt_client.publish(topic, payload, retain=True, qos=1)
    last_telemetry = get_timestamp()


# =============================================================================
# Display State Management
# =============================================================================

def show_unconfigured():
    """Show unconfigured state - display MAC address"""
    global device_state
    device_state = STATE_UNCONFIGURED

    # Display MAC address for discovery
    display_mac = mac_address.replace(':', '')[-8:]  # Last 8 chars for readability
    sign.write_text(f"SETUP:{display_mac}", mode='hold', color='amber', charset='7high')
    log(f"Showing unconfigured state: {mac_address}")


def show_zone_ready():
    """Show zone-appropriate ready state"""
    if not assigned_zone:
        show_unconfigured()
        return

    # Default ready message based on zone type
    if assigned_zone == 'starter':
        sign.write_text("READY", mode='hold', color='green', charset='10high')
    elif assigned_zone.startswith('usher'):
        sign.write_text("WAITING", mode='hold', color='green', charset='7high')
    elif assigned_zone.startswith('finish'):
        sign.write_text("--:--.---", mode='hold', color='green', charset='10high')
    elif assigned_zone in ['registration', 'audience']:
        sign.write_text("DERBYNET", mode='scroll', color='rainbow1', charset='7high')
    else:
        sign.write_text("READY", mode='hold', color='green', charset='7high')


def update_display_offline():
    """Update display to show offline state"""
    global device_state
    device_state = STATE_OFFLINE
    sign.write_text("CONNECTION LOST", mode='flash', color='red', charset='7high')
    log("Display showing offline state")


def check_priority_timeout():
    """Check if priority message has expired"""
    global priority_active, priority_expires

    if priority_active and priority_expires > 0:
        if get_timestamp() >= priority_expires:
            log("Priority message expired")
            sign.cancel_priority()
            priority_active = False

            # Return to normal display
            if current_message:
                args = parse_display_config(current_config or {})
                sign.write_text(current_message, **args)
            else:
                show_zone_ready()


# =============================================================================
# OTA Update
# =============================================================================

def perform_ota_update():
    """Perform OTA firmware update"""
    import urequests

    publish_status("updating")

    files_to_update = [
        (OTA_FIRMWARE_FILE, '/main.py'),
        (OTA_BETABRITE_FILE, '/betabrite.py'),
    ]

    for remote_file, local_path in files_to_update:
        url = f"{OTA_BASE_URL}/{remote_file}"
        log(f"Downloading: {url}")

        try:
            response = urequests.get(url)
            if response.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                log(f"Updated: {local_path}")
            else:
                log(f"Download failed ({response.status_code}): {url}", "ERROR")
            response.close()
        except Exception as e:
            log(f"Download error: {e}", "ERROR")

    log("OTA update complete, rebooting...")
    sign.write_text("REBOOTING...", mode='hold', color='green', charset='7high')
    time.sleep(2)
    machine.reset()


# =============================================================================
# Main Loop
# =============================================================================

def main_loop():
    """Main application loop"""
    global last_telemetry, last_identity

    log("Entering main loop")

    # Show initial state
    if device_state == STATE_UNCONFIGURED:
        show_unconfigured()

    while True:
        try:
            wdt.feed()

            # Check WiFi connection
            if not check_wifi():
                continue

            # Check MQTT connection
            try:
                mqtt_client.check_msg()
            except Exception as e:
                log(f"MQTT error: {e}", "ERROR")
                update_display_offline()
                connect_mqtt()
                continue

            # Check priority message timeout
            check_priority_timeout()

            # Periodic telemetry
            now = get_timestamp()
            if now - last_telemetry >= TELEMETRY_INTERVAL:
                try:
                    publish_telemetry()
                except Exception as e:
                    log(f"Telemetry error: {e}", "ERROR")

            # Periodic identity broadcast (for discovery)
            if now - last_identity >= IDENTITY_INTERVAL:
                try:
                    publish_identity()
                except Exception as e:
                    log(f"Identity error: {e}", "ERROR")

            # Small delay to prevent busy loop
            time.sleep(0.1)

        except KeyboardInterrupt:
            log("Interrupted by user")
            break
        except Exception as e:
            log(f"Main loop error: {e}", "ERROR")
            time.sleep(1)


# =============================================================================
# Application Entry Point
# =============================================================================

def main():
    """Application entry point"""
    log(f"DerbyNet LED Sign Controller v{VERSION}")
    log("=" * 40)

    try:
        # Initialize hardware
        init_hardware()

        # Connect to WiFi
        connect_wifi()

        # Discover MQTT broker (mDNS)
        discover_mqtt_broker()

        # Connect to MQTT
        connect_mqtt()

        # Run main loop
        main_loop()

    except Exception as e:
        log(f"Fatal error: {e}", "ERROR")
        if sign:
            sign.write_text("FATAL ERROR", mode='flash', color='red', charset='7high')
        time.sleep(5)
        machine.reset()

    finally:
        log("Shutting down")
        if mqtt_client:
            try:
                publish_status("offline")
                mqtt_client.disconnect()
            except Exception:
                pass


# Run main
if __name__ == '__main__':
    main()
