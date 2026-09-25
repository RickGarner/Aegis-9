# Discover SQL Server connection details for MOVEit HA
# Alternative approach: check config files and SQL Server services

function Get-SqlServerInfo {
    param(
        [string]$ComputerName
    )
    
    Write-Host "`nChecking SQL Server services on $ComputerName" -ForegroundColor Gray
    
    $sqlInfo = @{
        computerName = $ComputerName
        sqlServices = @()
        sqlInstances = @()
    }
    
    try {
        $sqlServices = Get-Service -ComputerName $ComputerName -Name "*MSSQL*" -ErrorAction Stop
        
        foreach ($svc in $sqlServices) {
            $sqlInfo.sqlServices += @{
                name = $svc.Name
                displayName = $svc.DisplayName
                status = $svc.Status
                startName = $null
            }
            
            # Try to get service account
            try {
                $wmiSvc = Get-WmiObject -Class Win32_Service -ComputerName $ComputerName -Filter "Name='$($svc.Name)'" -ErrorAction Stop
                $sqlInfo.sqlServices[-1].startName = $wmiSvc.StartName
            } catch {
                # Could not get WMI info
            }
        }
    } catch {
        Write-Host "  No SQL Server services found" -ForegroundColor Yellow
    }
    
    return $sqlInfo
}

function Get-MoveitConfigFiles {
    param(
        [string]$ComputerName
    )
    
    Write-Host "`nChecking MOVEit config files on $ComputerName" -ForegroundColor Gray
    
    $configPaths = @(
        "C:\Program Files\Progress\MOVEit Automation\WebAdmin\web.config",
        "C:\Program Files\Progress\MOVEit Automation\web.config",
        "C:\MOVEit Automation\web.config",
        "C:\ProgramData\Progress\MOVEit Automation\config.xml"
    )
    
    $foundConfigs = @()
    
    foreach ($path in $configPaths) {
        try {
            if (Test-Path -Path $path -ErrorAction Stop) {
                $foundConfigs += $path
                Write-Host "  Found config: $path" -ForegroundColor Cyan
            }
        } catch {
            # File not found
        }
    }
    
    return $foundConfigs
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

# MOVEit servers
$MoveitPrimary = "BSOAUTALB001"
$MoveitSecondary = "BSOAUTALB002"

Write-Host "`n=== MOVEit SQL Server Connection Discovery ===" -ForegroundColor Cyan

$results = @{
    timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    servers = @{
        primary = @{
            hostname = $MoveitPrimary
            ip = $null
            sqlServer = $null
            configFiles = @()
        }
        secondary = @{
            hostname = $MoveitSecondary
            ip = $null
            sqlServer = $null
            configFiles = @()
        }
    }
}

# Resolve hostnames
Write-Host "`nResolving hostnames..." -ForegroundColor Cyan
try {
    $primaryIp = [System.Net.Dns]::GetHostEntry($MoveitPrimary).AddressList[0].IPAddressToString
    $results.servers.primary.ip = $primaryIp
    Write-Host "  $MoveitPrimary -> $primaryIp" -ForegroundColor Gray
} catch {
    Write-Host "  Could not resolve $MoveitPrimary" -ForegroundColor Yellow
}

try {
    $secondaryIp = [System.Net.Dns]::GetHostEntry($MoveitSecondary).AddressList[0].IPAddressToString
    $results.servers.secondary.ip = $secondaryIp
    Write-Host "  $MoveitSecondary -> $secondaryIp" -ForegroundColor Gray
} catch {
    Write-Host "  Could not resolve $MoveitSecondary" -ForegroundColor Yellow
}

# Check SQL Server services on both servers
foreach ($server in @($MoveitPrimary, $MoveitSecondary)) {
    $isPrimary = ($server -eq $MoveitPrimary)
    $serverKey = if ($isPrimary) { "primary" } else { "secondary" }
    
    $sqlInfo = Get-SqlServerInfo -ComputerName $server
    
    if ($sqlInfo.sqlServices.Count -gt 0) {
        $results.servers.$serverKey.sqlServer = $sqlInfo
        Write-Host "`n  Found SQL Server services:" -ForegroundColor Cyan
        foreach ($svc in $sqlInfo.sqlServices) {
            Write-Host "    - $($svc.displayName) ($($svc.name)) - $($svc.status)" -ForegroundColor Gray
        }
    }
    
    # Check for config files
    $configFiles = Get-MoveitConfigFiles -ComputerName $server
    $results.servers.$serverKey.configFiles = $configFiles
}

# Test common SQL ports
Write-Host "`nTesting SQL Server ports..." -ForegroundColor Cyan
$sqlPorts = @(1433, 1434, 5022, 5021)

foreach ($port in $sqlPorts) {
    $primaryOpen = Test-SqlPort -ComputerName $MoveitPrimary -Port $port
    $secondaryOpen = Test-SqlPort -ComputerName $MoveitSecondary -Port $port
    
    if ($primaryOpen -or $secondaryOpen) {
        Write-Host "  Port ${port}: Primary=$primaryOpen, Secondary=$secondaryOpen" -ForegroundColor Green
    }
}

# Save results
$outputFile = "storage/moveit-sql-config-2026-09-23-v2.json"
$results | ConvertTo-Json -Depth 10 | Out-File -FilePath $outputFile -Encoding utf8

Write-Host "`nResults saved to: $outputFile" -ForegroundColor Green

# Print summary
Write-Host "`n=== SQL CONFIGURATION SUMMARY ===" -ForegroundColor Cyan

Write-Host "`nPrimary Server ($MoveitPrimary):" -ForegroundColor Yellow
Write-Host "  IP: $($results.servers.primary.ip)" -ForegroundColor Gray
if ($results.servers.primary.sqlServer) {
    Write-Host "  SQL Services:" -ForegroundColor Gray
    foreach ($svc in $results.servers.primary.sqlServer.sqlServices) {
        Write-Host "    - $($svc.displayName)" -ForegroundColor Gray
    }
}
if ($results.servers.primary.configFiles.Count -gt 0) {
    Write-Host "  Config Files:" -ForegroundColor Gray
    foreach ($cfg in $results.servers.primary.configFiles) {
        Write-Host "    - $cfg" -ForegroundColor Gray
    }
}

Write-Host "`nSecondary Server ($MoveitSecondary):" -ForegroundColor Yellow
Write-Host "  IP: $($results.servers.secondary.ip)" -ForegroundColor Gray
if ($results.servers.secondary.sqlServer) {
    Write-Host "  SQL Services:" -ForegroundColor Gray
    foreach ($svc in $results.servers.secondary.sqlServer.sqlServices) {
        Write-Host "    - $($svc.displayName)" -ForegroundColor Gray
    }
}
if ($results.servers.secondary.configFiles.Count -gt 0) {
    Write-Host "  Config Files:" -ForegroundColor Gray
    foreach ($cfg in $results.servers.secondary.configFiles) {
        Write-Host "    - $cfg" -ForegroundColor Gray
    }
}
