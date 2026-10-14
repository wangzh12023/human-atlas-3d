// Validate what a fresh clone actually ships, including decoded mesh chunks.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { MeshoptDecoder } from 'meshoptimizer/decoder';
import { REGIONS } from '../src/content/regions.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const data = path.join(root, 'public', 'data');
const manifest = JSON.parse(fs.readFileSync(path.join(data, 'manifest.json'), 'utf8'));
const { pieces, chunks, systems, qmin, qscale } = manifest;
assert(pieces.length > 0 && chunks.length > 0 && systems.length > 0);
assert(qmin.length === 3 && qmin.every(Number.isFinite));
assert(qscale.length === 3 && qscale.every(v => Number.isFinite(v) && v > 0));
const ids = new Set();
pieces.forEach((p, i) => {
  assert.equal(p.id, i, 'Piece IDs must match manifest order');
  assert([0, 1, 2].includes(p.x) && systems.includes(p.s));
  for (const box of [p.bM, p.bF]) {
    assert(box.length === 6 && box.every(Number.isFinite));
    assert(box.slice(0, 3).every((v, k) => v <= box[k + 3]));
  }
});
await MeshoptDecoder.ready;
let vertices = 0, triangles = 0, bytes = 0;
for (const chunk of chunks) {
  assert(/^[\w-]+$/.test(chunk.name) && systems.includes(chunk.system));
  const buf = fs.readFileSync(path.join(data, chunk.name + '.bin'));
  assert.equal(buf.length, chunk.bytes);
  const nv = buf.readUInt32LE(0), ni = buf.readUInt32LE(4);
  const vl = buf.readUInt32LE(8), il = buf.readUInt32LE(12);
  assert.equal(nv, chunk.vertexCount);
  assert.equal(ni, chunk.indexCount);
  assert.equal(ni % 3, 0);
  assert.equal(16 + vl + il, buf.length);
  const vert = new Uint8Array(nv * 20);
  const index = new Uint32Array(ni);
  MeshoptDecoder.decodeVertexBuffer(vert, nv, 20, buf.subarray(16, 16 + vl));
  MeshoptDecoder.decodeIndexBuffer(new Uint8Array(index.buffer), ni, 4, buf.subarray(16 + vl));
  const u16 = new Uint16Array(vert.buffer);
  for (let v = 0; v < nv; v++) {
    const pid = u16[v * 10 + 3], p = pieces[pid];
    assert(p && p.s === chunk.system, 'Invalid piece reference');
    ids.add(pid);
    if (!p.x && p.en !== 'Skin') {
      for (let k = 0; k < 3; k++) assert.equal(u16[v * 10 + k], u16[v * 10 + 4 + k], 'Shared body geometry differs across sexes');
    }
    for (const [offset, box] of [[0, p.bM], [4, p.bF]]) {
      for (let k = 0; k < 3; k++) {
        const coordinate = qmin[k] + u16[v * 10 + offset + k] * qscale[k];
        const tolerance = 0.11 + qscale[k];
        assert(coordinate >= box[k] - tolerance && coordinate <= box[k + 3] + tolerance, 'Manifest bounds do not cover decoded vertices');
      }
    }
  }
  for (let i = 0; i < ni; i += 3) {
    const a = index[i], b = index[i + 1], c = index[i + 2];
    assert(a < nv && b < nv && c < nv);
    assert(u16[a * 10 + 3] === u16[b * 10 + 3] && u16[a * 10 + 3] === u16[c * 10 + 3], 'Triangle spans multiple structures');
  }
  vertices += nv; triangles += ni / 3; bytes += buf.length;
}
assert.equal(ids.size, pieces.length, 'Some structures have no geometry');

for (const file of ['README.md', 'README.en.md', 'CONTRIBUTING.md', 'docs/DEPLOYMENT.md', 'docs/PIPELINE.md']) {
  const text = fs.readFileSync(path.join(root, file), 'utf8');
  const links = [...text.matchAll(/\]\(([^)]+)\)|\bsrc="([^"]+)"/g)].map(m => m[1] || m[2]);
  for (const link of links) {
    if (/^(https?:|#|mailto:)/.test(link)) continue;
    const target = decodeURIComponent(link.split('#')[0]);
    assert(fs.existsSync(path.resolve(root, path.dirname(file), target)), `Broken link in ${file}: ${link}`);
  }
}
for (const file of ['public/ATTRIBUTION.md', 'public/data/LICENSE', 'public/data/sources.json', 'public/licenses/Inter-OFL.txt']) {
  assert(fs.existsSync(path.join(root, file)), 'Missing attribution asset: ' + file);
}
console.log(`✓ ${pieces.length} pieces, ${systems.length} systems, ${REGIONS.length} regions`);
console.log(`✓ ${vertices.toLocaleString()} vertices, ${triangles.toLocaleString()} triangles, ${(bytes / 1048576).toFixed(1)} MiB decoded successfully`);
console.log('✓ Shared geometry, indices, bounds, documentation links, and attribution assets');
