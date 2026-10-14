"""Step 5: assemble every piece (male BP3D + procedural + skin parts + female-only) into one list.

writes CACHE/all_pieces.pkl: list of dicts with en, zh, system, sex (0 both / 1 male / 2 female),
      vM, vF, f, file, fma, kind ('' | 'proc' | 'hra')
"""
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from register import TPSWarp, umeyama

t0 = time.time()
P = load_pickle('male_pieces.pkl')
FM = load_pickle('female_map.pkl')
SKP = load_pickle('skin_parts.pkl')
PROC = load_pickle('proc_male_fm.pkl')
FX = load_pickle('female_extra.pkl')

MALE_ONLY_NAMES = ('Penis', 'Testis', 'Epididymis', 'Seminal Vesicle', 'Prostate', 'Deferent Duct', 'Testicular', 'Urethra')
out = []
for p in P:
    if p['en'] == 'Skin':
        continue
    sex = 0
    if p['system'] == 'reproductive' or any(k in p['en'] for k in MALE_ONLY_NAMES):
        sex = 1
    out.append(dict(en=p['en'], zh=p['zh'], system=p['system'], sex=sex, vM=np.asarray(p['v'], float),
                    vF=np.asarray(FM[p['file']], float), f=np.asarray(p['f']), file=p['file'], fma=p['fma'], kind=''))
# BP3D 'Urethra' is the male urethra (runs through prostate and penis)
for o in out:
    if o['en'] == 'Urethra':
        o['en'] = 'Male Urethra'; o['zh'] = '男性尿道'

# pubic hair: shared; for the female, re-project the warped patch onto the mons (lower, flatter, triangular)
for o in out:
    if o['en'] == 'Pubic Hair':
        v = o['vF'].copy()
        top = v[:, 1].max()
        k = np.clip((top - v[:, 1]) / 60.0, 0, 1)
        v[:, 1] -= 10.0 + 6.0 * k            # sits slightly lower on the mons
        v[:, 2] -= 6.0 * k
        o['vF'] = v

# skin: shared (morphs), male genital region, female genital region
sh = SKP['shared']
out.append(dict(en='Skin', zh='皮肤', system='integument', sex=0, vM=sh['vM'], vF=sh['vF'], f=sh['f'], file='FJ2810', fma='FMA7163', kind=''))
gm = SKP['male']
out.append(dict(en='Skin of External Genitalia (Male)', zh='外生殖器皮肤（男）', system='integument', sex=1, vM=gm['vM'], vF=gm['vF'], f=gm['f'], file='FJ2810m', fma='FMA7163', kind=''))
gf = SKP['female']
out.append(dict(en='Skin of Vulva Region', zh='外阴区皮肤', system='integument', sex=2, vM=gf['vM'], vF=gf['vF'], f=gf['f'], file='HRA-skin-f', fma='UBERON:0002097', kind='hra'))

# scrotum (male only): smooth sac around the testes, under the skin patch
C = load_pickle('fem_controls.pkl')
from proc_geom import ellipsoid
by = {p['en']: p for p in P}
tl, tr = np.asarray(by['Left Testis']['v'], float), np.asarray(by['Right Testis']['v'], float)
c = (np.vstack([tl, tr]).min(0) + np.vstack([tl, tr]).max(0)) / 2
ext = (np.vstack([tl, tr]).max(0) - np.vstack([tl, tr]).min(0)) / 2
sv, sf = ellipsoid(c + np.array([0, -1.0, 0]), ext + np.array([5.0, 5.0, 5.0]), 28, 18)
out.append(dict(en='Scrotum', zh='阴囊', system='reproductive', sex=1, vM=sv, vF=sv * 0.0 + c, f=sf, file='proc-scrotum', fma='FMA18252', kind='proc'))

# procedural (sex 0) with their female positions
for p in PROC:
    out.append(dict(en=p['en'], zh=p['zh'], system=p['system'], sex=p.get('sex', 0), vM=np.asarray(p['vM'], float), vF=np.asarray(p['vF'], float),
                    f=np.asarray(p['f']), file='proc-' + p['en'].lower().replace(' ', '-'), fma='', kind='proc'))
# female-only structures (breast fat is subcutaneous adipose -> integument layer, shown translucent in close-ups)
for p in FX:
    if 'Breast Adipose' in p['en']:
        p['system'] = 'integument'
    out.append(dict(en=p['en'], zh=p['zh'], system=p['system'], sex=2, vM=np.asarray(p['vM'], float), vF=np.asarray(p['vF'], float),
                    f=np.asarray(p['f']), file='f-' + p['en'].lower().replace(' ', '-'), fma=p.get('fma', ''), kind=p.get('kind', 'hra')))

# Keep the presentation build consistent across sexes, and localize differences
# to the breasts and reproductive structures before making morph placeholders.
from female_shape import normalize_female
normalize_female(out)

# male-only pieces: female position = collapse onto own centre (they fade out anyway; avoids flying geometry)
for o in out:
    if o['sex'] == 1:
        cM = (o['vM'].min(0) + o['vM'].max(0)) / 2
        cF = (o['vF'].min(0) + o['vF'].max(0)) / 2 if o['en'] != 'Scrotum' else cM
        o['vF'] = cF + (o['vM'] - cM) * 0.02
    if o['sex'] == 2:
        cF = (o['vF'].min(0) + o['vF'].max(0)) / 2
        o['vM'] = cF + (o['vF'] - cF) * 0.02
    assert len(o['vM']) == len(o['vF']), o['en']
    assert len(o['vM']) < 65536, (o['en'], len(o['vM']))
save_pickle(out, 'all_pieces.pkl')
import collections
cnt = collections.Counter((o['system'], o['sex']) for o in out)
print('pieces', len(out))
for k in sorted(cnt):
    print('  ', k, cnt[k])
print('done %.1fs' % (time.time() - t0))
