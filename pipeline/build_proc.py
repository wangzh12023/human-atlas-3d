"""Build schematic structures that BodyParts3D lacks, fitted to the (male) skeleton, right side + mirror.

Knee   : ACL, PCL, MCL, LCL, patellar ligament, quadriceps tendon, medial & lateral menisci
Ankle  : ATFL, CFL, PTFL, deltoid ligament, anterior inferior tibiofibular ligament
Foot   : plantar fascia
Trunk  : rectus abdominis, internal oblique, transversus abdominis, latissimus dorsi, quadratus lumborum
Pelvis : coccyx, scrotum (male)

All are tagged kind='proc' so the UI marks them as schematic.
writes CACHE/proc_male.pkl
"""
import os, sys
import numpy as np
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from proc_geom import *

P = load_pickle('male_pieces.pkl')
by = {p['en']: p for p in P}
V = lambda n: np.asarray(by[n]['v'], float)

out = []


def add(en, zh, system, vf, side=None, sex=0, mirror_too=True, extra=None):
    v, f = vf
    if side == 'R' and mirror_too:
        out.append(dict(en='Right ' + en, zh='右' + zh, system=system, v=v, f=f, kind='proc', sex=sex))
        v2, f2 = mirror(v, f)
        out.append(dict(en='Left ' + en, zh='左' + zh, system=system, v=v2, f=f2, kind='proc', sex=sex))
    else:
        out.append(dict(en=en, zh=zh, system=system, v=v, f=f, kind='proc', sex=sex))


def closest(points, p):
    t = cKDTree(points)
    return points[t.query(p)[1]]


# ================================================================== KNEE (right; x negative)
fe, ti, fi, pa = V('Right Femur'), V('Right Tibia'), V('Right Fibula'), V('Right Patella')
med_cond = np.array([-51.8, 446.2, 78.9]); lat_cond = np.array([-103.0, 451.2, 75.2])
med_epi = np.array([-31.7, 480.6, 72.7]); lat_epi = np.array([-112.9, 476.1, 74.9])
tib_top = 452.6
notch = np.array([-77.4, 455.0, 70.0])
tub = np.array([-83.9, 396.4, 113.6])
fib_head = np.array([-112.0, 432.0, 60.0])
pat_apex = np.array([-86.8, 441.5, 109.3]); pat_base = np.array([-82.5, 478.0, 111.6])

