# LED Signs

ESP32 controllers driving BetaBrite Alpha-Protocol LED signs over RS-232 serial. All units run identical firmware; behaviour is determined by **zone assignment** received over MQTT after HTTP discovery.

Lives at `extras/ledsign/`. MicroPython on ESP32. 176-test suite under `extras/ledsign/tests/`.

---

## Hardware

- ESP32 DevKit V1
- MAX3232 TTL-to-RS232 converter
- BetaBrite LED sign (Alpha Protocol)
- USB 5 V power

### Wiring

```
ESP32 DevKit          MAX3232 Module        BetaBrite Sign (RJ12)
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  GPIO17 TX ─┼──────┼─► T1IN      │      │             │
│             │      │   T1OUT ────┼──────┼─► Pin 4 (RX)│
│  GPIO16 RX ◄┼──────┼── R1OUT    │      │             │
│             │      │   R1IN  ◄───┼──────┼── Pin 5 (TX)│
│  GND ───────┼──────┼── GND ──────┼──────┼── Pin 1 (GND)│
│  5V/VIN ────┼──────┼── VCC      │      │             │
└─────────────┘      └─────────────┘      └─────────────┘
```

UART config: `UART(2, baudrate=9600, tx=17, rx=16)`. MAX3232 power is critical — silent failures usually trace to it being unpowered.

---

## Lifecycle

```
1. DISCOVERY (HTTP)
   ESP32 boots → connects WiFi → polls /ledsign.php?mac=...&ip=...&version=1.1.0
   Server responds: { zone: null, status: "identify" }
   Sign displays: SETUP:AABBCCDD

2. CONFIGURATION (HTTP)
   Admin assigns a zone in /ledsign-dashboard.php
   Next poll returns: { zone: "starter", mqtt_topics: { content, broadcast } }

3. CONTENT DELIVERY (MQTT)
   Sign subscribes to derbynet/ledsign/{zone}/message
   and derbynet/ledsign/broadcast (priority override)
```

**HTTP for discovery and config; MQTT only for runtime content.** Same pattern as the kiosk displays.

### Device states

| State | Display | Meaning |
|---|---|---|
| `UNCONFIGURED` | `SETUP:AABBCCDD` | polling, awaiting zone assignment |
| `CONFIGURED` | zone content | zone assigned, MQTT live |
| `OFFLINE` | `CONNECTION LOST` | WiFi disconnected |

---

## HTTP endpoints

```
GET /ledsign.php?mac=AA:BB:CC:DD:EE:FF&ip=192.168.100.150&version=1.1.0
```

Unconfigured response:

```json
{
  "mac": "AA:BB:CC:DD:EE:FF",
  "zone": null,
  "status": "identify",
  "poll_interval": 5,
  "mqtt_broker": "192.168.100.10",
  "mqtt_port": 1883
}
```

Configured response:

```json
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

---

## MQTT

```
derbynet/ledsign/{zone}/message            # zone-specific content
derbynet/ledsign/broadcast                 # priority override (emergency)
derbynet/ledsign/device/{mac}/update       # OTA trigger
```

Send a test message:

```bash
mosquitto_pub -h 192.168.100.10 \
  -t "derbynet/ledsign/starter/message" \
  -m '{"message":"Hello!","display_config":{"mode":"hold","color":"green"}}'

# Emergency broadcast
mosquitto_pub -h 192.168.100.10 \
  -t "derbynet/ledsign/broadcast" \
  -m '{"message":"EMERGENCY","display_config":{"mode":"flash","color":"red"}}'
```

---

## What each sign shows during a race

| Race state | Starter sign | Usher (per-lane) signs |
|---|---|---|
| STOPPED | `READY` (amber) | blank |
| STAGING | `SET` (amber) | `#0042` (green, current pinny) |
| RACING | `GO!` (green, flashing) | `#0042` (green) |
| FINISHED | `FINISHED` (red) | `DONE` (amber, 5 s) |

Race-server publishes are wired through `extras/soapbox/infra/server/ledsign_content.py`.

---

## Files

| File | Role |
|---|---|
| `src/main.py` | main app: HTTP poll, MQTT subscription, output to BetaBrite |
| `src/betabrite.py` | Alpha-Protocol library (modes, colours, effects) |
| `src/config.py` | hardcoded WiFi / broker / endpoints |
| `src/boot.py` | startup, WiFi |
| `src/test_betabrite.py` | interactive test helpers |

See [BetaBrite Protocol](../reference/betabrite-protocol.md) for protocol/mode details and [Firmware Audit](../development/ledsign-firmware-audit.md) for known issues.

---

## Flashing

```bash
esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash
esptool.py --chip esp32 --port /dev/ttyUSB0 write_flash -z 0x1000 \
           esp32-20230426-v1.20.0.bin

# upload firmware
ampy --port /dev/ttyUSB0 put boot.py
ampy --port /dev/ttyUSB0 put config.py
ampy --port /dev/ttyUSB0 put betabrite.py
ampy --port /dev/ttyUSB0 put main.py
```

REPL inspection:

```python
>>> import test_betabrite
>>> test_betabrite.msg("Hello!")
>>> test_betabrite.run_all()
```

---

## Troubleshooting

| Symptom | Check |
|---|---|
| Sign stuck on `SETUP:...` | DerbyNet server reachable from sign; `curl http://192.168.100.10/ledsign.php?mac=...&ip=...&version=1.1.0` |
| Won't connect to WiFi | `WIFI_SSID`/`WIFI_PASSWORD` in `config.py`; range; **2.4 GHz only** (ESP32 doesn't do 5 GHz) |
| Disappears from dashboard | not polling — check serial console; signs disappear after 60 s without polling |
| MQTT silent after assignment | broker running; HTTP registration first; `mosquitto_sub -h 192.168.100.10 -t '#' -v` |
| BetaBrite blank | wiring; MAX3232 powered; UART params (9600 baud, GPIO 17/16) |
| `MemoryError` | `gc.collect()`; remove `test_betabrite.py` from production devices |

---

## Version

- **1.1.0** — HTTP-based discovery and configuration (mirrors kiosk pattern). Zone assignment via `/ledsign-dashboard.php`. MQTT used only for content delivery.
- **1.0.0** — initial release with full MQTT integration and zone support.
