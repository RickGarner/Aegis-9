# Jarvis Free Local Avatar and Voice Implementation Handoff

## 2026-08-25 implementation status

Jarvis now has the first architecture slice of this specification implemented in the WPF desktop app and bundled FastAPI backend:

- WebView2 avatar host window with local virtual-host mappings for runtime and avatar assets.
- Versioned C# to JavaScript avatar message protocol for load, state, expression, speech start, and speech stop.
- JavaScript to C# ready/error messages with native fallback when the runtime or assets are unavailable.
- Avatar metadata contract using `avatar.json`, with legacy `manifest.json` fallback.
- Male/female placeholder avatar metadata under `desktop/Jarvis.Desktop/Assets/Avatars/`.
- Centralized `AvatarService` and persisted avatar/voice/lip-sync settings.
- Kokoro local speech client scaffolding with graceful failure when the runtime is not running.
- Asset validation script for metadata, licensing flags, supported formats, and model file presence.
- Pinned local `model-viewer.min.js` 4.0.0 runtime for GLB preview, with no runtime CDN dependency.

Current avatar authoring note: the development avatars are being created in Blender 5.2 from ActorCore FBX downloads. The expected first exports are `jarvis-male.glb` and `jarvis-female.glb` unless the matching `avatar.json` files are updated. The male export has been inspected and contains 121 facial morph targets, including ARKit-style controls; the current female download is an incomplete 132-byte empty-scene GLB and must be replaced.

Known remaining blockers: real male/female GLB or VRM files are not yet present, placeholder metadata still sets `redistributionAllowed` to `false`, `model-viewer.min.js` is not yet vendored locally, the Kokoro runtime/sidecar is not yet packaged, and full VRM/viseme lip-sync still needs the renderer adapter.

## Instructions for GitHub Copilot in Visual Studio 2022

You are taking over implementation of a free, local, offline-capable male/female avatar and voice system for the Jarvis WPF desktop application. Treat this document as the implementation specification. Inspect the existing solution before changing code, preserve working behavior, and adapt names and namespaces to the actual project.

Do not replace the existing avatar system wholesale. Extend it incrementally and keep the current native WPF fallback operational throughout the work.

---

## 1. Project context

Jarvis currently uses a hybrid avatar architecture:

- A native fallback avatar rendered directly in WPF using XAML shapes and animation in `MainWindow.xaml`.
- A 3D avatar window hosted by WebView2 in `AvatarWindow.xaml` and `AvatarWindow.xaml.cs`.
- A local HTML/CSS/JavaScript runtime in `index.html`, `avatar-host.css`, and `avatar-host.js`.
- GLB/glTF rendering through a locally bundled `model-viewer` script under `vendor`.
- VRM support is planned but is not fully implemented. Existing intentions may be documented in `avatar-onboarding-playbook.md`.

The first implementation must support two realistic game-style development characters:

- One adult male avatar.
- One adult female avatar.
- One distinct offline male voice.
- One distinct offline female voice.

No paid assets or cloud services may be required. All runtime components must work locally after installation. The development avatars do not need to be redistributed at this stage.

---

## 2. Approved free technology choices

### 2.1 Avatar creation

Use MakeHuman Community assets through MPFB (MakeHuman Plugin for Blender) to create the development avatars.

Required properties:

- Adult, realistic human proportions.
- Game-appropriate topology and texture resolution.
- Humanoid skeletal rig.
- Neutral rest pose.
- Facial shape keys for expressions and speech.
- Blink controls.
- Eye-look capability, preferably through eye bones.
- At least one complete neutral outfit per avatar.
- Exportable to GLB/glTF with textures packed or copied locally.

Only use MakeHuman core assets or other assets whose license has been individually verified. Do not assume that every community-contributed hair, clothing, texture, or accessory has the same license as MakeHuman core assets.

MakeHuman states that its core graphical assets and derivatives are CC0. Preserve a local copy of the applicable license page or license text in the repository's third-party notices area.

Official license reference:

`https://static.makehumancommunity.org/about/license.html`