# ACL: from posteromedial aspect of lateral femoral condyle (inside the notch) to anterior intercondylar area of tibia
acl_fem = np.array([-88.0, 462.0, 62.0]); acl_tib = np.array([-73.0, tib_top - 1.0, 88.0])
add('Anterior Cruciate Ligament', '前交叉韧带', 'ligaments', tube(smooth_path([acl_fem, (acl_fem + acl_tib) / 2 + [0, 0, 2], acl_tib], 18), np.linspace(4.2, 5.4, 18), twist=0.9, flat=0.7), 'R')
# PCL: lateral surface of medial femoral condyle (anterior notch) to posterior intercondylar area (below plateau)
pcl_fem = np.array([-66.0, 463.0, 82.0]); pcl_tib = np.array([-76.0, tib_top - 12.0, 58.0])
add('Posterior Cruciate Ligament', '后交叉韧带', 'ligaments', tube(smooth_path([pcl_fem, (pcl_fem + pcl_tib) / 2 + [0, 2, -6], pcl_tib], 18), np.linspace(5.6, 5.0, 18), twist=-0.6, flat=0.65), 'R')
knee_surf = BoneSurface([(fe, by['Right Femur']['f']), (ti, by['Right Tibia']['f']), (fi, by['Right Fibula']['f']), (pa, by['Right Patella']['f'])])
# MCL: medial epicondyle -> medial tibia ~ 60mm below joint line (broad flat band hugging the bones)
mcl_path = hug(smooth_path([med_epi + [3.5, 4, 0], [-31.0, 452.0, 76.0], [-36.0, 420.0, 80.0], [-41.0, 392.0, 84.0]], 22), knee_surf, [0.8, 1.8, 1.8, 1.8, 1.0])
add('Medial Collateral Ligament of Knee', '膝内侧副韧带', 'ligaments', band(mcl_path, np.linspace(13, 17, len(mcl_path)) * taper(len(mcl_path), 0.6), 2.4, up_hint=[1, 0, 0]), 'R')
# LCL: lateral epicondyle -> fibular head (cord standing slightly off the joint line)
lcl_path = hug(smooth_path([lat_epi + [-3, 2, -2], [-117.0, 455.0, 68.0], fib_head + [-5, 6, 0]], 18), knee_surf, [1.2, 4.0, 3.6, 1.2])
add('Lateral Collateral Ligament of Knee', '膝外侧副韧带', 'ligaments', tube(lcl_path, 3.3 * taper(len(lcl_path), 0.8)), 'R')
# Patellar ligament: patellar apex -> tibial tuberosity (thick flat)
pl_path = hug(smooth_path([pat_apex + [0, 3, 2], [-85.0, 420.0, 114.5], tub + [0, 2, 1.5]], 20), knee_surf, [3.0, 4.5, 4.5, 2.5])
add('Patellar Ligament', '髌韧带', 'ligaments', band(pl_path, np.linspace(24, 20, len(pl_path)) * taper(len(pl_path), 0.8, 0.4), np.linspace(5.5, 4.0, len(pl_path)), up_hint=[0, 0, 1], seg_w=8), 'R')
# Quadriceps tendon: above patella base
qt_path = hug(smooth_path([[-82.0, 548.0, 110.0], [-82.0, 510.0, 113.0], pat_base + [0, -3, 2]], 20), knee_surf, [9.0, 7.5, 6.0])
add('Quadriceps Tendon', '股四头肌腱', 'ligaments', band(qt_path, np.linspace(22, 40, len(qt_path)) * taper(len(qt_path), 0.8, 0.4), np.linspace(4.5, 6.5, len(qt_path)), up_hint=[0, 0, 1], seg_w=8), 'R')
# Menisci on tibial plateau. Medial: larger C (open laterally), lateral: nearly O (open medially)
add('Medial Meniscus', '内侧半月板', 'ligaments', crescent((-56.0, tib_top - 0.5, 82.0), 23.0, 26.0, 0.42, 6.5, 70, 180), 'R')
add('Lateral Meniscus', '外侧半月板', 'ligaments', crescent((-95.0, tib_top - 0.5, 80.0), 19.0, 20.0, 0.45, 6.0, 40, 0), 'R')

# ================================================================== ANKLE / FOOT (right)
lat_mal = np.array([-98.2, 52.2, 54.6]); med_mal = np.array([-52.1, 72.2, 84.6])
ta = V('Right Talus'); ca = V('Right Calcaneus'); nav = V('Navicular Bone of Right Foot')
ankle_surf = BoneSurface([(by[n]['v'], by[n]['f']) for n in ['Right Tibia', 'Right Fibula', 'Right Talus', 'Right Calcaneus', 'Navicular Bone of Right Foot']])
# ATFL: anterior lateral malleolus -> talar neck (lateral)
atfl_a = np.array([-100.0, 58.0, 66.0]); atfl_b = np.array([-88.0, 62.0, 88.0])
add('Anterior Talofibular Ligament', '距腓前韧带', 'ligaments', band(hug(smooth_path([atfl_a, (atfl_a + atfl_b) / 2 + [-3, 0, 0], atfl_b], 14), ankle_surf, 1.4), 9.0 * taper(14, 0.7), 2.6, up_hint=[1, 0, 0]), 'R')
# CFL: tip of lateral malleolus -> lateral calcaneus (down and back)
cfl_a = lat_mal + [-1, 2, 0]; cfl_b = np.array([-101.5, 30.0, 44.0])
add('Calcaneofibular Ligament', '跟腓韧带', 'ligaments', tube(hug(smooth_path([cfl_a, (cfl_a + cfl_b) / 2 + [-3, 0, 0], cfl_b], 14), ankle_surf, [1.2, 3.0, 1.2]), 3.2 * taper(14, 0.75)), 'R')
# PTFL: posterior malleolar fossa -> posterior talus (horizontal, medial)
ptfl_a = np.array([-97.0, 60.0, 47.0]); ptfl_b = np.array([-72.0, 58.0, 46.0])
add('Posterior Talofibular Ligament', '距腓后韧带', 'ligaments', tube(hug(smooth_path([ptfl_a, (ptfl_a + ptfl_b) / 2 + [0, 0, -3], ptfl_b], 14), ankle_surf, [1.0, 2.6, 1.0]), 3.5 * taper(14, 0.75), flat=0.6), 'R')
# Deltoid ligament: fan from medial malleolus to navicular, talus and sustentaculum (3 bands merged)
dl_parts = []
for tgt, w in [([-62.0, 58.0, 104.0], 9.0), ([-48.5, 52.0, 86.0], 11.0), ([-50.0, 40.0, 66.0], 10.0)]:
    dl_parts.append(band(hug(smooth_path([med_mal + [3, -2, 0], (med_mal + np.array(tgt)) / 2 + [4, 0, 0], tgt], 12), ankle_surf, 1.3), np.linspace(7, w, 12) * taper(12, 0.75), 2.4, up_hint=[1, 0, 0]))
