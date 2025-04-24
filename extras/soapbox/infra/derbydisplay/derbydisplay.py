
import json
import subprocess
import time
import paho.mqtt.client as mqtt # type: ignore
import random
import sys
import os
import uuid
import psutil # type: ignore

time.sleep(10)

###########################    SETUP    ###########################
from derbylogger import setup_logger
logger = setup_logger(__name__)

logger.info("####### Starting DerbyNet DerbyDisplay #######")

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
UPDATE_TOPIC    = "derbynet/device/{}/update"       # firmware update trigger message="update"

if os.path.exists("/boot/firmware/derbyid.txt"):
    with open("/boot/firmware/derbyid.txt", "r") as f:
        hwid = f.read().strip()
else:
    hwid = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)])
logger.debug(f"HWID: {hwid}")

# Callbacks
def on_connect(client, userdata, flags, rc, properties=None):
    logger.info(f"Connected with result code {rc}")
    client.subscribe(UPDATE_TOPIC.format(hwid))
    client.publish(STATUS_TOPIC.format(hwid), "online", retain=True)

def on_message(client, userdata, msg):
    logger.debug(f"Received message on topic {msg.topic} with payload {msg.payload}")
    parse_message(msg)

def on_disconnect(client, userdata, rc):
    logger.warning(f"Disconnected with result code {rc}")
    client.publish(STATUS_TOPIC.format(hwid), "offline", retain=True)

# Setup
clientid = f"{hwid}"#-{random.randint(1000, 9999)}"
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, clientid)
logger.debug(f"MQTT Client ID: {clientid}")
client.will_set(STATUS_TOPIC.format(hwid), "offline", retain=True)
client.on_connect = on_connect  
client.on_message = on_message
client.on_disconnect = on_disconnect
client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
client.loop_start()

def send_telemetry():
    '''
    Device status telemetry format V 0.2.0
    hostname
    hwid
    uptime
    ip
    mac
    wifi_rssi
    battery_level
    cpu_temp
    memory_usage
    disk
    cpu_usage
    '''
    payload = {
        "hostname": hwid,
        "mac": get_mac(),
        "ip": get_ip(),
        "cpu_temp": get_cpu_temp(),
        "wifi_rssi": get_wifi_rssi(),
        "uptime": get_uptime(),
        "memory_usage": get_memory_usage(),
        "disk": get_disk_usage(),
        "cpu_usage": get_cpu_usage(),
        "battery_level": 100,
        "battery_raw": 0,
        "hwid": hwid,
        "time": int(time.time()),
        "pcbVersion": "0.2.0",
    }
        #return payload

    #payload = pcb.packageTelemetry()
    logger.debug(f"Sending Telemetry: {json.dumps(payload)}")
    client.publish(TELEMETRY_TOPIC.format(hwid), json.dumps(payload), qos=1, retain=True)
    client.publish(STATUS_TOPIC.format(hwid), "online", retain=True)

def parse_message(msg):
    # Parses out the subscribed topic and sets the appropriate value
    #topic = msg.topic.split("/")[-1]
    pass
    '''
    if "update" in msg.topic and "update" in msg.payload.decode("utf-8").lower():
        logger.warning("Update requested")
        try:
            client.publish(STATUS_TOPIC.format(hwid), "updating", retain=True)
            pcb.update_pcb()
        except Exception as e:
            logger.error(f"Update failed: {e}")
    elif "url" in msg.topic:
        url = msg.payload.decode("utf-8")
        logger.info(f"Setting URL: {url}")
        #update_display(url)
    else:
        logger.warning(f"Unknown topic or payload: {msg.topic} {msg.payload}")
    '''


@staticmethod
def get_mac():
    macstr = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)])
    return macstr#.replace(":", "")

@staticmethod
def get_ip():
    cmd = "hostname -I | cut -d' ' -f1"
    return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()

@staticmethod
def get_hostname():
    cmd = "hostname"
    return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()

@staticmethod
def get_cpu_temp():
    try:
        temp = subprocess.check_output("vcgencmd measure_temp", shell=True).decode("utf-8")
        return float(temp.replace("temp=", "").replace("'C\n", ""))
    except:
        return None

@staticmethod
def get_wifi_rssi():
    try:
        rssi = subprocess.check_output("iwconfig wlan0 | grep -i --color=never 'Signal level'", shell=True).decode("utf-8")
        return int(rssi.split("=")[-1].split(" dBm")[0])
    except:
        return None

@staticmethod
def get_memory_usage():
    return psutil.virtual_memory().percent

@staticmethod
def get_cpu_usage():
    return psutil.cpu_percent()

@staticmethod
def get_disk_usage():
    disk = psutil.disk_usage('/')
    return disk.percent

def get_uptime():
    # get system uptime in seconds 
    try:
        with open('/proc/uptime', 'r') as f:
            uptime = f.readline().split()[0]
        return int(float(uptime))   
    # return uptime in seconds
    except Exception as e:
        logger.error(f"Error getting uptime: {e}")
        return 0

###########################     MAIN     ###########################
def main():
    try:
        while True:
            send_telemetry()
            time.sleep(TELEMETRY_INTERVAL)
            if not client.is_connected():
                logger.error("MQTT Disconnected")
                client.reconnect()
    except KeyboardInterrupt:
        logger.info("Exiting")
        exit(0)
    except Exception as e:
        logger.error(f"Error: {e}")
        exit(1)
    finally:
        exit(0)

if __name__ == "__main__":
    main()
