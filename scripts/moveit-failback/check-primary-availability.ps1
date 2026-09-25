# MOVEit HA Primary Availability Check
# Checks if the original primary server is available for fail-back

param(
    [string]$Password = $env:AEGIS_MOVEIT_PASSWORD,
    [string]$OriginalPrimary = "bsoautalb001",
    [string]$SecondaryServer = "bsoautalb002"
)

if ([string]::IsNullOrWhiteSpace($Password)) { throw 'Set AEGIS_MOVEIT_PASSWORD or supply -Password before running this script.' }

$securePassword = $Password | ConvertTo-SecureString -AsPlainText -Force

function Test-PrimaryAvailability {
    param([string]$ComputerName)
    
    $result = @{
        Server = $ComputerName
        Available = $false
        Checks = @{}
        Errors = @()
    }
    
    # Check 1: Network reachability
    Write-Host "  [1/4] Checking network reachability..." -ForegroundColor Yellow
    try {
        $ping = New-Object System.Net.NetworkInformation.Ping
        $reply = $ping.Send($ComputerName, 3000)
        if ($reply.Status -eq "Success") {
            $result.Checks.Network = @{ Status = "OK"; Latency = $reply.Roundtrip }
            Write-Host "    ✓ Network reachable (Latency: $($reply.Roundtrip)ms)" -ForegroundColor Green
        } else {
            $result.Checks.Network = @{ Status = "FAILED"; Reason = "Ping failed" }
            $result.Errors += "Network ping failed"
            Write-Host "    ✗ Network unreachable" -ForegroundColor Red
            return $result
        }
    } catch {
        $result.Checks.Network = @{ Status = "ERROR"; Reason = $_.Exception.Message }
        $result.Errors += "Network check error: $($_.Exception.Message)"
        Write-Host "    ✗ Network check error: $($_.Exception.Message)" -ForegroundColor Red
        return $result
    }
    
    # Check 2: WinRM accessibility
    Write-Host "  [2/4] Checking WinRM accessibility..." -ForegroundColor Yellow
    try {
        $cred = New-Object System.Management.Automation.PSCredential("$ComputerName\moveitsvc", $securePassword)
        $testResult = Test-WSMan -ComputerName $ComputerName -Credential $cred -ErrorAction Stop
        $result.Checks.WinRM = @{ Status = "OK"; Authentication = $testResult.Authentication }
        Write-Host "    ✓ WinRM accessible (Authentication: $($testResult.Authentication))" -ForegroundColor Green
    } catch {
        $result.Checks.WinRM = @{ Status = "FAILED"; Reason = $_.Exception.Message }
        $result.Errors += "WinRM check failed: $($_.Exception.Message)"
        Write-Host "    ✗ WinRM not accessible: $($_.Exception.Message)" -ForegroundColor Red
        return $result
    }
    
    # Check 3: MOVEit services status
    Write-Host "  [3/4] Checking MOVEit services..." -ForegroundColor Yellow
    try {
        $cred = New-Object System.Management.Automation.PSCredential("$ComputerName\moveitsvc", $securePassword)
        $services = Invoke-Command -ComputerName $ComputerName -Credential $cred -ScriptBlock {
            Get-Service -Name "*MOVEit*" -ErrorAction SilentlyContinue | Select-Object Name, Status, StartName | ConvertTo-Json
        } -ErrorAction Stop
        
        if ($services) {
            $servicesJson = $services | ConvertFrom-Json
            $runningCount = ($servicesJson | Where-Object { $_.Status -eq "Running" }).Count
            $totalCount = $servicesJson.Count
            
            $result.Checks.Services = @{
                Status = "OK"
                Total = $totalCount
                Running = $runningCount
                Services = $servicesJson
            }
            Write-Host "    ✓ MOVEit services found ($runningCount/$totalCount running)" -ForegroundColor Green
        } else {
            $result.Checks.Services = @{ Status = "FAILED"; Reason = "No MOVEit services found" }
            $result.Errors += "No MOVEit services found"
            Write-Host "    ✗ No MOVEit services found" -ForegroundColor Red
            return $result
        }
    } catch {
        $result.Checks.Services = @{ Status = "ERROR"; Reason = $_.Exception.Message }
        $result.Errors += "Service check error: $($_.Exception.Message)"
        Write-Host "    ✗ Service check error: $($_.Exception.Message)" -ForegroundColor Red
        return $result
    }
    
    # Check 4: HA status (basic check via WMI)
    Write-Host "  [4/4] Checking HA status..." -ForegroundColor Yellow
    try {
        $cred = New-Object System.Management.Automation.PSCredential("$ComputerName\moveitsvc", $securePassword)
        $haStatus = Invoke-Command -ComputerName $ComputerName -Credential $cred -ScriptBlock {
            # Check if MOVEit HA service is running
            $haService = Get-Service -Name "*MOVEit*HA*" -ErrorAction SilentlyContinue
            if ($haService) {
                return @{
                    HAServiceRunning = ($haService.Status -eq "Running")
                    HAServiceName = $haService.Name
                }
            } else {
                return @{
                    HAServiceRunning = $false
                    HAServiceName = "Not found"
                }
            }
        } -ErrorAction Stop
        
        $result.Checks.HA = $haStatus | ConvertFrom-Json | ForEach-Object { 
            @{ Status = if($_.HAServiceRunning){"OK"}else{"WARNING"}; Details = $_ }
        }
        
        if ($haStatus.HAServiceRunning) {
            Write-Host "    ✓ HA service running" -ForegroundColor Green
        } else {
            Write-Host "    ⚠ HA service not found (may still be available)" -ForegroundColor Yellow
        }
    } catch {
        $result.Checks.HA = @{ Status = "WARNING"; Reason = $_.Exception.Message }
        Write-Host "    ⚠ HA status check skipped: $($_.Exception.Message)" -ForegroundColor Yellow
    }
    
    # Final availability determination
    $result.Available = ($result.Checks.Network.Status -eq "OK" -and 
                         $result.Checks.WinRM.Status -eq "OK" -and 
                         $result.Checks.Services.Status -eq "OK")
    
    return $result
}

