# Avatar Onboarding Playbook

This playbook is the operational path to complete licensed local male/female avatars and local runtime hosting.

Current authoring tool: Blender 5.2. Use MakeHuman/MPFB in Blender 5.2 for the development male/female avatar exports unless the asset pipeline is intentionally changed and documented here.

## 1) Acquire licensed assets

For each profile (`male`, `female`), create or obtain one humanoid model in `glb`, `gltf`, or `vrm` format with explicit rights for:

- local application usage
- internal distribution within your installer footprint (if you ship the model)
- modification/conversion (if you retarget or optimize)

Before purchase or import, confirm the license grants all three rights above. If not explicit, treat as disallowed. For the current free path, keep MakeHuman/MPFB source files and license evidence alongside the export notes.

Blender 5.2 export checklist:

- Use adult, realistic proportions and a neutral rest pose.
- Include a humanoid rig and at least a basic neutral outfit.
- Include facial shape keys for blink and speech where available.
- Prefer ARKit or `visemes02` shape-key sets if file size and browser performance stay acceptable.
- Export GLB first for the current host path; VRM remains planned until the local VRM adapter is added.

## 2) Place models and manifests

Use this layout:

- `desktop/Jarvis.Desktop/Assets/Avatars/male/jarvis-male.glb` (or update `avatar.json` for a different filename/format)
- `desktop/Jarvis.Desktop/Assets/Avatars/male/avatar.json`
- `desktop/Jarvis.Desktop/Assets/Avatars/female/jarvis-female.glb` (or update `avatar.json` for a different filename/format)
- `desktop/Jarvis.Desktop/Assets/Avatars/female/avatar.json`

Set `redistributionAllowed` to `true` only when your license explicitly allows redistribution under your deployment model.

## 3) Install local runtime dependency (GLB)

Jarvis runtime is local-only and does not pull CDN scripts.

Add this file:

- `desktop/Jarvis.Desktop/Assets/AvatarHost/vendor/model-viewer.min.js`

Reference:
- `desktop/Jarvis.Desktop/Assets/AvatarHost/vendor/README.md`

## 4) Validate manifests and files

Run:

```powershell
./scripts/validate-avatar-assets.ps1
```

The script verifies both `male` and `female` profiles, `avatar.json` or legacy `manifest.json` required fields, supported formats, redistribution flag, and model file presence. With the current placeholders it is expected to fail until the Blender 5.2 exports are copied in and license fields are updated.

## 5) Enable in app

In Jarvis Settings:

- Enable local 3D avatar host
- Select `male` or `female` profile

Then click the `Avatar host` button in the command center.

## 6) VRM completion path

Current state:

- GLB/GLTF local preview is supported after local runtime file placement.
- VRM requires a local runtime module (not bundled yet).
- Avatar state and speech messages are already routed through the C# avatar service and WebView2 message protocol.
- Kokoro voice client scaffolding exists, but the local runtime/sidecar still needs to be installed or packaged.

Recommended completion:

1. Add local Three.js + VRM runtime files under `desktop/Jarvis.Desktop/Assets/AvatarHost/vendor/`.
2. Add a `vrm-runtime.js` adapter in that same folder.
3. Wire `avatar-host.js` VRM branch to call the adapter and set avatar states.

If you want this automated in-repo, the next implementation step is to add a dedicated VRM renderer adapter and a setup script to materialize pinned local runtime files.
