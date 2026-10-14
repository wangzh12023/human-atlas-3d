"""Female-only structures.

HRA (real reference anatomy, CC BY 4.0):
  uterus (fundus / body / cervix ...), uterine tubes (infundibulum, fimbriae, ampulla, isthmus), ovaries,
  breast (mammary lobes, lactiferous ducts & sinuses, nipple, areola, suspensory ligaments, fat)
Schematic (procedural, kind='proc'):
  vagina, clitoris (glans/body/crura), vestibular bulbs, labia minora, labia majora, mons pubis,
  female urethra, greater vestibular glands, round ligaments of uterus, ovarian ligaments
All female-only: sex = 2. 'vM' is a collapsed copy (never shown for the male).
writes CACHE/female_extra.pkl
"""
import os, sys, time
import numpy as np
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from register import *
from proc_geom import *
from proc_geom2 import ellipse_tube, pillow_profile

t0 = time.time()
P = load_pickle('male_pieces.pkl'); by = {p['en']: p for p in P}
FM = load_pickle('female_map.pkl')
S1 = load_pickle('fem_stage1.pkl')
SKP = load_pickle('skin_parts.pkl')
R1, t1, OFF = S1['R'], S1['t'], S1['OFF']
def W(v):
    w = (np.asarray(v, float) * 1000 + OFF) @ R1.T + t1
    k, y0 = S1.get('lean_k', 0.0), S1.get('lean_y0', 900.0)
    w[:, 0] -= np.where(w[:, 1] > y0, (w[:, 1] - y0) * k, 0.0)
    return w
F = lambda name: np.asarray(FM[by[name]['file']], float)

out = []


def add(en, zh, system, v, f, kind='hra', fma='', target=None):
    v = np.asarray(v, float); f = np.asarray(f, np.int64)
    v, f = clean_mesh(v, f)
    if target and len(f) > target:
        v, f = decimate(v, f, target)
    out.append(dict(en=en, zh=zh, system=system, v=v, f=f, kind=kind, sex=2, fma=fma))


def glb(fn):
    return {n.replace('VH_F_', ''): (W(v), f) for n, v, f in read_glb(os.path.join(HRA, fn))}


def merge_nodes(d, keys):
    vs, fs, o = [], [], 0
    for k in keys:
        v, f = d[k]
        v, f = weld(v, np.asarray(f), 1e-3)
        vs.append(v); fs.append(f + o); o += len(v)
    return np.vstack(vs), np.vstack(fs)


# ---------------------------------------------------------------- correct HRA organs into the warped pelvis
# HRA organs were registered to the HRA skeleton; our female skeleton is the warped (male topology) one which
# matches the HRA pelvis closely, so only a small residual correction is needed: fit HRA pelvis -> our pelvis.
pel = glb('3d-vh-f-pelvis.glb')
hra_pel = np.vstack([pel[k][0] for k in pel if 'compact' in k or k in ('sacrum',)])
our_pel = np.vstack([F('Left Hip Bone'), F('Right Hip Bone'), F('Sacrum')])
(s, R, t), _ = icp_similarity(hra_pel[fps(hra_pel, 3000)], our_pel[fps(our_pel, 3000)], iters=40, with_scale=True, init=(1.0, np.eye(3), np.zeros(3)), trim=0.9)
corr = lambda v: s * np.asarray(v) @ R.T + t
print('pelvis residual correction: scale %.3f, shift %s' % (s, np.round(t + (s * R - np.eye(3)) @ hra_pel.mean(0), 1)))

