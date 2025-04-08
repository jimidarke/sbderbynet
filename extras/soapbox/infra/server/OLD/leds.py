''' 
Manages the Race LED light by subscribing to the MQTT topic

    RED     STOPPED
    BLUE    STAGING
    GREEN   RACING

'''


import time
import paho.mqtt.client as mqtt # type: ignore
import RPi.GPIO as GPIO # type: ignore


PIN_RED = 17
PIN_GREEN = 27
PIN_BLUE = 22
PIN_1D = 10
PIN_1C = 9
PIN_2D = 11
PIN_2C = 0
PIN_3D = 5
PIN_3C = 6
PIN_4D = 13
PIN_4C = 19

pulse = False

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_RED, GPIO.OUT)
GPIO.setup(PIN_GREEN, GPIO.OUT)
GPIO.setup(PIN_BLUE, GPIO.OUT)

def led_off():
    '''
    Turns off all LEDs.
    '''
    GPIO.output(PIN_RED, GPIO.LOW)
    GPIO.output(PIN_GREEN, GPIO.LOW)
    GPIO.output(PIN_BLUE, GPIO.LOW)

def led_blue():
    '''
    Turns on the blue LED.
    '''
    GPIO.output(PIN_RED, GPIO.LOW)
    GPIO.output(PIN_GREEN, GPIO.LOW)
    GPIO.output(PIN_BLUE, GPIO.HIGH)

def led_green():
    '''
    Turns on the green LED.
    '''
    GPIO.output(PIN_RED, GPIO.LOW)
    GPIO.output(PIN_GREEN, GPIO.HIGH)
    GPIO.output(PIN_BLUE, GPIO.LOW)

def led_red():
    '''
    Turns on the red LED.
    '''
    GPIO.output(PIN_RED, GPIO.HIGH)
    GPIO.output(PIN_GREEN, GPIO.LOW)
    GPIO.output(PIN_BLUE, GPIO.LOW)

def led_pulse(colour = "Red"): 
    global pulse
    pulse = "Red"
    if colour == "Red":
        pulse = "Red"
    elif colour == "Green":
        pulse = "Green"
    elif colour == "Blue":
        pulse = "Blue"
    elif colour == "All":
        pulse = "All"
    else:
        print(f"Invalid LED color: {colour}")
        return
    
def message_received(client, userdata, message):
    global pulse
    colour = message.payload.decode("utf-8")
    print(f"LED colour: {colour}")
    if colour == "Blue":
        pulse = False
        led_off()
        led_blue()
    elif colour == "Green":
        pulse = False
        led_off()
        led_green()
    elif colour == "Red":
        pulse = False
        led_off()
        led_red()
    elif colour == "PulseRed":
        led_pulse("Red")
    elif colour == "PulseGreen":
        led_pulse("Green")
    elif colour == "PulseBlue":
        led_pulse("Blue")
    elif colour == "PulseAll":
        led_pulse("All")
    elif colour == "Off":
        pulse = False
        led_off()
    else:
        print(f"Invalid LED colour: {colour}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "derbyleds")
client.connect("192.168.100.10", 1883, 60)
client.subscribe("derbynet/race/led") # Blue, Green, Red, Off, etc.
client.on_message = message_received
client.loop_start()


def main():
    global pulse
    while True:
        #time.sleep(0.5)
        while pulse:
            for i in range(0, 10):
                if pulse == "Red":
                    led_red()
                elif pulse == "Green":
                    led_green()
                elif pulse == "Blue":
                    led_blue()
                elif pulse == "All":
                    led_red()
                    time.sleep(0.1)
                    led_green()
                    time.sleep(0.1)
                    led_blue()
                    time.sleep(0.1)
                time.sleep(0.1)
                led_off()
                time.sleep(0.1)
        if not pulse:
            time.sleep(1)

    
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        pass
    finally:
        GPIO.cleanup()
        client.loop_stop()