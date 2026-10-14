"""Procedural (schematic) anatomy missing from BodyParts3D, fitted to the male skeleton.

Built in WORLD frame (mm, X+ subject left, Y up, Z+ anterior). Every structure is created for the
right side and mirrored (x -> -x) for the left side.

Geometry helpers:
  tube(path, radii)            swept tube along a polyline (ligaments, tendons, cords)
  band(path, widths, thick)    flat ribbon with thickness (flat ligaments, fascia)
  sheet_on(mesh, region...)    offset patch from an existing surface (muscle sheets)
  crescent(...)                meniscus (wedge-shaped C)

Output: list of piece dicts (en, zh, system, v, f, kind='proc', side)
"""
import numpy as np
from scipy.spatial import cKDTree


# ------------------------------------------------------------------ primitive builders
def _fit(arr, n):
    """broadcast a scalar or resample a 1-D profile to length n"""
    a = np.atleast_1d(np.asarray(arr, float))
    if a.size == 1:
        return np.full(n, float(a[0]))
    if a.size == n:
        return a
    return np.interp(np.linspace(0, 1, n), np.linspace(0, 1, a.size), a)


def _frames(path):
    path = np.asarray(path, float)
    n = len(path)
    T = np.gradient(path, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
    # parallel transport
    ref = np.array([0, 0, 1.0]) if abs(T[0][2]) < 0.9 else np.array([1.0, 0, 0])
    N = np.zeros_like(path); B = np.zeros_like(path)
    N[0] = np.cross(T[0], ref); N[0] /= np.linalg.norm(N[0])
    B[0] = np.cross(T[0], N[0])
    for i in range(1, n):
        v = np.cross(T[i - 1], T[i])
        s = np.linalg.norm(v)
        if s < 1e-8:
            N[i] = N[i - 1]
        else:
            a = np.arcsin(np.clip(s, -1, 1))
            v /= s
            nn = N[i - 1]
            N[i] = nn * np.cos(a) + np.cross(v, nn) * np.sin(a) + v * np.dot(v, nn) * (1 - np.cos(a))
        B[i] = np.cross(T[i], N[i])
    return T, N, B


def smooth_path(pts, n=24):
    """Catmull-Rom resample of control points."""
    P = np.asarray(pts, float)
    if len(P) == 2:
        t = np.linspace(0, 1, n)[:, None]
        return P[0] * (1 - t) + P[1] * t
    P = np.vstack([P[0] * 2 - P[1], P, P[-1] * 2 - P[-2]])
    out = []
    segs = len(P) - 3
    for i in range(segs):
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        m = max(2, n // segs)
        for t in np.linspace(0, 1, m, endpoint=(i == segs - 1)):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    return np.array(out)


def tube(path, radii, seg=14, caps=True, flat=1.0, twist=0.0):
    """Swept elliptical tube. radii: scalar or per-point array. flat: ellipse ratio (b/a)."""
    path = np.asarray(path, float)
    n = len(path)
    r = _fit(radii, n)
    T, N, B = _frames(path)
    ang = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    V = []
    for i in range(n):
        tw = twist * i / max(1, n - 1)
        ca, sa = np.cos(ang + tw), np.sin(ang + tw)
        ring = path[i] + (N[i][None] * ca[:, None] * r[i] + B[i][None] * sa[:, None] * r[i] * flat)
        V.append(ring)
    V = np.concatenate(V)
    F = []
    for i in range(n - 1):
        for j in range(seg):
            a = i * seg + j; b = i * seg + (j + 1) % seg
            c = (i + 1) * seg + j; d = (i + 1) * seg + (j + 1) % seg
            F += [[a, c, b], [b, c, d]]
    if caps:
        c0 = len(V); V = np.vstack([V, path[0], path[-1]])
        for j in range(seg):
            F.append([c0, j, (j + 1) % seg])
            a = (n - 1) * seg
            F.append([c0 + 1, a + (j + 1) % seg, a + j])
    return V, np.array(F)


def band(path, widths, thick, up_hint=None, seg_w=6):
    """Flat ribbon (box section) along path; width direction ~ perpendicular to path and up_hint."""
    path = np.asarray(path, float)
    n = len(path)
    w = _fit(widths, n)
    th = _fit(thick, n)
    T = np.gradient(path, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
    hint = np.array(up_hint if up_hint is not None else [0, 0, 1.0], float)
    W = np.cross(T, hint); W /= np.linalg.norm(W, axis=1, keepdims=True) + 1e-12
    Nn = np.cross(W, T)
    # rounded rectangle cross-section
    prof = []
    for k in range(seg_w + 1):
        prof.append((-1 + 2 * k / seg_w, 1.0))
    for k in range(seg_w + 1):
        prof.append((1 - 2 * k / seg_w, -1.0))
    prof = np.array(prof)
    m = len(prof)
    V = []
    for i in range(n):
        x = prof[:, 0] * w[i] / 2
        y = prof[:, 1] * th[i] / 2 * np.sqrt(np.clip(1 - prof[:, 0] ** 6, 0.05, 1))
        V.append(path[i] + W[i][None] * x[:, None] + Nn[i][None] * y[:, None])
    V = np.concatenate(V)
    F = []
    for i in range(n - 1):
        for j in range(m):
            a = i * m + j; b = i * m + (j + 1) % m
            c = (i + 1) * m + j; d = (i + 1) * m + (j + 1) % m
            F += [[a, c, b], [b, c, d]]
    c0 = len(V); V = np.vstack([V, path[0], path[-1]])
    for j in range(m):
        F.append([c0, j, (j + 1) % m])
        a = (n - 1) * m
        F.append([c0 + 1, a + (j + 1) % m, a + j])
    return V, np.array(F)


def crescent(center, rx, rz, width, height, gap_deg, start_deg, seg=40):
    """Meniscus: C-shaped wedge lying in the XZ plane, wedge thicker at the outer rim."""
    cx, cy, cz = center
    a0 = np.radians(start_deg + gap_deg / 2); a1 = np.radians(start_deg + 360 - gap_deg / 2)
    angs = np.linspace(a0, a1, seg)
    prof = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.15, 0.25]])  # (radial, vertical) inner->outer
    V = []
    for k, a in enumerate(angs):
        taper = np.sin(np.pi * (k / (seg - 1))) ** 0.35
        for (u, h) in prof:
            rr = 1 - width * (1 - u)
            x = cx + np.cos(a) * rx * rr
            z = cz + np.sin(a) * rz * rr
            y = cy + h * height * (0.35 + 0.65 * taper)
            V.append([x, y, z])
    V = np.array(V)
    m = len(prof)
    F = []
    for k in range(seg - 1):
        for j in range(m):
            a = k * m + j; b = k * m + (j + 1) % m
            c = (k + 1) * m + j; d = (k + 1) * m + (j + 1) % m
            F += [[a, b, c], [b, d, c]]
    F += [[0, 2, 1], [0, 3, 2]]
    o = (seg - 1) * m
    F += [[o, o + 1, o + 2], [o, o + 2, o + 3]]
    return V, np.array(F)


