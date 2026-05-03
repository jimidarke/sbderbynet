// virtual-start-timer.js
//
// Browser start timer. Wire-compatible with extras/soapbox/infra/starttimer/.
// Single device per cloud twin: hwid 'START', publishes GO via the lane-1 DIP
// topic so derbyRace.startRace() picks it up unchanged.

(function () {
  const hwid = 'START';
  const dip = '0001';
  const stateTopic     = 'derbynet/device/' + hwid + '/state';
  const telemetryTopic = 'derbynet/device/' + hwid + '/telemetry';
  const statusTopic    = 'derbynet/device/' + hwid + '/status';
  const raceStateTopic = 'derbynet/race/state';

  // The race server's startRace() listens for state=GO on a finish-timer
  // topic (the one that maps to lane 1 by DIP). Real ESP32 start timer
  // publishes to derbynet/device/starttimer/state but the simulator path
  // (simulate_racing.py:271) uses the lane-1 DIP topic and that's what
  // derbyRace.py:229 reacts to. We mirror the simulator behavior.
  const goPublishTopic = 'derbynet/device/1000/state';

  let raceState = 'UNCONFIGURED';
  let gateOpen = false;
  let autoTimer = null;

  const ui = {
    raceState: document.getElementById('race-state'),
    gate: document.getElementById('gate-state'),
    btnGo: document.getElementById('btn-go'),
    autoMode: document.getElementById('auto-mode'),
    autoDelay: document.getElementById('auto-delay'),
  };

  function refreshButton() {
    ui.btnGo.disabled = !(raceState === 'STAGING' || raceState === 'RACING') || gateOpen;
  }

  function buildTelemetry() {
    return {
      hostname: 'browser-start',
      hwid: hwid,
      dip: dip,
      uptime: Math.floor(performance.now() / 1000),
      ip: '0.0.0.0',
      mac: 'B2:00:00:00:00:00',
      wifi_rssi: -45,
      temperature: 22.0,
      humidity: 50.0,
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
    setInterval(send, 5000); // real ESP32 publishes ~5 Hz from main.py loop
  }

  function fireGo(client) {
    if (gateOpen) return;
    gateOpen = true;
    ui.gate.textContent = 'OPEN';
    refreshButton();
    VirtualCommon.publish(client, goPublishTopic, {
      hwid: hwid, dip: dip, state: 'GO', toggle: true,
      timestamp: Date.now() / 1000,
    }, { qos: 2, retain: true });
    // Also post our own /state for observers
    VirtualCommon.publish(client, stateTopic, {
      hwid: hwid, state: 'GO', timestamp: Date.now() / 1000,
    }, { qos: 1 });
  }

  function maybeAutoFire(client) {
    clearTimeout(autoTimer);
    if (!ui.autoMode.checked) return;
    if (raceState !== 'STAGING') return;
    if (gateOpen) return;
    const delay = parseFloat(ui.autoDelay.value) || 2.0;
    autoTimer = setTimeout(() => fireGo(client), delay * 1000);
  }

  function onMessage(topic, payload, client) {
    if (topic === raceStateTopic) {
      raceState = (typeof payload === 'string') ? payload
                  : (payload.state || JSON.stringify(payload));
      ui.raceState.textContent = raceState;
      if (raceState === 'STAGING' || raceState === 'STOPPED') {
        gateOpen = false;
        ui.gate.textContent = 'CLOSED';
      }
      refreshButton();
      maybeAutoFire(client);
    }
  }

  async function main() {
    const clientId = 'b_start_' + Math.random().toString(36).slice(2, 8);
    let client;
    client = await VirtualCommon.connectBroker({
      clientId: clientId,
      will: { topic: statusTopic, payload: 'offline', qos: 1, retain: true },
      onConnect: (c) => {
        c.subscribe(raceStateTopic, { qos: 1 });
        c.publish(statusTopic, 'online', { qos: 1, retain: true });
        startTelemetry(c);
      },
      onMessage: (t, p) => onMessage(t, p, client),
    });
    VirtualCommon.wireVisibilityOffline(client, statusTopic);
    ui.btnGo.addEventListener('click', () => fireGo(client));
    ui.autoMode.addEventListener('change', () => maybeAutoFire(client));
  }

  main().catch((e) => {
    VirtualCommon.log('sys', '', 'init error: ' + e.message);
    alert('Virtual start timer init failed: ' + e.message);
  });
})();
