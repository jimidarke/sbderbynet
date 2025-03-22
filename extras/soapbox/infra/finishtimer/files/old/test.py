import time
from derbynetPCBv1 import derbyPCBv1
def toggle_callback():
    print("Toggle Pressed")
def main():
    derby = derbyPCBv1()
    derby.begin_toggle_watch(toggle_callback)
    derby.setLED("red")
    derby.setPinnyDisplay("1234")
    print(derby.readDIP())
    derby.end_toggle_watch()
    while True:
        time.sleep(1)
if __name__ == "__main__":
    main()
  
