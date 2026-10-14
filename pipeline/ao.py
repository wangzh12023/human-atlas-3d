"""Bake per-vertex ambient occlusion.

AO is computed per body system (a bone is only occluded by other bones), otherwise
deep structures would turn black when the layers above them are hidden.

usage: bake_ao(pieces, key='v', normal_key='n') -> writes p['ao'] (float32 0..1, 1 = open)
"""
import numpy as np
import open3d as o3d

N_RAYS = 20
MAX_DIST = 28.0  # mm


def _hemisphere_dirs(n):
    # fixed Fibonacci sphere directions
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / (2 * n))  # upper hemisphere only
    th = np.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], 1)


def _frame(nrm):
    a = np.where(np.abs(nrm[:, :1]) < 0.9, np.array([[1.0, 0, 0]]), np.array([[0, 1.0, 0]]))
    t = np.cross(nrm, a); t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-12
    b = np.cross(nrm, t)
    return t, b


def bake_group(pieces, key, nkey):
    scene = o3d.t.geometry.RaycastingScene()
    for p in pieces:
        scene.add_triangles(o3d.core.Tensor(np.asarray(p[key], np.float32)), o3d.core.Tensor(np.asarray(p['f'], np.uint32)))
    H = _hemisphere_dirs(N_RAYS)
    w = H[:, 2].sum()
    for p in pieces:
        v = np.asarray(p[key], np.float64); n0 = np.asarray(p[nkey], np.float64)
        best = None
        # two-sided: evaluate both hemispheres and keep the more open one. For closed meshes the inner
        # hemisphere is blocked by the piece itself, so this only matters for flipped/open sheets.
        for sgn in (1.0, -1.0):
            n = n0 * sgn
            t, b = _frame(n)
            occl = np.zeros(len(v))
            for d in H:
                dirs = t * d[0] + b * d[1] + n * d[2]
                org = v + n * 0.35
                rays = np.concatenate([org, dirs], 1).astype(np.float32)
                hit = scene.test_occlusions(o3d.core.Tensor(rays), tnear=0.0, tfar=MAX_DIST).numpy()
                occl += hit * d[2]  # cosine weighted
            ao = 1.0 - occl / w
            best = ao if best is None else np.maximum(best, ao)
        p['ao'] = np.clip(best, 0, 1).astype(np.float32)


def bake_ao(pieces, key='v', nkey='n', group_key='system'):
    groups = {}
    for p in pieces:
        groups.setdefault(p[group_key], []).append(p)
    for g, ps in groups.items():
        bake_group(ps, key, nkey)
