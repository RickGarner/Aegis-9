# A.E.G.I.S.-9 canonical version

## Read this first

As of 2026-08-30, active development is on the Git branch:

```text
feature/cinematic-jarvis-ui
```

The GitHub repository is:

```text
https://github.com/RickGarner/Jarvis-Desktop
```

`main` currently contains the older pre-cinematic WPF interface. Do not use a
build from `main` to review the current A.E.G.I.S.-9 UI, avatar, voice, or
provider-routing work. The cinematic branch includes all commits from `main`
through the merge commit `95a1f506`, followed by the current workstation
bootstrap commit `2a1079f8` and later commits on this branch.

Always verify the remote branch before beginning work:

```powershell
git fetch origin
git switch feature/cinematic-jarvis-ui
git pull --ff-only origin feature/cinematic-jarvis-ui
git status --short --branch
git log -5 --oneline --decorate
```

Expected branch display:

```text
feature/cinematic-jarvis-ui...origin/feature/cinematic-jarvis-ui
```

Do not assume that `origin/HEAD`, the default GitHub branch, or an existing
local `main` checkout is the current product version.

## Current application locations

| Area | Canonical location |
|---|---|
| Visual Studio solution | `Jarvis.sln` |
| Cinematic WPF UI | `desktop/Jarvis.Desktop/MainWindow.xaml` |
| Cinematic UI behavior | `desktop/Jarvis.Desktop/MainWindow.xaml.cs` |
| Cyber-lupine WebView runtime | `desktop/Jarvis.Desktop/Assets/AvatarHost/` |
| Cyber-lupine models | `desktop/Jarvis.Desktop/Assets/Avatars/shared/` |
| Avatar profile manifests | `desktop/Jarvis.Desktop/Assets/Avatars/male/` and `female/` |
| Adaptive provider router | `backend/app/providers.py` |
| Voice-input API | `backend/app/speech_recognition.py` and `backend/app/main.py` |
| Windows speech client | `desktop/Jarvis.Desktop/LocalSpeechRecognitionService.cs` |
| Kokoro speech client | `desktop/Jarvis.Desktop/KokoroSpeechService.cs` |
| Workstation installer | `deployment/windows/Install-Aegis9Workstation.ps1` |
| Workstation validator | `deployment/windows/Test-Aegis9Workstation.ps1` |
| Service templates | `deployment/windows/services/` |
| Dependency manifest | `deployment/windows/dependency-manifest.json` |
| Local configuration template | `.env.example` |
| Continuity record | `docs/handoff.md` |

The legacy browser client remains a separate repository/folder named
`Jarvis_Web`. It is not the current A.E.G.I.S.-9 operator interface.

## Clean-machine setup

On a new Windows workstation, clone and select the cinematic branch before
running any installation script:

```powershell
git clone https://github.com/RickGarner/Jarvis-Desktop.git
Set-Location Jarvis-Desktop
git switch feature/cinematic-jarvis-ui
Set-ExecutionPolicy -Scope Process Bypass
.\deployment\windows\Install-Aegis9Workstation.ps1 -ModelProfile Core
```

The bootstrap configures Python, .NET 8, WebView2, Ollama, LiteLLM, Kokoro
ONNX, LM Studio llmster, models, repository dependencies, `.env`, and Windows
services. See `deployment/windows/README.md` before running it.

Validate after installation or after moving to another computer:

```powershell
.\deployment\windows\Test-Aegis9Workstation.ps1
```

Then launch the current UI:

```powershell
.\desktop\Jarvis.Desktop\bin\Debug\net8.0-windows\Jarvis.Desktop.exe
```

## Verified cinematic state on 2026-08-30

- Cinematic WPF UI and cyber-lupine avatar assets are present.
- Adaptive local/remote provider discovery is implemented.
- Ollama, LM Studio, and LiteLLM routing code is present.
- Kokoro output and Windows offline speech fallback are integrated.
- Local Faster-Whisper voice input is implemented.
- The solution builds successfully on a third Windows workstation.
- Six backend provider/speech tests pass.
- The launched cinematic executable was visually confirmed as the expected UI.

Build currently reports one duplicated compiler warning that
`LocalSpeechRecognitionService.WakePhraseRecognized` is declared but unused.
There are no build errors.

## Work still open

- Complete end-to-end UI validation of microphone capture, transcription,
  Kokoro playback, interruption, and avatar mouth/state synchronization.
- Validate the service-based bootstrap after reboot on each new workstation,
  including the user-scoped LM Studio service credential.
- Validate GPU-specific routing and the Core/Full model profiles on different
  hardware.
- Finish MoveIT execution-history discovery or reliable log-based correlation.
- Connect the remote ServerMonitoring agent/hub feeds.
- Add the approved monitoring/workflow action catalog and notification outbox.
- Finish production packaging and installer validation.
- Implement research tools and broaden bounded artifact generation behind
  explicit approval and allowlist policies.

## Multi-computer safety rules

1. Fetch before reviewing or editing.
2. Confirm the branch is `feature/cinematic-jarvis-ui`.
3. Read this file and `docs/handoff.md` before making changes.
4. Do not copy build output, `.venv`, `.env`, model caches, `storage`, or user
   preferences between computers through Git.
5. Do not recreate dependency/runtime work outside `deployment/windows/`
   unless the bootstrap itself is being deliberately updated.
6. Keep commits scoped and push this branch so the next workstation sees them.
7. Do not merge the cinematic branch into `main` until an explicit release
   decision is made and the cinematic build has passed final acceptance.
