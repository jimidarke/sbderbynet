'''
    Communicates with the DerbyNet API to manage logins, exceptions, and functions like start and finish

from derbyapi import DerbyNetClient
SERVERIP = "192.168.100.10"

api = DerbyNetClient(SERVERIP)


'''

#import requests # type: ignore
from pip._vendor import requests
import logging
import xml.etree.ElementTree as ET

class DerbyNetClient:
    """Handles authentication and communication with the DerbyNet server."""

    def __init__(self, server_ip = None):
        if not server_ip:
            server_ip = "192.168.100.10"
        self.url = f"http://{server_ip}/derbynet/action.php"
        self.authcode = None

    def login(self):
        """Logs in to the DerbyNet server and retrieves an auth cookie."""
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        payload = 'action=role.login&name=Timer&password='

        try: 
            response = requests.post(self.url, headers=headers, data=payload, timeout=5)
            response.raise_for_status()
        except requests.RequestException as e:
            logging.error(f"Login failed: {e}")
            return None
        response_json = response.json()
        if response_json.get("outcome", {}).get("code") == "success":
            auth_code = response.headers.get('Set-Cookie', '').split(';')[0]
            logging.info("Successfully logged in with authcode: %s", auth_code)
            self.authcode = auth_code
            return auth_code
        else:
            logging.error("Login failed: Invalid credentials or server error")
            return None

    def send_timer_heartbeat(self): #sends an overall command that the timers are all still alive
        if not self.authcode:
            self.authcode = self.login()
            if not self.authcode:
                logging.critical("Failed to authenticate with DerbyNet.")
                return False
        payload = "message=HEARTBEAT&action=timer-message"
        headers = {
            'Content-Type': "application/x-www-form-urlencoded",
            'Cookie': self.authcode
        }
        try:
            response = requests.post(self.url, headers=headers, data=payload, timeout=5)
            response.raise_for_status()
        except requests.RequestException as e:
            logging.error(f"Failed to send heartbeat message: {e}")
    
    def send_start(self):
        """Sends the start signal to the DerbyNet server."""
        if not self.authcode:
            self.authcode = self.login()
            if not self.authcode:
                logging.critical("Failed to authenticate with DerbyNet.")
                return False

        payload = "message=STARTED&action=timer-message"
        headers = {
            'Content-Type': "application/x-www-form-urlencoded",
            'Cookie': self.authcode
        }

        try:
            response = requests.post(self.url, headers=headers, data=payload, timeout=5)
            response.raise_for_status()
        except requests.RequestException as e:
            logging.error(f"Failed to send start message: {e}")
            return False

        response_xml = ET.fromstring(response.text)

        if response_xml.find('failure') is not None:
            logging.warning("Authentication failed, retrying login...")
            self.authcode = self.login()
            if self.authcode:
                return self.send_start()
            else:
                logging.critical("Failed to re-authenticate after failure.")
                return False

        if response_xml.find('success') is not None:
            logging.info("Start message successfully sent.")
            return True
        else:
            logging.error("Failed to confirm start message reception.")
            return False

    def send_finish(self, roundid, heatid, lane_times):
        """Sends the finish signal to the DerbyNet server."""
        if not self.authcode:
            self.authcode = self.login()
            if not self.authcode:
                logging.critical("Failed to authenticate with DerbyNet.")
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
            response.raise_for_status()
        except requests.RequestException as e:
            logging.error(f"Failed to send finish message: {e}")
            return False

        response_xml = ET.fromstring(response.text)

        if response_xml.find('failure') is not None:
            logging.warning("Authentication failed, retrying login...")
            self.authcode = self.login()
            if self.authcode:
                return self.send_finish(lane_times)
            else:
                logging.critical("Failed to re-authenticate after failure.")
                return False

        if response_xml.find('success') is not None:
            logging.info("Finish message successfully sent.")
            return True
        else:
            logging.error("Failed to confirm finish message reception.")
            return False
    
    def get_race_status(self):
        # gets the race status and updates mqtt 
        if not self.authcode:
            self.authcode = self.login()
            if not self.authcode:
                logging.critical("Failed to authenticate with DerbyNet.")
                return False
        headers = {
            'Accept': 'application/json',
            'Cookie': self.authcode
        }
        payload = ''
        url = self.url + '?query=poll.coordinator'
        try:
            response = requests.get(url, headers=headers, data=payload, timeout=5)
            response.raise_for_status()
        except requests.RequestException as e:
            logging.error(f"Failed to get race status: {e}")
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