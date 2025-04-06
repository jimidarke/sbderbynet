
import logging
import json
import subprocess
import time
import paho.mqtt.client as mqtt # type: ignore
import random

from derbynetPCBv1 import derbyPCBv1


###########################    SETUP    ###########################
LOG_FORMAT      = '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] %(message)s'
LOG_FILE        = '/var/log/derbynet.log'

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, filename=LOG_FILE)
logging.info("####### Starting DerbyNet DerbyDisplay #######")

pcb = derbyPCBv1()

###########################    MQTT    ###########################
MQTT_BROKER = "192.168.100.10"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 120
TELEMETRY_INTERVAL = 5 # seconds

# Topics to publish to
TOGGLE_TOPIC    = "derbynet/device/{}/state"        # toggle state and timestamp
TELEMETRY_TOPIC = "derbynet/device/{}/telemetry"    # telemetry data
STATUS_TOPIC    = "derbynet/device/{}/status"       # online/offline with will message

# Topics to subscribe to
URL_TOPIC       = "derbynet/display/{}/url"         # sets the kiosk URL
UPDATE_TOPIC    = "derbynet/device/{}/update"       # firmware update trigger message="update"

# Callbacks
def on_connect(client, userdata, flags, rc, properties=None):
    logging.info(f"Connected with result code {rc}")
    client.subscribe(URL_TOPIC.format(str(pcb.readDIP())))
    client.subscribe(UPDATE_TOPIC.format(pcb.gethwid()))
    client.publish(STATUS_TOPIC.format(pcb.gethwid()), "online", retain=True)

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

def send_telemetry():
    payload = pcb.packageTelemetry()
    logging.info(f"Sending Telemetry: {json.dumps(payload)}")
    client.publish(TELEMETRY_TOPIC.format(pcb.gethwid()), json.dumps(payload), qos=1, retain=True)
    client.publish(STATUS_TOPIC.format(pcb.gethwid()), "online", retain=True)

def parse_message(msg):
    # Parses out the subscribed topic and sets the appropriate value
    #topic = msg.topic.split("/")[-1]
    if "update" in msg.topic and "update" in msg.payload.decode("utf-8").lower():
        logging.warning("Update requested")
        try:
            client.publish(STATUS_TOPIC.format(pcb.gethwid()), "updating", retain=True)
            pcb.update_pcb()
        except Exception as e:
            logging.error(f"Update failed: {e}")
    elif "url" in msg.topic:
        url = msg.payload.decode("utf-8")
        logging.info(f"Setting URL: {url}")
        update_display(url)
    else:
        logging.warning(f"Unknown topic or payload: {msg.topic} {msg.payload}")

# Start Chromium in kiosk mode
def update_display(url):
    logging.info(f"Updated display to {url}")
    subprocess.run(["pkill", "epiphany-browser"])
    subprocess.Popen(["epiphany-browser", "--profile", "--display=:0", "--application-mode", "--fullscreen", url])

    
###########################     MAIN     ###########################
def main():
    defulr = "http://derbynetpi/derbynet/fullscreen.php"
    update_display(defulr)
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
