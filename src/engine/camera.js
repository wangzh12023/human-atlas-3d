import * as THREE from 'three';

const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const TAU = Math.PI * 2;

function wrapAngle(a) {
  a = ((a + Math.PI) % TAU + TAU) % TAU - Math.PI;
  return a;
}

/**
 * Spherical orbit controller with inertia, damped zoom/pan and smooth "fly to" transitions.
 * State: target (vec3), yaw (around +Y, 0 = looking at subject's front), pitch, distance.
 */
export class CameraRig {
  constructor(camera, dom) {
    this.camera = camera;
    this.dom = dom;
    this.target = new THREE.Vector3(0, 900, 0);
    this.yaw = 0; this.pitch = 0.04; this.dist = 2600;
    this.goal = { target: this.target.clone(), yaw: 0, pitch: 0.04, dist: 2600 };
    this.vel = { yaw: 0, pitch: 0, panX: 0, panY: 0 };
    this.anim = null;
    this.autoRotate = false;
    this.autoSpeed = 0.16;
    this.minDist = 60; this.maxDist = 9000;
    this.mode = 'orbit'; // 'orbit' | 'pan' (inventory grid)
    this.enabled = true;
    this.onInteract = null;
    this.pointers = new Map();
    // screen-space safe area (px) the content should be framed into; produces a lens shift
    this.insets = { left: 0, right: 0, top: 0, bottom: 0 };
    this.shift = { x: 0, y: 0 };
    this.#bind();
  }

  /** free (unoccluded) viewport size in px */
  freeSize() {
    const w = this.dom.clientWidth, h = this.dom.clientHeight, i = this.insets;
    const side = Math.max(i.left, i.right);
    return { w: Math.max(120, w - 2 * side), h: Math.max(120, h - i.top - i.bottom) };
  }

  // ---------------------------------------------------------------- input
  #bind() {
    const d = this.dom;
    d.addEventListener('pointerdown', (e) => this.#down(e));
    window.addEventListener('pointermove', (e) => this.#move(e));
    window.addEventListener('pointerup', (e) => this.#up(e));
    window.addEventListener('pointercancel', (e) => this.#up(e));
    d.addEventListener('wheel', (e) => this.#wheel(e), { passive: false });
    d.addEventListener('contextmenu', (e) => e.preventDefault());
  }

  #down(e) {
    if (!this.enabled) return;
    this.dom.setPointerCapture?.(e.pointerId);
    this.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY, button: e.button });
    this.dragStart = { x: e.clientX, y: e.clientY, t: performance.now() };
    this.dragged = false;
    this.anim = null;
    this.vel.yaw = this.vel.pitch = this.vel.panX = this.vel.panY = 0;
    this.dom.classList.add('grabbing');
    if (this.pointers.size === 2) {
      const [a, b] = [...this.pointers.values()];
      this.pinch = { d: Math.hypot(a.x - b.x, a.y - b.y), dist: this.goal.dist };
    }
  }

  #move(e) {
    const p = this.pointers.get(e.pointerId);
    if (!p) return;
    const dx = e.clientX - p.x, dy = e.clientY - p.y;
    p.x = e.clientX; p.y = e.clientY;
    this.lastMoveT = performance.now();
    if (Math.hypot(e.clientX - this.dragStart.x, e.clientY - this.dragStart.y) > 4) {
      if (!this.dragged) { this.dragged = true; this.onInteract && this.onInteract('drag'); }
    }
    if (this.pointers.size === 2 && this.pinch) {
      const [a, b] = [...this.pointers.values()];
      const d = Math.hypot(a.x - b.x, a.y - b.y);
      this.goal.dist = THREE.MathUtils.clamp(this.pinch.dist * this.pinch.d / Math.max(d, 1), this.minDist, this.maxDist);
      return;
    }
    const pan = this.mode === 'pan' || p.button === 2 || p.button === 1 || e.shiftKey;
    if (pan) {
      this.#panBy(dx, dy);
      this.vel.panX = dx; this.vel.panY = dy;
    } else {
      const k = 0.0058;
      this.goal.yaw -= dx * k;
      this.goal.pitch = THREE.MathUtils.clamp(this.goal.pitch + dy * k, -1.35, 1.35);
      this.vel.yaw = -dx * k; this.vel.pitch = dy * k;
    }
  }

