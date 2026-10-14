// Headless screenshot harness for visual verification.
// usage: node tools/shot.mjs <url> <out.png> [script.js] [w] [h]
// The optional script is evaluated in the page after load (can return a promise).
import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
import { browserOptions } from './browser.mjs';

const [, , url = 'http://127.0.0.1:5178/', out = 'shot.png', scriptFile, w = '1440', h = '810'] = process.argv;
const browser = await puppeteer.launch({
  ...browserOptions(),
});
const page = await browser.newPage();
await page.setViewport({ width: +w, height: +h, deviceScaleFactor: 1 });
const logs = [];
page.on('console', (m) => logs.push('[' + m.type() + '] ' + m.text()));
page.on('pageerror', (e) => logs.push('[pageerror] ' + e.message));
await page.goto(url, { waitUntil: 'networkidle0', timeout: 120000 });
await page.waitForFunction(() => document.getElementById('loader')?.classList.contains('done'), { timeout: 120000 }).catch(() => logs.push('[timeout] loader not done'));
await new Promise((r) => setTimeout(r, 2600));
if (scriptFile) {
  const src = fs.readFileSync(scriptFile, 'utf8');
  const res = await page.evaluate(`(async () => { ${src} })()`).catch((e) => 'script error: ' + e.message);
  if (res !== undefined) logs.push('[script] ' + JSON.stringify(res));
}
await page.screenshot({ path: out });
console.log(logs.join('\n'));
await browser.close();
