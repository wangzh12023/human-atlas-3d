"""Female step 3: volumetric male -> female warp for every internal structure.

Control correspondences (male WORLD -> female WORLD):
  * skin       : shared skin vertices (male position -> fitted female position), torso/head/legs
  * bones      : HRA female pelvis / femur / tibia / fibula / patella / sternum / manubrium / disks,
                 fitted per bone (similarity ICP) to the matching male bone; sampled surface points
  * organs     : HRA female heart, liver, kidneys, spleen, lungs (centroid + principal extent points)
  * arms       : rigid per side - the shoulder girdle follows the torso warp; arm keeps male pose
All controls feed one regularised thin-plate RBF warp (with skeletal points weighted higher).
Bones are then made rigid: each bone piece is replaced by its own best similarity transform of the
warped vertices (prevents bent bones). Muscles etc. keep the smooth warp.

writes CACHE/female_map.pkl : {file: vF (float32)}  and CACHE/fem_controls.pkl
"""
import os, sys, time
import numpy as np
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from register import *

t0 = time.time()
P = load_pickle('male_pieces.pkl'); by = {p['en']: p for p in P}
S1 = load_pickle('fem_stage1.pkl')
SK = load_pickle('fem_skin.pkl')
R1, t1, OFF = S1['R'], S1['t'], S1['OFF']


def hra_world(v_m):
    """HRA metres -> female WORLD (same transform used for the female skin, incl. lean correction)"""
    w = (v_m * 1000.0 + OFF) @ R1.T + t1
    k, y0 = S1.get('lean_k', 0.0), S1.get('lean_y0', 900.0)
    w[:, 0] -= np.where(w[:, 1] > y0, (w[:, 1] - y0) * k, 0.0)
    return w


def glb(fn):
    return {n.replace('VH_F_', ''): (hra_world(v), f) for n, v, f in read_glb(os.path.join(HRA, fn))}


src, dst, wts, tags = [], [], [], []


def add(s, d, w, tag):
    s = np.asarray(s, float); d = np.asarray(d, float)
    src.append(s); dst.append(d); wts.append(np.full(len(s), w)); tags.append(np.full(len(s), tag, dtype=object))


# ---------------------------------------------------------------- skin controls
lab = SK['lab']
skin_ok = ~np.isin(lab, (4, 5))           # no arms
sv, sF = SK['sh_vM'][skin_ok], SK['sh_vF'][skin_ok]
idx = fps(sv, 900)
add(sv[idx], sF[idx], 1.0, 'skin')

# ---------------------------------------------------------------- bone controls (fit HRA bone to male bone)
bone_fem = {}   # male piece name -> female vertex positions (male topology, NRICP refined)


def bone_pair(male_name, fem_mesh, n=60, w=4.0, refine=True):
    """fit male bone to the female reference bone: similarity ICP, then (optionally) NRICP refine."""
    fem_v, fem_f = fem_mesh
    mv = np.asarray(by[male_name]['v'], float); mf = np.asarray(by[male_name]['f'])
    a = mv[fps(mv, 1500)]
    b = fem_v[fps(fem_v, 1500)]
    init = (1.0, np.eye(3), b.mean(0) - a.mean(0))
    (s, R, t), aw = icp_similarity(a, b, iters=50, with_scale=True, init=init, trim=0.9)
    x = s * mv @ R.T + t
    if refine:
        x = nricp(x, mf, fem_v, fem_f, stiffness=(24, 10, 4, 1.6), iters=3, max_dist=22.0, normal_dot=0.3)
    bone_fem[male_name] = x
    k = fps(mv, n)
    add(mv[k], x[k], w, 'bone:' + male_name)
    return s, R, t


def catmesh(d, keys):
    vs, fs, o = [], [], 0
    for k in keys:
        v, f = d[k]
        vs.append(v); fs.append(np.asarray(f) + o); o += len(v)
    return np.vstack(vs), np.vstack(fs)


pel = glb('3d-vh-f-pelvis.glb')
fit = {}
fit['Left Hip Bone'] = bone_pair('Left Hip Bone', catmesh(pel, ['ilium_compact_bone_L', 'ischium_compact_bone_L', 'pubis_compact_bone_L']), 110)
fit['Right Hip Bone'] = bone_pair('Right Hip Bone', catmesh(pel, ['ilium_compact_bone_R', 'ischium_compact_bone_R', 'pubis_compact_bone_R']), 110)
fit['Sacrum'] = bone_pair('Sacrum', pel['sacrum'], 70)
for side, s in (('L', 'Left'), ('R', 'Right')):
    k = glb('3d-vh-f-knee-%s.glb' % side.lower())
    fit[s + ' Femur'] = bone_pair(s + ' Femur', k['femur_' + side], 90)
    fit[s + ' Tibia'] = bone_pair(s + ' Tibia', k['tibia_' + side], 70)
    fit[s + ' Fibula'] = bone_pair(s + ' Fibula', k['fibula_' + side], 30, 2.0)
    fit[s + ' Patella'] = bone_pair(s + ' Patella', k['patella_' + side], 16)
