'''
Main program to handle the Derby race.

File location: /var/lib/infra/app/derbyRace.py
Service file: /etc/systemd/system/derbyrace.service

'''


from datetime import datetime, timedelta
import os
import subprocess
import time
import uuid
import paho.mqtt.client as mqtt # type: ignore
import random
import json
import threading
import queue
import sys
from derbyapi import DerbyNetClient
from derbylogger import setup_logger
import psutil # type: ignore 

# Add common library path to allow importing derbynet module
sys.path.append('/var/lib/infra/common')

logger = setup_logger("derbyRace")

try:
    from derbynet import discover_services
    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False
    logger.warning("Zeroconf module not available, service discovery disabled")

# MQTT setup - Default values that will be used if service discovery fails
MQTT_BROKER             = "localhost"
MQTT_PORT               = 1883

# Attempt to discover MQTT broker via mDNS
if ZEROCONF_AVAILABLE:
    try:
        logger.info("Attempting to discover MQTT broker via mDNS...")
        discovered_services = discover_services("_derbynet._tcp.local.")
        if discovered_services:
            # Get the first discovered service
            service_name = list(discovered_services.keys())[0]
            service_info = discovered_services[service_name]
            logger.info(f"Discovered MQTT broker: {service_info['name']} at {service_info['ip']}:{service_info['port']}")
            MQTT_BROKER = service_info['ip']
            MQTT_PORT = service_info['port']
        else:
            logger.warning("No derbynet services discovered, using default MQTT broker")
    except Exception as e:
        logger.error(f"Error during service discovery: {e}")
        logger.warning("Using default MQTT broker settings")

# Race timing and reliability settings
LANE_FINISH_TIMEOUT     = 90    # seconds to wait for all lanes to finish before auto-completion
HEARTBEAT_TIMEOUT       = 6     # seconds to consider a timer offline if no heartbeat received
HEARTBEAT_PULSE         = 1     # seconds to wait between heartbeat pulses
MQTT_QOS_CRITICAL       = 2     # QoS level for critical race messages
MQTT_QOS_NORMAL         = 1     # QoS level for normal operational messages

##### Subscribe Topics #####
MQTT_TOPIC_RACESTATE    = "derbynet/race/state"
MQTT_TOPIC_TELEMETRY    = "derbynet/device/+/telemetry"
MQTT_TOPIC_STATE        = "derbynet/device/+/state"

