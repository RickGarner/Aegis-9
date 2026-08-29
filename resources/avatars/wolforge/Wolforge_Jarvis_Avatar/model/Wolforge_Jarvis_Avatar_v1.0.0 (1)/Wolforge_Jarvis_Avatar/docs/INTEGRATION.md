# Jarvis Integration

## 1. Copy the avatar

Copy this package beneath Jarvis's existing local WebView2 avatar asset directory. Copy Jarvis's already-bundled `model-viewer.min.js` into `runtime/vendor/`; do not add a CDN reference.

## 2. Load the page

Navigate the avatar WebView2 instance to `runtime/avatar.html`. Keep the existing WPF avatar visible until WebView2 raises `NavigationCompleted` successfully. On failure, retain the WPF fallback.

## 3. Connect Jarvis states

Instantiate `WolforgeAvatarBridge` after WebView2 initialization and map application states:

| Jarvis state | Method |
|---|---|
| Ready/idle | `IdleAsync()` |
| Listening | `ListeningAsync()` |
| Generating response | `ThinkingAsync()` |
| Kokoro playback begins | `SpeakingAsync()` |
| Playback ends/cancels/fails | `StopSpeakingAsync()` |
| Completed | `SuccessAsync()` |
| Warning | `WarningAsync()` |
| Error | `ErrorAsync()` |

Always call `StopSpeakingAsync()` in a `finally` block so the mouth resets after cancellation or audio failure.

## 4. Speech behavior

Version 1 uses the `Speaking` jaw-performance clip and is immediately compatible with model-viewer. It provides convincing visible speech at avatar-window size. For exact phoneme synchronization, retain this GLB and move the local page to the already-planned Three.js controller: locate the named `Jaw` node, apply the Kokoro/audio envelope as an X rotation, and interpolate between 0 and -0.42 radians. The node metadata already declares the intended wolf viseme set.

## 5. Avatar switching

Use the existing safe order:

1. Cancel speech and audio playback.
2. Call `StopSpeakingAsync()`.
3. Dispose references to the previous controller/model.
4. Navigate to the selected avatar page.
5. Wait for load completion.
6. Restore `Idle`.
7. Persist `wolforge-jarvis` as the selected avatar ID.

## 6. Acceptance checks

- Model loads without network access.
- Cyan eyes and circuit marks emit light.
- `Idle` loops smoothly.
- `Blink` closes both eye lenses and returns to idle.
- `Listening` raises ears and focuses the head.
- `Thinking` performs a slow head scan.
- `Speaking` moves the jaw continuously.
- Cancelled speech returns the jaw to rest.
- Warning, error, and success clips return to idle.
- WebView2 failure leaves the native WPF fallback usable.

## Licensing

This package is a new asset derived from the user's supplied Wolforge artwork. It contains no third-party character model or cloud dependency. Keep the source artwork and package license records with the Jarvis project.
