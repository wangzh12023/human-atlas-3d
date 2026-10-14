import * as THREE from 'three';
import { SYSTEMS } from './engine/atlas.js';
import { installRegions } from './regions-ui.js';

// Lazy-loaded content (written separately); the UI degrades gracefully without it.
let STRUCTURES = {}, SYSTEM_TEXT = {}, REGIONS = [];

const $ = (id) => document.getElementById(id);
const VIEW_YAW = { front: 0, side: Math.PI / 2, back: Math.PI, iso: Math.PI / 4 };
const ORGAN_SYSTEMS = ['heart', 'respiratory', 'digestive', 'urinary', 'reproductive', 'endocrine', 'lymphatic'];
const DEFAULT_ON = new Set(['skeleton', 'muscles', 'ligaments', 'heart', 'arteries', 'veins', 'nervous', 'sensory', 'respiratory', 'digestive', 'urinary', 'reproductive', 'endocrine', 'lymphatic']);
const SYS_DESC_FALLBACK = {
  skeleton: 'Bones form the supporting framework of the body, protect organs, and provide attachment points for muscles.',
  muscles: 'Skeletal muscles generate movement by pulling on their attachments. Together with tendons, they move joints, stabilize posture, and produce heat.',
};

function stripSide(en) { return en.replace(/^(Left|Right)\s+/, ''); }
function escapeHtml(s) { return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]); }

export class UI {
  constructor({ atlas, rig, camera, renderer, canvas, shadow }) {
    this.atlas = atlas; this.rig = rig; this.camera = camera; this.renderer = renderer; this.canvas = canvas; this.shadow = shadow;
    this.sex = 'male';
    this.morph = 0; this.morphTarget = 0;
    this.explode = 0; this.explodeShown = 0;
    this.sysOn = {};
    this.selected = -1; this.hovered = -1;
    this.isolated = null; // Set of piece ids
    this.region = null;
    this.selGroup = null; // ids highlighted as one structure (L+R or region)
    this.view = 'front';
  }

  async init() {
    try {
      // glob import: tolerates content files that are not generated yet
      const mods = import.meta.glob('./content/*.js');
      const load = (n) => (mods[`./content/${n}.js`] ? mods[`./content/${n}.js`]().catch(() => ({})) : Promise.resolve({}));
      const [s, r] = await Promise.all([load('structures'), load('regions')]);
      STRUCTURES = s.STRUCTURES || {}; SYSTEM_TEXT = s.SYSTEM_TEXT || {}; REGIONS = r.REGIONS || [];
    } catch (e) { console.warn('content not available', e); }
    const P = this.atlas.pieces;
    this.bySystem = {};
    for (const p of P) (this.bySystem[p.s] || (this.bySystem[p.s] = [])).push(p.idx);
    for (const s of this.atlas.systems) this.sysOn[s] = DEFAULT_ON.has(s);
    // name groups: same structure on both sides
    this.byBase = new Map();
    for (const p of P) {
      const k = p.s + '|' + stripSide(p.en);
      if (!this.byBase.has(k)) this.byBase.set(k, []);
      this.byBase.get(k).push(p.idx);
    }
    this.#buildSystemList();
    this.#bindPanel();
    this.#bindSearch();
    this.#bindInspector();
    this.#bindViewbar();
    this.#bindExplode();
    this.#bindSex();
    this.#bindCanvas();
    this.#bindKeys();
    this.#bindModal();
    installRegions(this, REGIONS);
    this.applyVisibility(true);
    this.updateInsets();
    window.addEventListener('resize', () => this.updateInsets());
    $('pieceCount').textContent = P.length.toLocaleString('en-US');
    this.rig.flyTo({ target: new THREE.Vector3(0, 880, 0), yaw: 0, pitch: 0.03, dist: 6200 }, 0.01);
    this.rig.update(0.016);
  }

