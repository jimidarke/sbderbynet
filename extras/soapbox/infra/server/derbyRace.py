'''
Main program to handle the Derby race.

File location: /var/lib/infra/app/derbyRace.py
Service file: /etc/systemd/system/derbyrace.service

'''


from datetime import datetime
import os
import subprocess
import time
import uuid
import paho.mqtt.client as mqtt # type: ignore
import random
import json
from derbyapi import DerbyNetClient
from derbylogger import setup_logger
import psutil # type: ignore

logger = setup_logger("derbyRace")

# MQTT setup
MQTT_BROKER             = "localhost"
MQTT_PORT               = 1883

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
        self.timer_heartbeat = {} 
        self.firstupdated = False
        self.updateFromDerbyAPI()
        
    def on_log(self, client, userdata, level, buf): # callback for mqtt logging
        logger.debug(f"MQTT Log: {buf}")

    def on_connect(self, client, userdata, flags, rc, properties=None): # callback for mqtt connection
        logger.debug(f"Connected with result code {rc}")        
        client.subscribe(MQTT_TOPIC_TELEMETRY)
        logger.info(f"Subscribed to {MQTT_TOPIC_TELEMETRY}")
        client.subscribe(MQTT_TOPIC_STATE)
        logger.info(f"Subscribed to {MQTT_TOPIC_STATE}")
    
    def on_message(self, client, userdata, message): # callback for mqtt messages
        topic = message.topic
        payload = message.payload.decode("utf-8")
        logger.debug(f"Received message on {topic} {payload}") 
        dip = None
        try:
            dip = json.loads(payload).get("dip","")
        except Exception as e:
            logger.error(f"Error parsing dip from payload: {e}")
        lane = self.getDIPName(dip) # get the lane number from the dip switch
        
        ########### Trigger for START RACE ###########
        if "state" in topic and self.race_state == "STAGING": # Triggers start only if in staging mode
            val = json.loads(payload).get("state",False)
            if val == "GO":
                self.startRace()
                self.api.send_start()
        
        ########### Trigger for LANE FINISH ###########
        if "state" in topic and self.race_state == "RACING" and lane > 0: # run through lane finish check
            self.laneFinish(lane)
        
        ########### Trigger for DEVICE TELEMETRY ###########
        if "telemetry" in topic: # this is the heartbeat from the timer to indicate it is alive and well as well as status telemetry
            #logger.info(f"Telemetry from {topic}")
            logger.debug(f"Telemetry from {topic} with payload {payload}")
            self.api.send_device_status(json.loads(payload))
            if lane > 0:
                self.timerHeartbeat(lane)

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

    def startRace(self,timer = None):
        if timer == None: # set to utc timestamp 
            timer = time.time()
        if self.start_time == 0: # not started yet
            self.lanesFinished = 0
            self.start_time = timer
            logger.info("Race Started at " + str(self.start_time))
        
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
        
    def laneFinish(self,lane,timer = None):
        if timer == None:
            timer = time.time()
        self.lane_times[lane] = round(timer - self.start_time,1)
        self.lanesFinished += 1
        logger.info(f"Lane {lane} Finished at {timer} with time {self.lane_times[lane]}s which is # {self.lanesFinished} to finish")
        logger.debug(f"LaneFinishTimes: {self.lane_times}")
        self.updateLED("purple",lane) # purple for finished
        if self.lanesFinished == self.lane_count:
            self.stopRace(timer)
            return True
        return False
    
    def timerHeartbeat(self,lane):
        self.timer_heartbeat[lane] = time.time()
        # check if all timers have checked in in the last 30 seconds and then send an api command for heartbeat
        if all(time.time() - self.timer_heartbeat[lane] < 90 for lane in self.timer_heartbeat):
            self.api.send_timer_heartbeat()
            logger.debug("Sent Timer Heartbeat")

    def close(self,graceful = False):
        self.client.loop_stop()
        self.client.disconnect()
        logger.warning("DerbyRace Closed")
        if not graceful:
            exit(1)
        else:
            exit(0)
    
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
    