# Discover SQL Server connection details for MOVEit HA
# Direct approach: check for SQL Server instances and MOVEit config

function Get-SqlInstances {
    param(
        [string]$ComputerName
    )
    
    Write-Host "`nScanning for SQL Server instances on $ComputerName" -ForegroundColor Gray
    
    $instances = @()
    
    # Try to enumerate SQL Server services
    try {
        $services = Get-Service -ComputerName $ComputerName -ErrorAction Stop | Where-Object { $_.Name -like "*MSSQL*" }
        
        foreach ($svc in $services) {
            $instances += @{
                name = $svc.Name
                displayName = $svc.DisplayName
                status = $svc.Status
                startName = $null
            }
            
            # Try to get service account
            try {
                $wmiSvc = Get-WmiObject -Class Win32_Service -ComputerName $ComputerName -Filter "Name='$($svc.Name)'" -ErrorAction Stop
                $instances[-1].startName = $wmiSvc.StartName
            } catch {
                # Could not get WMI info
            }
        }
    } catch {
        Write-Host "  Could not enumerate services" -ForegroundColor Yellow
    }
    
    return $instances
}

function Test-SqlPort {
    param(
        [string]$ComputerName,
        [int]$Port = 1433
    )
    
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $asyncResult = $tcpClient.BeginConnect($ComputerName, $Port, $null, $null)
        $completed = $asyncResult.AsyncWaitHandle.WaitOne(2000, $false)
        
        if ($completed) {
            $tcpClient.EndConnect($asyncResult)
            $tcpClient.Close()
            return $true
        }
        $tcpClient.Close()
        return $false
    } catch {
        return $false
    }
}

function Get-MoveitInstallPath {
    param(
        [string]$ComputerName
    )
    
    Write-Host "`nChecking MOVEit installation paths on $ComputerName" -ForegroundColor Gray
    
    $commonPaths = @(
        "C:\Program Files\Progress\MOVEit Automation",
        "C:\Program Files (x86)\Progress\MOVEit Automation",
        "C:\MOVEit Automation",
        "D:\MOVEit Automation"
    )
    
    $foundPaths = @()
    
    foreach ($path in $commonPaths) {
        try {
            if (Test-Path -Path $path -ErrorAction Stop) {
                $foundPaths += $path
                Write-Host "  Found: $path" -ForegroundColor Cyan
            }
        } catch {
            # Path not found
        }
    }
    
    return $foundPaths
}

# MOVEit servers
$MoveitPrimary = "BSOAUTALB001"
$MoveitSecondary = "BSOAUTALB002"

Write-Host "`n=== MOVEit SQL Server Connection Discovery ===" -ForegroundColor Cyan

$results = @{
    timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    servers = @{
        primary = @{
            hostname = $MoveitPrimary
            ip = "10.30.67.105"
            sqlInstances = @()
            moveitInstallPath = @()
        }
        secondary = @{
            hostname = $MoveitSecondary
            ip = "10.30.67.106"
            sqlInstances = @()
            moveitInstallPath = @()
        }
    }
}

# Check SQL Server instances on both servers
foreach ($server in @($MoveitPrimary, $MoveitSecondary)) {
    $isPrimary = ($server -eq $MoveitPrimary)
    $serverKey = if ($isPrimary) { "primary" } else { "secondary" }
    
    $instances = Get-SqlInstances -ComputerName $server
    
    if ($instances.Count -gt 0) {
        $results.servers.$serverKey.sqlInstances = $instances
        Write-Host "`n  Found SQL Server instances:" -ForegroundColor Cyan
        foreach ($inst in $instances) {
            Write-Host "    - $($inst.displayName) ($($inst.name))" -ForegroundColor Gray
        }
    } else {
        Write-Host "`n  No SQL Server instances found" -ForegroundColor Yellow
    }
    
    # Check MOVEit installation path
    $installPaths = Get-MoveitInstallPath -ComputerName $server
    $results.servers.$serverKey.moveitInstallPath = $installPaths
}

# Test common SQL ports
Write-Host "`nTesting SQL Server ports..." -ForegroundColor Cyan
$sqlPorts = @(1433, 1434, 5022, 5021, 1435)

foreach ($port in $sqlPorts) {
    $primaryOpen = Test-SqlPort -ComputerName $MoveitPrimary -Port $port
    $secondaryOpen = Test-SqlPort -ComputerName $MoveitSecondary -Port $port
    
    if ($primaryOpen -or $secondaryOpen) {
        Write-Host "  Port ${port}: Primary=$primaryOpen, Secondary=$secondaryOpen" -ForegroundColor Green
    }
}

# Save results
$outputFile = "storage/moveit-sql-config-2026-09-23-v3.json"
$results | ConvertTo-Json -Depth 10 | Out-File -FilePath $outputFile -Encoding utf8

Write-Host "`nResults saved to: $outputFile" -ForegroundColor Green

# Print summary
Write-Host "`n=== SQL CONFIGURATION SUMMARY ===" -ForegroundColor Cyan

Write-Host "`nPrimary Server ($MoveitPrimary):" -ForegroundColor Yellow
Write-Host "  IP: $($results.servers.primary.ip)" -ForegroundColor Gray
if ($results.servers.primary.sqlInstances.Count -gt 0) {
    Write-Host "  SQL Instances:" -ForegroundColor Gray
    foreach ($inst in $results.servers.primary.sqlInstances) {
        Write-Host "    - $($inst.displayName)" -ForegroundColor Gray
    }
}
if ($results.servers.primary.moveitInstallPath.Count -gt 0) {
    Write-Host "  MOVEit Install Path:" -ForegroundColor Gray
    foreach ($path in $results.servers.primary.moveitInstallPath) {
        Write-Host "    - $path" -ForegroundColor Gray
    }
}

Write-Host "`nSecondary Server ($MoveitSecondary):" -ForegroundColor Yellow
Write-Host "  IP: $($results.servers.secondary.ip)" -ForegroundColor Gray
if ($results.servers.secondary.sqlInstances.Count -gt 0) {
    Write-Host "  SQL Instances:" -ForegroundColor Gray
    foreach ($inst in $results.servers.secondary.sqlInstances) {
        Write-Host "    - $($inst.displayName)" -ForegroundColor Gray
    }
}
if ($results.servers.secondary.moveitInstallPath.Count -gt 0) {
    Write-Host "  MOVEit Install Path:" -ForegroundColor Gray
    foreach ($path in $results.servers.secondary.moveitInstallPath) {
        Write-Host "    - $path" -ForegroundColor Gray
    }
}
