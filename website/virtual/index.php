<?php
require_once(__DIR__ . '/_guard.inc');
virtual_page_guard();

$lane_count = isset($_SERVER['LANE_COUNT']) ? (int)$_SERVER['LANE_COUNT'] : 3;
if ($lane_count < 1 || $lane_count > 4) $lane_count = 3;
$last_sync = function_exists('cloud_last_sync_utc') ? cloud_last_sync_utc() : null;
?>
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Virtual Hardware Control Panel</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="../css/global.css">
<link rel="stylesheet" href="/derbynet/virtual/virtual.css<?= virtual_asset_v('virtual.css') ?>">
</head>
<body class="virtual-device">

<header class="vd-header">
  <span class="vd-tag">VIRTUAL</span>
  <h1>Browser Virtual Hardware</h1>
  <span class="vd-conn" id="conn-status" data-state="off">disconnected</span>
  <?php if ($last_sync): ?>
    <span class="vd-conn" data-state="connected">last sync <?= htmlspecialchars($last_sync) ?></span>
  <?php endif; ?>
</header>

<main class="vd-combined" style="--lanes: <?= $lane_count ?>">
  <section class="vd-combined-start" aria-label="Start timer">
    <div class="vd-combined-label">START · hwid <code>START</code></div>
    <div id="device-start" class="vd-device-chassis vd-start-chassis">
      <button type="button"
              class="vd-latch-button"
              data-role="btn-latch"
              role="switch"
              aria-checked="false"
              data-latched="false"
              title="Press to latch GO. Press again to release (STOP).">
        <span class="vd-latch-bezel">
          <span class="vd-latch-cap">
            <span class="vd-latch-label" data-role="latch-label">START</span>
          </span>
        </span>
      </button>
      <div class="vd-device-meta">
        <span>Signal: <span data-role="signal-state">LOW</span></span>
        <span>Race: <span data-role="race-state">UNCONFIGURED</span></span>
      </div>
    </div>
  </section>

  <section class="vd-combined-finishes" aria-label="Finish timers">
    <?php for ($lane = 1; $lane <= $lane_count; $lane++):
      $dip = virtual_dip_for_lane($lane);
      $hwid = 'B_FINISH_' . $lane; ?>
    <div class="vd-combined-finish">
      <div class="vd-combined-label">LANE <?= $lane ?> · hwid <code><?= htmlspecialchars($hwid) ?></code> · DIP <?= htmlspecialchars($dip) ?></div>
      <div class="vd-device-chassis device-finish"
           data-lane="<?= $lane ?>"
           data-dip="<?= htmlspecialchars($dip) ?>"
           data-hwid="<?= htmlspecialchars($hwid) ?>">
        <div class="vd-led" data-role="lane-led" data-color="off">
          <div class="vd-led-circle"></div>
        </div>
        <div class="vd-7seg" data-role="pinny" aria-label="Pinny display">----</div>
        <button type="button"
                class="vd-hw-toggle"
                data-role="ready-toggle"
                role="switch"
                aria-checked="false"
                data-position="down"
                title="Click to flip the toggle (up = car loaded, down = car gone)">
          <span class="vd-hw-toggle-track">
            <span class="vd-hw-toggle-label vd-hw-toggle-up">UP</span>
            <span class="vd-hw-toggle-label vd-hw-toggle-down">DOWN</span>
            <span class="vd-hw-toggle-lever"></span>
          </span>
        </button>
        <div class="vd-device-meta">
          <span>Race: <span data-role="race-state">UNCONFIGURED</span></span>
        </div>
      </div>
    </div>
    <?php endfor; ?>
  </section>

  <section class="vd-log" aria-label="MQTT log">
    <div class="vd-log-label">MQTT log (single shared client)</div>
    <ol id="mqtt-log"></ol>
  </section>
</main>

<script src="/derbynet/virtual/virtual-common.js<?= virtual_asset_v('virtual-common.js') ?>"></script>
<script src="/derbynet/virtual/virtual-start-timer.js<?= virtual_asset_v('virtual-start-timer.js') ?>"></script>
<script src="/derbynet/virtual/virtual-finish-timer.js<?= virtual_asset_v('virtual-finish-timer.js') ?>"></script>
<script>
(async function () {
  // Single MQTT client serving START + N finish timers. MQTT's `will` is
  // per-connection so LWT only covers one hwid (we point it at START).
  // The visibility hook publishes offline retained for ALL hwids; the race
  // server's telemetry-gap fallback (~5s) handles ungraceful disconnects
  // for the rest.
  const startRoot = document.getElementById('device-start');
  const finishRoots = Array.from(document.querySelectorAll('.device-finish'));
  const startStatus = 'derbynet/device/START/status';

  const descriptors = [];
  function dispatch(topic, payload) {
    descriptors.forEach((d) => d.onMessage(topic, payload));
  }
  function onConnectAll(c) {
    descriptors.forEach((d) => d.onConnected());
  }

  const client = await VirtualCommon.connectBroker({
    clientId: 'b_combined_' + Math.random().toString(36).slice(2, 8),
    will: { topic: startStatus, payload: 'offline', qos: 1, retain: true },
    onConnect: onConnectAll,
    onMessage: dispatch,
  });

  // Mount finish timers first, then start. Order doesn't matter for MQTT;
  // it only affects the order onConnected publishes online/telemetry.
  finishRoots.forEach((root) => {
    descriptors.push(VirtualFinish.mount({
      root: root,
      client: client,
      lane: parseInt(root.dataset.lane, 10),
      hwid: root.dataset.hwid,
      dip: root.dataset.dip,
    }));
  });
  descriptors.push(VirtualStart.mount({
    root: startRoot,
    client: client,
    hwid: 'START',
    dip: '0001',
  }));

  VirtualCommon.wireVisibilityOfflineMany(
    client,
    descriptors.map((d) => d.statusTopic)
  );

  // Mirror real-hardware networkError(): when the broker drops the
  // shared client, every device that wants a disconnect override gets
  // notified. Reconnect-driven onConnected() runs again via the connect
  // event and reapplies the toggle's local colour.
  client.on('close', () => {
    descriptors.forEach((d) => { if (d.onDisconnect) d.onDisconnect(); });
  });
  client.on('offline', () => {
    descriptors.forEach((d) => { if (d.onDisconnect) d.onDisconnect(); });
  });
})().catch((e) => {
  VirtualCommon.log('sys', '', 'init error: ' + e.message);
  alert('Virtual hardware init failed: ' + e.message);
});
</script>

</body>
</html>