# ---------------------------------------------------------------- uterus
U = glb('3d-vh-f-uterus.glb')
U = {k: (corr(v), f) for k, (v, f) in U.items()}
v, f = merge_nodes(U, ['fundus_of_uterus', 'cornua'])
add('Fundus of Uterus', '子宫底', 'reproductive', v, f, fma='UBERON:0009853', target=3000)
v, f = merge_nodes(U, ['body_of_uterus', 'anterior_wall_of_uterus', 'posterior_wall_of_uterus'])
add('Body of Uterus', '子宫体', 'reproductive', v, f, fma='UBERON:0009853', target=7000)
v, f = merge_nodes(U, ['lower_uterine_segment', 'internal_cervical_os'])
add('Isthmus of Uterus', '子宫峡', 'reproductive', v, f, target=1200)
v, f = merge_nodes(U, ['cervix', 'external_cervical_os', 'cervicovaginal_junction'])
add('Cervix of Uterus', '子宫颈', 'reproductive', v, f, fma='UBERON:0000002', target=3500)
# ---------------------------------------------------------------- tubes & ovaries
for side, zs, S in (('L', '左', 'Left'), ('R', '右', 'Right')):
    T = glb('3d-vh-f-fallopian-tube-%s.glb' % side.lower())
    T = {k: (corr(v), f) for k, (v, f) in T.items()}
    keys = list(T)
    amp = [k for k in keys if 'ampulla' in k]; ist = [k for k in keys if 'isthmus' in k]
    inf = [k for k in keys if 'infundibulum' in k or 'fibria' in k or 'fimbria' in k]
    v, f = merge_nodes(T, amp); add(S + ' Ampulla of Uterine Tube', zs + '输卵管壶腹', 'reproductive', v, f, target=2500)
    v, f = merge_nodes(T, ist); add(S + ' Isthmus of Uterine Tube', zs + '输卵管峡', 'reproductive', v, f, target=800)
    v, f = merge_nodes(T, inf); add(S + ' Infundibulum and Fimbriae of Uterine Tube', zs + '输卵管漏斗与伞', 'reproductive', v, f, target=2200)
    O = glb('3d-vh-f-ovary-%s.glb' % side.lower())
    v, f = merge_nodes({k: (corr(v), f) for k, (v, f) in O.items()}, list(O))
    add(S + ' Ovary', zs + '卵巢', 'reproductive', v, f, fma='UBERON:0000992')

# key landmarks (female world)
ut_v = np.vstack([o['v'] for o in out if 'Uterus' in o['en'] or 'Cervix' in o['en']])
cervix = [o for o in out if o['en'] == 'Cervix of Uterus'][0]['v']
ext_os = cervix[np.argmin(cervix[:, 1] - 0.3 * cervix[:, 2])]   # lowest/anterior-ish tip of cervix
hipL, hipR = F('Left Hip Bone'), F('Right Hip Bone')
symL = hipL[np.argmin(hipL[:, 0])]; symR = hipR[np.argmax(hipR[:, 0])]
sym = (symL + symR) / 2                                         # pubic symphysis (medial-most pubis points)
sym_low = np.vstack([hipL[hipL[:, 0] < symL[0] + 6], hipR[hipR[:, 0] > symR[0] - 6]])
sym_bottom = sym_low[np.argmin(sym_low[:, 1])]
midx = sym[0]
skin_all = np.vstack([SKP['shared']['vF'], SKP['female']['vF']])
mid_skin = skin_all[np.abs(skin_all[:, 0] - midx) < 9]
print('symphysis', np.round(sym, 1), 'sym bottom', np.round(sym_bottom, 1), 'cervix os', np.round(ext_os, 1), 'midline x', round(midx, 1))


def skin_front(y):
    s = mid_skin[np.abs(mid_skin[:, 1] - y) < 4]
    s = s[s[:, 2] > 40]
    return s[:, 2].max() if len(s) else np.nan


# ---------------------------------------------------------------- vulva frame (anchored to the pubic symphysis)
# anterior commissure lies in front of / below the symphysis; the cleft runs ~70 mm down and back
ant = sym_bottom + np.array([0.0, -10.0, 30.0])
ant[0] = midx
dirc = np.array([0.0, -0.80, -0.60]); dirc /= np.linalg.norm(dirc)
post = ant + dirc * 72.0
cleft = smooth_path([post, ant * 0.5 + post * 0.5 + np.array([0, 0, 4.0]), ant], 30)   # posterior -> anterior
U = np.gradient(cleft, axis=0); U /= np.linalg.norm(U, axis=1, keepdims=True)
Xax = np.array([1.0, 0, 0])
Nn = np.cross(Xax, U); Nn *= np.sign(Nn[:, 2:3] + 1e-9)            # outward normal of the vulva (antero-inferior)
idx = np.arange(len(cleft))
at = lambda frac: np.array([np.interp(frac * (len(cleft) - 1), idx, cleft[:, k]) for k in range(3)])
nat = lambda frac: np.array([np.interp(frac * (len(cleft) - 1), idx, Nn[:, k]) for k in range(3)])
vest = at(0.30) - nat(0.30) * 7.0          # vaginal orifice
ure_meatus = at(0.62) - nat(0.62) * 5.0    # urethral meatus
glans = at(0.86) - nat(0.86) * 2.5         # clitoral glans under the prepuce
print('vulva: ant', np.round(ant, 1), 'post', np.round(post, 1), 'vestibule', np.round(vest, 1))

