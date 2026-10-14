import * as THREE from 'three';
import { MeshoptDecoder } from 'meshoptimizer/decoder';
import { atlasVertex, atlasFragment, pickVertex, pickFragment } from './shaders.js';

const STRIDE = 20;
const ROW = 256; // pieces per texture row

// ------------------------------------------------------------------ system palette (sRGB)
export const SYSTEMS = {
  skeleton:     { zh: '骨骼', en: 'Skeleton',        color: '#ede6d6', dot: '#d9d2c3', mat: 1.0 },
  muscles:      { zh: '肌肉', en: 'Muscles',         color: '#cd7563', dot: '#b5564b', mat: 0.0 },
  ligaments:    { zh: '韧带软骨', en: 'Ligaments', color: '#e8e6dc', dot: '#c9c4b2', mat: 0.55 },
  heart:        { zh: '心脏', en: 'Heart',           color: '#b84a48', dot: '#9b3a3b', mat: 0.0 },
  arteries:     { zh: '动脉', en: 'Arteries',        color: '#c2443d', dot: '#c0463f', mat: 0.0 },
  veins:        { zh: '静脉', en: 'Veins',           color: '#4d6f9b', dot: '#4f6d93', mat: 0.0 },
  nervous:      { zh: '神经', en: 'Nervous system', color: '#e3c9a6', dot: '#c9b25c', mat: 0.2 },
  sensory:      { zh: '感官', en: 'Sensory organs', color: '#e4e2dc', dot: '#bfc3c6', mat: 0.3 },
  respiratory:  { zh: '呼吸', en: 'Respiratory',  color: '#d79a9c', dot: '#8e9399', mat: 0.1 },
  digestive:    { zh: '消化', en: 'Digestive',    color: '#dcb58c', dot: '#c99a63', mat: 0.05 },
  urinary:      { zh: '泌尿', en: 'Urinary',      color: '#b9685a', dot: '#a35b4f', mat: 0.05 },
  reproductive: { zh: '生殖', en: 'Reproductive', color: '#cf8d93', dot: '#c27a86', mat: 0.05 },
  endocrine:    { zh: '内分泌', en: 'Endocrine',      color: '#c79a5a', dot: '#b98d4f', mat: 0.1 },
  lymphatic:    { zh: '淋巴', en: 'Lymphatic',     color: '#9a6f8f', dot: '#8c6a85', mat: 0.05 },
  integument:   { zh: '皮肤', en: 'Integument',       color: '#e5bfa8', dot: '#dcb49c', mat: 0.25 },
};

