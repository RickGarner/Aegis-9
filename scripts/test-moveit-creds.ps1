# MOVEit Credential Test Script
# This script tests the moveitsvc credentials against the MOVEit servers

if ([string]::IsNullOrWhiteSpace($env:AEGIS_MOVEIT_PASSWORD)) { throw 'Set AEGIS_MOVEIT_PASSWORD before running this script.' }
$password = $env:AEGIS_MOVEIT_PASSWORD
$securePassword = $password | ConvertTo-SecureString -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential("bsoautalb001\moveitsvc", $securePassword)

Write-Host "Testing credentials on bsoautalb001..." -ForegroundColor Yellow

try {
    $services = Invoke-Command -ComputerName bsoautalb001 -Credential $cred -ScriptBlock {
        Get-Service -Name "*MOVEit*" -ErrorAction SilentlyContinue | Select-Object Name, DisplayName, Status, StartName
    }
    
    Write-Host "  ✓ Successfully connected to bsoautalb001" -ForegroundColor Green
    Write-Host ""
    Write-Host "  MOVEit Services:" -ForegroundColor Cyan
    $services | Format-Table -AutoSize
    
} catch {
    Write-Host "  ✗ Failed to connect: $_" -ForegroundColor Red
}

# Test secondary server
$cred2 = New-Object System.Management.Automation.PSCredential("bsoautalb002\moveitsvc", $securePassword)

Write-Host ""
Write-Host "Testing credentials on bsoautalb002..." -ForegroundColor Yellow

try {
    $services2 = Invoke-Command -ComputerName bsoautalb002 -Credential $cred2 -ScriptBlock {
        Get-Service -Name "*MOVEit*" -ErrorAction SilentlyContinue | Select-Object Name, DisplayName, Status, StartName
    }
    
    Write-Host "  ✓ Successfully connected to bsoautalb002" -ForegroundColor Green
    Write-Host ""
    Write-Host "  MOVEit Services:" -ForegroundColor Cyan
    $services2 | Format-Table -AutoSize
    
} catch {
    Write-Host "  ✗ Failed to connect: $_" -ForegroundColor Red
}
