import time
import json
import os
import uuid
import paho.mqtt.client as mqtt # type: ignore
import RPi.GPIO as GPIO # type: ignore
import tm1637 # type: ignore
import random 

# Pin Definitions
PIN_CLK         = 18
PIN_DIO         = 23
PIN_RED         = 8
PIN_GREEN       = 7
PIN_BLUE        = 1
PIN_DIP1        = 6
PIN_DIP2        = 13
PIN_DIP3        = 19
PIN_DIP4        = 26


# Read HWID
if os.path.exists("/boot/firmware/derbyid.txt"):
    with open("/boot/firmware/derbyid.txt", "r") as f:
        HWID = f.read().strip()
else:
    HWID = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)])

print(f"HWID: {HWID}")
# Initialize 7-segment Display
tm = tm1637.TM1637(clk=PIN_CLK, dio=PIN_DIO)
tm.brightness(7)


# MQTT Setup
MQTT_BROKER = "192.168.100.10"
DISPLAYTOPIC = "derbynet/lane/{}/pinny"
LEDTOPIC = "derbynet/lane/{}/led"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, f"{HWID}-{random.randint(1000, 9999)}")

# GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_RED, GPIO.OUT)
GPIO.setup(PIN_GREEN, GPIO.OUT)
GPIO.setup(PIN_BLUE, GPIO.OUT)
GPIO.output(PIN_RED, GPIO.LOW)
GPIO.output(PIN_GREEN, GPIO.LOW)
GPIO.output(PIN_BLUE, GPIO.LOW)

GPIO.setup(PIN_DIP1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_DIP2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_DIP3, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_DIP4, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def get_dip_lane():
    d1 = str(int(not GPIO.input(PIN_DIP1)))
    d2 = str(int(not GPIO.input(PIN_DIP2)))
    d3 = str(int(not GPIO.input(PIN_DIP3)))
    d4 = str(int(not GPIO.input(PIN_DIP4)))
    dips = "".join([d1, d2, d3, d4])
    if dips == "1000":
        return "1"
    elif dips == "1001":
        return "2"
    elif dips == "1010":
        return "3"
    elif dips == "1011":
        return "4"
    else:
        return "0"

def led_set(red=False, green=False, blue=False, white=False):
    GPIO.output(PIN_RED, GPIO.HIGH if red or white else GPIO.LOW)
    GPIO.output(PIN_GREEN, GPIO.HIGH if green or white else GPIO.LOW)
    GPIO.output(PIN_BLUE, GPIO.HIGH if blue or white else GPIO.LOW)

# MQTT Callback Functions
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Connected to MQTT broker!")
        print(f"Subscribing to {DISPLAYTOPIC.format(get_dip_lane())}")
        client.subscribe(DISPLAYTOPIC.format(get_dip_lane()), qos=1)  # Subscribes with QoS 1
        print(f"Subscribing to {LEDTOPIC.format(get_dip_lane())}")
        client.subscribe(LEDTOPIC.format(get_dip_lane()), qos=1)
    else:
        print(f"Failed to connect, reason code {reason_code}")

def on_message(client, userdata, message):
    try:
        payload = message.payload.decode("utf-8")
        topic = message.topic
        print(f"Topic {topic} Received message: {payload}")
        if "led" in topic:
            led_set(red=payload == 'red', green=payload == 'green', blue=payload == 'blue', white=payload == 'white')
        if "pinny" in topic:
            pinny = str(payload).zfill(4)
            print(f"Displaying {pinny}")
            tm.show(pinny)
    except Exception as e:
        print(f"Error processing message: {e}")
        tm.show("err0")

# Assign Callbacks
client.on_connect = on_connect
client.on_message = on_message

try:
    print(f"Connecting to MQTT broker at {MQTT_BROKER}...")
    client.connect(MQTT_BROKER, 1883, keepalive=60)
    client.loop_start()  # Starts a non-blocking MQTT loop
    tm.show("rrrr")
    while True:
        time.sleep(1)
        if not client.is_connected():
            print("Reconnecting...")
            try:
                client.reconnect()
            except Exception as e:
                print(f"Reconnect failed: {e}")

except KeyboardInterrupt:
    print("\nExiting gracefully...")

finally:
    GPIO.cleanup()
    client.disconnect()
    client.loop_stop()
