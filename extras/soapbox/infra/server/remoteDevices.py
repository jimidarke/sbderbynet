'''
Manages the remote DerbyNet devices and communicates over MQTT. 
The primary function is to assign lane numbers to the remote devices when they connect to the server, and then feed data to that device accordingly.

Sample Payload that the devices will publish to MQTT every minute:
derbynet/device/abc123/telemetry
{
    "mac": "aa:bb:cc:dd:ee:ff",
    "ip": "192.168.100.250",
    "hostname": "derbytimer",
    "hwid": "abc123",
    "cpu_temp": "45.1",
    "wifi_rssi": "-45",
    "uptime": "123456",
    "memory_usage": "50",
    "cpu_usage": "25",
    "battery_level": "90",
    "dip_switch": "1010",
    "toggle": true
}

the finish timer device will listen to the following MQTT topic:
derbynet/device/abc123/display
{
    "lane": "1",
    "pinny": "1234",
    "led": "blue"
}

The lane number is just for record keeping/audit, the finish timer's only outward communication to the user is through the LED colour to indicate general race status and readiness, and the 4 digit 7-segment display that shows the pinny number (racerid) that is being tracked. 
The finish timer's only inward communication is through the dip switches that are used to set the lane number and the toggle switch which is used to indicate the finish timing of the assigned lane/pinny/racer. Once that cart crosses the finish line and the toggle is switched, the device will publish the time to the MQTT topic derbynet/device/abc123/state with the following payload:
{
    "toggle": true,
    "time": "1723993023"
}

This script will listen for those state changes and update the DerbyNet API accordingly. Once all finish timers report in from a race, the final values and results will be sent to the DerbyNet API, which will then update the leaderboard and progress to the next race. 

This script will gather information on the state of each of the timers based on the MQTT data, and update a locally plugged in 2 inch LCD screen with each devices' status and the current time. 

To summarize, this script will perform the following functions:
- Listen to MQTT for telemetry and state data from the finish timers
- Assign lane numbers to the finish timers by publishing to the MQTT topic derbynet/device/abc123/display and derbynet/lanes/1
- Send the assigned pinny number to each finish timer by publishing to the MQTT topic derbynet/device/abc123/display
- Captue the finish time of each racer by listening to the MQTT topic derbynet/device/abc123/state
- Compute the finish positions and times of each racer and send the results to the DerbyNet API

'''

# Import the necessary libraries
import paho.mqtt.client as mqtt # type: ignore
from datetime import datetime
import time 
import json
import random
import logging
from derbyapi import DerbyNetClient


# setup logging to file and console
logging.basicConfig(filename='remoteDevices.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Setup the DerbyNet API 
SERVERIP = "localhost"
api = DerbyNetClient(SERVERIP)

# Define the MQTT broker address and port
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_DISPLAY = "derbynet/device/{}/display"       # Send to HW ID for each finish timer
MQTT_TOPIC_TELEMETRY = "derbynet/device/+/telemetry"    # Receive from HW ID for each finish timer
MQTT_TOPIC_STATE = "derbynet/device/+/state"            # Receive from finish timer state of finish toggle switch 
MQTT_TOPIC_LANE = "derbynet/lane/{}/"                   # Send to lane number for each finish timer 1..4

# Define the MQTT client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, f"Derby-{random.randint(1000, 9999)}")

# Set up the MQTT Callback functions
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        logging.info("Connected to MQTT broker")
        client.subscribe(MQTT_TOPIC_TELEMETRY, qos=1)  # Subscribes with QoS 1
        client.subscribe(MQTT_TOPIC_STATE, qos=1)
    else:
        logging.error(f"Failed to connect to MQTT broker: {reason_code}")

def on_message(client, userdata, message):
    try:
        payload = message.payload.decode("utf-8")
        topic = message.topic
        msg = json.loads(payload)
        #print(json.dumps(msg, indent=4))
        logging.info(f"Received message on topic {topic}")
        logging.debug(f"Message: {json.dumps(msg)}")
        process_message(topic, msg)
    except Exception as e:
        print(f"Error processing message: {e}")

# Assign the callback functions
client.on_connect = on_connect
client.on_message = on_message

def getLane(dip):
    lane = 0
    if dip == "1000": #lane 1
        lane = 1
    elif dip == "1001": #lane 2
        lane = 2
    elif dip == "1010": #lane 3
        lane = 3
    elif dip == "1011": #lane 4
        lane = 4
    else:
        logging.error(f"Invalid dip switch value: {dip}")
    return lane

def process_message(topic,  msg):
    if "telemetry" in topic: 
        # msg = {"mac": "18:c6:31:4c:13:84", "ip": "192.168.100.181", "hostname": "DT54SIV0001", "cpu_temp": 34.2, "wifi_rssi": -27, "uptime": 4953, "memory_usage": 21.7, "cpu_usage": 0.7, "battery_level": 70, "dip_switch": "0000", "toggle": false, "time": 1629780000}
        # topic = derbynet/device/DT54SIV0001/telemetry
        hwid = topic.split("/")[-2]
        dip = msg.get("dip_switch", "0000")
        lane = getLane(dip)
        publishtopic = MQTT_TOPIC_LANE.format(lane) + "telemetry"
        payload = {
            "lane": lane,
            "hwid": hwid,
            "lastupdate": msg.get("time", int(time.time())),
            "rssi": msg.get("wifi_rssi", -100),
            "uptime": msg.get("uptime", 0),
            "battery_level": msg.get("battery_level", 0)
        }
        client.publish(publishtopic, json.dumps(payload), qos=1)
    elif "state" in topic:
        #{"toggle": false,"time": 1742259569,"hwid": "DT54SIV0002","dip": "1001"}
        hwid = topic.split("/")[-2]
        dip = msg.get("dip", "0000")
        lane = getLane(dip)
        publishtopic = MQTT_TOPIC_LANE.format(lane) + "state"
        payload = {
            "time": msg.get("time", int(time.time())),
            "toggle": msg.get("toggle", None)
        }
        client.publish(publishtopic, json.dumps(payload), qos=1)


# Connect to the MQTT broker
def connect_mqtt():
    try:
        print(f"Connecting to MQTT broker at {MQTT_BROKER}...")
        client.connect(MQTT_BROKER, 1883, keepalive=60)
        client.loop_start()  # Starts a non-blocking MQTT loop
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}")

def update_lcd(msg):
    pass

def assign_lane(msg):
    pass

def update_api(msg):
    pass

# Main function
def main():
    connect_mqtt()
    while True:
        time.sleep(1)
        if not client.is_connected():
            print("Reconnecting...")
            try:
                client.reconnect()
            except Exception as e:
                print(f"Reconnect failed: {e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting...")
        client.disconnect()
        client.loop_stop()
        exit(0)
    except Exception as e:
        print(f"An error occurred: {e}")
        client.disconnect()
        client.loop_stop()  
        exit(1)