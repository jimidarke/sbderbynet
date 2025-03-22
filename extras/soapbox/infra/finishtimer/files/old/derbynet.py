'''
    Main program on the finish timers to receive data from DerbyNet and act accordingly by displaying the pinny and changing the LED colour
'''

import json
import time
import os
import uuid
import paho.mqtt.client as mqtt # type: ignore
import RPi.GPIO as GPIO # type: ignore
import tm1637 # type: ignore
import random 
import logging

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
PIN_TOGGLE      = 24

led = "blue" # Default LED colour

# logging setup 
logging.basicConfig( level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='/var/log/derbynet.log')

logging.info("Starting DerbyNet Display")

# Read HWID
if os.path.exists("/boot/firmware/derbyid.txt"):
    with open("/boot/firmware/derbyid.txt", "r") as f:
        HWID = f.read().strip()
else:
    HWID = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)])

logging.info(f"HWID: {HWID}")

# Initialize 7-segment Display
tm = tm1637.TM1637(clk=PIN_CLK, dio=PIN_DIO)
tm.brightness(7)

# MQTT Setup
MQTT_BROKER = "192.168.100.10"
DISPLAYTOPIC = "derbynet/lane/{}/pinny"
LEDTOPIC = "derbynet/lane/{}/led"
clientid = f"{HWID}-{random.randint(1000, 9999)}"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, clientid)
logging.info(f"MQTT Client ID: {clientid}")

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
GPIO.setup(PIN_TOGGLE, GPIO.IN, pull_up_down=GPIO.PUD_UP)

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
    logging.info(f"LED: Red={red}, Green={green}, Blue={blue}, White={white}")

def display_set(pinny):
    global led
    toggle = GPIO.input(PIN_TOGGLE)
    if led == "blue" and toggle: # in STAGING and toggle is "off"
        tm.show("flip")
        logging.warning(f"flip")
    else:
        tm.show(pinny)

# MQTT Callback Functions
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        logging.info(f"Connected to MQTT broker")
        client.subscribe(DISPLAYTOPIC.format(get_dip_lane()))  
        logging.info(f"Subscribing to {DISPLAYTOPIC.format(get_dip_lane())}")
        client.subscribe(LEDTOPIC.format(get_dip_lane()))
        logging.info(f"Subscribing to {LEDTOPIC.format(get_dip_lane())}")
    else:
        logging.error(f"Failed to connect to MQTT broker: {reason_code}")

def on_message(client, userdata, message):
    global led
    try:
        payload = message.payload.decode("utf-8")
        topic = message.topic
        logging.info(f"Received message on {topic}: {payload}")
        if "led" in topic:
            led = str(payload)
            led_set(red=payload == 'red', green=payload == 'green', blue=payload == 'blue', white=payload == 'white')
        if "pinny" in topic:
            pinny = str(payload).zfill(4)
            logging.info(f"Displaying pinny: {pinny}")
            display_set(pinny)
    except Exception as e:
        print(f"Error processing message: {e}")
        tm.show("err4") ##ERR4 = MQTT Message Receive Error

# Assign Callbacks
client.on_connect = on_connect
client.on_message = on_message

def main():
    try:
        logging.info(f"Connecting to MQTT broker at {MQTT_BROKER}")
        lane = get_dip_lane()
        if lane == "0":
            tm.show("err1") ##ERR1 = Invalid Lane Number
            logging.error("Invalid Lane Number")
        else:
            tm.show("L  " + lane) # Display Lane Number on 7-segment display as a boot/default display 
        time.sleep(5)
        client.connect(MQTT_BROKER, 1883, keepalive=120)
        client.loop_start()  # Starts a non-blocking MQTT loop
        while True:
            time.sleep(1)
            if not client.is_connected():
                try:
                    client.reconnect()
                except Exception as e:
                    logging.error(f"Failed to reconnect to MQTT Broker: {e}")
                    tm.show("err3") ##ERR3 = MQTT Reconnect Error
                    exit(1)

    except KeyboardInterrupt:
        logging.info("Keyboard Interrupt")
        
    finally:
        client.disconnect()
        client.loop_stop()
        #tm.cleanup()
        logging.info("Exiting DerbyNet Display")
        
if __name__ == "__main__":
    tm.show("----")
    try:
        main()
    except Exception as e:
        logging.error(f"Error in Main Loop: {e}")
        exit(1)
    logging.info(f"Exiting DerbyNet Display for {HWID}")