  intro() {
    this.rig.flyTo({ target: new THREE.Vector3(0, 870, 0), yaw: 0, pitch: 0.03, dist: this.#fitBodyDist() }, 1.8);
  }

  #fitBodyDist() {
    return this.rig.fitDistance(700, 1760, 0.94);
  }

  updateInsets() {
    const w = window.innerWidth;
    const narrow = w < 900;
    const ins = this.rig.insets;
    ins.top = narrow ? 90 : 24;
    ins.bottom = narrow ? 170 : 150;
    ins.left = narrow ? 0 : 250;
    ins.right = narrow ? 0 : 90;
    const cardOpen = !$('regionCard').hidden || !$('inspector').hidden;
    this.rig.shiftX = !narrow && cardOpen && (this.region || this.explodeShown < 0.02) ? -Math.min(150, w * 0.08) : 0;
  }

  // ---------------------------------------------------------------- visibility model
  sexAllows(p) {
    if (p.x === 1) return this.sex === 'male';
    if (p.x === 2) return this.sex === 'female';
    return true;
  }

  applyVisibility(snap = false) {
    const a = this.atlas;
    let count = 0;
    for (const p of a.pieces) {
      let v = this.sysOn[p.s] && this.sexAllows(p) ? 1 : 0;
      // Solid skin supplies the breast surface. Keep its inner fat envelope
      // occluded to avoid intersecting the coarser body-surface triangles.
      // Region close-ups explicitly restore the fat as a translucent layer.
      if (this.sysOn.integument && !this.isolated && /breast adipose tissue/i.test(p.en)) v = 0;
      let ghost = 0;
      if (this.isolated) {
        if (!this.isolated.has(p.idx)) { ghost = v ? 1 : 0; }
        else v = this.sexAllows(p) ? 1 : 0;
      }
      a.setTarget('vis', p.idx, v);
      a.setTarget('ghost', p.idx, this.isolated ? ghost : 0);
      if (v && !ghost) count++;
    }
    if (snap) a.snap();
    $('visibleCount').textContent = count.toLocaleString('en-US');
    this.#refreshSystemRows();
    if (this.explode > 0.001) this.#relayoutGrid();
  }

  // ---------------------------------------------------------------- systems panel
  #buildSystemList() {
    const ul = $('sysList');
    ul.innerHTML = '';
    $('systemCount').textContent = this.atlas.systems.length;
    for (const s of this.atlas.systems) {
      const info = SYSTEMS[s];
      const li = document.createElement('li');
      li.dataset.sys = s;
      li.innerHTML = `<span class="sdot" style="background:${info.dot}"></span><span class="name">${info.en}<small>${info.zh}</small></span><span class="cnt"></span><span class="toggle"></span>`;
      li.addEventListener('click', () => { this.sysOn[s] = !this.sysOn[s]; this.#setPresetActive(null); this.applyVisibility(); });
      ul.appendChild(li);
    }
  }

  #refreshSystemRows() {
    for (const li of $('sysList').children) {
      const s = li.dataset.sys;
      const n = (this.bySystem[s] || []).filter((i) => this.sexAllows(this.atlas.pieces[i])).length;
      li.querySelector('.cnt').textContent = n;
      li.querySelector('.toggle').classList.toggle('on', !!this.sysOn[s]);
      li.classList.toggle('off', !this.sysOn[s]);
    }
  }

  #setPresetActive(name) {
    for (const b of $('presetSeg').children) b.classList.toggle('active', b.dataset.preset === name);
  }

  setPreset(name) {
    for (const s of this.atlas.systems) {
      if (name === 'all') this.sysOn[s] = DEFAULT_ON.has(s);
      else if (name === 'skeleton') this.sysOn[s] = s === 'skeleton' || s === 'ligaments';
      else if (name === 'organs') this.sysOn[s] = ORGAN_SYSTEMS.includes(s);
    }
    this.#setPresetActive(name);
    this.applyVisibility();
  }

