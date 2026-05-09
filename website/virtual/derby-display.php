<?php
require_once(__DIR__ . '/_guard.inc');
virtual_page_guard();

$id = isset($_GET['id']) ? (int)$_GET['id'] : 1;
$kiosk = isset($_GET['kiosk']) ? preg_replace('/[^a-zA-Z0-9_-]/', '', $_GET['kiosk'])
                                : 'welcome';
$hwid = 'B_DISPLAY_' . $id;
$tenant_slug = virtual_active_tenant();
?>
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Virtual Display <?= htmlspecialchars($id) ?></title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="/derbynet/virtual/virtual.css<?= virtual_asset_v('virtual.css') ?>">
<style>
  .vd-display-frame { width: 100%; height: calc(100vh - 60px); border: 0; background: white; }
</style>
</head>
<body class="virtual-device" data-role="derby-display"
      data-id="<?= htmlspecialchars($id) ?>"
      data-hwid="<?= htmlspecialchars($hwid) ?>">

<header class="vd-header">
  <span class="vd-tag">VIRTUAL</span>
  <h1>Display <?= htmlspecialchars($id) ?> · kiosk=<?= htmlspecialchars($kiosk) ?></h1>
  <span class="vd-sandbox" data-state="<?= $tenant_slug === '' ? 'warn' : 'info' ?>"
        title="All MQTT publishes on this page are scoped to this sandbox.">
    sandbox: <b><?= htmlspecialchars($tenant_slug !== '' ? $tenant_slug : '(none)') ?></b>
  </span>
  <span class="vd-conn" id="conn-status" data-state="off">disconnected</span>
</header>

<iframe class="vd-display-frame"
        src="/derbynet/kiosk.php?name=<?= htmlspecialchars($kiosk) ?>"></iframe>

<script>
  window.DERBYNET_TENANT = <?= json_encode($tenant_slug) ?>;
</script>
<!-- mqtt.min.js loaded dynamically by virtual-common.js (vendored first). -->
<script src="/derbynet/virtual/virtual-common.js<?= virtual_asset_v('virtual-common.js') ?>"></script>
<script>
// Display devices are passive: they only report telemetry/status so the
// race server tracks them as online. The kiosk content itself is fetched
// over HTTP by the iframe above, exactly as a real Chromium kiosk does.
(function () {
  const hwid = document.body.dataset.hwid;
  const id   = document.body.dataset.id;
  const telemetryTopic = VirtualCommon.topic('device', hwid, 'telemetry');
  const statusTopic    = VirtualCommon.topic('device', hwid, 'status');

  async function main() {
    const clientId = 'b_display_' + id + '_' + Math.random().toString(36).slice(2, 8);
    const client = await VirtualCommon.connectBroker({
      clientId: clientId,
      will: { topic: statusTopic, payload: 'offline', qos: 1, retain: true },
      onConnect: (c) => {
        c.publish(statusTopic, 'online', { qos: 1, retain: true });
        const send = () => VirtualCommon.publish(c, telemetryTopic,
          { hostname: 'browser-display-' + id, hwid: hwid,
            uptime: Math.floor(performance.now() / 1000),
            cpu_temp: 40, memory_usage: 30, disk: 20, cpu_usage: 5 },
          { qos: 0, retain: true });
        send();
        setInterval(send, 5000);
      },
    });
    VirtualCommon.wireVisibilityOffline(client, statusTopic);
  }
  main().catch((e) => alert('Display init failed: ' + e.message));
})();
</script>
</body>
</html>
