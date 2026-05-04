// virtual-start-timer.js
//
// Browser start timer. Wire-compatible with extras/soapbox/infra/starttimer/
// (ESP32, MicroPython). The real device is just a latching push-button on
// a GPIO: when the signal goes HIGH it publishes {state:'GO'}, when it
// returns LOW it publishes {state:'STOP'}. The user has to press the
// button again to release the latch — this virtual mirrors that exactly.
//
// Exposed as a factory on window.VirtualStart.mount({root, client, hwid, dip})
// so the combined index pane drives all devices on one MQTT client.

(function (global) {
  function mount(opts) {
    const root = opts.root;
    const client = opts.client;
    // Cloud broker ACL enumerates allowed topics literally; the real-device
    // hostname 'starttimer' would be rejected. We keep hwid 'START' (matching
    // the cloud ACL) and rely on derbyRace.py's wildcard subscription on
    // derbynet/device/+/state to consume the GO edge regardless.
    const hwid = opts.hwid || 'START';
    const dip = opts.dip || '0001';

    const stateTopic     = 'derbynet/device/' + hwid + '/state';
    const telemetryTopic = 'derbynet/device/' + hwid + '/telemetry';
    const statusTopic    = 'derbynet/device/' + hwid + '/status';
    const raceStateTopic = 'derbynet/race/state';

    let raceState = 'UNCONFIGURED';
    let latched = false; // mirrors start_signal pin: HIGH = GO, LOW = STOP

    const ui = {
      raceState: root.querySelector('[data-role="race-state"]') || root.querySelector('#race-state'),
      signal:    root.querySelector('[data-role="signal-state"]') || root.querySelector('#signal-state'),
      btn:       root.querySelector('[data-role="btn-latch"]') || root.querySelector('#btn-latch'),
      label:     root.querySelector('[data-role="latch-label"]') || root.querySelector('#latch-label'),
    };

    function renderLatch() {
      ui.btn.dataset.latched = latched ? 'true' : 'false';
      ui.btn.setAttribute('aria-checked', latched ? 'true' : 'false');
      ui.label.textContent = latched ? 'GO' : 'START';
      if (ui.signal) ui.signal.textContent = latched ? 'HIGH' : 'LOW';
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

    let telemetryHandle = null;
    function startTelemetry() {
      const send = () => {
        if (client.connected) {
          VirtualCommon.publish(client, telemetryTopic, buildTelemetry(),
                                { qos: 0, retain: true });
        }
      };
      send();
      telemetryHandle = setInterval(send, 5000); // real ESP32 publishes ~5s
    }

    function publishLatchEdge() {
      // Mirrors starttimer/src/main.py send_mqtt_message():
      // edge HIGH → 'GO', edge LOW → 'STOP'. Retained, on its own topic.
      VirtualCommon.publish(client, stateTopic, {
        state: latched ? 'GO' : 'STOP',
        timestamp: Math.floor(Date.now() / 1000),
        hwid: hwid,
        dip: dip,
      }, { qos: 2, retain: true });
    }

    function pressButton() {
      latched = !latched;
      renderLatch();
      publishLatchEdge();
    }

    function onMessage(topic, payload) {
      if (topic === raceStateTopic) {
        raceState = (typeof payload === 'string') ? payload
                    : (payload.state || JSON.stringify(payload));
        if (ui.raceState) ui.raceState.textContent = raceState;
      }
    }

    function onConnected() {
      client.subscribe(raceStateTopic, { qos: 1 });
      client.publish(statusTopic, 'online', { qos: 1, retain: true });
      startTelemetry();
    }

    renderLatch();
    ui.btn.addEventListener('click', pressButton);
    // Caller is responsible for invoking onConnected() once the client's
    // 'connect' event fires (and again on each reconnect if telemetry/online
    // re-publish is desired).

    return {
      hwid: hwid,
      statusTopic: statusTopic,
      subscriptions: [{ topic: raceStateTopic, qos: 1 }],
      onConnected: onConnected,
      onMessage: onMessage,
      teardown: function () {
        if (telemetryHandle) clearInterval(telemetryHandle);
        ui.btn.removeEventListener('click', pressButton);
      },
    };
  }

  global.VirtualStart = { mount: mount };
})(window);
