'''
Primary module for the Finish Timer plugin. Relies on the derbynetPCBv1 library and communicates over MQTT
'''


import json
import time
import paho.mqtt.client as mqtt # type: ignore
import random
import os
import queue
import threading
from datetime import datetime

from derbynetPCBv1 import derbyPCBv1
from derbylogger import setup_logger

###########################    SETUP    ###########################
logger = setup_logger(__name__)
logger.info("####### Starting DerbyNet Finish Timer #######")

try:
    pcb = derbyPCBv1()
    logger.info("PCB Initialized")
except Exception as e:
    logger.error(f"PCB Initialization failed: {e}")
    time.sleep(1)
    exit(1)

###########################    MQTT    ###########################
MQTT_BROKER         = "192.168.100.10"
MQTT_PORT           = 1883
MQTT_KEEPALIVE      = 10 # seconds
TELEMETRY_INTERVAL  = 2 # seconds

# Connection resilience settings
MQTT_MAX_RETRIES    = 10  # Maximum number of connection retry attempts
MQTT_RETRY_DELAY    = 5   # Initial delay between retries in seconds
MQTT_MAX_DELAY      = 300 # Maximum delay between retries in seconds

# Topics to publish to
TOGGLE_TOPIC        = "derbynet/device/{}/state"        # toggle state and timestamp
TELEMETRY_TOPIC     = "derbynet/device/{}/telemetry"    # telemetry data
STATUS_TOPIC        = "derbynet/device/{}/status"       # online/offline with will message

# Topics to subscribe to
LED_TOPIC           = "derbynet/lane/{}/led"            # set LED color
PINNY_TOPIC         = "derbynet/lane/{}/pinny"          # set pinny display
UPDATE_TOPIC        = "derbynet/device/{}/update"       # firmware update trigger message="update"

# Setup
clientid = f"{pcb.gethwid()}"#-{random.randint(1000, 9999)}"
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, clientid)
logger.debug(f"MQTT Client ID: {clientid}")

pinny   = "errr" # default pinny display
led     = "white" # default LED color


