# LED Sign Controller - ESP32 Firmware

MicroPython firmware for ESP32-based BetaBrite LED sign controllers.

## Architecture (v1.1.0)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        LED SIGN LIFECYCLE                                │
│                                                                         │
│  1. DISCOVERY (HTTP)           2. CONFIGURATION (HTTP)                  │
│  ┌─────────┐                   ┌─────────┐                              │
│  │  ESP32  │ ──GET /ledsign.php?mac=AA:BB:CC:DD:EE:FF──► │  DerbyNet │  │
│  │         │ ◄──── JSON: {zone: null, status: "identify"} │  Server  │  │
│  └─────────┘                   └─────────┘                              │
│       │                             │                                   │
│       │ Poll every 5s               │ Admin assigns zone via dashboard  │
│       ▼                             ▼                                   │
│  ┌─────────┐                   ┌─────────┐                              │
│  │  ESP32  │ ──GET poll.ledsign&mac=...──────────────────► │  DerbyNet │ │
│  │         │ ◄──── JSON: {zone: "starter", mqtt_topics: {...}} │ Server│ │
│  └─────────┘                   └─────────┘                              │
│       │                                                                 │
│       │ 3. CONTENT DELIVERY (MQTT) - only after zone assigned           │
│       ▼                                                                 │
│  ┌─────────┐    subscribe: derbynet/ledsign/starter/message            │
│  │  ESP32  │ ◄─────────────────────────────────────────── MQTT Broker  │
│  │         │    subscribe: derbynet/ledsign/broadcast                   │
│  └─────────┘                                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key Principle:** HTTP for discovery/config (self-identify like kiosks), MQTT only for real-time content delivery after zone assignment.

## Files

| File | Purpose |
|------|---------|
| `boot.py` | ESP32 startup configuration |
| `main.py` | Main application firmware |
| `config.py` | Hardcoded configuration settings |
| `betabrite.py` | BetaBrite Alpha Protocol library |
| `test_betabrite.py` | Hardware testing utilities |

## Hardware Requirements

- ESP32 DevKit V1
- MAX3232 TTL-to-RS232 converter module
- BetaBrite LED sign
- USB power supply (5V)

### Wiring

```
ESP32 DevKit          MAX3232 Module         BetaBrite Sign (RJ12)
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  GPIO17 TX ─┼──────┼─► T1IN      │      │             │
│             │      │   T1OUT ────┼──────┼─► Pin 4 (RX)│
│  GPIO16 RX ◄┼──────┼── R1OUT    │      │             │
│             │      │   R1IN  ◄───┼──────┼── Pin 5 (TX)│
│  GND ───────┼──────┼── GND ──────┼──────┼── Pin 1 (GND)│
│  5V/VIN ────┼──────┼── VCC      │      │             │
└─────────────┘      └─────────────┘      └─────────────┘
```

## Deployment

### 1. Install MicroPython on ESP32

```bash
# Download MicroPython firmware
# https://micropython.org/download/esp32/

# Erase flash
esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash

# Flash MicroPython
esptool.py --chip esp32 --port /dev/ttyUSB0 write_flash -z 0x1000 esp32-20230426-v1.20.0.bin
```

### 2. Upload Firmware Files

Using `ampy` (Adafruit MicroPython Tool):

```bash
# Install ampy
pip install adafruit-ampy

# Upload files
ampy --port /dev/ttyUSB0 put boot.py
ampy --port /dev/ttyUSB0 put config.py
ampy --port /dev/ttyUSB0 put betabrite.py
ampy --port /dev/ttyUSB0 put main.py
```

Or using `rshell`:

```bash
# Install rshell
pip install rshell

# Connect and copy files
rshell --port /dev/ttyUSB0
cp boot.py /pyboard/
cp config.py /pyboard/
cp betabrite.py /pyboard/
cp main.py /pyboard/
```

Or using Thonny IDE:
1. Open Thonny
2. Select MicroPython (ESP32) interpreter
3. Open each file and save to device

### 3. Verify Deployment

```bash
# Connect to REPL
screen /dev/ttyUSB0 115200

# Or using rshell
rshell --port /dev/ttyUSB0 repl
```

You should see:
```
==========================================
DerbyNet LED Sign Controller
Booting...
==========================================
[INFO] ... LEDSIGN: Watchdog initialized
[INFO] ... LEDSIGN: Device MAC: AA:BB:CC:DD:EE:FF
```

## Device Operation

### States

| State | LED Sign Display | Description |
|-------|------------------|-------------|
| UNCONFIGURED | `SETUP:AABBCCDD` | Polling HTTP, awaiting zone assignment |
| CONFIGURED | Zone content | Zone assigned, MQTT connected for content |
| OFFLINE | `CONNECTION LOST` | WiFi disconnected |

### HTTP-Based Discovery

When the device boots, it:
1. Connects to WiFi
2. Polls `GET /ledsign.php?mac=AA:BB:CC:DD:EE:FF&ip=192.168.x.x&version=1.1.0`
3. Receives JSON response with zone assignment (if any)
4. Once zone is assigned, connects to MQTT for content delivery

