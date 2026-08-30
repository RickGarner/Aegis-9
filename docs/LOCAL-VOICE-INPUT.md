# Local voice input

Jarvis captures 16 kHz mono WAV audio with NAudio and sends it only to the local Jarvis backend, where Faster-Whisper performs transcription. Audio is not sent to a cloud transcription service.

## Controls

- Select **MIC** or press **Ctrl+Space** to begin one voice command.
- Select **STOP** or press **Ctrl+Space** again to cancel.
- The cyan meter beneath the composer shows live microphone input.
- With automatic submission enabled, recognized text is sent immediately. Otherwise it remains in the command box for review.
- Wake-phrase listening is deferred until the streaming Whisper phase. Push-to-talk remains available through MIC and Ctrl+Space.

Voice input can be configured under **Configure → Voice Input**.

## Windows prerequisites

1. Allow desktop applications to access the microphone under **Settings → Privacy & security → Microphone**.
2. Select the intended default recording device in Windows sound settings.

The first setup installs Faster-Whisper and downloads the selected model. After the model is cached locally, transcription works offline.
