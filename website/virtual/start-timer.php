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
<link rel="stylesheet" href="/derbynet/virtual/virtual.css">
</head>
<body class="virtual-device" data-role="start-timer"
      data-hwid="START" data-dip="0001">

<header class="vd-header">
  <span class="vd-tag">VIRTUAL</span>
  <h1>Start Timer</h1>
  <span class="vd-conn" id="conn-status" data-state="off">disconnected</span>
</header>

<main class="vd-main">
  <section class="vd-state">
    <div class="vd-state-label">Race State</div>
    <div class="vd-state-value" id="race-state">UNCONFIGURED</div>
  </section>

  <section>
    <div class="vd-pinny-label">Gate</div>
    <div class="vd-state-value" id="gate-state">CLOSED</div>
  </section>

  <section class="vd-controls">
    <button id="btn-go" class="vd-go-button" disabled>OPEN GATE — GO</button>

    <label class="vd-auto">
      <input type="checkbox" id="auto-mode">
      Auto-fire GO when state enters STAGING after
      <input type="number" id="auto-delay" value="2.0" min="0.0" max="30" step="0.1">
      seconds
    </label>
  </section>

  <section class="vd-log">
    <div class="vd-log-label">MQTT log</div>
    <ol id="mqtt-log"></ol>
  </section>
</main>

<script src="https://unpkg.com/mqtt@5.10.1/dist/mqtt.min.js"></script>
<script src="/derbynet/virtual/virtual-common.js"></script>
<script src="/derbynet/virtual/virtual-start-timer.js"></script>
</body>
</html>
