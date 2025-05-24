import time
import spidev as SPI
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'common'))
from lcdscreen import LCD_2inch
from PIL import Image, ImageDraw, ImageFont
from derbyapi import DerbyNetClient
import paho.mqtt.client as mqtt # type: ignore
import json
import random

# Version information
VERSION = "0.5.0"  # Standardized version

'''
Version History:
- 0.5.0 - May 19, 2025 - Standardized version schema across all components
- 0.4.0 - May 10, 2025 - Added service discovery via mDNS
- 0.3.0 - April 22, 2025 - Added remote syslogging and improved error handling
- 0.2.0 - April 15, 2025 - Added MQTT callbacks and telemetry
- 0.1.0 - April 4, 2025 - Added initial LCD display formatting
- 0.0.1 - March 31, 2025 - Initial implementation
'''

from derbylogger import setup_logger, get_logger
logger = setup_logger("DerbyLCD", use_centralized_config=True)
logger.info(f"Starting DerbyNet LCD Display v{VERSION}")

# LCD Setup
RST = 27
DC = 25
BL = 18
bus = 0
device = 0
disp = LCD_2inch.LCD_2inch(spi=SPI.SpiDev(bus, device),spi_freq=10000000,rst=RST,dc=DC,bl=BL)

displayData = {}

# DerbyNet API Setup
SERVERIP = "127.0.0.1"
api = DerbyNetClient(SERVERIP)
authcode = api.login()

# MQTT Setup
# Define the MQTT broker address and port
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_LANESTATE = "derbynet/lane/+/state"                   # Send to lane number for each finish timer 1..4
MQTT_TOPIC_LANETELEM = "derbynet/lane/+/telemetry"                   # Send to lane number for each finish timer 1..4

# Define the MQTT client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, f"DerbyLCD-{random.randint(1000, 9999)}")

# Set up the MQTT Callback functions
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        logger.info("Connected to MQTT broker")
        logger.info("Subscribing to topic: %s", MQTT_TOPIC_LANESTATE)
        client.subscribe(MQTT_TOPIC_LANESTATE, qos=1)  # Subscribes with QoS 1
        logger.info("Subscribing to topic: %s", MQTT_TOPIC_LANETELEM)
        client.subscribe(MQTT_TOPIC_LANETELEM, qos=1)  # Subscribes with QoS 1
    else:
        logger.error(f"Failed to connect to MQTT broker: {reason_code}")

def on_message(client, userdata, message):
    try:
        payload = message.payload.decode("utf-8")
        topic = message.topic
        msg = json.loads(payload)
        #print(json.dumps(msg, indent=4))
        logger.info(f"Received message on topic {topic}")
        logger.debug(f"Message: {json.dumps(msg)}")
        process_message(topic, msg)
    except Exception as e:
        print(f"Error processing message: {e}")

# Assign the callback functions
client.on_connect = on_connect
client.on_message = on_message

def process_message(topic, msg):
    lane = int(topic.split("/")[2])
    pass