  #bindPanel() {
    for (const b of $('presetSeg').children) b.addEventListener('click', () => this.setPreset(b.dataset.preset));
    $('hideAll').addEventListener('click', () => {
      const anyOn = Object.values(this.sysOn).some(Boolean);
      for (const s in this.sysOn) this.sysOn[s] = !anyOn;
      $('hideAll').textContent = anyOn ? 'Show all' : 'Hide all';
      this.#setPresetActive(null);
      this.applyVisibility();
    });
    for (const t of document.querySelectorAll('.ptab')) {
      t.addEventListener('click', () => this.showTab(t.dataset.tab));
    }
    // small screens: the panel collapses so the model stays visible
    const panel = $('leftPanel');
    const narrow = () => window.innerWidth < 900;
    if (narrow()) panel.classList.add('collapsed');
    $('panelToggle').addEventListener('click', () => panel.classList.remove('collapsed'));
    this.collapsePanel = () => { if (narrow()) panel.classList.add('collapsed'); };
    const head = document.createElement('button');
    head.className = 'link panel-close'; head.textContent = '收起 ▾';
    head.style.cssText = 'position:absolute;right:12px;top:10px;display:none';
    panel.appendChild(head);
    head.addEventListener('click', () => panel.classList.add('collapsed'));
    const syncHead = () => { head.style.display = narrow() ? 'block' : 'none'; };
    syncHead(); window.addEventListener('resize', syncHead);
  }

  showTab(tab) {
    for (const t of document.querySelectorAll('.ptab')) t.classList.toggle('active', t.dataset.tab === tab);
    for (const b of document.querySelectorAll('.tab-body')) b.hidden = b.dataset.tab !== tab;
  }

  // ---------------------------------------------------------------- search
  #bindSearch() {
    const input = $('searchInput'), list = $('searchResults');
    this.searchIndex = [];
    for (const [k, ids] of this.byBase) {
      const p = this.atlas.pieces[ids[0]];
      const zh = p.zh.replace(/^[左右]/, '');
      this.searchIndex.push({ key: k, ids, en: stripSide(p.en), zh, s: p.s, hay: (stripSide(p.en) + ' ' + zh + ' ' + p.fma).toLowerCase() });
    }
    let active = 0, results = [];
    const render = () => {
      const q = input.value.trim().toLowerCase();
      if (!q) { list.hidden = true; return; }
      const terms = q.split(/\s+/);
      results = this.searchIndex.filter((e) => terms.every((t) => e.hay.includes(t)) && e.ids.some((i) => this.sexAllows(this.atlas.pieces[i])));
      results.sort((a, b) => (a.en.toLowerCase().startsWith(q) || a.zh.startsWith(q) ? -1 : 0) - (b.en.toLowerCase().startsWith(q) || b.zh.startsWith(q) ? -1 : 0) || a.en.length - b.en.length);
      const regionHits = REGIONS.filter((r) => (r.zh + ' ' + r.en).toLowerCase().includes(q) && this.#regionAllowed(r));
      results = [...regionHits.map((r) => ({ region: r })), ...results].slice(0, 40);
      active = 0;
      list.innerHTML = results.length ? results.map((e, i) => e.region
        ? `<li data-i="${i}" class="${i === active ? 'active' : ''}"><span class="sdot" style="background:#c8705f"></span><span class="rt"><span class="zh">${escapeHtml(e.region.zh)}</span><span class="en">${escapeHtml(e.region.en)}</span></span><span class="tag">部位特写</span></li>`
        : `<li data-i="${i}" class="${i === active ? 'active' : ''}"><span class="sdot" style="background:${SYSTEMS[e.s].dot}"></span><span class="rt"><span class="zh">${escapeHtml(e.zh)}</span><span class="en">${escapeHtml(e.en)}</span></span><span class="tag">${SYSTEMS[e.s].zh}${e.ids.length > 1 ? ' ×' + e.ids.length : ''}</span></li>`).join('')
        : `<li class="empty">没有找到匹配的结构 · No match</li>`;
      list.hidden = false;
    };
    const choose = (i) => {
      const e = results[i];
      if (!e) return;
      list.hidden = true; input.blur();
      if (e.region) { this.openRegion(e.region.id); return; }
      const visibleIds = e.ids.filter((id) => this.sexAllows(this.atlas.pieces[id]));
      if (!this.sysOn[e.s]) { this.sysOn[e.s] = true; this.applyVisibility(); }
      this.select(visibleIds[0], { group: visibleIds, focus: true });
    };
    input.addEventListener('input', render);
    input.addEventListener('focus', render);
    input.addEventListener('keydown', (ev) => {
      if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') {
        ev.preventDefault();
        active = (active + (ev.key === 'ArrowDown' ? 1 : -1) + results.length) % Math.max(1, results.length);
        for (const li of list.children) li.classList.toggle('active', +li.dataset.i === active);
        list.children[active]?.scrollIntoView({ block: 'nearest' });
      } else if (ev.key === 'Enter') { choose(active); }
      else if (ev.key === 'Escape') { input.value = ''; list.hidden = true; input.blur(); }
    });
    list.addEventListener('pointerdown', (ev) => { const li = ev.target.closest('li[data-i]'); if (li) { ev.preventDefault(); choose(+li.dataset.i); } });
    input.addEventListener('blur', () => setTimeout(() => { list.hidden = true; }, 120));
  }

  // ---------------------------------------------------------------- selection & inspector
  select(id, { group, focus = false, fromCanvas = false } = {}) {
    const a = this.atlas;
    if (id >= 0) this.collapsePanel && this.collapsePanel();
    if (this.selGroup) for (const i of this.selGroup) a.setTarget('sel', i, 0);
    if (id < 0) {
      this.selected = -1; this.selGroup = null;
      $('inspector').hidden = true;
      if (this.region) $('regionCard').hidden = false;
      if (this.isolated && !this.region) { this.isolated = null; this.applyVisibility(); }
      return;
    }
    this.selected = id;
    this.selGroup = group || [id];
    for (const i of this.selGroup) a.setTarget('sel', i, 1);
    this.#fillInspector(id);
    if (this.region) $('regionCard').hidden = true;
    $('inspector').hidden = false;
    if (focus) this.focusPieces(this.selGroup);
  }

  #fillInspector(id) {
    const p = this.atlas.pieces[id];
    const sys = SYSTEMS[p.s];
    const base = stripSide(p.en);
    const info = STRUCTURES[base];
    $('inspBar').style.background = sys.dot;
    $('inspSystem').textContent = `${sys.en} · ${sys.zh}`;
    const group = this.selGroup || [id];
    const bilateral = group.length > 1 && group.every((i) => stripSide(this.atlas.pieces[i].en) === base);
    $('inspTitle').textContent = bilateral ? p.zh.replace(/^[左右]/, '') + '（左右）' : p.zh;
    $('inspSub').textContent = bilateral ? base + ' (both sides)' : p.en;
    $('inspDesc').textContent = info?.d || SYSTEM_TEXT[p.s] || SYS_DESC_FALLBACK[p.s] || '';
    const sport = $('inspSport');
    if (info?.s) { sport.hidden = false; sport.textContent = '运动相关 · ' + info.s; } else sport.hidden = true;
    $('inspNote').textContent = p.k === 'proc'
      ? 'Schematic model · 示意性建模（依据解剖学文献构建）'
      : p.k === 'hra' ? 'Human Reference Atlas (NIH HuBMAP) · female reference organ' : 'System overview · structure identified from source anatomy';
    $('inspRef').textContent = p.fma || '—';
    $('inspCount').textContent = (this.selGroup || [id]).length;
    const link = $('inspLink');
    if (p.fma && p.fma.startsWith('FMA')) {
      link.href = `https://www.ebi.ac.uk/ols4/search?q=${encodeURIComponent(p.fma.replace('FMA', 'FMA:'))}`;
      link.hidden = false;
    } else if (p.fma && p.fma.startsWith('UBERON')) {
      link.href = `https://www.ebi.ac.uk/ols4/search?q=${encodeURIComponent(p.fma.replace('_', ':'))}`;
      link.hidden = false;
    } else link.hidden = true;
    this.#refreshIsolateBtn();
  }

  #refreshIsolateBtn() {
    const on = !!this.isolated && !this.region;
    $('isolateBtn').classList.toggle('on', on);
    $('isolateLabel').textContent = on ? '显示全部 · Show all' : '单独查看 · Isolate';
  }

  #bindInspector() {
    $('inspClose').addEventListener('click', () => { this.select(-1); if (this.region) $('regionCard').hidden = false; });
    $('clearSel').addEventListener('click', () => { this.isolated = null; this.select(-1); this.applyVisibility(); });
    $('isolateBtn').addEventListener('click', () => {
      if (this.isolated && !this.region) {
        this.isolated = null; this.applyVisibility(); this.#refreshIsolateBtn();
        return;
      }
      if (this.selected < 0) return;
      if (this.region) this.closeRegion(false);
      this.isolated = new Set(this.selGroup);
      this.applyVisibility();
      this.#refreshIsolateBtn();
      this.focusPieces(this.selGroup);
    });
  }

  /** Frame a set of pieces (works in assembled and exploded layouts). */
  focusPieces(ids, opts = {}) {
    const a = this.atlas;
    const box = new THREE.Box3();
    const tmp = new THREE.Box3(), c = new THREE.Vector3();
    for (const i of ids) {
      if (this.explodeShown > 0.02) {
        a.livePieceCenter(i, c);
        const s = a.liveScale(i) * a.pieces[i].size * 0.5;
        tmp.set(c.clone().subScalar(s), c.clone().addScalar(s));
      } else a.pieceBox(i, tmp, this.morphTarget);
      box.union(tmp);
    }
    if (box.isEmpty()) return;
    let yaw = opts.yaw;
    if (yaw === undefined) {
      if (this.explodeShown > 0.02) yaw = 0;
      else {
        // face the structure: choose front or back depending on depth relative to body centre
        // face the structure: compare its depth with the body's mid-plane at that height
        const bc = box.getCenter(c);
        const mid = this.#bodyMidZ(bc.y);
        const cur = this.rig.goal.yaw;
        const front = Math.abs(Math.atan2(Math.sin(cur), Math.cos(cur))) < Math.PI / 2;
        yaw = bc.z < mid - 25 && front ? Math.PI : bc.z > mid + 25 && !front ? 0 : cur;
      }
    }
    const size = box.getSize(new THREE.Vector3());
    const minSize = 110;
    if (size.length() < minSize) box.expandByScalar((minSize - size.length()) / 2);
    return this.rig.frameBox(box, { yaw, pitch: opts.pitch ?? 0.05, fill: opts.fill ?? 0.5, duration: opts.duration ?? 1.3 });
  }

  /** approximate anterior-posterior mid-plane (z) of the body at height y */
  #bodyMidZ(y) {
    if (!this._midZ) {
      const a = this.atlas, bins = new Map();
      for (const p of a.pieces) {
        if (p.s !== 'skeleton' && p.s !== 'muscles') continue;
        const b = Math.round(p.cM[1] / 100);
        const e = bins.get(b) || [1e9, -1e9];
        e[0] = Math.min(e[0], p.bM[2]); e[1] = Math.max(e[1], p.bM[5]);
        bins.set(b, e);
      }
      this._midZ = bins;
    }
    const e = this._midZ.get(Math.round(y / 100));
    return e ? (e[0] + e[1]) / 2 : 90;
  }

  // ---------------------------------------------------------------- canvas interaction
  #bindCanvas() {
    const tip = $('tooltip');
    let lastMove = null;
    this.canvas.addEventListener('pointermove', (e) => { lastMove = e; });
    this.pendingHover = () => {
      if (!lastMove || this.rig.pointers.size) { return; }
      const e = lastMove; lastMove = null;
      const rect = this.canvas.getBoundingClientRect();
      const id = this.atlas.pick(this.camera, e.clientX - rect.left, e.clientY - rect.top, rect.width, rect.height);
      this.setHover(id);
      if (id >= 0) {
        const p = this.atlas.pieces[id];
        tip.innerHTML = `${escapeHtml(p.zh)}<small>${escapeHtml(p.en)}</small>`;
        tip.style.left = e.clientX + 'px'; tip.style.top = e.clientY + 'px';
        tip.hidden = false;
        this.canvas.classList.add('pointer');
      } else { tip.hidden = true; this.canvas.classList.remove('pointer'); }
    };
    this.canvas.addEventListener('pointerleave', () => { this.setHover(-1); tip.hidden = true; });
    this.canvas.addEventListener('pointerup', (e) => {
      if (this.rig.dragged) return;
      if (e.button !== 0) return;
      const rect = this.canvas.getBoundingClientRect();
      const id = this.atlas.pick(this.camera, e.clientX - rect.left, e.clientY - rect.top, rect.width, rect.height);
      if (id >= 0) {
        const p = this.atlas.pieces[id];
        this.select(id, { group: [id], fromCanvas: true, focus: e.detail >= 2 });
      } else if (this.selected >= 0 && !this.isolated) this.select(-1);
    });
    this.canvas.addEventListener('dblclick', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const id = this.atlas.pick(this.camera, e.clientX - rect.left, e.clientY - rect.top, rect.width, rect.height);
      if (id >= 0) this.focusPieces([id], { fill: 0.42 });
    });
    this.rig.onInteract = () => { $('tooltip').hidden = true; this.stopRegionOrbit && this.stopRegionOrbit(); };
  }

  setHover(id) {
    if (id === this.hovered) return;
    if (this.hovered >= 0) this.atlas.setTarget('hover', this.hovered, 0);
    this.hovered = id;
    if (id >= 0) this.atlas.setTarget('hover', id, 1);
  }

  // ---------------------------------------------------------------- view bar
  #bindViewbar() {
    for (const b of document.querySelectorAll('#viewbar [data-view]')) {
      b.addEventListener('click', () => this.setView(b.dataset.view));
    }
    $('autoRotate').addEventListener('click', () => {
      this.rig.autoRotate = !this.rig.autoRotate;
      $('autoRotate').classList.toggle('active', this.rig.autoRotate);
    });
    $('resetView').addEventListener('click', () => this.resetAll());
  }

  setView(v) {
    this.view = v;
    for (const b of document.querySelectorAll('#viewbar [data-view]')) b.classList.toggle('active', b.dataset.view === v);
    if (this.explodeShown > 0.5) return;
    this.rig.flyTo({ yaw: VIEW_YAW[v], pitch: v === 'iso' ? 0.18 : 0.03 }, 1.1);
  }

  resetAll() {
    this.closeRegion(false);
    this.isolated = null;
    this.select(-1);
    this.setExplode(0, true);
    this.setPreset('all');
    this.rig.autoRotate = false; $('autoRotate').classList.remove('active');
    this.view = 'front';
    for (const b of document.querySelectorAll('#viewbar [data-view]')) b.classList.toggle('active', b.dataset.view === 'front');
    this.rig.flyTo({ target: new THREE.Vector3(0, 870, 0), yaw: 0, pitch: 0.03, dist: this.#fitBodyDist() }, 1.4);
  }

  // ---------------------------------------------------------------- explode
  #bindExplode() {
    const slider = $('explodeSlider');
    const setFromX = (x) => {
      const r = slider.getBoundingClientRect();
      this.setExplode(THREE.MathUtils.clamp((x - r.left) / r.width, 0, 1));
    };
    let dragging = false;
    slider.addEventListener('pointerdown', (e) => { dragging = true; slider.setPointerCapture(e.pointerId); setFromX(e.clientX); });
    slider.addEventListener('pointermove', (e) => { if (dragging) setFromX(e.clientX); });
    slider.addEventListener('pointerup', () => { dragging = false; });
    slider.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowRight' || e.key === 'ArrowUp') this.setExplode(Math.min(1, this.explode + 0.05));
      if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') this.setExplode(Math.max(0, this.explode - 0.05));
    });
    $('explodeReset').addEventListener('click', () => this.setExplode(0, true));
  }

  setExplode(v, animate = false) {
    const prev = this.explode;
    this.explode = v;
    this.explodeAnimate = animate;
    if (v > 0.001 && prev <= 0.001) {
      this.#relayoutGrid();
    }
    const pct = Math.round(v * 100);
    $('explodeVal').textContent = pct;
    $('explodeFill').style.width = pct + '%';
    $('explodeKnob').style.left = pct + '%';
    $('explodeSlider').setAttribute('aria-valuenow', pct);
  }

  #relayoutGrid() {
    const ids = this.atlas.pieces.filter((p) => this.atlas.tgt.vis[p.idx] > 0.5 && this.atlas.tgt.ghost[p.idx] < 0.5).map((p) => p.idx);
    const f = this.rig.freeSize();
    this.gridBounds = this.atlas.layoutGrid(ids.length ? ids : this.atlas.pieces.map((p) => p.idx), this.sex === 'female', f.w / f.h);
  }

  #updateExplodeCamera(prevShown) {
    // camera choreography: assembled -> separated (zoom out) -> inventory grid (pan mode, face-on)
    const e = this.explodeShown;
    const B = this.atlas.uniforms.uExplodeB.value;
    if (B > 0.35 && this.rig.mode !== 'pan') {
      this.rig.mode = 'pan';
      const gb = this.gridBounds;
      const dist = this.rig.fitDistance(gb.w, gb.h, 0.96);
      this.rig.bounds = new THREE.Box3(new THREE.Vector3(-gb.w / 2, gb.cy - gb.h / 2, -10), new THREE.Vector3(gb.w / 2, gb.cy + gb.h / 2, 10));
      this.rig.maxDist = Math.max(9000, dist * 1.5);
      this.rig.flyTo({ target: new THREE.Vector3(0, gb.cy, 0), yaw: 0, pitch: 0, dist }, 1.2);
      document.querySelector('.hints').innerHTML = '<span>Drag to pan</span><span>Scroll / pinch to zoom</span><span>Tap to inspect</span>';
      $('stageLabel').textContent = 'ANATOMICAL INVENTORY';
    } else if (B < 0.25 && this.rig.mode === 'pan') {
      this.rig.mode = 'orbit';
      this.rig.bounds = null;
      this.rig.maxDist = 9000;
      this.rig.flyTo({ target: new THREE.Vector3(0, 870, 0), yaw: VIEW_YAW[this.view] || 0, pitch: 0.03, dist: this.#fitBodyDist() * (1 + this.atlas.uniforms.uExplodeA.value * 0.9) }, 1.1);
      document.querySelector('.hints').innerHTML = '<span>Drag to orbit</span><span>Scroll / pinch to zoom</span><span>Tap to inspect</span>';
    }
    if (this.rig.mode === 'orbit') {
      const A = this.atlas.uniforms.uExplodeA.value;
      $('stageLabel').textContent = A > 0.02 ? 'SEPARATED STRUCTURES' : `ADULT HUMAN · ${this.sex === 'female' ? 'FEMALE' : 'MALE'}`;
      if (Math.abs(A - (this.lastA ?? 0)) > 0.0005 && !this.rig.isAnimating() && !this.region) {
        // widen framing as systems separate
        const want = this.#fitBodyDist() * (1 + A * 0.9);
        if (this.rig.goal.dist < want) this.rig.goal.dist += (want - this.rig.goal.dist) * 0.2;
        this.rig.goal.target.y += (870 - this.rig.goal.target.y) * 0.1;
      }
      this.lastA = A;
    }
  }

  // ---------------------------------------------------------------- sex
  #bindSex() {
    for (const b of document.querySelectorAll('.sex-btn')) b.addEventListener('click', () => this.setSex(b.dataset.sex));
  }

  setSex(sex) {
    if (sex === this.sex) return;
    this.sex = sex;
    this.morphTarget = sex === 'female' ? 1 : 0;
    document.querySelector('.sex-switch').classList.toggle('female', sex === 'female');
    for (const b of document.querySelectorAll('.sex-btn')) {
      b.classList.toggle('active', b.dataset.sex === sex);
      b.setAttribute('aria-checked', b.dataset.sex === sex);
    }
    if (this.selected >= 0 && !this.sexAllows(this.atlas.pieces[this.selected])) this.select(-1);
    if (this.region && !this.#regionAllowed(this.region)) this.closeRegion(true);
    this.applyVisibility();
    this.onSexChange && this.onSexChange();
    if (!this.region && this.explodeShown < 0.02 && !this.rig.isAnimating()) {
      this.rig.flyTo({ yaw: this.rig.goal.yaw + 0.35, pitch: 0.06 }, 0.9).then(() => {
        if (!this.region) this.rig.flyTo({ yaw: VIEW_YAW[this.view] ?? 0, pitch: 0.03 }, 1.0);
      });
    }
  }

  #regionAllowed(r) { return !r.sex || r.sex === 'both' || r.sex === this.sex; }

  // ---------------------------------------------------------------- keys
  #bindKeys() {
    window.addEventListener('keydown', (e) => {
      const tag = document.activeElement?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;
      if (e.key === '/') { e.preventDefault(); $('searchInput').focus(); }
      else if (e.key === 'Escape') {
        if (!$('modal').hidden) $('modal').hidden = true;
        else if (this.region) this.closeRegion(true);
        else if (this.isolated) { this.isolated = null; this.applyVisibility(); this.#refreshIsolateBtn(); }
        else this.select(-1);
      } else if (e.key === 'f' || e.key === 'F') this.setView('front');
      else if (e.key === 'b' || e.key === 'B') this.setView('back');
      else if (e.key === 's' || e.key === 'S') this.setView('side');
      else if (e.key === 'r' || e.key === 'R') this.resetAll();
      else if (e.key === 'm' || e.key === 'M') this.setSex(this.sex === 'male' ? 'female' : 'male');
      else if (e.key === 'ArrowRight' && this.region) this.stepRegion(1);
      else if (e.key === 'ArrowLeft' && this.region) this.stepRegion(-1);
    });
  }

  // ---------------------------------------------------------------- modal
  #bindModal() {
    const open = (html) => { $('modalBody').innerHTML = html; $('modal').hidden = false; };
    $('modalClose').addEventListener('click', () => { $('modal').hidden = true; });
    $('modal').addEventListener('click', (e) => { if (e.target.id === 'modal') $('modal').hidden = true; });
    $('creditsBtn').addEventListener('click', () => open(CREDITS_HTML));
    $('infoBtn').addEventListener('click', () => open(ABOUT_HTML));
  }

  // regions: openRegion / closeRegion / stepRegion are installed by regions-ui.js

  // ---------------------------------------------------------------- per frame
  update(dt) {
    // morph (male <-> female), eased
    const u = this.atlas.uniforms;
    const md = this.morphTarget - this.morph;
    if (Math.abs(md) > 1e-4) {
      this.morphT = (this.morphT ?? 0);
      this.morph += md * (1 - Math.exp(-dt * 3.2));
      if (Math.abs(this.morphTarget - this.morph) < 0.001) this.morph = this.morphTarget;
    }
    const m = this.morph;
    u.uMorph.value = m * m * (3 - 2 * m);
    // explode: smooth follow of the slider
    const prevShown = this.explodeShown;
    const k = this.explodeAnimate ? 2.6 : 9;
    this.explodeShown += (this.explode - this.explodeShown) * (1 - Math.exp(-dt * k));
    if (Math.abs(this.explode - this.explodeShown) < 0.0005) this.explodeShown = this.explode;
    const e = this.explodeShown;
    u.uExplodeA.value = THREE.MathUtils.smoothstep(e, 0, 0.42) * (1 - THREE.MathUtils.smoothstep(e, 0.55, 0.95));
    u.uExplodeB.value = THREE.MathUtils.clamp((e - 0.42) / 0.58, 0, 1);
    this.#updateExplodeCamera(prevShown);
    this.shadow.material.uniforms.uOpacity.value = 1 - THREE.MathUtils.smoothstep(e, 0.02, 0.3);
    this.pendingHover && this.pendingHover();
    this.updateInsets();
    this.onFrame && this.onFrame(dt);
  }

  postCamera(dt) { this.onPostCamera && this.onPostCamera(dt); }
}

