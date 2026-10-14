<div align="center">

<img src="docs/assets/logo.svg" width="88" height="88" alt="Human Atlas 3D logo" />

# Human Atlas 3D

**Explore anatomy in your browser, from the whole body to a single tendon.**

Male / female models · System layers · Regional close-ups · Chinese / English search

[![Build](https://github.com/wangzh12023/human-atlas-3d/actions/workflows/ci.yml/badge.svg)](https://github.com/wangzh12023/human-atlas-3d/actions/workflows/ci.yml)
[![Code: MIT](https://img.shields.io/badge/Code-MIT-334155?style=flat-square&logo=opensourceinitiative&logoColor=white)](LICENSE)
[![Anatomy: CC BY 4.0](https://img.shields.io/badge/Anatomy-CC_BY_4.0-8b5e66?style=flat-square&logo=creativecommons&logoColor=white)](public/ATTRIBUTION.md)
[![Three.js](https://img.shields.io/badge/Three.js-WebGL2-111827?style=flat-square&logo=threedotjs&logoColor=white)](https://threejs.org/)
[![Vite](https://img.shields.io/badge/Vite-6-646cff?style=flat-square&logo=vite&logoColor=white)](https://vite.dev/)
[![Stars](https://img.shields.io/github/stars/wangzh12023/human-atlas-3d?style=flat-square&logo=github)](https://github.com/wangzh12023/human-atlas-3d/stargazers)

[Quick start](#-quick-start) · [Features](#-features) · [Controls](#-controls) · [Licensing](#-data-and-licensing) · [Contributing](CONTRIBUTING.md)

[简体中文](README.md) | **English**

<img src="docs/assets/overview.png" width="100%" alt="Full-body anatomy viewer with system layers, structure hotspots, and an explode slider" />

<sub>2,298 modeled pieces · 15 system layers · 28 regional close-ups</sub>

</div>

## ✨ Features

A static, browser-based anatomy explorer built with Three.js and custom WebGL 2 shaders. Encoded models and learning content ship with the repository: no backend, API key, or separate model download is required to run the app.

| | Feature | Experience |
| :--: | :-- | :-- |
| 🧍 | **Male / female models** | Smooth morphing with sex-specific structures and a shared base build for consistent spatial context. |
| 🦴 | **System layers** | Toggle bones, muscles, ligaments, vessels, nerves, and organs; use anatomy, skeleton, or organ presets. |
| 🎯 | **Regional close-ups** | Shoulder, knee, ankle, foot, core, brain, heart/lungs, and reproductive anatomy with camera framing and highlights. |
| 🔎 | **Bilingual search** | Search Chinese or English structure and region names. Educational descriptions are primarily Chinese. |
| 🧩 | **Exploded anatomy** | Separate body systems, then lay individual structures out in a browsable inventory. |
| 🖱️ | **Structure inspection** | Hover, select, focus, isolate, and orbit around individual structures. |

<table>
  <tr>
    <td width="50%"><img src="docs/assets/breast-detail.png" alt="Breast close-up with transparent outer layers and internal mammary structures" /></td>
    <td width="50%"><img src="docs/assets/foot-detail.png" alt="Foot close-up with bones, tendons, and blood vessels" /></td>
  </tr>
  <tr>
    <td align="center"><b>Layer-aware close-ups</b></td>
    <td align="center"><b>Fine anatomical detail</b></td>
  </tr>
</table>

## 🚀 Quick start

Requirements: **Node.js 22.12+**, npm, and a browser supporting **WebGL 2**.

```bash
git clone https://github.com/wangzh12023/human-atlas-3d.git
cd human-atlas-3d
npm ci
npm run dev
```

Open **http://127.0.0.1:5178/**. The first load fetches approximately **15.3 MiB** of compressed model chunks included in the repository.

### 📦 Build and deploy

```bash
npm run check:assets
npm run build
npm run preview
```

Preview the production build at **http://127.0.0.1:5179/**. Deploy `dist/` to a static host. Relative resource paths support hosting under a repository subpath; see the [deployment guide](docs/DEPLOYMENT.md).

Serve the app over HTTP rather than opening `index.html` directly. Windows users may also launch [`启动.bat`](启动.bat).

## 🕹️ Controls

| Action | Control |
| :-- | :-- |
| Orbit / zoom | Left drag / scroll or pinch |
| Pan | Right drag or Shift + drag |
| Inspect / focus | Click / double-click |
| Search | `/` |
| Switch sex | `M` |
| Front / side / back | `F` / `S` / `B` |
| Reset camera | `R` |
| Previous / next region | `←` / `→` |
| Return | `Esc` |

## 🛠️ Development

The runtime uses JavaScript ES modules, Three.js, custom GLSL, meshoptimizer compression, GPU state textures, and GPU picking. The optional Python pipeline handles mesh processing, registration, schematic geometry, normals, and ambient occlusion.

| Path | Purpose |
| :-- | :-- |
| `src/engine/` | Model loading, shaders, camera, picking |
| `src/content/` | Structure and region descriptions |
| `public/data/` | Ready-to-use encoded model chunks and manifest |
| `pipeline/` | Optional asset generation pipeline |
| `tools/` | Asset validation, screenshots, geometry checks |
| `docs/` | Deployment, pipeline documentation, screenshots |

Python and the original source datasets are only required to **regenerate** models. See [pipeline documentation](docs/PIPELINE.md). Normal application development uses the bundled assets.

## 📚 Data and licensing

Application code, processing scripts, and original project text are licensed under [MIT](LICENSE). Adapted anatomical assets and screenshots containing them are licensed under [CC BY 4.0](public/data/LICENSE), with separate source attribution.

- **BodyParts3D / DBCLS:** base anatomical geometry. [Official database license](https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html).
- **Human Reference Atlas / HuBMAP:** female reference organs and registration references. [Reference library and license](https://humanatlas.io/3d-reference-library).
- **Inter:** SIL Open Font License 1.1, distributed through Fontsource.

See [`public/ATTRIBUTION.md`](public/ATTRIBUTION.md) for credit, adaptations, and versioned source links. This attribution file travels with the built site; preserve it when redistributing the models or deploying a derivative.

The female presentation uses the shared base build with localized breast and sex-specific anatomy. Some structures and external forms are schematic reconstructions, labeled `Schematic model` in the app, rather than unmodified individual reference anatomy.

> This project supports education and visualization. It is not intended for diagnosis, treatment, or clinical decision-making.

## 🤝 Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md), then [report an issue](https://github.com/wangzh12023/human-atlas-3d/issues) or submit a focused pull request. Anatomy/content corrections should include verifiable sources. Visual changes should include screenshots and the relevant interaction checks.

## 🙏 Acknowledgments

Thanks to DBCLS / BodyParts3D, Human Reference Atlas / HuBMAP, the NIH / National Library of Medicine Visible Human Project, and the original model creators; and to Three.js, meshoptimizer, Vite, Fontsource, and Inter.

<div align="center">

If the project helps you learn or build, consider a ⭐ and share your feedback.

</div>
