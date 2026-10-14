"""Female step 2: part-aware fit of the male skin onto the HRA female skin.
1. label male skin vertices (head / torso / legL / legR / armL / armR) via nearest bone
2. per-part similarity ICP to the female skin (coarse) + TPS blend
3. label female points by nearest coarse-warped male vertex; NRICP with same-label correspondences
writes CACHE/fem_skin.pkl
"""
import os, sys, time
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from register import *

t0 = time.time()
P = load_pickle('male_pieces.pkl'); by = {p['en']: p for p in P}
S1 = load_pickle('fem_stage1.pkl')
fv, ff = S1['fskin_v'], S1['fskin_f']
sv, sf = np.asarray(by['Skin']['v'], float), np.asarray(by['Skin']['f'])
HEAD, TORSO, LEGL, LEGR, ARML, ARMR = range(6)

# ---------------------------------------------------------------- male labels via nearest bone
ARM = ('Humerus', 'Radius', 'Ulna', 'Metacarpal', 'Phalanx of', 'Scaphoid', 'Lunate', 'Triquetral', 'Pisiform', 'Trapezium', 'Trapezoid', 'Capitate', 'Hamate')
LEG = ('Femur', 'Tibia', 'Fibula', 'Patella', 'Talus', 'Calcaneus', 'Navicular', 'Cuboid', 'Cuneiform', 'Metatarsal', 'Sesamoid')
HEADB = ('Mandible', 'Maxilla', 'Frontal', 'Parietal', 'Occipital', 'Temporal', 'Sphenoid', 'Ethmoid', 'Zygomatic', 'Nasal', 'Vomer', 'Lacrimal', 'Palatine', 'Concha', 'Hyoid')


def bone_labels():
    bp, bl = [], []
    for p in P:
        if p['system'] != 'skeleton':
            continue
        n = p['en']; cx = p['v'][:, 0].mean()
        toe = 'toe' in n.lower() or 'foot' in n.lower()
        if any(k in n for k in ARM) and not toe:
            lab = ARML if cx > 0 else ARMR
        elif any(k in n for k in LEG) or toe:
            lab = LEGL if cx > 0 else LEGR
        elif any(k in n for k in HEADB):
            lab = HEAD
        else:
            lab = TORSO
        bp.append(p['v']); bl.append(np.full(len(p['v']), lab))
    return np.vstack(bp), np.concatenate(bl)


BP, BL = bone_labels()


def label_points(pts):
    _, j = cKDTree(BP).query(pts)
    lab = BL[j].copy()
    lab[(lab == HEAD) & (pts[:, 1] < 1490)] = TORSO   # neck belongs to torso
    lab[(lab == TORSO) & (pts[:, 1] > 1560)] = HEAD
    return lab


