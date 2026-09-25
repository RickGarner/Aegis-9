# MOVEit HA Continuous Monitoring Script
# Monitors HA status and detects when fail-back conditions are met

param(
    [string]$Password = $env:AEGIS_MOVEIT_PASSWORD,
    [string]$OriginalPrimary = "bsoautalb001",
    [string]$CurrentPrimary = "bsoautalb002",
    [int]$CheckIntervalMinutes = 5,
    [switch]$Once
)

if ([string]::IsNullOrWhiteSpace($Password)) { throw 'Set AEGIS_MOVEIT_PASSWORD or supply -Password before running this script.' }

$securePassword = $Password | ConvertTo-SecureString -AsPlainText -Force

function Write-Status {
    param(
        [string]$Message,
        [string]$Level = "INFO",
        [string]$Color = "White"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $prefix = "[$timestamp] [$Level]"
    
    switch ($Level) {
        "INFO" { $color = "White" }
        "WARNING" { $color = "Yellow" }
        "ERROR" { $color = "Red" }
        "SUCCESS" { $color = "Green" }
    }
    
    Write-Host "$prefix $Message" -ForegroundColor $color
}

function Test-ServerAvailability {
    param([string]$ComputerName)
    
    $result = @{
        Server = $ComputerName
        Reachable = $false
        WinRMAccessible = $false
        MOVEitServices = $null
    }
    
    # Check network reachability
    try {
        $ping = New-Object System.Net.NetworkInformation.Ping
        $reply = $ping.Send($ComputerName, 2000)
        if ($reply.Status -eq "Success") {
            $result.Reachable = $true
        }
    } catch {
        return $result
    }
    
    # Check WinRM accessibility
    if ($result.Reachable) {
        try {
            $cred = New-Object System.Management.Automation.PSCredential("$ComputerName\moveitsvc", $securePassword)
            $services = Invoke-Command -ComputerName $ComputerName -Credential $cred -ScriptBlock {
                Get-Service -Name "*MOVEit*" -ErrorAction SilentlyContinue | Select-Object Name, Status | ConvertTo-Json
            } -ErrorAction SilentlyContinue
            
            if ($LASTEXITCODE -eq 0 -and $services) {
                $result.WinRMAccessible = $true
                $result.MOVEitServices = $services | ConvertFrom-Json
            }
        } catch {
            # WinRM not accessible
        }
    }
    
    return $result
}

function Get-HAStatus {
    $originalStatus = Test-ServerAvailability -ComputerName $OriginalPrimary
    $currentStatus = Test-ServerAvailability -ComputerName $CurrentPrimary
    
    $status = @{
        Timestamp = Get-Date -Format "o"
        OriginalPrimary = @{
            Server = $OriginalPrimary
            Reachable = $originalStatus.Reachable
            WinRMAccessible = $originalStatus.WinRMAccessible
            ServicesRunning = ($originalStatus.MOVEitServices | Where-Object { $_.Status -eq "Running" }).Count
        }
        CurrentPrimary = @{
            Server = $CurrentPrimary
            Reachable = $currentStatus.Reachable
            WinRMAccessible = $currentStatus.WinRMAccessible
            ServicesRunning = ($currentStatus.MOVEitServices | Where-Object { $_.Status -eq "Running" }).Count
        }
        ActingPrimary = $null
        FailbackReady = $false
    }
    
    # Determine acting primary
    if ($currentStatus.WinRMAccessible -and -not $originalStatus.WinRMAccessible) {
        $status.ActingPrimary = $CurrentPrimary
        $status.FailbackReady = $originalStatus.WinRMAccessible
    } elseif ($originalStatus.WinRMAccessible -and -not $currentStatus.WinRMAccessible) {
        $status.ActingPrimary = $OriginalPrimary
        $status.FailbackReady = $false
    } elseif ($originalStatus.WinRMAccessible -and $currentStatus.WinRMAccessible) {
        $status.ActingPrimary = $OriginalPrimary  # Default to original
        $status.FailbackReady = $true
    } else {
        $status.ActingPrimary = "UNKNOWN"
        $status.FailbackReady = $false
    }
    
    return $status
}

function Check-FailbackConditions {
    param([object]$HAStatus)
    
    $conditions = @{
        OriginalPrimaryAvailable = $false
        CurrentPrimaryAccessible = $false
        BothServersAccessible = $false
        ReadyForFailback = $false
    }
    
    $conditions.OriginalPrimaryAvailable = $HAStatus.OriginalPrimary.WinRMAccessible
    $conditions.CurrentPrimaryAccessible = $HAStatus.CurrentPrimary.WinRMAccessible
    $conditions.BothServersAccessible = $conditions.OriginalPrimaryAvailable -and $conditions.CurrentPrimaryAccessible
    $conditions.ReadyForFailback = $conditions.BothServersAccessible -and ($HAStatus.ActingPrimary -eq $CurrentPrimary)
    
    return $conditions
}

# Main monitoring loop
Write-Status "========================================" "INFO" "White"
Write-Status "MOVEit HA Continuous Monitor" "INFO" "White"
Write-Status "========================================" "INFO" "White"
Write-Status "Original Primary: $OriginalPrimary" "INFO" "White"
Write-Status "Current Primary: $CurrentPrimary" "INFO" "White"
Write-Status "Check Interval: ${CheckIntervalMinutes} minutes" "INFO" "White"
Write-Status ""

$previousStatus = $null
$failbackTriggered = $false

while ($true) {
    # Get current HA status
    $haStatus = Get-HAStatus
    
    # Check for state changes
    if ($previousStatus -and $previousStatus.ActingPrimary -ne $haStatus.ActingPrimary) {
        Write-Status "PRIMARY CHANGE DETECTED: $($previousStatus.ActingPrimary) -> $($haStatus.ActingPrimary)" "WARNING" "Yellow"
    }
    
    # Check fail-back conditions
    $conditions = Check-FailbackConditions -HAStatus $haStatus
    
    if ($conditions.ReadyForFailback -and -not $failbackTriggered) {
        Write-Status "FAIL-BACK CONDITIONS MET!" "SUCCESS" "Green"
        Write-Status "  - Original primary ($OriginalPrimary) is available" "SUCCESS" "Green"
        Write-Status "  - Current primary ($CurrentPrimary) is accessible" "SUCCESS" "Green"
        Write-Status "  - Both servers are accessible" "SUCCESS" "Green"
        Write-Status "  - Ready to initiate fail-back" "SUCCESS" "Green"
        Write-Status ""
        Write-Status "To initiate fail-back, run:" "INFO" "White"
        Write-Status "  .\scripts\moveit-failback\run-failback-process.ps1" "INFO" "White"
        Write-Status "    -OriginalPrimary $OriginalPrimary" "INFO" "White"
        Write-Status "    -CurrentPrimary $CurrentPrimary" "INFO" "White"
        Write-Status '    Supply -Password securely or set AEGIS_MOVEIT_PASSWORD.' 'INFO' 'White'
        Write-Status ""
        $failbackTriggered = $true
    } elseif (-not $conditions.ReadyForFailback -and $failbackTriggered) {
        Write-Status "FAIL-BACK CONDITIONS NO LONGER MET" "WARNING" "Yellow"
        $failbackTriggered = $false
    }
    
    # Output status
    Write-Status "Status: Acting Primary = $($haStatus.ActingPrimary)" "INFO" "White"
    Write-Status "  - ${OriginalPrimary}: Reachable=$($haStatus.OriginalPrimary.Reachable), WinRM=$($haStatus.OriginalPrimary.WinRMAccessible), Services=$($haStatus.OriginalPrimary.ServicesRunning)" "INFO" "Gray"
    Write-Status "  - ${CurrentPrimary}: Reachable=$($haStatus.CurrentPrimary.Reachable), WinRM=$($haStatus.CurrentPrimary.WinRMAccessible), Services=$($haStatus.CurrentPrimary.ServicesRunning)" "INFO" "Gray"
    Write-Status ""
    
    if ($Once) {
        break
    }
    
    # Wait for next check
    Write-Status "Next check in ${CheckIntervalMinutes} minutes..." "INFO" "Gray"
    Start-Sleep -Seconds ($CheckIntervalMinutes * 60)
    
    $previousStatus = $haStatus
}

# Output JSON status
$haStatus | ConvertTo-Json -Depth 10
