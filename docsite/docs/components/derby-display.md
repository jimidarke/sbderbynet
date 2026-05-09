# Derby Display

Manages kiosk display screens on Raspberry Pis. Launches Chromium in kiosk mode pointing at DerbyNet kiosk pages, reports health telemetry over MQTT, handles display configuration.

Lives at `extras/soapbox/infra/derbydisplay/`. Python 3 + Chromium. Runs as `derbydisplay.service`.

---

## Hardware

- Raspberry Pi 3B+ or newer (Pi 4 recommended)
- HDMI monitor or TV
- 5 V 3 A power supply (minimum for Pi 4)
- Wired network preferred over WiFi

Tested with 1080p displays. 4K TVs downscale automatically; standard monitors work out-of-the-box.

---

## Configuration

- MQTT broker: `192.168.100.10:1883`
- Telemetry interval: 5 s
- `hwid`: from `/boot/firmware/derbyid.txt`, falling back to MAC-derived

---

## MQTT topics

**Publishes**:

- `derbynet/device/{hwid}/state` — current display state
- `derbynet/device/{hwid}/telemetry` — system telemetry
- `derbynet/device/{hwid}/status` — online/offline

**Subscribes**:

- `derbynet/device/{hwid}/update` — firmware update commands

---

## Files

| File | Role |
|---|---|
| `derbydisplay.py` | main service: MQTT, telemetry, display config |
| `derbydisplay.service` | systemd unit |
| `kiosk.sh` | Chromium kiosk-mode launcher |
| `setup.sh` | install script for new devices |
| `force-1080p.sh` | utility to force 1080p on uncooperative TVs |
| `status.html`, `loading.png`, `error.png` | offline / startup screens |

---

## Install / run

```bash
sudo ./setup.sh                              # one-time install
sudo systemctl {start,stop,status} derbydisplay
sudo journalctl -u derbydisplay -f
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Loading screen forever | check network, broker, `journalctl -u derbydisplay` |
| Error image | check system errors, `hwid` config, display registration in race manager |
| Display freezes / blanks | restart service; check overheating, power, browser process |
| TV shows display in a corner (not fullscreen) | run `sudo /opt/derbydisplay/force-1080p.sh`; disable TV's overscan/zoom/screen-fit; try a different HDMI port; check `/boot/firmware/config.txt` |

---

## Related

- [Web App](web-app.md) — serves the kiosk pages
- [DerbyPi](derbypi.md) — Ansible deploys this onto Pis automatically