### 2.2 Facial animation

Use MPFB facial shape-key support when preparing each avatar.

Preferred shape-key sets:

1. ARKit face units, when export size and browser performance remain acceptable.
2. `visemes02` for speech mouth positions.
3. Blink and basic emotion/expression keys.

MPFB documentation indicates that an export copy can include visemes and ARKit face units before export:

`https://static.makehumancommunity.org/mpfb/docs/exporting/export_copy.html`

MPFB lip-sync reference:

`https://static.makehumancommunity.org/mpfb/docs/lipsync/index.html`

### 2.3 Offline text-to-speech

Use Kokoro-82M for the initial offline voice runtime.

Initial voice assignments:

- Female: `af_heart`
- Male: `am_fenrir`

Keep the voice IDs configurable. Do not hard-code them throughout the application.

Kokoro model reference:

`https://huggingface.co/hexgrad/Kokoro-82M`

Kokoro voice reference:

`https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md`

Kokoro's published model license is Apache License 2.0. Include the required Apache license and notices with the local runtime. Confirm the licenses of all transitive packages selected for the Windows implementation.

---

## 3. Non-negotiable requirements

1. Jarvis must continue to start if the 3D avatar or TTS runtime is unavailable.
2. The native WPF avatar remains the final fallback.
3. No runtime CDN, hosted JavaScript, cloud TTS, analytics, or external API is permitted.
4. WebView2 must load all avatar/runtime files locally.
5. Avatar and voice selection must persist between application launches.
6. The user must be able to choose male or female independently of other Jarvis settings.
7. TTS failures must not freeze the WPF UI thread.
8. Switching avatars must dispose or unload the previous 3D model and associated audio resources.
9. Speech requests must be cancellable. New speech may cancel or queue behind existing speech according to one centralized policy.
10. Paths must be resolved relative to the installed application or an approved application-data directory, never a developer-specific absolute path.
11. Preserve the existing solution's dependency-injection, logging, configuration, and MVVM patterns where present.
12. Do not introduce Python as an invisible undeclared prerequisite. If Python is used for the first development implementation, provide an explicit setup check, configurable executable path, health check, and graceful fallback. Prefer a self-contained Windows sidecar or ONNX-based runtime for packaging when practical.

---

## 4. Inspect before editing

Before making changes, inspect and summarize:

- The solution and project files.
- Target .NET and Windows versions.
- Current MVVM or code-behind architecture.
- Dependency-injection container, if any.
- Existing configuration mechanism.
- Existing logging mechanism.
- Current WebView2 initialization and navigation flow.
- Current C# to JavaScript and JavaScript to C# message handling.
- Current avatar state and animation commands.
- Current audio playback and speech services.
- Existing tests.
- `avatar-onboarding-playbook.md` and any referenced design documents.

Then produce a short implementation plan naming the exact files to add or modify. Do not edit files until this inspection is complete.

---

## 5. Proposed repository layout

Adapt this layout to existing project conventions:

```text
Jarvis/
  Assets/
    Avatars/
      male/
        jarvis-male.glb
        avatar.json
      female/
        jarvis-female.glb
        avatar.json
    AvatarRuntime/
      index.html
      avatar-host.css
      avatar-host.js
      vendor/
    Voices/
      kokoro/
        models/
        voices/
        licenses/
  Configuration/
    avatar-settings.json
  Services/
    Avatars/
      IAvatarService.cs
      AvatarService.cs
      AvatarDefinition.cs
      AvatarRuntimeState.cs
    Speech/
      ISpeechService.cs
      KokoroSpeechService.cs
      SpeechRequest.cs
      SpeechResult.cs
      SpeechPlaybackService.cs
  ThirdPartyNotices/
    MakeHuman-CC0.txt
    Kokoro-Apache-2.0.txt
    THIRD-PARTY-NOTICES.md
```

Do not commit large binary model files until the repository's binary-asset policy is known. Check whether Git LFS is already configured. If not, propose it before committing avatar or voice weights.

---

## 6. Avatar metadata contract

