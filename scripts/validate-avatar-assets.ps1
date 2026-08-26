param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$avatarsRoot = Join-Path $ProjectRoot "desktop\Jarvis.Desktop\Assets\Avatars"
$profiles = @("male", "female")
$errors = @()

if (-not (Test-Path $avatarsRoot)) {
    Write-Error "Avatar assets root not found: $avatarsRoot"
    exit 1
}

foreach ($profile in $profiles) {
    $profileDir = Join-Path $avatarsRoot $profile
    $avatarJsonPath = Join-Path $profileDir "avatar.json"
    $manifestPath = Join-Path $profileDir "manifest.json"

    $metadataPath = if (Test-Path $avatarJsonPath) { $avatarJsonPath } elseif (Test-Path $manifestPath) { $manifestPath } else { $null }

    if ($null -eq $metadataPath) {
        $errors += "[$profile] Missing avatar metadata: $avatarJsonPath or $manifestPath"
        continue
    }

    try {
        $manifest = Get-Content $metadataPath -Raw | ConvertFrom-Json
    }
    catch {
        $errors += "[$profile] Invalid JSON metadata: $metadataPath"
        continue
    }

    $isAvatarJson = $metadataPath -eq $avatarJsonPath
    $modelField = if ($isAvatarJson) { "model" } else { "modelFile" }
    $requiredFields = @("displayName", "profile", $modelField, "format", "licenseName", "licenseUrl", "redistributionAllowed", "localUseAllowed", "attribution")
    foreach ($field in $requiredFields) {
        if ($null -eq $manifest.$field -or [string]::IsNullOrWhiteSpace([string]$manifest.$field) -and $field -ne "redistributionAllowed") {
            $errors += "[$profile] Missing required field '$field' in $metadataPath"
        }
    }

    if (-not $manifest.redistributionAllowed -and -not $manifest.localUseAllowed) {
        $errors += "[$profile] Neither redistributionAllowed nor localUseAllowed is true; host will refuse to load this avatar."
    }

    if (-not $manifest.redistributionAllowed -and $manifest.localUseAllowed) {
        Write-Host "[$profile] Local-use-only asset; redistribution remains disabled." -ForegroundColor Yellow
    }

    if ($manifest.profile -ne $profile) {
        $errors += "[$profile] Manifest profile '$($manifest.profile)' does not match folder profile '$profile'."
    }

    $format = ([string]$manifest.format).ToLowerInvariant()
    if ($format -notin @("glb", "gltf", "vrm")) {
        $errors += "[$profile] Unsupported format '$format'. Expected glb, gltf, or vrm."
    }

    $modelName = if ($isAvatarJson) { [string]$manifest.model } else { [string]$manifest.modelFile }
    $modelPath = Join-Path $profileDir $modelName
    if (-not (Test-Path $modelPath)) {
        $errors += "[$profile] Model file not found: $modelPath"
    }
    elseif ($format -eq "glb") {
        $modelBytes = [IO.File]::ReadAllBytes($modelPath)
        if ($modelBytes.Length -lt 1024 -or $modelBytes.Length -lt 20 -or [Text.Encoding]::ASCII.GetString($modelBytes, 0, 4) -ne "glTF") {
            $errors += "[$profile] GLB file is missing or incomplete: $modelPath"
        }
    }
}

if ($errors.Count -gt 0) {
    Write-Host "Avatar validation failed:" -ForegroundColor Red
    $errors | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
    exit 1
}

Write-Host "Avatar assets validated successfully for male/female profiles." -ForegroundColor Green
exit 0