// specific organ tints (matched against english name, lower case)
const NAME_TINTS = [
  [/liver|hepatovenous/, '#9c4a3c'], [/gallbladder/, '#6f8a4c'], [/stomach/, '#d9978d'], [/pancrea/, '#e2c08c'],
  [/duoden|jejun|ileum|ileocecal/, '#e0b089'], [/colon|cecum|append|rectum|taenia/, '#d4a57d'], [/esophag/, '#cf8a80'],
  [/spleen/, '#7e4a5c'], [/kidney/, '#9e4f45'], [/ureter|urethra/, '#d9b04f'], [/urinary bladder/, '#d7b25d'],
  [/adrenal/, '#d6a44c'], [/thymus/, '#c9a0a8'], [/tongue/, '#d07a78'], [/tooth/, '#f2eee2'], [/gingiva|lip\b|palate/, '#d98b88'],
  [/parotid|submandibular gland|sublingual gland|lacrimal gland/, '#e0b693'], [/mesenter|mesocolon|mesoappendix|omentum/, '#eed9a6'],
  [/white matter|corpus callosum|internal capsule|fornix|commissure|stria|optic tract|optic chiasm/, '#ede6dc'],
  [/cerebell|gyrus|lobule|insula|occipital lobe|hippocamp|amygdal|cortex|uncus|cuneus|precuneus/, '#e7c3b8'],
  [/thalam|putamen|pallid|caudate nucleus|nucleus|geniculate|colliculus|habenula|hypothalamus|mammillary/, '#d8a99c'],
  [/pons|medulla|midbrain|peduncle|spinal cord/, '#e6cfba'], [/ventricle|aqueduct|central canal|choroid plexus/, '#9ab7cf'],
  [/nerve|ganglion/, '#e3c25b'], [/pituitary|pineal/, '#d9a560'], [/tentorium/, '#d8d0c3'],
  [/sclera|vitreous|lens|cornea/, '#f1f0ec'], [/iris|choroid/, '#6c5546'], [/retina/, '#d98d6d'], [/eyeball/, '#dfe9ee'],
  [/trachea|bronch|cartilage|epiglott|arytenoid|cricoid|corniculate|cuneiform/, '#e4ded2'],
  [/lung|lobe of lung|pulmonary segment/, '#e3a6a5'],
  [/disk/, '#cdd8de'], [/calcaneal tendon|tendon|iliotibial|linea alba|retinaculum|aponeuros|fascia/, '#ece0c6'],
  [/meniscus|menisci/, '#a9c6cf'], [/cruciate|collateral|talofibular|calcaneofibular|tibiofibular|deltoid ligament|patellar ligament|plantar|ligament/, '#e6cf9f'],
  [/testis|epididym/, '#e3b9b1'], [/prostate|seminal vesicle/, '#c98f86'], [/corpus cavernosum|corpus spongiosum|glans/, '#c97f80'],
  [/deferent|ductus deferens/, '#e1c08f'], [/uter|cervix/, '#b85f66'], [/ovar/, '#e2c4b4'], [/tube|fimbri|infundibul|ampulla|isthmus/, '#d58a8f'],
  [/vagin|vestib|labi|clitor/, '#cf8187'], [/mammary|lobe of breast|lactiferous/, '#e8c79b'], [/nipple|areola/, '#b9786c'],
  [/breast adipose/, '#d38b78'], [/breast fat|adipose/, '#f0d9b5'], [/cooper|suspensory ligament of breast/, '#efe4cf'],
  [/hair|eyebrow/, '#5a4639'], [/heart wall|wall of|myocard/, '#b14d4a'], [/cavity of/, '#e39a92'],
  [/valve|leaflet|cusp/, '#efe2cf'], [/papillary/, '#b9574f'],
];

const SKELETON_TINTS = [[/tooth/, '#f4f0e4']];

function hashf(i) {
  const s = Math.sin(i * 127.1 + 311.7) * 43758.5453;
  return s - Math.floor(s);
}

export class Atlas {
  constructor(renderer) {
    this.renderer = renderer;
    this.group = new THREE.Group();
    this.pieces = [];
    this.meshes = [];
    this.ghostMeshes = [];
    this.pickMeshes = [];
    this.n = 0;
    this.time = 0;
    this.uniforms = null;
  }

