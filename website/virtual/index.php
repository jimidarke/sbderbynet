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
<link rel="stylesheet" href="/derbynet/virtual/virtual.css">
</head>
<body class="virtual-device">

<header class="vd-header">
  <span class="vd-tag">VIRTUAL</span>
  <h1>Browser Virtual Hardware</h1>
  <?php if ($last_sync): ?>
    <span class="vd-conn" data-state="connected">last sync <?= htmlspecialchars($last_sync) ?></span>
  <?php endif; ?>
</header>

<main>
  <p style="padding: 0 20px; color: #aaa;">
    Cloud-only test instruments. Each card opens a dedicated browser tab that
    publishes/subscribes to MQTT exactly like the corresponding real device.
    All hwids are prefixed <code>B_</code> and excluded from race-day device
    assignment. Open these on a desktop browser. Once the page is closed (or
    the tab is hidden) the device goes offline.
  </p>

  <h2 style="padding: 0 20px;">Finish Timers</h2>
  <div class="vd-index-grid">
    <?php for ($lane = 1; $lane <= $lane_count; $lane++): ?>
      <div class="vd-index-card">
        <a href="finish-timer.php?lane=<?= $lane ?>" target="_blank">Lane <?= $lane ?></a>
        <div class="vd-index-meta">B_FINISH_<?= $lane ?> · DIP <?= htmlspecialchars(virtual_dip_for_lane($lane)) ?></div>
      </div>
    <?php endfor; ?>
  </div>

  <h2 style="padding: 0 20px;">Start Timer</h2>
  <div class="vd-index-grid">
    <div class="vd-index-card">
      <a href="start-timer.php" target="_blank">Start Gate</a>
      <div class="vd-index-meta">hwid START</div>
    </div>
  </div>

  <h2 style="padding: 0 20px;">LED Signs</h2>
  <div class="vd-index-grid">
    <div class="vd-index-card">
      <a href="led-sign.php?zone=starter" target="_blank">Starter</a>
      <div class="vd-index-meta">B_LEDSIGN_starter</div>
    </div>
    <?php for ($lane = 1; $lane <= $lane_count; $lane++): ?>
      <div class="vd-index-card">
        <a href="led-sign.php?zone=usher-lane<?= $lane ?>" target="_blank">Usher Lane <?= $lane ?></a>
        <div class="vd-index-meta">B_LEDSIGN_usher-lane<?= $lane ?></div>
      </div>
    <?php endfor; ?>
  </div>

  <h2 style="padding: 0 20px;">Displays</h2>
  <div class="vd-index-grid">
    <div class="vd-index-card">
      <a href="derby-display.php?id=1&kiosk=welcome" target="_blank">Display 1 (welcome)</a>
      <div class="vd-index-meta">B_DISPLAY_1</div>
    </div>
    <div class="vd-index-card">
      <a href="derby-display.php?id=2&kiosk=now-racing" target="_blank">Display 2 (now-racing)</a>
      <div class="vd-index-meta">B_DISPLAY_2</div>
    </div>
  </div>

  <h2 style="padding: 0 20px;">Quick Reference</h2>
  <ul style="padding: 0 40px; color: #ccc;">
    <li>Race state topic: <code>derbynet/race/state</code></li>
    <li>Lane LED: <code>derbynet/lane/{N}/led</code> · Pinny: <code>derbynet/lane/{N}/pinny</code></li>
    <li>Device state: <code>derbynet/device/{hwid}/state</code> with <code>{dip,state,toggle,timestamp}</code></li>
    <li>Telemetry: <code>derbynet/device/{hwid}/telemetry</code> · Status (LWT): <code>derbynet/device/{hwid}/status</code></li>
  </ul>
</main>

</body>
</html>
