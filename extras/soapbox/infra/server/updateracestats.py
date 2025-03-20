'''
This will monitor for changes in the race statistics and send updates to the MQTT broker for different devices to consume and or monitor on
'''

from derbyapi import DerbyNetClient
import json
import paho.mqtt.client as mqtt # type: ignore
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "derbyraceupdate")
client.connect("192.168.100.10", 1883, 60)

api = DerbyNetClient()

api.login()
racestats = api.get_race_status()

led = None
if racestats['timer-state-string'] == 'STAGING':
    led = "Blue"
elif racestats['timer-state-string'] == 'RUNNING':
    led = "Green"
else:
    led = "Red"
racestats['led'] = led

print(racestats) #{'active': False, 'roundid': -1, 'heat': None, 'class': '', 'lanes': [], 'timer-state': 1, 'timer-state-string': 'NOT CONNECTED'}
client.publish("derbynet/race/state", json.dumps(racestats), qos=0, retain=True)
client.publish("derbynet/race/led", led, qos=0, retain=True)