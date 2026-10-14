"""Quick software preview renderer (painter's algorithm, flat shading).

usage (as module): render(meshes, view='front', size=900, out='x.png')
meshes: list of (vertices Nx3 in a Z-up or Y-up frame already converted to
viewer frame: X right, Y up, Z toward viewer), faces Mx3, rgb tuple)
"""
import numpy as np
from PIL import Image, ImageDraw


def _view_matrix(view):
    # returns rotation that maps world (X right, Y up, Z toward viewer when 'front') to camera
    if isinstance(view, (tuple, list, np.ndarray)) and np.array(view).shape == (3, 3):
        return np.array(view, dtype=float)
    yaw = {'front': 0, 'back': 180, 'left': -90, 'right': 90}.get(view, 0)
    if isinstance(view, (int, float)):
        yaw = view
    a = np.radians(yaw)
    return np.array([[np.cos(a), 0, -np.sin(a)], [0, 1, 0], [np.sin(a), 0, np.cos(a)]])


def render(meshes, view='front', size=900, out='preview.png', bg=(239, 239, 237), box=None, pad=0.04):
    R = _view_matrix(view)
    polys = []
    depths = []
    cols = []
    allv = []
    for v, f, c in meshes:
        if len(f) == 0:
            continue
        vv = v @ R.T
        allv.append(vv)
    if not allv:
        return
    allcat = np.concatenate(allv)
    if box is None:
        lo = allcat.min(0); hi = allcat.max(0)
    else:
        lo, hi = np.array(box[0], float), np.array(box[1], float)
        lo = lo @ R.T; hi = hi @ R.T
        lo, hi = np.minimum(lo, hi), np.maximum(lo, hi)
    ext = max(hi[0] - lo[0], hi[1] - lo[1]) * (1 + 2 * pad)
    cx = (lo[0] + hi[0]) / 2; cy = (lo[1] + hi[1]) / 2
    scale = size / ext
    light = np.array([0.35, 0.45, 0.82]); light /= np.linalg.norm(light)
    for (v, f, c), vv in zip([m for m in meshes if len(m[1])], allv):
        tri = vv[f]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        ln = np.linalg.norm(n, axis=1) + 1e-12
        n /= ln[:, None]
        n[n[:, 2] < 0] *= -1  # two-sided
        shade = 0.35 + 0.65 * np.clip(n @ light, 0, 1)
        z = tri[:, :, 2].mean(1)
        xy = np.empty((len(f), 3, 2))
        xy[:, :, 0] = (tri[:, :, 0] - cx) * scale + size / 2
        xy[:, :, 1] = size / 2 - (tri[:, :, 1] - cy) * scale
        col = (np.array(c)[None, :] * shade[:, None]).clip(0, 255).astype(np.uint8)
        polys.append(xy); depths.append(z); cols.append(col)
    xy = np.concatenate(polys); z = np.concatenate(depths); col = np.concatenate(cols)
    order = np.argsort(z)  # far (small z) first; camera looks toward -Z, viewer at +Z
    img = Image.new('RGB', (size, size), bg)
    d = ImageDraw.Draw(img)
    for i in order:
        p = xy[i]
        d.polygon([(p[0, 0], p[0, 1]), (p[1, 0], p[1, 1]), (p[2, 0], p[2, 1])], fill=tuple(col[i]))
    img.save(out)
    return img


def load_obj(fn):
    vs = []; fs = []
    with open(fn, encoding='utf-8', errors='ignore') as fh:
        for line in fh:
            if line.startswith('v '):
                vs.append([float(x) for x in line.split()[1:4]])
            elif line.startswith('f '):
                idx = [int(t.split('/')[0]) for t in line.split()[1:]]
                for k in range(1, len(idx) - 1):
                    fs.append([idx[0] - 1, idx[k] - 1, idx[k + 1] - 1])
    return np.array(vs, float), np.array(fs, int)


def bp3d_to_view(v):
    # BP3D: X+ = subject left, Y- = anterior, Z+ = up (mm)
    # viewer front: X right of screen = subject left, Y up, Z toward viewer = anterior
    return np.stack([v[:, 0], v[:, 2], -v[:, 1]], 1)


def hra_to_view(v):
    # HRA: X+ = subject left, Y up, Z+ anterior (meters) -> mm
    return v * 1000.0