### Configuration via Admin Dashboard

Zone assignment is managed through the DerbyNet admin interface:
1. Open `http://derbynet-server/ledsign-dashboard.php`
2. Discovered signs appear automatically (via HTTP polling)
3. Select a zone from the dropdown for each sign
4. Device receives zone on next HTTP poll (within 5 seconds)

### HTTP Endpoints Used

```
# Registration (device → server)
GET /ledsign.php?mac=AA:BB:CC:DD:EE:FF&ip=192.168.100.150&version=1.1.0

# Response (unconfigured):
{
  "mac": "AA:BB:CC:DD:EE:FF",
  "zone": null,
  "status": "identify",
  "poll_interval": 5,
  "mqtt_broker": "192.168.100.10",
  "mqtt_port": 1883
}

# Response (configured):
{
  "mac": "AA:BB:CC:DD:EE:FF",
  "zone": "starter",
  "zone_display_name": "Start Line",
  "status": "configured",
  "mqtt_broker": "192.168.100.10",
  "mqtt_topics": {
    "content": "derbynet/ledsign/starter/message",
    "broadcast": "derbynet/ledsign/broadcast"
  }
}
```

### Send Test Message

```bash
# Send message to zone
mosquitto_pub -h 192.168.100.10 \
  -t "derbynet/ledsign/starter/message" \
  -m '{"message": "Hello World!", "display_config": {"mode": "hold", "color": "green"}}'

# Emergency broadcast
mosquitto_pub -h 192.168.100.10 \
  -t "derbynet/ledsign/broadcast" \
  -m '{"message": "EMERGENCY TEST", "display_config": {"mode": "flash", "color": "red"}}'
```

### OTA Update

```bash
# Trigger OTA update
mosquitto_pub -h 192.168.100.10 \
  -t "derbynet/ledsign/device/AABBCCDDEEFF/update" \
  -m "update"
```

## Testing

### Interactive Testing

```python
# Connect to REPL and import test module
>>> import test_betabrite

# Quick functions
>>> test_betabrite.msg("Hello!")
>>> test_betabrite.alert("Warning!")
>>> test_betabrite.scroll("Long scrolling message...")
>>> test_betabrite.clear()

# Run specific tests
>>> test_betabrite.test_basic()
>>> test_betabrite.test_colors()
>>> test_betabrite.test_derby_starter()

# Run all tests
>>> test_betabrite.run_all()
```

### Direct BetaBrite Testing

```python
>>> from machine import UART
>>> from betabrite import BetaBrite
>>> uart = UART(2, baudrate=9600, tx=17, rx=16)
>>> sign = BetaBrite(uart)
>>> sign.write_text("Test!", mode='hold', color='green')
>>> sign.write_priority("ALERT!", color='red')
>>> sign.cancel_priority()
```

## Troubleshooting

### WiFi Connection Issues

- Check `WIFI_SSID` and `WIFI_PASSWORD` in `config.py`
- Ensure ESP32 is within WiFi range
- Verify WiFi network is 2.4GHz (ESP32 doesn't support 5GHz)

### HTTP Registration Issues

- Verify DerbyNet server is running and accessible
- Check `DERBYNET_SERVER` and `DERBYNET_PORT` in `config.py`
- Test registration endpoint manually:
  ```bash
  curl "http://192.168.100.10/ledsign.php?mac=AA:BB:CC:DD:EE:FF&ip=192.168.1.100&version=1.1.0"
  ```
- Check DerbyNet PHP error logs if registration fails
- Device should show `SETUP:XXXXXXXX` when waiting for zone assignment

### Zone Not Appearing in Dashboard

- Ensure device is polling (check serial console for HTTP registration logs)
- Verify device is on same network as DerbyNet server
- Signs disappear from dashboard after 60 seconds without polling

### MQTT Connection Issues (Content Delivery)

- MQTT is only used after zone assignment - check HTTP registration first
- Verify MQTT broker is running: `systemctl status mosquitto`
- Test connectivity: `mosquitto_sub -h 192.168.100.10 -t '#' -v`

### BetaBrite Not Displaying

- Check wiring (TX/RX connections)
- Verify MAX3232 is powered (VCC connected)
- Test with simple command:
  ```python
  >>> uart.write(b'\x00\x00\x00\x00\x00\x01Z00A\x02A\x1b0bHello\x03\x04')
  ```

### Memory Issues

If you see `MemoryError`:
```python
>>> import gc
>>> gc.collect()
>>> gc.mem_free()
```

Consider removing `test_betabrite.py` from production devices.

## Version History

- **1.1.0** - HTTP-based discovery and configuration (mirrors kiosk pattern)
  - Device registration via HTTP polling (`/ledsign.php`)
  - Zone assignment via DerbyNet admin dashboard
  - MQTT now only used for content delivery after zone assignment
  - Simplified architecture: HTTP for config, MQTT for content
- **1.0.0** - Initial release with full MQTT integration and zone support
