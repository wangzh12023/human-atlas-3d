"""Extra procedural primitives (appended module; imported by fem_extra.py)."""
import numpy as np
from proc_geom import _fit


def ellipse_tube(path, lat_dir, r_lat, r_out, seg=18, caps=True):
    """Swept ellipse with explicit axes: one axis along `lat_dir` (fixed vector or per point),
    the other along the outward normal (perpendicular to path & lat_dir)."""
    path = np.asarray(path, float)
    n = len(path)
    T = np.gradient(path, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
    L = np.broadcast_to(np.asarray(lat_dir, float), (n, 3)).copy()
    L -= T * (L * T).sum(1, keepdims=True)
    L /= np.linalg.norm(L, axis=1, keepdims=True) + 1e-12
    O = np.cross(T, L)
    a = _fit(r_lat, n); b = _fit(r_out, n)
    ang = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    V = np.concatenate([path[i] + L[i] * (np.cos(ang)[:, None] * a[i]) + O[i] * (np.sin(ang)[:, None] * b[i]) for i in range(n)])
    F = []
    for i in range(n - 1):
        for j in range(seg):
            p0 = i * seg + j; p1 = i * seg + (j + 1) % seg
            q0 = (i + 1) * seg + j; q1 = (i + 1) * seg + (j + 1) % seg
            F += [[p0, q0, p1], [p1, q0, q1]]
    if caps:
        c0 = len(V); V = np.vstack([V, path[0], path[-1]])
        for j in range(seg):
            F.append([c0, (j + 1) % seg, j])
            k = (n - 1) * seg
            F.append([c0 + 1, k + j, k + (j + 1) % seg])
    return V, np.array(F)


def pillow_profile(n, lo=0.12, power=0.55):
    """smooth 0..1..0 profile with rounded (non-zero) ends"""
    t = np.linspace(0, 1, n)
    return lo + (1 - lo) * np.sin(np.pi * t) ** power
