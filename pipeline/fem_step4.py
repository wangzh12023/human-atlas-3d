"""Female step 4: close the genital hole of the shared skin (female only), map the male genital patch,
assemble female positions for every male piece (+ procedural pieces) and write female_map.pkl.

Skin handling
  * 'Skin' (shared)       : male skin minus genital patch -> morphs to female skin
  * 'Skin (male region)'  : genital patch, male only
  * 'Skin (female region)': hole filler fitted to the female vulva region (female only)
"""
import os, sys, time
import numpy as np
from scipy.spatial import cKDTree
import scipy.sparse as sp
import scipy.sparse.linalg as spla
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from register import *

t0 = time.time()
P = load_pickle('male_pieces.pkl'); by = {p['en']: p for p in P}
SK = load_pickle('fem_skin.pkl')
FM = load_pickle('female_map_raw.pkl')
C = load_pickle('fem_controls.pkl')
warp = TPSWarp(C['src'], C['dst'], lam=8.0, weights=C['w'])

sh_vM, sh_vF, sh_f = SK['sh_vM'], SK['sh_vF'], SK['sh_f']


def boundary_loops(f):
    e = np.sort(np.vstack([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), 1)
    u, c = np.unique(e, axis=0, return_counts=True)
    b = u[c == 1]
    import collections
    adj = collections.defaultdict(list)
    for a, bb in b:
        adj[a].append(bb); adj[bb].append(a)
    seen = set(); loops = []
    for s in np.unique(b):
        if s in seen:
            continue
        loop = [s]; seen.add(s); cur = s; prev = -1
        while True:
            nx = [x for x in adj[cur] if x != prev and x not in seen]
            if not nx:
                break
            prev, cur = cur, nx[0]; loop.append(cur); seen.add(cur)
        loops.append(np.array(loop))
    return loops


# ---------------------------------------------------------------- female genital-region skin
# 1) snap the fitted shared skin onto the true HRA female skin around the pelvis (smooth falloff)
# 2) cut the HRA skin faces that the shared skin does not cover (the former male genital hole) as the
#    female-only patch, plus one ring of overlap so there is never a gap.
import open3d as o3d
S1 = load_pickle('fem_stage1.pkl')
tv, tf = S1['fskin_v'], S1['fskin_f']
scene = o3d.t.geometry.RaycastingScene()
scene.add_triangles(o3d.core.Tensor(tv.astype(np.float32)), o3d.core.Tensor(tf.astype(np.uint32)))
loops = [l for l in boundary_loops(sh_f) if len(l) >= 3]
rim = np.unique(np.concatenate(loops))
rim_c = sh_vF[rim].mean(0)
print('hole loops', [len(l) for l in loops], 'rim centre', np.round(rim_c, 1))
d_rim = np.linalg.norm((sh_vF - rim_c) * np.array([1.0, 0.8, 1.0]), axis=1)
w_snap = np.clip(1.0 - (d_rim - 70.0) / 70.0, 0.0, 1.0)
w_snap = w_snap * w_snap * (3 - 2 * w_snap)
cp = scene.compute_closest_points(o3d.core.Tensor(sh_vF.astype(np.float32)))['points'].numpy().astype(float)
sh_vF = sh_vF + (cp - sh_vF) * w_snap[:, None]
print('snapped %d skin vertices (weight > 0.5: %d)' % ((w_snap > 0).sum(), (w_snap > 0.5).sum()))
# 2) uncovered HRA faces near the hole
sc2 = o3d.t.geometry.RaycastingScene()
sc2.add_triangles(o3d.core.Tensor(sh_vF.astype(np.float32)), o3d.core.Tensor(sh_f.astype(np.uint32)))
cen = tv[tf].mean(1)
near = np.linalg.norm(cen - rim_c, axis=1) < 75.0
dist = np.full(len(tf), 1e9)
dist[near] = np.abs(sc2.compute_signed_distance(o3d.core.Tensor(cen[near].astype(np.float32))).numpy())
sel = near & (dist > 0.9)
# keep only the connected component(s) touching the hole (drop stray faces elsewhere)
from scipy.sparse.csgraph import connected_components
fi = np.where(sel)[0]
e = np.vstack([tf[fi][:, [0, 1]], tf[fi][:, [1, 2]], tf[fi][:, [2, 0]]])
nv = len(tv)
A = sp.coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(nv, nv))
ncomp, labels = connected_components(A, directed=False)
face_lab = labels[tf[fi][:, 0]]
rim_tree = cKDTree(sh_vF[rim])
keep_lab = set()
for L in np.unique(face_lab):
    fv_ = tv[np.unique(tf[fi[face_lab == L]])]
    if rim_tree.query(fv_)[0].min() < 6.0 and len(fv_) > 12:
        keep_lab.add(L)
fi = fi[np.isin(face_lab, list(keep_lab))]
# one ring of overlap
ring_v = np.unique(tf[fi])
grow = np.where(near & np.isin(tf, ring_v).any(1))[0]
fi = np.union1d(fi, grow)
filler_v, filler_f = clean_mesh(tv, tf[fi])
print('female genital-region skin patch', filler_v.shape, filler_f.shape)

# ---------------------------------------------------------------- female positions for every piece
fem = {}
for p in P:
    if p['en'] == 'Skin':
        continue
    fem[p['file']] = FM[p['file']]
# shared skin replaces the BP3D skin piece (topology changed: genital patch removed)
skin_shared = dict(vM=sh_vM, vF=sh_vF, f=sh_f)
skin_male_patch = dict(vM=SK['gen_v'], vF=warp(SK['gen_v']), f=SK['gen_f'])
# female filler: male position = collapsed onto the male hole rim (it only shows for females)
_, j = cKDTree(sh_vF).query(filler_v)
filler_M = sh_vM[j]
skin_female_patch = dict(vM=filler_M, vF=filler_v, f=filler_f)

# procedural male structures -> female via the volumetric warp (bones rigid)
X = load_pickle('proc_male.pkl')
for p in X:
    v = np.asarray(p['v'], float)
    w = warp(v)
    if p['system'] == 'skeleton':
        s, R, t = umeyama(v, w, with_scale=True); w = s * v @ R.T + t
    p['vF'] = w.astype(np.float32); p['vM'] = v.astype(np.float32)

save_pickle(fem, 'female_map.pkl')
save_pickle(dict(shared=skin_shared, male=skin_male_patch, female=skin_female_patch), 'skin_parts.pkl')
save_pickle(X, 'proc_male_fm.pkl')
print('done %.1fs' % (time.time() - t0))
