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

try:
    pcb = derbyPCBv1()
    logging.info("PCB Initialized")
except Exception as e:
    logging.error(f"PCB Initialization failed: {e}")
    time.sleep(1)
    exit(1)

###########################    MQTT    ###########################
MQTT_BROKER         = "192.168.100.10"
MQTT_PORT           = 1883
MQTT_KEEPALIVE      = 10 # seconds
TELEMETRY_INTERVAL  = 2 # seconds

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
logging.info(f"MQTT Client ID: {clientid}")

pinny   = "errr" # default pinny display
led     = "white" # default LED color


###########################    CALLBACKS    ###########################
def on_connect(client, userdata, flags, rc, properties=None):
    logging.info(f"Connected with result code {rc}")
    client.subscribe(LED_TOPIC.format(pcb.get_Lane()))
    client.subscribe(PINNY_TOPIC.format(pcb.get_Lane()))
    client.subscribe(UPDATE_TOPIC.format(pcb.gethwid()))
    client.publish(STATUS_TOPIC.format(pcb.gethwid()), "online", retain=True)

def on_message(client, userdata, msg):
    logging.info(f"Received message on topic {msg.topic} with payload {msg.payload}")
    parse_message(msg)

def on_disconnect(*args):
    logging.warning(f"Disconnected from MQTT")
    client.publish(STATUS_TOPIC.format(pcb.gethwid()), "offline", retain=True)

def initMQTT():
    client.will_set(STATUS_TOPIC.format(pcb.gethwid()), "offline", retain=True)
    client.on_connect = on_connect  
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
        logging.info(f"Connecting to MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
        client.loop_start()
    except OSError as e:#OSError: [Errno 101] Network is unreachable 
        logging.error(f"OS Failure. Network Unreachable?: {e}")
        # set led and pinny to error state
        pcb.setLED("yellow")
        pcb.setPinny("Err4")
        time.sleep(5)
        exit(1)
    except Exception as e:
        logging.error(f"General MQTT Connection failed: {e}")
        # set led and pinny to error state
        pcb.setLED("yellow")
        pcb.setPinny("Err5")
        time.sleep(5)
        exit(1)
    logging.info("MQTT Client Initialized")

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
    global led, pinny
    topic = msg.topic.split("/")[-1]
    if topic == "led":
        led = msg.payload.decode("utf-8").lower()
        pcb.setLED(led)
    elif topic == "pinny":
        pinny = msg.payload.decode("utf-8").lower()
        pcb.setPinny(pinny)
    elif topic == "update": # 
        logging.info("Update requested")
        try:
            client.publish(STATUS_TOPIC.format(pcb.gethwid()), "updating", retain=True)
            pcb.update_pcb()
        except Exception as e:
            logging.error(f"Update failed: {e}")
    else:
        logging.warning(f"Unknown topic: {topic}")

def post_sequence(): # runs through a sequence of LED colors and pinny displays 
    logging.info("Running post sequence")
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
    logging.info("Starting Finish Timer Main Loop")
    logging.info("Running post sequence")
    post_sequence()
    logging.info("Setting up PCB Callbacks")
    lane = pcb.get_Lane()
    logging.info(f"Lane: {lane}")
    pcb.setPinny("LAN" + str(int(lane)))
    initMQTT()
    pcb.begin_toggle_watch(toggle_callback) #must init mqtt first
    try:
        while True:
            send_telemetry()
            time.sleep(TELEMETRY_INTERVAL)
            pcb.setLED(led)
            pcb.setPinny(pinny)
            if not client.is_connected():
                logging.error("MQTT Disconnected")
                client.reconnect()
    except KeyboardInterrupt:
        pcb.close()
        logging.info("Exiting Cleanly")
        client.loop_stop()
        client.disconnect()
        # set led and pinny to error state
        pcb.setLED("yellow")
        pcb.setPinny("----")
        exit(0)
    except Exception as e:
        logging.error(f"Error: {e}")
        client.loop_stop()
        client.disconnect()
        # set led and pinny to error state
        pcb.setLED("yellow")
        pcb.setPinny("Err1")
        pcb.close()
        time.sleep(5)
        exit(1)
    finally:
        pcb.close()
        client.loop_stop()
        client.disconnect()
        # set led and pinny to error state
        pcb.setLED("yellow")
        pcb.setPinny("----")
        logging.info("Exiting Cleanly")
        exit(0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Exiting Cleanly")
        pcb.close()
        client.loop_stop()
        client.disconnect()
        # set led and pinny to error state
        pcb.setLED("yellow")
        pcb.setPinny("----")
        exit(0)
    except Exception as e:
        logging.error(f"Error: {e}")
        pcb.close()
        client.loop_stop()
        client.disconnect()
        # set led and pinny to error state
        pcb.setLED("yellow")
        pcb.setPinny("Err0")
        time.sleep(5)
        exit(1)
