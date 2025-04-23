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

class DerbyNetClient:
    """Handles authentication and communication with the DerbyNet server."""

    def __init__(self, server_ip = None):
        if not server_ip:
            server_ip = "192.168.100.10"
        self.url = f"http://{server_ip}/derbynet/action.php"
        self.rooturl = f"http://{server_ip}/derbynet/"
        self.server_ip = server_ip
        self.authcode = None

    def login(self):
        """Logs in to the DerbyNet server and retrieves an auth cookie."""
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        payload = 'action=role.login&name=Timer&password='
        self.authcode = None
        attempt = 1
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
            exit(1)
            return None
        response_json = response.json()
        if response_json.get("outcome", {}).get("code") == "success":
            auth_code = response.headers.get('Set-Cookie', '').split(';')[0]
            logger.debug("Successfully logged in with authcode: %s", auth_code)
            self.authcode = auth_code
            return auth_code
        else:
            logger.error("Login failed: Invalid credentials or server error. API Response: %s", response.text)
            return None

    def send_timer_heartbeat(self): #sends an overall command that the timers are all still alive
        if not self.authcode:
            self.authcode = self.login()
            if not self.authcode:
                logger.critical("Failed to authenticate with DerbyNet.")
                return False
        payload = "message=HEARTBEAT&action=timer-message&confirmed=1&lane1=1&lane2=2&lane3=3&timerId1=L1&timerId2=L2&timerId3=L3"
        headers = {
            'Content-Type': "application/x-www-form-urlencoded",
            'Cookie': self.authcode
        }
        try:
            response = requests.post(self.url, headers=headers, data=payload, timeout=5)
            if response.status_code == 401: # unauthed, send for login
                self.authcode = self.login()
                self.send_timer_heartbeat()
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to send heartbeat message: {e}")
    
    def send_start(self):
        """Sends the start signal to the DerbyNet server."""
        if not self.authcode:
            self.authcode = self.login()
            if not self.authcode:
                logger.critical("Failed to authenticate with DerbyNet.")
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
                self.send_start()
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to send start message: {e}")
            return False

        response_xml = ET.fromstring(response.text)

        if response_xml.find('failure') is not None:
            logger.warning("Authentication failed, retrying login...")
            self.authcode = self.login()
            if self.authcode:
                return self.send_start()
            else:
                logger.critical("Failed to re-authenticate after failure.")
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
                self.send_finish(roundid, heatid, lane_times)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to send finish message: {e}")
            return False

        response_xml = ET.fromstring(response.text)

        if response_xml.find('failure') is not None:
            logger.warning("Authentication failed, retrying login...")
            self.authcode = self.login()
            if self.authcode:
                return self.send_finish(lane_times)
            else:
                logger.critical("Failed to re-authenticate after failure.")
                return False

        if response_xml.find('success') is not None:
            logger.info("Finish message successfully sent.")
            return True
        else:
            logger.error("Failed to confirm finish message reception.")
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
                self.get_race_status()
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to get race status: {e}")
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
                self.send_device_status(payload)
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
        if rssi <= -100:
            return 0
        elif rssi >= -50:
            return 100
        else:
            return int((rssi + 100) * 2)