add('Deltoid Ligament of Ankle', '踝三角韧带', 'ligaments', merge(*dl_parts), 'R')
# AITFL: distal anterior tibia -> anterior fibula, oblique
aitfl_a = np.array([-80.0, 92.0, 86.0]); aitfl_b = np.array([-97.0, 80.0, 70.0])
add('Anterior Inferior Tibiofibular Ligament', '胫腓前韧带', 'ligaments', band(hug(smooth_path([aitfl_a, aitfl_b], 10), ankle_surf, 1.3), 10.0 * taper(10, 0.75), 2.4, up_hint=[0, 0, 1]), 'R')
# Plantar fascia: calcaneal tuberosity (medial process) fanning to metatarsal heads
heel = np.array([-70.0, 12.0, 38.0])
heads = [np.array([-90.0, 12.5, 188.0]), np.array([-104.0, 11.0, 184.0]), np.array([-117.0, 10.5, 176.0]), np.array([-129.0, 10.0, 168.0]), np.array([-140.0, 9.5, 156.0])]
pf = []
for k, h in enumerate(heads):
    mid = heel * 0.45 + h * 0.55 + np.array([0, -1.5, 0])
    path = smooth_path([heel + [-k * 2.5, 0, 6], mid, h + [0, 0, -14]], 24)
    w = np.concatenate([np.linspace(13, 7.5, 12), np.linspace(7.5, 6.0, 12)])
    pf.append(band(path, w, 2.2, up_hint=[0, 1, 0]))
add('Plantar Fascia', '足底筋膜', 'ligaments', merge(*pf), 'R')

# ================================================================== TRUNK MUSCLES
eo = by['Right External Oblique']
eo_v, eo_f = np.asarray(eo['v'], float), np.asarray(eo['f'], int)
outer = front_layer(eo_v, eo_f)
cen = eo_v[eo_f].mean(1)

# Rectus abdominis: the medial strip of the anterior wall (where BP3D sculpted the six-pack),
# lifted slightly so it reads as its own structure.
ra_mask = outer & (cen[:, 0] > -66) & (cen[:, 0] < -7.5) & (cen[:, 1] > 880) & (cen[:, 1] < 1262)
add('Rectus Abdominis', '腹直肌', 'muscles', slab(eo_v, eo_f[ra_mask], 0.9, 8.0), 'R')
# Internal oblique / transversus abdominis: deep lateral layers (fibres lateral to the linea semilunaris)
io_mask = outer & (cen[:, 0] < -52) & (cen[:, 1] > 880) & (cen[:, 1] < 1150)
add('Internal Oblique', '腹内斜肌', 'muscles', slab(eo_v, eo_f[io_mask], -9.0, 5.0), 'R')
ta_mask = outer & (cen[:, 0] < -45) & (cen[:, 1] > 885) & (cen[:, 1] < 1185)
add('Transversus Abdominis', '腹横肌', 'muscles', slab(eo_v, eo_f[ta_mask], -15.5, 3.5), 'R')