  #up(e) {
    if (!this.pointers.has(e.pointerId)) return;
    this.pointers.delete(e.pointerId);
    if (this.pointers.size < 2) this.pinch = null;
    if (this.pointers.size === 0) this.dom.classList.remove('grabbing');
    // drop inertia if the pointer rested before release
    if (performance.now() - (this.lastMoveT || 0) > 90) { this.vel.yaw = this.vel.pitch = this.vel.panX = this.vel.panY = 0; }
  }

  #panBy(dx, dy) {
    const h = this.dom.clientHeight;
    const worldPerPx = (2 * this.goal.dist * Math.tan(THREE.MathUtils.degToRad(this.camera.fov) / 2)) / h;
    const m = this.camera.matrixWorld.elements;
    const right = new THREE.Vector3(m[0], m[1], m[2]).normalize();
    const up = this.mode === 'pan' ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(m[4], m[5], m[6]).normalize();
    this.goal.target.addScaledVector(right, -dx * worldPerPx);
    this.goal.target.addScaledVector(up, dy * worldPerPx);
    this.#clampTarget();
  }

  #clampTarget() {
    const b = this.bounds;
    if (!b) return;
    this.goal.target.x = THREE.MathUtils.clamp(this.goal.target.x, b.min.x, b.max.x);
    this.goal.target.y = THREE.MathUtils.clamp(this.goal.target.y, b.min.y, b.max.y);
    this.goal.target.z = THREE.MathUtils.clamp(this.goal.target.z, b.min.z, b.max.z);
  }

  #wheel(e) {
    if (!this.enabled) return;
    e.preventDefault();
    this.anim = null;
    const delta = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY;
    const f = Math.exp(delta * 0.0012);
    const newDist = THREE.MathUtils.clamp(this.goal.dist * f, this.minDist, this.maxDist);
    // zoom toward the cursor
    const rect = this.dom.getBoundingClientRect();
    const nx = (e.clientX - rect.left) / rect.width - 0.5;
    const ny = (e.clientY - rect.top) / rect.height - 0.5;
    const h = rect.height;
    const worldPerPx = (2 * this.goal.dist * Math.tan(THREE.MathUtils.degToRad(this.camera.fov) / 2)) / h;
    const worldPerPx2 = (2 * newDist * Math.tan(THREE.MathUtils.degToRad(this.camera.fov) / 2)) / h;
    const k = (worldPerPx - worldPerPx2);
    const m = this.camera.matrixWorld.elements;
    const right = new THREE.Vector3(m[0], m[1], m[2]).normalize();
    const up = new THREE.Vector3(m[4], m[5], m[6]).normalize();
    this.goal.target.addScaledVector(right, nx * rect.width * k);
    this.goal.target.addScaledVector(up, -ny * rect.height * k);
    this.#clampTarget();
    this.goal.dist = newDist;
    this.onInteract && this.onInteract('zoom');
  }

  // ---------------------------------------------------------------- transitions
  /** Smoothly fly to a view. duration in seconds. yaw is chosen along the shortest path. */
  flyTo({ target, yaw, pitch, dist }, duration = 1.4) {
    const from = { target: this.goal.target.clone(), yaw: this.goal.yaw, pitch: this.goal.pitch, dist: this.goal.dist };
    const to = {
      target: target ? target.clone() : from.target.clone(),
      yaw: yaw === undefined ? from.yaw : from.yaw + wrapAngle(yaw - from.yaw),
      pitch: pitch === undefined ? from.pitch : pitch,
      dist: dist === undefined ? from.dist : dist,
    };
    // when the move is long, arc out (zoom out mid-flight) for a cinematic feel
    const travel = from.target.distanceTo(to.target);
    const arc = Math.min(0.55, travel / Math.max(from.dist, to.dist) * 0.35);
    this.vel.yaw = this.vel.pitch = this.vel.panX = this.vel.panY = 0;
    this.anim = { from, to, t: 0, duration: Math.max(0.01, duration), arc };
    return new Promise((res) => { this.anim.resolve = res; });
  }

  /** distance at which a box of world size (sw x sh) fills `fill` of the free viewport */
  fitDistance(sw, sh, fill = 0.8) {
    const H = this.dom.clientHeight, W = this.dom.clientWidth;
    const f = this.freeSize();
    const t = Math.tan(THREE.MathUtils.degToRad(this.camera.fov) / 2);
    const dV = (sh / 2) / (t * f.h / H) / fill;
    const dH = (sw / 2) / (t * (W / H) * f.w / W) / fill;
    return Math.max(dV, dH);
  }

  frameBox(box, { yaw, pitch, fill = 0.72, duration = 1.4, offset } = {}) {
    const c = box.getCenter(new THREE.Vector3());
    const s = box.getSize(new THREE.Vector3());
    const radius = Math.max(s.x, s.z) / 2;
    const dist = this.fitDistance(Math.max(s.x, s.z), s.y, fill) + radius * 0.6;
    if (offset) c.add(offset);
    return this.flyTo({ target: c, yaw, pitch, dist: THREE.MathUtils.clamp(dist, this.minDist, this.maxDist) }, duration);
  }

  // ---------------------------------------------------------------- per frame
  update(dt) {
    const g = this.goal;
    if (this.anim) {
      const a = this.anim;
      a.t = Math.min(1, a.t + dt / a.duration);
      const k = easeInOut(a.t);
      g.target.lerpVectors(a.from.target, a.to.target, k);
      g.yaw = a.from.yaw + (a.to.yaw - a.from.yaw) * k;
      g.pitch = a.from.pitch + (a.to.pitch - a.from.pitch) * k;
      const baseDist = Math.exp(Math.log(a.from.dist) + (Math.log(a.to.dist) - Math.log(a.from.dist)) * k);
      g.dist = baseDist * (1 + a.arc * Math.sin(Math.PI * k));
      if (a.t >= 1) { const r = a.resolve; this.anim = null; r && r(); }
      // follow the goal closely while animating
      this.target.copy(g.target); this.yaw = g.yaw; this.pitch = g.pitch; this.dist = g.dist;
    } else {
      if (this.pointers.size === 0) {
        // inertia
        const decay = Math.exp(-dt * 4.2);
        if (Math.abs(this.vel.yaw) > 1e-5 || Math.abs(this.vel.pitch) > 1e-5) {
          g.yaw += this.vel.yaw * 0.9; g.pitch = THREE.MathUtils.clamp(g.pitch + this.vel.pitch * 0.9, -1.35, 1.35);
          this.vel.yaw *= decay; this.vel.pitch *= decay;
        }
        if (Math.abs(this.vel.panX) > 0.05 || Math.abs(this.vel.panY) > 0.05) {
          this.#panBy(this.vel.panX * 0.6, this.vel.panY * 0.6);
          this.vel.panX *= decay; this.vel.panY *= decay;
        }
        if (this.autoRotate) g.yaw += this.autoSpeed * dt;
      }
      const s = 1 - Math.exp(-dt * 10);
      this.target.lerp(g.target, s);
      this.yaw += (g.yaw - this.yaw) * s;
      this.pitch += (g.pitch - this.pitch) * s;
      this.dist = Math.exp(Math.log(this.dist) + (Math.log(g.dist) - Math.log(this.dist)) * (1 - Math.exp(-dt * 8)));
    }
    const cp = Math.cos(this.pitch);
    this.camera.position.set(
      this.target.x + Math.sin(this.yaw) * cp * this.dist,
      this.target.y + Math.sin(this.pitch) * this.dist,
      this.target.z + Math.cos(this.yaw) * cp * this.dist,
    );
    this.camera.lookAt(this.target);
    // lens shift so the target sits in the centre of the free area
    const W = this.dom.clientWidth, H = this.dom.clientHeight, ins = this.insets;
    const sx = this.shiftX ?? 0, wantY = (ins.bottom - ins.top) / 2;
    const ks = 1 - Math.exp(-dt * 6);
    this.shift.x += (sx - this.shift.x) * ks;
    this.shift.y += (wantY - this.shift.y) * ks;
    this.camera.setViewOffset(W, H, -this.shift.x, this.shift.y, W, H);
    // adapt clip planes to distance for depth precision
    this.camera.near = Math.max(1, this.dist * 0.02);
    this.camera.far = this.dist * 6 + 12000;
    this.camera.updateProjectionMatrix();
  }

  isAnimating() { return !!this.anim; }
}
