[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$FreeFlowHost,
    [int]$JmfPort = 7751,
    [string]$JmfPath = "/FreeFlowCore",
    [string]$OutputDirectory = "."
)

. (Join-Path $PSScriptRoot "Aegis9-FreeFlow.Common.ps1")

$url = "http://$FreeFlowHost`:$JmfPort$JmfPath"
Write-AegisStep "Direct JMF KnownDevices test"
Write-Host "Endpoint: $url"

$result = Invoke-AegisJmfKnownDevices -Url $url

$outDir = Resolve-Path -LiteralPath $OutputDirectory
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$requestPath = Join-Path $outDir "FreeFlow-KnownDevices-request-$stamp.xml"
$responsePath = Join-Path $outDir "FreeFlow-KnownDevices-response-$stamp.xml"

Set-Content -LiteralPath $requestPath -Value $result.Request -Encoding UTF8
Set-Content -LiteralPath $responsePath -Value $result.Content -Encoding UTF8

Write-AegisOk "HTTP $($result.StatusCode)"
Write-Host "Request : $requestPath"
Write-Host "Response: $responsePath"
Write-AegisWarn "The response may contain workflow/queue identifiers. Treat captured XML as operational data."
