"""Build the pipeline's IS-A OBJ index from original BodyParts3D headers.

Usage from the repository root: python -I pipeline/prepare_bp3d.py
"""
from pathlib import Path
import json
import re

root = Path(__file__).resolve().parents[2] / 'body_data' / 'bp3d'
directory = root / 'isa_obj' / 'isa_BP3D_4.0_obj_99'
files = sorted(directory.glob('*.obj'))
if not files:
    raise SystemExit('Extract isa_BP3D_4.0_obj_99.zip under ' + str(directory.parent))
result = []
for file in files:
    header = {}
    with file.open(encoding='utf-8', errors='replace') as stream:
        for line in stream:
            if line.startswith('v '):
                break
            match = re.match(r'#\s*(File ID|Representation ID|Concept ID|English name)\s*:\s*(.*)', line)
            if match:
                header[match[1]] = match[2].strip()
    if not header.get('English name') or not header.get('Concept ID'):
        raise ValueError('Missing source identity in ' + file.name)
    result.append(dict(file=file.stem, fma=header['Concept ID'],
                       rep=header.get('Representation ID', ''), name=header['English name']))
with (root / 'isa_index.json').open('w', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
print('Indexed', len(result), 'BodyParts3D OBJ files')
