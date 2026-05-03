// virtual-start-timer.js
//
// Browser start timer. Wire-compatible with extras/soapbox/infra/starttimer/
// (ESP32, MicroPython). The real device is just a latching push-button on
// a GPIO: when the signal goes HIGH it publishes {state:'GO'}, when it
// returns LOW it publishes {state:'STOP'}. The user has to press the
// button again to release the latch — this virtual mirrors that exactly.

(function () {
  const hwid = 'starttimer';
  const dip = '0001';
  const stateTopic     = 'derbynet/device/' + hwid + '/state';
  const telemetryTopic = 'derbynet/device/' + hwid + '/telemetry';
  const statusTopic    = 'derbynet/device/' + hwid + '/status';
  const raceStateTopic = 'derbynet/race/state';

  let raceState = 'UNCONFIGURED';
  let latched = false; // mirrors start_signal pin: HIGH = GO, LOW = STOP

  const ui = {
    raceState: document.getElementById('race-state'),
    signal: document.getElementById('signal-state'),
    btn: document.getElementById('btn-latch'),
    label: document.getElementById('latch-label'),
  };

  function renderLatch() {
    ui.btn.dataset.latched = latched ? 'true' : 'false';
    ui.btn.setAttribute('aria-checked', latched ? 'true' : 'false');
    ui.label.textContent = latched ? 'GO' : 'START';
    ui.signal.textContent = latched ? 'HIGH' : 'LOW';
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
      state: latched ? 1 : 0,
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
    setInterval(send, 5000); // real ESP32 publishes ~5s telemetry
  }

  function publishLatchEdge(client) {
    // Mirrors starttimer/src/main.py send_mqtt_message():
    // edge HIGH → 'GO', edge LOW → 'STOP'. Retained, on its own topic.
    VirtualCommon.publish(client, stateTopic, {
      state: latched ? 'GO' : 'STOP',
      timestamp: Math.floor(Date.now() / 1000),
      hwid: hwid,
      dip: dip,
    }, { qos: 2, retain: true });
  }

  function pressButton(client) {
    latched = !latched;
    renderLatch();
    publishLatchEdge(client);
  }

  function onMessage(topic, payload) {
    if (topic === raceStateTopic) {
      raceState = (typeof payload === 'string') ? payload
                  : (payload.state || JSON.stringify(payload));
      ui.raceState.textContent = raceState;
    }
  }

  async function main() {
    const clientId = 'b_start_' + Math.random().toString(36).slice(2, 8);
    const client = await VirtualCommon.connectBroker({
      clientId: clientId,
      will: { topic: statusTopic, payload: 'offline', qos: 1, retain: true },
      onConnect: (c) => {
        c.subscribe(raceStateTopic, { qos: 1 });
        c.publish(statusTopic, 'online', { qos: 1, retain: true });
        startTelemetry(c);
      },
      onMessage: onMessage,
    });
    VirtualCommon.wireVisibilityOffline(client, statusTopic);

    renderLatch();
    ui.btn.addEventListener('click', () => pressButton(client));
  }

  main().catch((e) => {
    VirtualCommon.log('sys', '', 'init error: ' + e.message);
    alert('Virtual start timer init failed: ' + e.message);
  });
})();
