''' 
This script will send the current unix time (and localized friendly date time string) to the MQTT broken for all clients to receive.

local file      /var/lib/infra/app/derbyTime.py
service file    /etc/systemd/system/derbyTime.service
'''

import paho.mqtt.client as mqtt # type: ignore
import time
import datetime
import pytz # type: ignore
import json

from serverlogger import ServerLogger
import os
import logging

# Support environment variables for debug logging
console_mode = os.getenv('DERBY_CONSOLE_LOG', 'false').lower() == 'true'
debug_mode = os.getenv('DERBY_DEBUG', 'false').lower() == 'true'

logger = ServerLogger(
    name='derbyTime',
    level=logging.DEBUG if debug_mode else logging.INFO,
    console=console_mode
).get_logger()

# MQTT configuration - support environment variables for Docker deployment
MQTT_BROKER = os.getenv('MQTT_BROKER', '127.0.0.1')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
MQTT_USER = os.getenv('MQTT_USER', '')
MQTT_PASS = os.getenv('MQTT_PASS', '')

# Tenant routing mode: in 'multi' (cloud), the time payload fans out to each
# known tenant's prefix so every sandbox shows the same race clock without
# inventing a tenantless cross-cutting topic. In single-tenant (Pi) mode the
# legacy `derbynet/race/time` is preserved.
DERBYNET_TENANT_MODE = os.getenv('DERBYNET_TENANT_MODE', '').lower()
TENANTS_DIR = os.path.join(
    os.getenv('DERBYNET_DB_PATH', '/var/lib/derbynet'), 'tenants')


def _list_active_tenants():
    """Snapshot the set of tenants on disk. Cheap (one readdir per tick).
    Catches new sandboxes the moment their picker creates the dir."""
    if not os.path.isdir(TENANTS_DIR):
        return []
    out = []
    for entry in os.listdir(TENANTS_DIR):
        if os.path.isfile(os.path.join(TENANTS_DIR, entry, 'derbynet.sqlite3')):
            out.append(entry)
    return out

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "racetime")
# Broker requires auth on the cloud twin (allow_anonymous=false). The Pi
# broker is currently anonymous, so empty creds are also valid there.
if MQTT_USER:
    client.username_pw_set(MQTT_USER, MQTT_PASS)
client.connect(MQTT_BROKER, MQTT_PORT, 5)
# paho-mqtt v2 requires an explicit loop. Without it, connect() never
# completes the CONNACK round-trip and every publish returns NO_CONN.
client.loop_start()
time_start = time.time()

def sendTime():
    timestampnow = time.time() # Unix timestamp
    dt = datetime.datetime.fromtimestamp(timestampnow, pytz.timezone('America/Edmonton'))
    dtstr = dt.strftime('%Y-%m-%d %H:%M:%S %Z')
    #timestr to show clock friendly returns a tuple of hour and minute integers
    hr = int(time.strftime("%H"))
    if hr > 12:
        hr = hr - 12
    elif hr == 0:
        hr = 12
    #print("Racetime: " + dtstr)
    payload = {
        "timestamp": int(timestampnow),
        "datetime": dtstr,
        "clockhr": hr,
        "clockmin": int(time.strftime("%M")),
        "clocksecond": int(time.strftime("%S")),
        "uptime": int(time.time() - time_start)
    }
    payload = json.dumps(payload)
    if DERBYNET_TENANT_MODE == 'multi':
        tenants = _list_active_tenants()
        if not tenants:
            return  # nothing to publish to yet; idle until a sandbox exists
        for slug in tenants:
            topic = f"derbynet/t/{slug}/race/time"
            sent = client.publish(topic, payload, 0, False)
            if sent.rc != mqtt.MQTT_ERR_SUCCESS:
                raise Exception(f"Failed to send racetime to {topic}: {dtstr}")
    else:
        sent = client.publish("derbynet/race/time", payload, 0, False)
        if sent.rc != mqtt.MQTT_ERR_SUCCESS:
            raise Exception("Failed to send racetime: " + dtstr)

if __name__ == "__main__":
    logger.info("Starting Derby Time Service")
    while True:
        try:
            sendTime()
        except Exception as e:
            print ("General exception: " + str(e))
            logger.error("General exception: " + str(e))
            client.disconnect()
            client.connect(MQTT_BROKER, MQTT_PORT, 5)
        time.sleep(0.95)
