# Anatomical data attribution

Human Atlas 3D uses adapted open anatomical data. The application's MIT license does not replace the licenses of the anatomical datasets or fonts.

## BodyParts3D

BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International.

- Database: https://dbarchive.biosciencedbc.jp/en/bodyparts3d/
- Official license: https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html
- Downloads: https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html
- Source used: BodyParts3D 4.0, IS-A polygon mesh dataset `isa_BP3D_4.0_obj_99.zip` and associated structure metadata.

The official database license page specifies CC BY 4.0. The downloaded 4.0 OBJ archive contains historical CC BY-SA 2.1 Japan comments; this distribution uses the current license stated by the database's official licensor, linked above. The geometry supplies the base body, skeleton, muscles, vessels, nerves, and organs. Meshes have been cleaned, welded, deduplicated, simplified, classified, transformed, quantized, and meshoptimizer-compressed. Names have been mapped into display labels and Chinese translations; source structure identifiers are retained in `data/manifest.json`.

## Human Reference Atlas / HuBMAP

Female reference organ geometry and registration references are credited to the Human Reference Atlas / HuBMAP, the Cyberinfrastructure for Network Science Center at Indiana University, Kristen Browne, Heidi Schlehlein, and the creators and contributors associated with each versioned reference object. Visible Human reference data originates from the NIH / National Library of Medicine Visible Human Project.

- Reference library, credits, citations, and CC BY 4.0 license: https://humanatlas.io/3d-reference-library
- Versioned objects used as inputs: [`data/sources.json`](data/sources.json).

The source list distinguishes the registration references from the female-specific organs incorporated into the final presentation. Original GLB meshes and local intermediate caches are not distributed in this repository. To cite a particular source dataset, follow its versioned reference-object link and retain that dataset's own creator and citation metadata.

Adaptations include coordinate conversion, registration to the base body, simplification, interpolation, mirroring and repositioning of breast components, local skin morphing, and re-anchoring sex-specific structures to a shared build. The displayed female body is a presentation adaptation rather than an unmodified HRA reference individual.

## Schematic geometry and screenshots

Some missing ligaments, muscle sheets, genital structures, and breast envelopes are project-generated schematic reconstructions. The manifest and structure inspector label these as `proc` / `Schematic model`.

The compiled mixed anatomical assets in `data/` and screenshots showing these assets in `docs/assets/*.png` are distributed by this project under CC BY 4.0. Project-specific adaptations and screenshot composition: © 2026 Zihan Wang. Retain the original dataset credits above when redistributing these assets or images. This project does not imply endorsement by the dataset creators.

License: https://creativecommons.org/licenses/by/4.0/
Legal code: https://creativecommons.org/licenses/by/4.0/legalcode

## Fonts and software dependencies

Inter font files, distributed through `@fontsource-variable/inter`, use the SIL Open Font License 1.1. The font license is included at [`licenses/Inter-OFL.txt`](licenses/Inter-OFL.txt), which is copied into production builds.

Three.js, Vite, meshoptimizer, Fontsource tooling, and development dependencies retain their respective upstream software licenses, available in the installed packages and package metadata. No upstream anatomical organization is an author or endorser of this application.

## Redistribution

Preserve this attribution, the source links, and the anatomical data license when copying the model data, reproducing screenshots, or deploying an adapted site. Code and original project learning text are separately covered by the repository's MIT license.
