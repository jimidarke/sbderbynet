'''
Primary module for the Finish Timer plugin. Relies on the derbynetPCBv1 library and communicates over MQTT
Uses service discovery for improved resilience 

Version History:
- 0.8.0 - Dec 12, 2025 - Standardized version across all soapbox components
- 0.6.4 - Dec 09, 2025 - Fixed toggle state debouncing
- 0.6.3 - Dec 08, 2025 - Fixed rsyslog TAG/programname for unified logging
- 0.6.2 - Dec 08, 2025 - Simplified boot sequence: show version then lane with LED cycle
- 0.6.1 - Dec 08, 2025 - Unified logging system integration 
- 0.6.0 - May 25, 2025 - Fixed the AI logging crap and added more robust error handling
- 0.5.1 - May 22, 2025 - Enhanced logging system with improved source file/line tracking and rsyslog integration
- 0.5.0 - May 19, 2025 - Standardized version schema across all components
'''

VERSION = "0.8.0"

import json
import time
import random
import os
import queue
import threading
import sys
from datetime import datetime
import logging

# Add parent directory to path for importing common modules
#sys.path.append(os.path.dirname(__file__))
from derbynetPCBv1 import derbyPCBv1
from nodelogger import NodeLogger
from derbynet import MQTTClient, DeviceTelemetry

###########################    SETUP    ###########################
# Set up logger with centralized configuration
logger = NodeLogger(
    name='finishtimer',
    log_file='/var/log/derbynet.log',
    level=logging.INFO,  # Default log level
).get_logger()

try:
    pcb = derbyPCBv1()
    logger.info(f"Finish Timer initialized on lane {pcb.get_Lane()}")
except Exception as e:
    logger.error(f"Failed to initialize PCB: {e}")
    time.sleep(1)
    exit(1)

###########################    MQTT    ###########################

DEFAULT_MQTT_BROKER = "192.168.100.10"
DEFAULT_MQTT_PORT = 1883
TELEMETRY_INTERVAL = 1 # seconds - tightened for faster is-ready detection

# Topics to publish to
TOGGLE_TOPIC        = "derbynet/device/{}/state"        # toggle state and timestamp
TELEMETRY_TOPIC     = "derbynet/device/{}/telemetry"    # telemetry data
STATUS_TOPIC        = "derbynet/device/{}/status"       # online/offline with will message

# Topics to subscribe to
LED_TOPIC           = "derbynet/lane/{}/led"            # set LED color
PINNY_TOPIC         = "derbynet/lane/{}/pinny"          # set pinny display
UPDATE_TOPIC        = "derbynet/device/{}/update"       # firmware update trigger message="update"

# Default display values
pinny = "0000" # default pinny display
led = "white" # default LED color

# Setup MQTTClient from derbynet library with auto-reconnect
client = MQTTClient(pcb.gethwid(), broker=DEFAULT_MQTT_BROKER, port=DEFAULT_MQTT_PORT)

# Define callbacks for specific topics
def on_led_message(topic, payload):
    global led
    if isinstance(payload, str):
        led_value = payload.lower()
    else:
        led_value = str(payload).lower()
    logger.debug(f"Setting LED to: {led_value}")
    led = led_value
    pcb.setLED(led)

def on_pinny_message(topic, payload):
    global pinny
    if isinstance(payload, str):
        pinny_value = payload
    else:
        pinny_value = str(payload)
    logger.debug(f"Setting pinny to: {pinny_value}")
    pinny = pinny_value
    pcb.setPinny(pinny)

def on_update_message(topic, payload):
    if isinstance(payload, str) and "update" in payload.lower():
        logger.warning("Update requested")
        try:
            pcb.update_pcb()
        except Exception as e:
            logger.error(f"Update failed: {e}")

def initMQTT():
    
    # Subscribe to topics
    client.subscribe(LED_TOPIC.format(pcb.get_Lane()), on_led_message)
    client.subscribe(PINNY_TOPIC.format(pcb.get_Lane()), on_pinny_message)
    client.subscribe(UPDATE_TOPIC.format(pcb.gethwid()), on_update_message)
    
    # Connect with auto-reconnect
    client.connect()
    
    # Initial status
    client.publish(STATUS_TOPIC.format(pcb.gethwid()), "online", retain=True)
    
    logger.debug("MQTT Client Initialized")


