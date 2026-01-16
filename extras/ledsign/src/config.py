"""
LED Sign Controller Configuration

Hardcoded configuration for ESP32 LED sign controllers.
Same configuration used across all devices (single agnostic firmware).

Version: 1.0.0
"""

# =============================================================================
# WiFi Configuration (hardcoded - same as other edge devices)
# =============================================================================

WIFI_SSID = "DerbyNet"
WIFI_PASSWORD = "all4theKids"

# =============================================================================
# MQTT Configuration
# =============================================================================

# Default broker (mDNS discovery will override if available)
DEFAULT_MQTT_BROKER = "192.168.100.10"
MQTT_PORT = 1883

# MQTT topic prefixes
TOPIC_PREFIX = "derbynet/ledsign"
DEVICE_TOPIC_PREFIX = "derbynet/ledsign/device"

# =============================================================================
# Serial Configuration (BetaBrite connection)
# =============================================================================

SERIAL_BAUDRATE = 9600
SERIAL_TX_PIN = 17  # GPIO17 (UART2 TX)
SERIAL_RX_PIN = 16  # GPIO16 (UART2 RX)

# =============================================================================
# Timing Configuration
# =============================================================================

# Telemetry interval (seconds)
TELEMETRY_INTERVAL = 10

# Identity broadcast interval (seconds) - for device discovery
IDENTITY_INTERVAL = 30

# Watchdog timeout (milliseconds)
WATCHDOG_TIMEOUT = 60000  # 1 minute

# WiFi/MQTT reconnect backoff max (seconds)
MAX_BACKOFF = 60

# Priority message default timeout (seconds)
PRIORITY_TIMEOUT = 60

# =============================================================================
# OTA Configuration
# =============================================================================

OTA_BASE_URL = "http://192.168.100.10/ledsign"
OTA_FIRMWARE_FILE = "main.py"
OTA_BETABRITE_FILE = "betabrite.py"

# =============================================================================
# Display Defaults
# =============================================================================

# Default display settings for unconfigured state
DEFAULT_MODE = 'hold'
DEFAULT_COLOR = 'green'
DEFAULT_CHARSET = '7high'
DEFAULT_POSITION = 'fill'
DEFAULT_SPEED = 2

# Error display settings
ERROR_MODE = 'flash'
ERROR_COLOR = 'red'
ERROR_CHARSET = '7high'

# =============================================================================
# Version
# =============================================================================

VERSION = "1.0.0"
