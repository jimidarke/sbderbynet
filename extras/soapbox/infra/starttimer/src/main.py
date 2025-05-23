# main.py -- put your code here!
import gc
import network
import machine
import time
from umqtt.simple import MQTTClient
import ubinascii
import uos
import dht
import ntptime
import random
import urequests


VERSION = '0.2.0'  # Version of the firmware.  
# V0.0.1 - March 31 2025    - Initial version with basic functionality including sending state and telemetry to mqtt
# V0.1.0 - April 4 2025     - Added OTA updates
# V0.2.0 - April 5 2025     - Added watchdog timer for stability
HWID = "STARTTIMER"

# Wi-Fi Configuration
SSID = 'DerbyNet'
PASSWORD = 'all4theKids'

# MQTT Configuration
MQTT_BROKER = '192.168.100.10'  # Replace with your MQTT broker IP
MQTT_TOPIC = 'derbynet/device/starttimer' #/status /telemetry /state
CLIENT_ID = HWID + str(random.randint(1000, 9999))  # Unique client ID

# NTP Configuration
NTP_SERVER = '192.168.100.10'  # Replace with your local NTP server IP
UNIX_EPOCH_OFFSET = 946684800  # Seconds between 1970-01-01 and 2000-01-01

# GPIO Configuration
START_PIN = 33 # GPIO pin for start signal
LED_PIN = 2  # Onboard LED
DHT_PIN = 32  # DHT22 sensor data pin

# Watchdog Timer Configuration (1 minute)
WATCHDOG_TIMEOUT = 60000  # 1 minute in milliseconds

# Setup GPIO
# start_pin should have a pull-down resistor to ensure it reads LOW. When a HIGH signal is detected, it indicates the start signal.
#start_signal = machine.Pin(START_PIN, machine.Pin.IN)
start_signal = machine.Pin(START_PIN, machine.Pin.IN, machine.Pin.PULL_DOWN)  # Pull-down resistor
led = machine.Pin(LED_PIN, machine.Pin.OUT)
dht_sensor = dht.DHT22(machine.Pin(DHT_PIN))

# Global variables for tracking state
previous_state = start_signal.value()  # Initialize with LOW state
client = None
boot_time = time.ticks_ms()

# Initialize the hardware watchdog timer
wdt = machine.WDT(timeout=WATCHDOG_TIMEOUT)

# OTA Configuration
OTA_URL = 'http://192.168.100.10/starttimer/main.py'  # Replace with your local HTTP server IP

# OTA Update Function
def ota_update():
    try:
        print('Starting OTA update...')
        print(f'Downloading firmware from {OTA_URL}...')
        response = urequests.get(OTA_URL)
        print(f'Downloaded {len(response.content)} bytes from {OTA_URL}')
        # Check if the response is valid
        if response.status_code == 200:
            print('Firmware download complete. Writing to flash...')
            with open('/main.py', 'wb') as f:
                f.write(response.content)
            print('Firmware saved.')
            response.close()
            # Flash the new firmware
            machine.reset()
        else:
            print(f'Failed to download firmware: {response.status_code}')
    except Exception as e:
        print(f'OTA update failed: {e}')

# MQTT Callback for OTA
def mqtt_callback(topic, msg):
    print(f'Received message: {msg} on topic: {topic}')
    if topic == bytes(MQTT_TOPIC + '/update', 'utf-8') and msg == b'update':
        ota_update()

# Sync time using NTP
def sync_time():
    attempt = 0
    while True:
        try:
            ntptime.host = NTP_SERVER
            ntptime.settime()
            print('Time synchronized with NTP server')
            break
        except Exception as e:
            print('NTP sync failed, retrying...', str(e))
            time.sleep(exponential_backoff(attempt))
            attempt += 1

# Get current Unix timestamp
def get_timestamp():
    try:
        current_time = time.time() + UNIX_EPOCH_OFFSET  # Adjust for local time zone
        return int(current_time)
    except Exception as e:
        print('Error getting timestamp:', e)
        return 0

# Exponential backoff for reconnections
def exponential_backoff(attempt):
    if attempt > 10:
        print('Max attempts reached, resetting...')
        machine.reset()
    return min(60, (2 ** attempt))

# Connect to Wi-Fi
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to Wi-Fi...')
        wlan.connect(SSID, PASSWORD)
        attempt = 0
        while not wlan.isconnected():
            print('Waiting for Wi-Fi connection...')
            time.sleep(exponential_backoff(attempt))
            attempt += 1
    print('Connected to Wi-Fi:', wlan.ifconfig())
    wdt.feed()

