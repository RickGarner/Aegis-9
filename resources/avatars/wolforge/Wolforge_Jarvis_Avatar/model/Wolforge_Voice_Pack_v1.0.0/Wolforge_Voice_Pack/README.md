# Wolforge Voice Pack 1.0

Offline English speech treatment for the Wolforge Jarvis cyber-wolf avatar. It uses Jarvis's existing Kokoro synthesizer with `am_fenrir`, then applies a controlled gruff, deep cyber-wolf treatment through a local FFmpeg process.

The pack deliberately avoids growls layered over words. Speech remains intelligible and professional while pitch, shifted formants, chest EQ, mild saturation, compression, and limiting establish the character.

## Included

- Five delivery profiles: normal, warning, urgent, success, and error.
- Cancellable C# audio processor.
- Kokoro-to-processing-to-playback coordinator.
- PCM16 jaw-envelope extraction at 20 ms resolution.
- PowerShell processing and capability-test tools.
- Integration and tuning documentation.
- Acceptance-test phrases.

## Runtime requirements

- Existing Jarvis Kokoro integration and `am_fenrir` voice.
- A local FFmpeg build containing the `rubberband` filter.
- .NET 9 Windows/WPF, matching the current Jarvis target. Change the project target if Jarvis uses a different .NET version.

No network service, API key, or cloud voice provider is used at runtime.
