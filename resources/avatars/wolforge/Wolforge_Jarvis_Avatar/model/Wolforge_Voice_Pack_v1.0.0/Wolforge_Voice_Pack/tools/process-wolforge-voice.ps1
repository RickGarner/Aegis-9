[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$InputWav,
    [Parameter(Mandatory)][string]$OutputWav,
    [ValidateSet('normal','warning','urgent','success','error')][string]$Profile = 'normal',
    [string]$ConfigPath = (Join-Path $PSScriptRoot '..\config\wolforge-voice.json')
)
$ErrorActionPreference = 'Stop'
$cfg = Get-Content -Raw $ConfigPath | ConvertFrom-Json
$p = $cfg.profiles.$Profile
$pitch = [Math]::Pow(2, [double]$p.pitchSemitones / 12)
$inv = [Globalization.CultureInfo]::InvariantCulture
function N([double]$v) { $v.ToString('0.######', $inv) }
$limit = [Math]::Pow(10, [double]$p.targetPeakDb / 20)
$filter = @(
    "rubberband=pitch=$(N $pitch):tempo=$(N $p.tempo):transients=smooth:detector=soft:formant=shifted:pitchq=quality"
    'highpass=f=55'
    'lowpass=f=10500'
    "equalizer=f=125:t=q:w=0.8:g=$(N $p.bassGainDb)"
    "equalizer=f=2600:t=q:w=1.1:g=$(N $p.presenceGainDb)"
    "aeval=tanh($(N $p.drive)*val(0))/tanh($(N $p.drive))"
    "acompressor=threshold=$(N $p.compressorThresholdDb)dB:ratio=$(N $p.compressorRatio):attack=12:release=140:makeup=1.15"
    "alimiter=limit=$(N $limit):attack=5:release=50"
) -join ','
$ffmpeg = if ($cfg.ffmpegPath) { [string]$cfg.ffmpegPath } else { 'ffmpeg.exe' }
& $ffmpeg -hide_banner -loglevel error -y -i $InputWav -af $filter -ar $cfg.outputSampleRate -ac 1 -c:a pcm_s16le $OutputWav
if ($LASTEXITCODE -ne 0 -or !(Test-Path $OutputWav)) { throw "Wolforge voice processing failed with exit code $LASTEXITCODE." }
Get-Item $OutputWav
