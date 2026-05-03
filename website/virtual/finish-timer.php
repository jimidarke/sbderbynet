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
<link rel="stylesheet" href="/derbynet/virtual/virtual.css">
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

<main class="vd-main">
  <section class="vd-pinny">
    <div class="vd-pinny-label">Car</div>
    <div class="vd-pinny-number" id="pinny">----</div>
  </section>

  <section class="vd-led" id="lane-led" data-color="off">
    <div class="vd-led-label">Lane LED</div>
    <div class="vd-led-circle"></div>
    <div class="vd-led-color" id="lane-led-name">off</div>
  </section>

  <section class="vd-state">
    <div class="vd-state-label">Race State</div>
    <div class="vd-state-value" id="race-state">UNCONFIGURED</div>
  </section>

  <section class="vd-controls">
    <label class="vd-toggle">
      <input type="checkbox" id="ready-toggle">
      <span>Ready (toggle is up — staff has loaded a car)</span>
    </label>

    <button id="btn-finish" class="vd-finish-button" disabled>
      CAR CROSSED FINISH LINE
    </button>

    <label class="vd-auto">
      <input type="checkbox" id="auto-mode">
      Auto-finish during RACING
      <input type="number" id="auto-min" value="2.5" min="0.5" max="30" step="0.1">
      to
      <input type="number" id="auto-max" value="6.5" min="0.5" max="30" step="0.1">
      seconds
    </label>
  </section>

  <section class="vd-log">
    <div class="vd-log-label">MQTT log</div>
    <ol id="mqtt-log"></ol>
  </section>
</main>

<!-- mqtt.min.js is loaded dynamically by virtual-common.js (vendored first,
     unpkg fallback). See website/js/vendor/README.md. -->
<script src="/derbynet/virtual/virtual-common.js"></script>
<script src="/derbynet/virtual/virtual-finish-timer.js"></script>
</body>
</html>
