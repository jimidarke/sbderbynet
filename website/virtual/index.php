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

  <h2 class="vd-section-heading">Finish Timers</h2>
  <div class="vd-index-grid cat-during">
    <?php for ($lane = 1; $lane <= $lane_count; $lane++): ?>
      <a class="vd-index-card" href="finish-timer.php?lane=<?= $lane ?>" target="_blank">
        <span class="vd-index-title">Lane <?= $lane ?></span>
        <span class="vd-index-meta">B_FINISH_<?= $lane ?> · DIP <?= htmlspecialchars(virtual_dip_for_lane($lane)) ?></span>
      </a>
    <?php endfor; ?>
  </div>

  <h2 class="vd-section-heading">Start Timer</h2>
  <div class="vd-index-grid cat-before">
    <a class="vd-index-card" href="start-timer.php" target="_blank">
      <span class="vd-index-title">Start Gate</span>
      <span class="vd-index-meta">hwid START</span>
    </a>
  </div>

  <h2 class="vd-section-heading">LED Signs</h2>
  <div class="vd-index-grid cat-other">
    <a class="vd-index-card" href="led-sign.php?zone=starter" target="_blank">
      <span class="vd-index-title">Starter</span>
      <span class="vd-index-meta">B_LEDSIGN_starter</span>
    </a>
    <?php for ($lane = 1; $lane <= $lane_count; $lane++): ?>
      <a class="vd-index-card" href="led-sign.php?zone=usher-lane<?= $lane ?>" target="_blank">
        <span class="vd-index-title">Usher Lane <?= $lane ?></span>
        <span class="vd-index-meta">B_LEDSIGN_usher-lane<?= $lane ?></span>
      </a>
    <?php endfor; ?>
  </div>

  <h2 class="vd-section-heading">Displays</h2>
  <div class="vd-index-grid cat-after">
    <a class="vd-index-card" href="derby-display.php?id=1&kiosk=welcome" target="_blank">
      <span class="vd-index-title">Display 1 (welcome)</span>
      <span class="vd-index-meta">B_DISPLAY_1</span>
    </a>
    <a class="vd-index-card" href="derby-display.php?id=2&kiosk=now-racing" target="_blank">
      <span class="vd-index-title">Display 2 (now-racing)</span>
      <span class="vd-index-meta">B_DISPLAY_2</span>
    </a>
  </div>

  <h2 class="vd-section-heading">Quick Reference</h2>
  <ul style="padding: 0 40px; color: #ccc;">
    <li>Race state topic: <code>derbynet/race/state</code></li>
    <li>Lane LED: <code>derbynet/lane/{N}/led</code> · Pinny: <code>derbynet/lane/{N}/pinny</code></li>
    <li>Device state: <code>derbynet/device/{hwid}/state</code> with <code>{dip,state,toggle,timestamp}</code></li>
    <li>Telemetry: <code>derbynet/device/{hwid}/telemetry</code> · Status (LWT): <code>derbynet/device/{hwid}/status</code></li>
  </ul>
</main>

</body>
</html>
