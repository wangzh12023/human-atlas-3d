// Encode raw chunk buffers produced by export.py with meshoptimizer.
// usage: node pipeline/encode.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { MeshoptEncoder } from 'meshoptimizer';

const here = path.dirname(fileURLToPath(import.meta.url));
const RAW = path.join(here, 'raw');
const OUT = path.join(here, '..', 'public', 'data');
fs.mkdirSync(OUT, { recursive: true });

await MeshoptEncoder.ready;
const manifest = JSON.parse(fs.readFileSync(path.join(RAW, 'manifest.json'), 'utf8'));
const STRIDE = 20;
let total = 0;
for (const c of manifest.chunks) {
  const file = fs.readFileSync(path.join(RAW, c.name + '.raw'));
  const ab = file.buffer.slice(file.byteOffset, file.byteOffset + file.length);
  const dv = new DataView(ab);
  const nV = dv.getUint32(0, true), nI = dv.getUint32(4, true);
  const vert = new Uint8Array(ab, 8, nV * STRIDE);
  const idx = new Uint32Array(ab.slice(8 + nV * STRIDE, 8 + nV * STRIDE + nI * 4));
  // Vertex-cache optimisation keeps the same vertex set (only reorders), so remap the vertex struct too.
  const [remap, unique] = MeshoptEncoder.reorderMesh(idx, true, false);
  const vert2 = new Uint8Array(unique * STRIDE);
  for (let i = 0; i < nV; i++) {
    const r = remap[i];
    if (r === 0xffffffff) continue;
    vert2.set(vert.subarray(i * STRIDE, i * STRIDE + STRIDE), r * STRIDE);
  }
  const vEnc = MeshoptEncoder.encodeVertexBuffer(vert2, unique, STRIDE);
  const iEnc = MeshoptEncoder.encodeIndexBuffer(new Uint8Array(idx.buffer), nI, 4);
  const header = Buffer.alloc(16);
  header.writeUInt32LE(unique, 0); header.writeUInt32LE(nI, 4);
  header.writeUInt32LE(vEnc.length, 8); header.writeUInt32LE(iEnc.length, 12);
  const out = Buffer.concat([header, Buffer.from(vEnc), Buffer.from(iEnc)]);
  fs.writeFileSync(path.join(OUT, c.name + '.bin'), out);
  c.vertexCount = unique;
  c.bytes = out.length;
  total += out.length;
  console.log(c.name, 'verts', unique, 'tris', nI / 3, (out.length / 1024 / 1024).toFixed(2) + ' MB');
}
fs.writeFileSync(path.join(OUT, 'manifest.json'), JSON.stringify(manifest));
console.log('total', (total / 1024 / 1024).toFixed(2), 'MB');