const CREDITS_HTML = `
<h3>Source &amp; credits</h3>
<p>本站为教育与科普用途的交互式人体解剖图谱。This atlas is built for education.</p>
<h4>3D 数据来源 · Data</h4>
<ul>
<li><b>BodyParts3D</b>, © The Database Center for Life Science (DBCLS), licensed under <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener">CC BY 4.0</a>. 男性全身模型（骨骼、肌肉、血管、神经、器官等 2,000+ 结构）。<a href="https://dbarchive.biosciencedbc.jp/en/bodyparts3d/" target="_blank" rel="noopener">dbarchive.biosciencedbc.jp</a></li>
<li><b>Human Reference Atlas (HRA) 3D Reference Organs</b>, NIH HuBMAP / Cyberinfrastructure for Network Science Center, Indiana University, licensed under CC BY 4.0. 女性体表、骨盆、子宫、输卵管、卵巢、乳腺、膝关节等参考器官，用于女性模型与形态配准。<a href="https://humanatlas.io/" target="_blank" rel="noopener">humanatlas.io</a></li>
<li>部分结构（如膝/踝韧带、半月板、足底筋膜、腹直肌、腹横肌、女性外生殖器等）为依据解剖学文献构建的<b>示意性模型</b>，已在详情中标注。</li>
</ul>
<h4>说明 · Notes</h4>
<ul>
<li>女性模型由男性解剖结构经与女性参考体表/骨骼配准变形得到，并替换为女性特有器官；比例与个体差异请以医学资料为准。</li>
<li>解剖名称遵循 FMA（Foundational Model of Anatomy）及《人体解剖学名词》。</li>
<li>内容仅供科普学习，不构成医疗建议；如有疼痛或疾病请咨询专业医生。</li>
</ul>
<h4>技术 · Tech</h4>
<p>three.js · meshoptimizer · Inter typeface.</p>`;

