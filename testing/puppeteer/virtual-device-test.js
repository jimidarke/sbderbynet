// virtual-device-test.js
//
// Smoke test for the cloud-twin browser virtual hardware. Verifies that the
// combined virtual control panel renders, the single MQTT client reaches a
// connected state, and one chassis per device (start + each finish lane) is
// present. There is exactly one entry point — /virtual/ — that drives the
// whole rig in a single pane.
//
// Usage:
//     node virtual-device-test.js https://<cloud-host>/derbynet
//
// Requires:
//   - The cloud stack running (DERBYNET_CLOUD_MODE=public, virtual-device
//     MQTT user provisioned, Caddy proxying /mqtt to mosquitto:9001).
//   - A coordinator session cookie OR basic-auth credentials available
//     in the BASE_URL (e.g. https://user:pw@host/derbynet).

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

  console.log('Test 1: combined /virtual/ loads and renders all chassis');
  const page = await browser.newPage();
  const resp = await page.goto(root + '/virtual/',
                               { waitUntil: 'domcontentloaded' });
  if (!resp || resp.status() !== 200) {
    console.error('  FAIL: status ' + (resp ? resp.status() : 'null'));
    await browser.close();
    process.exit(1);
  }
  const startCount = await page.$$eval('.vd-combined-start', els => els.length);
  const finishCount = await page.$$eval('.vd-combined-finish', els => els.length);
  assert.equal(1, startCount, 'expected one start chassis');
  assert.equal(true, finishCount >= 3, 'expected at least three finish chassis');
  console.log(`  PASS (${startCount} start + ${finishCount} finish chassis)`);

  console.log('Test 2: shared MQTT client reaches connected state');
  await expectConnected(page, 'combined');

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
