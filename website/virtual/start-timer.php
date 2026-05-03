<?php
require_once(__DIR__ . '/_guard.inc');
virtual_page_guard();
?>
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Virtual Start Timer</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="/derbynet/virtual/virtual.css<?= virtual_asset_v('virtual.css') ?>">
</head>
<body class="virtual-device" data-role="start-timer"
      data-hwid="starttimer" data-dip="0001">

<header class="vd-header">
  <span class="vd-tag">VIRTUAL</span>
  <h1>Start Timer</h1>
  <span class="vd-conn" id="conn-status" data-state="off">disconnected</span>
</header>

<main class="vd-main vd-start-main">
  <section class="vd-start-device" aria-label="Start timer device">
    <div class="vd-device-chassis vd-start-chassis">
      <button type="button"
              class="vd-latch-button"
              id="btn-latch"
              role="switch"
              aria-checked="false"
              data-latched="false"
              title="Press to latch GO. Press again to release (STOP).">
        <span class="vd-latch-bezel">
          <span class="vd-latch-cap">
            <span class="vd-latch-label" id="latch-label">START</span>
          </span>
        </span>
      </button>

      <div class="vd-device-meta">
        <span>HWID starttimer</span>
        <span>Signal: <span id="signal-state">LOW</span></span>
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
<script src="/derbynet/virtual/virtual-start-timer.js<?= virtual_asset_v('virtual-start-timer.js') ?>"></script>
</body>
</html>