const ABOUT_HTML = `
<h3>使用指南 · How to use</h3>
<ul>
<li><b>旋转</b>：拖动模型；<b>缩放</b>：滚轮 / 双指；<b>平移</b>：右键拖动或 Shift + 拖动。</li>
<li><b>查看结构</b>：单击任意结构查看名称与介绍，双击放大聚焦。</li>
<li><b>男 / 女切换</b>：左上角开关（快捷键 <span class="kbd">M</span>），模型会平滑变形并显示对应的生殖结构。</li>
<li><b>部位特写</b>：左侧「部位特写」标签页，或点击身体上的热点，相机会自动飞到对应部位并展示讲解与相关结构。</li>
<li><b>系统开关</b>：在「系统」中开关骨骼、肌肉、血管等；「Skeleton / Organs」为快速预设。</li>
<li><b>分解视图</b>：拖动底部「Explode anatomy」滑块，从完整人体 → 系统分离 → 全部结构清单。</li>
<li><b>搜索</b>：按 <span class="kbd">/</span> 搜索中文或英文名称（如「跟腱」「ACL」「臀大肌」）。</li>
<li>视角快捷键：<span class="kbd">F</span> 前 <span class="kbd">S</span> 侧 <span class="kbd">B</span> 后 <span class="kbd">R</span> 重置 <span class="kbd">Esc</span> 返回。</li>
</ul>`;
