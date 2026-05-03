// virtual-finish-timer.js
//
// Browser-resident finish timer. Wire-compatible with the real device
// (extras/soapbox/infra/finishtimer/files/finishtimer.py): same topics,
// same JSON payloads, same DIP-derived lane mapping.

(function () {
  const body = document.body;
  const lane = parseInt(body.dataset.lane, 10);
  const dip = body.dataset.dip;
  const hwid = body.dataset.hwid;

  const stateTopic     = 'derbynet/device/' + hwid + '/state';
  const telemetryTopic = 'derbynet/device/' + hwid + '/telemetry';
  const statusTopic    = 'derbynet/device/' + hwid + '/status';
  const raceStateTopic = 'derbynet/race/state';
  const ledTopic       = 'derbynet/lane/' + lane + '/led';
  const pinnyTopic     = 'derbynet/lane/' + lane + '/pinny';

  let raceState = 'UNCONFIGURED';
  let isReady = false;     // toggle position
  let hasFinished = false; // car has crossed in this race
  let autoFinishTimer = null;

  const ui = {
    raceState: document.getElementById('race-state'),
    pinny: document.getElementById('pinny'),
    led: document.getElementById('lane-led'),
    ledName: document.getElementById('lane-led-name'),
    btnFinish: document.getElementById('btn-finish'),
    readyToggle: document.getElementById('ready-toggle'),
    autoMode: document.getElementById('auto-mode'),
    autoMin: document.getElementById('auto-min'),
    autoMax: document.getElementById('auto-max'),
  };

  function setLed(color) {
    ui.led.dataset.color = color;
    ui.ledName.textContent = color;
  }

  function refreshFinishButton() {
    // Real timer fires the toggle on any car cross, but UX-wise we only enable
    // the button while the race is RACING and the toggle is up.
    ui.btnFinish.disabled = !(raceState === 'RACING' && isReady && !hasFinished);
  }

  function buildTelemetry() {
    return {
      hostname: 'browser-finish-' + lane,
      hwid: hwid,
      dip: dip,
      uptime: Math.floor(performance.now() / 1000),
      ip: '0.0.0.0',
      mac: 'B2:00:00:00:00:0' + lane,
      wifi_rssi: -45,
      battery_level: 100,
      cpu_temp: 25,
      memory_usage: 0,
      disk: 0,
      cpu_usage: 0,
      readyToRace: isReady,
      toggle: isReady && !hasFinished,
      pcbVersion: 'browser',
    };
  }

  function startTelemetry(client) {
    const send = () => {
      if (client.connected) {
        VirtualCommon.publish(client, telemetryTopic, buildTelemetry(),
                              { qos: 0, retain: true });
      }
    };
    send();
    setInterval(send, 1000);
  }

  function publishState(client, payload) {
    VirtualCommon.publish(client, stateTopic, payload, { qos: 2, retain: true });
  }

  function onReadyToggle(client) {
    isReady = ui.readyToggle.checked;
    hasFinished = false;
    refreshFinishButton();
    publishState(client, {
      hwid: hwid, dip: dip,
      state: isReady ? 'READY' : 'IDLE',
      toggle: isReady,
      timestamp: Date.now() / 1000,
    });
  }

  function triggerFinish(client) {
    if (!isReady || hasFinished || raceState !== 'RACING') return;
    hasFinished = true;
    refreshFinishButton();
    publishState(client, {
      hwid: hwid, dip: dip,
      state: 'GO',         // matches real device
      toggle: false,       // switch DOWN = car crossed
      timestamp: Date.now() / 1000,
    });
  }

  function maybeScheduleAutoFinish() {
    clearTimeout(autoFinishTimer);
    if (!ui.autoMode.checked) return;
    if (raceState !== 'RACING') return;
    if (!isReady || hasFinished) return;
    const lo = parseFloat(ui.autoMin.value) || 2.5;
    const hi = parseFloat(ui.autoMax.value) || 6.5;
    const delay = lo + Math.random() * Math.max(0, hi - lo);
    autoFinishTimer = setTimeout(() => {
      // re-resolve client through closure below
      autoFinishTimer = null;
      triggerFinish(window.__virtual_client);
    }, delay * 1000);
  }

  function onMessage(topic, payload) {
    if (topic === raceStateTopic) {
      raceState = (typeof payload === 'string') ? payload
                  : (payload.state || JSON.stringify(payload));
      ui.raceState.textContent = raceState;
      if (raceState === 'STAGING' || raceState === 'STOPPED') {
        hasFinished = false;
      }
      refreshFinishButton();
      maybeScheduleAutoFinish();
    } else if (topic === ledTopic) {
      setLed(typeof payload === 'string' ? payload : (payload.color || 'off'));
    } else if (topic === pinnyTopic) {
      const v = (typeof payload === 'string') ? payload
                : (payload.pinny || JSON.stringify(payload));
      ui.pinny.textContent = v;
    }
  }

  async function main() {
    const clientId = 'b_finish_' + lane + '_' + Math.random().toString(36).slice(2, 8);
    const client = await VirtualCommon.connectBroker({
      clientId: clientId,
      will: { topic: statusTopic, payload: 'offline', qos: 1, retain: true },
      onConnect: (c) => {
        c.subscribe(raceStateTopic, { qos: 1 });
        c.subscribe(ledTopic, { qos: 1 });
        c.subscribe(pinnyTopic, { qos: 1 });
        c.publish(statusTopic, 'online', { qos: 1, retain: true });
        startTelemetry(c);
      },
      onMessage: onMessage,
    });
    window.__virtual_client = client;
    VirtualCommon.wireVisibilityOffline(client, statusTopic);

    ui.readyToggle.addEventListener('change', () => onReadyToggle(client));
    ui.btnFinish.addEventListener('click', () => triggerFinish(client));
    ui.autoMode.addEventListener('change', maybeScheduleAutoFinish);
  }

  main().catch((e) => {
    VirtualCommon.log('sys', '', 'init error: ' + e.message);
    document.body.classList.add('vd-init-failed');
    alert('Virtual finish timer init failed: ' + e.message);
  });
})();
