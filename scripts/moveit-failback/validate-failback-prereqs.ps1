# MOVEit HA Pre-Fail-Back Validation
# Validates prerequisites before executing fail-back

param(
    [string]$Password = $env:AEGIS_MOVEIT_PASSWORD,
    [string]$OriginalPrimary = "bsoautalb001",
    [string]$CurrentPrimary = "bsoautalb002"
)

if ([string]::IsNullOrWhiteSpace($Password)) { throw 'Set AEGIS_MOVEIT_PASSWORD or supply -Password before running this script.' }

$securePassword = $Password | ConvertTo-SecureString -AsPlainText -Force

function Test-FailbackPrerequisites {
    param([string]$OriginalPrimary, [string]$CurrentPrimary)
    
    $result = @{
        Valid = $false
        Prerequisites = @{}
        Warnings = @()
        Errors = @()
    }
    
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Pre-Fail-Back Validation" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Prerequisite 1: Original primary is available
    Write-Host "[1/6] Checking original primary availability..." -ForegroundColor Yellow
    $originalCred = New-Object System.Management.Automation.PSCredential("$OriginalPrimary\moveitsvc", $securePassword)
    try {
        $originalTest = Test-WSMan -ComputerName $OriginalPrimary -Credential $originalCred -ErrorAction Stop
        $result.Prerequisites.OriginalPrimaryAvailable = $true
        Write-Host "  ✓ Original primary ($OriginalPrimary) is accessible" -ForegroundColor Green
    } catch {
        $result.Prerequisites.OriginalPrimaryAvailable = $false
        $result.Errors += "Original primary ($OriginalPrimary) is not accessible"
        Write-Host "  ✗ Original primary ($OriginalPrimary) is not accessible" -ForegroundColor Red
        return $result
    }
    
    # Prerequisite 2: Current primary is accessible
    Write-Host "[2/6] Checking current primary availability..." -ForegroundColor Yellow
    $currentCred = New-Object System.Management.Automation.PSCredential("$CurrentPrimary\moveitsvc", $securePassword)
    try {
        $currentTest = Test-WSMan -ComputerName $CurrentPrimary -Credential $currentCred -ErrorAction Stop
        $result.Prerequisites.CurrentPrimaryAvailable = $true
        Write-Host "  ✓ Current primary ($CurrentPrimary) is accessible" -ForegroundColor Green
    } catch {
        $result.Prerequisites.CurrentPrimaryAvailable = $false
        $result.Errors += "Current primary ($CurrentPrimary) is not accessible"
        Write-Host "  ✗ Current primary ($CurrentPrimary) is not accessible" -ForegroundColor Red
        return $result
    }
    
    # Prerequisite 3: MOVEit services running on original primary
    Write-Host "[3/6] Checking MOVEit services on original primary..." -ForegroundColor Yellow
    try {
        $originalServices = Invoke-Command -ComputerName $OriginalPrimary -Credential $originalCred -ScriptBlock {
            Get-Service -Name "*MOVEit*" -ErrorAction SilentlyContinue | Select-Object Name, Status | ConvertTo-Json
        } -ErrorAction Stop
        
        $servicesJson = $originalServices | ConvertFrom-Json
        $runningCount = ($servicesJson | Where-Object { $_.Status -eq "Running" }).Count
        
        if ($runningCount -gt 0) {
            $result.Prerequisites.ServicesRunning = $true
            $result.Prerequisites.RunningServicesCount = $runningCount
            Write-Host "  ✓ MOVEit services running ($runningCount services)" -ForegroundColor Green
        } else {
            $result.Prerequisites.ServicesRunning = $false
            $result.Errors += "No MOVEit services running on original primary"
            Write-Host "  ✗ No MOVEit services running on original primary" -ForegroundColor Red
            return $result
        }
    } catch {
        $result.Prerequisites.ServicesRunning = $false
        $result.Errors += "Could not check MOVEit services: $($_.Exception.Message)"
        Write-Host "  ✗ Could not check MOVEit services: $($_.Exception.Message)" -ForegroundColor Red
        return $result
    }
    
    # Prerequisite 4: MOVEit services running on current primary
    Write-Host "[4/6] Checking MOVEit services on current primary..." -ForegroundColor Yellow
    try {
        $currentServices = Invoke-Command -ComputerName $CurrentPrimary -Credential $currentCred -ScriptBlock {
            Get-Service -Name "*MOVEit*" -ErrorAction SilentlyContinue | Select-Object Name, Status | ConvertTo-Json
        } -ErrorAction Stop
        
        $servicesJson = $currentServices | ConvertFrom-Json
        $runningCount = ($servicesJson | Where-Object { $_.Status -eq "Running" }).Count
        
        if ($runningCount -gt 0) {
            $result.Prerequisites.CurrentPrimaryServicesRunning = $true
            $result.Prerequisites.CurrentPrimaryRunningServicesCount = $runningCount
            Write-Host "  ✓ MOVEit services running on current primary ($runningCount services)" -ForegroundColor Green
        } else {
            $result.Prerequisites.CurrentPrimaryServicesRunning = $false
            $result.Warnings += "No MOVEit services running on current primary"
            Write-Host "  ⚠ No MOVEit services running on current primary" -ForegroundColor Yellow
        }
    } catch {
        $result.Prerequisites.CurrentPrimaryServicesRunning = $false
        $result.Warnings += "Could not check MOVEit services on current primary: $($_.Exception.Message)"
        Write-Host "  ⚠ Could not check MOVEit services on current primary: $($_.Exception.Message)" -ForegroundColor Yellow
    }
    
    # Prerequisite 5: Database connectivity
    Write-Host "[5/6] Checking database connectivity..." -ForegroundColor Yellow
    try {
        # Check if SQL Server is accessible from both servers
        $dbCheck = Invoke-Command -ComputerName $CurrentPrimary -Credential $currentCred -ScriptBlock {
            # Try to resolve SQL Server hostname
            $sqlServer = "BSOSQAALB001"
            $ping = New-Object System.Net.NetworkInformation.Ping
            $reply = $ping.Send($sqlServer, 1000)
            return @{
                DatabaseReachable = ($reply.Status -eq "Success")
                SQLServer = $sqlServer
            }
        } -ErrorAction Stop
        
        $dbResult = $dbCheck | ConvertFrom-Json
        $result.Prerequisites.DatabaseAccessible = $dbResult.DatabaseReachable
        $result.Prerequisites.SQLServer = $dbResult.SQLServer
        
        if ($dbResult.DatabaseReachable) {
            Write-Host "  ✓ Database server ($($dbResult.SQLServer)) is accessible" -ForegroundColor Green
        } else {
            $result.Warnings += "Database server may not be accessible"
            Write-Host "  ⚠ Database server ($($dbResult.SQLServer)) may not be accessible" -ForegroundColor Yellow
        }
    } catch {
        $result.Prerequisites.DatabaseAccessible = $false
        $result.Warnings += "Could not check database connectivity: $($_.Exception.Message)"
        Write-Host "  ⚠ Could not check database connectivity: $($_.Exception.Message)" -ForegroundColor Yellow
    }
    
    # Prerequisite 6: Disk space check
    Write-Host "[6/6] Checking disk space..." -ForegroundColor Yellow
    try {
        $diskCheck = Invoke-Command -ComputerName $OriginalPrimary -Credential $originalCred -ScriptBlock {
            $moveitDrive = Get-Volume -DriveLetter C | Select-Object SizeRemaining, Size
            return @{
                DriveLetter = "C"
                SpaceRemainingGB = [math]::Round($_.SizeRemaining / 1GB, 2)
                TotalSpaceGB = [math]::Round($_.Size / 1GB, 2)
                PercentFree = [math]::Round(($_.SizeRemaining / $_.Size) * 100, 2)
            }
        } -ErrorAction Stop
        
        $diskResult = $diskCheck | ConvertFrom-Json
        $result.Prerequisites.DiskSpace = $diskResult
        
        if ($diskResult.PercentFree -gt 10) {
            $result.Prerequisites.AdequateDiskSpace = $true
            Write-Host "  ✓ Adequate disk space on original primary ($($diskResult.PercentFree)% free)" -ForegroundColor Green
        } else {
            $result.Prerequisites.AdequateDiskSpace = $false
            $result.Errors += "Insufficient disk space on original primary"
            Write-Host "  ✗ Insufficient disk space on original primary ($($diskResult.PercentFree)% free)" -ForegroundColor Red
            return $result
        }
    } catch {
        $result.Prerequisites.AdequateDiskSpace = $false
        $result.Warnings += "Could not check disk space: $($_.Exception.Message)"
        Write-Host "  ⚠ Could not check disk space: $($_.Exception.Message)" -ForegroundColor Yellow
    }
    
    # Final validation result
    $result.Valid = ($result.Prerequisites.OriginalPrimaryAvailable -and 
                     $result.Prerequisites.CurrentPrimaryAvailable -and 
                     $result.Prerequisites.ServicesRunning -and 
                     $result.Prerequisites.AdequateDiskSpace)
    
    return $result
}

