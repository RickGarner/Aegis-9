[CmdletBinding()]
param(
    [string]$InstallRoot = 'C:\Aegis9',
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path,
    [ValidateSet('None','Core','Full')] [string]$ModelProfile = 'Core',
    [string]$LmStudioModel = 'ibm/granite-4-micro',
    [PSCredential]$LmStudioServiceCredential,
    [switch]$SkipLmStudioService
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Run this script from an elevated PowerShell window.'
    }
}

function Invoke-Download {
    param([Parameter(Mandatory)][string]$Uri, [Parameter(Mandatory)][string]$Destination, [string]$Sha256)
    if (Test-Path -LiteralPath $Destination) {
        if (-not $Sha256 -or (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash -eq $Sha256) { return }
        Remove-Item -LiteralPath $Destination -Force
    }
    Write-Host "Downloading $Uri"
    Invoke-WebRequest -Uri $Uri -OutFile $Destination -UseBasicParsing
    if ($Sha256 -and (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash -ne $Sha256) {
        Remove-Item -LiteralPath $Destination -Force
        throw "Checksum validation failed for $Uri"
    }
}

function Get-Python311 {
    try {
        $path = (& py -3.11 -c 'import sys; print(sys.executable)' 2>$null).Trim()
        if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $path)) { return $path }
    } catch { }

    $installer = Join-Path $downloadRoot 'python-3.11.9-amd64.exe'
    Invoke-Download 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' $installer
    $process = Start-Process -FilePath $installer -ArgumentList '/quiet','InstallAllUsers=1','PrependPath=1','Include_test=0','Include_launcher=1' -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "Python 3.11 installation failed with exit code $($process.ExitCode)." }
    $path = (& "$env:WINDIR\py.exe" -3.11 -c 'import sys; print(sys.executable)').Trim()
    if (-not (Test-Path -LiteralPath $path)) { throw 'Python 3.11 was installed but could not be located.' }
    return $path
}

function Ensure-VirtualEnvironment {
    param([string]$Directory, [string]$Requirements)
    $venvPython = Join-Path $Directory '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $venvPython)) {
        New-Item -ItemType Directory -Force -Path $Directory | Out-Null
        & $python311 -m venv (Join-Path $Directory '.venv')
        if ($LASTEXITCODE -ne 0) { throw "Unable to create virtual environment in $Directory" }
    }
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r $Requirements
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed in $Directory" }
    return $venvPython
}

function ConvertTo-XmlText {
    param([AllowEmptyString()][string]$Value)
    return [Security.SecurityElement]::Escape($Value)
}

function Install-WinSWService {
    param(
        [string]$Name,
        [string]$DisplayName,
        [string]$Application,
        [string]$WorkingDirectory,
        [string]$Arguments,
        [string[]]$Environment = @(),
        [PSCredential]$Credential
    )
    $serviceDirectory = Join-Path $serviceRoot $Name
    $logDirectory = Join-Path $serviceDirectory 'logs'
    New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
    $wrapper = Join-Path $serviceDirectory "$Name.exe"
    $config = Join-Path $serviceDirectory "$Name.xml"

    $service = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if ($service) {
        Stop-Service -Name $Name -Force -ErrorAction SilentlyContinue
        & sc.exe delete $Name | Out-Null
        for ($attempt = 0; $attempt -lt 20 -and (Get-Service -Name $Name -ErrorAction SilentlyContinue); $attempt++) {
            Start-Sleep -Milliseconds 250
        }
        if (Get-Service -Name $Name -ErrorAction SilentlyContinue) { throw "Unable to replace existing service $Name." }
    }
    Copy-Item -LiteralPath $winsw -Destination $wrapper -Force

    $environmentXml = foreach ($entry in $Environment) {
        $parts = $entry -split '=', 2
        if ($parts.Count -eq 2) { "  <env name=`"$(ConvertTo-XmlText $parts[0])`" value=`"$(ConvertTo-XmlText $parts[1])`" />" }
    }
    $xml = @(
        '<service>'
        "  <id>$(ConvertTo-XmlText $Name)</id>"
        "  <name>$(ConvertTo-XmlText $DisplayName)</name>"
        "  <description>Managed by the A.E.G.I.S.-9 Windows workstation bootstrap.</description>"
        "  <executable>$(ConvertTo-XmlText $Application)</executable>"
        "  <arguments>$(ConvertTo-XmlText $Arguments)</arguments>"
        "  <workingdirectory>$(ConvertTo-XmlText $WorkingDirectory)</workingdirectory>"
        '  <startmode>Automatic</startmode>'
        '  <stoptimeout>15sec</stoptimeout>'
        '  <onfailure action="restart" delay="5 sec" />'
        '  <onfailure action="restart" delay="15 sec" />'
        '  <resetfailure>1 hour</resetfailure>'
        "  <logpath>$(ConvertTo-XmlText $logDirectory)</logpath>"
        '  <log mode="roll-by-size">'
        '    <sizeThreshold>10240</sizeThreshold>'
        '    <keepFiles>8</keepFiles>'
        '  </log>'
        $environmentXml
        '</service>'
    )
    Set-Content -LiteralPath $config -Value $xml -Encoding utf8

    & $wrapper install
    if ($LASTEXITCODE -ne 0) { throw "Unable to install service $Name." }
    if ($Credential) {
        $plainPassword = $Credential.GetNetworkCredential().Password
        try {
            & sc.exe config $Name 'obj=' $Credential.UserName 'password=' $plainPassword | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "Unable to configure the service account for $Name." }
        }
        finally { $plainPassword = $null }
    }
}