# Latissimus dorsi: lofted sheet from the thoracolumbar fascia / iliac crest to the humerus,
# wrapped onto the back by ray casting against the underlying muscles.
def latissimus():
    hum_ins = np.array([-148.0, 1330.0, 74.0])
    K, M = 14, 30
    origins = []
    for t in np.linspace(0, 1, K):
        if t < 0.72:   # vertebral origin T7 -> L5 (posterior midline)
            y = 1255 - (t / 0.72) * 270
            origins.append(np.array([-4.0, y, -14.0]))
        else:          # iliac crest, running laterally
            u = (t - 0.72) / 0.28
            origins.append(np.array([-4.0 - u * 108.0, 985.0 + u * 22.0, -10.0 + u * 34.0]))
    G = np.zeros((K, M, 3))
    for k, o in enumerate(origins):
        mid = o * 0.45 + hum_ins * 0.55 + np.array([-45.0, -25.0 + 30 * k / K, -38.0])
        path = smooth_path([o, mid, hum_ins + [0, -8 + 16 * k / (K - 1), 0]], M)
        idx = np.linspace(0, len(path) - 1, M)
        G[k] = np.array([np.interp(idx, np.arange(len(path)), path[:, d]) for d in range(3)]).T
    under_names = [n for n in by if by[n]['system'] in ('muscles', 'skeleton') and by[n]['v'][:, 2].mean() < 70
                   and 940 < by[n]['v'][:, 1].mean() < 1400 and 'Trapezius' not in n and 'Deltoid' not in n
                   and 'Triceps' not in n and abs(by[n]['v'][:, 0].mean()) < 175]
    meshes = [(by[n]['v'], by[n]['f']) for n in under_names]
    w = np.ones((K, M)); w[:, int(M * 0.72):] = np.linspace(1, 0, M - int(M * 0.72))[None]
    G2, ok = raycast_wrap(G, meshes, lambda p: np.array([min(0.0, p[0] * 0.15), p[1], 95.0]), push=3.0, weight=w)
    # smooth across fibres
    for _ in range(3):
        G2[1:-1] = G2[1:-1] * 0.5 + (G2[:-2] + G2[2:]) * 0.25
        G2[:, 1:-1] = G2[:, 1:-1] * 0.6 + (G2[:, :-2] + G2[:, 2:]) * 0.2
    v, f = grid_surface(G2)
    # thickness tapers toward the tendon
    return slab(v, f, 2.0, 5.0)
add('Latissimus Dorsi', '背阔肌', 'muscles', latissimus(), 'R')


# Quadratus lumborum: 12th rib & L1-L4 transverse processes -> iliac crest; quadrilateral slab (deep)
def ql():
    path = smooth_path([[-48.0, 1095.0, 40.0], [-55.0, 1040.0, 44.0], [-62.0, 990.0, 40.0], [-70.0, 958.0, 34.0]], 20)
    return band(path, np.concatenate([np.linspace(30, 44, 10), np.linspace(44, 52, 10)]), 12.0, up_hint=[0, 0, 1], seg_w=6)
add('Quadratus Lumborum', '腰方肌', 'muscles', ql(), 'R')

# ================================================================== PELVIS: coccyx (4 fused segments)
sac = V('Sacrum')
apex = sac[np.argmin(sac[:, 1])]
segs = []
p0 = apex + np.array([0, -2.0, -1.0])
for k, (w, h) in enumerate([(13, 9), (10, 7.5), (8, 6.5), (6, 5)]):
    c = p0 + np.array([0, -h * 0.9, 3.5 * k])
    segs.append(ellipsoid(c, (w, h * 0.55, h * 0.75), 14, 8))
    p0 = c + np.array([0, -h * 0.5, 1.5])
add('Coccyx', '尾骨', 'skeleton', merge(*segs))

save_pickle(out, 'proc_male.pkl')
for p in out:
    print('%-44s %6d v %6d f' % (p['en'], len(p['v']), len(p['f'])))
