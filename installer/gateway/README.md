# DerbyNet Local Gateway

MQTT bridge that connects race-day hardware devices to the cloud DerbyNet server.

## How It Works

```
Local Network (192.168.100.x)              Cloud VPS
┌──────────────┐                           ┌──────────────────┐
│ Start Timer  │──┐                        │ Cloud Mosquitto   │
│ Finish Timer │──┤──► Local Mosquitto ◄──bridge──► Race Server│
│ LED Signs    │──┤    (192.168.100.10)    │ PHP Web App       │
│ Kiosk Display│──┘                        │ Caddy (HTTPS)     │
└──────────────┘                           └──────────────────┘
```

- Local devices connect to the gateway at `192.168.100.10:1883` (unchanged)
- The gateway bridges all `derbynet/#` MQTT topics bidirectionally to the cloud broker
- Zero firmware changes needed on any device

## Setup

1. Configure the bridge:
   ```bash
   cp .env.example .env
   nano .env  # Set CLOUD_HOST, CLOUD_MQTT_USER, CLOUD_MQTT_PASS
   ```

2. Update the bridge config with your cloud credentials:
   ```bash
   # Edit mosquitto-bridge.conf and replace:
   #   CLOUD_HOST        → your VPS IP or domain
   #   CLOUD_MQTT_USER   → MQTT username
   #   CLOUD_MQTT_PASS   → MQTT password
   ```

3. Start the gateway:
   ```bash
   docker compose up -d
   ```

4. Verify the bridge is connected:
   ```bash
   # On the cloud VPS, check for bridge status:
   mosquitto_sub -h localhost -u derbynet -P <pass> -t 'derbynet/bridge/status'
   ```

## Race Day Failover

If the cloud becomes unreachable during an event:

```bash
# Switch to fully local operation (no cloud dependency)
./switch-to-local.sh

# Resume cloud operation when connectivity is restored
./switch-to-cloud.sh
```

See `docker-compose.fallback.yml` for the full local stack.
