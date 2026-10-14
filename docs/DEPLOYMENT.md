# 📦 Deployment

Human Atlas 3D builds into a static site. There is no application server or API to configure.

## Build output

```bash
npm ci
npm run check:assets
npm run build
```

Publish the **entire `dist/` directory**, including `data/`, `ATTRIBUTION.md`, and `licenses/`. Model chunks and the manifest must be deployed together from the same build.

## Hosting configuration

| Host | Build command | Publish directory |
| :-- | :-- | :-- |
| Vercel / Netlify | `npm run build` | `dist` |
| GitHub Pages | Build locally or in Actions, then publish the resulting static files | Contents of `dist` |
| Nginx / other static server | `npm run build` | Point the document root at `dist` |

The Vite `base` is `./`, allowing repository subpaths such as `/human-atlas-3d/`. The app does not use client-side routing, so it does not require an SPA rewrite rule. Serve `.bin` model files as binary content and `.json` as JSON.

This repository's CI validates assets and produces downloadable build artifacts; it does not enable hosting automatically. For GitHub Pages, configure the repository's Pages source and publish the built output using your preferred Pages workflow.

## Local production verification

```bash
npm run preview
```

Visit http://127.0.0.1:5179/. Check model loading, sex switching, system toggles, search, region navigation, and the explode slider. Stop the preview with `Ctrl+C` after verification.

## Troubleshooting

- **Model loading fails:** inspect network requests for `data/manifest.json` and the `.bin` chunks; verify the complete output was uploaded.
- **Blank rendering:** use a WebGL 2 browser and check GPU/browser support and console errors.
- **Old assets after an update:** redeploy the manifest and all model chunks together, then refresh browser/CDN caches.
- **`file://` access:** run the development or preview server instead of opening the HTML directly.

Keep the anatomical data attribution accessible in deployed copies. See [data attribution](../public/ATTRIBUTION.md).
