''' 
This will monitor and send the device telemetry for reporting and monitoring to the MQTT broker

It publishes the following topics:

derbynet/device/{HWID}/config
    - a json object with the configuration of the device that runs at boot and not subject to change during runtime
        - hostname
        - ip address
        - mac address
        - device role
        - software version 
        - hardware version
        - dip switch settings

derbynet/device/{HWID}/state
    - a json object with the current state of the device that can change during runtime such as race updates and user interactions
        - led colour
        - displayed text
        - uptime
        - toggle state
        - battery level
        - wifi rssi
        - cpu temperature
        - cpu usage
        - memory usage
        - disk usage
        - race ready state 

   
pip3 install paho-mqtt psutil netifaces gpiozero   

local file      /home/derby/sendtelemetry.py
service file    /etc/systemd/system/devicetelemetry.service
[Unit]
Description=Sends device telemetry
After=network.target 

[Service]
ExecStart=/usr/bin/python3 /home/derby/starttimer/mqtt/sendtelemetry.py     #/home/derby/finishtimer/sendtelemetry.py
Restart=always
User=root
WorkingDirectory=/home/derby/starttimer/mqtt/                               #/home/derby/finishtimer/

[Install]
WantedBy=multi-user.target


'''

MQTT_BROKER = "192.168.100.10"
DEVICE_ROLE = "finish-timer"  # Change this as per device role
SWVER = "0.1.0"
HWVER = "0.1"


import psutil # type: ignore
import json
import time
import uuid
import subprocess
import os
#import RPi.GPIO as GPIO # type: ignore
 
#GPIO.setmode(GPIO.BCM)

# ADC MCP3421 Setup
from smbus2 import SMBus # type: ignore
I2C_ADDR = 0x68  # MCP3421 I2C address
CONFIG_BYTE = 0b10010000  # 16-bit mode, one-shot, gain 1 (adjust as needed)

# MQTT Client Setup
import paho.mqtt.client as mqtt # type: ignore
MQTT_PORT = 1883
MQTT_TOPIC_CONFIG = "derbynet/device/{}/config"
MQTT_TOPIC_STATE = "derbynet/device/{}/state"
PUBLISH_INTERVAL = 5  # Publish state every 10 seconds
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "derbydevice")
time_start = time.time()

# Device Information
def get_mac():
    macstr = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)])
    return macstr #.replace(":", "")

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

def get_battery_level():
    try:
        with SMBus(1) as bus:
            bus.write_byte(I2C_ADDR, CONFIG_BYTE)  # Start a conversion
            time.sleep(0.1)  # Wait for conversion (adjust if using 18-bit mode)
            data = bus.read_i2c_block_data(I2C_ADDR, 0, 3)  # Read 3 bytes (for 16-bit mode)
            raw_value = (data[0] << 8) | data[1]  # Combine bytes
            if raw_value & 0x8000:  # Handle negative values (two's complement)
                raw_value -= 1 << 16
            resp = (raw_value * 2.048) / (1 << 15) * 100000 # Convert to some unit
            return int(resp)
    except:
        return None
    

def get_wifi_rssi():
    try:
        rssi = subprocess.check_output("iwconfig wlan0 | grep -i --color=never 'Signal level'", shell=True).decode("utf-8")
        return int(rssi.split("=")[-1].split(" dBm")[0])
    except:
        return None

def get_dip_switch():
    return 1001 # Placeholder, modify as needed
    try:
        dip_value = os.popen("gpio -g read 4").read().strip()  # Adjust GPIO pin as needed
        return int(dip_value)
    except:
        return None


def publish_config():
    """Publish device configuration (runs only at boot)"""
    hwid = get_hostname()
    topic = MQTT_TOPIC_CONFIG.format(hwid)
    config_data = {
        "hostname": get_hostname(),
        "ip_address": get_ip(),
        "mac_address": get_mac(),
        "device_role": DEVICE_ROLE,   
        "software_version": SWVER,
        "hardware_version": HWVER,
        "dip_switch_settings": get_dip_switch(),
    }
    client.publish(topic, json.dumps(config_data), retain=True, qos=1)
    print(f"Published config: {config_data}")

def publish_state():
    """Publish dynamic device state"""
    hwid = get_hostname()
    topic = MQTT_TOPIC_STATE.format(hwid)
    state_data = {
        "led_colour": "blue",  # Placeholder, modify as needed
        "displayed_text": "-00-",
        "uptime":  int(time.time() - time_start),
        "toggle_state": 1,  # Placeholder, adjust based on input state
        "battery_level": get_battery_level(),
        "wifi_rssi": get_wifi_rssi(),
        "cpu_temperature": get_cpu_temp(),
        "cpu_usage": psutil.cpu_percent(),
        "memory_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent,
        "race_ready_state": True  # Change dynamically as needed
    }
    sent = client.publish(topic, json.dumps(state_data))
    if sent.rc != mqtt.MQTT_ERR_SUCCESS:
        raise Exception(f"Error publishing state: {sent.rc}")

    #print(f"Published state: {state_data}")

# Main Execution
def main():
    client.connect(MQTT_BROKER, 1883, 60)
    publish_config()
    while True:
        try:
            publish_state()
            time.sleep(PUBLISH_INTERVAL)
        except Exception as e:
            print(f"Error publishing state: {e}")
            client.connect(MQTT_BROKER, 1883, 60) 

if __name__ == "__main__":
    main()