# ---------------------------------------------------------------- vagina: fibromuscular tube, vestibule -> fornix (behind the cervix)
fornix = ext_os + np.array([0, -3.0, -8.0])
ctrl = [vest, vest * 0.62 + fornix * 0.38 + np.array([0, 1, 2]), vest * 0.22 + fornix * 0.78, fornix]
path = smooth_path(ctrl, 30)
v, f = ellipse_tube(path, Xax, np.concatenate([np.linspace(10.0, 12.5, 15), np.linspace(12.5, 16.0, 15)]),
                    np.concatenate([np.linspace(4.5, 5.5, 15), np.linspace(5.5, 8.0, 15)]), seg=22)
add('Vagina', '阴道', 'reproductive', v, f, kind='proc', fma='UBERON:0000996')

# ---------------------------------------------------------------- female urethra (~4 cm, anterior to the vagina)
bl = np.asarray(FM[by['Urinary Bladder']['file']], float)
neck = bl[np.argmin(bl[:, 1] - 0.25 * bl[:, 2])]
path = smooth_path([neck, neck * 0.5 + ure_meatus * 0.5 + np.array([0, -1, 3]), ure_meatus], 20)
v, f = tube(path, 3.0, seg=12)
add('Female Urethra', '女性尿道', 'urinary', v, f, kind='proc', fma='UBERON:0001333')

# ---------------------------------------------------------------- clitoris: glans + body (bends toward the symphysis) + paired crura
knee_c = sym_bottom + np.array([0.0, -1.0, 16.0]); knee_c[0] = midx
cl_parts = [ellipsoid(glans, (3.4, 3.2, 3.6), 18, 12)]
cl_parts.append(tube(smooth_path([glans + [0, 1.5, -1.0], glans * 0.4 + knee_c * 0.6 + np.array([0, 3, 4]), knee_c], 16), np.linspace(3.2, 4.4, 16), seg=16))
for sx in (1, -1):
    hip = hipL if sx > 0 else hipR
    ram = hip[(np.abs(hip[:, 0] - midx) > 10) & (np.abs(hip[:, 0] - midx) < 48) & (hip[:, 1] < sym_bottom[1] - 6) & (hip[:, 1] > sym_bottom[1] - 55) & (hip[:, 2] > sym_bottom[2] - 45)]
    ram_c = ram[np.argmin(ram[:, 1])] if len(ram) else knee_c + np.array([sx * 30, -40, -28])
    crus = smooth_path([knee_c, knee_c + np.array([sx * 8, -6, -5]), ram_c * 0.55 + knee_c * 0.45 + np.array([-sx * 2, 0, 4]), ram_c + np.array([-sx * 6, 5, 6])], 24)
    cl_parts.append(tube(crus, np.concatenate([np.linspace(4.2, 3.8, 12), np.linspace(3.8, 1.6, 12)]), seg=14))
v, f = merge(*cl_parts)
add('Clitoris', '阴蒂', 'reproductive', v, f, kind='proc', fma='UBERON:0002411')

# ---------------------------------------------------------------- vestibular bulbs + greater vestibular (Bartholin) glands
for sx, zs, S in ((1, '左', 'Left'), (-1, '右', 'Right')):
    pts = np.array([knee_c + np.array([sx * 3.0, -5.0, -3.0])] + [at(fr) - nat(fr) * 10.0 + np.array([sx * (6 + 7 * np.sin(np.pi * (0.95 - fr))), 0, 0]) for fr in (0.70, 0.50, 0.30, 0.18)])
    path = smooth_path(pts, 26)
    v, f = ellipse_tube(path, Xax, np.concatenate([np.linspace(1.8, 4.0, 13), np.linspace(4.0, 2.6, 13)]),
                        np.concatenate([np.linspace(2.4, 7.0, 13), np.linspace(7.0, 4.0, 13)]), seg=16)
    add(S + ' Vestibular Bulb', zs + '前庭球', 'reproductive', v, f, kind='proc', fma='UBERON:0006690')
    g = ellipsoid(at(0.14) - nat(0.14) * 10.0 + np.array([sx * 9.0, 0, 0]), (4.0, 4.2, 4.6), 14, 10)
    add(S + ' Greater Vestibular Gland', zs + '前庭大腺', 'reproductive', g[0], g[1], kind='proc', fma='UBERON:0000460')


