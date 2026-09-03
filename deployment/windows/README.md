# A.E.G.I.S.-9 Windows workstation bootstrap

> This bootstrap belongs to the canonical `feature/cinematic-jarvis-ui`
> branch. Confirm that branch before running it. The older `main` branch does
> not contain the current cinematic UI/runtime stack. See
> [`docs/CURRENT-VERSION.md`](../../docs/CURRENT-VERSION.md) for the
> cross-computer handoff.

This package reproduces the local provider and speech-service layout used by the development workstation. It is intended for a clean 64-bit Windows 10 22H2 or Windows 11 computer with administrator access and a supported GPU driver.

## What it installs

| Component | Startup mechanism | Address | Purpose |
|---|---|---:|---|
| Ollama standalone runtime | Windows service (`Ollama`) | `127.0.0.1:11434` | Local general, coding, vision, and embedding models |
| LiteLLM Proxy 1.98.0 | Windows service (`LiteLLM`) | `127.0.0.1:4000` | Stable OpenAI-compatible aliases over local providers |
| Kokoro ONNX | Windows service (`Aegis9Kokoro`) | `127.0.0.1:5050` | Local A.E.G.I.S.-9 voice synthesis |
| LM Studio llmster | Windows service (`Aegis9LMStudio`) | `127.0.0.1:1234` | Headless LM Studio-compatible inference server |
| Jarvis FastAPI backend | Started and stopped by the WPF app | `127.0.0.1:8000` | Application API, storage, monitoring, Whisper, and routing |

The script also installs or verifies Python 3.11, the .NET 8 SDK/Desktop runtime, WebView2, WinSW, repository Python dependencies, and the Kokoro model files. Services bind to loopback only; no firewall port is opened.

## Before starting

1. Install the current GPU driver directly from NVIDIA, AMD, or Intel.
2. Ensure at least 20 GB free for the Core model profile or approximately 120 GB for Full.
3. Clone the repository and check out the synchronized branch:

   ```powershell
   git clone https://github.com/RickGarner/Aegis-9.git
   cd Aegis-9
   git switch feature/cinematic-jarvis-ui
   ```

4. Open **Windows PowerShell as Administrator**. The bootstrap uses direct vendor downloads, so it does not depend on WinGet (which may be disabled by organizational policy).

## Install

Core profile, recommended initially:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\deployment\windows\Install-Aegis9Workstation.ps1 -ModelProfile Core
```

Full Ollama profile matching the broader development inventory:

```powershell
.\deployment\windows\Install-Aegis9Workstation.ps1 -ModelProfile Full
```

Install services without downloading language models:

```powershell
.\deployment\windows\Install-Aegis9Workstation.ps1 -ModelProfile None
```

The LM Studio runtime is user-scoped. Windows will request the current account password once so WinSW can run that service under the same account and access its model store. The password is handed directly to the Windows service manager and is not written to the repository or bootstrap logs. To defer LM Studio service installation, use `-SkipLmStudioService`.

The default LM Studio model is the small official quick-start model `ibm/granite-4-micro`. Override it with:

```powershell
.\deployment\windows\Install-Aegis9Workstation.ps1 `
  -ModelProfile Core `
  -LmStudioModel 'publisher/model-id'
```

## Model profiles

Core pulls:

- `llama3.2:latest`
- `qwen2.5-coder:7b`
- `qwen3-vl:4b`
- `nomic-embed-text:latest`

Full additionally pulls:

- `gpt-oss:20b`
- `devstral-small-2:24b`
- `qwen3-vl:8b`
- `qwen3-coder:30b`
- `embeddinggemma:latest`
- `qwen2.5-coder:14b`
- `deepseek-coder-v2:16b`
- `deepseek-coder:6.7b`

Model downloads are deliberately separate from Git because the current Ollama inventory is roughly 100 GB. Faster-Whisper downloads `small.en` into the local Hugging Face cache on first transcription.

## Secrets and local state

The bootstrap generates a random LiteLLM master key in:

```text
C:\Aegis9\Secrets\litellm-master-key.txt
```

The directory ACL is restricted to SYSTEM, Administrators, and the installing account. The key is also written to the repository’s git-ignored `.env` as `JARVIS_LITELLM_API_KEY`. Never commit `.env`, model caches, SQLite storage, or `%LOCALAPPDATA%\Jarvis\settings.json`.

## Verify after reboot

```powershell
.\deployment\windows\Test-Aegis9Workstation.ps1
```

The verifier checks all four services and endpoints, builds `Aegis-9.sln`, and runs the backend unit tests. Then launch:

```powershell
.\desktop\Aegis.Desktop\bin\Debug\net8.0-windows\Aegis.Desktop.exe
```

## Troubleshooting

Service state:

```powershell
Get-Service Ollama,LiteLLM,Aegis9Kokoro,Aegis9LMStudio
```

Logs are under `C:\Aegis9\Services\<service>\logs`. Provider probes:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
Invoke-RestMethod http://127.0.0.1:4000/health/liveliness
Invoke-RestMethod http://127.0.0.1:1234/v1/models
Invoke-RestMethod http://127.0.0.1:5050/health
```

If LM Studio fails after a Windows password change, update its service logon credential or rerun the bootstrap. If a machine lacks sufficient VRAM, use the Core profile and allow A.E.G.I.S.-9’s hardware-aware provider router to select a smaller model.

## Design notes

- The installer is idempotent: rerunning it repairs files, updates Python dependencies, and reconfigures existing services.
- Service restart recovery and rolling logs are configured through WinSW and the Windows Service Control Manager.
- The A.E.G.I.S.-9 backend remains app-owned so closing the desktop application also closes its backend. It is intentionally not a permanent service.
- The bootstrap does not copy chat history, credentials, user preferences, uploads, or generated artifacts from another computer.
