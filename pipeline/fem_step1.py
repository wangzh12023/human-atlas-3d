"""Female step 1: bring HRA female data into WORLD frame and similarity-align it to the male skin.
Produces CACHE/fem_stage1.pkl with female skin + bones in WORLD frame (floor y=0) and the skin
correspondence frame."""
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from register import *

t0 = time.time()
P = load_pickle('male_pieces.pkl'); by = {p['en']: p for p in P}
mskin_v = np.asarray(by['Skin']['v'], float); mskin_f = np.asarray(by['Skin']['f'])

F = read_glb(os.path.join(HRA, '3d-vh-f-skin.glb'))[0]
fv, ff = weld(F[1] * 1000.0, F[2], 1e-3)
fv, ff = clean_mesh(fv, ff)
fv, ff = decimate(fv, ff, 120000)
print('female skin', fv.shape, ff.shape, '%.1fs' % (time.time() - t0))
# HRA female frame: floor at y=-793 -> 0. X,Z axes already match WORLD (X+ = subject left, Z+ = anterior)
OFF = np.array([0.0, 792.6, 0.0])
fv = fv + OFF
# centre in x/z like male: male skin centre x ~0, z ~ 101 ; female z centre -56
# Use torso landmarks (exclude arms: |x| > 180 on male, female arms are abducted) for a rigid fit
def torso(v):
    return v[(np.abs(v[:, 0]) < 165) & (v[:, 1] > 60)]
ms = torso(mskin_v); fs = torso(fv)
ms = ms[fps(ms, 6000)]; fs = fs[fps(fs, 6000)]
# initial: align centroids, no rotation
init = (1.0, np.eye(3), ms.mean(0) - fs.mean(0))
(s, R, t), _ = icp_similarity(fs, ms, iters=30, with_scale=False, init=init, trim=0.85)
ang = np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1)))
print('rigid female->male: rot %.2f deg, t %s' % (ang, np.round(t, 1)))
# keep the small rotation; re-anchor translation: floor on y=0, pelvis/torso centred on the male torso in x/z
fv_w = fv @ R.T
miny = fv_w[:, 1].min()
fv_w[:, 1] -= miny
# centre on the bony pelvis (left/right ilium extremes, front/back of the pelvic ring) instead of the skin
pel = {n: v * 1000.0 for n, v, f in read_glb(os.path.join(HRA, '3d-vh-f-pelvis.glb'))}
hra_pel = np.vstack([v for n, v in pel.items() if 'compact' in n])
hra_pel_w = ((hra_pel + OFF) @ R.T); hra_pel_w[:, 1] -= miny
male_pel = np.vstack([np.asarray(by[n]['v'], float) for n in ('Left Hip Bone', 'Right Hip Bone')])
cf = (hra_pel_w.min(0) + hra_pel_w.max(0)) / 2
cm = (male_pel.min(0) + male_pel.max(0)) / 2
fv_w[:, 0] += cm[0] - cf[0]; fv_w[:, 2] += cm[2] - cf[2]
t = np.array([cm[0] - cf[0], -miny, cm[2] - cf[2]])  # world = (raw_mm + OFF) @ R.T + t
print('pelvis centring shift x %.1f z %.1f' % (cm[0] - cf[0], cm[2] - cf[2]))
# straighten the lateral lean: fit the skin midline x(y) above the pelvis and shear it back to x = pelvis centre
ys, xs = [], []
for y in np.arange(950, 1560, 20):
    sl = fv_w[np.abs(fv_w[:, 1] - y) < 5]
    core = sl[np.abs(sl[:, 0] - np.median(sl[:, 0])) < (120 if y > 1430 else 165)]
    if len(core) > 20:
        ys.append(y); xs.append((core[:, 0].min() + core[:, 0].max()) / 2)
k, b = np.polyfit(ys, xs, 1)
y0 = 900.0
lean = lambda v: np.where(v[:, 1:2] > y0, (v[:, 1:2] - y0) * k, 0.0)
shear = -lean(fv_w)[:, 0]
fv_w[:, 0] += shear
LEAN_K, LEAN_Y0 = k, y0
print('lean correction: %.4f mm/mm (%.2f deg)' % (k, np.degrees(np.arctan(k))))
save_pickle(dict(OFF=OFF, R=R, t=t, fskin_v=fv_w, fskin_f=ff, lean_k=LEAN_K, lean_y0=LEAN_Y0), 'fem_stage1.pkl')
print('female skin bounds', fv_w.min(0).round(), fv_w.max(0).round(), 'male', mskin_v.min(0).round(), mskin_v.max(0).round())
print('done %.1fs' % (time.time() - t0))
