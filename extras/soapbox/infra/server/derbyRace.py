'''
Main program to handle the Derby race.

File location: /var/lib/infra/app/derbyRace.py
Service file: /etc/systemd/system/derbyrace.service

'''

import logging 
from datetime import datetime
import time
import paho.mqtt.client as mqtt # type: ignore
import random
import json
from derbyapi import DerbyNetClient

# MQTT setup
MQTT_BROKER             = "localhost"
MQTT_PORT               = 1883

##### Subscribe Topics #####
MQTT_TOPIC_RACESTATE    = "derbynet/race/state"
MQTT_TOPIC_TELEMETRY    = "derbynet/device/+/telemetry"
MQTT_TOPIC_STATE        = "derbynet/device/+/state"

LOG_FORMAT      = '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] %(message)s'
LOG_FILE        = '/var/log/derbynet.log'

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, filename=LOG_FILE)

class derbyRace: 
    def __init__(self, lane_count = 3 ):
        logging.info("Initializing DerbyRace")
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "derbysvr" + str(random.randint(1000,9999)))
        self.client.on_log = self.on_log
        self.client.will_set("derbynet/status", payload="offline", qos=1, retain=True)
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect
        self.client.connect(MQTT_BROKER, MQTT_PORT, 90)
        self.client.loop_start()
        logging.info(f"Connected to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT}")
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
        logging.debug(f"MQTT Log: {buf}")

    def on_connect(self, client, userdata, flags, rc, properties=None): # callback for mqtt connection
        logging.info(f"Connected with result code {rc}")        
        client.subscribe(MQTT_TOPIC_TELEMETRY)
        logging.info(f"Subscribed to {MQTT_TOPIC_TELEMETRY}")
        client.subscribe(MQTT_TOPIC_STATE)
        logging.info(f"Subscribed to {MQTT_TOPIC_STATE}")
    
    def on_message(self, client, userdata, message): # callback for mqtt messages
        topic = message.topic
        payload = message.payload.decode("utf-8")
        logging.debug(f"Received message on {topic} {payload}") 
        # Received message on derbynet/device/DT54SIV0002/state: {"toggle": true, "time": 1742533387, "hwid": "DT54SIV0002", "dip": "1001"}
        #logging.info(f"RaceState: {self.race_state}")
        # check for finish toggle if race is active to indicate someone has crossed the finish line
        try:
            dip = json.loads(payload).get("dip","")
        except Exception as e:
            dip = ""
            logging.error(f"Error parsing dip from payload: {e}")
        if dip == "1000": #lane1 
            lane = 1
        elif dip == "1001": #lane2
            lane = 2
        elif dip == "1010": #lane3
            lane = 3
        elif dip == "1011": #lane4
            lane = 4
        else: 
            lane = 0
        if "state" in topic and self.race_state == "STAGING": # Triggers start only if in staging mode
            val = json.loads(payload).get("state",False)
            if val == "GO":
                self.startRace()
                self.api.send_start()
        if "state" in topic and self.race_state == "RACING" and lane > 0: # this can only happen if the individual finish is triggered 
            self.laneFinish(lane)
        if "telemetry" in topic and lane > 0: # this is the heartbeat from the timer to indicate it is alive and well
            logging.debug(f"Timer heartbeat from lane {lane} with payload {payload}")
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
            logging.error(f"Error publishing to {MQTT_TOPIC_RACESTATE} with rc {result.rc} and error {result.error_string}")

    def setLanePinny(self, lane, pinny):
        pinny = str(pinny).zfill(4)
        if self.lanePinny.get(str(lane),None) == pinny:
            return
        self.lanePinny[str(lane)] = pinny
        topic = f"derbynet/lane/{lane}/pinny"
        result = self.client.publish(topic, pinny, qos=2, retain=True)
        if result.rc != 0:
            logging.error(f"Error publishing to {topic} with rc {result.rc} and error {result.error_string}")
        logging.info(f"Set Lane {lane} to Pinny {pinny}")

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
            logging.info(f"Set LED to {led}")

    def updateLED(self,led,lane="all"):
        if lane == "all":
            for i in range(1,self.lane_count+1):
                topic = f"derbynet/lane/{i}/led"
                result = self.client.publish(topic, led, qos=2, retain=True)
                if result.rc != 0:
                    logging.error(f"Error publishing to {topic} with rc {result.rc} and error {result.error_string}")
        else:
            topic = f"derbynet/lane/{lane}/led"
            result = self.client.publish(topic, led, qos=2, retain=True)
            if result.rc != 0:
                logging.error(f"Error publishing to {topic} with rc {result.rc} and error {result.error_string}")
        #logging.info(f"Set LED to {led} for lane {lane}")
    
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
            self.start_time = timer
            logging.info("Race Started at " + str(int(self.start_time)))
        #self.race_state = "RACING"
        #self.updateLED("green") # racing
        #api.send_start()

    def stopRace(self,timer = None):
        if timer == None: # set to utc timestamp 
            timer = time.time()
        logging.info("All Lanes Finished at " + str(int(timer)))
        self.race_state = "STOPPED"
        logging.info(self.lane_times)
        self.updateLED("red")
        self.api.send_finish(self.roundid,self.heatid,self.lane_times)
        self.lanesFinished = 0
        self.lane_times = {}
        self.start_time = 0
        
    def laneFinish(self,lane,timer = None):
        if timer == None:
            timer = time.time()
        self.lane_times[lane] = int(timer) - int(self.start_time)
        logging.info(f"Lane {lane} Finished at {int(timer)} with time {self.lane_times[lane]}")
        #pinny = str(int(self.lane_times[lane])).zfill(4)
        #self.setLanePinny(lane,pinny)
        self.updateLED("purple",lane) # purple for finished
        self.lanesFinished += 1
        if self.lanesFinished == self.lane_count:
            self.stopRace(timer)
            return True
        return False
    
    def timerHeartbeat(self,lane):
        self.timer_heartbeat[lane] = time.time()
        # check if all timers have checked in in the last 30 seconds and then send an api command for heartbeat
        if all(time.time() - self.timer_heartbeat[lane] < 90 for lane in self.timer_heartbeat):
            self.api.send_timer_heartbeat()
            logging.debug("Sent Timer Heartbeat")

    def close(self,graceful = False):
        self.client.loop_stop()
        self.client.disconnect()
        logging.info("DerbyRace Closed")
        if not graceful:
            exit(1)
        else:
            exit(0)

if __name__ == "__main__":
    logging.info("DerbyRace Started")
    try:
        derby = derbyRace()
    except Exception as e:
        logging.error(f"Error in DerbyRace: {e}")
        exit(1)
    while True:
        try:
            derby.updateFromDerbyAPI()
        except KeyboardInterrupt:
            derby.close()
        except Exception as e:
            logging.error(f"Error in DerbyRace: {e}")
            derby.close()
            exit(1)
        time.sleep(0.75) # update every 0.75 seconds to keep the api happy and not hammer it too hard
    