class derbyRace: 
    def __init__(self, lane_count = 3 ):
        logger.info("Initializing DerbyRace")
        self.boottime = datetime.now()
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "derbysvr" + str(random.randint(1000,9999)))
        self.client.on_log = self.on_log
        self.client.will_set("derbynet/status", payload="offline", qos=1, retain=True)
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect
        self.client.connect(MQTT_BROKER, MQTT_PORT, 90)
        self.client.loop_start()
        logger.info(f"Connected to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT}")
        self.api = DerbyNetClient("localhost") 
        self.start_time = 0
        self.lane_times = {}
        self.lanesFinished = 0
        self.lane_count = lane_count
        self.roundid = 0
        self.heatid = 0
        self.class_name = ""
        self.led = "red"
        self.lanePinny = {}
        self.race_state = "STOPPED" # STOPPED, RACING, STAGING
        self.timer_heartbeats = {} # stores the last heartbeat and isready status for each lane
        self.firstupdated = False
        self.last_heartbeat = 0 # updates to unix time when the last heartbeat was sent
        self.updateFromDerbyAPI()
        
    def on_log(self, client, userdata, level, buf): # callback for mqtt logging
        logger.debug(f"MQTT Log: {buf}")

    def on_connect(self, client, userdata, flags, rc, properties=None): # callback for mqtt connection
        self.mqtt_connected = True
        logger.info(f"Connected to MQTT broker with result code {rc}")
        
        # Subscribe to all required topics
        client.subscribe(MQTT_TOPIC_TELEMETRY)
        logger.info(f"Subscribed to {MQTT_TOPIC_TELEMETRY}")
        client.subscribe(MQTT_TOPIC_STATE)
        logger.info(f"Subscribed to {MQTT_TOPIC_STATE}")
        
        # Publish status message with high QoS
        client.publish("derbynet/status", payload="online", qos=MQTT_QOS_CRITICAL, retain=True)
        
    def on_disconnect(self, client, userdata, rc):
        self.mqtt_connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection with code {rc}, initiating reconnection")
            # Schedule reconnection attempt
            threading.Timer(5, self.connect_with_retry).start()
    
    def on_message(self, client, userdata, message): # callback for mqtt messages
        topic = message.topic
        payload = message.payload.decode("utf-8")
        logger.debug(f"Received message on {topic} {payload}") 
        
        # Validate message format first
        try:
            payload_data = json.loads(payload)
            
            # Extract device identification
            dip = payload_data.get("dip", "")
            hwid = payload_data.get("hwid", None)
            lane = self.getDIPName(dip)  # get the lane number from the dip switch
            
            # Store message for sequence tracking and duplicate detection
            if hwid and "state" in topic:
                message_id = payload_data.get("timestamp", time.time())
                if hasattr(self, 'timer_messages') and hasattr(self, 'store_received_message'):
                    self.store_received_message(hwid, topic, message_id, payload_data)
            
            ########### Trigger for START RACE ###########
            if "state" in topic and self.race_state == "STAGING": # Triggers start only if in staging mode
                val = payload_data.get("state", False)
                if val == "GO":
                    self.startRace()
                    self.api.send_start()
            
            ########### Trigger for LANE FINISH ###########
            if "state" in topic and self.race_state == "RACING" and lane > 0: 
                # Extract toggle state and validate
                toggle = payload_data.get("toggle", None)
                timestamp = payload_data.get("timestamp", time.time())
                
                if not toggle:# and hasattr(self, 'lane_finish_queue'):
                    # Queue the finish event for processing
                    #self.lane_finish_queue.put((lane, timestamp, payload_data))
                    #logger.info(f"Queued lane {lane} finish event with timestamp {timestamp}")
                #else:
                    # Fallback to direct processing if queue doesn't exist
                    self.laneFinish(lane)
            
            ########### Trigger for DEVICE TELEMETRY ###########
            if "telemetry" in topic: 
                # Send to API
                self.api.send_device_status(payload_data)
                
                # Update heartbeat timestamp
                isReady = payload_data.get("readyToRace", False)
                if lane > 0:
                    self.timerHeartbeat(lane,isReady)
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for message on {topic}: {e}")
        except Exception as e:
            logger.error(f"Error processing message on {topic}: {e}")

    def updateFromDerbyAPI(self): 
        # sets online
        self.client.publish("derbynet/status", payload="online", qos=1, retain=True)
        # called frequently once a second to update the finish timers and led colours
        racestats = self.api.get_race_status()
        self.roundid = racestats.get("roundid",0)
        self.heatid = racestats.get("heat",0)
        self.class_name = racestats.get("class","")
        lanes = racestats.get("lanes",[])
        self.setLEDFromRaceStat(racestats)
        for lane in lanes:
            self.setLanePinny(lane["lane"],lane["racerid"])
        # publish racestate
        result = self.client.publish(MQTT_TOPIC_RACESTATE, self.race_state, qos=1)
        if result.rc != 0:
            logger.error(f"Error publishing to {MQTT_TOPIC_RACESTATE} with rc {result.rc} and error {result.error_string}")

    def setLanePinny(self, lane, pinny):
        pinny = str(pinny).zfill(4)
        if self.lanePinny.get(str(lane),None) == pinny:
            return
        self.lanePinny[str(lane)] = pinny
        topic = f"derbynet/lane/{lane}/pinny"
        result = self.client.publish(topic, pinny, qos=2, retain=True)
        if result.rc != 0:
            logger.error(f"Error publishing to {topic} with rc {result.rc} and error {result.error_string}")
        logger.info(f"Set Lane {lane} to Pinny {pinny}")

    def setLEDFromRaceStat(self,racestats): # checks the api for the led to use and sends thusly 
        #racestats = api.get_race_status()
        led = None
        if racestats.get("active",False) and self.race_state == "STOPPED":
            led = "blue"
            self.race_state = "STAGING"
        if racestats.get("timer-state-string",) == "Race running":
           self.race_state = "RACING"
           led = "green"
           self.startRace()
        if not racestats.get("active",False):
            led = "red"
            self.race_state = "STOPPED"
        if led and led != self.led:
            self.led = led
            self.updateLED(led)
            logger.debug(f"Set LED to {led}")

    def updateLED(self,led,lane="all"):
        if lane == "all":
            for i in range(1,self.lane_count+1):
                topic = f"derbynet/lane/{i}/led"
                result = self.client.publish(topic, led, qos=2, retain=True)
                if result.rc != 0:
                    logger.error(f"Error publishing to {topic} with rc {result.rc} and error {result.error_string}")
        else:
            topic = f"derbynet/lane/{lane}/led"
            result = self.client.publish(topic, led, qos=2, retain=True)
            if result.rc != 0:
                logger.error(f"Error publishing to {topic} with rc {result.rc} and error {result.error_string}")
        #logger.info(f"Set LED to {led} for lane {lane}")
    
    def getRaceStatus(self):
        payload = {
            "state":self.race_state,
            "roundid":self.roundid,
            "heatid":self.heatid,
            "class":self.class_name,
            "lanetimes":self.lane_times
        }
        return payload

    def startRace(self, timer=None):
        """Initialize a new race with start time"""
        if timer is None:  # set to current timestamp 
            timer = time.time()
            
        if self.start_time == 0:  # not started yet
            # Reset race state
            self.lanesFinished = 0
            self.lane_times = {}
            self.start_time = timer
            
            # Log start with precision timestamp
            logger.info(f"Race started at {datetime.fromtimestamp(timer).strftime('%H:%M:%S.%f')[:-3]} (UNIX: {timer})")
            
            # Announce race start to all timers with high QoS
            start_payload = {
                "event": "race_start",
                "timestamp": timer,
                "roundid": self.roundid,
                "heatid": self.heatid
            }
            self.client.publish("derbynet/race/event", json.dumps(start_payload), qos=MQTT_QOS_CRITICAL)
        
    def stopRace(self,timer = None):
        if timer == None: # set to utc timestamp 
            timer = time.time()
        logger.info("All Lanes Finished at " + str(timer))
        self.race_state = "STOPPED"
        logger.info(self.lane_times)
        self.updateLED("red")
        self.api.send_finish(self.roundid,self.heatid,self.lane_times)
        self.lanesFinished = 0
        self.lane_times = {}
        self.start_time = 0
        
    def laneFinish(self, lane, timer=None, payload=None):
        if timer is None:
            timer = time.time()
            
        # Calculate race time
        if self.start_time > 0:
            race_time = round(timer - self.start_time, 3)  # Increased precision to 3 decimal places
        else:
            logger.warning(f"Lane {lane} finish detected but no valid start time recorded, using current time")
            race_time = 0.0
            
        # Record the finish time
        self.lane_times[lane] = race_time
        self.lanesFinished += 1
        
        # Log the finish with detailed information
        logger.info(f"Lane {lane} finished at {timer} with time {race_time}s (#{self.lanesFinished} to finish)")
        logger.debug(f"LaneFinishTimes: {self.lane_times}")
        
        # Update LED to indicate finish
        self.updateLED("purple", lane)  # purple for finished
        
        # Check if race is complete
        if self.lanesFinished == self.lane_count:
            self.stopRace(timer)
            return True
            
            
        return False
    
    def timerHeartbeat(self, lane, isReady = False): # is called from the telemetry message
        """Update timer heartbeat timestamp and check status"""
        current_time = time.time()
        prev_heartbeat = self.timer_heartbeats.get(lane, {})
        
        self.timer_heartbeats[lane] = {'time': current_time, 'isReady': isReady}
        logger.debug(f"Timer {lane} heartbeat at {current_time}, isReady: {isReady}")
        
        # If this is the first heartbeat or reconnection after timeout
        lastheartbeat = prev_heartbeat.get('time', 0)
        if lastheartbeat == 0 or (current_time - lastheartbeat) > HEARTBEAT_TIMEOUT:
            logger.info(f"Timer for lane {lane} is online")

        if prev_heartbeat.get('isReady', None) != isReady:
            logger.info(f"Timer for lane {lane} is now ready: {isReady}")

        # Check if all active timers have checked in recently and remove any that are offline from self.timer_heartbeats
        active_timers = [l for l in self.timer_heartbeats if self.timer_heartbeats[l]['time'] > current_time - HEARTBEAT_TIMEOUT]
        for lane_num in list(self.timer_heartbeats.keys()):
            if lane_num not in active_timers:
                logger.info(f"Timer for lane {lane_num} is offline")
                del self.timer_heartbeats[lane_num]

        # checks self.last_heartbeat to see if we need to send a heartbeat 
        if self.last_heartbeat == 0 or (current_time - self.last_heartbeat) > HEARTBEAT_PULSE:
            self.last_heartbeat = current_time
            logger.debug(f"Sending heartbeat to API {self.timer_heartbeats}")
            # sends self.timer_heartbeats to the api for a full status update
            self.api.send_timer_heartbeat(self.timer_heartbeats)
        # sample timer_heartbeats = {2: {'time': 1747607679.600188, 'isReady': True}, 1: {'time': 1747607678.8986795, 'isReady': False}, 3: {'time': 1747607681.1048107, 'isReady': True}}
        
        '''
        # Check if all active timers have checked in recently
        active_timers = [l for l in self.timer_heartbeat if l <= self.lane_count]
        if all(current_time - self.timer_heartbeat[l] < HEARTBEAT_TIMEOUT for l in active_timers):
            # Build a dynamic active_lanes dictionary for the heartbeat
            active_lanes = {}
            for lane_num in active_timers:
                # Use lane number as both key and value, with 'L' prefix for timer ID
                # This can be customized if you have specific timer IDs to use
                active_lanes[lane_num] = f"L{lane_num}"
            
            # All timers are online, send heartbeat to API with active lanes
            self.api.send_timer_heartbeat(active_lanes)
            logger.debug(f"Sent Timer Heartbeat to API with lanes: {active_lanes}")
            
        # Check for any timers that might be offline
        if hasattr(self, 'check_timer_status'):
            self.check_timer_status()
        '''

    def close(self,graceful = False):
        # Send offline status
        try:
            if hasattr(self, 'mqtt_connected') and self.mqtt_connected:
                self.client.publish("derbynet/status", payload="offline", qos=MQTT_QOS_CRITICAL, retain=True)
        except Exception as e:
            logger.error(f"Error sending offline status: {e}")
        
        # Clean up MQTT
        self.client.loop_stop()
        self.client.disconnect()
        logger.warning("DerbyRace Closed")
        
        # Exit with appropriate code
        if not graceful:
            exit(1)
        else:
            exit(0)
            
    def connect_with_retry(self):
        """Connect to MQTT broker with retry mechanism"""
        try:
            logger.info(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
            self.client.connect(MQTT_BROKER, MQTT_PORT, 90)
            self.client.loop_start()
            self.mqtt_connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            logger.info("Will retry connection in 5 seconds")
            threading.Timer(5, self.connect_with_retry).start()
            return False
    
    @staticmethod
    def getDIPName(dip):
        name = 0
        if dip == "1000": #lane1 
            name = 1
        elif dip == "1001": #lane2
            name = 2
        elif dip == "1010": #lane3
            name = 3
        elif dip == "1011": #lane4
            name = 4
        return name
    
    def sendServerTelemetry(self):
        '''
        "device_name": payload.get("hostname","UNKNOWN"),
        "serial": payload.get("hwid",""),
        "uptime": payload.get("uptime",0),
        "ip_address": payload.get("ip",""),
        "mac_address": payload.get("mac",""),
        "wifi_signal": self.getWiFiPercentFromRSSI(payload.get("wifi_rssi",0)),
        "battery": payload.get("battery_level",0),
        "temperature": payload.get("cpu_temp",0),
        "memory": payload.get("memory_usage",0),
        "disk": payload.get("disk",0),
        "cpu": payload.get("cpu_usage",0)}
        '''
        #self.boottime
        uptime = int((time.time() - self.boottime.timestamp()) ) # uptime in seconds
        cmd = "hostname -I | cut -d' ' -f1"
        ipaddr = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
        macaddr = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)])
        tempraw = subprocess.check_output("vcgencmd measure_temp", shell=True).decode("utf-8")
        temp =  float(tempraw.replace("temp=", "").replace("'C\n", ""))
        memusage = psutil.virtual_memory().percent
        cpuusage = psutil.cpu_percent()
        diskusage = psutil.disk_usage('/').percent
        payload = {
            "hostname": "derbynetpi",
            "hwid": "derbyRace",
            "uptime": uptime,
            "ip": ipaddr,
            "mac": macaddr,
            "wifi_rssi": str(0),
            "battery_level": 100,
            "cpu_temp": str(temp),
            "memory_usage": str(memusage),
            "disk": str(diskusage),
            "cpu_usage": str(cpuusage)
        }
        logger.debug(f"Telemetry: {payload}")
        self.api.send_device_status(payload)



if __name__ == "__main__":
    logger.debug("DerbyRace Started")
    #try:
    derby = derbyRace()
    #except Exception as e:
    #    logger.error(f"Error in DerbyRace: {e}")
    #    exit(1)
    while True:
        try:
            derby.updateFromDerbyAPI()
            derby.sendServerTelemetry()
        except KeyboardInterrupt:
            derby.close()
        except Exception as e:
            logger.error(f"Error in DerbyRace: {e}")
            derby.close()
            exit(1)
        time.sleep(0.75) # update every 0.75 seconds to keep the api happy and not hammer it too hard
    