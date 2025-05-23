'''
Library to manage the DerbyNet PCB v1 finish timer hardware

DerbyNet PCB V1 Hardware Pinout
--------------------------------------

NAME    GPIOPIN    HWPIN    FUNCTION
--------------------------------------
TOGGLE      24      18        INPUT
SDA         2       3         I2C (ADC)
SCL         3       5         I2C (ADC)
DIP1        6       31        INPUT
DIP2        13      33        INPUT
DIP3        19      35        INPUT
DIP4        26      37        INPUT
CLK         18      12        DISPLAY
DIO         23      16        DISPLAY
REDLED      8       24        OUTPUT
GREENLED    7       26        OUTPUT
BLUELED     1       28        OUTPUT

Version History:
- 0.5.0 - May 19, 2025 - Standardized version schema across all components
- 0.4.0 - May 10, 2025 - Added service discovery for MQTT broker
- 0.3.3 - April 30, 2025 - Fixed timing synchronization issues
- 0.3.0 - April 22, 2025 - Added remote syslogging and improved error handling
- 0.2.0 - April 15, 2025 - Added telemetry and toggle state persistence
- 0.1.0 - April 4, 2025 - Added MQTT communication protocols
- 0.0.1 - March 31, 2025 - Initial implementation
'''

# Constants and pin definitions
PCB_VERSION     = "0.5.0"  # Updated to standardized version
DEVICE_CLASS    = "Lane"

PIN_TOGGLE      = 24
PIN_SDA         = 2
PIN_SCL         = 3
PIN_DIP1        = 6
PIN_DIP2        = 13
PIN_DIP3        = 19
PIN_DIP4        = 26
PIN_CLK         = 18
PIN_DIO         = 23
PIN_RED         = 8
PIN_GREEN       = 7
PIN_BLUE        = 1
MCP3421_ADDR    = 0x68
 

from derbylogger import setup_logger, get_logger
logger = setup_logger(__name__) # setup logger with hwid
logger.debug("DerbyNet PCB Class Loaded")


# Imports
import time
import os
import uuid
import RPi.GPIO as GPIO # type: ignore
import tm1637 # type: ignore
import threading
import smbus2 # type: ignore
import subprocess
import psutil # type: ignore
 
# GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_RED, GPIO.OUT)
GPIO.setup(PIN_GREEN, GPIO.OUT)
GPIO.setup(PIN_BLUE, GPIO.OUT)

GPIO.output(PIN_RED, GPIO.HIGH)
GPIO.output(PIN_GREEN, GPIO.HIGH)
GPIO.output(PIN_BLUE, GPIO.HIGH)

GPIO.setup(PIN_TOGGLE, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_DIP1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_DIP2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_DIP3, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_DIP4, GPIO.IN, pull_up_down=GPIO.PUD_UP)