st = glb('3d-vh-f-sternum.glb'); ma = glb('3d-vh-f-manubrium.glb')
fit['Body of Sternum'] = bone_pair('Body of Sternum', st['sternum'], 24)
fit['Manubrium'] = bone_pair('Manubrium', ma['manubrium'], 16)
# intervertebral disks -> spine curve
dk = glb('3d-vh-f-intervertebral-disk.glb')
ORD = ['axis', 'third_cervical', 'fourth_cervical', 'fifth_cervical', 'sixth_cervical', 'seventh_cervical'] + \
      ['%s_thoracic' % w for w in ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth', 'eleventh', 'twelfth']] + \
      ['%s_lumbar' % w for w in ['first', 'second', 'third', 'fourth', 'fifth']]
male_disk = {}
for p in P:
    n = p['en'].lower()
    if n.startswith('intervertebral disk'):
        male_disk[n] = p
NAMEMAP = {'axis': 'intervertebral disk of axis'}
for o in ORD[1:]:
    num, reg = o.split('_')
    NAMEMAP[o] = 'intervertebral disk of %s %s vertebra' % (num, reg)
for o in ORD:
    key = 'intervertebral_disk_of_' + (o if o == 'axis' else o + '_vertebra')
    mn = NAMEMAP[o]
    if key in dk and mn in male_disk:
        mv = np.asarray(male_disk[mn]['v'], float); fvv = dk[key][0]
        mc = (mv.min(0) + mv.max(0)) / 2; fc = (fvv.min(0) + fvv.max(0)) / 2
        add([mc], [fc], 5.0, 'disk')
# the unnamed male 'Intervertebral Disk' is T12/L1 in BP3D numbering -> matched by nearest y below
print('controls after bones: %d  (%.1fs)' % (sum(len(s) for s in src), time.time() - t0))

# ---------------------------------------------------------------- organ controls (centroid + extents)
def organ(male_names, fem_file, fem_keys=None, w=2.0, n_ext=6):
    mv = np.vstack([np.asarray(by[n]['v'], float) for n in male_names if n in by])
    d = glb(fem_file)
    fvv = np.vstack([d[k][0] for k in d if (fem_keys is None or any(x in k for x in fem_keys))])
    a = mv[fps(mv, 1200)]; b = fvv[fps(fvv, 1200)]
    init = (1.0, np.eye(3), b.mean(0) - a.mean(0))
    (s, R, t), _ = icp_similarity(a, b, iters=40, with_scale=True, init=init, trim=0.9)
    k = fps(mv, n_ext)
    add(mv[k], s * mv[k] @ R.T + t, w, 'organ:' + fem_file)
heart = [p['en'] for p in P if p['system'] == 'heart']
organ(heart, '3d-vh-f-heart.glb', w=2.0, n_ext=10)
organ(['Left Kidney'], '3d-vh-f-kidney-l.glb', n_ext=6)
organ(['Right Kidney'], '3d-vh-f-kidney-r.glb', n_ext=6)
organ(['Spleen'], '3d-vh-f-spleen.glb', n_ext=5, w=1.0)
liver = [p['en'] for p in P if p['en'].startswith('Hepatovenous Segment') or p['en'] == 'Caudate Lobe of Liver']
organ(liver, '3d-vh-f-liver.glb', n_ext=10, w=1.5)
organ(['Urinary Bladder'], '3d-vh-f-urinary-bladder.glb', n_ext=4, w=1.0)
organ(['Trachea'], '3d-vh-f-trachea.glb', ['trachea'], n_ext=6, w=1.5)

# ---------------------------------------------------------------- rib cage width from the female lungs
# The VH female has a thick subcutaneous fat layer; the skin-driven warp would widen the rib cage with it.
# Lateral rib points are pinned to (female lung lateral extent + pleura/intercostal/rib thickness).
lung = glb('3d-vh-f-lung.glb')
lv = np.vstack([v for k, (v, f) in lung.items() if 'bronchopulmonary_segment' in k or 'segmen' in k])
ribs = [p for p in P if p['system'] in ('skeleton',) and (' Rib' in p['en'] or 'rib' in p['en'].split()[-1:])]
rib_pts = np.vstack([np.asarray(p['v'], float) for p in ribs])
tmp_warp = TPSWarp(np.vstack(src), np.vstack(dst), lam=8.0, weights=np.concatenate(wts))
wr = tmp_warp(rib_pts)
ly0, ly1 = lv[:, 1].min(), lv[:, 1].max()
# lung half-width per side at its widest (the costal margin below the lungs follows the same envelope,
# tapering slightly toward the floating ribs)
lat_max = {sd: (lv[lv[:, 0] * sd > 0][:, 0] * sd).max() for sd in (1, -1)}
add_s, add_d = [], []
ylo = wr[:, 1].min()
for side in (1, -1):
    m_side = rib_pts[:, 0] * side > 20
    for y in np.arange(ylo + 6, ly1 - 25, 10.0):
        if y >= ly0 + 30:
            sl = lv[(np.abs(lv[:, 1] - y) < 6) & (lv[:, 0] * side > 0)]
            if len(sl) < 20:
                continue
            lung_lat = (sl[:, 0] * side).max()
        else:
            # below the lung base: costal margin narrows ~ linearly toward the 12th rib
            u = np.clip((ly0 + 30 - y) / max(1.0, ly0 + 30 - ylo), 0, 1)
            lung_lat = lat_max[side] * (1.0 - 0.12 * u)
        sel = m_side & (np.abs(wr[:, 1] - y) < 5)
        if sel.sum() < 3:
            continue
        idx = np.where(sel)[0]
        k = idx[np.argmax(wr[idx, 0] * side)]          # lateral-most rib point at this female level
        tgt = wr[k].copy()
        want = lung_lat + 16.0
        if tgt[0] * side > want:
            tgt[0] = side * want
            add_s.append(rib_pts[k]); add_d.append(tgt)
# below the lungs (floating ribs) keep the same proportional narrowing as the lowest lung level
if add_s:
    add(np.array(add_s), np.array(add_d), 4.0, 'ribcage')
    print('rib cage controls', len(add_s))

# ---------------------------------------------------------------- arms: carried rigidly by the shoulder
arm_controls = []
for side, sx in (('Left', 1), ('Right', -1)):
    names = [p['en'] for p in P if p['system'] == 'skeleton' and side in p['en'] and any(k in p['en'] for k in ('Humerus', 'Radius', 'Ulna', 'Metacarpal', 'Phalanx', 'Scaphoid', 'Lunate', 'Capitate', 'Hamate', 'Trapez', 'Triquetral', 'Pisiform'))]
    pts = np.vstack([by[n]['v'] for n in names])
    arm_controls.append((side, pts))

src_a = np.vstack(src); dst_a = np.vstack(dst); w_a = np.concatenate(wts); tag_a = np.concatenate(tags)
print('total controls', len(src_a))
warp0 = TPSWarp(src_a, dst_a, lam=8.0, weights=w_a)
err = np.linalg.norm(warp0(src_a) - dst_a, axis=1)
for t in ('skin', 'bone', 'disk', 'organ', 'ribcage'):
    m = np.array([str(x).startswith(t) for x in tag_a])
    print('  fit err %-6s mean %.1f  max %.1f mm' % (t, err[m].mean(), err[m].max()))

# arm rigid transforms: shoulder region (humeral head) moves with warp0; keep male arm orientation
arm_T = {}
for side, pts in arm_controls:
    hum = np.asarray(by[side + ' Humerus']['v'], float)
    head = hum[hum[:, 1] > hum[:, 1].max() - 45]
    moved = warp0(head)
    s, R, t = umeyama(head, moved, with_scale=False)
    arm_T[side] = (R, t)
    # add the whole arm as rigid controls for the final warp
    k = fps(pts, 140)
    src_a = np.vstack([src_a, pts[k]]); dst_a = np.vstack([dst_a, pts[k] @ R.T + t]); w_a = np.concatenate([w_a, np.full(len(k), 3.0)])
warp = TPSWarp(src_a, dst_a, lam=8.0, weights=w_a)
print('final warp with arms, controls', len(src_a), '%.1fs' % (time.time() - t0))

# ---------------------------------------------------------------- apply to every piece
ARMB = ('Humerus', 'Radius', 'Ulna', 'Metacarpal', 'Phalanx of', 'Scaphoid', 'Lunate', 'Triquetral', 'Pisiform', 'Trapezium', 'Trapezoid', 'Capitate', 'Hamate')
out = {}
for p in P:
    v = np.asarray(p['v'], float)
    if p['en'] == 'Skin':
        continue
    w = warp(v)
    if p['system'] in ('skeleton',) or (p['system'] == 'ligaments' and 'Disk' not in p['en']):
        # rigidify bones (similarity of warped vs original)
        if p['en'] in bone_fem:
            w = bone_fem[p['en']]
        elif any(k in p['en'] for k in ARMB):
            # arm bones: rigid (they are carried by the shoulder, keep the male pose without bending)
            s, R, t = umeyama(v, w, with_scale=True)
            w = s * v @ R.T + t
        # all other bones (ribs, vertebrae, skull, scapula ...) keep the smooth warp so they stay
        # consistent with the muscles around them (rigidifying ribs made them pierce the back muscles)
    out[p['file']] = w.astype(np.float32)
save_pickle(out, 'female_map_raw.pkl')
save_pickle(dict(src=src_a, dst=dst_a, w=w_a, arm_T=arm_T, fit=fit), 'fem_controls.pkl')
print('mapped %d pieces  %.1fs' % (len(out), time.time() - t0))
