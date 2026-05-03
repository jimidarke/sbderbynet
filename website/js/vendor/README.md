# Vendored Third-Party JavaScript

Files in this directory are served verbatim by the web layer. They are *not*
fetched at build time — to keep the cloud twin reachable when external CDNs
are blocked or down (race-day venue WiFi, restricted networks, etc.), drop
the file here once and commit it.

## mqtt.min.js (used by website/virtual/*)

Cloud-only: the browser virtual hardware pages prefer this local copy and
fall back to unpkg only if it's missing.

To vendor:

```sh
curl -L -o website/js/vendor/mqtt.min.js \
  https://unpkg.com/mqtt@5.10.1/dist/mqtt.min.js
```

Then verify the size is roughly 200 KB and the file starts with a JS
license/iife banner. Commit it. Update the version in this README and in
`website/virtual/virtual-common.js` (the unpkg fallback URL) when bumping.

Pinned version: **mqtt@5.10.1** (MIT, github.com/mqttjs/MQTT.js).