# ---------------------------------------------------------------- labia minora / majora: smooth pillows along the cleft
def labium(lat, out_off, r_lat, r_out, f0, f1, sx, n=28):
    fr = np.linspace(f0, f1, n)
    prof = pillow_profile(n, 0.18, 0.6)
    pts = np.array([at(x) for x in fr]); nn = np.array([nat(x) for x in fr])
    pts = pts + np.array([sx * 1.0, 0, 0]) * (lat * (0.55 + 0.45 * prof))[:, None] + nn * (out_off * prof)[:, None]
    return ellipse_tube(pts, Xax, r_lat * prof, r_out * prof, seg=18)


for sx, zs, S in ((1, '左', 'Left'), (-1, '右', 'Right')):
    v, f = labium(4.6, -1.0, 1.6, 7.0, 0.10, 0.92, sx)
    add(S + ' Labium Minus', zs + '小阴唇', 'reproductive', v, f, kind='proc', fma='UBERON:0012464')
    v, f = labium(14.0, -2.0, 8.5, 11.0, -0.04, 1.02, sx)
    add(S + ' Labium Majus', zs + '大阴唇', 'reproductive', v, f, kind='proc', fma='UBERON:0012463')

# mons pubis: rounded fat pad in front of the symphysis, under the skin
mons_c = sym + np.array([0.0, 12.0, 30.0]); mons_c[0] = midx
v, f = ellipsoid(mons_c, (46.0, 28.0, 13.0), 28, 16)
add('Mons Pubis', '阴阜', 'reproductive', v, f, kind='proc', fma='UBERON:0035115')

# ---------------------------------------------------------------- ligaments of uterus (round, ovarian)
fundus = [o for o in out if o['en'] == 'Fundus of Uterus'][0]['v']
for sx, zs, S in ((1, '左', 'Left'), (-1, '右', 'Right')):
    corn = fundus[np.argmax(sx * fundus[:, 0])]
    ov = [o for o in out if o['en'] == S + ' Ovary'][0]['v']
    ovc = ov.mean(0)
    v, f = tube(smooth_path([corn, (corn + ovc) / 2 + [0, -3, -2], ovc], 14), 1.8, seg=10)
    add(S + ' Ovarian Ligament', zs + '卵巢固有韧带', 'reproductive', v, f, kind='proc')
    # round ligament: from the cornu forward and laterally to the deep inguinal ring, then to the labium majus
    ring = np.array([midx + sx * 55.0, sym[1] + 30.0, sym[2] + 12.0])
    v, f = tube(smooth_path([corn + [0, -2, 4], corn * 0.4 + ring * 0.6 + [0, 8, 6], ring, ring * 0.5 + np.array([midx + sx * 18, sym_bottom[1] - 6, sym[2] + 14]) * 0.5], 24), 2.0, seg=10)
    add(S + ' Round Ligament of Uterus', zs + '子宫圆韧带', 'reproductive', v, f, kind='proc')

# ---------------------------------------------------------------- breast (HRA mammary gland), slightly scaled to the fitted chest
for side, zs, S in (('L', '左', 'Left'), ('R', '右', 'Right')):
    M = glb('3d-vh-f-mammary-gland-%s.glb' % side.lower())
    parts = {
        'Mammary Lobes': (['mammary_lobes'], '乳腺腺叶', 6000),
        'Lactiferous Ducts': (['main_lactiferous_ducts'], '输乳管', 5000),
        'Lactiferous Sinuses': (['main_lactiferous_sinuses'], '输乳管窦', 1600),
        'Nipple': (['nipple'], '乳头', 1200),
        'Areola': (['areola', 'areolar_tubercles'], '乳晕', 2500),
        'Suspensory Ligaments of Breast': (['suspensory_ligaments'], '乳房悬韧带（Cooper韧带）', 4000),
        'Breast Adipose Tissue': (['fat'], '乳房脂肪组织', 6000),
    }
    for en, (keys, zh, tgt) in parts.items():
        ks = [k for k in M if any(k.startswith(x) for x in keys)]
        v, f = merge_nodes(M, ks)
        add(S + ' ' + en, zs + zh, 'reproductive', v, f, fma='UBERON:0001911', target=tgt)

# male placeholder positions: collapse every female piece onto its own centroid (scaled to ~0) so the
# morph grows it from nothing; it is hidden for the male anyway.
for o in out:
    c = o['v'].mean(0)
    o['vF'] = o['v'].astype(np.float32)
    o['vM'] = (c + (o['v'] - c) * 0.02).astype(np.float32)
save_pickle(out, 'female_extra.pkl')
for o in out:
    print('%-46s %-6s %6d v %6d f' % (o['en'], o['kind'], len(o['v']), len(o['f'])))
print('done %.1fs' % (time.time() - t0))
