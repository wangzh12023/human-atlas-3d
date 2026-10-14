"""Verify regenerated anatomy geometry; optionally compare original assembly.

Usage: python tools/check-shape.py [baseline-all_pieces.pkl]
"""
import pickle
import sys
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1]
with (root.parent / 'body_data/cache/all_pieces.pkl').open('rb') as stream:
    pieces = pickle.load(stream)

shared = [p for p in pieces if p['sex'] == 0 and p['en'] != 'Skin']
assert all(np.array_equal(p['vM'], p['vF']) for p in shared), 'Shared anatomy must not morph'
assert all(np.isfinite(p['vF']).all() for p in pieces), 'Invalid female coordinates'
skin = next(p for p in pieces if p['en'] == 'Skin')
displacement = skin['vF'] - skin['vM']
assert not displacement[skin['vM'][:, 1] < 1100].any(), 'Skin changes below the chest'
assert not displacement[:, :2].any(), 'Body width or height changes'
assert np.all(displacement[:, 2] >= 0), 'Breast sculpt folds inward into the chest'
assert np.isfinite(skin['normalF']).all(), 'Invalid skin sculpt normals'
assert np.allclose(np.linalg.norm(skin['normalF'], axis=1), 1), 'Unnormalized skin normals'

by_name = {p['en']: p for p in pieces}
for part in ['Breast Adipose Tissue', 'Nipple', 'Areola', 'Mammary Lobes']:
    left, right = by_name['Left ' + part], by_name['Right ' + part]
    assert np.allclose(left['vF'] * [-1, 1, 1], right['vF']), 'Breast asymmetry: ' + part
    if part == 'Breast Adipose Tissue':
        f = left['f']
        edges = np.sort(np.vstack([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
        assert np.all(np.unique(edges, axis=0, return_counts=True)[1] == 2), 'Open breast envelope'
        triangles = left['vF'][f]
        areas = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0],
                                       triangles[:, 2] - triangles[:, 0]), axis=1)
        assert np.all(areas > 1e-6), 'Degenerate breast faces'
        assert left['vF'][:, 2].max() > 250, 'Insufficient breast projection'

if len(sys.argv) > 1:
    with Path(sys.argv[1]).open('rb') as stream:
        baseline = pickle.load(stream)
    assert len(pieces) == len(baseline)
    for current, original in zip(pieces, baseline):
        assert current['en'] == original['en'], 'Assembly order changed'
        if current['sex'] != 2:
            assert np.array_equal(current['vM'], original['vM']), 'Male geometry changed'
            assert np.array_equal(current['f'], original['f']), 'Male topology changed'
    print('PASS: original male geometry and topology preserved')

print('PASS: %d shared structures identical; localized skin morph; symmetric, closed breasts' % len(shared))
