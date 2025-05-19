
import json
import subprocess
import time
import random
import sys
import os
import uuid
import psutil # type: ignore

# Version information
VERSION = "0.5.0"  # Standardized version

'''
Version History:
- 0.5.0 - May 19, 2025 - Standardized version schema across all components
- 0.4.0 - May 10, 2025 - Added service discovery via mDNS for dynamic MQTT broker configuration
- 0.3.0 - April 22, 2025 - Added remote syslogging and improved error handling
- 0.2.0 - April 15, 2025 - Added telemetry and status reporting
- 0.1.0 - April 4, 2025 - Added MQTT communication protocols
- 0.0.1 - March 31, 2025 - Initial implementation
'''

time.sleep(10)

###########################    SETUP    ###########################
# Import derbynet module for standardized networking and service discovery
sys.path.append(os.path.join(os.path.dirname(__file__), "../../common"))
from derbylogger import setup_logger
from derbynet import MQTTClient, DeviceTelemetry, discover_services

logger = setup_logger(__name__)

logger.info(f"####### Starting DerbyNet DerbyDisplay v{VERSION} #######")

###########################    MQTT    ###########################
# Default values - will be overridden by service discovery
DEFAULT_MQTT_BROKER = "192.168.100.10"
DEFAULT_MQTT_PORT = 1883
TELEMETRY_INTERVAL = 5 # seconds

# Topics to publish to
TOGGLE_TOPIC    = "derbynet/device/{}/state"        # toggle state and timestamp
TELEMETRY_TOPIC = "derbynet/device/{}/telemetry"    # telemetry data
STATUS_TOPIC    = "derbynet/device/{}/status"       # online/offline with will message

# Topics to subscribe to
UPDATE_TOPIC    = "derbynet/device/{}/update"       # firmware update trigger message="update"

if os.path.exists("/boot/firmware/derbyid.txt"):
    with open("/boot/firmware/derbyid.txt", "r") as f:
        hwid = f.read().strip()
else:
    hwid = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)])
logger.debug(f"HWID: {hwid}")

# First, try to discover MQTT broker using service discovery
logger.info("Attempting to discover MQTT broker using mDNS...")
services = discover_services("_derbynet._tcp.local.", timeout=3)
mqtt_broker = DEFAULT_MQTT_BROKER
mqtt_port = DEFAULT_MQTT_PORT

if services:
    # Find MQTT service
    for name, service in services.items():
        if "mqtt" in name.lower() or "broker" in name.lower():
            mqtt_broker = service["ip"]
            mqtt_port = service["port"]
            logger.info(f"Discovered MQTT broker: {mqtt_broker}:{mqtt_port}")
            break
else:
    logger.warning(f"No services discovered, using default broker: {mqtt_broker}:{mqtt_port}")

# Setup MQTTClient from derbynet library
logger.debug(f"MQTT Client ID: {hwid}")
client = MQTTClient(hwid, broker=mqtt_broker, port=mqtt_port)

# Register callbacks for our specific topics
def on_update(topic, payload):
    logger.debug(f"Received update request: {payload}")
    # Handle update message here
    
# Subscribe to our topic with callback
client.subscribe(UPDATE_TOPIC.format(hwid), on_update)

# Connect with auto-reconnect
client.connect()

# Publish initial status
client.publish(STATUS_TOPIC.format(hwid), "online", retain=True)

def send_telemetry():
    '''
    Use the standardized DeviceTelemetry class from derbynet module
    to collect and send telemetry data
    '''
    # Create telemetry collector
    telemetry = DeviceTelemetry(hwid, "display")
    
    # Collect standard telemetry
    payload = telemetry.collect()
    
    # Add display-specific telemetry
    payload["version"] = VERSION
    payload["time"] = int(time.time())
    
    # Send telemetry
    logger.debug(f"Sending Telemetry: {json.dumps(payload)}")
    client.publish(TELEMETRY_TOPIC.format(hwid), json.dumps(payload), qos=1, retain=True)
    client.publish(STATUS_TOPIC.format(hwid), "online", retain=True)

###########################     MAIN     ###########################
def main():
    """
    Main loop for the Derby Display service
    - Sends telemetry at regular intervals
    - MQTTClient handles reconnection automatically
    """
    try:
        while True:
            send_telemetry()
            time.sleep(TELEMETRY_INTERVAL)
    except KeyboardInterrupt:
        logger.info("Exiting")
        # Clean disconnect
        client.disconnect()
        exit(0)
    except Exception as e:
        logger.error(f"Error: {e}")
        exit(1)
    finally:
        # Ensure we disconnect properly
        client.disconnect()
        exit(0)

if __name__ == "__main__":
    main()
