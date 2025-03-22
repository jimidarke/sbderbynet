'''
Sends device data to the MQTT broker for consumption by the DerbyNet server, mostly for analytics and monitoring purposes.

Examples of telemetry to send:
- Hardware ID (on PCB)
- Version 
- Battery percentage (using the get_battery_percentage function)
- IP and MAC address
- Device uptime
- CPU and memory usage
- RSSI (signal strength)
- DIP switch settings (4 pin)
- Toggle state (to a specific topic apart from the telemetry topic)
- Assigned Lane ID
- Assigned Pinny ID
- Assigned LED colour

MQTT Topic Structure:
derbynet/device/<hardware_id>/telemetry (for telemetry data)
derbynet/device/<hardware_id>/state     (for toggle state)

Telemetry data is transmitted every minute, while the toggle state is transmitted every time it changes.

DerbyNet PCB V1 Hardware Pinout
--------------------------------------

NAME    GPIOPIN    HWPIN    FUNCTION
--------------------------------------
TOGGLE      24      18        INPUT
SDA         2       3         I2C (ADC)
SCL         3       5         I2C (ADC)
DIP1        6       31        INPUT
DIP2        13      33        INPUT
DIP3        19      35        INPUT
DIP4        26      37        INPUT
CLK         18      12        DISPLAY
DIO         23      16        DISPLAY
REDLED      8       24        OUTPUT
GREENLED    7       26        OUTPUT
BLUELED     1       28        OUTPUT


'''
PIN_TOGGLE      = 24
PIN_SDA         = 2
PIN_SCL         = 3
PIN_DIP1        = 6
PIN_DIP2        = 13
PIN_DIP3        = 19
PIN_DIP4        = 26

import time

import psutil # type: ignore
import json
import threading
import subprocess
import uuid
import paho.mqtt.client as mqtt # type: ignore
import RPi.GPIO as GPIO # type: ignore
import smbus2 # type: ignore
import os
import random
import logging

time_start = 0

#### READ HWID FROM BOOT PARTITION ####
# /boot/derbyid.txt contains the HWID
if os.path.exists("/boot/firmware/derbyid.txt"):
    with open("/boot/firmware/derbyid.txt", "r") as f:
        HWID = f.read().strip() # DT_54siv_0007
else:
    HWID = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)]) # mac address

# MCP3421 I2C Address (default is 0x68, change if needed)
MCP3421_ADDR = 0x68

# Constants
TELEMETRY_INTERVAL = 10 # seconds

TOGGLE_TOPIC = "derbynet/device/{}/state"
TELEMETRY_TOPIC = "derbynet/device/{}/telemetry"
STATUS_TOPIC = "derbynet/device/{}/status" #online/offline with will message

# Setup logging
logging.basicConfig(filename='/var/log/derbytelemetry.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info(f"Starting DerbyNet Telemetry for {HWID}")

clientid = f"{HWID}-{random.randint(1000, 9999)}"
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, clientid)


logging.info(f"MQTT Client ID: {clientid}")

### GPIO SETUP ###
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_TOGGLE, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_DIP1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_DIP2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_DIP3, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_DIP4, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def get_dip_switches():
    d1 = str(int(not GPIO.input(PIN_DIP1)))
    d2 = str(int(not GPIO.input(PIN_DIP2)))
    d3 = str(int(not GPIO.input(PIN_DIP3)))
    d4 = str(int(not GPIO.input(PIN_DIP4)))
    return "".join([d1, d2, d3, d4])

# thread to monitor the toggle switch
def toggle_thread():
    toggle = not GPIO.input(PIN_TOGGLE)
    while True:
        if GPIO.input(PIN_TOGGLE) != toggle: # change of state
            logging.info(f"Toggle: {toggle}")
            d1 = str(int(not GPIO.input(PIN_DIP1)))
            d2 = str(int(not GPIO.input(PIN_DIP2)))
            d3 = str(int(not GPIO.input(PIN_DIP3)))
            d4 = str(int(not GPIO.input(PIN_DIP4)))
            dips = "".join([d1, d2, d3, d4])
            payload = {
                "toggle": toggle,
                "time": int(time.time()),
                "hwid": HWID,
                "dip": dips
            }
            try:
                client.publish(TOGGLE_TOPIC.format(HWID), json.dumps(payload), qos=2, retain=True)
                toggle = not toggle
            except Exception as e:
                logging.error(f"Error publishing toggle state: {e}")
                client.reconnect()
                time.sleep(0.5)
                client.publish(TOGGLE_TOPIC.format(HWID), json.dumps(payload), qos=2, retain=True)
        time.sleep(0.1)

t = threading.Thread(target=toggle_thread, args=(), daemon=True)

# Device Information
def get_mac():
    macstr = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)])
    return macstr#.replace(":", "")

def get_ip():
    cmd = "hostname -I | cut -d' ' -f1"
    return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()

def get_hostname():
    cmd = "hostname"
    return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()

