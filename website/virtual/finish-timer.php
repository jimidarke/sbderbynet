<?php
require_once(__DIR__ . '/_guard.inc');
virtual_page_guard();

$lane = isset($_GET['lane']) ? (int)$_GET['lane'] : 0;
$dip = virtual_dip_for_lane($lane);
if (!$dip) {
  http_response_code(400);
  echo "Missing or invalid ?lane= (1..4)";
  exit;
}
?>
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Virtual Finish Timer — Lane <?= htmlspecialchars($lane) ?></title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="/derbynet/virtual/virtual.css<?= virtual_asset_v('virtual.css') ?>">
</head>
<body class="virtual-device" data-role="finish-timer"
      data-lane="<?= htmlspecialchars($lane) ?>"
      data-dip="<?= htmlspecialchars($dip) ?>"
      data-hwid="B_FINISH_<?= htmlspecialchars($lane) ?>">

<header class="vd-header">
  <span class="vd-tag">VIRTUAL</span>
  <h1>Finish Timer · Lane <?= htmlspecialchars($lane) ?></h1>
  <span class="vd-conn" id="conn-status" data-state="off">disconnected</span>
</header>

<main class="vd-main vd-finish-main">
  <section class="vd-finish-device" aria-label="Finish timer device">
    <div class="vd-device-chassis">
      <div class="vd-led" id="lane-led" data-color="off">
        <div class="vd-led-circle"></div>
      </div>

      <div class="vd-7seg" id="pinny" aria-label="Pinny display">----</div>

      <button type="button"
              class="vd-hw-toggle"
              id="ready-toggle"
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
        <span>HWID <?= htmlspecialchars('B_FINISH_' . $lane) ?></span>
        <span>DIP <?= htmlspecialchars($dip) ?></span>
        <span>Race: <span id="race-state">UNCONFIGURED</span></span>
      </div>
    </div>
  </section>

  <section class="vd-log">
    <div class="vd-log-label">MQTT log</div>
    <ol id="mqtt-log"></ol>
  </section>
</main>

<!-- mqtt.min.js is loaded dynamically by virtual-common.js (vendored first,
     unpkg fallback). See website/js/vendor/README.md. -->
<script src="/derbynet/virtual/virtual-common.js<?= virtual_asset_v('virtual-common.js') ?>"></script>
<script src="/derbynet/virtual/virtual-finish-timer.js<?= virtual_asset_v('virtual-finish-timer.js') ?>"></script>
</body>
</html>
