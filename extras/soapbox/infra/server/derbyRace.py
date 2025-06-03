'''
Main program to handle the Derby race.

File location: /var/lib/infra/app/derbyRace.py
Service file: /etc/systemd/system/derbyrace.service

Version History:
- 0.5.0 - May 19, 2025 - Standardized version schema across all components
- 0.4.0 - May 10, 2025 - Added service discovery via mDNS
- 0.3.0 - April 22, 2025 - Added remote syslogging and improved error handling
- 0.2.0 - April 15, 2025 - Added telemetry and watchdog timers
- 0.1.0 - April 4, 2025 - Added MQTT communication protocols
- 0.0.1 - March 31, 2025 - Initial implementation
'''


import logging
from serverlogger import ServerLogger
from derbyapi import DerbyNetClient
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
import psutil # type: ignore 
import sys

# Version information
VERSION = "0.6.2"

logger = ServerLogger(
    name='DERBYSERVER', # Name of the logger, can be anything like 'finishtimer', 'derbydisplay', etc.
    log_file='/var/log/derbynet.log', # Default
    level=logging.INFO,  # Default log level
).get_logger()

# MQTT setup - Default values that will be used if service discovery fails
MQTT_BROKER             = "localhost"
MQTT_PORT               = 1883
MQTT_QOS_CRITICAL       = 2     # QoS level for critical race messages
MQTT_QOS_NORMAL         = 1     # QoS level for normal operational messages
##### Subscribe Topics #####
MQTT_TOPIC_RACESTATE    = "derbynet/race/state"
MQTT_TOPIC_TELEMETRY    = "derbynet/device/+/telemetry"
MQTT_TOPIC_STATE        = "derbynet/device/+/state"

