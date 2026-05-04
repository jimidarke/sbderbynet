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
//
// Exposed as a factory on window.VirtualFinish.mount({root, client, lane,
// hwid, dip}). The combined index pane mounts one per lane against the
// single shared MQTT client.

(function (global) {
  function mount(opts) {
    const root = opts.root;
    const client = opts.client;
    const lane = parseInt(opts.lane, 10);
    const dip = opts.dip;
    const hwid = opts.hwid;

    const stateTopic     = 'derbynet/device/' + hwid + '/state';
    const telemetryTopic = 'derbynet/device/' + hwid + '/telemetry';
    const statusTopic    = 'derbynet/device/' + hwid + '/status';
    const raceStateTopic = 'derbynet/race/state';
    const ledTopic       = 'derbynet/lane/' + lane + '/led';
    const pinnyTopic     = 'derbynet/lane/' + lane + '/pinny';

    let raceState = 'UNCONFIGURED';
    let toggleUp = false;  // physical switch position; true = UP

    const ui = {
      raceState: root.querySelector('[data-role="race-state"]') || root.querySelector('#race-state'),
      pinny:     root.querySelector('[data-role="pinny"]')      || root.querySelector('#pinny'),
      led:       root.querySelector('[data-role="lane-led"]')   || root.querySelector('#lane-led'),
      toggle:    root.querySelector('[data-role="ready-toggle"]') || root.querySelector('#ready-toggle'),
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

    let telemetryHandle = null;
    function startTelemetry() {
      const send = () => {
        if (client.connected) {
          VirtualCommon.publish(client, telemetryTopic, buildTelemetry(),
                                { qos: 0, retain: true });
        }
      };
      send();
      telemetryHandle = setInterval(send, 1000);
    }

    function publishToggle() {
      // Mirrors finishtimer.py toggle_callback payload exactly.
      VirtualCommon.publish(client, stateTopic, {
        toggle: toggleUp,
        timestamp: Math.floor(Date.now() / 1000),
        hwid: hwid,
        dip: dip,
        lane: lane,
      }, { qos: 2, retain: true });
    }

    function flipToggle() {
      toggleUp = !toggleUp;
      renderToggle();
      publishToggle();
    }

    function onMessage(topic, payload) {
      if (topic === raceStateTopic) {
        raceState = (typeof payload === 'string') ? payload
                    : (payload.state || JSON.stringify(payload));
        if (ui.raceState) ui.raceState.textContent = raceState;
      } else if (topic === ledTopic) {
        setLed(typeof payload === 'string' ? payload : (payload.color || 'off'));
      } else if (topic === pinnyTopic) {
        const v = (typeof payload === 'string') ? payload
                  : (payload.pinny || JSON.stringify(payload));
        if (ui.pinny) ui.pinny.textContent = v;
      }
    }

    function onConnected() {
      client.subscribe(raceStateTopic, { qos: 1 });
      client.subscribe(ledTopic, { qos: 1 });
      client.subscribe(pinnyTopic, { qos: 1 });
      client.publish(statusTopic, 'online', { qos: 1, retain: true });
      startTelemetry();
    }

    renderToggle();
    ui.toggle.addEventListener('click', flipToggle);
    // Caller fires onConnected() on the client's 'connect' event.

    return {
      hwid: hwid,
      lane: lane,
      statusTopic: statusTopic,
      subscriptions: [
        { topic: raceStateTopic, qos: 1 },
        { topic: ledTopic, qos: 1 },
        { topic: pinnyTopic, qos: 1 },
      ],
      ledTopic: ledTopic,
      pinnyTopic: pinnyTopic,
      onConnected: onConnected,
      onMessage: onMessage,
      teardown: function () {
        if (telemetryHandle) clearInterval(telemetryHandle);
        ui.toggle.removeEventListener('click', flipToggle);
      },
    };
  }

  global.VirtualFinish = { mount: mount };
})(window);
