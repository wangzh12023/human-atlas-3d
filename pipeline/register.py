"""Registration utilities: similarity ICP, Laplacian non-rigid ICP, thin-plate RBF warp."""
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.spatial import cKDTree
from common import vertex_normals


# ------------------------------------------------------------------ similarity
def umeyama(src, dst, with_scale=True):
    mu_s, mu_d = src.mean(0), dst.mean(0)
    xs, xd = src - mu_s, dst - mu_d
    cov = xd.T @ xs / len(src)
    U, D, Vt = np.linalg.svd(cov)
    S = np.eye(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        S[2, 2] = -1
    R = U @ S @ Vt
    s = (D * np.diag(S)).sum() / (xs ** 2).sum() * len(src) if with_scale else 1.0
    t = mu_d - s * R @ mu_s
    return s, R, t


def icp_similarity(src, dst, iters=40, with_scale=True, init=None, trim=0.9):
    """align point set src to dst; returns (s,R,t) and transformed src"""
    tree = cKDTree(dst)
    s, R, t = (1.0, np.eye(3), dst.mean(0) - src.mean(0)) if init is None else init
    src_tree_pts = src
    for it in range(iters):
        x = s * src @ R.T + t
        d, j = tree.query(x)
        # reverse correspondences for symmetry
        xt = cKDTree(x)
        d2, i2 = xt.query(dst)
        A = np.vstack([src, src[i2]]); B = np.vstack([dst[j], dst])
        dd = np.concatenate([d, d2])
        keep = dd <= np.quantile(dd, trim)
        s, R, t = umeyama(A[keep], B[keep], with_scale)
    return (s, R, t), s * src @ R.T + t


# ------------------------------------------------------------------ Laplacian
def uniform_laplacian(n, f):
    i = np.concatenate([f[:, 0], f[:, 1], f[:, 2], f[:, 1], f[:, 2], f[:, 0]])
    j = np.concatenate([f[:, 1], f[:, 2], f[:, 0], f[:, 0], f[:, 1], f[:, 2]])
    A = sp.coo_matrix((np.ones(len(i)), (i, j)), shape=(n, n)).tocsr()
    A.data[:] = 1.0
    deg = np.asarray(A.sum(1)).ravel()
    deg[deg == 0] = 1
    D = sp.diags(1.0 / deg)
    return sp.eye(n) - D @ A


def nricp(src_v, src_f, tgt_v, tgt_f, weights=None, stiffness=(30, 12, 5, 2, 0.8), iters=3, max_dist=60.0,
          normal_dot=0.2, reverse=True, fixed=None, verbose=False, tgt_tree=None):
    """Non-rigid ICP with Laplacian (detail preserving) regulariser.
    weights: per source vertex data weight (0 = follow neighbours only).
    fixed  : optional (idx, positions) hard-ish constraints (high weight)."""
    n = len(src_v)
    x0 = np.asarray(src_v, float)
    x = x0.copy()
    L = uniform_laplacian(n, src_f)
    LtL = (L.T @ L).tocsc()
    delta = LtL @ x0
    tgt_v = np.asarray(tgt_v, float)
    tree = tgt_tree or cKDTree(tgt_v)
    tn = vertex_normals(tgt_v, tgt_f)
    w0 = np.ones(n) if weights is None else np.asarray(weights, float)
    for alpha in stiffness:
        for it in range(iters):
            xn = vertex_normals(x, src_f)
            d, j = tree.query(x)
            nt = tn[j]
            c = tgt_v[j]
            # project onto target tangent plane (point-to-plane)
            cp = x + nt * ((c - x) * nt).sum(1, keepdims=True)
            ok = (d < max_dist) & ((xn * nt).sum(1) > normal_dot)
            w = w0 * ok
            T = cp.copy()
            if reverse:
                xt = cKDTree(x)
                d2, i2 = xt.query(tgt_v)
                okr = (d2 < max_dist) & ((xn[i2] * tn).sum(1) > normal_dot) & (w0[i2] > 0)
                acc = np.zeros((n, 3)); cnt = np.zeros(n)
                np.add.at(acc, i2[okr], tgt_v[okr]); np.add.at(cnt, i2[okr], 1)
                m = cnt > 0
                T[m] = (T[m] * w[m, None] + acc[m]) / (w[m, None] + cnt[m, None])
                w = w.copy(); w[m] = w[m] + w0[m] * np.minimum(cnt[m], 3) * 0.5
            W = sp.diags(w)
            A = (alpha * LtL + W).tocsc()
            rhs = alpha * delta + W @ T
            if fixed is not None:
                idx, pos = fixed
                big = np.zeros(n); big[idx] = 50.0
                A = A + sp.diags(big)
                rhs = rhs + big[:, None] * np.zeros((n, 3))
                rhs[idx] += 50.0 * pos
            solve = spla.factorized(A)
            x = np.stack([solve(rhs[:, k]) for k in range(3)], 1)
            if verbose:
                print('  alpha %.2f it %d  mean dist %.2f  active %d' % (alpha, it, d[ok].mean() if ok.any() else -1, ok.sum()))
    return x


# ------------------------------------------------------------------ thin plate RBF warp
class TPSWarp:
    """3-D thin-plate style RBF (phi = r) with affine part, smoothing lam."""

    def __init__(self, src, dst, lam=1.0, weights=None):
        src = np.asarray(src, float); dst = np.asarray(dst, float)
        n = len(src)
        self.c = src
        K = np.linalg.norm(src[:, None] - src[None], axis=2)
        w = np.ones(n) if weights is None else np.asarray(weights, float)
        # phi(r) = r is conditionally *negative* definite, so smoothing enters with a minus sign
        K[np.diag_indices(n)] -= lam / np.maximum(w, 1e-3)
        Pm = np.hstack([np.ones((n, 1)), src])
        A = np.zeros((n + 4, n + 4))
        A[:n, :n] = K; A[:n, n:] = Pm; A[n:, :n] = Pm.T
        b = np.zeros((n + 4, 3)); b[:n] = dst - src
        sol = np.linalg.solve(A, b)
        self.w = sol[:n]; self.a = sol[n:]

    def __call__(self, x, chunk=4000):
        x = np.asarray(x, float)
        out = np.empty_like(x)
        c32 = self.c.astype(np.float32); w32 = self.w.astype(np.float32)
        for s in range(0, len(x), chunk):
            xs = x[s:s + chunk]
            r = np.sqrt(((xs[:, None, :].astype(np.float32) - c32[None]) ** 2).sum(2))
            disp = r @ w32 + self.a[0] + xs @ self.a[1:]
            out[s:s + chunk] = xs + disp
        return out


def sample_mesh_points(v, f, n, seed=0):
    """area-weighted surface samples (points only)"""
    rng = np.random.default_rng(seed)
    tri = v[f]
    a = np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    p = a / a.sum()
    k = rng.choice(len(f), n, p=p)
    r1, r2 = rng.random(n), rng.random(n)
    s = np.sqrt(r1)
    return tri[k, 0] * (1 - s)[:, None] + tri[k, 1] * (s * (1 - r2))[:, None] + tri[k, 2] * (s * r2)[:, None], k


def fps(points, n, seed=0):
    """farthest point sampling (indices)"""
    pts = np.asarray(points, float)
    if len(pts) <= n:
        return np.arange(len(pts))
    rng = np.random.default_rng(seed)
    idx = [rng.integers(len(pts))]
    d = np.linalg.norm(pts - pts[idx[0]], axis=1)
    for _ in range(n - 1):
        i = int(np.argmax(d)); idx.append(i)
        d = np.minimum(d, np.linalg.norm(pts - pts[i], axis=1))
    return np.array(idx)
