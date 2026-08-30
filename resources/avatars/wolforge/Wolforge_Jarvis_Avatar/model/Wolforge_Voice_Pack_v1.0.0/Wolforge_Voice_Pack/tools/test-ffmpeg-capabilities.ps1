[CmdletBinding()]
param([string]$FfmpegPath = 'ffmpeg.exe')
$ErrorActionPreference='Stop'
$filters = & $FfmpegPath -hide_banner -filters 2>&1 | Out-String
$required = 'rubberband','highpass','lowpass','equalizer','aeval','acompressor','alimiter'
$missing = @($required | Where-Object { $filters -notmatch "\b$([regex]::Escape($_))\b" })
if ($missing.Count) { throw "FFmpeg is missing required filters: $($missing -join ', ')" }
Write-Host 'Wolforge FFmpeg capability check passed.' -ForegroundColor Green