Each avatar directory should contain an `avatar.json` manifest. Start with this schema and adjust only when needed:

```json
{
  "id": "jarvis-male-dev",
  "displayName": "Male Development Avatar",
  "version": 1,
  "format": "glb",
  "model": "jarvis-male.glb",
  "voiceId": "am_fenrir",
  "scale": 1.0,
  "cameraTarget": [0.0, 1.55, 0.0],
  "cameraOrbit": "0deg 82deg 1.6m",
  "animationNames": {
    "idle": "Idle",
    "greeting": "Greeting",
    "thinking": "Thinking",
    "speaking": "Speaking"
  },
  "morphTargets": {
    "blinkLeft": "eyeBlinkLeft",
    "blinkRight": "eyeBlinkRight",
    "jawOpen": "jawOpen",
    "mouthSmileLeft": "mouthSmileLeft",
    "mouthSmileRight": "mouthSmileRight"
  },
  "visemeMap": {
    "sil": "viseme_sil",
    "PP": "viseme_PP",
    "FF": "viseme_FF",
    "TH": "viseme_TH",
    "DD": "viseme_DD",
    "kk": "viseme_kk",
    "CH": "viseme_CH",
    "SS": "viseme_SS",
    "nn": "viseme_nn",
    "RR": "viseme_RR",
    "aa": "viseme_aa",
    "E": "viseme_E",
    "I": "viseme_I",
    "O": "viseme_O",
    "U": "viseme_U"
  }
}
```

The exported MakeHuman shape-key names may differ. Inspect the actual GLB and update the manifest instead of renaming keys blindly in runtime code.

---

## 7. C# avatar service contract

Create or adapt a single application-level avatar service. The UI and other services must not construct WebView messages independently.

Suggested interface:

```csharp
public interface IAvatarService
{
    AvatarDefinition? ActiveAvatar { get; }
    IReadOnlyList<AvatarDefinition> AvailableAvatars { get; }

    Task InitializeAsync(CancellationToken cancellationToken = default);
    Task SelectAvatarAsync(string avatarId, CancellationToken cancellationToken = default);
    Task SetStateAsync(AvatarVisualState state, CancellationToken cancellationToken = default);
    Task SetExpressionAsync(string expression, double intensity = 1.0,
        CancellationToken cancellationToken = default);
    Task SpeakAsync(SpeechPlaybackData speech,
        CancellationToken cancellationToken = default);
    Task StopSpeakingAsync(CancellationToken cancellationToken = default);
}
```

Use an enum for stable high-level visual states such as:

- `Loading`
- `Idle`
- `Listening`
- `Thinking`
- `Speaking`
- `Error`
- `Offline`

Map these states to actual animations in one place.

---

## 8. WebView2 message protocol

Use versioned JSON messages. Avoid scattered string commands.

### C# to JavaScript examples

```json
{
  "version": 1,
  "type": "avatar.load",
  "requestId": "guid",
  "payload": {
    "manifestUrl": "local-relative-or-virtual-host-url"
  }
}
```

```json
{
  "version": 1,
  "type": "avatar.state",
  "requestId": "guid",
  "payload": {
    "state": "speaking"
  }
}
```

```json
{
  "version": 1,
  "type": "avatar.speech.start",
  "requestId": "guid",
  "payload": {
    "audioUrl": "local-runtime-url",
    "durationMs": 2150,
    "cues": [
      { "timeMs": 0, "viseme": "sil", "weight": 0.0 },
      { "timeMs": 90, "viseme": "PP", "weight": 1.0 }
    ]
  }
}
```

### JavaScript to C# examples

```json
{
  "version": 1,
  "type": "avatar.ready",
  "requestId": "guid",
  "payload": {
    "avatarId": "jarvis-male-dev",
    "animations": ["Idle", "Speaking"],
    "morphTargets": ["eyeBlinkLeft", "eyeBlinkRight", "jawOpen"]
  }
}
```

```json
{
  "version": 1,
  "type": "avatar.error",
  "requestId": "guid",
  "payload": {
    "code": "MODEL_LOAD_FAILED",
    "message": "Human-readable diagnostic"
  }
}
```

