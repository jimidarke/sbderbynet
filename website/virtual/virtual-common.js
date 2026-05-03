// virtual-common.js
//
// Shared helpers for browser virtual hardware pages.
// All pages use MQTT.js (loaded via CDN) and the cred endpoint at
// POST /derbynet/action.php with action=virtual-mqtt-creds.
//
// Cloud-only: pages are guarded server-side by website/virtual/_guard.inc.

(function (global) {
  const log_max = 50;

  // Load MQTT.js. Prefer the vendored copy at /derbynet/js/vendor/mqtt.min.js
  // so the page keeps working when unpkg.com is unreachable (race-day venue
  // WiFi, CDN outage, blocked DNS). Fall back to unpkg only if the local
  // file is missing — pinned to the same version as the README.
  let _mqttPromise = null;
  function ensureMqtt() {
    if (typeof global.mqtt !== 'undefined') return Promise.resolve();
    if (_mqttPromise) return _mqttPromise;

    function loadScript(src) {
      return new Promise((resolve, reject) => {
        const s = document.createElement('script');
        s.src = src;
        s.onload = () => resolve();
        s.onerror = () => reject(new Error('failed: ' + src));
        document.head.appendChild(s);
      });
    }

    _mqttPromise = loadScript('/derbynet/js/vendor/mqtt.min.js')
      .catch((e) => {
        logEvent('sys', '', 'vendored mqtt.min.js missing — falling back to unpkg');
        return loadScript('https://unpkg.com/mqtt@5.10.1/dist/mqtt.min.js');
      });
    return _mqttPromise;
  }

  function logEvent(direction, topic, payload) {
    const ol = document.getElementById('mqtt-log');
    if (!ol) return;
    const li = document.createElement('li');
    li.className = 'log-' + direction;
    const t = new Date().toISOString().substr(11, 12);
    let body = payload;
    if (typeof payload === 'object') body = JSON.stringify(payload);
    if (body && body.length > 120) body = body.substr(0, 120) + '…';
    li.textContent = t + ' ' + direction + ' ' + topic + ' ' + (body || '');
    ol.insertBefore(li, ol.firstChild);
    while (ol.children.length > log_max) ol.removeChild(ol.lastChild);
  }

  function setConnState(state) {
    const el = document.getElementById('conn-status');
    if (!el) return;
    el.dataset.state = state;
    el.textContent = state;
  }

  async function fetchCreds() {
    // action.php dispatches POST as actions and GET as queries — sending
    // GET ?action=... falls through to the empty-query branch and fails as
    // "Unrecognized query". Use POST with form-encoded body.
    const url = '/derbynet/action.php';
    const res = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: 'action=virtual-mqtt-creds',
    });
    if (!res.ok) {
      throw new Error('Cred endpoint HTTP ' + res.status);
    }
    const data = await res.json();
    if (!data.outcome || data.outcome.code !== 'success') {
      throw new Error('Cred endpoint failed: '
                      + (data.outcome ? data.outcome.description : 'unknown'));
    }
    return data.credentials;
  }

  async function connectBroker(opts) {
    await ensureMqtt();
    const creds = await fetchCreds();
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = proto + '//' + location.host + creds.broker_path;

    const client = mqtt.connect(url, {
      username: creds.user,
      password: creds.pass,
      clientId: opts.clientId,
      keepalive: 30,
      reconnectPeriod: 2000,
      clean: true,
      will: opts.will || undefined,
    });

    client.on('connect', () => {
      setConnState('connected');
      logEvent('sys', '', 'connected as ' + opts.clientId);
      if (opts.onConnect) opts.onConnect(client);
    });
    client.on('reconnect', () => setConnState('reconnecting'));
    client.on('close', () => setConnState('disconnected'));
    client.on('error', (e) => {
      logEvent('sys', '', 'error ' + e.message);
      setConnState('error');
    });
    client.on('message', (topic, payload) => {
      let parsed = payload.toString();
      try { parsed = JSON.parse(parsed); } catch (_) {}
      logEvent('rx', topic, parsed);
      if (opts.onMessage) opts.onMessage(topic, parsed);
    });

    return client;
  }

  function publish(client, topic, payload, options) {
    const body = (typeof payload === 'string') ? payload : JSON.stringify(payload);
    client.publish(topic, body, options || {});
    logEvent('tx', topic, payload);
  }

  // Hook visibility: when the tab is hidden we explicitly publish offline so
  // the race server doesn't keep the device green just because LWT hasn't
  // fired yet. When it returns, the device's reconnect/online flow runs.
  function wireVisibilityOffline(client, statusTopic) {
    document.addEventListener('visibilitychange', () => {
      if (document.hidden && client && client.connected) {
        client.publish(statusTopic, 'offline', { qos: 1, retain: true });
        logEvent('tx', statusTopic, 'offline (hidden)');
      } else if (!document.hidden && client && client.connected) {
        client.publish(statusTopic, 'online', { qos: 1, retain: true });
        logEvent('tx', statusTopic, 'online (visible)');
      }
    });
  }

  global.VirtualCommon = {
    log: logEvent,
    setConnState: setConnState,
    connectBroker: connectBroker,
    publish: publish,
    wireVisibilityOffline: wireVisibilityOffline,
  };
})(window);
