# MOVEit Onsite Credential Validation - Simplified
# Run this locally on the MOVEit servers

[System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}

$serviceAccount = ".\moveitsvc"
if ([string]::IsNullOrWhiteSpace($env:AEGIS_MOVEIT_PASSWORD)) { throw 'Set AEGIS_MOVEIT_PASSWORD before running this script.' }
$password = $env:AEGIS_MOVEIT_PASSWORD | ConvertTo-SecureString -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential($serviceAccount, $password)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MOVEit Credential Validation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Computer: $env:COMPUTERNAME" -ForegroundColor Gray
Write-Host "Service Account: $serviceAccount" -ForegroundColor Gray
Write-Host ""

# Test PowerShell remoting
Write-Host "Testing PowerShell remoting..." -ForegroundColor Yellow
try {
    $test = Test-WSMan -ComputerName $env:COMPUTERNAME -Credential $cred -ErrorAction Stop
    Write-Host "  ✓ PowerShell remoting successful" -ForegroundColor Green
} catch {
    Write-Host "  ✗ PowerShell remoting failed: $_" -ForegroundColor Red
}

# Enumerate MOVEit services
Write-Host ""
Write-Host "Enumerating MOVEit services..." -ForegroundColor Yellow
$moveitServices = Get-WmiObject -Class Win32_Service -Filter "Name='MOVEitCentral' OR Name='MICAdmin'" -ErrorAction SilentlyContinue
foreach ($svc in $moveitServices) {
    Write-Host "  Service: $($svc.DisplayName)" -ForegroundColor Gray
    Write-Host "    Name: $($svc.Name)" -ForegroundColor Gray
    Write-Host "    State: $($svc.State)" -ForegroundColor Gray
    Write-Host "    Start Name: $($svc.StartName)" -ForegroundColor Gray
}

# Test Web Admin
Write-Host ""
Write-Host "Testing Web Admin..." -ForegroundColor Yellow
$isPrimary = ($env:COMPUTERNAME -eq "bsoautalb001")
$webUrl = if ($isPrimary) { "https://bsoautalb001/" } else { "https://bsoautalb002/" }

try {
    $webRequest = [System.Net.HttpWebRequest]::Create($webUrl)
    $webRequest.Timeout = 5000
    $webRequest.AllowAutoRedirect = $false
    $response = $webRequest.GetResponse()
    $statusCode = [int]$response.StatusCode
    $response.Close()
    Write-Host "  ✓ Web Admin reachable (Status: $statusCode)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Web Admin unreachable: $_" -ForegroundColor Red
}

# Check SQL Server
Write-Host ""
Write-Host "Checking SQL Server..." -ForegroundColor Yellow
$sqlServices = Get-Service -Name "*MSSQL*" -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq "Running" }
if ($sqlServices) {
    foreach ($svc in $sqlServices) {
        $instanceName = $svc.Name -replace "MSSQL$", ""
        $instanceName = if ($instanceName -eq "") { "MSSQLSERVER" } else { $instanceName }
        Write-Host "  Local SQL Instance: $instanceName" -ForegroundColor Green
    }
} else {
    Write-Host "  No local SQL Server instances found" -ForegroundColor Yellow
    Write-Host "  SQL Server may be on: BSOSQAALB001 (10.30.67.108)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Validation Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