# Connect to MQTT Broker
def connect_mqtt():
    global client
    attempt = 0
    while True:
        try:
            print('Connecting to MQTT Broker...')
            client = MQTTClient(CLIENT_ID, MQTT_BROKER, keepalive=60)
            #set callbacks or will messages
            client.set_callback(mqtt_callback)
            client.set_last_will(MQTT_TOPIC + "/status", 'offline', retain=True) 
            client.connect()
            client.subscribe(MQTT_TOPIC + '/update')
            client.publish(MQTT_TOPIC + "/status", 'online', retain=True)
            print('MQTT connected')
            wdt.feed()
            return
        except Exception as e:
            print('Failed to connect to MQTT:', e)
            time.sleep(exponential_backoff(attempt))
            attempt += 1

# Ensure MQTT connection is active
def ensure_mqtt():
    global client
    try:
        if client is None:
            connect_mqtt()
        client.ping()
        client.publish(MQTT_TOPIC + "/status", 'online', retain=True)
    except Exception as e:
        print('MQTT connection lost:', e)
        connect_mqtt()

# Blink LED to indicate message sent
def blink_led():
    led.on()
    time.sleep(0.1)
    led.off()

# Calculate uptime in seconds
def uptime_seconds():
    return time.ticks_ms() // 1000

# Collect DHT22 data
def read_dht22():
    try:
        dht_sensor.measure()
        temperature = dht_sensor.temperature()
        humidity = dht_sensor.humidity()
        #print(f'DHT22 - Temperature: {temperature}°C, Humidity: {humidity}%')
        return temperature, humidity
    except Exception as e:
        print('DHT22 read error:', e)
        return 0, 0

# Collect device telemetry data
def collect_telemetry():
    wlan = network.WLAN(network.STA_IF)
    ip = wlan.ifconfig()[0]
    mac = ubinascii.hexlify(wlan.config('mac')).decode()
    rssi = wlan.status('rssi')
    uptime = uptime_seconds()
    free_mem = gc.mem_free()

    # Flash size and usage
    stats = uos.statvfs('/')
    flash_size = stats[0] * stats[2]
    flash_free = stats[0] * stats[3]

    # DHT22 sensor data
    temperature, humidity = read_dht22()

    telemetry = {
        'ip_address': ip,
        'mac_address': mac,
        'rssi': rssi,
        'uptime': uptime,
        'free_memory': free_mem,
        'flash_size': flash_size,
        'flash_free': flash_free,
        'temperature': temperature,
        'humidity': humidity,
        'timestamp': get_timestamp(),
        'version': VERSION,
        'hwid': HWID,
        'state': start_signal.value()
    }
    #print('Telemetry data:', telemetry)
    return telemetry

# Send telemetry data to MQTT
def send_telemetry():
    telemetry = collect_telemetry()
    try:
        ensure_mqtt()
        telemetry_msg = str(telemetry).replace("'", '"')  # Convert to JSON-like format
        client.publish(MQTT_TOPIC + "/telemetry", telemetry_msg)
        print(telemetry_msg)
        #print(f'Sent telemetry: {telemetry_msg}')
        wdt.feed()
    except Exception as e:
        print('Error sending telemetry:', e)

# Send MQTT message for start signal
def send_mqtt_message(state):
    try:
        ensure_mqtt()
        message = 'GO' if state else 'STOP'
        msg = {"state": message, "timestamp": get_timestamp()}
        msg = str(msg).replace("'", '"')  # Convert to JSON-like format
        client.publish(MQTT_TOPIC + "/state", msg, retain=True)
        print(msg)
        time.sleep(0.1)
        blink_led()
        wdt.feed()
    except Exception as e:
        print('Error sending MQTT message:', e)

# Monitor for changes in start signal
def monitor_signal():
    global previous_state
    telemetry_interval = 60  # Send telemetry every x seconds
    last_telemetry = 0
    while True:

        # Check Wi-Fi connectivity periodically
        if not network.WLAN(network.STA_IF).isconnected():
            print('Wi-Fi disconnected, reconnecting...')
            connect_wifi()
        
        #ensure_mqtt()
        client.check_msg()  # Check for incoming MQTT messages

        # Check for signal change
        current_state = start_signal.value()
        if current_state != previous_state:
            #print(f'State changed to: {"HIGH" if current_state else "LOW"}')
            send_mqtt_message(current_state)
            previous_state = current_state
            send_telemetry()

        # Send telemetry periodically
        if get_timestamp() - last_telemetry >= telemetry_interval:
            send_telemetry()
            last_telemetry = get_timestamp()
        # Feed watchdog periodically even if no state change
        wdt.feed()
        time.sleep(0.1)

# Main program
print('Starting program...')
try:
    connect_wifi()
    sync_time()    
    connect_mqtt()
    monitor_signal()
except Exception as e:
    print('Unhandled error:', e)
    if client:
        client.disconnect()
    led.off()
    machine.reset()
finally:
    if client:
        client.disconnect()
    led.off()
    print('Program terminated.')
