# Wolforge Jarvis Avatar

An original, offline-ready cyber-wolf avatar based on the supplied Wolforge icon. The package contains an animated glTF/GLB model, named Jarvis state animations, a WebView2/model-viewer controller, and a small C# bridge.

## Contents

- `model/wolforge_jarvis_avatar.glb` — runtime model.
- `model/build_wolforge_glb.py` — reproducible source generator requiring only Python 3.
- `model/animation-manifest.json` — stable state-to-clip mapping.
- `runtime/avatar.html` — transparent WebView2 host page.
- `runtime/wolforge-avatar-controller.js` — JavaScript control API.
- `runtime/WolforgeAvatarBridge.cs` — C# calls for Jarvis states.
- `reference/wolforge-production-turnaround.png` — approved modeling reference.
- `docs/INTEGRATION.md` — installation and validation instructions.

## Model controls

The GLB contains nine named clips: `Idle`, `Blink`, `JawOpen`, `Speaking`, `Listening`, `Thinking`, `Success`, `Warning`, and `Error`.

The jaw, ears, eyes, head, neck, muzzle, armor plates, cyan circuits, and shoulders are individually named nodes. This permits a later Three.js renderer to add audio-envelope jaw control or per-viseme control without replacing the asset.

## Rebuild

Run:

```powershell
py .\model\build_wolforge_glb.py
```

The generated GLB is deterministic and has no external textures or network dependencies.