###########################    HELPERS    ###########################
def toggle_callback():
    togglestate = pcb.getToggleState()
    logger.info("Toggle Changed to: " + str(togglestate))
    nowtime = int(time.time())
    hwid = pcb.gethwid()
    dip = pcb.readDIP()
    lane = pcb.get_Lane()
    payload = {
        "toggle": togglestate,
        "timestamp": nowtime,
        "hwid": hwid,
        "dip": dip,
        "lane": lane
    }
    logger.debug(f"Sending Toggle: {json.dumps(payload)}")
    
    # Publish with QoS 2 to ensure delivery
    client.publish(TOGGLE_TOPIC.format(pcb.gethwid()), json.dumps(payload), qos=2, retain=True)
    
    # Update telemetry 
    send_telemetry()

def send_telemetry():    
    payload = pcb.packageTelemetry()

    # Add timestamp
    payload["sent_timestamp"] = int(time.time())
    
    logger.debug(f"Sending Telemetry: {json.dumps(payload)}")
    
    # Publish using MQTTClient (handles offline queuing automatically)
    client.publish(TELEMETRY_TOPIC.format(pcb.gethwid()), json.dumps(payload), qos=1, retain=True)
    client.publish(STATUS_TOPIC.format(pcb.gethwid()), "online", qos=1, retain=True)

def post_sequence(): # runs through a sequence of LED colors and pinny displays
    logger.info("Running post sequence")

    # Extract version number for display (e.g., "0.6.2" -> "0062" for 4-digit display)
    version_parts = VERSION.split('.')
    version_display = "".join(part.zfill(1) for part in version_parts[:3]).zfill(4)[-4:]  # e.g., "0062"

    # Show version for 2 seconds
    pcb.setLED("white", False)
    pcb.setPinny(version_display, False)
    logger.info(f"Displaying version: {VERSION} as {version_display}")
    time.sleep(2)

    # Show lane number while cycling through LED colors (10 seconds total)
    lanestr = "LAN" + str(int(pcb.get_Lane()))
    led_sequence = ["red", "green", "blue", "purple", "yellow", "white"]
    led_duration = 10.0 / len(led_sequence)  # ~1.67 seconds per color

    for led_color in led_sequence:
        pcb.setLED(led_color, False)
        pcb.setPinny(lanestr, False)
        time.sleep(led_duration)    

###########################     MAIN     ###########################
def main():
    global led, pinny
    
    logger.info("Starting Finish Timer Main Loop")
    post_sequence()
    
    lane = pcb.get_Lane()
    logger.info(f"Lane: {lane}")
    
    # Initialize MQTT connection
    initMQTT()
    
    # Set up toggle watch callback
    pcb.begin_toggle_watch(toggle_callback)
    
    try:
        last_telemetry_time = 0
        while True:
            # Connection check
            if not client.connected:
                logger.warning("Connection to MQTT broker lost. Could be network issue or broker down. Reconnection will be attempted automatically.")
                pcb.networkError()
                time.sleep(1)
            else:
                # Update LED and display
                pcb.setLED(led)
                pcb.setPinny(pinny)
                if last_telemetry_time + TELEMETRY_INTERVAL < time.time():# Send regular telemetry updates
                    last_telemetry_time = time.time()    
                    send_telemetry()
            time.sleep(0.5)
    except KeyboardInterrupt:
        shutdown(graceful=True)
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        shutdown(graceful=False, error_code="Err1")
    finally:
        shutdown(graceful=True)

###########################  RESILIENCE FUNCTIONS  ########################

# Graceful shutdown function
def shutdown(graceful=True, error_code=None):
    logger.info(f"Shutting down finish timer {'gracefully' if graceful else 'with errors'}")
    
    # Send offline status if possible
    try:
        client.publish(STATUS_TOPIC.format(pcb.gethwid()), "offline", qos=1, retain=True)
    except Exception as e:
        logger.warning(f"Could not publish offline status: {e}")
    
    # Clean up resources
    pcb.close()
    client.disconnect()
    
    # Set final visual indicator
    pcb.setLED("yellow")
    if error_code:
        pcb.setPinny(error_code)
    else:
        pcb.setPinny("----")
    
    time.sleep(1)  # Give time for final MQTT messages to be sent
    
    # Exit with appropriate code
    exit(0 if graceful else 1)

###########################  MAIN ENTRY POINT  ########################

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        shutdown(graceful=True)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        shutdown(graceful=False, error_code="Err0")