###########################    CALLBACKS    ###########################
def on_connect(client, userdata, flags, rc, properties=None):
    global mqtt_connected, mqtt_reconnect_timer
    if rc == 0:
        logger.info(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        mqtt_connected = True
        mqtt_reconnect_timer = None
        
        # Subscribe to topics
        client.subscribe(LED_TOPIC.format(pcb.get_Lane()))
        client.subscribe(PINNY_TOPIC.format(pcb.get_Lane()))
        client.subscribe(UPDATE_TOPIC.format(pcb.gethwid()))
        
        # Announce we're online
        client.publish(STATUS_TOPIC.format(pcb.gethwid()), "online", retain=True)
        
        # Sync state after reconnection
        sync_state_after_reconnect()
        
        # Process any queued messages
        process_offline_messages()
    else:
        logger.warning(f"Failed to connect to MQTT broker, return code: {rc}")
        # Connection failed, will retry automatically

def on_message(client, userdata, msg):
    logger.debug(f"Received message on topic {msg.topic} with payload {msg.payload}")
    parse_message(msg)

def on_disconnect(client, userdata, rc, properties=None):
    global mqtt_connected
    mqtt_connected = False
    
    if rc != 0:
        logger.warning(f"Unexpected disconnection from MQTT broker, code: {rc}")
    else:
        logger.info("Disconnected from MQTT broker")
        
    # Will attempt to reconnect automatically via connect_with_retry()

def initMQTT():
    global mqtt_connected, mqtt_reconnect_timer, mqtt_offline_queue
    
    # Initialize message queue for offline storage
    mqtt_offline_queue = queue.Queue()
    mqtt_connected = False
    mqtt_reconnect_timer = None
    
    # Set up client with persistent session
    client.will_set(STATUS_TOPIC.format(pcb.gethwid()), "offline", retain=True)
    client.on_connect = on_connect  
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    # Create data directory for offline storage if it doesn't exist
    os.makedirs("/var/lib/finishtimer/offline", exist_ok=True)
    
    # Start connection attempts with exponential backoff
    connect_with_retry()
    
    logger.debug("MQTT Client Initialized")
    
    # Start background thread for processing offline messages
    threading.Thread(target=process_offline_queue, daemon=True).start()

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
    
    # Store event before attempting to send
    store_critical_event("toggle", payload)
    
    # Publish with QoS 2 to ensure delivery
    publish_with_offline_support(TOGGLE_TOPIC.format(pcb.gethwid()), json.dumps(payload), qos=2, retain=True)
    send_telemetry()

def send_telemetry():
    payload = pcb.packageTelemetry()
    logger.debug(f"Sending Telemetry: {json.dumps(payload)}")
    
    # Add timestamp to payload
    payload["sent_timestamp"] = int(time.time())
    
    # Publish with offline support
    publish_with_offline_support(TELEMETRY_TOPIC.format(pcb.gethwid()), json.dumps(payload), qos=1, retain=True)
    publish_with_offline_support(STATUS_TOPIC.format(pcb.gethwid()), "online", qos=1, retain=True)

def parse_message(msg):
    # Parses out the subscribed topic and sets the appropriate value
    global led, pinny
    topic = msg.topic.split("/")[-1]
    if topic == "led":
        led = msg.payload.decode("utf-8").lower()
        pcb.setLED(led)
    elif topic == "pinny":
        pinny = msg.payload.decode("utf-8").lower()
        pcb.setPinny(pinny)
    elif topic == "update": # 
        logger.warning("Update requested")
        try:
            client.publish(STATUS_TOPIC.format(pcb.gethwid()), "updating", retain=True)
            pcb.update_pcb()
        except Exception as e:
            logger.error(f"Update failed: {e}")
    else:
        logger.warning(f"Unknown topic: {topic}")

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
    initMQTT()
    pcb.begin_toggle_watch(toggle_callback) #must init mqtt first
    try:
        while True:
            # Send regular telemetry updates
            send_telemetry()
            
            # Update LED and display
            pcb.setLED(led)
            pcb.setPinny(pinny)
            
            # Check connection status and attempt reconnection if needed
            if not mqtt_connected and client.is_connected():
                logger.info("MQTT connection reestablished")
                mqtt_connected = True
            elif not client.is_connected() and mqtt_connected:
                logger.warning("MQTT connection lost, initiating reconnection")
                mqtt_connected = False
                connect_with_retry()
                
            # Visual indicator of connection status
            if not mqtt_connected:
                flash_connection_status()
                
            # Check for any offline messages that need to be sent
            process_offline_messages()
                
            time.sleep(TELEMETRY_INTERVAL)
    except KeyboardInterrupt:
        shutdown(graceful=True)
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        shutdown(graceful=False, error_code="Err1")
    finally:
        shutdown(graceful=True)

###########################  RESILIENCE FUNCTIONS  ########################

# Maintains MQTT connection with exponential backoff
def connect_with_retry(first_attempt=True):
    global mqtt_reconnect_timer
    
    # Cancel any existing timer
    if mqtt_reconnect_timer:
        mqtt_reconnect_timer.cancel()
        mqtt_reconnect_timer = None
        
    # Set visual indicator of connection attempt
    if not first_attempt:
        pcb.setLED("yellow")
        pcb.setPinny("COnn")
        
    # Attempt connection
    try:
        logger.info(f"Connecting to MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
        client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
        client.loop_start()  # Start the network loop
        return True
    except Exception as e:
        # First connection attempt failure handling
        if first_attempt:
            logger.warning(f"Initial connection to MQTT broker failed: {e}, will retry")
            # Schedule first retry with initial delay
            mqtt_reconnect_timer = threading.Timer(MQTT_RETRY_DELAY, lambda: connect_with_retry(False))
            mqtt_reconnect_timer.daemon = True
            mqtt_reconnect_timer.start()
        else:
            # Subsequent failures - use exponential backoff
            retry_count = getattr(connect_with_retry, 'retry_count', 0) + 1
            connect_with_retry.retry_count = retry_count
            
            # Calculate delay with exponential backoff
            delay = min(MQTT_RETRY_DELAY * (2 ** (retry_count - 1)), MQTT_MAX_DELAY)
            
            logger.warning(f"MQTT connection attempt {retry_count}/{MQTT_MAX_RETRIES} failed: {e}")
            logger.info(f"Will retry in {delay} seconds")
            
            # Visual indicator of retry count
            pcb.setPinny(f"rt{retry_count:02d}")
            
            # Check if we've reached the retry limit
            if retry_count >= MQTT_MAX_RETRIES:
                logger.error("Maximum MQTT connection retries reached")
                # Reset retry count but continue trying with max delay
                connect_with_retry.retry_count = 0
                delay = MQTT_MAX_DELAY
            
            # Schedule next retry
            mqtt_reconnect_timer = threading.Timer(delay, lambda: connect_with_retry(False))
            mqtt_reconnect_timer.daemon = True
            mqtt_reconnect_timer.start()
        return False

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
        if client.is_connected():
            client.publish(STATUS_TOPIC.format(pcb.gethwid()), "offline", qos=1, retain=True)
    except Exception as e:
        logger.warning(f"Could not publish offline status: {e}")
    
    # Clean up resources
    pcb.close()
    client.loop_stop()
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

# Queue message when offline and send when online
def publish_with_offline_support(topic, payload, qos=0, retain=False):
    global mqtt_offline_queue
    
    # Try to publish immediately if connected
    if client.is_connected():
        result = client.publish(topic, payload, qos, retain)
        if result.rc != 0:
            logger.warning(f"Failed to publish to {topic}, queuing message. Error: {result.rc}")
            mqtt_offline_queue.put((topic, payload, qos, retain, time.time()))
    else:
        # Queue the message for later
        logger.debug(f"MQTT disconnected, queuing message for topic {topic}")
        mqtt_offline_queue.put((topic, payload, qos, retain, time.time()))
        
        # Also store to disk if it's a critical message
        if qos >= 1:
            store_message_to_disk(topic, payload, qos, retain)

# Process the offline message queue
def process_offline_messages():
    global mqtt_offline_queue
    
    if not client.is_connected():
        return
    
    # Process queued messages
    messages_processed = 0
    while not mqtt_offline_queue.empty() and messages_processed < 10:  # Process in batches
        try:
            topic, payload, qos, retain, timestamp = mqtt_offline_queue.get_nowait()
            age = time.time() - timestamp
            
            # Skip very old non-critical messages
            if age > 300 and qos == 0:  # 5 minutes for QoS 0
                logger.debug(f"Skipping old non-critical message for {topic}, age: {age:.1f}s")
                mqtt_offline_queue.task_done()
                continue
                
            # Publish the message
            logger.debug(f"Publishing queued message for {topic}, age: {age:.1f}s")
            result = client.publish(topic, payload, qos, retain)
            
            if result.rc != 0:
                logger.warning(f"Failed to publish queued message to {topic}, requeueing")
                mqtt_offline_queue.put((topic, payload, qos, retain, timestamp))
            
            mqtt_offline_queue.task_done()
            messages_processed += 1
            
        except queue.Empty:
            break

# Background thread for processing offline queue
def process_offline_queue():
    while True:
        time.sleep(5)  # Check periodically
        if client.is_connected():
            process_offline_messages()
            
            # Also check for stored messages
            process_stored_messages()

# Store critical event for later recovery
def store_critical_event(event_type, payload):
    # Store locally with timestamp for later reconciliation
    event_data = {
        "type": event_type,
        "payload": payload,
        "stored_time": time.time(),
        "processed": False
    }
    
    # Create unique filename based on timestamp
    filename = f"/var/lib/finishtimer/offline/{event_type}_{int(time.time()*1000)}.json"
    
    try:
        with open(filename, 'w') as f:
            json.dump(event_data, f)
        logger.debug(f"Stored critical {event_type} event to {filename}")
    except Exception as e:
        logger.error(f"Failed to store critical event: {e}")

# Store MQTT message to disk
def store_message_to_disk(topic, payload, qos, retain):
    message_data = {
        "topic": topic,
        "payload": payload,
        "qos": qos,
        "retain": retain,
        "timestamp": time.time()
    }
    
    filename = f"/var/lib/finishtimer/offline/mqtt_{int(time.time()*1000)}.json"
    
    try:
        with open(filename, 'w') as f:
            json.dump(message_data, f)
    except Exception as e:
        logger.error(f"Failed to store message to disk: {e}")

# Process stored messages from disk
def process_stored_messages():
    if not client.is_connected():
        return
        
    # Find all stored message files
    try:
        files = os.listdir("/var/lib/finishtimer/offline/")
        mqtt_files = [f for f in files if f.startswith("mqtt_") and f.endswith(".json")]
        
        for file in mqtt_files[:10]:  # Process in batches
            filepath = f"/var/lib/finishtimer/offline/{file}"
            try:
                with open(filepath, 'r') as f:
                    message_data = json.load(f)
                    
                # Publish the message
                topic = message_data["topic"]
                payload = message_data["payload"]
                qos = message_data["qos"]
                retain = message_data["retain"]
                
                logger.info(f"Publishing stored message for {topic} from {filepath}")
                result = client.publish(topic, payload, qos, retain)
                
                if result.rc == 0:
                    # Successfully published, remove the file
                    os.remove(filepath)
                else:
                    logger.warning(f"Failed to publish stored message, keeping file {filepath}")
            except Exception as e:
                logger.error(f"Error processing stored message {filepath}: {e}")
    except Exception as e:
        logger.error(f"Error accessing stored messages: {e}")

# Sync state after reconnection
def sync_state_after_reconnect():
    logger.info("Synchronizing state after reconnection")
    
    # Send current status information
    payload = pcb.packageTelemetry()
    payload["reconnection"] = True
    payload["offline_duration"] = getattr(sync_state_after_reconnect, 'last_disconnect_time', 0)
    
    # Publish with high QoS to ensure delivery
    client.publish(TELEMETRY_TOPIC.format(pcb.gethwid()), json.dumps(payload), qos=2)
    
    # Send current toggle state with high priority
    toggle_callback()

# Keep track of when we disconnect
def set_disconnect_time():
    sync_state_after_reconnect.last_disconnect_time = time.time()

###########################  MAIN ENTRY POINT  ########################

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        shutdown(graceful=True)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        shutdown(graceful=False, error_code="Err0")
