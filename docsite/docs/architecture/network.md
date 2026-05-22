# Network Architecture

Race-day operations run on a deliberately isolated subnet. No internet required, and nothing on the venue's house WiFi can reach race infrastructure. The cloud twin lives entirely outside this subnet and only ever receives a one-way push from the Pi.

![Network topology — TODO screenshot](../images/placeholder-network-topology.png)

---

## The race subnet — `192.168.100.0/24`

| Address | Device | Role |
|---|---|---|
| `192.168.100.1` | router/AP | DHCP, gateway (gateway is venue-dependent / often unused) |
| `192.168.100.10` | **DerbyPi** (race server) | PHP, SQLite, Mosquitto broker, race-server daemon, NTP source |
| `192.168.100.21` | finishtimer Lane 1 | Pi Zero W V1.1 |
| `192.168.100.22` | finishtimer Lane 2 | Pi Zero W V1.1 |
| `192.168.100.23` | finishtimer Lane 3 | Pi Zero W V1.1 |
| DHCP range | start timer (ESP32), kiosk displays, LED signs, HLS feed box, operator laptops/tablets | |

The MQTT broker on `.10:1883` is the rendezvous for everything device-side. Devices retry with exponential backoff on disconnect and queue messages locally during outages.

---

## The wifi extender bridge

There's enough physical distance between the start line and the finish line at most venues that a single AP doesn't reliably cover both ends of the track. Race-day uses a **WiFi extender bridge** between the race-server enclosure (typically near the start) and the finish-line enclosure (where the finish timers, finish-line LED signs, and a display kiosk live).

### What it is

A pair of point-to-point bridge radios (or an extender + AP) that carries the `192.168.100.0/24` subnet from the start-side switch to a switch at the finish line. Finish timers cable into the finish-side switch; everything looks like one flat L2 network from above.

### Why it matters

- Throughput on the bridge is the bottleneck: MQTT telemetry plus HLS feed plus OTA firmware pulls all share it.
- Link quality varies with bridge placement, alignment, weather, and crowd density. Bad placement → MQTT disconnects → timers go yellow → race halts.
- Battery on portable enclosures matters: a flapping link drains both radios faster.

### Practical guidance

- Site-survey the bridge during setup. Don't assume yesterday's placement still works today.
- Keep both radios in line of sight if at all possible.
- Run a `ping -i 0.5 192.168.100.21` from the race server during warm-up. Sustained latency >50ms or any packet loss = move the radio.

!!! todo "SNMP polling — followup work"
    The bridge radios expose RSSI, link rate, and retransmit counts via SNMP. We should poll these on the race server, log to a timeseries (sqlite or rrd), and surface a small panel on the coordinator/dashboard so the placement team can optimize during warm-up rather than discovering signal issues mid-race. Open work item: implement an SNMP poller (Python, on `192.168.100.10`), schema on disk, and a coordinator widget.

---

## Out-of-band: the cloud

The cloud twin (`uisp.darketech.ca`) is **separate**:

- Not on the race subnet.
- Pi pushes a SQLite snapshot to it via a cron job (`cloud-sync.sh`) over the venue's external internet uplink.
- Used for dress rehearsal, public results, and the Flutter app. Never used to control race-day infrastructure.

If the venue uplink is dead, the cloud falls behind — race-day is unaffected.

See [VPS Procedures](../operations/vps-procedures.md) and [Production Access](../operations/production-access.md).

---

## Failure modes worth knowing

| Symptom | Likely cause |
|---|---|
| All three finish timers go yellow at once | bridge link dropped, or `192.168.100.10` rebooted |
| One finish timer flaps | radio interference or finish-side switch port |
| Start timer never connects | ESP32 WiFi credentials baked into firmware are wrong, or out of range |
| LED signs stop responding to broadcasts | broker not running, or MQTT auth misconfigured |
| Cloud twin shows old data | `cloud-sync.sh` cron failed; check Pi-side logs (see [Logging](../operations/logging.md)) |