# Main execution
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MOVEit Primary Availability Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Checking original primary: $OriginalPrimary" -ForegroundColor Yellow
Write-Host ""

$availability = Test-PrimaryAvailability -ComputerName $OriginalPrimary

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Availability Result" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($availability.Available) {
    Write-Host "Status: AVAILABLE" -ForegroundColor Green
    Write-Host ""
    Write-Host "All checks passed:" -ForegroundColor Green
    Write-Host "  - Network: $($availability.Checks.Network.Status)" -ForegroundColor Green
    Write-Host "  - WinRM: $($availability.Checks.WinRM.Status)" -ForegroundColor Green
    Write-Host "  - Services: $($availability.Checks.Services.Status) ($($availability.Checks.Services.Running)/$($availability.Checks.Services.Total) running)" -ForegroundColor Green
    Write-Host "  - HA: $($availability.Checks.HA.Status)" -ForegroundColor Green
} else {
    Write-Host "Status: NOT AVAILABLE" -ForegroundColor Red
    Write-Host ""
    Write-Host "Failed checks:" -ForegroundColor Red
    if ($availability.Checks.Network.Status -ne "OK") {
        Write-Host "  - Network: $($availability.Checks.Network.Status)" -ForegroundColor Red
    }
    if ($availability.Checks.WinRM.Status -ne "OK") {
        Write-Host "  - WinRM: $($availability.Checks.WinRM.Status)" -ForegroundColor Red
    }
    if ($availability.Checks.Services.Status -ne "OK") {
        Write-Host "  - Services: $($availability.Checks.Services.Status)" -ForegroundColor Red
    }
}

Write-Host ""

# Output JSON result
$availability | ConvertTo-Json -Depth 10