# Main execution
Write-Host ""
Write-Host "Validating prerequisites for fail-back from $CurrentPrimary to $OriginalPrimary" -ForegroundColor Yellow
Write-Host ""

$validation = Test-FailbackPrerequisites -OriginalPrimary $OriginalPrimary -CurrentPrimary $CurrentPrimary

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Validation Result" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($validation.Valid) {
    Write-Host "Status: VALID - Ready to proceed with fail-back" -ForegroundColor Green
    Write-Host ""
    Write-Host "All prerequisites met:" -ForegroundColor Green
    Write-Host "  ✓ Original primary ($OriginalPrimary) is accessible" -ForegroundColor Green
    Write-Host "  ✓ Current primary ($CurrentPrimary) is accessible" -ForegroundColor Green
    Write-Host "  ✓ MOVEit services running on original primary ($($validation.Prerequisites.RunningServicesCount) services)" -ForegroundColor Green
    Write-Host "  ✓ Database server ($($validation.Prerequisites.SQLServer)) is accessible" -ForegroundColor Green
    Write-Host "  ✓ Adequate disk space on original primary ($($validation.Prerequisites.DiskSpace.PercentFree)% free)" -ForegroundColor Green
} else {
    Write-Host "Status: INVALID - Cannot proceed with fail-back" -ForegroundColor Red
    Write-Host ""
    Write-Host "Failed prerequisites:" -ForegroundColor Red
    if (-not $validation.Prerequisites.OriginalPrimaryAvailable) {
        Write-Host "  ✗ Original primary ($OriginalPrimary) is not accessible" -ForegroundColor Red
    }
    if (-not $validation.Prerequisites.CurrentPrimaryAvailable) {
        Write-Host "  ✗ Current primary ($CurrentPrimary) is not accessible" -ForegroundColor Red
    }
    if (-not $validation.Prerequisites.ServicesRunning) {
        Write-Host "  ✗ MOVEit services not running on original primary" -ForegroundColor Red
    }
    if (-not $validation.Prerequisites.AdequateDiskSpace) {
        Write-Host "  ✗ Insufficient disk space on original primary" -ForegroundColor Red
    }
}

if ($validation.Warnings.Count -gt 0) {
    Write-Host ""
    Write-Host "Warnings:" -ForegroundColor Yellow
    $validation.Warnings | ForEach-Object { Write-Host "  ⚠ $_" -ForegroundColor Yellow }
}

Write-Host ""

# Output JSON result
$validation | ConvertTo-Json -Depth 10
