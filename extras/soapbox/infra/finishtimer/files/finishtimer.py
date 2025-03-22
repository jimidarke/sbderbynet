'''
Primary module for the Finish Timer plugin. Relies on the derbynetPCBv1 library and communicates over MQTT
'''

import logging
import json
import time
import paho.mqtt.client as mqtt # type: ignore
import random

from derbynetPCBv1 import derbyPCBv1

###########################    SETUP    ###########################
LOG_FORMAT      = '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] %(message)s'
LOG_FILE        = '/var/log/derbynet.log'

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, filename=LOG_FILE)
logging.info("####### Starting DerbyNet Finish Timer #######")

pcb = derbyPCBv1()

###########################    MQTT    ###########################
MQTT_BROKER = "192.168.100.10"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 120
TELEMETRY_INTERVAL = 10 # seconds

# Topics to publish to
TOGGLE_TOPIC    = "derbynet/device/{}/state"        # toggle state and timestamp
TELEMETRY_TOPIC = "derbynet/device/{}/telemetry"    # telemetry data
STATUS_TOPIC    = "derbynet/device/{}/status"       # online/offline with will message

# Topics to subscribe to
LED_TOPIC       = "derbynet/lane/{}/led"            # set LED color
PINNY_TOPIC     = "derbynet/lane/{}/pinny"          # set pinny display

# Callbacks
def on_connect(client, userdata, flags, rc, properties=None):
    logging.info(f"Connected with result code {rc}")
    client.subscribe(LED_TOPIC.format(pcb.get_Lane()))
    client.subscribe(PINNY_TOPIC.format(pcb.get_Lane()))

def on_message(client, userdata, msg):
    logging.info(f"Received message on topic {msg.topic} with payload {msg.payload}")
    parse_message(msg)

def on_disconnect(client, userdata, rc):
    logging.info(f"Disconnected with result code {rc}")
    client.publish(STATUS_TOPIC.format(pcb.gethwid()), "offline", retain=True)

# Setup
clientid = f"{pcb.gethwid()}-{random.randint(1000, 9999)}"
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, clientid)
logging.info(f"MQTT Client ID: {clientid}")
client.will_set(STATUS_TOPIC.format(pcb.gethwid()), "offline", retain=True)
client.on_connect = on_connect  
client.on_message = on_message
client.on_disconnect = on_disconnect
client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
client.loop_start()

###########################    HELPERS    ###########################
def toggle_callback():
    togglestate = pcb.getToggleState()
    logging.info("Toggle Changed to: " + str(togglestate))
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
    logging.info(f"Sending Toggle: {json.dumps(payload)}")
    client.publish(TOGGLE_TOPIC.format(pcb.gethwid()), json.dumps(payload), qos=2, retain=True)
    send_telemetry()

def send_telemetry():
    payload = pcb.packageTelemetry()
    logging.debug(f"Sending Telemetry: {json.dumps(payload)}")
    client.publish(TELEMETRY_TOPIC.format(pcb.gethwid()), json.dumps(payload), qos=1, retain=True)
    client.publish(STATUS_TOPIC.format(pcb.gethwid()), "online", retain=True)

def parse_message(msg):
    # Parses out the subscribed topic and sets the appropriate value
    topic = msg.topic.split("/")[-1]
    if topic == "led":
        led = msg.payload.decode("utf-8").lower()
        pcb.setLED(led)
    elif topic == "pinny":
        pinny = msg.payload.decode("utf-8").lower()
        pcb.setPinny(pinny)
    else:
        logging.warning(f"Unknown topic: {topic}")

###########################     MAIN     ###########################
def main():
    pcb.begin_toggle_watch(toggle_callback)
    try:
        while True:
            send_telemetry()
            time.sleep(TELEMETRY_INTERVAL)
            if not client.is_connected():
                logging.error("MQTT Disconnected")
                client.reconnect()
    except KeyboardInterrupt:
        pcb.close()
        logging.info("Exiting")
        exit(0)
    except Exception as e:
        logging.error(f"Error: {e}")
        pcb.close()
        exit(1)
    finally:
        pcb.close()
        exit(0)

if __name__ == "__main__":
    main()
