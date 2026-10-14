"""Classify BodyParts3D IS-A pieces into the 15 display systems.

usage: python -I classify.py [system_to_list]
reads  ../body_data/bp3d/isa_index.json + isa_inclusion_relation_list.txt
writes ../body_data/bp3d/pieces_classified.json
"""
import json, re, collections, sys, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'body_data', 'bp3d')
rows = json.load(open(os.path.join(ROOT, 'isa_index.json'), encoding='utf-8'))

par = collections.defaultdict(set)
name = {}
for line in open(os.path.join(ROOT, 'isa_inclusion_relation_list.txt'), encoding='utf-8').read().splitlines()[1:]:
    p, pn, c, cn = line.split('\t')
    par[c].add(p); name[p] = pn; name[c] = cn


def ancestors(c):
    seen = set(); st = [c]
    while st:
        x = st.pop()
        for p in par.get(x, ()):
            if p not in seen:
                seen.add(p); st.append(p)
    return {name[x] for x in seen}


def has(n, *pats):
    return any(re.search(p, n) for p in pats)


MUSCLE_ANC = {'muscle organ', 'head of muscle organ', 'zone of muscle organ', 'musculature'}
BONE_ANC = {'bone organ', 'long bone', 'short bone', 'irregular bone', 'flat bone', 'vertebra', 'rib', 'phalanx of toe',
            'phalanx of finger', 'carpal bone', 'tarsal bone', 'metacarpal bone', 'metatarsal bone', 'sesamoid bone'}


