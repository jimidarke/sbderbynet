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

from derbylogger import setup_logger
logger = setup_logger("derbyTime")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "racetime")
client.connect("127.0.0.1", 1883, 5)
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
            client.connect("127.0.0.1", 1883, 5)
        time.sleep(0.95)