def draw_race_table(disp, race_stats, current_time, lane_statuses, pinny_ids, toggle_states, last_run_times):
    image = Image.new("RGB", (disp.height, disp.width), "WHITE")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("lcdscreen/Font00.ttf", 20)
    #font = ImageFont.load_default()

    col_widths = [79, 79, 79, 80]  # Adjusted column widths
    row_height = 40 # this fills the screen height
    x_start = 1
    y_start = 1

    # Row 1: Merged first three columns for race stats, last column for time
    draw.rectangle([x_start, y_start, x_start + sum(col_widths[:3]), y_start + row_height], outline="BLACK", width=1)
    draw.text((x_start + 5, y_start + 5), race_stats, font=font, fill="BLACK")
    
    x = x_start + sum(col_widths[:3])
    draw.rectangle([x, y_start, x + col_widths[3], y_start + row_height], outline="BLACK", width=1)
    draw.text((x + 5, y_start + 5), current_time, font=font, fill="BLACK")

    # Row 2: Static lane labels
    y = y_start + row_height
    for i, lane in enumerate(["Lane 1", "Lane 2", "Lane 3", "Lane 4"]):
        x = x_start + sum(col_widths[:i])
        draw.rectangle([x, y, x + col_widths[i], y + row_height], outline="WHITE", width=1, fill="BLACK")
        draw.text((x + 5, y + 5), lane, font=font, fill="WHITE")
    
    # Row 3: Online/Offline status with background colors
    y += row_height
    for i, status in enumerate(lane_statuses):
        x = x_start + sum(col_widths[:i])
        color = "GREEN" if status == "Online" else "RED"
        draw.rectangle([x, y, x + col_widths[i], y + row_height], fill=color, outline="BLACK", width=1)
        draw.text((x + 5, y + 5), status, font=font, fill="WHITE")
    
    # Row 4: PINNYIDs
    y += row_height
    for i, pinny in enumerate(pinny_ids):
        x = x_start + sum(col_widths[:i])
        draw.rectangle([x, y, x + col_widths[i], y + row_height], outline="BLACK", width=1)
        draw.text((x + 5, y + 5), pinny, font=font, fill="BLACK")
    
    # Row 5: Toggle state with background colors
    y += row_height
    for i, toggle in enumerate(toggle_states):
        x = x_start + sum(col_widths[:i])
        color = "GREEN" if toggle == "On" else "RED"
        draw.rectangle([x, y, x + col_widths[i], y + row_height], fill=color, outline="BLACK", width=1)
        draw.text((x + 5, y + 5), toggle, font=font, fill="WHITE")
    
    # Row 6: Last run time
    y += row_height
    for i, run_time in enumerate(last_run_times):
        x = x_start + sum(col_widths[:i])
        draw.rectangle([x, y, x + col_widths[i], y + row_height], outline="BLACK", width=1)
        draw.text((x + 5, y + 5), run_time, font=font, fill="BLACK")
    
    # Rotate for display
    image = image.rotate(180)
    disp.clear()
    disp.bl_DutyCycle(100)
    disp.ShowImage(image)

def getTime():
    hr = int(time.strftime("%H"))
    if hr > 12:
        hr = hr - 12
    elif hr == 0:
        hr = 12
    timedisplay = " " + str(hr) + ":" + time.strftime("%M")
    return timedisplay

def getRaceStats(racestats):
    #{'active': False, 'roundid': -1, 'heat': None, 'class': '', 'lane-count': 0, 'lanes': [], 'timer-state': 1, 'timer-state-string': 'NOT CONNECTED'}
    #{'active': True, 'roundid': 1, 'heat': 1, 'class': 'Age 6-8', 'lane-count': 0, 'lanes': [{'lane': 1, 'name': 'Faustino Holmes', 'racerid': 1}, {'lane': 2, 'name': 'Jeana Juergens', 'racerid': 3}, {'lane': 3, 'name': 'Edna Essary', 'racerid': 8}], 'timer-state': 1, 'timer-state-string': 'NOT CONNECTED'}
    #print (racestats)
    return racestats['class'] + " Round-" + str(racestats['roundid']) + " Heat-" + str(racestats['heat'])
    #return "Round 1 - Age 10"

def getLaneStatus(racestats):
    #print (racestats['lanes'])
    return ["Online", "Offline", "Online", "Offline"]

def getPinnyDisplay(racestats):
    lanes = racestats['lanes']
    return [str(lane['racerid']) for lane in lanes]

def getToggleStates():
    return ["On", "Off", "On", "Off"]

def getLastRunTimes():
    return ["02:45", "03:12", "01:58", "02:30"]

def main():
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_start()
    disp.Init()
    disp.clear()
    disp.bl_DutyCycle(100)
    while True:
        #racestats = api.get_race_status() 
        #draw_race_table(disp, getRaceStats(racestats), getTime(), getLaneStatus(racestats), getPinnyDisplay(racestats), getToggleStates(), getLastRunTimes())
        time.sleep(3)
    #disp.module_exit()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting...")
        client.disconnect()
        client.loop_stop()
        disp.clear()
        disp.module_exit()
        exit(0)