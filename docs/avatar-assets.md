# Jarvis Avatar Assets

## Current implementation status

The native fallback avatar remains in the WPF command center, and Jarvis now includes a local 3D avatar host window backed by manifest-driven asset loading.

Implemented in this repository:

- 3D host window: `desktop/Jarvis.Desktop/AvatarWindow.xaml`
- Avatar contract, manifest, and loader: `desktop/Jarvis.Desktop/AvatarDefinition.cs`, `desktop/Jarvis.Desktop/AvatarManifest.cs`, `desktop/Jarvis.Desktop/AvatarAssetCatalog.cs`
- Avatar orchestration: `desktop/Jarvis.Desktop/IAvatarService.cs`, `desktop/Jarvis.Desktop/AvatarService.cs`, `desktop/Jarvis.Desktop/AvatarProtocol.cs`, `desktop/Jarvis.Desktop/AvatarVisualState.cs`
- Speech scaffolding: `desktop/Jarvis.Desktop/ISpeechService.cs`, `desktop/Jarvis.Desktop/KokoroSpeechService.cs`, `desktop/Jarvis.Desktop/SpeechRequest.cs`, `desktop/Jarvis.Desktop/SpeechResult.cs`
- Local web host assets: `desktop/Jarvis.Desktop/Assets/AvatarHost/`
- Vendored GLB renderer: `desktop/Jarvis.Desktop/Assets/AvatarHost/vendor/model-viewer.min.js` version 4.0.0
- Profile metadata: `desktop/Jarvis.Desktop/Assets/Avatars/male/avatar.json`, `desktop/Jarvis.Desktop/Assets/Avatars/female/avatar.json`, with legacy `manifest.json` fallback
- Operator controls: settings for selected avatar/profile, voice IDs, lip-sync, and host toggle, plus Ctrl+click open from the avatar panel

If model files are missing or not licensed for redistribution, Jarvis automatically falls back to the native WPF avatar.

## Direction

Jarvis will use licensed local 3D male and female humanoid avatars. The current development avatars are being authored in Blender 5.2 using MakeHuman/MPFB as the intended free local creation path. The application must not redistribute the reference image used during design discussion or depend on a remote avatar/image service at runtime.

## Planned local layout

```text
desktop/Jarvis.Desktop/Assets/Avatars/
    male/
        jarvis-male.glb or jarvis-male.vrm
        avatar.json
    female/
        jarvis-female.glb or jarvis-female.vrm
        avatar.json
```

## Manifest requirements

Each avatar manifest should record:

- display name and presentation profile
- model filename and format
- asset creator and source
- license name and license URL
- redistribution rights and restrictions
- available idle, listening, thinking, speaking, and reaction animations
- available facial expressions and visemes
- attribution text required by the license

Do not add model files until the license explicitly permits local application use and redistribution in the intended Jarvis package. Keep the license text and attribution beside the asset.

## Runtime plan

- Prefer VRM when humanoid bones, expressions, eye movement, and visemes are available.
- Support GLB as the general local model format.
- Host the renderer locally using a WPF-compatible WebView2 host.
- Keep the current native WPF avatar as a fallback when a model is missing or fails to load.
- Voice input, text generation, and text-to-speech will drive a shared avatar state model rather than directly controlling renderer details.

Current host notes:

- GLB/GLTF preview is supported after `desktop/Jarvis.Desktop/Assets/AvatarHost/vendor/model-viewer.min.js` is provided locally.
- VRM files are detected but currently require a dedicated runtime extension; the host shows a fallback message until that adapter is added.
- The host only loads profiles whose `avatar.json` or fallback manifest explicitly sets `redistributionAllowed: true`.
- Development assets may use `localUseAllowed: true` while `redistributionAllowed` remains false; this keeps account-restricted ActorCore content local and prevents accidental packaging.
- C# sends versioned JSON messages to the runtime for avatar load, state, expression, speech start, and speech stop; JavaScript reports ready/error states back to WebView2.
- Kokoro speech output is scaffolded through a local HTTP endpoint and remains graceful when the service is unavailable.

## Required states

- idle
- attentive
- listening
- thinking
- speaking
- happy
- concerned
- unavailable

The native WPF avatar currently covers idle/attentive/listening/thinking/response transitions. The 3D host now accepts speaking state and speech playback messages; full viseme-driven lip-sync mapping remains the next pass after real Blender 5.2 avatar exports are available.

## Security and privacy

Avatar files are local application assets. User-selected avatar, name, voice, and appearance preferences belong in the local user profile and must not be sent to the assistant provider unless explicitly needed for a request.

## Operator onboarding

Use the implementation checklist in:

- `docs/avatar-onboarding-playbook.md`