def sheet_from_surface(base_v, base_f, mask_fn, offset, thick, smooth_iter=2):
    """Extract faces of an existing mesh whose centroid passes mask_fn, offset along normals, and
    give it a thickness -> closed slab. Used for muscle sheets lying on/under existing muscles."""
    from common import vertex_normals, clean_mesh
    cen = base_v[base_f].mean(1)
    keep = mask_fn(cen)
    f = base_f[keep]
    v, f = clean_mesh(base_v, f)
    n = vertex_normals(v, f)
    outer = v + n * offset
    inner = v + n * (offset - thick)
    V = np.vstack([outer, inner])
    nv = len(v)
    F = np.vstack([f, f[:, ::-1] + nv])
    # boundary walls
    edges = np.sort(np.vstack([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
    uniq, cnt = np.unique(edges, axis=0, return_counts=True)
    bnd = uniq[cnt == 1]
    walls = []
    for a, b in bnd:
        walls += [[a, b, b + nv], [a, b + nv, a + nv]]
    if walls:
        F = np.vstack([F, np.array(walls)])
    return V, F


def mirror(v, f):
    v2 = v.copy(); v2[:, 0] *= -1
    return v2, f[:, ::-1].copy()


def merge(*parts):
    V = []; F = []; o = 0
    for v, f in parts:
        V.append(v); F.append(f + o); o += len(v)
    return np.vstack(V), np.vstack(F)


def ellipsoid(c, r, seg=18, rings=12):
    c = np.asarray(c, float); r = np.broadcast_to(np.asarray(r, float), (3,))
    V = []
    for i in range(rings + 1):
        th = np.pi * i / rings
        for j in range(seg):
            ph = 2 * np.pi * j / seg
            V.append(c + r * np.array([np.sin(th) * np.cos(ph), np.cos(th), np.sin(th) * np.sin(ph)]))
    V = np.array(V)
    F = []
    for i in range(rings):
        for j in range(seg):
            a = i * seg + j; b = i * seg + (j + 1) % seg
            cc = (i + 1) * seg + j; d = (i + 1) * seg + (j + 1) % seg
            F += [[a, b, cc], [b, d, cc]]
    return V, np.array(F)


def surface_point(tree_v, tree, p, direction=None):
    """closest point on a bone (vertex set) to p"""
    d, i = tree.query(p)
    return tree_v[i]


def front_layer(v, f, axis_z=95.0):
    """faces of a closed thin shell whose normals point away from the torso axis (outer layer)"""
    c = v[f].mean(1)
    n = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    radial = np.stack([c[:, 0], np.zeros(len(c)), c[:, 2] - axis_z], 1)
    radial /= np.linalg.norm(radial, axis=1, keepdims=True) + 1e-12
    return (n * radial).sum(1) > 0.15


def slab(v, f, offset, thick):
    """open surface (v,f) -> closed slab: outer = v + n*offset, inner = v + n*(offset-thick)"""
    from common import vertex_normals, clean_mesh
    v, f = clean_mesh(v, f)
    n = vertex_normals(v, f)
    outer = v + n * offset
    inner = v + n * (offset - thick)
    nv = len(v)
    V = np.vstack([outer, inner])
    F = [f, f[:, ::-1] + nv]
    edges = np.sort(np.vstack([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
    uniq, cnt = np.unique(edges, axis=0, return_counts=True)
    bnd = uniq[cnt == 1]
    if len(bnd):
        a, b = bnd[:, 0], bnd[:, 1]
        F.append(np.stack([a, b, b + nv], 1)); F.append(np.stack([a, b + nv, a + nv], 1))
    return V, np.vstack(F)


def grid_surface(G):
    """G: (K, M, 3) grid -> (v, f)"""
    K, M, _ = G.shape
    v = G.reshape(-1, 3)
    f = []
    for i in range(K - 1):
        for j in range(M - 1):
            a = i * M + j; b = a + 1; c = a + M; d = c + 1
            f += [[a, c, b], [b, c, d]]
    return v, np.array(f)


def raycast_wrap(G, meshes, axis_fn, push=2.5, weight=None, max_in=400.0):
    """Snap grid points onto the outer envelope of `meshes` by casting rays from outside toward axis_fn(p).
    weight: (K,M) blend 0..1 between original and snapped point."""
    import open3d as o3d
    sc = o3d.t.geometry.RaycastingScene()
    for v, f in meshes:
        sc.add_triangles(o3d.core.Tensor(np.asarray(v, np.float32)), o3d.core.Tensor(np.asarray(f, np.uint32)))
    pts = G.reshape(-1, 3)
    ax = np.array([axis_fn(p) for p in pts])
    d = pts - ax
    d[:, 1] = 0
    d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9
    org = ax + d * max_in
    rays = np.concatenate([org, -d], 1).astype(np.float32)
    hit = sc.cast_rays(o3d.core.Tensor(rays))['t_hit'].numpy()
    ok = np.isfinite(hit)
    snapped = pts.copy()
    snapped[ok] = org[ok] - d[ok] * (hit[ok, None] - push)
    if weight is not None:
        w = weight.reshape(-1, 1)
        snapped = pts * (1 - w) + snapped * w
    return snapped.reshape(G.shape), ok.reshape(G.shape[:2])


class BoneSurface:
    """nearest-surface queries on one or more bone meshes (vertex-normal based)."""
    def __init__(self, meshes):
        from common import vertex_normals
        vs, ns = [], []
        for v, f in meshes:
            v = np.asarray(v, float); f = np.asarray(f, int)
            n = vertex_normals(v, f)
            c = v[f].mean(1)
            fn = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
            fn /= np.linalg.norm(fn, axis=1, keepdims=True) + 1e-12
            vs += [v, c]; ns += [n, fn]
        self.v = np.vstack(vs); self.n = np.vstack(ns)
        self.tree = cKDTree(self.v)

    def project(self, p, offset):
        d, i = self.tree.query(p, k=6)
        q = self.v[i].mean(0)
        nn = self.n[i].mean(0); nn /= np.linalg.norm(nn) + 1e-12
        return q + nn * offset


def hug(path, surf, offsets, keep_ends=0.0):
    """Project each path point onto `surf` + normal*offset (offsets scalar or profile)."""
    path = np.asarray(path, float)
    off = _fit(offsets, len(path))
    out = np.array([surf.project(p, o) for p, o in zip(path, off)])
    if keep_ends:
        out[0] = out[0] * (1 - keep_ends) + path[0] * keep_ends
        out[-1] = out[-1] * (1 - keep_ends) + path[-1] * keep_ends
    for _ in range(2):
        out[1:-1] = out[1:-1] * 0.5 + (out[:-2] + out[2:]) * 0.25
    return out


def taper(n, lo=0.55, power=0.5):
    t = np.linspace(0, 1, n)
    return lo + (1 - lo) * np.sin(np.pi * t) ** power
