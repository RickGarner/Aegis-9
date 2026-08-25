# Jarvis Avatar Host Vendor Runtime

This folder stores local runtime dependencies used by the WebView2 avatar host.

## Required for GLB/GLTF preview

- model-viewer.min.js

Place it at:
- vendor/model-viewer.min.js

## Optional for VRM preview

A VRM runtime module is not bundled by default. Add your local VRM runtime implementation at:
- vendor/vrm-runtime.js

The host will stay on native avatar fallback until this runtime is present.

## Why local-only

Jarvis should run without internet dependency at runtime. Vendor files are loaded from disk through WebView2.
