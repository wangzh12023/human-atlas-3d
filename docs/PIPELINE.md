# 🧬 Model pipeline and verification

## Run the viewer without rebuilding models

`public/data/` contains the encoded assets required by the app. A normal clone needs only `npm ci` and `npm run dev`. Original OBJ/GLB files and Python caches are optional development inputs and are not included.

## Regeneration prerequisites

Use Python 3.10–3.12 with the packages in `pipeline/requirements.txt`. The pipeline uses NumPy, SciPy, trimesh, Open3D, and Pillow. The existing assets were generated with Python 3.10, NumPy 1.26.4, SciPy 1.15.3, trimesh 4.5.2, Open3D 0.18.0, and Pillow 10.4.0. Open3D installation depends on your Python version and platform; choose a Python version for which its wheel is available.

```bash
python -m pip install -r pipeline/requirements.txt
```

The expected input layout is a sibling of the repository:

```text
projects/
├── human-atlas-3d/
└── body_data/
    ├── bp3d/
    │   ├── isa_obj/isa_BP3D_4.0_obj_99/*.obj
    │   ├── isa_parts_list_e.txt
    │   ├── isa_inclusion_relation_list.txt
    │   └── isa_index.json
    ├── hra/                 # Original named GLB inputs
    └── cache/               # Generated local pickle files
```

Obtain the BodyParts3D IS-A mesh archive and associated metadata from the [official download page](https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html). `prepare_bp3d.py` creates `isa_index.json` from the original OBJ header identity fields: `file` (OBJ stem), `fma` (concept ID), `rep` (representation ID), and `name` (English label). It only indexes available OBJ files.

The HRA reference files and versioned downloads are recorded in [`public/data/sources.json`](../public/data/sources.json). Keep their original filenames under `body_data/hra/`. References include skin, pelvis, knees, sternum/manubrium, intervertebral discs, selected internal organs, uterus, uterine tubes, ovaries, and mammary glands.

## Generation order

Run each command from the repository root, stopping if any stage fails:

```bash
python -I pipeline/prepare_bp3d.py
python -I pipeline/classify.py
python -I pipeline/build_male.py
python -I pipeline/build_proc.py
python -I pipeline/fem_step1.py
python -I pipeline/fem_step2.py
python -I pipeline/fem_step3.py
python -I pipeline/fem_step4.py
python -I pipeline/fem_extra.py
python -I pipeline/fem_fix_sheets.py
python -I pipeline/assemble.py
python -I pipeline/export.py
npm run encode
npm run check:assets
npm run build
```

`assemble.py` applies `female_shape.py`: shared body geometry is preserved, sex-specific pelvic structures are re-anchored, and the breast envelope, skin sculpt, and internal components are adapted together. `export.py` computes normals/AO and raw buffers; `encode.mjs` produces the tracked binary assets. Keep the license and source attribution alongside regenerated chunks.

Intermediate output in `pipeline/raw/` and `body_data/cache/` is not tracked. The pipeline is an optional developer workflow, not a one-command downloader; acquisition and input preparation must be completed first.

## Validation

Validate the bundled model manifest and decode every binary chunk:

```bash
npm run check:assets
```

With the optional source cache present, check shared geometry, breast symmetry, closed envelopes, and skin sculpt invariants:

```bash
python tools/check-shape.py
```

An optional previous `all_pieces.pkl` can be passed to verify that male geometry is preserved. Do not add local baseline caches to Git.

## Browser verification and screenshots

Install Chrome or Chromium locally. Set `CHROME_PATH` if the browser is outside a standard installation path; no browser binary is bundled. The tools also accept a URL for an already-running development or preview server.

```bash
node tools/verify-shape.mjs http://127.0.0.1:5179/
node tools/shot.mjs http://127.0.0.1:5178/ tools/qa/overview.png
```

`verify-shape.mjs` checks decoded shared vertices, picking, sex-specific visibility, runtime errors, and multi-angle screenshots. `tools/qa/` is ignored; copy only curated images into `docs/assets/` when updating documentation. Screenshot scripts should be run against trusted local project pages.
