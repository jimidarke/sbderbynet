''' 
This script will be used to interact with the GPIO pins on the Raspberry Pi to control arrival of carts over the finish line.
There are four lanes, each with a corresponding GPIO pin. When a cart crosses the finish line, the corresponding GPIO pin will be manually triggered to record the time of finish. 
The status of the race is monitored through a REST API and the time of finish is sent to the API to be recorded.
'''

APIURL = 'http://derbynetpi/derbynet/action.php'
import random
import time
import requests
import xml.etree.ElementTree as ET



def api_login():
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    payload = 'action=role.login&name=Timer&password='
    response = requests.post(APIURL, headers=headers, data=payload)
    response_json = response.json()
    if "outcome" in response_json and "code" in response_json["outcome"] and response_json["outcome"]["code"] == "success":
        #get cookie
        authcode = response.headers['Set-Cookie'].split(';')[0]
        print("Login successful")
        return authcode
    else:
        print("Login failed")
        return None
    
def api_heartbeat(authcode):
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': authcode
    }
    payload = 'action=timer-message&message=HEARTBEAT'
    response = requests.post(APIURL, headers=headers, data=payload) # XML
    ## parse response xml 
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
    <action-response action="timer-message" message="HEARTBEAT">
        <success/>
        <heat-ready lane-mask="7" class="Age 6-8" round="1" roundid="1" heat="1" lanes="3"/>
        <remote-log send='false'/>
    </action-response>
    '''
    # print(response.text)
    # print(xml)
    #root = ET.fromstring(xml)
    root = ET.fromstring(response.text) 
    issuccess = root.find('success')
    out = {}
    if issuccess is not None:
        out['heartbeat'] = True
        if root.find('heat-ready') is not None:
            heat = root.find('heat-ready')
            current_race = {
                "class":  heat.get('class'),
                "round":heat.get('round'),
                "roundid": heat.get('roundid'),
                "heat": heat.get('heat'),
                "lanes": heat.get('lanes')
            }
            out['current_race'] = current_race
        return out # {'class': 'Age 6-8', 'round': '1', 'roundid': '1', 'heat': '1', 'lanes': '3'}
    return None

def start_racing_now(): # green light GO
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Cookie': authcode
    }
    payload = 'message=STARTED&action=timer-message'
    response = requests.post(APIURL, headers=headers, data=payload)
    print(response.text)

def finish_racing_now(finish_payload): # All carts have finished or timed out for DNF
    finish_payload_sample = {
        '1': 10.1,
        '2': 10.2,
        '3': 10.0,
        '4': 10.4
    }
    sorted_lanes_by_time = []
    sorted_lanes_by_time = sorted(finish_payload.items(), key=lambda x: x[1])
    sorted_lanes_by_time = [lane for lane, time in sorted_lanes_by_time]
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Cookie': authcode
    }
    race_stats = get_race_stats()
    payload = f"message=FINISHED&action=timer-message&roundid={race_stats['Round']}&heat={race_stats['Heat']}&lane1={finish_payload['1']}&lane2={finish_payload['2']}&lane3={finish_payload['3']}&lane4={finish_payload['4']}&place1={sorted_lanes_by_time[0]}&place2={sorted_lanes_by_time[1]}&place3={sorted_lanes_by_time[2]}&place4={sorted_lanes_by_time[3]}"
    response = requests.post(APIURL, headers=headers, data=payload)
    print(response.text)
    


def get_race_stats(): # ajax call to get coordinator details. unauthed. 
    url = APIURL + "?query=poll.coordinator"
    response = requests.get(url)
    response = response.json()
    race_stats = {}
    if "current-heat" in response:
        race_stats["Active"] = response["current-heat"]["now_racing"]
        race_stats["Class"] = response["current-heat"]["class"]
        race_stats["Round"] = response["current-heat"]["round"]
        race_stats["Heat"] = response["current-heat"]["heat"]
    if "racers" in response:
        racer_list = []
        for racer in response["racers"]:
            racer_list.append({
                "lane": racer["lane"],
                "carnumber": racer["carnumber"],
                "racerid": racer["racerid"],
                "name": racer["name"]
            })
        race_stats["Racers"] = racer_list
    if "timer-state" in response:
        race_stats['Timer-Messages'] = response["timer-state"]["message"]
        race_stats['Lanes'] = response["timer-state"]["lanes"]
        if response["timer-state"]["state"] ==  4:
            race_stats["RaceRunning"] = True
        else:
            race_stats["RaceRunning"] = False
    print(race_stats)
    return race_stats


if __name__ == '__main__':
    authcode = api_login()
    api_heartbeat(authcode)
    race_stats = get_race_stats()
    start_racing_now()
    time.sleep(5)
    finish_payload_sample = {
        '1': random.randint(40,60),
        '2': random.randint(40,60),
        '3': random.randint(40,60),
        '4': 61
    }
    finish_racing_now(finish_payload_sample)
    exit()
    