Validate messages on both sides. Log malformed or unknown messages without crashing.

---

## 9. Local WebView2 hosting

Prefer `SetVirtualHostNameToFolderMapping` for local runtime files. This avoids fragile `file://` behavior and gives model, texture, JavaScript, and audio resources a consistent secure origin.

Requirements:

- Map a synthetic local host such as `https://jarvis.local/` to the approved avatar runtime directory.
- Deny or intercept unexpected external navigation.
- Do not allow arbitrary web content to invoke privileged host messages.
- Keep WebView2 developer tools configurable and disabled in production builds.
- Dispose event handlers and WebView resources correctly when the window closes.
- Verify model and audio paths before exposing them to the browser layer.

If the existing project already uses a safe virtual-host mapping, retain it.

---

## 10. JavaScript runtime responsibilities

Refactor or extend `avatar-host.js` so it owns:

- Loading and unloading the selected GLB.
- Inspecting available animations and morph targets.
- Idle animation playback.
- Natural randomized blinking.
- Optional subtle head and eye movement.
- High-level state transitions.
- Speech animation and viseme application.
- Resetting morph-target weights after speech or cancellation.
- Reporting readiness and diagnostics to C#.
- Releasing audio objects, timers, animation frames, and model references.

Do not assume `model-viewer` alone exposes every morph-target operation needed. If direct morph control is unavailable through the current wrapper, add a small locally bundled Three.js-based adapter or another local adapter after documenting the reason. Do not load it from a CDN.

### Development lip-sync fallback

Kokoro may not provide phoneme timestamps directly. Implement lip sync in stages:

1. First working version: audio-amplitude-driven jaw movement plus randomized compatible mouth shapes.
2. Improved local version: generate phoneme/viseme cues from the input text using a local phonemizer and approximate timing across the synthesized audio duration.
3. Future version: use an offline aligner if exact timing becomes necessary.

The fallback must never block speech playback.

---

## 11. Kokoro speech service

Implement Kokoro behind `ISpeechService`, keeping the rest of Jarvis independent of the engine.

Suggested interface:

```csharp
public interface ISpeechService
{
    bool IsAvailable { get; }
    Task<SpeechResult> SynthesizeAsync(
        SpeechRequest request,
        CancellationToken cancellationToken = default);
}
```

Suggested request fields:

- Text
- Voice ID
- Speed
- Output format
- Correlation/request ID

Suggested result fields:

- Local audio file or byte buffer
- Sample rate
- Duration
- Optional phoneme/viseme cue collection
- Diagnostics

### Runtime approach

Choose the least disruptive approach compatible with the existing solution:

1. Prefer a maintained local ONNX or self-contained Windows Kokoro runtime that can be packaged explicitly.
2. For development only, a controlled Python sidecar is acceptable if the machine already supports it or setup is documented.
3. Never install packages automatically without user confirmation.
4. Never download models silently at runtime. Provide an explicit setup/acquisition command and verify hashes where published.

If using a sidecar:

- Bind only to loopback if HTTP is used.
- Select an available port safely or communicate through standard input/output or named pipes.
- Start it without a visible console window when appropriate.
- Capture standard output and standard error asynchronously.
- Add a startup timeout and health check.
- Stop the child process during application shutdown if Jarvis owns it.
- Do not kill unrelated Python processes.
- Sanitize text and arguments; do not construct shell command strings from user input.

### Audio lifecycle

- Generate temporary audio under a Jarvis-specific application-data cache.
- Use unique filenames.
- Delete expired files only from that explicit cache directory.
- Do not recursively delete broad or unresolved paths.
- Bound the cache by age and/or total size.
- Ensure files are not deleted while WebView2 or the audio player is using them.

---

## 12. Configuration

Add configuration resembling:

```json
{
  "avatar": {
    "enabled": true,
    "selectedAvatarId": "jarvis-male-dev",
    "useNativeFallback": true,
    "enableLipSync": true,
    "enableBlinking": true
  },
  "speech": {
    "provider": "kokoro-local",
    "maleVoiceId": "am_fenrir",
    "femaleVoiceId": "af_heart",
    "speed": 1.0,
    "startupTimeoutSeconds": 30,
    "requestTimeoutSeconds": 120
  }
}
```

Do not store machine-specific absolute paths unless the user deliberately configures an override. Validate all settings and fall back to safe defaults.

---

## 13. User interface behavior

Add or connect settings that allow the user to:

- Enable or disable the 3D avatar.
- Select the male development avatar.
- Select the female development avatar.
- Preview the corresponding voice.
- Enable or disable lip sync.
- Return to the native WPF avatar.
- See a concise diagnostic if required local components are missing.

Changing avatars should:

1. Stop current speech safely.
2. Persist the new selection.
3. Load the new avatar.
4. Select its configured default voice.
5. Restore the prior high-level state, normally `Idle`.

Do not make gender assumptions elsewhere in the application. Avatar and voice IDs are configuration data.

---

## 14. Asset preparation procedure

Do not attempt to automate artistic decisions inside application startup. Prepare assets as a separate development/build activity.

For each avatar:

1. Install Blender and a compatible MPFB release from official sources.
2. Create a new MakeHuman/MPFB adult character using core assets.
3. Create a distinct male or female appearance with realistic game-character proportions.
4. Apply one neutral, professional, non-branded outfit.
5. Use a humanoid rig appropriate for animation.
6. Create an MPFB export copy.
7. Add the required facial shape keys: ARKit units where practical, `visemes02`, blinking, and basic expressions.
8. Inspect eye bones, jaw behavior, teeth, tongue, hair, and clothing deformation.
9. Reduce unnecessary materials and texture resolution for a desktop assistant viewport.
10. Export GLB with skinning, animations, shape keys/morph targets, and local textures.
11. Inspect the GLB in an offline viewer and in Jarvis's actual WebView2 runtime.
12. Record the exact morph-target and animation names in `avatar.json`.
13. Test at least idle, blink, jaw-open, smile, and several visemes.
14. Keep the editable Blender source outside the runtime folder and manage it according to repository size policy.

Suggested initial performance targets per avatar:

- GLB download/load size: preferably under 40 MB for development; optimize toward under 20 MB later.
- Texture size: 2K or smaller unless close-up quality clearly requires more.
- Materials: minimize draw calls.
- First local load: under 5 seconds on the development workstation.
- Sustained rendering: 30 FPS minimum in the configured avatar window.

These are targets, not reasons to remove required facial functionality.

---

## 15. Error handling and fallback matrix

| Failure | Required behavior |
|---|---|
| WebView2 unavailable | Show native WPF avatar; log actionable diagnostic. |
| HTML/JS runtime fails | Show native WPF avatar; keep Jarvis usable. |
| GLB missing or invalid | Attempt no arbitrary substitute; show native fallback. |
| Selected avatar manifest invalid | Log validation errors and use default valid avatar or WPF fallback. |
| Kokoro unavailable | Continue without speech or use an already-approved local fallback; do not use cloud TTS silently. |
| Speech synthesis times out | Cancel request, restore idle state, and keep UI responsive. |
| Audio playback fails | Reset mouth shapes and speaking state, then log the error. |
| Avatar switched during speech | Cancel playback and synthesis, clear facial state, then load selection. |
| Application shutdown during synthesis | Cancel gracefully and terminate only the owned sidecar process. |

---

## 16. Testing requirements

Add unit tests where the existing solution supports them and provide a manual validation checklist.

### Automated tests

- Avatar manifest parsing and validation.
- Configuration defaulting and persistence.
- Voice selection for male and female avatars.
- Message serialization/deserialization.
- Unknown protocol message handling.
- Cancellation of speech requests.
- Cache-path validation and cleanup boundaries.
- Fallback selection when runtime files are missing.

Abstract WebView2 and speech-process boundaries where necessary so orchestration can be tested without launching the full UI.

### Manual tests

