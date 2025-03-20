'''
Main program to handle the Derby race.

'''

import logging 
from datetime import datetime
import time
import paho.mqtt.client as mqtt # type: ignore
import random
import json
from derbyapi import DerbyNetClient
import RPi.GPIO as GPIO # type: ignore

GPIO.setmode(GPIO.BCM)
PIN_START_BUTTON = 7
GPIO.setup(PIN_START_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)
api = DerbyNetClient("localhost")

# MQTT setup
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

# Logging setup
logging.basicConfig( level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')#, filename='derbyRace.log')

class derbyRace: 
    def __init__(self, lane_count = 3 ):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "derbyupdater" + str(random.randint(1000,9999)))
        self.client.connect(MQTT_BROKER, MQTT_PORT, 90)
        # subscribe to the derbynet topics for finish timer heartbeats and toggle states
        self.client.subscribe("derbynet/lane/+/telemetry", qos=1)
        self.client.subscribe("derbynet/lane/+/state", qos=1)
        self.client.on_message = self.on_message
        self.client.loop_start()
        self.start_time = 0
        self.lane_times = {}
        self.lanesFinished = 0
        self.lane_count = lane_count
        self.roundid = 0
        self.heatid = 0
        self.class_name = ""
        self.race_state = "STOPPED" # STOPPED, RACING, STAGING
        self.timer_heartbeat = {} 
        self.firstupdated = False
        self.updateFromDerbyAPI()
        logging.info("Initialized")
        
    def on_message(self, client, userdata, message): # callback for mqtt messages
        topic = message.topic
        lane = int(topic.split("/")[2])
        payload = message.payload.decode("utf-8")
        logging.info(f"Received message on {topic}: {payload}")
        logging.info(f"RaceState: {self.race_state}")
        # check for finish toggle if race is active to indicate someone has crossed the finish line
        if "state" in topic and self.race_state == "RACING": # this can only happen if the individual finish is triggered 
            logging.info(f"Received state message on {topic}: {payload}")
            self.laneFinish(lane)
            logging.info(f"Lane {lane} Finished. Lane data: {self.lane_times}")
        if "telemetry" in topic:
            self.timerHeartbeat(lane)

    def updateFromDerbyAPI(self): # called frequently once a second to update the finish timers and led colours
        racestats = api.get_race_status()
        if not self.firstupdated:
            self.setLEDFromRaceStat(racestats)
            self.firstupdated = True
        self.roundid = racestats.get("roundid",0)
        self.heatid = racestats.get("heat",0)
        self.class_name = racestats.get("class","")
        lanes = racestats.get("lanes",[])
        self.setLEDFromRaceStat(racestats)
        for lane in lanes:
            self.setLanePinny(lane["lane"],lane["racerid"])

    def setLanePinny(self, lane, pinny):
        pinny = str(pinny).zfill(4)
        topic = f"derbynet/lane/{lane}/pinny"
        self.client.publish(topic, pinny, qos=1)
        #logging.info(f"Set Lane {lane} to Pinny {pinny}")

    def setLEDFromRaceStat(self,racestats): # checks the api for the led to use and sends thusly 
        #racestats = api.get_race_status()
        #print(racestats)
        led = None
        if racestats.get("active",False) and self.race_state == "STOPPED":
            led = "blue"
            self.race_state = "STAGING"
        if racestats.get("timer-state-string",) == "Race running":
           self.race_state == "RACING"
           led = "green"
        if not racestats.get("active",False):
            led = "red"
            self.race_state = "STOPPED"
        if led: 
            self.updateLED(led)
            #logging.info(f"Set LED to {led}")

    def updateLED(self,led,lane=all):
        if lane == all:
            for i in range(1,self.lane_count+1):
                topic = f"derbynet/lane/{i}/led"
                self.client.publish(topic, led, qos=1)
        else:
            topic = f"derbynet/lane/{lane}/led"
            self.client.publish(topic, led, qos=1)
    
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
        self.start_time = timer
        logging.info("Race Started at " + str(int(self.start_time)))
        self.race_state = "RACING"
        self.updateLED("green") # racing
        api.send_start()
        
    def laneFinish(self,lane,timer = None):
        if timer == None:
            timer = time.time()
        self.lane_times[lane] = int(timer) - int(self.start_time)
        logging.info(f"Lane {lane} Finished")
        self.lanesFinished += 1
        if self.lanesFinished == self.lane_count:
            logging.info("All Lanes Finished")
            self.race_state = "STOPPED"
            logging.info(self.lane_times)
            print(self.lane_times)
            self.updateLED("red")
            api.send_finish(self.roundid,self.heatid,self.lane_times)
            self.lanesFinished = 0
            self.lane_times = {}
            self.start_time = 0
            return True
        return False
    
    def timerHeartbeat(self,lane):
        self.timer_heartbeat[lane] = time.time()
        # check if all timers have checked in in the last 30 seconds and then send an api command for heartbeat
        if all(time.time() - self.timer_heartbeat[lane] < 90 for lane in self.timer_heartbeat):
            api.send_timer_heartbeat()
            logging.info("Sent Timer Heartbeat")
 
if __name__ == "__main__":
    derby = derbyRace()
    stime = time.time()
    while True:
        derby.updateFromDerbyAPI() # polls the api and updates the led and pinny data
        if GPIO.input(PIN_START_BUTTON) == 0:
            logging.info("Start Button Pressed")
            derby.startRace()
        time.sleep(1)
        