def get_cpu_temp():
    try:
        temp = subprocess.check_output("vcgencmd measure_temp", shell=True).decode("utf-8")
        return float(temp.replace("temp=", "").replace("'C\n", ""))
    except:
        return None

def get_wifi_rssi():
    try:
        rssi = subprocess.check_output("iwconfig wlan0 | grep -i --color=never 'Signal level'", shell=True).decode("utf-8")
        return int(rssi.split("=")[-1].split(" dBm")[0])
    except:
        return None

def get_uptime():
    return int(time.time() - time_start)

def get_memory_usage():
    return psutil.virtual_memory().percent

def get_cpu_usage():
    return psutil.cpu_percent()

def prepPayload(): # returns the json to be sent
    payload = {
        "mac": get_mac(),
        "ip": get_ip(),
        "hostname": get_hostname(),
        "cpu_temp": get_cpu_temp(),
        "wifi_rssi": get_wifi_rssi(),
        "uptime": get_uptime(),
        "memory_usage": get_memory_usage(),
        "cpu_usage": get_cpu_usage(),
        "battery_level": get_battery_percentage(),
        "battery_raw": read_mcp3421(),
        "dip": get_dip_switches(),
        "toggle": not GPIO.input(PIN_TOGGLE),
        "hwid": HWID,
        "time": int(time.time())
    }
    return json.dumps(payload)

### BATTERY VOLTAGE READING ###

'''
This will read the battery voltage from the MCP3421 ADC and return the battery percentage.
If the battery output shows 105% then the device is charging but not fully charged yet. 
If the battery output shows 110% then the device is charging and is fully charged.
If the battery output shows 0% then the device is dead.
Otherwise, the battery output will show the battery percentage between 1 and 100.

'''

# Data function to read raw ADC value from MCP3421
def read_mcp3421():
    bus = smbus2.SMBus(1)  # Use I2C bus 1
    try:
        data = bus.read_i2c_block_data(MCP3421_ADDR, 0, 3)  # Read 3 bytes
        bus.close()

        raw_value = (data[0] << 8) | data[1]  # 16-bit ADC value
        if raw_value & 0x8000:  # Check if negative (ADC is signed)
            raw_value -= 65536
        
        return raw_value # Return the raw ADC value which is unitless

    except Exception as e:
        logging.error(f"Error reading MCP3421: {e}")
        return None

# Helper function to convert raw ADC value to voltage
def adc_to_voltage(raw_value):
    # adc range is 1500-1820 and voltage range is 3.40-4.10 representing the maximum battery charge and the point at which the device dies. 
    # The voltage range is 3.40-4.10 and the battery range is 0-100%.
    if raw_value is None:
        return None
    return 3.40 + (raw_value - 1500) * (4.10 - 3.40) / (1820 - 1500)

# Helper function to convert voltage to battery percentage
def voltage_to_battery(voltage):
    if voltage is None:
        return None
    if voltage >= 4.10:
        return 100
    if voltage <= 3.40:
        return 0
    return int((voltage - 3.40) / (4.10 - 3.40) * 100)

# Main Function to read the battery voltage and return the battery percentage. Called by the main program.
def get_battery_percentage(delay=1):
    # get an average of `delay`x4 readings over `delay` seconds once every quarter second
    raw_value = 0
    for _ in range(delay*4):
        raw_value += read_mcp3421()
        time.sleep(0.25)
    raw_value = raw_value / (delay*4)
    if raw_value > 1880:
        return 105 # represents a device being charged but not fully charged yet
    if raw_value > 1840:
        return 110 # represents a device being charged and is fully charged 
    voltage = adc_to_voltage(raw_value)
    return voltage_to_battery(voltage) 

def on_connect(client, userdata, flags, reason_code, properties = None):
    if reason_code == 0:
        logging.info(f"Connected to MQTT broker")
    else:
        logging.error(f"Failed to connect to MQTT broker: {reason_code}")

def main(): # main function
    while True:
        if client.is_connected() == False:
            client.reconnect()
        payload = prepPayload()
        client.publish(TELEMETRY_TOPIC.format(HWID), payload, qos=1)    
        logging.info(f"Telemetry: {payload}")
        time.sleep(TELEMETRY_INTERVAL)

if __name__ == "__main__":
    client.will_set(STATUS_TOPIC.format(HWID), payload="offline", qos=1, retain=True)
    client.on_connect = on_connect
    client.connect("192.168.100.10", 1883, 120)
    client.loop_start()
    client.publish(STATUS_TOPIC.format(HWID), payload="online", qos=1, retain=True)
    t.start()
    time_start = time.time()
    logging.info(f"Starting Main Loop")
    try:
        main()
    except Exception as e:
        logging.error(f"Error in Main Loop: {e}")
        client.reconnect()
        main()
    finally:
        client.disconnect()
        client.loop_stop()
        t.join()
        exit(0)
        logging.info(f"Exiting DerbyNet Telemetry for {HWID}")
        