class derbyPCBv1:
    def __init__(self):
        # logging setup
        logger.debug("Starting DerbyNet PCB Class")
        # Initialize variables
        self.toggle_thread = None
        self.toggle_callback = None
        self.led = None
        self.pinny = "----"
        self.timestart = time.time()
        self.readyToRace = False
        logger.info(f"Initializing DerbyNet PCB v{PCB_VERSION}")
        # check if system hostname is DEFAULT then run sudo /opt/derbynet/setup.sh to set the hostname
        try:
            hostname = subprocess.check_output("hostname", shell=True).decode("utf-8").strip()
            if hostname == "DEFAULT":
                logger.warning("Hostname is DEFAULT. Running setup.sh to set hostname.")
                subprocess.check_output("sudo /opt/derbynet/setup.sh", shell=True)
        except Exception as e:
            logger.error(f"Error checking hostname: {e}")
        
        # Read HWID
        if os.path.exists("/boot/firmware/derbyid.txt"):
            with open("/boot/firmware/derbyid.txt", "r") as f:
                self.hwid = f.read().strip()
        else:
            self.hwid = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)])
        logger.debug(f"HWID: {self.hwid}")
        # Initialize 7-segment Display
        self.tm = tm1637.TM1637(clk=PIN_CLK, dio=PIN_DIO)
        self.tm.brightness(7)
        time.sleep(0.5)
        self.setLED("")
        logger.info("DerbyNet PCB Class Initialized")

    def begin_toggle_watch(self, callback):
        self.toggle_callback = callback
        self.toggle_thread = threading.Thread(target=self._toggle_watch)
        self.toggle_thread.start()
        logger.debug("Toggle Watch Started")

    def _toggle_watch(self):
        tog = not derbyPCBv1.getToggleState()
        self._updatePinny()
        while True:
            tchk = derbyPCBv1.getToggleState()
            if tog != tchk:
                tog = tchk
                logger.debug(f"Toggle Changed to: {tog}")
                if self.toggle_callback:
                    self.toggle_callback()
            if self.readyToRace != (tchk and self.led == "blue"):
                # change of state detected
                self.readyToRace = self.led == "green" or (tchk and self.led == "blue")
                logger.info(f"Ready to race: {self.readyToRace}")
                self._updatePinny()
            time.sleep(0.25)

    def end_toggle_watch(self):
        self.toggle_thread = None
        self.toggle_callback = None
        logger.warning("Toggle Watch Stopped")

    def setPinny(self, text, actNormal=True): # set the pinny display value. call this function to update the display from the main thread with mqtt
        # take first 4 characters of the string and pad with zeros
        text = text[:4].zfill(4)
        self.pinny = text 
        self._updatePinny(actNormal)

    def setLED(self, colour="", actNormal=True):
        if colour == "red":
            GPIO.output(PIN_RED, GPIO.HIGH)
            GPIO.output(PIN_GREEN, GPIO.LOW)
            GPIO.output(PIN_BLUE, GPIO.LOW)
        elif colour == "green":
            GPIO.output(PIN_RED, GPIO.LOW)
            GPIO.output(PIN_GREEN, GPIO.HIGH)
            GPIO.output(PIN_BLUE, GPIO.LOW)
        elif colour == "blue":
            GPIO.output(PIN_RED, GPIO.LOW)
            GPIO.output(PIN_GREEN, GPIO.LOW)
            GPIO.output(PIN_BLUE, GPIO.HIGH)
        elif colour == "white":
            GPIO.output(PIN_RED, GPIO.HIGH)
            GPIO.output(PIN_GREEN, GPIO.HIGH)
            GPIO.output(PIN_BLUE, GPIO.HIGH)
        elif colour == "purple":
            GPIO.output(PIN_RED, GPIO.HIGH)
            GPIO.output(PIN_GREEN, GPIO.LOW)
            GPIO.output(PIN_BLUE, GPIO.HIGH)
        elif colour == "yellow":
            GPIO.output(PIN_RED, GPIO.HIGH)
            GPIO.output(PIN_GREEN, GPIO.HIGH)
            GPIO.output(PIN_BLUE, GPIO.LOW)
        else:
            GPIO.output(PIN_RED, GPIO.LOW)
            GPIO.output(PIN_GREEN, GPIO.LOW)
            GPIO.output(PIN_BLUE, GPIO.LOW)
        if self.led != colour and actNormal:
            logger.info(f"LED Changed to {colour}")
        else:
            logger.debug(f"LED Set to {colour}")
        self.led = colour
        if actNormal:
            self._updatePinny()
        

    def _updatePinny(self, actNormal=True):
        if not actNormal:
            self.tm.brightness(7)
            self.tm.show(self.pinny)
            return
        if self.led == "blue" and self.readyToRace == False:
            self.tm.brightness(4)
            self.tm.show("flip")
            logger.warning("Not ready to race, showing FLIP")
        elif self.led == "red":
            if self.getBatteryPercent() < 20:
                self.tm.show("BATT")
                self.tm.brightness(3)
                logger.warning("Battery low " + str(self.getBatteryPercent()) + "%")
            else:
                self.tm.brightness(1)
                self.tm.show("stop")
        else: 
            self.tm.brightness(7)
            self.tm.show(self.pinny)

    def get_uptime(self):
        # get system uptime in seconds 
        try:
            with open('/proc/uptime', 'r') as f:
                uptime = f.readline().split()[0]
            return int(float(uptime))   
        # return uptime in seconds
        except Exception as e:
            logger.error(f"Error getting uptime: {e}")
            return 0

    
    def packageTelemetry(self): 
        '''
        Device status telemetry format V 0.5.0

        hostname
        hwid
        version
        uptime
        ip
        mac
        wifi_rssi
        battery_level
        cpu_temp
        memory_usage
        disk
        cpu_usage
        plus device-specific fields
        '''
        payload = {
            "hostname": DEVICE_CLASS + derbyPCBv1.get_Lane(),
            "mac": derbyPCBv1.get_mac(),
            "ip": derbyPCBv1.get_ip(),
            "cpu_temp": derbyPCBv1.get_cpu_temp(),
            "wifi_rssi": derbyPCBv1.get_wifi_rssi(),
            "uptime": self.get_uptime(),
            "memory_usage": derbyPCBv1.get_memory_usage(),
            "disk": derbyPCBv1.get_disk_usage(),
            "cpu_usage": derbyPCBv1.get_cpu_usage(),
            "battery_level": derbyPCBv1.getBatteryPercent(),
            "battery_raw": derbyPCBv1.getBatteryRaw(),
            "dip": derbyPCBv1.readDIP(),
            "toggle": derbyPCBv1.getToggleState(),
            "lane": derbyPCBv1.get_Lane(),
            "hwid": self.hwid,
            "time": int(time.time()),
            "led": self.led,
            "pinny": self.pinny,
            "readyToRace": self.readyToRace,
            "version": PCB_VERSION
        }
        return payload

    def close(self):
        GPIO.cleanup()
        self.end_toggle_watch()
        logger.warning("PCB class closed")
        return True
    
    def gethwid(self):
        return self.hwid
    
    def getIsReadyToRace(self):
        return self.readyToRace
    
    ####### STATIC METHODS #######    
    @staticmethod
    def getToggleState():
        return not GPIO.input(PIN_TOGGLE) # Returns not value because the toggle is active low
    
    @staticmethod
    def getBatteryRaw(): #returns raw adc value from battery single shot
        try:
            bus = smbus2.SMBus(1)  # Use I2C bus 1
            data = bus.read_i2c_block_data(MCP3421_ADDR, 0, 3)  # Read 3 bytes
            bus.close()
            raw_value = (data[0] << 8) | data[1]  # 16-bit ADC value
            if raw_value & 0x8000:  # Check if negative (ADC is signed)
                raw_value -= 65536
            return raw_value # Return the raw ADC value which is unitless
        except Exception as e:
            logger.error(f"Error reading MCP3421: {e}")
            return None

    @staticmethod
    def getBatteryPercent(): # converts raw battery reading to percentage  with an average sampling of 10 readings
        # convert raw value to percentage. 1400 is 0% and 1865 is 100% and is a linear relationship. take a sampling of 10 readings and average them
        battery_raw = []
        for i in range(10):
            battery_raw.append(derbyPCBv1.getBatteryRaw())
            time.sleep(0.05)
        battery_raw = sum(battery_raw)/len(battery_raw)
        battery_percent = (battery_raw - 1400)/(1865-1400)*100
        return int(battery_percent)
    
    @staticmethod
    def readDIP():
        d1 = str(int(not GPIO.input(PIN_DIP1)))
        d2 = str(int(not GPIO.input(PIN_DIP2)))
        d3 = str(int(not GPIO.input(PIN_DIP3)))
        d4 = str(int(not GPIO.input(PIN_DIP4)))
        return "".join([d1, d2, d3, d4])

    @staticmethod
    def get_Lane():#returns the lane number based on the dip switches
        dip = derbyPCBv1.readDIP()
        if dip == "1000":
            return "1"
        elif dip == "1001":
            return "2"
        elif dip == "1010":
            return "3"
        elif dip == "1011":
            return "4"
        else:
            return "0"

    @staticmethod
    def get_mac():
        macstr = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)])
        return macstr#.replace(":", "")
    
    @staticmethod
    def get_ip():
        cmd = "hostname -I | cut -d' ' -f1"
        return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()

    @staticmethod
    def get_hostname():
        cmd = "hostname"
        return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()

    @staticmethod
    def get_cpu_temp():
        try:
            temp = subprocess.check_output("vcgencmd measure_temp", shell=True).decode("utf-8")
            return float(temp.replace("temp=", "").replace("'C\n", ""))
        except:
            return None

    @staticmethod
    def get_wifi_rssi():
        try:
            rssi = subprocess.check_output("iwconfig wlan0 | grep -i --color=never 'Signal level'", shell=True).decode("utf-8")
            return int(rssi.split("=")[-1].split(" dBm")[0])
        except:
            return None

    @staticmethod
    def get_memory_usage():
        return psutil.virtual_memory().percent

    @staticmethod
    def get_cpu_usage():
        return psutil.cpu_percent()
    
    @staticmethod
    def get_pcb_version():
        return PCB_VERSION
    
    @staticmethod
    def get_disk_usage():
        disk = psutil.disk_usage('/')
        return disk.percent

    @staticmethod
    def update_pcb(): # calls /opt/derbynet/setup.sh to update the PCB and restart the service 
        logger.warning("Update requested. Calling /setup.sh")
        try:
            subprocess.check_output("sudo /setup.sh", shell=True)
            exit(0) # exit the script to restart the service
        except Exception as e:
            logger.error(f"Update failed: {e}")
            return False
        return True