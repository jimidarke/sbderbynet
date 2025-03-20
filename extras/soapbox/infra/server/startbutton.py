'''
This will monitor the GPIO 16 which is connected to a momentary push button and ground, and will send a start message to the derbynet server when the button is pressed.  This is used to start the timer and turns the light green to start the race. 

localfile   /var/lib/infra/app/startbutton.py
servicefile /etc/systemd/system/startbutton.service

'''

import RPi.GPIO as GPIO # type: ignore
import time
#import requests # type: ignore
import xml.etree.ElementTree as ET
import sys
from derbyapi import DerbyNetClient

SERVER_IP = "127.0.0.1"
api = DerbyNetClient(SERVER_IP)

PIN_GO_TRIGGER = 4  # GPIO connected to momentary push button, and ground. Needs a pull up resistor

''' Logging settings '''
import logging
LOG_LEVEL = logging.INFO
LOG_FILE = '/var/lib/infra/derby-start.log'
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
logging.basicConfig(filename=LOG_FILE, level=LOG_LEVEL, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

# Set up GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_GO_TRIGGER, GPIO.IN, pull_up_down=GPIO.PUD_UP)    

# Button callback
def startButtonCallback(channel):
    logging.info("Start button pressed")
    print("Start button pressed")
    api.send_start()

GPIO.add_event_detect(PIN_GO_TRIGGER, GPIO.FALLING, callback=startButtonCallback, bouncetime=150)
    
def main():
    print ("Starting Start Button Monitor")
    logging.info("Starting Start Button Monitor")
    api.login()
    while True: 
        time.sleep(0.1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error("Error: " + str(e))
        print("Error: " + str(e))
    finally:
        GPIO.cleanup()
        logging.info("Exiting")
        print("Exiting")