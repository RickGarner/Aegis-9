# MOVEit HA Primary Detection Script
# Detects which server is currently acting as primary

param(
    [string]$Password = $env:AEGIS_MOVEIT_PASSWORD,
    [string]$OriginalPrimary = "bsoautalb001",
    [string]$CurrentPrimary = "bsoautalb002"
)

if ([string]::IsNullOrWhiteSpace($Password)) { throw 'Set AEGIS_MOVEIT_PASSWORD or supply -Password before running this script.' }

$securePassword = $Password | ConvertTo-SecureString -AsPlainText -Force

function Test-ServerAvailability {
    param([string]$ComputerName)
    
    $result = @{
        Server = $ComputerName
        Reachable = $false
        WinRMAccessible = $false
        MOVEitServices = $null
        IsPrimary = $false
        Error = $null
    }
    
    # Check network reachability (ping)
    try {
        $ping = New-Object System.Net.NetworkInformation.Ping
        $reply = $ping.Send($ComputerName, 2000)
        if ($reply.Status -eq "Success") {
            $result.Reachable = $true
        }
    } catch {
        $result.Error = "Ping failed: $_"
        return $result
    }
    
    # Check WinRM accessibility with credentials
    if ($result.Reachable) {
        try {
            $cred = New-Object System.Management.Automation.PSCredential("$ComputerName\moveitsvc", $securePassword)
            $services = Invoke-Command -ComputerName $ComputerName -Credential $cred -ScriptBlock {
                Get-Service -Name "*MOVEit*" -ErrorAction SilentlyContinue | Select-Object Name, Status | ConvertTo-Json
            } -ErrorAction SilentlyContinue
            
            if ($LASTEXITCODE -eq 0 -and $services) {
                $result.WinRMAccessible = $true
                $result.MOVEitServices = $services | ConvertFrom-Json
            } else {
                $result.Error = "WinRM access failed or no MOVEit services found"
            }
        } catch {
            $result.Error = "WinRM connection failed: $($_.Exception.Message)"
        }
    }
    
    return $result
}

function Detect-CurrentPrimary {
    param([string]$OriginalPrimary, [string]$SecondaryServer)
    
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "MOVEit HA Primary Detection" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Test original primary
    Write-Host "Checking original primary ($OriginalPrimary)..." -ForegroundColor Yellow
    $originalResult = Test-ServerAvailability -ComputerName $OriginalPrimary
    Write-Host "  Reachable: $($originalResult.Reachable)" -ForegroundColor $(if($originalResult.Reachable){"Green"}else{"Red"})
    Write-Host "  WinRM Accessible: $($originalResult.WinRMAccessible)" -ForegroundColor $(if($originalResult.WinRMAccessible){"Green"}else{"Red"})
    if ($originalResult.MOVEitServices) {
        Write-Host "  MOVEit Services: $($originalResult.MOVEitServices.Count) services found" -ForegroundColor Green
    }
    Write-Host ""
    
    # Test secondary server
    Write-Host "Checking secondary server ($SecondaryServer)..." -ForegroundColor Yellow
    $secondaryResult = Test-ServerAvailability -ComputerName $SecondaryServer
    Write-Host "  Reachable: $($secondaryResult.Reachable)" -ForegroundColor $(if($secondaryResult.Reachable){"Green"}else{"Red"})
    Write-Host "  WinRM Accessible: $($secondaryResult.WinRMAccessible)" -ForegroundColor $(if($secondaryResult.WinRMAccessible){"Green"}else{"Red"})
    if ($secondaryResult.MOVEitServices) {
        Write-Host "  MOVEit Services: $($secondaryResult.MOVEitServices.Count) services found" -ForegroundColor Green
    }
    Write-Host ""
    
    # Determine current primary
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Detection Result" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    $currentPrimary = $null
    if ($secondaryResult.WinRMAccessible -and -not $originalResult.WinRMAccessible) {
        $currentPrimary = $SecondaryServer
        Write-Host "Current Acting Primary: $currentPrimary" -ForegroundColor Green
        Write-Host "Original Primary ($OriginalPrimary): Secondary (not accessible)" -ForegroundColor Gray
    } elseif ($originalResult.WinRMAccessible -and -not $secondaryResult.WinRMAccessible) {
        $currentPrimary = $OriginalPrimary
        Write-Host "Current Acting Primary: $currentPrimary" -ForegroundColor Green
        Write-Host "Secondary Server ($SecondaryServer): Not accessible" -ForegroundColor Gray
    } elseif ($originalResult.WinRMAccessible -and $secondaryResult.WinRMAccessible) {
        $currentPrimary = $OriginalPrimary  # Default to original if both accessible
        Write-Host "Current Acting Primary: $currentPrimary (both servers accessible)" -ForegroundColor Yellow
        Write-Host "Note: Both servers are accessible - assuming original primary is active" -ForegroundColor Yellow
    } else {
        Write-Host "ERROR: Neither server is accessible!" -ForegroundColor Red
        Write-Host "Original Primary ($OriginalPrimary): Not accessible" -ForegroundColor Red
        Write-Host "Secondary Server ($SecondaryServer): Not accessible" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "Web Admin URL: https://$currentPrimary/" -ForegroundColor Cyan
    Write-Host ""
    
    # Return result as JSON for programmatic use
    $result = @{
        CurrentPrimary = $currentPrimary
        OriginalPrimary = $OriginalPrimary
        OriginalPrimaryAccessible = $originalResult.WinRMAccessible
        SecondaryAccessible = $secondaryResult.WinRMAccessible
        OriginalPrimaryServices = $originalResult.MOVEitServices
        SecondaryServices = $secondaryResult.MOVEitServices
        Timestamp = Get-Date -Format "o"
    }
    
    return $result
}

# Run detection
$primaryInfo = Detect-CurrentPrimary -OriginalPrimary $OriginalPrimary -SecondaryServer $CurrentPrimary

# Output JSON result
$primaryInfo | ConvertTo-Json -Depth 10
