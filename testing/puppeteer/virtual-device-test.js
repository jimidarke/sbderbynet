// virtual-device-test.js
//
// Smoke test for the cloud-twin browser virtual hardware. Verifies that the
// virtual control panel and individual device pages render and reach a
// connected MQTT state when run against a live cloud stack.
//
// Usage:
//     node virtual-device-test.js https://<cloud-host>/derbynet
//
// Requires:
//   - The cloud stack running (DERBYNET_CLOUD_MODE=public, virtual-device
//     MQTT user provisioned, Caddy proxying /mqtt to mosquitto:9001).
//   - A coordinator session cookie OR basic-auth credentials available
//     in the BASE_URL (e.g. https://user:pw@host/derbynet) — fall back to
//     unauthenticated GET, which will see the 403 guard page.
//
// This is a smoke check, not a full race-equivalence test. Use
// testing/replay-real-race.py for that.

const assert = require('./assert.js');
const puppeteer = require('puppeteer');

let root = process.argv[2] || 'http://localhost/derbynet';
if (root.endsWith('/')) root = root.slice(0, -1);

(async function main() {
  const browser = await puppeteer.launch({
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });
  let failed = 0;

  async function expectConnected(page, label) {
    // Wait up to 20s for the on-page MQTT client to reach connected state.
    try {
      await page.waitForFunction(
        () => document.getElementById('conn-status')
              && document.getElementById('conn-status').dataset.state === 'connected',
        { timeout: 20000 },
      );
      console.log(`  [${label}] connected`);
    } catch (e) {
      console.error(`  [${label}] FAILED to connect within 20s`);
      const html = await page.content();
      if (html.includes('403') || html.includes('404')) {
        console.error('    page returned a guard error — check auth/cloud mode');
      }
      failed += 1;
    }
  }

  // 1. Index page
  console.log('Test 1: virtual/index.php loads');
  let page = await browser.newPage();
  const indexResp = await page.goto(root + '/virtual/index.php',
                                    { waitUntil: 'domcontentloaded' });
  if (!indexResp || indexResp.status() !== 200) {
    console.error('  FAIL: index returned ' + (indexResp ? indexResp.status() : 'null'));
    console.error('  Skipping remaining tests — cloud guard or auth blocked the page.');
    await browser.close();
    process.exit(1);
  }
  const cardCount = await page.$$eval('.vd-index-card', els => els.length);
  assert.equal(true, cardCount >= 5, 'expected at least 5 device cards');
  console.log(`  PASS (${cardCount} device cards)`);

  // 2. Each finish timer connects
  for (const lane of [1, 2, 3]) {
    console.log(`Test 2.${lane}: finish-timer.php?lane=${lane} connects`);
    const p = await browser.newPage();
    await p.goto(root + '/virtual/finish-timer.php?lane=' + lane,
                 { waitUntil: 'domcontentloaded' });
    await expectConnected(p, 'finish lane ' + lane);
    await p.close();
  }

  // 3. Start timer connects
  console.log('Test 3: start-timer.php connects');
  const ps = await browser.newPage();
  await ps.goto(root + '/virtual/start-timer.php',
                { waitUntil: 'domcontentloaded' });
  await expectConnected(ps, 'start');
  await ps.close();

  // 4. LED sign and display present and connect
  console.log('Test 4: led-sign.php?zone=starter connects');
  const pl = await browser.newPage();
  await pl.goto(root + '/virtual/led-sign.php?zone=starter',
                { waitUntil: 'domcontentloaded' });
  await expectConnected(pl, 'ledsign starter');
  await pl.close();

  await browser.close();

  if (failed) {
    console.error(`\n${failed} virtual-device test(s) failed`);
    process.exit(1);
  }
  console.log('\n============= Virtual-device smoke tests passed =============');
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
