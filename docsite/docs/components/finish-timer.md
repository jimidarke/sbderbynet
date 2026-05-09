# Finish Timer

Lane finish detection on a Raspberry Pi (Pi Zero 2W on race day). Toggle switch flips when the car crosses the finish line; the Pi publishes a timestamped event over MQTT, the race server records it.

One per lane. All three run identical firmware; lane is set by DIP switches on the board.

Lives at `extras/soapbox/infra/finishtimer/`. Python 3 + RPi.GPIO. Runs as `finishtimer.service`.

---

## Hardware

DerbyNet PCB v1 with:

- Raspberry Pi (Zero 2W in production)
- Physical toggle switch on the finish line
- RGB LED for status feedback
- 4-digit 7-segment display
- DIP switches for lane assignment
- I2C ADC for battery monitoring

### PCB v1 pinout

| Name | GPIO | HW pin | Function |
|---|---|---|---|
| TOGGLE | 24 | 18 | INPUT |
| SDA | 2 | 3 | I2C (ADC) |
| SCL | 3 | 5 | I2C (ADC) |
| DIP1 | 6 | 31 | INPUT |
| DIP2 | 13 | 33 | INPUT |
| DIP3 | 19 | 35 | INPUT |
| DIP4 | 26 | 37 | INPUT |
| CLK | 18 | 12 | DISPLAY |
| DIO | 23 | 16 | DISPLAY |
| REDLED | 8 | 24 | OUTPUT |
| GREENLED | 7 | 26 | OUTPUT |
| BLUELED | 1 | 28 | OUTPUT |

### DIP-switch lane configuration

| Lane | DIPs |
|---|---|
| 1 | `1000` |
| 2 | `1001` |
| 3 | `1010` |
| 4 | `1011` |

---

## MQTT topics

**Publishes**:

- `derbynet/device/{hwid}/state` — toggle state + timestamp (QoS 2)
- `derbynet/device/{hwid}/telemetry` — telemetry (QoS 1)
- `derbynet/device/{hwid}/status` — online/offline (QoS 1, retained)

**Subscribes**:

- `derbynet/lane/{lane}/led` — LED colour control
- `derbynet/lane/{lane}/pinny` — numeric display control
- `derbynet/device/{hwid}/update` — firmware update trigger

`hwid` is MAC-derived or read from `/boot/firmware/derbyid.txt`. See [Hardware IDs](../architecture/hardware-ids.md).

---

## LED status

| Colour | Meaning |
|---|---|
| Red | race stopped / not ready |
| Blue | ready (toggle must be up) |
| Green | race in progress |
| Purple | this lane has finished |
| Yellow | connection / hardware error |
| White | initial power-on / diagnostic |

## Display codes

| Code | Meaning |
|---|---|
| `LAN1`–`LAN4` | lane number configuration |
| `----` | standby / idle |
| `FLIP` | toggle needs to be in the up position |
| `COnn` | attempting to connect |
| `BATT` | low battery warning |
| `Err0`–`Err9` | error conditions |
| `rt##` | reconnection attempt number |

---

## Race sequence

1. Server sends blue LED command when race is staged.
2. Timer shows `FLIP` if toggle isn't in ready position.
3. When race starts, server sends green LED.
4. Timer detects toggle state change when car crosses finish line.
5. Timer publishes the event with a precise timestamp.
6. Server calculates race times and updates displays.
7. LED changes to purple when the lane has finished.

---

## Network resilience

- Exponential backoff reconnection (5 s initial, max 5 min).
- Local message queue during outages.
- Heartbeat every 2 s including battery + RSSI.
- Visual feedback during reconnection attempts (display + LED).

---

## Deployment

```bash
./sync.sh           # push files to the Pi
./setup.sh          # on the Pi: install service
sudo systemctl start finishtimer
```

Ansible automation: `extras/soapbox/infra/finishtimer/ansible/`.

Logs:

- Local: `/var/log/derbynet.log`
- Central syslog: `192.168.100.10:514`

---

## Troubleshooting

| Indicator | Meaning |
|---|---|
| Yellow LED | connection or hardware error |
| Flashing LED | reconnection in progress |
| `Err0` | unhandled exception |
| `Err1` | main loop error |
| `Err4` / `Err5` | MQTT connection error |
| `BATT` on display | battery < 20 % |

See also: [Race State Engine](../architecture/race-state-engine.md), [MQTT API](../reference/mqtt-api.md).
