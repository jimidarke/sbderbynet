# Start Timer

ESP32-based race-start signal detection. Detects gate opening via a switch and broadcasts a timestamped GO event over MQTT so all race components synchronise timing.

Lives at `extras/soapbox/infra/starttimer/`. MicroPython on ESP32.

If this hardware is unavailable, the coordinator page provides a manual start button that publishes to `derbynet/device/manualstart/state`.

---

## Hardware

- ESP32 microcontroller (MicroPython)
- Start switch on **GPIO 33**
- DHT22 temp/humidity sensor on **GPIO 32**
- Built-in LED on **GPIO 2**
- Battery-operated (portable start-line placement)

---

## MQTT topics

The start timer is the one device that doesn't follow the standard `{hwid}` topic pattern — its `hwid` is hardcoded to `starttimer`. See [Hardware IDs](../architecture/hardware-ids.md) for the full story.

- `derbynet/device/starttimer/status` — online/offline
- `derbynet/device/starttimer/state` — start signal (GO / STOP)
- `derbynet/device/starttimer/telemetry` — device telemetry
- `derbynet/device/starttimer/update` — OTA update trigger

### Telemetry fields

WiFi RSSI, IP and MAC address, temperature and humidity (DHT22), uptime, firmware version, current start-signal state.

---

## Configuration

| Setting | Default |
|---|---|
| WiFi SSID | `DerbyNet` |
| MQTT broker | `192.168.100.10` |
| NTP server | `192.168.100.10` |
| OTA URL | `http://192.168.100.10/starttimer/main.py` |

WiFi credentials are baked into firmware at flash time — there's no runtime configuration. Update before flashing.

---

## Flashing

```bash
# Erase
esptool.py --port /dev/ttyUSB0 erase_flash

# Install MicroPython
esptool.py --port /dev/ttyUSB0 --baud 460800 \
           write_flash --flash_size=detect 0 esp32-20220618-v1.19.1.bin

# Upload code
ampy --port /dev/ttyUSB0 put main.py
ampy --port /dev/ttyUSB0 put boot.py
```

---

## OTA updates

```bash
# Stage new firmware on the web server
./copytoweb.sh

# Trigger update
mosquitto_pub -h 192.168.100.10 \
              -t derbynet/device/starttimer/update -m "update"
```

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Won't connect to WiFi | wrong creds in firmware, out of range, weak bridge link |
| Start events not detected | physical switch wiring (GPIO 33), broker reachability |
| OTA update failing | HTTP server not serving the file, ESP32 low on memory |

See also: [Network](../architecture/network.md), [Race Server](race-server.md).
