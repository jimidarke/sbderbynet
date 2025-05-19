# main.py -- put your code here!

# this runs the main program for the DerbyNet Start Timer an esp32 based device that monitors a start signal and sends telemetry data to a MQTT broker
# It uses a DHT22 sensor to collect temperature and humidity data, and a watchdog timer to ensure the device remains responsive.

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
import usocket


VERSION = '0.4.0'  # Version of the firmware.  
# V0.0.1 - March 31 2025    - Initial version with basic functionality including sending state and telemetry to mqtt
# V0.1.0 - April 4 2025     - Added OTA updates
# V0.2.0 - April 15 2025    - Added watchdog timer and updated telemetry data 
# V0.2.2 - April 15 2025    - Fixed telemetry and OTA
# V0.3.0 - April 22 2025    - Added remote syslogging and improved error handling
# V0.4.0 - May 19 2025      - Added service discovery via mDNS for dynamic MQTT broker configuration
HWID = "START"

# Wi-Fi Configuration
SSID = 'DerbyNet'
PASSWORD = 'all4theKids'

# MQTT Configuration
DEFAULT_MQTT_BROKER = '192.168.100.10'  # Default MQTT broker IP if service discovery fails
MQTT_BROKER = DEFAULT_MQTT_BROKER  # Will be updated via mDNS if available
MQTT_PORT = 1883  # Default MQTT port
MQTT_TOPIC = 'derbynet/device/starttimer' #/status /telemetry /state
CLIENT_ID = HWID # + str(random.randint(1000, 9999))  # Unique client ID

# NTP Configuration
NTP_SERVER = DEFAULT_MQTT_BROKER  # Same as MQTT broker by default
UNIX_EPOCH_OFFSET = 946684800  # Seconds between 1970-01-01 and 2000-01-01

# Import mDNS library if available
try:
    import mdns
    MDNS_AVAILABLE = True
    print("mDNS discovery enabled")
except ImportError:
    MDNS_AVAILABLE = False
    print("mDNS library not available, using default broker settings")

# mDNS Service Discovery function
def discover_mqtt_service():
    global MQTT_BROKER, MQTT_PORT
    if not MDNS_AVAILABLE:
        return False
    
    try:
        print("Starting mDNS service discovery...")
        # Initialize mDNS
        server = mdns.Server()
        # Search for MQTT services
        services = server.query("_derbynet._tcp.local.")
        if services:
            # Get the first service
            service = services[0]
            MQTT_BROKER = service.ip()
            MQTT_PORT = service.port()
            print(f"Discovered MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
            # Also update the NTP server to use the same host
            global NTP_SERVER
            NTP_SERVER = MQTT_BROKER
            return True
        else:
            print("No MQTT services found via mDNS, using default settings")
            return False
    except Exception as e:
        print(f"Error during mDNS discovery: {e}")
        return False

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

def sendLog(message, level="INFO"):
    try:
        # Format the log message
        # %(levelname)s - [%(filename)s:%(lineno)d] %(message)s
        log_message = f"STARTER {level} - [main.py] {message}"
        # Send the log message over UDP
        sock = usocket.socket(usocket.AF_INET, usocket.SOCK_DGRAM)
        sock.sendto(log_message.encode('utf-8'), (MQTT_BROKER, 514))
        sock.close()
    except Exception as e:
        print(f"Failed to send log to rsyslog: {e}")

# OTA Update Function
def ota_update():
    try:
        sendLog('Starting OTA update...')
        sendLog(f'Downloading firmware from {OTA_URL}...',"DEBUG")
        response = urequests.get(OTA_URL)
        sendLog(f'Downloaded {len(response.content)} bytes from {OTA_URL}',"DEBUG")
        # Check if the response is valid
        if response.status_code == 200:
            sendLog('Firmware download complete. Writing to flash...',"DEBUG")
            with open('/main.py', 'wb') as f:
                f.write(response.content)
            sendLog('Firmware saved.',"DEBUG")
            response.close()
            # Flash the new firmware
            machine.reset()
        else:
            sendLog(f'Failed to download firmware: {response.status_code}',"ERROR")
    except Exception as e:
        sendLog(f'OTA update failed: {e}',"ERROR")

# MQTT Callback for OTA
def mqtt_callback(topic, msg):
    sendLog(f'Received message: {msg} on topic: {topic}',"DEBUG")
    if topic == bytes(MQTT_TOPIC + '/update', 'utf-8') and msg == b'update':
        ota_update()

# Sync time using NTP
def sync_time():
    attempt = 0
    while True:
        try:
            ntptime.host = NTP_SERVER
            ntptime.settime()
            sendLog('Time synchronized with NTP server', "DEBUG")
            break
        except Exception as e:
            sendLog('NTP sync failed, retrying...' +  str(e), "ERROR")
            time.sleep(exponential_backoff(attempt))
            attempt += 1

# Get current Unix timestamp
def get_timestamp():
    try:
        current_time = time.time() + UNIX_EPOCH_OFFSET  # Adjust for local time zone
        return int(current_time)
    except Exception as e:
        sendLog('Error getting timestamp:' + str(e), "ERROR")
        return 0

# Exponential backoff for reconnections
def exponential_backoff(attempt):
    if attempt > 10:
        sendLog('Max attempts reached, resetting...')
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
    #sendLog('Connected to Wi-Fi', "DEBUG")
    
    # Now that we're connected, try to discover MQTT broker via mDNS
    if discover_mqtt_service():
        sendLog(f"Using discovered MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
    else:
        sendLog("Using default MQTT broker settings", "DEBUG")
    
    wdt.feed()

# Connect to MQTT Broker
def connect_mqtt():
    global client
    attempt = 0
    while True:
        try:
            print(f'Connecting to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT}...')
            client = MQTTClient(CLIENT_ID, MQTT_BROKER, port=MQTT_PORT, keepalive=10)
            #set callbacks or will messages
            client.set_callback(mqtt_callback)
            client.set_last_will(MQTT_TOPIC + "/status", 'offline', retain=True) 
            client.connect()
            client.subscribe(MQTT_TOPIC + '/update')
            client.publish(MQTT_TOPIC + "/status", 'online', retain=True)
            sendLog(f'MQTT connected to {MQTT_BROKER}:{MQTT_PORT}')
            wdt.feed()
            return
        except Exception as e:
            print('Failed to connect to MQTT:', e)
            sendLog('MQTT connection failed, retrying...' + str(e), "ERROR")
            # If we can't connect, try to rediscover the service
            if attempt % 3 == 0:  # Every 3 attempts
                discover_mqtt_service()
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
        sendLog('MQTT connection lost, reconnecting...' + str(e), "ERROR")
        client = None
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
        'hostname': 'Starter',
        'ip': ip,
        'mac': mac,
        'wifi_rssi': rssi,
        'battery_level': 100,  # Placeholder for battery level
        'cpu_usage': 0,  # Placeholder for CPU usage
        'uptime': uptime,
        'memory_usage': 0,
        'flash_size': flash_size,
        'disk': 0,
        'cpu_temp': temperature,
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
        sendLog('Error sending MQTT message:' + str(e), "ERROR")

# Monitor for changes in start signal
def monitor_signal():
    global previous_state
    telemetry_interval = 10  # Send telemetry every x seconds
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
