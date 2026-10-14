"""Step 3: export all pieces to raw chunk buffers + manifest/metadata.

Reads  CACHE/male_pieces.pkl              (from build_male.py)
       CACHE/female_map.pkl  (optional)   (from build_female.py: per-piece female positions)
       CACHE/extra_pieces.pkl (optional)  (procedural / female-only / HRA pieces)
Writes body/pipeline/raw/*.raw  (vertex struct 20 B + u32 indices) -> encoded by encode.mjs
       body/public/data/pieces.json
"""
import os, sys, json, time, struct
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from encode import oct_encode
from ao import bake_ao

t0 = time.time()
RAW = os.path.join(HERE, 'raw')
os.makedirs(RAW, exist_ok=True)

SYSTEM_ORDER = ['skeleton', 'muscles', 'ligaments', 'heart', 'arteries', 'veins', 'nervous', 'sensory',
                'respiratory', 'digestive', 'urinary', 'reproductive', 'endocrine', 'lymphatic', 'integument']

pieces = load_pickle('all_pieces.pkl')   # from assemble.py (vM, vF, f, sex, kind ...)
print('pieces:', len(pieces))

# normals
for p in pieces:
    p['vM'] = np.asarray(p['vM'], np.float64); p['vF'] = np.asarray(p['vF'], np.float64)
    p['f'] = np.asarray(p['f'], np.int64)
    p['nM'] = vertex_normals(p['vM'], p['f'])
    p['nF'] = np.asarray(p['normalF'], np.float64) if 'normalF' in p else vertex_normals(p['vF'], p['f'])
print('normals %.1fs' % (time.time() - t0))

# ambient occlusion, per system, both sexes
male_pieces = [p for p in pieces if p['sex'] != 2]
bake_ao(male_pieces, key='vM', nkey='nM')
for p in male_pieces:
    p['aoM'] = p.pop('ao')
fem_pieces = [p for p in pieces if p['sex'] != 1]
bake_ao(fem_pieces, key='vF', nkey='nF')
for p in fem_pieces:
    p['aoF'] = p.pop('ao')
for p in pieces:
    if 'aoF' not in p:
        p['aoF'] = p['aoM']
    if 'aoM' not in p:
        p['aoM'] = p['aoF']
print('ao %.1fs' % (time.time() - t0))

# order: by system then by size
pieces.sort(key=lambda p: (SYSTEM_ORDER.index(p['system']), -float(np.prod(p['vM'].max(0) - p['vM'].min(0) + 1))))
for i, p in enumerate(pieces):
    p['id'] = i

allv = np.concatenate([np.concatenate([p['vM'], p['vF']]) for p in pieces])
qmin = allv.min(0) - 1.0
qmax = allv.max(0) + 1.0
qscale = (qmax - qmin) / 65535.0


def q(v):
    return np.clip(np.round((v - qmin) / qscale), 0, 65535).astype(np.uint16)


# chunks: one per system (the integument / big systems may be split to keep chunks < ~400k verts)
chunks = []
for s in SYSTEM_ORDER:
    ps = [p for p in pieces if p['system'] == s]
    if not ps:
        continue
    cur = []; nv = 0
    for p in ps:
        if cur and nv + len(p['vM']) > 300000:
            chunks.append((s, cur)); cur = []; nv = 0
        cur.append(p); nv += len(p['vM'])
    if cur:
        chunks.append((s, cur))

manifest = dict(qmin=qmin.tolist(), qscale=qscale.tolist(), chunks=[])
for ci, (s, ps) in enumerate(chunks):
    nV = sum(len(p['vM']) for p in ps)
    vert = np.zeros(nV, dtype=[('pM', '<u2', 3), ('pid', '<u2'), ('pF', '<u2', 3), ('aoM', 'u1'), ('aoF', 'u1'),
                               ('nM', 'i1', 2), ('nF', 'i1', 2)])
    idx = []
    o = 0
    for p in ps:
        n = len(p['vM'])
        sl = slice(o, o + n)
        vert['pM'][sl] = q(p['vM']); vert['pF'][sl] = q(p['vF'])
        vert['pid'][sl] = p['id']
        vert['aoM'][sl] = np.round(p['aoM'] * 255); vert['aoF'][sl] = np.round(p['aoF'] * 255)
        vert['nM'][sl] = oct_encode(p['nM']); vert['nF'][sl] = oct_encode(p['nF'])
        idx.append(p['f'] + o)
        o += n
    idx = np.concatenate(idx).astype(np.uint32).reshape(-1)
    assert vert.dtype.itemsize == 20
    name = '%02d_%s' % (ci, s)
    with open(os.path.join(RAW, name + '.raw'), 'wb') as fh:
        fh.write(struct.pack('<II', nV, len(idx)))
        fh.write(vert.tobytes()); fh.write(idx.tobytes())
    manifest['chunks'].append(dict(name=name, system=s, vertexCount=int(nV), indexCount=int(len(idx))))
    print('chunk', name, nV, 'verts', len(idx) // 3, 'tris')

meta = []
for p in pieces:
    bM = np.concatenate([p['vM'].min(0), p['vM'].max(0)]).round(1).tolist()
    bF = np.concatenate([p['vF'].min(0), p['vF'].max(0)]).round(1).tolist()
    meta.append(dict(id=p['id'], en=p['en'], zh=p['zh'], s=p['system'], x=p['sex'], fma=p.get('fma', ''),
                     f=p.get('file', ''), bM=bM, bF=bF, k=p.get('kind', '')))
    if 'breast_shape' in p:
        meta[-1]['breastShape'] = p['breast_shape']
manifest['pieces'] = meta
manifest['systems'] = SYSTEM_ORDER
write_json(manifest, os.path.join(RAW, 'manifest.json'))
print('pieces', len(meta), 'done %.1fs' % (time.time() - t0))
