"""Step 1: load every BodyParts3D piece, dedupe, decimate, compute normals.

writes CACHE/male_pieces.pkl : list of dicts
  file, fma, en, zh, system, v (float32 world mm), f (int32), src_faces
"""
import os, re, sys, json, time, collections
import numpy as np
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

t0 = time.time()
rows = json.load(open(os.path.join(BP3D, 'pieces_classified.json'), encoding='utf-8'))
zh_map = json.load(open(os.path.join(HERE, 'zh_map.json'), encoding='utf-8'))


def zh_name(en):
    m = re.match(r'^(left|right)\s+(.*)$', en.strip(), flags=re.I)
    side, base = (m.group(1).lower(), m.group(2)) if m else (None, en.strip())
    z = zh_map.get(base.lower())
    if z is None:
        z = zh_map.get(en.strip().lower(), en)
    if side and not z.startswith(('左', '右')):
        z = ('左' if side == 'left' else '右') + z
    return z


def title_case(s):
    small = {'of', 'the', 'to', 'and', 'with', 'in', 'for', 'on'}
    out = []
    for i, w in enumerate(s.split(' ')):
        if i > 0 and w.lower() in small:
            out.append(w.lower())
        elif re.fullmatch(r'[ivx]+', w.lower()) and i > 0:
            out.append(w.upper())
        else:
            out.append(w[:1].upper() + w[1:])
    return ' '.join(out)


# ---------------------------------------------------------------- load
pieces = []
for r in rows:
    v, f = load_obj(os.path.join(BP3D_OBJ, r['file'] + '.obj'))
    v = bp3d_to_world(v)
    v, f = clean_mesh(v, f)
    v, f = weld(v, f, 1e-3)
    v, f = clean_mesh(v, f)
    pieces.append(dict(file=r['file'], fma=r['fma'] or '', en=title_case(r['name']), zh=zh_name(r['name']),
                       system=r['system'], v=v, f=f, src_faces=len(f), derived=bool(r.get('derived'))))
print('loaded', len(pieces), 'pieces in %.1fs' % (time.time() - t0))

# ---------------------------------------------------------------- dedupe
lo = np.array([p['v'].min(0) for p in pieces]); hi = np.array([p['v'].max(0) for p in pieces])
vol = np.prod(hi - lo + 1e-3, 1)
trees = {}


def tree(i):
    if i not in trees:
        trees[i] = cKDTree(pieces[i]['v'])
    return trees[i]


def name_score(p):
    n = p['en'].lower(); s = -10 if p['derived'] else 0
    for bad in ('set of', 'segment', 'zone of', 'part of', 'pre-hepatic', 'parenchyma', 'marginal colic', 'celiac artery', 'trunk of'):
        if bad in n:
            s -= 1
    return (s, p['src_faces'])


drop = set()
for i in range(len(pieces)):
    if i in drop:
        continue
    il = np.maximum(lo[i], lo); ih = np.minimum(hi[i], hi)
    inter = np.prod(np.clip(ih - il, 0, None), 1)
    iou = inter / (vol[i] + vol - inter)
    for j in np.where(iou > 0.9)[0]:
        if j <= i or j in drop:
            continue
        a, b = pieces[i], pieces[j]
        da = tree(j).query(a['v'][::max(1, len(a['v']) // 400)])[0].mean()
        db = tree(i).query(b['v'][::max(1, len(b['v']) // 400)])[0].mean()
        if max(da, db) < 0.8:
            loser = j if name_score(a) >= name_score(b) else i
            drop.add(loser)
            print('  dup %-45s | %-45s -> drop %s' % (a['en'][:45], b['en'][:45], pieces[loser]['file']))
            if loser == i:
                break
pieces = [p for k, p in enumerate(pieces) if k not in drop]
print('after dedupe', len(pieces))

# ---------------------------------------------------------------- decimate
RATIO = dict(muscles=0.22, skeleton=0.36, arteries=0.24, veins=0.24, nervous=0.25, digestive=0.35, respiratory=0.42,
             heart=0.5, sensory=0.25, ligaments=0.45, integument=0.4, reproductive=1.0, urinary=0.8, endocrine=0.8,
             lymphatic=0.8, other=0.5)
SKIN_TARGET = 90000
tot_in = tot_out = 0
for p in pieces:
    n = len(p['f'])
    if p['en'] == 'Skin':
        target = SKIN_TARGET
    else:
        target = int(max(min(n, 160), n * RATIO[p['system']]))
    v, f = decimate(p['v'], p['f'], target)
    p['v'] = v.astype(np.float32); p['f'] = f.astype(np.int32)
    tot_in += n; tot_out += len(f)
print('decimated %d -> %d tris (%.1fs)' % (tot_in, tot_out, time.time() - t0))

save_pickle(pieces, 'male_pieces.pkl')
print('done %.1fs' % (time.time() - t0))
