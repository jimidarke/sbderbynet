<?php
require_once(__DIR__ . '/_guard.inc');
virtual_page_guard();

$zone = isset($_GET['zone']) ? preg_replace('/[^a-zA-Z0-9_-]/', '', $_GET['zone']) : '';
if ($zone === '') {
  http_response_code(400);
  echo "Missing ?zone= (e.g. starter, usher-lane1)";
  exit;
}
$hwid = 'B_LEDSIGN_' . $zone;
?>
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Virtual LED Sign — <?= htmlspecialchars($zone) ?></title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="/derbynet/virtual/virtual.css">
</head>
<body class="virtual-device" data-role="led-sign"
      data-zone="<?= htmlspecialchars($zone) ?>"
      data-hwid="<?= htmlspecialchars($hwid) ?>">

<header class="vd-header">
  <span class="vd-tag">VIRTUAL</span>
  <h1>LED Sign · <?= htmlspecialchars($zone) ?></h1>
  <span class="vd-conn" id="conn-status" data-state="off">disconnected</span>
</header>

<main class="vd-main">
  <section style="grid-column: 1 / -1;">
    <div class="vd-log-label">Sign Display</div>
    <div class="vd-sign-display" id="sign-text">…</div>
  </section>

  <section class="vd-log" style="grid-column: 1 / -1;">
    <div class="vd-log-label">MQTT log</div>
    <ol id="mqtt-log"></ol>
  </section>
</main>

<script src="https://unpkg.com/mqtt@5.10.1/dist/mqtt.min.js"></script>
<script src="/derbynet/virtual/virtual-common.js"></script>
<script>
(function () {
  const body = document.body;
  const zone = body.dataset.zone;
  const hwid = body.dataset.hwid;
  const messageTopic   = 'derbynet/ledsign/' + zone + '/message';
  const broadcastTopic = 'derbynet/ledsign/broadcast';
  const telemetryTopic = 'derbynet/device/' + hwid + '/telemetry';
  const statusTopic    = 'derbynet/device/' + hwid + '/status';
  const sign = document.getElementById('sign-text');

  function render(payload) {
    let text = '';
    if (typeof payload === 'string') text = payload;
    else if (payload && payload.message) text = payload.message;
    else text = JSON.stringify(payload);
    sign.textContent = text;
  }

  async function main() {
    const clientId = 'b_ledsign_' + zone + '_' + Math.random().toString(36).slice(2, 8);
    const client = await VirtualCommon.connectBroker({
      clientId: clientId,
      will: { topic: statusTopic, payload: 'offline', qos: 1, retain: true },
      onConnect: (c) => {
        c.subscribe(messageTopic, { qos: 1 });
        c.subscribe(broadcastTopic, { qos: 1 });
        c.publish(statusTopic, 'online', { qos: 1, retain: true });
        // Telemetry
        const send = () => VirtualCommon.publish(c, telemetryTopic,
          { hostname: 'browser-ledsign-' + zone, hwid: hwid, zone: zone,
            uptime: Math.floor(performance.now() / 1000), wifi_rssi: -45 },
          { qos: 0, retain: true });
        send();
        setInterval(send, 5000);
      },
      onMessage: (topic, payload) => {
        if (topic === messageTopic || topic === broadcastTopic) render(payload);
      },
    });
    VirtualCommon.wireVisibilityOffline(client, statusTopic);
  }
  main().catch((e) => alert('LED sign init failed: ' + e.message));
})();
</script>
</body>
</html>
