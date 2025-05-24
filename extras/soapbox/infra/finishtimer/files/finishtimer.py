'''
Primary module for the Finish Timer plugin. Relies on the derbynetPCBv1 library and communicates over MQTT
Uses service discovery for improved resilience

VERSION = "0.5.1"
  
Version History:
- 0.5.1 - May 22, 2025 - Enhanced logging system with improved source file/line tracking and rsyslog integration
- 0.5.0 - May 19, 2025 - Standardized version schema across all components
'''

import json
import time
import random
import os
import queue
import threading
import sys
from datetime import datetime

# Add parent directory to path for importing common modules
sys.path.append(os.path.dirname(__file__))
from derbynetPCBv1 import derbyPCBv1
from derbylogger import setup_logger, get_logger
from derbynet import MQTTClient, DeviceTelemetry, discover_services

###########################    SETUP    ###########################
# Set up logger with centralized configuration
setup_logger("FinishTimer", use_centralized_config=True)  # Configure logger for this component
logger = get_logger(__name__) # Get logger instance for this module
logger.debug("DerbyNet PCB Class Loaded") 
logger.info("####### Starting DerbyNet Finish Timer #######")

try:
    pcb = derbyPCBv1()
    logger.info("PCB Initialized")
except Exception as e:
    logger.error(f"PCB Initialization failed: {e}")
    time.sleep(1)
    exit(1)

###########################    MQTT    ###########################
# Default values - will be overridden by service discovery
DEFAULT_MQTT_BROKER = "192.168.100.10"
DEFAULT_MQTT_PORT = 1883
TELEMETRY_INTERVAL = 2 # seconds

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

# Topics to publish to
TOGGLE_TOPIC        = "derbynet/device/{}/state"        # toggle state and timestamp
TELEMETRY_TOPIC     = "derbynet/device/{}/telemetry"    # telemetry data
STATUS_TOPIC        = "derbynet/device/{}/status"       # online/offline with will message

# Topics to subscribe to
LED_TOPIC           = "derbynet/lane/{}/led"            # set LED color
PINNY_TOPIC         = "derbynet/lane/{}/pinny"          # set pinny display
UPDATE_TOPIC        = "derbynet/device/{}/update"       # firmware update trigger message="update"

# Default display values
pinny = "errr" # default pinny display
led = "white" # default LED color

# Globals for state management
mqtt_connected = False

###########################    MQTT SETUP    ###########################

# Create data directory for offline storage if it doesn't exist
os.makedirs("/var/lib/finishtimer/offline", exist_ok=True)

# Setup MQTTClient from derbynet library with auto-reconnect
client = MQTTClient(pcb.gethwid(), broker=mqtt_broker, port=mqtt_port)

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
        pinny_value = payload.lower()
    else:
        pinny_value = str(payload).lower()
    logger.debug(f"Setting pinny to: {pinny_value}")
    pinny = pinny_value
    pcb.setPinny(pinny)

def on_update_message(topic, payload):
    if isinstance(payload, str) and "update" in payload.lower():
        logger.warning("Update requested")
        try:
            client.publish(STATUS_TOPIC.format(pcb.gethwid()), "updating", retain=True)
            pcb.update_pcb()
        except Exception as e:
            logger.error(f"Update failed: {e}")

def initMQTT():
    global mqtt_connected
    
    # Subscribe to topics
    client.subscribe(LED_TOPIC.format(pcb.get_Lane()), on_led_message)
    client.subscribe(PINNY_TOPIC.format(pcb.get_Lane()), on_pinny_message)
    client.subscribe(UPDATE_TOPIC.format(pcb.gethwid()), on_update_message)
    
    # Connect with auto-reconnect
    client.connect()
    
    # Initial status
    client.publish(STATUS_TOPIC.format(pcb.gethwid()), "online", retain=True)
    
    logger.debug("MQTT Client Initialized")
    mqtt_connected = True

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
    # Get device telemetry
    telemetry = DeviceTelemetry(pcb.gethwid(), "finishtimer")
    payload = telemetry.collect()
    
    # Add PCB-specific telemetry
    pcb_telemetry = pcb.packageTelemetry()
    payload.update(pcb_telemetry)
    
    # Add timestamp
    payload["sent_timestamp"] = int(time.time())
    
    logger.debug(f"Sending Telemetry: {json.dumps(payload)}")
    
    # Publish using MQTTClient (handles offline queuing automatically)
    client.publish(TELEMETRY_TOPIC.format(pcb.gethwid()), json.dumps(payload), qos=1, retain=True)
    client.publish(STATUS_TOPIC.format(pcb.gethwid()), "online", qos=1, retain=True)

def post_sequence(): # runs through a sequence of LED colors and pinny displays 
    logger.debug("Running post sequence")
    led_sequence = ["white", "red", "green", "blue", "purple", "yellow"]
    lanestr = "LAN" + str(int(pcb.get_Lane()))
    pinny_sequence = ["----", "err-", "stop", "0000", "batt", lanestr]
    for i in range(len(led_sequence)):
        led = led_sequence[i]
        pinny = pinny_sequence[i]
        pcb.setLED(led, False)
        pcb.setPinny(pinny, False)
        time.sleep(1)
    time.sleep(5)    

###########################     MAIN     ###########################
def main():
    global led, pinny
    
    logger.info("Starting Finish Timer Main Loop")
    logger.debug("Running post sequence")
    post_sequence()
    
    logger.debug("Setting up PCB Callbacks")
    lane = pcb.get_Lane()
    logger.info(f"Lane: {lane}")
    pcb.setPinny("LAN" + str(int(lane)))
    
    # Initialize MQTT connection
    initMQTT()
    
    # Set up toggle watch callback
    pcb.begin_toggle_watch(toggle_callback)
    
    try:
        while True:
            # Send regular telemetry updates
            send_telemetry()
            
            # Update LED and display
            pcb.setLED(led)
            pcb.setPinny(pinny)
            
            # Visual indicator if not connected
            if not client.connected:
                flash_connection_status()
                
            time.sleep(TELEMETRY_INTERVAL)
    except KeyboardInterrupt:
        shutdown(graceful=True)
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        shutdown(graceful=False, error_code="Err1")
    finally:
        shutdown(graceful=True)

###########################  RESILIENCE FUNCTIONS  ########################

# Flash LED to indicate connection status
def flash_connection_status():
    # Briefly flash the LED to indicate connection attempt
    current_led = pcb.led
    pcb.setLED("yellow", False)
    time.sleep(0.1)
    pcb.setLED(current_led, False)

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
    
    time.sleep(2)  # Give time for final MQTT messages to be sent
    
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