def classify(r):
    n = r['name'].lower()
    anc = ancestors(r['fma']) if r['fma'] else set()
    A = lambda *a: any(x in anc for x in a)
    # 1 integument
    if n in ('skin', 'eyebrow', 'hair of head', 'pubic hair'):
        return 'integument'
    # 2 reproductive (organs only; penile vessels stay vascular)
    if has(n, r'penis', r'testis', r'epididym', r'seminal vesicle', r'prostat', r'deferent duct', r'ductus deferens') and not has(n, r'arter', r'vein'):
        return 'reproductive'
    # 3 heart (walls, valves, chambers) before vessels
    if has(n, r'cavity of (left|right) (atrium|ventricle)', r'wall of (left |right )?(atrium|ventricle)', r'papillary muscle', r'leaflet of', r'cusp of',
           r'chorda', r'\bheart\b'):
        return 'heart'
    # 4 vessels
    if A('artery', 'segment of arterial tree organ', 'arterial trunk', 'systemic arterial trunk', 'set of arteries', 'coronary artery') or \
            has(n, r'arter', r'aorta', r'palmar arch', r'plantar arch', r'arterial'):
        return 'arteries'
    if A('vein', 'segment of venous tree organ', 'venous trunk', 'set of veins', 'cardiac vein') or \
            has(n, r'\bvein', r'vena', r'venous', r'sagittal sinus', r'transverse sinus', r'sigmoid sinus', r'coronary sinus', r'portal', r'hepatovenous'):
        return 'veins'
    # 5 muscles (FMA ancestors are reliable; name rules would catch bones like 'trapezium')
    if A(*MUSCLE_ANC) or (has(n, r'\bmuscle\b', r'diaphragm', r'sphincter', r'trapezius\b') and not has(n, r'nerve')):
        return 'muscles'
    # 6 respiratory (airway + larynx/nose cartilage and ligaments)
    if A('segment of bronchial tree', 'segment of tracheobronchial tree', 'pulmonary segment of bronchial tree', 'laryngeal cartilage') or \
            has(n, r'\blung', r'bronch', r'trache', r'laryn', r'epiglott', r'arytenoid', r'cricoid', r'thyroid cartilage', r'corniculate', r'cuneiform cartilage',
                r'vocal ligament', r'thyrohyoid ligament', r'cricothyroid ligament', r'hyo-epiglottic', r'thyro-epiglottic', r'nasal cartilage', r'alar cartilage',
                r'conus elasticus', r'thyrohyoid membrane'):
        return 'respiratory'
    # 7 urinary / endocrine / lymphatic
    if has(n, r'kidney', r'ureter', r'urinary bladder', r'urethra'):
        return 'urinary'
    if has(n, r'adrenal', r'thyroid gland', r'parathyroid', r'pituitary', r'pineal'):
        return 'endocrine'
    if has(n, r'spleen', r'thymus', r'tonsil', r'lymph'):
        return 'lymphatic'
    # 8 digestive (before nervous: 'caudate lobe of liver')
    if has(n, r'stomach', r'esophag', r'duoden', r'jejun', r'ileum', r'ileocecal', r'colon', r'cecum', r'append', r'rectum', r'anal canal', r'liver', r'hepatic biliary',
           r'hepatic duct', r'gallbladder', r'bile', r'cystic duct', r'pancrea', r'tongue', r'tooth', r'parotid', r'submandibular gland', r'sublingual gland',
           r'pharyn', r'mesenter', r'mesocolon', r'mesoappendix', r'omentum', r'gingiva', r'palate', r'\blip\b', r'taenia', r'pterygomandibular raphe'):
        return 'digestive'
    # 9 sensory organs (eye, ear and their adnexa)
    if has(n, r'sclera', r'cornea', r'\blens\b', r'retina\b', r'optic part of', r'choroid$', r'\biris\b', r'corona ciliaris', r'vitreous', r'eyeball', r'lacrimal (gland|sac|lake|canaliculus)',
           r'nasolacrimal', r'conjunctiva', r'tarsal plate', r'check ligament', r'common tendinous ring', r'suspensory ligament of', r'external ear', r'cochlea', r'tympan',
           r'malleus', r'incus', r'stapes', r'semicircular', r'(left|right) choroid', r'trochlea of'):
        return 'sensory'
    # 10 nervous
    if A('segment of neuraxis', 'nerve', 'segment of neural tree organ', 'cell part cluster of neuraxis', 'gyrus of neuraxis', 'nucleus of brain',
         'white matter of neuraxis', 'gray matter of neuraxis') or \
            has(n, r'brain', r'cerebr', r'cerebell', r'spinal cord', r'\bnerve', r'ganglion', r'thalam', r'hippocamp', r'\bpons\b', r'medulla oblongata', r'midbrain',
                r'corpus callosum', r'ventricle', r'choroid plexus', r'optic tract', r'optic chiasm', r'gyrus', r'lobule', r'caudate nucleus', r'putamen', r'pallid',
                r'amygdal', r'insula', r'mammillary', r'fornix', r'internal capsule', r'peduncle', r'colliculus', r'commissure', r'habenula', r'hypothalamus',
                r'lamina terminalis', r'stria', r'tuber cinereum', r'septum of telencephalon', r'tentorium', r'geniculate', r'occipital lobe', r'interpeduncular', r'aqueduct',
                r'central canal', r'interventricular foramen'):
        return 'nervous'
    # 11 ligaments / tendons / cartilage / discs
    if has(n, r'ligament', r'tendon', r'menisc', r'cartilage', r'\bdisk\b', r'retinaculum', r'iliotibial tract', r'linea alba', r'membrane', r'tendinous arch',
           r'symphysis', r'raphe'):
        return 'ligaments'
    # 12 skeleton
    if A(*BONE_ANC) or has(n, r'\bbone\b', r'vertebra', r'\brib\b', r'sternum', r'manubrium', r'xiphoid', r'femur', r'tibia\b', r'fibula\b', r'patella\b', r'humerus',
                           r'radius', r'ulna\b', r'scapula\b', r'clavicle', r'mandible', r'maxilla', r'phalanx', r'calcaneus', r'talus', r'sacrum', r'coccyx',
                           r'^atlas$', r'^axis$', r'ethmoid', r'vomer', r'concha', r'capitate', r'hamate', r'lunate', r'pisiform', r'scaphoid', r'trapezium', r'trapezoid', r'triquetral'):
        return 'skeleton'
    return 'other'


def main():
    out = []
    cnt = collections.Counter()
    for r in rows:
        s = classify(r)
        cnt[s] += 1
        rr = dict(r); rr['system'] = s
        out.append(rr)
    json.dump(out, open(os.path.join(ROOT, 'pieces_classified.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    for k, v in cnt.most_common():
        print(v, k)
    if len(sys.argv) > 1:
        want = sys.argv[1]
        for r in out:
            if r['system'] == want:
                print('  ', r['file'], r['name'])


if __name__ == '__main__':
    main()