1. Launch with the male avatar and verify idle animation.
2. Speak a short sentence and verify male voice plus mouth movement.
3. Switch to the female avatar and verify female voice.
4. Speak multiple sentences and check cancellation/queue behavior.
5. Trigger listening and thinking states.
6. Resize, minimize, restore, and reopen the avatar window.
7. Disconnect networking and confirm everything still works.
8. Rename or temporarily remove the avatar model and verify WPF fallback.
9. Stop or remove the TTS runtime and verify the UI remains responsive.
10. Restart Jarvis and verify the selected avatar persists.
11. Run for at least 30 minutes and check CPU, GPU, memory, handles, and temporary files for growth.
12. Close Jarvis during speech and verify clean shutdown.

---

## 17. Security and privacy

- Keep all speech text and generated audio local.
- Do not add telemetry.
- Do not send models, prompts, speech text, or audio to external services.
- Restrict WebView2 navigation and local host-object exposure.
- Treat messages from JavaScript as untrusted input and validate them.
- Do not expose arbitrary filesystem paths to the browser runtime.
- Validate model and voice files against expected locations and, when available, published hashes.
- Document every third-party executable, library, model, and asset.

---

## 18. Licensing records

Create `ThirdPartyNotices/THIRD-PARTY-NOTICES.md` containing, at minimum:

- Component or asset name.
- Upstream project/author.
- Exact source URL.
- Version or retrieval date.
- License name.
- Local files covered.
- Whether attribution or notice inclusion is required.
- Any usage restrictions relevant to Jarvis.

Do not describe community assets as CC0 without checking the individual asset record. Prefer core MakeHuman assets for this development phase.

---

## 19. Implementation phases

Complete work in reviewable phases. Build and test after each phase.

### Phase 1: Audit and contracts

- Inspect current implementation.
- Document exact files to change.
- Introduce models/interfaces and the versioned message contract.
- Add configuration without changing existing runtime behavior.

### Phase 2: Avatar runtime hardening

- Implement local virtual-host mapping if not already present.
- Add manifest loading, readiness reporting, state control, and fallback.
- Prove the existing GLB path still works.

### Phase 3: Development avatars

- Add male and female manifests.
- Integrate prepared MakeHuman GLBs.
- Add idle, blink, expression, and avatar-switch behavior.

If the GLB files have not yet been created, implement against clearly named placeholders and produce the exact Blender/MPFB export checklist. Do not fabricate binary assets.

### Phase 4: Kokoro TTS

- Add `ISpeechService` and local implementation.
- Implement health checks, cancellation, caching, playback, and fallback.
- Connect configurable male/female voices.

### Phase 5: Lip sync

- Add amplitude-driven development lip sync.
- Add local viseme approximation when feasible.
- Reset all morphs correctly after completion and cancellation.

### Phase 6: Settings, tests, and documentation

- Add UI selection and preview controls.
- Add automated tests.
- Run manual validation.
- Complete setup, troubleshooting, and licensing documentation.

---

## 20. Definition of done

The development implementation is complete only when:

- Jarvis launches normally with no network connection.
- Male and female 3D avatars can be selected and persist across restarts.
- Each avatar uses its configured Kokoro voice.
- Speech is audible and produces synchronized development-quality mouth movement.
- Blinking and idle behavior work without obvious timer/resource leaks.
- Avatar switching is safe during idle and speech.
- Missing models, WebView2 failures, and TTS failures fall back cleanly.
- No cloud resource is loaded at runtime.
- The solution builds cleanly in Visual Studio 2022.
- Relevant tests pass.
- Setup, asset preparation, troubleshooting, and third-party licenses are documented.

---

## 21. Required Copilot handoff response

When you receive this specification, respond first with:

1. A summary of the existing avatar and speech architecture found in the repository.
2. Conflicts between this specification and current code.
3. The exact implementation phases you will follow.
4. The exact files you intend to add or modify in Phase 1.
5. Any prerequisites that genuinely block implementation.

Then wait for approval before making broad architectural changes. Small additive Phase 1 changes may proceed only if the user explicitly asks you to begin implementation.

