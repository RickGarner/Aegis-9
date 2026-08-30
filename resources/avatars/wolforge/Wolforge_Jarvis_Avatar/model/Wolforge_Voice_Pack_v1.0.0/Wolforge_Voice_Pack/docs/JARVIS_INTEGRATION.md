# Jarvis integration handoff

## Objective

Add `wolforge` as a selectable Jarvis English voice. Jarvis continues to synthesize locally through Kokoro `am_fenrir`; this pack post-processes the resulting WAV into the recognizable Wolforge character voice and supplies a jaw envelope for avatar synchronization.

## Files to copy

1. Copy `src/Wolforge.Voice` into the Jarvis solution and add the project to the solution.
2. Add a project reference from the WPF application to `Wolforge.Voice`.
3. Copy `config/wolforge-voice.json` into Jarvis's voice asset folder and set **Copy to Output Directory** to `PreserveNewest`.
4. Put an approved FFmpeg Windows executable in Jarvis's local tools folder or change `ffmpegPath` to the installed executable.

## Existing adapters to implement

Implement these small interfaces against Jarvis's current services:

- `IKokoroSynthesizer`: call the existing Kokoro service and write mono PCM WAV. Pass through `voice=am_fenrir`, `language=en-us`, and `speed=0.94`.
- `IWolforgeAudioPlayer`: play the processed WAV using Jarvis's existing cancellable audio player. During playback, compare its elapsed position to each `JawFrame.Time` and send `JawFrame.Openness` to the avatar when fine-grained jaw control is available.
- `IWolforgeAvatar`: adapt the existing `WolforgeAvatarBridge.SpeakingAsync()` and `StopSpeakingAsync()` calls.

Register `WolforgeVoiceOptions`, `WolforgeVoiceProcessor`, and `WolforgeSpeechCoordinator` with the application's service container. Maintain one coordinator per active avatar session.

## Required speech lifecycle

1. Kokoro creates a temporary unprocessed WAV.
2. `WolforgeVoiceProcessor` creates a mono 24 kHz PCM16 Wolforge WAV.
3. `WavJawEnvelope` calculates amplitude-driven jaw positions.
4. Avatar enters `Speaking`.
5. Audio player plays the processed WAV.
6. On completion, cancellation, or error, playback stops, avatar returns to idle, and both temporary files are deleted.

The supplied coordinator enforces step 6 in a `finally` block.

## Profile selection

Use `normal` for ordinary responses. Map Jarvis states as follows:

| Situation | Profile |
|---|---|
| Conversation and explanation | `normal` |
| Noncritical warning | `warning` |
| Time-sensitive operational warning | `urgent` |
| Completion acknowledgement | `success` |
| Failed operation | `error` |

Never infer urgency from punctuation alone. The application state or response metadata must select the profile.

## Startup diagnostic

Run `tools/test-ffmpeg-capabilities.ps1` during installation or from Jarvis diagnostics. If it fails, disable Wolforge processing and fall back to clean Kokoro output; do not disable speech entirely.

## Security and reliability

- `ProcessStartInfo.ArgumentList` is used instead of shell command construction, so input/output paths are not executed as commands.
- Cancellation kills the FFmpeg process tree and removes partial output.
- Input text is passed only to Kokoro, never to FFmpeg or a remote service.
- Use a Jarvis-owned temporary directory and keep the existing cleanup policy.
- Log the selected profile and elapsed processing time, but do not log sensitive spoken text.

## Acceptance test

1. Confirm Kokoro `am_fenrir` produces the raw test phrases.
2. Run all five profiles and verify every output is mono PCM16 at 24 kHz.
3. Confirm normal speech is deep and gruff but fully intelligible.
4. Confirm warning/error are stronger without clipping.
5. Confirm urgent speech is slightly faster than normal.
6. Cancel a long utterance and verify the avatar mouth closes and temporary files disappear.
7. Temporarily rename FFmpeg and confirm clean Kokoro fallback still speaks.
8. Disconnect the network and repeat the complete test.

## Tuning limits

Keep `pitchSemitones` between approximately `-1.0` and `-3.0`. More extreme values tend to reduce intelligibility. Treat the supplied profiles as the production baseline and tune using the same test phrases and listening volume.