# Race timing and reliability settings 
LANE_FINISH_TIMEOUT     = 90    # seconds to wait for all lanes to finish before auto-completion
HEARTBEAT_TIMEOUT       = 4     # seconds to consider a timer offline if no heartbeat received
HEARTBEAT_PULSE         = 1     # seconds to wait between heartbeat pulses
RACE_TIMEOUT            = 70    # seconds maximum race time before marking DNF
DNF_TIME               = 99.999 # DNF (Did Not Finish) time value
class derbyRace: 
    def __init__(self, lane_count = 3 ):
        logger.info(f"Initializing DerbyRace v{VERSION}")
        self.boottime = datetime.now()
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "derbysvr" )
        self.client.will_set("derbynet/status", payload="offline", qos=1, retain=True)
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect
        self.client.connect(MQTT_BROKER, MQTT_PORT, 90)
        self.client.loop_start()
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
        self.race_state = "" # STOPPED, RACING, STAGING
        self.timer_heartbeats = {} # stores the last heartbeat and isready status for each lane
        self.firstupdated = False
        self.last_heartbeat = 0 # updates to unix time when the last heartbeat was sent
        self.updateFromDerbyAPI()
        
    def on_connect(self, client, userdata, flags, rc, properties=None): # callback for mqtt connection
        self.mqtt_connected = True
        logger.debug(f"Connected to MQTT broker with result code {rc}")
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
            logger.critical(f"Unexpected MQTT disconnection with code {rc}, initiating reconnection")
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
            
            ########### Trigger for START RACE ###########
            if "state" in topic:
                logging.info(f"Received state change on {topic} with payload: {payload_data}")
                
            ########### Trigger for START RACE ###########
                val = payload_data.get("state", False)
                if val == "GO":
                    self.startRace()
                    self.api.send_start()
            
            ########### Trigger for LANE FINISH ###########
                if self.race_state == "RACING" and lane > 0: 
                    # Extract toggle state and validate
                    toggle = payload_data.get("toggle", None)
                    if not toggle: # must be a downward toggle to mimic crossing the finish line
                        # Only count finish if this lane hasn't already finished in this race
                        if lane not in self.lane_times:
                            self.laneFinish(lane)
                        else:
                            logger.warning(f"Lane {lane} finish ignored - already finished this race with time {self.lane_times[lane]}s")
                
            ########### Trigger for DEVICE TELEMETRY (ignore if active racing) ###########
            if "telemetry" in topic and self.race_state != "RACING":
                # Validate telemetry payload before sending to API
                required_fields = ["hostname", "hwid", "uptime", "ip", "mac"]
                if all(field in payload_data for field in required_fields):
                    # Send to API
                    success = self.api.send_device_status(payload_data)
                    if not success:
                        logger.warning(f"Failed to send device telemetry for {hwid}")
                else:
                    logger.error(f"Incomplete telemetry data from {hwid}: missing required fields")
                
                # Update heartbeat timestamp 
                isReady = payload_data.get("readyToRace", False)
                if lane > 0:
                    self.timerHeartbeat(lane, isReady)
                    logger.debug(f"Updated heartbeat for lane {lane}, ready: {isReady}")
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
        logger.debug(f"Race Stats: {racestats}")
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
        raceActive = racestats.get("active", None)
        timer_state_string = racestats.get("timer-state-string", "")
        prev_race_state = self.race_state
        
        if raceActive == True:
            # Race is active - determine proper state
            if timer_state_string == "Race running": 
                self.race_state = "RACING"
                led = "green"
            else:
                # Race is active but not running - we're staging
                self.race_state = "STAGING"
                led = "blue"
                # Only call set_staging if we're transitioning from a different state
                if prev_race_state in ["FINISHED", "STOPPED", ""]:
                    logger.info(f"Transitioning from {prev_race_state} to STAGING")
                    self.api.set_staging()
        else:
            # Race is not active 
            led = "red"
            self.race_state = "STOPPED"
            
        # Log state changes for debugging
        if prev_race_state != self.race_state:
            logger.info(f"Race state changed: {prev_race_state} -> {self.race_state}")
            # Force immediate heartbeat when race state changes to update DerbyNet quickly
            self.force_heartbeat_update()
            
        if led is not None and led != self.led: # only update if the led has changed
            self.led = led
            self.updateLED(led)
            logger.info(f"Set RACE LED to {led}")

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
            logger.info(f"RACE STARTED {datetime.fromtimestamp(timer).strftime('%H:%M:%S.%f')[:-3]} ({timer})")
            self.race_state = "RACING"
            self.updateLED("green")
        
    def stopRace(self,timer = None):
        if timer == None: # set to utc timestamp 
            timer = time.time()
        logger.info(f"RACE FINISHED {datetime.fromtimestamp(timer).strftime('%H:%M:%S.%f')[:-3]} ({timer})")
        self.race_state = "FINISHED"
        logger.info(self.lane_times)
        self.api.send_finish(self.roundid,self.heatid,self.lane_times)
        self.lanesFinished = 0
        self.lane_times = {}
        self.start_time = 0
        
    def laneFinish(self, lane, timer=None):
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
        logger.info(f"Lane {lane} finished at {timer} with time {race_time}s (#{self.lanesFinished} to finish) of total {self.lane_count} lanes")
        logger.debug(f"LaneFinishTimes: {self.lane_times}")
        
        # Update LED to indicate finish
        self.updateLED("purple", lane)  # purple for finished
        
        # Check if race is complete
        if self.lanesFinished == self.lane_count:
            self.stopRace(timer)
            return True
        return False
    
    def checkRaceTimeout(self):
        """Check if race has exceeded maximum time and mark unfinished lanes as DNF"""
        if self.race_state != "RACING" or self.start_time == 0:
            return False
            
        current_time = time.time()
        race_duration = current_time - self.start_time
        
        # Check if race has exceeded timeout
        if race_duration > RACE_TIMEOUT:
            dnf_lanes = []
            # Mark unfinished lanes as DNF
            for lane in range(1, self.lane_count + 1):
                if lane not in self.lane_times:
                    self.lane_times[lane] = DNF_TIME
                    self.lanesFinished += 1
                    dnf_lanes.append(lane)
                    # Update LED to indicate DNF
                    self.updateLED("red", lane)  # red for DNF
                    
            if dnf_lanes:
                logger.warning(f"Race timeout after {race_duration:.1f}s - marked lanes {dnf_lanes} as DNF with time {DNF_TIME}s")
                
                # Stop race if all lanes are now finished
                if self.lanesFinished >= self.lane_count:
                    self.stopRace(current_time)
                    return True
                    
        return False
    
    def timerHeartbeat(self, lane, isReady = False): # is called from the telemetry message
        """Update timer heartbeat timestamp and check status"""
        current_time = time.time()
        prev_heartbeat = self.timer_heartbeats.get(lane, {})
        
        # Update heartbeat for this specific lane
        self.timer_heartbeats[lane] = {'time': current_time, 'isReady': isReady}
    
        # If this is the first heartbeat or reconnection after timeout
        lastheartbeat = prev_heartbeat.get('time', 0)
        force_immediate_heartbeat = False
        
        if lastheartbeat == 0 or (current_time - lastheartbeat) > HEARTBEAT_TIMEOUT:
            logger.info(f"Timer for lane {lane} is online (reconnected)")
            force_immediate_heartbeat = True

        if prev_heartbeat.get('isReady', None) != isReady:
            logger.info(f"Timer for lane {lane} ready state changed to: {isReady}")
            force_immediate_heartbeat = True

        # Clean up offline timers (moved to separate function to avoid race conditions)
        self.cleanup_offline_timers(current_time)

        # Send heartbeat to API every second, or immediately if there's a state change
        # This ensures DerbyNet always knows we're alive and gets current status
        if force_immediate_heartbeat or (current_time - self.last_heartbeat) >= HEARTBEAT_PULSE:
            self.send_heartbeat_to_api(current_time)
    
    def cleanup_offline_timers(self, current_time):
        """Remove timers that haven't sent heartbeats within timeout period"""
        offline_timers = []
        for lane_num in list(self.timer_heartbeats.keys()):
            if (current_time - self.timer_heartbeats[lane_num]['time']) > HEARTBEAT_TIMEOUT:
                offline_timers.append(lane_num)
                logger.warning(f"Timer for lane {lane_num} is offline (no heartbeat for {current_time - self.timer_heartbeats[lane_num]['time']:.1f}s)")
                del self.timer_heartbeats[lane_num]
        
        return offline_timers
    
    def send_heartbeat_to_api(self, current_time):
        """Send heartbeat to DerbyNet API with current timer status"""
        self.last_heartbeat = current_time
        
        # Log current timer status
        online_timers = list(self.timer_heartbeats.keys())
        ready_timers = [lane for lane, data in self.timer_heartbeats.items() if data.get('isReady', False)]
        
        logger.debug(f"Heartbeat: Online={online_timers}, Ready={ready_timers}")
        
        if len(online_timers) < self.lane_count:
            missing = [i for i in range(1, self.lane_count + 1) if i not in online_timers]
            logger.warning(f"Missing timers for lanes: {missing}")
        
        # Send heartbeat to API - this will determine confirmation based on current status
        success = self.api.send_timer_heartbeat(self.timer_heartbeats)
        if not success:
            logger.error("Failed to send timer heartbeat to API")
    
    def force_heartbeat_update(self):
        """Force an immediate heartbeat update - useful when state changes"""
        current_time = time.time()
        self.last_heartbeat = 0  # Reset to force immediate send
        self.send_heartbeat_to_api(current_time)
        logger.debug("Forced immediate heartbeat update")
        

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
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
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
            "version": VERSION,
            "uptime": uptime,
            "ip": ipaddr,
            "mac": macaddr,
            "wifi_rssi": str(random.randint(-40, -30)),  # Simulated RSSI value
            "battery_level": 100,
            "cpu_temp": str(temp),
            "memory_usage": str(memusage),
            "disk": str(diskusage),
            "cpu_usage": str(cpuusage)
        }
        logger.debug(f"Telemetry: {payload}")
        self.api.send_device_status(payload)

if __name__ == "__main__":
    logger.info("DerbyRace Server Started")
    derby = derbyRace()
    while True:
        try:
            derby.updateFromDerbyAPI()
            derby.sendServerTelemetry()
            # Check for race timeout during active racing
            if derby.race_state == "RACING":
                derby.checkRaceTimeout()
        except KeyboardInterrupt:
            derby.close()
        except Exception as e:
            logger.error(f"Error in DerbyRace: {e}")
            derby.close()
            exit(1)
        time.sleep(1) # update every .5 seconds to keep the api happy and not hammer it too hard
    