function Set-DotEnvValue {
    param([string]$Path, [string]$Name, [string]$Value)
    $lines = if (Test-Path -LiteralPath $Path) { [Collections.Generic.List[string]](Get-Content -LiteralPath $Path) } else { [Collections.Generic.List[string]]::new() }
    $index = -1
    for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -match "^$([regex]::Escape($Name))=") { $index = $i; break } }
    $entry = "$Name=$Value"
    if ($index -ge 0) { $lines[$index] = $entry } else { $lines.Add($entry) }
    Set-Content -LiteralPath $Path -Value $lines -Encoding utf8
}

Assert-Administrator

$serviceRoot = Join-Path $InstallRoot 'Services'
$modelRoot = Join-Path $InstallRoot 'Models'
$toolRoot = Join-Path $InstallRoot 'Tools'
$downloadRoot = Join-Path $InstallRoot 'Downloads'
$secretRoot = Join-Path $InstallRoot 'Secrets'
foreach ($directory in $serviceRoot,$modelRoot,$toolRoot,$downloadRoot,$secretRoot) {
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
}

Write-Host 'Installing base runtimes...'
$python311 = Get-Python311

$dotnetCommand = Get-Command dotnet.exe -ErrorAction SilentlyContinue
$dotnet8 = if ($dotnetCommand) { @(& $dotnetCommand.Source --list-sdks 2>$null | Where-Object { $_ -match '^8\.' }) } else { @() }
if ($dotnet8.Count -eq 0) {
    $dotnetInstall = Join-Path $downloadRoot 'dotnet-install.ps1'
    Invoke-Download 'https://dot.net/v1/dotnet-install.ps1' $dotnetInstall
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $dotnetInstall -Channel 8.0 -InstallDir "$env:ProgramFiles\dotnet"
    if ($LASTEXITCODE -ne 0) { throw '.NET 8 SDK installation failed.' }
    $env:PATH = "$env:ProgramFiles\dotnet;$env:PATH"
}

$webViewInstaller = Join-Path $downloadRoot 'MicrosoftEdgeWebView2Setup.exe'
Invoke-Download 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' $webViewInstaller
$webViewProcess = Start-Process -FilePath $webViewInstaller -ArgumentList '/silent','/install' -Wait -PassThru
if ($webViewProcess.ExitCode -notin 0,1638) { Write-Warning "WebView2 installer returned $($webViewProcess.ExitCode)." }

Write-Host 'Installing WinSW service wrapper...'
$winswDirectory = Join-Path $toolRoot 'WinSW'
$winsw = Join-Path $winswDirectory 'WinSW-x64.exe'
if (-not (Test-Path -LiteralPath $winsw)) {
    New-Item -ItemType Directory -Force -Path $winswDirectory | Out-Null
    Invoke-Download 'https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe' $winsw
}

Write-Host 'Installing Ollama service...'
$ollamaDirectory = Join-Path $toolRoot 'Ollama'
$ollama = Join-Path $ollamaDirectory 'ollama.exe'
if (-not (Test-Path -LiteralPath $ollama)) {
    $ollamaArchive = Join-Path $downloadRoot 'ollama-windows-amd64.zip'
    Invoke-Download 'https://ollama.com/download/ollama-windows-amd64.zip' $ollamaArchive
    New-Item -ItemType Directory -Force -Path $ollamaDirectory | Out-Null
    Expand-Archive -LiteralPath $ollamaArchive -DestinationPath $ollamaDirectory -Force
    if (-not (Test-Path -LiteralPath $ollama)) { throw 'Ollama archive did not contain ollama.exe.' }
}
$ollamaModels = Join-Path $modelRoot 'Ollama'
New-Item -ItemType Directory -Force -Path $ollamaModels | Out-Null
Install-WinSWService -Name 'Ollama' -DisplayName 'Ollama Local Model Service' -Application $ollama -WorkingDirectory $ollamaDirectory -Arguments 'serve' -Environment @("OLLAMA_MODELS=$ollamaModels","OLLAMA_HOST=127.0.0.1:11434")
Start-Service Ollama

