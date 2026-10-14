"""Shared helpers for the asset pipeline.

Coordinate frames
-----------------
BP3D  : millimetres, X+ = subject left, Y+ = posterior, Z+ = up
HRA   : metres,      X+ = subject left, Y+ = up,        Z+ = anterior
WORLD : millimetres, X+ = subject left, Y+ = up,        Z+ = anterior  (three.js friendly, floor at y=0)
"""
import os, re, json, gzip, struct
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, '..'))
DATA = os.path.abspath(os.path.join(PROJ, '..', 'body_data'))
BP3D = os.path.join(DATA, 'bp3d')
BP3D_OBJ = os.path.join(BP3D, 'isa_obj', 'isa_BP3D_4.0_obj_99')
HRA = os.path.join(DATA, 'hra')
CACHE = os.path.join(DATA, 'cache')
OUT = os.path.join(PROJ, 'public', 'data')
os.makedirs(CACHE, exist_ok=True)

# BP3D skin min z is the sole of the foot; WORLD puts the floor at y = 0
BP3D_FLOOR_Z = -78.11


def bp3d_to_world(v):
    v = np.asarray(v, dtype=np.float64)
    return np.stack([v[:, 0], v[:, 2] - BP3D_FLOOR_Z, -v[:, 1]], 1)


def hra_to_world_raw(v):
    """HRA metres -> WORLD axes in mm (no translation)."""
    return np.asarray(v, dtype=np.float64) * 1000.0


def load_obj(fn):
    """Fast OBJ reader for BP3D files (v / vn / f with v//vn)."""
    with open(fn, 'rb') as fh:
        data = fh.read().decode('utf-8', 'ignore')
    vs, fs = [], []
    for line in data.split('\n'):
        if line.startswith('v '):
            vs.append(line[2:])
        elif line.startswith('f '):
            fs.append(line[2:])
    v = np.array(' '.join(vs).split(), dtype=np.float64).reshape(-1, 3)
    toks = ' '.join(fs).split()
    idx = np.array([t.split('/')[0] for t in toks], dtype=np.int64) - 1
    # BP3D is pure triangles
    f = idx.reshape(-1, 3)
    return v, f


def clean_mesh(v, f):
    """Drop degenerate faces and unreferenced vertices."""
    f = f[(f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 0] != f[:, 2])]
    used = np.unique(f)
    remap = -np.ones(len(v), dtype=np.int64)
    remap[used] = np.arange(len(used))
    return v[used], remap[f]


def weld(v, f, tol=1e-4):
    q = np.round(v / tol).astype(np.int64)
    _, first, inv = np.unique(q, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    return v[first], inv[f]


def vertex_normals(v, f):
    v = np.asarray(v, dtype=np.float64)
    fn = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    n = np.zeros_like(v)
    for k in range(3):
        np.add.at(n, f[:, k], fn)
    ln = np.linalg.norm(n, axis=1)
    bad = ln < 1e-20
    n[~bad] /= ln[~bad, None]
    n[bad] = (0, 1, 0)
    return n


def decimate(v, f, target):
    """Quadric decimation via open3d; returns (v, f)."""
    import open3d as o3d
    if len(f) <= target:
        return v, f
    m = o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(v), o3d.utility.Vector3iVector(f.astype(np.int32)))
    m.remove_duplicated_vertices()
    m.remove_degenerate_triangles()
    m2 = m.simplify_quadric_decimation(int(target), boundary_weight=3.0)
    v2 = np.asarray(m2.vertices); f2 = np.asarray(m2.triangles).astype(np.int64)
    if len(f2) < 4:
        return v, f
    return clean_mesh(v2, f2)


def bounds_center(v):
    return (v.min(0) + v.max(0)) * 0.5


def save_pickle(obj, name):
    import pickle
    with open(os.path.join(CACHE, name), 'wb') as fh:
        pickle.dump(obj, fh, protocol=4)


def load_pickle(name):
    import pickle
    with open(os.path.join(CACHE, name), 'rb') as fh:
        return pickle.load(fh)


def read_glb(fn):
    """Return list of (node_name, vertices(n,3) metres, faces(m,3)) with node transforms applied."""
    import trimesh
    s = trimesh.load(fn, process=False)
    out = []
    for node in s.graph.nodes_geometry:
        T, gname = s.graph[node]
        g = s.geometry[gname]
        v = np.asarray(g.vertices, dtype=np.float64)
        v = v @ T[:3, :3].T + T[:3, 3]
        f = np.asarray(g.faces, dtype=np.int64)
        out.append((node, v, f))
    return out


def write_json(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False, separators=(',', ':'))


def write_gz(buf, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, 'wb', compresslevel=9) as fh:
        fh.write(buf)
