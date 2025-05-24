'''
    Communicates with the DerbyNet API to manage logins, exceptions, and functions like start and finish

from derbyapi import DerbyNetClient
SERVERIP = "192.168.100.10"

api = DerbyNetClient(SERVERIP)


Device status telemetry format V 0.2.1

hostname
hwid
uptime
ip
mac
wifi_rssi
battery_level
cpu_temp
memory_usage
disk
cpu_usage

'''
 
#import requests # type: ignore
import time
from pip._vendor import requests

import xml.etree.ElementTree as ET

from derbylogger import setup_logger
logger = setup_logger("derbyapi")

# DerbyNet Timer State Constants
TIMER_STATE_CONNECTED = "CONNECTED"
TIMER_STATE_STAGING = "STAGING"
TIMER_STATE_RUNNING = "RUNNING"
TIMER_STATE_UNHEALTHY = "UNHEALTHY"
TIMER_STATE_NOT_CONNECTED = "NOT_CONNECTED"

# Heartbeat Constants
HEARTBEAT_INTERVAL = 60  # DerbyNet requires a heartbeat every 60 seconds

class DerbyNetClient:
    """Handles authentication and communication with the DerbyNet server."""

    def __init__(self, server_ip = None):
        if not server_ip:
            server_ip = "192.168.100.10"
        self.url = f"http://{server_ip}/derbynet/action.php"
        self.rooturl = f"http://{server_ip}/derbynet/"
        self.server_ip = server_ip
        self.authcode = None
        self.timer_state = TIMER_STATE_NOT_CONNECTED
        self.last_heartbeat_time = 0
        self.last_connection_attempt = 0

    def login(self):
        """Logs in to the DerbyNet server and retrieves an auth cookie."""
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        payload = 'action=role.login&name=Timer&password='
        self.authcode = None
        attempt = 1
        
        # Record connection attempt time
        self.last_connection_attempt = time.time()
        
        while attempt < 5:
            try: 
                response = requests.post(self.url, headers=headers, data=payload, timeout=5)
                if response.status_code == 200:
                    break
            except Exception as e:
                logger.error(f"Login failed: {e}")
            time.sleep(1 * attempt)  # Wait before retrying
            attempt += 1
        if attempt >= 5:
            logger.critical("Failed to login after multiple attempts.")
            self.timer_state = TIMER_STATE_NOT_CONNECTED
            exit(1)
            return None
        response_json = response.json()
        if response_json.get("outcome", {}).get("code") == "success":
            auth_code = response.headers.get('Set-Cookie', '').split(';')[0]
            logger.debug("Successfully logged in with authcode: %s", auth_code)
            self.authcode = auth_code
            self.timer_state = TIMER_STATE_CONNECTED
            return auth_code
        else:
            logger.error("Login failed: Invalid credentials or server error. API Response: %s", response.text)
            self.timer_state = TIMER_STATE_NOT_CONNECTED
            return None    
    
    def send_timer_heartbeat(self, timer_heartbeats):  # sends heartbeat messages
        """
        Send heartbeat message to DerbyNet with active timer information
        
        timer_heartbeats = {2: {'time': 1747607679.600188, 'isReady': True}, 1: {'time': 1747607678.8986795, 'isReady': False}, 3: {'time': 1747607681.1048107, 'isReady': True}}
        """
        current_time = time.time()
        
        # Check if we need to send a heartbeat (required every 60 seconds by DerbyNet)
        if (current_time - self.last_heartbeat_time) < HEARTBEAT_INTERVAL:
            # Only send if state changes or we're approaching the deadline
            if (current_time - self.last_heartbeat_time) < (HEARTBEAT_INTERVAL - 5):
                # If not near the deadline, only send if state changed or first heartbeat
                if self.last_heartbeat_time > 0:
                    return True
        
        if not self.authcode:
            self.authcode = self.login()
            if not self.authcode:
                logger.critical("Failed to authenticate with DerbyNet.")
                self.timer_state = TIMER_STATE_NOT_CONNECTED
                return False
        
        # check if all timers are online by virtue of being in the dictionary
        online1 = True if 1 in timer_heartbeats else False
        online2 = True if 2 in timer_heartbeats else False
        online3 = True if 3 in timer_heartbeats else False
        
        # checks if all timers are ready
        ready1 = timer_heartbeats.get(1, {}).get('isReady', False)
        ready2 = timer_heartbeats.get(2, {}).get('isReady', False)
        ready3 = timer_heartbeats.get(3, {}).get('isReady', False)
        if ready1 and ready2 and ready3 and online1 and online2 and online3:
            confirmed = 1
        else:
            confirmed = 0

        # Build dynamic payload
        payload = "message=HEARTBEAT&action=timer-message&confirmed=" + str(confirmed)
        for lane, data in timer_heartbeats.items():
            payload += f"&timerId{lane}=L{lane}&lane{lane}=1"
            if data.get('isReady', False):
                payload += f"&ready{lane}=1"
            else:
                payload += f"&ready{lane}=0"
        
        headers = {
            'Content-Type': "application/x-www-form-urlencoded",
            'Cookie': self.authcode
        }
        logger.debug("Sending heartbeat message: %s", payload)
        try:
            response = requests.post(self.url, headers=headers, data=payload, timeout=5)
            if response.status_code == 401: # unauthed, send for login
                self.authcode = self.login()
                return self.send_timer_heartbeat(timer_heartbeats)
                
            response.raise_for_status()
            # Update last heartbeat time
            self.last_heartbeat_time = current_time
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to send heartbeat message: {e}")
            # Set timer state to UNHEALTHY if connection failed
            if self.timer_state != TIMER_STATE_NOT_CONNECTED:
                self.timer_state = TIMER_STATE_UNHEALTHY
            return False
    
    def set_timer_state(self, new_state):
        """
        Updates the timer state and ensures it's properly synchronized with DerbyNet
        """
        if new_state not in [TIMER_STATE_CONNECTED, TIMER_STATE_STAGING, TIMER_STATE_RUNNING, 
                            TIMER_STATE_UNHEALTHY, TIMER_STATE_NOT_CONNECTED]:
            logger.error(f"Invalid timer state: {new_state}")
            return False
            
        # Check for invalid state transitions
        #if (new_state == TIMER_STATE_RUNNING and self.timer_state != TIMER_STATE_STAGING):
        #    logger.warning(f"Invalid state transition: {self.timer_state} -> {new_state}")
        #    return False
            
        # Record the state change
        old_state = self.timer_state
        self.timer_state = new_state
        
        # Log the state change
        logger.info(f"Timer state changed: {old_state} -> {new_state}")
        
        # Forced heartbeat on state change to update DerbyNet immediately
        if old_state != new_state:
            self.last_heartbeat_time = 0  # Force a heartbeat
            
        return True
        
    def send_start(self):
        """Sends the start signal to the DerbyNet server."""
        if not self.authcode:
            self.authcode = self.login()
            if not self.authcode:
                logger.critical("Failed to authenticate with DerbyNet.")
                return False
        
        # Update the timer state to RUNNING
        if not self.set_timer_state(TIMER_STATE_RUNNING):
            logger.error("Failed to transition to RUNNING state")
            return False

        payload = "message=STARTED&action=timer-message"
        headers = {
            'Content-Type': "application/x-www-form-urlencoded",
            'Cookie': self.authcode
        }

        try:
            response = requests.post(self.url, headers=headers, data=payload, timeout=5)
            if response.status_code == 401: # unauthed, send for login
                self.authcode = self.login()
                return self.send_start()
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to send start message: {e}")
            self.set_timer_state(TIMER_STATE_UNHEALTHY)
            return False

        response_xml = ET.fromstring(response.text)

        if response_xml.find('failure') is not None:
            logger.warning("Authentication failed, retrying login...")
            self.authcode = self.login()
            if self.authcode:
                return self.send_start()
            else:
                logger.critical("Failed to re-authenticate after failure.")
                self.set_timer_state(TIMER_STATE_NOT_CONNECTED)
                return False

        if response_xml.find('success') is not None:
            logger.debug("Start message successfully sent.")
            return True
        else:
            logger.error("Failed to confirm start message reception.")
            return False

    def send_finish(self, roundid, heatid, lane_times):
        """Sends the finish signal to the DerbyNet server."""
        if not self.authcode:
            self.authcode = self.login()
            if not self.authcode:
                logger.critical("Failed to authenticate with DerbyNet.")
                return False
                
        # Update the timer state back to CONNECTED after finish
        self.set_timer_state(TIMER_STATE_CONNECTED)
        
        payload =f"message=FINISHED&action=timer-message&roundid={roundid}&heat={heatid}" 
        #&lane1=10&lane2=12&lane3=13&place1=1&place2=2&place3=3"
        for lane, time in lane_times.items():
            payload += f"&lane{lane}={time}"
        headers = {
            'Content-Type': "application/x-www-form-urlencoded",
            'Cookie': self.authcode
        }
        try:
            response = requests.post(self.url, headers=headers, data=payload, timeout=5)
            if response.status_code == 401: # unauthed, send for login
                self.authcode = self.login()
                return self.send_finish(roundid, heatid, lane_times)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to send finish message: {e}")
            self.set_timer_state(TIMER_STATE_UNHEALTHY)
            return False

        response_xml = ET.fromstring(response.text)

        if response_xml.find('failure') is not None:
            logger.warning("Authentication failed, retrying login...")
            self.authcode = self.login()
            if self.authcode:
                return self.send_finish(roundid, heatid, lane_times)
            else:
                logger.critical("Failed to re-authenticate after failure.")
                self.set_timer_state(TIMER_STATE_NOT_CONNECTED)
                return False

        if response_xml.find('success') is not None:
            logger.info("Finish message successfully sent.")
            return True
        else:
            logger.error("Failed to confirm finish message reception.")
            return False
    
    def set_staging(self):
        """Sets the timer state to STAGING and notifies DerbyNet."""
        if not self.authcode:
            self.authcode = self.login()
            if not self.authcode:
                logger.critical("Failed to authenticate with DerbyNet.")
                return False
                
        # Update the timer state to STAGING
        if not self.set_timer_state(TIMER_STATE_STAGING):
            logger.error("Failed to transition to STAGING state")
            return False
            
        # Send the staging message to DerbyNet
        payload = "message=STAGING&action=timer-message"
        headers = {
            'Content-Type': "application/x-www-form-urlencoded",
            'Cookie': self.authcode
        }

        try:
            response = requests.post(self.url, headers=headers, data=payload, timeout=5)
            if response.status_code == 401: # unauthed, send for login
                self.authcode = self.login()
                return self.set_staging()
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to send staging message: {e}")
            self.set_timer_state(TIMER_STATE_UNHEALTHY)
            return False
    
    def get_race_status(self):
        # gets the race status and updates mqtt 
        if not self.authcode:
            self.authcode = self.login()
            if not self.authcode:
                logger.critical("Failed to authenticate with DerbyNet.")
                return False
        headers = {
            'Accept': 'application/json',
            'Cookie': self.authcode
        }
        payload = ''
        url = self.url + '?query=poll.coordinator'
        try:
            response = requests.get(url, headers=headers, data=payload, timeout=5)
            if response.status_code == 401:
                self.authcode = self.login()
                return self.get_race_status()
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to get race status: {e}")
            self.set_timer_state(TIMER_STATE_UNHEALTHY)
            return False
        response_json = response.json()
        out = {}
        out['active'] = response_json.get('current-heat', {}).get('now_racing', False)
        out['roundid'] = response_json.get('current-heat', {}).get('roundid', 0)
        out['heat'] = response_json.get('current-heat', {}).get('heat', 0)
        out['class'] = response_json.get('current-heat', {}).get('class', '')
        out['lane-count'] = response_json.get('race_info', {}).get('lane_count', 0)
        if 'racers' in response_json:
            out['lanes'] = []
            for lane in response_json['racers']:
                out['lanes'].append({'lane': lane['lane'], 'name': lane['name'], 'racerid': lane['carnumber']})
        else:
            out['lanes'] = []
        out['timer-state'] = response_json.get('timer-state', {}).get('state', '')
        out['timer-state-string'] = response_json.get('timer-state', {}).get('message', '')
        
        # Sync our internal state with DerbyNet's view if possible
        derbynet_state = out.get('timer-state', '')
        if derbynet_state:
            if derbynet_state == "connected":
                self.timer_state = TIMER_STATE_CONNECTED
            elif derbynet_state == "staging":
                self.timer_state = TIMER_STATE_STAGING
            elif derbynet_state == "running":
                self.timer_state = TIMER_STATE_RUNNING
            
        return out
    
    def send_device_status(self,payload):
        # sends telemetry data to the DerbyNet server for the Device Status API
        if not self.authcode:
            self.authcode = self.login()
            if not self.authcode:
                logger.critical("Failed to authenticate with DerbyNet.")
                return False
        headers = {
            'Content-Type': 'application/json',
            'Cookie': self.authcode
        }
        # check if payload is a dict, if not, return false
        if not isinstance(payload, dict):
            logger.error("Payload is not a dictionary.")
            return False
        APIpayload = {
            "devices":[{
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
            ]
        }
        url = self.rooturl + 'device-status-api.php'
        try:
            response = requests.post(url, headers=headers, json=APIpayload, timeout=5)
            if response.status_code == 401:
                self.authcode = self.login()
                return self.send_device_status(payload)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to send device telemetry: {e}")
            return False
        logger.debug("Device telemetry successfully sent.")
        logger.debug("Device telemetry response: %s", response.text)
        return True
    
    @staticmethod
    def getWiFiPercentFromRSSI(rssi):
        """Converts RSSI value to percentage."""
        # check if rssi is an int, if not, return 0
        if not isinstance(rssi, int):
            logger.debug("RSSI value is not an integer.")
            return 0
        if rssi <= -100:
            return 0
        elif rssi >= -50:
            return 100
        else:
            return int((rssi + 100) * 2)