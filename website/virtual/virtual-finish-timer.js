// virtual-finish-timer.js
//
// Browser-resident finish timer. Wire-compatible with the real device
// (extras/soapbox/infra/finishtimer/files/finishtimer.py): same topics,
// same JSON payloads, same DIP-derived lane mapping.
//
// Real-hardware fidelity: the only operator interaction is the physical
// toggle switch. UP = car loaded/staged. DOWN = car has departed/crossed.
// The device publishes {toggle, timestamp, hwid, dip, lane} on each flip;
// it does not publish a synthesized READY/IDLE/GO state.

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
  let toggleUp = false;  // physical switch position; true = UP

  const ui = {
    raceState: document.getElementById('race-state'),
    pinny: document.getElementById('pinny'),
    led: document.getElementById('lane-led'),
    toggle: document.getElementById('ready-toggle'),
  };

  function setLed(color) {
    ui.led.dataset.color = color;
  }

  function renderToggle() {
    ui.toggle.dataset.position = toggleUp ? 'up' : 'down';
    ui.toggle.setAttribute('aria-checked', toggleUp ? 'true' : 'false');
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
      readyToRace: toggleUp,
      toggle: toggleUp,
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

  function publishToggle(client) {
    // Mirrors finishtimer.py toggle_callback payload exactly.
    VirtualCommon.publish(client, stateTopic, {
      toggle: toggleUp,
      timestamp: Math.floor(Date.now() / 1000),
      hwid: hwid,
      dip: dip,
      lane: lane,
    }, { qos: 2, retain: true });
  }

  function flipToggle(client) {
    toggleUp = !toggleUp;
    renderToggle();
    publishToggle(client);
  }

  function onMessage(topic, payload) {
    if (topic === raceStateTopic) {
      raceState = (typeof payload === 'string') ? payload
                  : (payload.state || JSON.stringify(payload));
      ui.raceState.textContent = raceState;
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

    renderToggle();
    ui.toggle.addEventListener('click', () => flipToggle(client));
  }

  main().catch((e) => {
    VirtualCommon.log('sys', '', 'init error: ' + e.message);
    document.body.classList.add('vd-init-failed');
    alert('Virtual finish timer init failed: ' + e.message);
  });
})();