if __name__ == '__main__':
    lab_m = label_points(sv)
    # genital patch (male only, removed from the shared skin)
    gen_names = [n for n in by if any(k in n for k in ('Penis', 'Testis', 'Epididymis'))]
    dg, _ = cKDTree(np.vstack([by[n]['v'] for n in gen_names])).query(sv)
    genital = (dg < 14.0) & (sv[:, 1] < 880)
    fmask = genital[sf].any(1)
    sh_v, sh_f = clean_mesh(sv, sf[~fmask])
    used = np.unique(sf[~fmask]); lab_sh = lab_m[used]
    gen_v, gen_f = clean_mesh(sv, sf[fmask])
    print('shared skin', sh_v.shape, 'labels', np.bincount(lab_sh))

    # ------------------------------------------------------------ female coarse part regions
    H = fv[:, 1].max()
    fcx = np.median(fv[(fv[:, 1] > 850) & (fv[:, 1] < 1100)][:, 0])
    reg = {
        HEAD: fv[fv[:, 1] > H * 0.885],
        TORSO: fv[(fv[:, 1] > 760) & (fv[:, 1] < H * 0.86) & (np.abs(fv[:, 0] - fcx) < 150)],
        LEGL: fv[(fv[:, 1] < 700) & (fv[:, 0] > fcx + 4)],
        LEGR: fv[(fv[:, 1] < 700) & (fv[:, 0] < fcx - 4)],
    }
    msel = {
        HEAD: sh_v[(lab_sh == HEAD)],
        TORSO: sh_v[(lab_sh == TORSO) & (sh_v[:, 1] > 820) & (np.abs(sh_v[:, 0]) < 150)],
        LEGL: sh_v[(lab_sh == LEGL) & (sh_v[:, 1] < 760)],
        LEGR: sh_v[(lab_sh == LEGR) & (sh_v[:, 1] < 760)],
    }
    sims = {}
    for k in (HEAD, TORSO, LEGL, LEGR):
        a = msel[k][fps(msel[k], 2500)]; b = reg[k][fps(reg[k], 3000)]
        init = (1.0, np.eye(3), b.mean(0) - a.mean(0))
        (s, R, t), _ = icp_similarity(a, b, iters=40, with_scale=True, init=init, trim=0.88)
        sims[k] = (s, R, t)
        print('part', k, 'scale %.3f' % s, 'rot %.1f deg' % np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))), 't', np.round(t, 1))
    sims[ARML] = sims[TORSO]; sims[ARMR] = sims[TORSO]

    # coarse TPS from part samples
    cs, cd = [], []
    for k in range(6):
        pts = sh_v[lab_sh == k]
        if k in (ARML, ARMR):
            pts = pts[pts[:, 1] > 1250]  # only shoulders constrain; rest of the arm is carried along
        idx = fps(pts, 220 if k == TORSO else 120)
        s, R, t = sims[k]
        cs.append(pts[idx]); cd.append(s * pts[idx] @ R.T + t)
    cs = np.vstack(cs); cd = np.vstack(cd)
    tps = TPSWarp(cs, cd, lam=40.0)
    coarse = tps(sh_v)
    print('coarse TPS done %.1fs' % (time.time() - t0))

    # ------------------------------------------------------------ female labels via coarse
    _, jj = cKDTree(coarse).query(fv)
    lab_f = lab_sh[jj]
    dd = np.linalg.norm(fv - coarse[jj], axis=1)
    valid_f = (dd < 45.0) & ~np.isin(lab_f, (ARML, ARMR))
    tor = coarse[lab_sh == TORSO]
    ybins = np.linspace(700, 1700, 101)
    maxx = np.zeros(100); minx = np.zeros(100)
    bi = np.clip(np.digitize(tor[:, 1], ybins) - 1, 0, 99)
    for b in range(100):
        m = bi == b
        if m.any():
            maxx[b] = tor[m, 0].max(); minx[b] = tor[m, 0].min()
    fb = np.clip(np.digitize(fv[:, 1], ybins) - 1, 0, 99)
    side_ok = (fv[:, 0] < maxx[fb] + 10) & (fv[:, 0] > minx[fb] - 10)
    valid_f &= ~((lab_f == TORSO) & ~side_ok & (fv[:, 1] > 1000))
    print('female target points valid', valid_f.sum(), 'of', len(fv))

    # ------------------------------------------------------------ NRICP, label-restricted correspondences
    n = len(sh_v)
    L = uniform_laplacian(n, sh_f); LtL = (L.T @ L).tocsc()
    x = coarse.copy()
    delta = LtL @ coarse
    fn = vertex_normals(fv, ff)
    trees = {}
    for k in (HEAD, TORSO, LEGL, LEGR):
        idx = np.where(valid_f & (lab_f == k))[0]
        if len(idx):
            trees[k] = (idx, cKDTree(fv[idx]))
    w0 = np.where(np.isin(lab_sh, (ARML, ARMR)), 0.0, 1.0)
    w0[lab_sh == HEAD] = 0.8
    # pin the arms to their coarse (male-pose) position so the female arms are not followed
    pin = np.where(np.isin(lab_sh, (ARML, ARMR)), 6.0, 0.0)
    for alpha in (40, 16, 6, 2.5, 1.0):
        for it in range(3):
            xn = vertex_normals(x, sh_f)
            T = x.copy(); w = np.zeros(n)
            for k, (idx, tr) in trees.items():
                m = np.where(lab_sh == k)[0]
                d, j = tr.query(x[m])
                jj = idx[j]
                nt = fn[jj]
                ok = (d < 50) & ((xn[m] * nt).sum(1) > 0.1)
                cp = x[m] + nt * ((fv[jj] - x[m]) * nt).sum(1, keepdims=True)
                T[m[ok]] = cp[ok]; w[m[ok]] = w0[m[ok]]
            T[pin > 0] = coarse[pin > 0]; w = w + pin
            W = sp.diags(w)
            solve = spla.factorized((alpha * LtL + W).tocsc())
            rhs = alpha * delta + W @ T
            x = np.stack([solve(rhs[:, c]) for c in range(3)], 1)
        print('  alpha %.1f active %d' % (alpha, (w > 0).sum()))
    # relax folds near the part seams (armpits, groin, neck): smooth the displacement field there
    seam = np.zeros(n)
    e = np.vstack([sh_f[:, [0, 1]], sh_f[:, [1, 2]], sh_f[:, [2, 0]]])
    diff = lab_sh[e[:, 0]] != lab_sh[e[:, 1]]
    seam[e[diff].ravel()] = 1.0
    Lw = uniform_laplacian(n, sh_f)
    for _ in range(25):            # grow a soft band around the seams
        seam = np.maximum(seam, np.clip(seam - Lw @ seam, 0, 1) * 0.97)
    disp = x - coarse
    for _ in range(60):
        disp = disp - 0.5 * (seam[:, None] * (Lw @ disp))
    x = coarse + disp
    # final mild smoothing of positions in the seam band (removes residual wrinkles)
    for _ in range(10):
        x = x - 0.35 * (seam[:, None] * (Lw @ x))
    res = x
    dch = []
    for k, (idx, tr) in trees.items():
        d, _ = tr.query(res[lab_sh == k]); dch.append(d)
    dch = np.concatenate(dch)
    print('residual mean %.2f mm  p95 %.2f mm' % (dch.mean(), np.quantile(dch, 0.95)))
    save_pickle(dict(sh_vM=sh_v, sh_f=sh_f, sh_vF=res, lab=lab_sh, gen_v=gen_v, gen_f=gen_f, coarse=coarse,
                     ftarget_v=fv, ftarget_f=ff, valid_f=valid_f, sims=sims, tps_src=cs, tps_dst=cd), 'fem_skin.pkl')
    print('done %.1fs' % (time.time() - t0))
