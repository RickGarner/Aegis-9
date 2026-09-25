# MOVEit Credential Validation Script
# Dynamically detects acting primary and validates credentials

if ([string]::IsNullOrWhiteSpace($env:AEGIS_MOVEIT_PASSWORD)) { throw 'Set AEGIS_MOVEIT_PASSWORD before running this script.' }
$password = $env:AEGIS_MOVEIT_PASSWORD
$securePassword = $password | ConvertTo-SecureString -AsPlainText -Force

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MOVEit Credential Validation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Test bsoautalb001
Write-Host "Testing credentials on bsoautalb001..." -ForegroundColor Yellow
$cred1 = New-Object System.Management.Automation.PSCredential("bsoautalb001\moveitsvc", $securePassword)
try {
    $services1 = Invoke-Command -ComputerName bsoautalb001 -Credential $cred1 -ScriptBlock {
        Get-Service -Name "*MOVEit*" -ErrorAction SilentlyContinue | Select-Object Name, Status
    } -ErrorAction Stop
    Write-Host "  SUCCESS: Connected to bsoautalb001" -ForegroundColor Green
    Write-Host "  MOVEit Services:" -ForegroundColor Cyan
    $services1 | Format-Table -AutoSize
    $primary = "bsoautalb001"
} catch {
    Write-Host "  FAILED: bsoautalb001 - $($_.Exception.Message)" -ForegroundColor Red
    $primary = "bsoautalb002"
}

Write-Host ""

# Test bsoautalb002
Write-Host "Testing credentials on bsoautalb002..." -ForegroundColor Yellow
$cred2 = New-Object System.Management.Automation.PSCredential("bsoautalb002\moveitsvc", $securePassword)
try {
    $services2 = Invoke-Command -ComputerName bsoautalb002 -Credential $cred2 -ScriptBlock {
        Get-Service -Name "*MOVEit*" -ErrorAction SilentlyContinue | Select-Object Name, Status
    } -ErrorAction Stop
    Write-Host "  SUCCESS: Connected to bsoautalb002" -ForegroundColor Green
    Write-Host "  MOVEit Services:" -ForegroundColor Cyan
    $services2 | Format-Table -AutoSize
    if (-not $primary) {
        $primary = "bsoautalb002"
    }
} catch {
    Write-Host "  FAILED: bsoautalb002 - $($_.Exception.Message)" -ForegroundColor Red
    if (-not $primary) {
        $primary = "bsoautalb001"
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($primary -eq "bsoautalb001") {
    Write-Host "Acting Primary: bsoautalb001" -ForegroundColor Green
    Write-Host "Secondary: bsoautalb002" -ForegroundColor Gray
} else {
    Write-Host "Acting Primary: bsoautalb002" -ForegroundColor Green
    Write-Host "Secondary: bsoautalb001" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Web Admin URL: https://$primary/" -ForegroundColor Cyan
