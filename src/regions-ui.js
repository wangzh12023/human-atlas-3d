import * as THREE from 'three';
import { SYSTEMS } from './engine/atlas.js';
import { REGION_DEFS, REGION_GROUPS } from './regions-def.js';

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const stripSide = (en) => en.replace(/^(Left|Right)\s+/, '');
const isRight = (p) => /\bright\b/i.test(p.en) || (p.cM[0] < -15 && !/\bleft\b/i.test(p.en));
const isLeft = (p) => /\bleft\b/i.test(p.en) || (p.cM[0] > 15 && !/\bright\b/i.test(p.en));

/**
 * Installs region ("部位特写") behaviour on the UI instance:
 * list + filter chips, region card, camera choreography, hotspots, auto orbit.
 */
export function installRegions(ui, REGIONS) {
  const atlas = ui.atlas, rig = ui.rig;
  const P = atlas.pieces;
  const regions = REGIONS.map((r) => ({ ...r, def: REGION_DEFS[r.id] || { match: [], show: [] } }));
  let group = 'all';
  let current = null; // region object
  let saved = null;   // view state to restore
  let orbitTimer = null;

  // ---------------------------------------------------------------- piece resolution
  const resolve = (res) => P.filter((p) => res.some((re) => re.test(p.en))).map((p) => p.idx);
  for (const r of regions) {
    const d = r.def;
    r.ids = resolve(d.match || []);
    r.ctx = resolve(d.context || []).filter((i) => !r.ids.includes(i));
    r.ghostIds = resolve(d.ghost || []);
    if (d.nervousOnlyBrain) r.ids = r.ids.filter((i) => P[i].cM[1] > 1450);
  }

  // ---------------------------------------------------------------- list
  const groupsEl = $('regionGroups');
  groupsEl.innerHTML = REGION_GROUPS.map((g) => `<button data-g="${g.id}" class="${g.id === 'all' ? 'active' : ''}">${g.zh}</button>`).join('');
  groupsEl.addEventListener('click', (e) => {
    const b = e.target.closest('button[data-g]');
    if (!b) return;
    group = b.dataset.g;
    for (const x of groupsEl.children) x.classList.toggle('active', x === b);
    renderList();
  });

  const allowed = (r) => !r.sex || r.sex === 'both' || r.sex === ui.sex;
  function renderList() {
    const ul = $('regionList');
    const list = regions.filter((r) => allowed(r) && (group === 'all' || r.group === group));
    $('regionCount').textContent = regions.filter(allowed).length;
    ul.innerHTML = list.map((r) => {
      const n = regions.filter(allowed).indexOf(r) + 1;
      const sexTag = r.sex === 'male' ? '♂' : r.sex === 'female' ? '♀' : '';
      return `<li data-id="${r.id}" class="${current && current.id === r.id ? 'active' : ''}"><span class="rnum">${String(n).padStart(2, '0')}</span><span class="rtext"><span class="rname">${esc(r.zh)}</span><span class="rtag">${esc(r.tagline || r.en)}</span></span><span class="rsex">${sexTag}</span></li>`;
    }).join('');
  }
  $('regionList').addEventListener('click', (e) => {
    const li = e.target.closest('li[data-id]');
    if (li) ui.openRegion(li.dataset.id);
  });

  // ---------------------------------------------------------------- card
  function renderCard(r) {
    $('rcGroup').textContent = `部位特写 · ${({ upper: '上肢', trunk: '躯干', lower: '下肢', organs: '器官', repro: '生殖健康' })[r.group] || 'Close-up'}`;
    $('rcTitle').textContent = r.zh;
    $('rcSub').textContent = r.en + (r.tagline ? ' · ' + r.tagline : '');
    // structure chips: unique base names, both sides grouped
    const seen = new Map();
    for (const i of r.ids) {
      const p = P[i];
      if (!ui.sexAllows(p)) continue;
      const k = p.s + '|' + stripSide(p.en);
      if (!seen.has(k)) seen.set(k, { ids: [], p });
      seen.get(k).ids.push(i);
    }
    const chips = [...seen.values()].sort((a, b) => b.p.size - a.p.size).slice(0, 28);
    r.chipGroups = chips;
    const sec = (title, inner) => `<div class="rc-sec"><h4>${title}</h4>${inner}</div>`;
    let html = '';
    html += `<div class="rc-sec"><p>${esc(r.summary)}</p></div>`;
    if (r.sports?.length) html += sec('相关运动 · Sports', `<div class="tags">${r.sports.map((s) => `<span>${esc(s)}</span>`).join('')}</div>`);
    if (chips.length) html += sec(`关键结构 · Structures <span style="font-weight:500;letter-spacing:0">（${chips.length}）</span>`,
      `<div class="struct-chips">${chips.map((c, k) => `<button data-k="${k}"><i style="background:${SYSTEMS[c.p.s].dot}"></i>${esc(c.p.zh.replace(/^[左右]/, ''))}</button>`).join('')}</div>`);
    if (r.keyPoints?.length) html += sec('解剖要点 · Key points', `<ul>${r.keyPoints.map((t) => `<li>${esc(t)}</li>`).join('')}</ul>`);
    if (r.injuries?.length) html += sec(r.group === 'repro' ? '常见健康问题 · Health' : '常见损伤 · Injuries', `<ul>${r.injuries.map((t) => `<li><b>${esc(t.name)}</b>：${esc(t.desc)}</li>`).join('')}</ul>`);
    if (r.training?.length) html += sec(r.group === 'repro' ? '保健建议 · Care' : '训练与预防 · Training', `<ul>${r.training.map((t) => `<li>${esc(t)}</li>`).join('')}</ul>`);
    if (r.funFact) html += sec('你知道吗 · Did you know', `<div class="fun">${esc(r.funFact)}</div>`);
    html += `<p class="insp-note" style="margin-top:14px">科普内容仅供参考，不能替代专业医疗建议。</p>`;
    $('rcBody').innerHTML = html;
    $('rcBody').scrollTop = 0;
  }
  $('rcBody').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-k]');
    if (!b || !current) return;
    const c = current.chipGroups[+b.dataset.k];
    ui.select(c.ids[0], { group: c.ids });
    for (const i of c.ids) atlas.setTarget('dim', i, 0);
    ui.focusPieces(c.ids, { fill: 0.45, yaw: rig.goal.yaw, pitch: rig.goal.pitch });
  });

  // ---------------------------------------------------------------- framing
  function regionBox(r) {
    const d = r.def;
    let ids = r.ids.filter((i) => ui.sexAllows(P[i]));
    if (d.side === 'R') { const s = ids.filter((i) => isRight(P[i])); if (s.length) ids = s; }
    if (d.side === 'L') { const s = ids.filter((i) => isLeft(P[i])); if (s.length) ids = s; }
    const box = new THREE.Box3(), tmp = new THREE.Box3();
    for (const i of ids) box.union(atlas.pieceBox(i, tmp, ui.morphTarget));
    // special boxes for joints (the long bones would otherwise dominate)
    if (d.box) {
      const c = box.getCenter(new THREE.Vector3());
      const sexF = ui.sex === 'female';
      const kneeY = sexF ? 470 : 500;
      const special = {
        knee: () => joint(/patella$/i, d.side, 150, 200),
        ankle: () => joint(/talus/i, d.side, 150, 140),
        achilles: () => { const j = jointCenter(/calcaneus/i, d.side); return new THREE.Box3().setFromCenterAndSize(j.add(new THREE.Vector3(0, 120, -20)), new THREE.Vector3(120, 330, 150)); },
        chest: () => new THREE.Box3().setFromCenterAndSize(new THREE.Vector3(0, 1290, 20), new THREE.Vector3(320, 330, 220)),
        pelvis: () => new THREE.Box3().setFromCenterAndSize(new THREE.Vector3(0, 900, 30), new THREE.Vector3(240, 240, 200)),
        // organ-centred boxes so the camera aims at the genital organs, not the whole pelvis
        fpelvis: () => boxOf(/uterus|ovary$|uterine tube|^vagina$|^clitoris$|vestibular bulb|labium/i, 1.2),
        mpelvis: () => boxOf(/testis|epididymis|prostate|seminal vesicle|of penis$|glans penis|scrotum/i, 1.15),
        breast: () => boxOf(/left (mammary|breast adipose|nipple|areola)/i, 1.35),
      };
      if (special[d.box]) return special[d.box]();
      void c; void kneeY;
    }
    return box;
  }
  function boxOf(re, grow = 1.2) {
    const box = new THREE.Box3(), tmp = new THREE.Box3();
    for (const p of P) if (re.test(p.en) && ui.sexAllows(p)) box.union(atlas.pieceBox(p.idx, tmp, ui.morphTarget));
    if (box.isEmpty()) return new THREE.Box3().setFromCenterAndSize(new THREE.Vector3(0, 900, 60), new THREE.Vector3(200, 200, 200));
    const c = box.getCenter(new THREE.Vector3()), s = box.getSize(new THREE.Vector3()).multiplyScalar(grow);
    return new THREE.Box3().setFromCenterAndSize(c, s);
  }
  function jointCenter(re, side) {
    const cands = P.filter((p) => re.test(p.en) && (side === 'R' ? isRight(p) : side === 'L' ? isLeft(p) : true));
    const box = new THREE.Box3(), tmp = new THREE.Box3();
    for (const p of cands) box.union(atlas.pieceBox(p.idx, tmp, ui.morphTarget));
    return box.getCenter(new THREE.Vector3());
  }
  function joint(re, side, w, h) {
    return new THREE.Box3().setFromCenterAndSize(jointCenter(re, side), new THREE.Vector3(w, h, w));
  }

  // ---------------------------------------------------------------- open / close
  ui.openRegion = (id, opts = {}) => {
    const r = regions.find((x) => x.id === id);
    if (!r) return;
    if (!allowed(r)) {
      // switch sex automatically for sex-specific regions
      ui.setSex(r.sex);
    }
    stopOrbit();
    if (!current) {
      saved = { sysOn: { ...ui.sysOn } };
    }
    current = r; ui.region = r;
    ui.select(-1);
    ui.isolated = null;
    if (ui.explode > 0.001) ui.setExplode(0, true);
    // systems: show what the region needs
    for (const s of atlas.systems) ui.sysOn[s] = (r.def.show || []).includes(s);
    ui.applyVisibility();
    // dim everything outside the region, highlight region structures softly
    const keep = new Set([...r.ids, ...r.ctx]);
    for (const p of P) {
      atlas.setTarget('dim', p.idx, keep.has(p.idx) ? (r.ids.includes(p.idx) ? 0 : 0.55) : 0.9);
    }
    // ghost far-away pieces of visible systems for clarity (keeps context silhouette)
    const box = regionBox(r);
    const big = box.clone().expandByScalar(Math.max(140, box.getSize(new THREE.Vector3()).length() * 0.6));
    const tmp = new THREE.Box3();
    for (const p of P) {
      if (atlas.tgt.vis[p.idx] < 0.5) continue;
      const inside = big.intersectsBox(atlas.pieceBox(p.idx, tmp, ui.morphTarget));
      atlas.setTarget('ghost', p.idx, keep.has(p.idx) || inside ? 0 : 1);
    }
    // translucent outer layers (skin / breast fat) give the close-up its body outline
    for (const i of r.ghostIds) {
      if (!ui.sexAllows(P[i])) continue;
      atlas.setTarget('vis', i, 1);
      atlas.setTarget('ghost', i, 1);
    }
    renderCard(r);
    renderList();
    ui.showTab('regions');
    ui.collapsePanel && ui.collapsePanel();
    $('regionCard').hidden = false;
    $('inspector').hidden = true;
    const v = r.def.view || {};
    rig.autoRotate = false; $('autoRotate').classList.remove('active');
    ui.updateInsets();
    rig.frameBox(box, { yaw: v.yaw ?? 0, pitch: v.pitch ?? 0.05, fill: v.fill ?? 0.6, duration: opts.duration ?? 1.6 }).then(() => {
      if (current === r && opts.orbit !== false) startOrbitHint(r);
    });
    updateHotspots(true);
  };

  ui.closeRegion = (restoreView = true) => {
    if (!current) return;
    stopOrbit();
    current = null; ui.region = null;
    atlas.setAll('dim', 0);
    if (saved) { Object.assign(ui.sysOn, saved.sysOn); saved = null; }
    ui.isolated = null;
    ui.select(-1);
    ui.applyVisibility();
    $('regionCard').hidden = true;
    renderList();
    if (restoreView) rig.flyTo({ target: new THREE.Vector3(0, 870, 0), yaw: 0, pitch: 0.03, dist: rig.fitDistance(700, 1760, 0.94) }, 1.4);
  };

  ui.stepRegion = (dir) => {
    const list = regions.filter(allowed);
    if (!current) { ui.openRegion(list[0].id); return; }
    const i = list.findIndex((r) => r.id === current.id);
    ui.openRegion(list[(i + dir + list.length) % list.length].id);
  };

  $('regionClose').addEventListener('click', () => ui.closeRegion(true));
  $('rcPrev').addEventListener('click', () => ui.stepRegion(-1));
  $('rcNext').addEventListener('click', () => ui.stepRegion(1));
  $('rcOrbit').addEventListener('click', () => (orbitTimer || rig.autoRotate ? stopOrbit() : startOrbit()));

  // ---------------------------------------------------------------- orbit
  function startOrbitHint(r) {
    // a gentle half-swing to reveal depth, then settle
    const y0 = rig.goal.yaw;
    rig.flyTo({ yaw: y0 + 0.45 }, 2.2).then(() => { if (current === r && !rig.pointers.size) rig.flyTo({ yaw: y0 }, 2.0); });
  }
  function startOrbit() {
    rig.autoSpeed = 0.35; rig.autoRotate = true;
    $('rcOrbit').classList.add('on'); orbitTimer = true;
  }
  function stopOrbit() {
    if (orbitTimer) { rig.autoRotate = false; rig.autoSpeed = 0.16; }
    orbitTimer = null;
    $('rcOrbit')?.classList.remove('on');
  }
  ui.stopRegionOrbit = stopOrbit;

  // ---------------------------------------------------------------- hotspots on the body
  const hsLayer = $('hotspots');
  const hotspots = [];
  const HOTSPOT_IDS = new Set(['shoulder', 'chest', 'core', 'glutes', 'lower_back', 'quads', 'hamstrings', 'knee', 'calf', 'achilles', 'ankle', 'foot', 'neck', 'arm', 'heart_lungs', 'male_repro', 'female_repro', 'breast', 'itb']);
  for (const r of regions) {
    const re = r.def.hotspot;
    if (!re || !HOTSPOT_IDS.has(r.id)) continue;
    const cands = P.filter((p) => re.test(p.en));
    if (!cands.length) continue;
    const el = document.createElement('button');
    el.className = 'hotspot';
    el.innerHTML = `<span class="hs-label">${esc(r.zh)}</span>`;
    el.addEventListener('click', (e) => { e.stopPropagation(); ui.openRegion(r.id); });
    hsLayer.appendChild(el);
    hotspots.push({ r, el, ids: cands.map((p) => p.idx) });
  }
  let hsVisible = true;
  const hsBtn = document.createElement('button');
  hsBtn.id = 'hotspotToggle'; hsBtn.title = '显示/隐藏部位热点';
  hsBtn.innerHTML = '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="8" stroke-dasharray="3 3"/></svg>';
  hsBtn.classList.add('active');
  hsBtn.addEventListener('click', () => { hsVisible = !hsVisible; hsBtn.classList.toggle('active', hsVisible); });
  $('viewbar').insertBefore(hsBtn, $('autoRotate'));

  const v3 = new THREE.Vector3(), camDir = new THREE.Vector3(), toP = new THREE.Vector3();
  function updateHotspots() {
    const show = hsVisible && !current && ui.explodeShown < 0.02 && !ui.isolated && !rig.isAnimating();
    hsLayer.classList.toggle('hidden', !show);
    if (!show) return;
    const W = ui.canvas.clientWidth, H = ui.canvas.clientHeight;
    ui.camera.getWorldDirection(camDir);
    for (const h of hotspots) {
      const ok = allowed(h.r) && h.ids.some((i) => atlas.tgt.vis[i] > 0.5);
      if (!ok) { h.el.style.opacity = 0; h.el.style.pointerEvents = 'none'; continue; }
      // pick the instance facing the camera (left/right)
      let best = null, bestD = Infinity;
      for (const i of h.ids) {
        atlas.pieceCenter(i, v3);
        const d = v3.distanceTo(ui.camera.position);
        if (d < bestD) { bestD = d; best = v3.clone(); }
      }
      // facing test: each region has a preferred viewing yaw; hide dots on the far side of the body
      const ry = h.r.def.view?.yaw ?? 0;
      const fwd = new THREE.Vector3(Math.sin(ry), 0, Math.cos(ry));
      const facing = -fwd.dot(new THREE.Vector3(camDir.x, 0, camDir.z).normalize());
      best.project(ui.camera);
      const x = (best.x * 0.5 + 0.5) * W, y = (-best.y * 0.5 + 0.5) * H;
      const vis = facing > -0.15 && best.z < 1;
      h.el.style.left = x + 'px'; h.el.style.top = y + 'px';
      h.el.style.opacity = vis ? (ui.selected >= 0 ? 0.35 : 1) : 0;
      h.el.style.pointerEvents = vis ? 'auto' : 'none';
    }
  }
  ui.onPostCamera = () => updateHotspots();
  ui.onSexChange = () => {
    renderList();
    if (current) renderCard(current);
  };

  renderList();
}
