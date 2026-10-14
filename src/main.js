import * as THREE from 'three';
import { Atlas, SYSTEMS } from './engine/atlas.js';
import { CameraRig } from './engine/camera.js';
import { shadowVertex, shadowFragment } from './engine/shaders.js';
import { UI } from './ui.js';

const DATA_URL = import.meta.env.BASE_URL + 'data/';

// ------------------------------------------------------------------ renderer
const canvas = document.getElementById('scene');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setClearColor(0x000000, 0);
renderer.outputColorSpace = THREE.LinearSRGBColorSpace; // shaders output sRGB themselves

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(26, 1, 10, 30000);
const rig = new CameraRig(camera, canvas);

// soft floor shadow
const shadow = new THREE.Mesh(
  new THREE.PlaneGeometry(1300, 1300),
  new THREE.ShaderMaterial({ glslVersion: THREE.GLSL3, vertexShader: shadowVertex, fragmentShader: shadowFragment, transparent: true, depthWrite: false, uniforms: { uOpacity: { value: 1 } } }),
);
shadow.rotation.x = -Math.PI / 2;
shadow.position.y = -2;
shadow.renderOrder = -1;
scene.add(shadow);

function resize() {
  const w = window.innerWidth, h = window.innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize);
resize();

// ------------------------------------------------------------------ load
const loaderFill = document.getElementById('loaderFill');
const loaderText = document.getElementById('loaderText');
const atlas = new Atlas(renderer);

(async () => {
  try {
    await atlas.load(DATA_URL, (f) => { loaderFill.style.width = (f * 100).toFixed(1) + '%'; });
  } catch (err) {
    console.error(err);
    loaderText.textContent = '模型加载失败：' + err.message;
    return;
  }
  scene.add(atlas.group);
  loaderText.textContent = '准备场景…';
  const ui = new UI({ atlas, rig, camera, renderer, canvas, shadow });
  window.__atlas = { atlas, rig, ui, camera, renderer, THREE };
  await ui.init();
  atlas.snap();
  // warm up shaders before revealing
  renderer.compile(scene, camera);
  requestAnimationFrame(() => {
    document.getElementById('loader').classList.add('done');
    ui.intro();
  });
  start(ui);
})();

function start(ui) {
  let last = performance.now();
  const clock = () => {
    const now = performance.now();
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    ui.update(dt);
    rig.update(dt);
    atlas.update(dt);
    ui.postCamera(dt);
    renderer.render(scene, camera);
    requestAnimationFrame(clock);
  };
  requestAnimationFrame(clock);
}