Write-Host 'Installing LiteLLM service...'
$liteDirectory = Join-Path $serviceRoot 'LiteLLM'
New-Item -ItemType Directory -Force -Path $liteDirectory | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'services\litellm\config.yaml') -Destination (Join-Path $liteDirectory 'config.yaml') -Force
$litePython = Ensure-VirtualEnvironment $liteDirectory (Join-Path $PSScriptRoot 'services\litellm\requirements.txt')
$liteExecutable = Join-Path $liteDirectory '.venv\Scripts\litellm.exe'
$masterKeyPath = Join-Path $secretRoot 'litellm-master-key.txt'
if (-not (Test-Path -LiteralPath $masterKeyPath)) {
    $randomBytes = [Security.Cryptography.RandomNumberGenerator]::GetBytes(32)
    Set-Content -LiteralPath $masterKeyPath -Value ("sk-" + [Convert]::ToHexString($randomBytes).ToLowerInvariant()) -NoNewline
}
$currentAccount = [Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls.exe $secretRoot '/inheritance:r' '/grant:r' 'SYSTEM:(OI)(CI)F' 'BUILTIN\Administrators:(OI)(CI)F' "$currentAccount`:(OI)(CI)F" | Out-Null
$masterKey = (Get-Content -LiteralPath $masterKeyPath -Raw).Trim()
Install-WinSWService -Name 'LiteLLM' -DisplayName 'LiteLLM Local AI Gateway' -Application $liteExecutable -WorkingDirectory $liteDirectory -Arguments "--config `"$liteDirectory\config.yaml`" --host 127.0.0.1 --port 4000" -Environment @('PYTHONUTF8=1','PYTHONIOENCODING=utf-8',"LITELLM_MASTER_KEY=$masterKey")
Start-Service LiteLLM

Write-Host 'Installing Kokoro speech service...'
$kokoroDirectory = Join-Path $serviceRoot 'Kokoro'
New-Item -ItemType Directory -Force -Path $kokoroDirectory | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'services\kokoro\app.py') -Destination (Join-Path $kokoroDirectory 'app.py') -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'services\kokoro\requirements.txt') -Destination (Join-Path $kokoroDirectory 'requirements.txt') -Force
$kokoroPython = Ensure-VirtualEnvironment $kokoroDirectory (Join-Path $kokoroDirectory 'requirements.txt')
$kokoroModels = Join-Path $modelRoot 'Kokoro'
New-Item -ItemType Directory -Force -Path $kokoroModels,(Join-Path $kokoroModels 'cache') | Out-Null
Invoke-Download 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx' (Join-Path $kokoroModels 'kokoro-v1.0.onnx') 'BEB0D1848DEE9A49DA392CC3DF26958D46CFA35D321EDF434F52949153F0DF3A'
Invoke-Download 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin' (Join-Path $kokoroModels 'voices-v1.0.bin') 'BCA610B8308E8D99F32E6FE4197E7EC01679264EFED0CAC9140FE9C29F1FBF7D'
Install-WinSWService -Name 'Aegis9Kokoro' -DisplayName 'A.E.G.I.S.-9 Kokoro Neural Speech' -Application $kokoroPython -WorkingDirectory $kokoroDirectory -Arguments "-m uvicorn app:app --app-dir `"$kokoroDirectory`" --host 127.0.0.1 --port 5050 --no-use-colors" -Environment @("KOKORO_MODEL_ROOT=$kokoroModels","KOKORO_CACHE_ROOT=$kokoroModels\cache")
Start-Service Aegis9Kokoro

if (-not $SkipLmStudioService) {
    Write-Host 'Installing LM Studio llmster headless runtime...'
    $lmInstaller = Join-Path $downloadRoot 'lmstudio-install.ps1'
    Invoke-Download 'https://lmstudio.ai/install.ps1' $lmInstaller
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $lmInstaller
    $lmsCandidates = @(
        (Join-Path $env:USERPROFILE '.lmstudio\bin\lms.exe'),
        (Get-Command lms.exe -ErrorAction SilentlyContinue).Source
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }
    $lms = $lmsCandidates | Select-Object -First 1
    if (-not $lms) { throw 'LM Studio installed, but lms.exe could not be found.' }
    if (-not $LmStudioServiceCredential) {
        $defaultUser = "$env:USERDOMAIN\$env:USERNAME"
        $LmStudioServiceCredential = Get-Credential -UserName $defaultUser -Message 'LM Studio is user-scoped. Enter this Windows account password so its service can access the user model store.'
    }
    $lmWrapper = Join-Path $serviceRoot 'Aegis9LMStudio\Start-LMStudioService.ps1'
    New-Item -ItemType Directory -Force -Path (Split-Path $lmWrapper) | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Start-LMStudioService.ps1') -Destination $lmWrapper -Force
    Install-WinSWService -Name 'Aegis9LMStudio' -DisplayName 'A.E.G.I.S.-9 LM Studio Headless Service' -Application "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -WorkingDirectory (Split-Path $lmWrapper) -Arguments "-NoProfile -ExecutionPolicy Bypass -File `"$lmWrapper`" -LmsPath `"$lms`" -Port 1234" -Environment @("USERPROFILE=$env:USERPROFILE","HOME=$env:USERPROFILE") -Credential $LmStudioServiceCredential
    & $lms daemon up
    if ($ModelProfile -ne 'None' -and $LmStudioModel) { & $lms get $LmStudioModel }
    Start-Service Aegis9LMStudio
}

if ($ModelProfile -ne 'None') {
    $ollamaCoreModels = @('llama3.2:latest','qwen2.5-coder:7b','qwen3-vl:4b','nomic-embed-text:latest')
    $ollamaFullModels = @('gpt-oss:20b','devstral-small-2:24b','qwen3-vl:8b','qwen3-coder:30b','embeddinggemma:latest','qwen2.5-coder:14b','deepseek-coder-v2:16b','deepseek-coder:6.7b')
    $models = if ($ModelProfile -eq 'Full') { $ollamaCoreModels + $ollamaFullModels } else { $ollamaCoreModels }
    foreach ($model in $models | Select-Object -Unique) {
        Write-Host "Pulling Ollama model $model"
        & $ollama pull $model
        if ($LASTEXITCODE -ne 0) { Write-Warning "Ollama could not pull $model" }
    }
}

Write-Host 'Preparing the repository runtime...'
$repoVenv = Join-Path $RepoRoot '.venv'
if (-not (Test-Path -LiteralPath (Join-Path $repoVenv 'Scripts\python.exe'))) { & $python311 -m venv $repoVenv }
& (Join-Path $repoVenv 'Scripts\python.exe') -m pip install --upgrade pip
& (Join-Path $repoVenv 'Scripts\python.exe') -m pip install -r (Join-Path $RepoRoot 'backend\requirements.txt')

$dotEnv = Join-Path $RepoRoot '.env'
if (-not (Test-Path -LiteralPath $dotEnv)) { Copy-Item -LiteralPath (Join-Path $RepoRoot '.env.example') -Destination $dotEnv }
Set-DotEnvValue $dotEnv 'JARVIS_LMSTUDIO_BASE_URL' 'http://127.0.0.1:1234/v1'
Set-DotEnvValue $dotEnv 'JARVIS_OLLAMA_BASE_URL' 'http://127.0.0.1:11434'
Set-DotEnvValue $dotEnv 'JARVIS_LITELLM_BASE_URL' 'http://127.0.0.1:4000/v1'
Set-DotEnvValue $dotEnv 'JARVIS_LITELLM_API_KEY' $masterKey
Set-DotEnvValue $dotEnv 'JARVIS_PROVIDER_DISCOVERY_ENABLED' 'true'
Set-DotEnvValue $dotEnv 'JARVIS_WHISPER_MODEL' 'small.en'
Set-DotEnvValue $dotEnv 'JARVIS_WHISPER_DEVICE' 'auto'
Set-DotEnvValue $dotEnv 'JARVIS_WHISPER_COMPUTE_TYPE' 'auto'

Push-Location $RepoRoot
try {
    & dotnet restore Aegis-9.sln
    & dotnet build Aegis-9.sln --no-restore
    if ($LASTEXITCODE -ne 0) { throw 'A.E.G.I.S.-9 desktop build failed.' }
}
finally { Pop-Location }

Write-Host ''
Write-Host 'Installation completed. Reboot once, then run:' -ForegroundColor Green
Write-Host "  powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\Test-Aegis9Workstation.ps1`" -RepoRoot `"$RepoRoot`""
Write-Host "LiteLLM key: $masterKeyPath"
