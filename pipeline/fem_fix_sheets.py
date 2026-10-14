# -*- coding: utf-8 -*-
"""Female fix-up for wrapped sheet muscles (latissimus dorsi): re-wrap the warped sheet onto the
FEMALE underlying back muscles so it never sinks into them.  Run after fem_step4.py (updates proc_male_fm.pkl)."""
import os, sys
import numpy as np
import open3d as o3d
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

P = load_pickle('male_pieces.pkl')
FM = load_pickle('female_map.pkl')
X = load_pickle('proc_male_fm.pkl')

# underlying back muscles + ribs in the female shape
under = [p for p in P if p['system'] in ('muscles', 'skeleton') and p['v'][:, 2].mean() < 70
         and 940 < p['v'][:, 1].mean() < 1400 and 'Trapezius' not in p['en'] and 'Deltoid' not in p['en']
         and 'Triceps' not in p['en'] and abs(p['v'][:, 0].mean()) < 175]
scene = o3d.t.geometry.RaycastingScene()
for p in under:
    scene.add_triangles(o3d.core.Tensor(np.asarray(FM[p['file']], np.float32)), o3d.core.Tensor(np.asarray(p['f'], np.uint32)))

for p in X:
    if 'Latissimus' not in p['en']:
        continue
    v = np.asarray(p['vF'], float)
    n = vertex_normals(v, p['f'])
    # push every vertex outward (posterior) until it clears the underlying muscles by >= 3 mm
    q = o3d.core.Tensor(v.astype(np.float32))
    d = scene.compute_signed_distance(q).numpy()        # >0 outside, <0 inside
    occ = scene.compute_occupancy(q).numpy() > 0.5
    cp = scene.compute_closest_points(q)['points'].numpy().astype(float)
    push = np.where(occ | (d < 3.0), 1.0, 0.0)
    out_dir = v - cp
    ln = np.linalg.norm(out_dir, axis=1, keepdims=True) + 1e-9
    out_dir = np.where(occ[:, None], -out_dir / ln, out_dir / ln)
    target = cp + out_dir * 3.5
    w = push[:, None]
    v2 = v * (1 - w) + target * w
    # smooth the correction field so the sheet stays continuous
    from register import uniform_laplacian
    L = uniform_laplacian(len(v), p['f'])
    disp = v2 - v
    for _ in range(25):
        disp = disp - 0.5 * (L @ disp)
        disp = np.where(w > 0, np.maximum(np.abs(disp), np.abs(v2 - v)) * np.sign(v2 - v + 1e-12), disp)
    p['vF'] = (v + disp).astype(np.float32)
    print(p['en'], 'pushed', int(push.sum()), 'of', len(v))
save_pickle(X, 'proc_male_fm.pkl')