  async load(baseUrl, onProgress) {
    await MeshoptDecoder.ready;
    const manifest = await (await fetch(baseUrl + 'manifest.json')).json();
    this.manifest = manifest;
    this.pieces = manifest.pieces;
    this.n = this.pieces.length;
    this.systems = manifest.systems;
    this.#initTextures();
    const total = manifest.chunks.reduce((a, c) => a + (c.bytes || 1), 0);
    let done = 0;
    onProgress && onProgress(0);
    const results = new Array(manifest.chunks.length);
    // fetch in parallel, decode as they arrive
    await Promise.all(manifest.chunks.map(async (c, i) => {
      const res = await fetch(baseUrl + c.name + '.bin');
      const buf = new Uint8Array(await res.arrayBuffer());
      results[i] = this.#decodeChunk(buf, c);
      done += c.bytes || 1;
      onProgress && onProgress(done / total);
    }));
    results.forEach((geo, i) => this.#addChunk(geo, manifest.chunks[i]));
    // piece ids per chunk (chunks are per system) for draw-call culling
    for (const m of this.meshes) m.userData.ids = this.pieces.filter((p) => p.s === m.userData.system).map((p) => p.idx);
    this.#computeLayouts();
    return this;
  }

  #decodeChunk(buf, chunk) {
    const dv = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
    const nV = dv.getUint32(0, true), nI = dv.getUint32(4, true);
    const vLen = dv.getUint32(8, true), iLen = dv.getUint32(12, true);
    const vSrc = buf.subarray(16, 16 + vLen);
    const iSrc = buf.subarray(16 + vLen, 16 + vLen + iLen);
    const vert = new Uint8Array(nV * STRIDE);
    MeshoptDecoder.decodeVertexBuffer(vert, nV, STRIDE, vSrc);
    const idx = new Uint32Array(nI);
    MeshoptDecoder.decodeIndexBuffer(new Uint8Array(idx.buffer), nI, 4, iSrc);
    const u16 = new Uint16Array(vert.buffer);
    const ib = new THREE.InterleavedBuffer(u16, STRIDE / 2);
    const g = new THREE.BufferGeometry();
    g.setAttribute('aPM', new THREE.InterleavedBufferAttribute(ib, 3, 0, false));
    g.setAttribute('aPid', new THREE.InterleavedBufferAttribute(ib, 1, 3, false));
    g.setAttribute('aPF', new THREE.InterleavedBufferAttribute(ib, 3, 4, false));
    g.setAttribute('aAO', new THREE.InterleavedBufferAttribute(ib, 1, 7, false));
    g.setAttribute('aNrm', new THREE.InterleavedBufferAttribute(ib, 2, 8, false));
    g.setIndex(new THREE.BufferAttribute(idx, 1));
    g.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 900, 0), 6000);
    g.boundingBox = new THREE.Box3(new THREE.Vector3(-1e5, -1e5, -1e5), new THREE.Vector3(1e5, 1e5, 1e5));
    return g;
  }

  #initTextures() {
    const rows = Math.ceil(this.n / ROW);
    this.stateData = new Float32Array(ROW * 2 * rows * 4);
    this.stateTex = new THREE.DataTexture(this.stateData, ROW * 2, rows, THREE.RGBAFormat, THREE.FloatType);
    this.stateTex.minFilter = this.stateTex.magFilter = THREE.NearestFilter;
    this.dataData = new Float32Array(ROW * 8 * rows * 4);
    this.dataTex = new THREE.DataTexture(this.dataData, ROW * 8, rows, THREE.RGBAFormat, THREE.FloatType);
    this.dataTex.minFilter = this.dataTex.magFilter = THREE.NearestFilter;

    // animated per-piece state: current & target for vis, hover, sel, ghost, dim
    const n = this.n;
    this.cur = { vis: new Float32Array(n), hover: new Float32Array(n), sel: new Float32Array(n), ghost: new Float32Array(n), dim: new Float32Array(n) };
    this.tgt = { vis: new Float32Array(n), hover: new Float32Array(n), sel: new Float32Array(n), ghost: new Float32Array(n), dim: new Float32Array(n) };
    this.speed = { vis: 5.5, hover: 14, sel: 8, ghost: 5, dim: 5 };
    this.stateDirty = true;

    const q = this.manifest;
    this.uniforms = {
      uState: { value: this.stateTex },
      uData: { value: this.dataTex },
      uQMin: { value: new THREE.Vector3().fromArray(q.qmin) },
      uQScale: { value: new THREE.Vector3().fromArray(q.qscale) },
      uMorph: { value: 0 },
      uExplodeA: { value: 0 },
      uExplodeB: { value: 0 },
      uArc: { value: 260 },
      uTime: { value: 0 },
      uSelColor: { value: new THREE.Color("#57b3a0") },
      uMuscleColor: { value: new THREE.Color(SYSTEMS.muscles.color) },
      uGhostOpacity: { value: 1 },
    };

    // static per-piece data: colour, centres, separation
    const c = new THREE.Color();
    for (let i = 0; i < n; i++) {
      const p = this.pieces[i];
      const sys = SYSTEMS[p.s] || SYSTEMS.muscles;
      let hex = sys.color;
      const lname = p.en.toLowerCase();
      if (p.s !== 'muscles' && p.s !== 'arteries' && p.s !== 'veins') {
        for (const [re, h] of NAME_TINTS) if (re.test(lname)) { hex = h; break; }
      }
      if (p.s === 'skeleton') for (const [re, h] of SKELETON_TINTS) if (re.test(lname)) { hex = h; break; }
      c.set(hex); // Color.set() already converts sRGB -> linear working space
      // subtle per-piece variation so neighbouring muscles read as separate
      const v = p.s === 'muscles' ? 0.93 + 0.14 * hashf(i) : p.s === 'skeleton' ? 0.96 + 0.06 * hashf(i) : 0.95 + 0.1 * hashf(i);
      p.color = [c.r * v, c.g * v, c.b * v];
      p.idx = i;
      const bM = p.bM, bF = p.bF;
      p.cM = [(bM[0] + bM[3]) / 2, (bM[1] + bM[4]) / 2, (bM[2] + bM[5]) / 2];
      p.cF = [(bF[0] + bF[3]) / 2, (bF[1] + bF[4]) / 2, (bF[2] + bF[5]) / 2];
      p.size = Math.max(bM[3] - bM[0], bM[4] - bM[1], bM[5] - bM[2]);
      this.#setData(i, 0, p.color[0], p.color[1], p.color[2], sys.mat);
      this.#setData(i, 1, p.cM[0], p.cM[1], p.cM[2], hashf(i * 3.7 + 1));
      this.#setData(i, 2, p.cF[0], p.cF[1], p.cF[2], 0);
      if (p.breastShape) {
        const [cx, cy, rx, upperRy, lowerRy] = p.breastShape;
        this.#setData(i, 6, cx, cy, rx, upperRy);
        this.#setData(i, 7, lowerRy, 1, 0, 0);
      }
    }
  }

  #setData(i, k, x, y, z, w) {
    const o = (((i >> 8) * ROW * 8) + ((i & 255) << 3) + k) * 4;
    const d = this.dataData;
    d[o] = x; d[o + 1] = y; d[o + 2] = z; d[o + 3] = w;
  }

  #addChunk(geo, chunk) {
    const defines = {};
    const mat = new THREE.ShaderMaterial({
      glslVersion: THREE.GLSL3, vertexShader: atlasVertex, fragmentShader: atlasFragment, uniforms: this.uniforms,
      side: THREE.DoubleSide, defines,
    });
    const ghost = new THREE.ShaderMaterial({
      glslVersion: THREE.GLSL3, vertexShader: atlasVertex, fragmentShader: atlasFragment, uniforms: this.uniforms,
      side: THREE.FrontSide, transparent: true, depthWrite: false, defines: { GHOST: 1 },
    });
    const pick = new THREE.ShaderMaterial({
      glslVersion: THREE.GLSL3, vertexShader: pickVertex, fragmentShader: pickFragment, uniforms: this.uniforms, side: THREE.DoubleSide,
    });
    const m = new THREE.Mesh(geo, mat);
    m.frustumCulled = false;
    m.userData.system = chunk.system;
    const g = new THREE.Mesh(geo, ghost);
    g.frustumCulled = false; g.renderOrder = 10;
    const pk = new THREE.Mesh(geo, pick);
    pk.frustumCulled = false;
    this.group.add(m, g);
    this.meshes.push(m); this.ghostMeshes.push(g); this.pickMeshes.push(pk);
  }

  // ---------------------------------------------------------------- explode layouts
  #computeLayouts() {
    // separation offsets by system ("separated structures")
    const SEP = {
      skeleton: [-560, 0, -140], ligaments: [-300, 0, -60], muscles: [0, 0, 0], integument: [0, 0, 260],
      heart: [330, 0, 120], respiratory: [330, 0, 120], digestive: [330, 0, 120], urinary: [330, 0, 120],
      reproductive: [330, 0, 120], endocrine: [330, 0, 120], lymphatic: [330, 0, 120],
      arteries: [600, 0, -40], veins: [820, 0, -100], nervous: [-820, 0, 40], sensory: [-820, 0, 40],
    };
    const sysC = {};
    for (const p of this.pieces) {
      const s = sysC[p.s] || (sysC[p.s] = [0, 0, 0, 0]);
      s[0] += p.cM[0]; s[1] += p.cM[1]; s[2] += p.cM[2]; s[3]++;
    }
    for (const k in sysC) { const s = sysC[k]; s[0] /= s[3]; s[1] /= s[3]; s[2] /= s[3]; }
    for (const p of this.pieces) {
      const o = SEP[p.s] || [0, 0, 0];
      const s = sysC[p.s];
      const spread = 0.22;
      this.#setData(p.idx, 5, o[0] + (p.cM[0] - s[0]) * spread, (p.cM[1] - s[1]) * spread * 0.35, o[2] + (p.cM[2] - s[2]) * spread, 0);
    }
    this.dataTex.needsUpdate = true;
  }

  /** Lay out the given pieces (array of indices) as an inventory grid. aspect = width / height of the free view. */
  layoutGrid(ids, sexF, aspect = 1.7) {
    const order = this.systems;
    const list = ids.map((i) => this.pieces[i]).sort((a, b) => {
      const sa = order.indexOf(a.s), sb = order.indexOf(b.s);
      if (sa !== sb) return sa - sb;
      return b.size - a.size;
    });
    const gap = 14;
    // cell size per piece (sublinear in its extent, so tiny vessels stay legible)
    const cells = list.map((p) => {
      const b = sexF ? p.bF : p.bM;
      const w = b[3] - b[0], h = b[4] - b[1];
      const ext = Math.max(w, h, 1);
      const target = Math.min(150, Math.max(16, Math.pow(ext, 0.62) * 6.2));
      const s = Math.min(1.25, target / ext);
      return { p, w: w * s + gap, h: h * s + gap, s };
    });
    const area = cells.reduce((a, c) => a + c.w * c.h, 0);
    const pack = (W) => {
      let x = 0, y = 0, rowH = 0, lastSys = null;
      const placed = [];
      for (const c of cells) {
        if ((lastSys !== null && c.p.s !== lastSys && x > 0) || x + c.w > W) {
          y -= rowH + (c.p.s !== lastSys ? gap * 2.5 : 0);
          x = 0; rowH = 0;
        }
        lastSys = c.p.s;
        placed.push([c.p, x + c.w / 2, y - c.h / 2, c.s]);
        x += c.w; rowH = Math.max(rowH, c.h);
      }
      return { placed, H: -(y - rowH) };
    };
    // search the width whose packed block matches the screen aspect
    let W = Math.sqrt(area * aspect) * 1.1, res = pack(W);
    for (let it = 0; it < 6; it++) {
      const r = (W / res.H) / aspect;
      if (Math.abs(r - 1) < 0.04) break;
      W = W / Math.sqrt(r);
      res = pack(W);
    }
    const totalH = res.H;
    const cy = 900 + totalH / 2;
    for (const [p, px, py, s] of res.placed) {
      const gx = px - W / 2, gy = py + cy;
      this.#setData(p.idx, 3, gx, gy, 0, s);
      this.#setData(p.idx, 4, gx, gy, 0, s);
    }
    this.dataTex.needsUpdate = true;
    this.gridBounds = { w: W, h: totalH, cx: 0, cy: 900 };
    return this.gridBounds;
  }

  // ---------------------------------------------------------------- state
  setTarget(key, i, v) {
    if (this.tgt[key][i] !== v) { this.tgt[key][i] = v; this.stateDirty = true; }
  }
  setAll(key, v) {
    this.tgt[key].fill(v); this.stateDirty = true;
  }
  snap() {
    for (const k in this.cur) this.cur[k].set(this.tgt[k]);
    this.stateDirty = true;
  }

  update(dt) {
    this.time += dt;
    this.uniforms.uTime.value = this.time;
    if (!this.stateDirty) return;
    let moving = false;
    const n = this.n, sd = this.stateData;
    for (const k in this.cur) {
      const c = this.cur[k], t = this.tgt[k];
      const a = 1 - Math.exp(-dt * this.speed[k]);
      for (let i = 0; i < n; i++) {
        const d = t[i] - c[i];
        if (d !== 0) {
          if (Math.abs(d) < 0.003) c[i] = t[i];
          else { c[i] += d * a; moving = true; }
        }
      }
    }
    const { vis, hover, sel, ghost, dim } = this.cur;
    for (let i = 0; i < n; i++) {
      const o = (((i >> 8) * ROW * 2) + ((i & 255) << 1)) * 4;
      sd[o] = vis[i]; sd[o + 1] = hover[i]; sd[o + 2] = sel[i]; sd[o + 3] = ghost[i];
      sd[o + 4] = dim[i];
    }
    this.stateTex.needsUpdate = true;
    this.stateDirty = moving;
    this.#cullChunks();
  }

  #cullChunks() {
    const { vis, ghost } = this.cur;
    this.meshes.forEach((m, k) => {
      let solid = false, ghosted = false, pickable = false;
      for (const i of m.userData.ids) {
        if (vis[i] > 0.002) {
          if (ghost[i] < 0.998) solid = true;
          if (ghost[i] > 0.002) ghosted = true;
          if (this.tgt.vis[i] > 0.5 && this.tgt.ghost[i] < 0.5) pickable = true;
        }
        if (solid && ghosted && pickable) break;
      }
      m.visible = solid;
      this.ghostMeshes[k].visible = ghosted;
      this.pickMeshes[k].visible = pickable;
    });
  }

  isVisible(i) { return this.tgt.vis[i] > 0.5 && this.tgt.ghost[i] < 0.5; }

  // ---------------------------------------------------------------- picking
  initPicking() {
    this.pickTarget = new THREE.WebGLRenderTarget(1, 1, { type: THREE.UnsignedByteType });
    this.pickScene = new THREE.Scene();
    for (const m of this.pickMeshes) this.pickScene.add(m);
    this.pickBuf = new Uint8Array(4);
  }

  pick(camera, x, y, w, h) {
    if (!this.pickTarget) this.initPicking();
    const r = this.renderer;
    const cam = camera.clone();
    const dpr = r.getPixelRatio();
    const ox = camera.view ? camera.view.offsetX : 0, oy = camera.view ? camera.view.offsetY : 0;
    cam.setViewOffset(w * dpr, h * dpr, Math.floor((x + ox) * dpr), Math.floor((y + oy) * dpr), 1, 1);
    cam.updateProjectionMatrix();
    const prevTarget = r.getRenderTarget();
    const prevClear = r.getClearColor(new THREE.Color());
    const prevAlpha = r.getClearAlpha();
    r.setRenderTarget(this.pickTarget);
    r.setClearColor(0x000000, 0);
    r.clear();
    r.render(this.pickScene, cam);
    r.readRenderTargetPixels(this.pickTarget, 0, 0, 1, 1, this.pickBuf);
    r.setRenderTarget(prevTarget);
    r.setClearColor(prevClear, prevAlpha);
    const id = this.pickBuf[0] + (this.pickBuf[1] << 8) + (this.pickBuf[2] << 16);
    return id - 1;
  }

  // ---------------------------------------------------------------- geometry queries (CPU mirror of the shader)
  pieceCenter(i, out = new THREE.Vector3(), morph) {
    const p = this.pieces[i], m = morph ?? this.uniforms.uMorph.value;
    return out.set(p.cM[0] + (p.cF[0] - p.cM[0]) * m, p.cM[1] + (p.cF[1] - p.cM[1]) * m, p.cM[2] + (p.cF[2] - p.cM[2]) * m);
  }

  pieceBox(i, box = new THREE.Box3(), morph) {
    const p = this.pieces[i], m = morph ?? this.uniforms.uMorph.value;
    const b = p.bM.map((v, k) => v + (p.bF[k] - v) * m);
    return box.set(new THREE.Vector3(b[0], b[1], b[2]), new THREE.Vector3(b[3], b[4], b[5]));
  }

  /** Current (exploded) centre of a piece, mirrors atlasPosition() in the shader. */
  livePieceCenter(i, out = new THREE.Vector3()) {
    const u = this.uniforms;
    this.pieceCenter(i, out);
    const o5 = this.#getData(i, 5), o1 = this.#getData(i, 1), o3 = this.#getData(i, 3);
    out.x += o5[0] * u.uExplodeA.value; out.y += o5[1] * u.uExplodeA.value; out.z += o5[2] * u.uExplodeA.value;
    let t = Math.min(1, Math.max(0, u.uExplodeB.value * 1.5 - o1[3] * 0.5));
    t = t * t * (3 - 2 * t);
    if (t > 0) {
      out.lerp(new THREE.Vector3(o3[0], o3[1], o3[2]), t);
      out.z += Math.sin(t * Math.PI) * u.uArc.value * (0.35 + o1[3]);
    }
    return out;
  }

  liveScale(i) {
    const u = this.uniforms;
    const o1 = this.#getData(i, 1), o3 = this.#getData(i, 3);
    let t = Math.min(1, Math.max(0, u.uExplodeB.value * 1.5 - o1[3] * 0.5));
    t = t * t * (3 - 2 * t);
    return 1 + (o3[3] - 1) * t;
  }

  #getData(i, k) {
    const o = (((i >> 8) * ROW * 8) + ((i & 255) << 3) + k) * 4;
    return this.dataData.subarray(o, o + 4);
  }
}
