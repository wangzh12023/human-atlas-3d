// Geometry and browser regression checks for the shared male/female build.
// Usage: node tools/verify-shape.mjs [url]
import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { browserOptions } from './browser.mjs';

const out = path.join(path.dirname(fileURLToPath(import.meta.url)), 'qa');
fs.mkdirSync(out, { recursive: true });
const browser = await puppeteer.launch(browserOptions());
const errors = [];
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1000, deviceScaleFactor: 1 });
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(process.argv[2] || 'http://127.0.0.1:5179/', { waitUntil: 'networkidle0' });
  await page.waitForFunction(() => document.getElementById('loader')?.classList.contains('done'));
  await new Promise(r => setTimeout(r, 2300));

  const geometry = await page.evaluate(() => {
    const { atlas } = window.__atlas;
    let sharedVertices = 0, mismatches = 0;
    for (const mesh of atlas.meshes) {
      const { aPM, aPF, aPid } = mesh.geometry.attributes;
      for (let i = 0; i < aPM.count; i++) {
        const p = atlas.pieces[aPid.getX(i)];
        if (p.x || p.en === 'Skin') continue;
        sharedVertices++;
        if (aPM.getX(i) !== aPF.getX(i) || aPM.getY(i) !== aPF.getY(i) || aPM.getZ(i) !== aPF.getZ(i)) mismatches++;
      }
    }
    return { pieces: atlas.pieces.length, sharedVertices, mismatches };
  });
  if (geometry.mismatches || !geometry.sharedVertices) throw Error(JSON.stringify(geometry));

  async function shot(name, sex, target, yaw = 0, pitch = 0.03, dist, skin = false) {
    await page.evaluate(async (settings) => {
      const { ui, rig, THREE } = window.__atlas;
      ui.closeRegion(false);
      ui.setSex(settings.sex);
      ui.setPreset('all');
      ui.sysOn.integument = settings.skin;
      ui.applyVisibility();
      document.querySelectorAll('.hotspot').forEach(el => el.style.display = 'none');
      await rig.flyTo({ target: new THREE.Vector3(...settings.target), yaw: settings.yaw,
                       pitch: settings.pitch, dist: settings.dist }, 0.1);
      await new Promise(r => setTimeout(r, 2500));
    }, { sex, target, yaw, pitch, dist, skin });
    await page.screenshot({ path: path.join(out, name + '.png') });
  }
  await shot('male-front', 'male', [0, 870, 0], 0, 0.03, 4330);
  await shot('female-front', 'female', [0, 870, 0], 0, 0.03, 4330);
  await shot('female-chest', 'female', [0, 1290, 140], 0.5, 0.08, 1450);
  await shot('female-side', 'female', [0, 1290, 140], Math.PI / 2, 0.02, 1250);
  await shot('female-skin', 'female', [0, 870, 0], 0.3, 0.03, 4330, true);
  await shot('female-chest-skin', 'female', [0, 1290, 140], 0.5, 0.1, 1250, true);
  await shot('female-back', 'female', [0, 870, 0], Math.PI, 0.03, 4330);
  await shot('female-foot', 'female', [0, 60, 65], 0.35, 0.65, 1000);

  const picking = await page.evaluate(async () => {
    const { ui, rig, atlas, THREE, camera } = window.__atlas;
    ui.sysOn.integument = false;
    ui.applyVisibility();
    await rig.flyTo({ target: new THREE.Vector3(0, 1280, 150), yaw: 0, pitch: 0, dist: 1300 }, 0.1);
    await new Promise(r => setTimeout(r, 800));
    const nipple = atlas.pieces.find(p => p.en === 'Left Nipple');
    const pos = atlas.pieceCenter(nipple.idx).project(camera);
    // project() already includes the camera's view offset.
    const screenX = (pos.x + 1) * innerWidth / 2;
    const screenY = (1 - pos.y) * innerHeight / 2;
    const id = atlas.pick(camera, screenX, screenY, innerWidth, innerHeight);
    return { expected: nipple.en, picked: atlas.pieces[id]?.en };
  });
  if (picking.expected !== picking.picked) throw Error('Picking mismatch: ' + JSON.stringify(picking));

  for (const id of ['breast', 'female_repro']) {
    await page.evaluate(async id => {
      const { ui, rig } = window.__atlas;
      ui.openRegion(id, { duration: 0.1, orbit: false });
      await new Promise(r => setTimeout(r, 1000));
      rig.autoRotate = false;
    }, id);
    await page.screenshot({ path: path.join(out, 'region-' + id + '.png') });
  }
  // Toggle repeatedly: no gender-exclusive structures may leak into the other sex.
  const visibility = await page.evaluate(async () => {
    const { ui, atlas } = window.__atlas;
    ui.closeRegion(false);
    for (const sex of ['male', 'female', 'male', 'female']) {
      ui.setSex(sex);
      await new Promise(r => setTimeout(r, 600));
      if (atlas.pieces.some(p => !ui.sexAllows(p) && atlas.tgt.vis[p.idx] > 0)) return false;
    }
    return true;
  });
  if (!visibility || errors.length) throw Error(JSON.stringify({ visibility, errors }));
  console.log(JSON.stringify({ geometry, picking, visibility, errors, screenshots: out }, null, 2));
} finally {
  await browser.close();
}
