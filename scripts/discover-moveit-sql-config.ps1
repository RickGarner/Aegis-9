# Discover SQL Server connection details for MOVEit HA
# This script checks for SQL Server configuration in MOVEit services

function Get-MoveitSqlConfig {
    param(
        [string]$ComputerName,
        [string]$ServiceName
    )
    
    Write-Host "`nChecking $ServiceName on $ComputerName" -ForegroundColor Gray
    
    $config = @{
        computerName = $ComputerName
        serviceName = $ServiceName
        sqlServer = $null
        sqlDatabase = $null
        sqlConnection = $null
        sqlInstance = $null
    }
    
    # Check for SQL Server configuration in common locations
    # 1. Check Windows Registry for MOVEit configuration
    try {
        $registryPaths = @(
            "HKLM:\SOFTWARE\Progress Software\MOVEit Automation",
            "HKLM:\SOFTWARE\Wow6432Node\Progress Software\MOVEit Automation"
        )
        
        foreach ($regPath in $registryPaths) {
            try {
                $regValue = Get-ItemProperty -Path $regPath -Name "ConnectionString" -ErrorAction Stop
                $config.sqlConnection = $regValue.ConnectionString
                Write-Host "  Found connection string in registry" -ForegroundColor Cyan
                break
            } catch {
                # Registry key not found, continue
            }
        }
    } catch {
        Write-Host "  Could not read registry: $($_.Exception.Message)" -ForegroundColor Yellow
    }
    
    # 2. Check for SQL Server service
    try {
        $sqlServices = Get-Service -ComputerName $ComputerName -Name "*MSSQL*" -ErrorAction Stop
        foreach ($sqlService in $sqlServices) {
            $config.sqlServer = $sqlService.Name
            Write-Host "  Found SQL Server service: $($sqlService.DisplayName)" -ForegroundColor Cyan
        }
    } catch {
        Write-Host "  No SQL Server services found" -ForegroundColor Yellow
    }
    
    return $config
}

function Test-SqlConnection {
    param(
        [string]$ComputerName,
        [string]$ConnectionString
    )
    
    Write-Host "`nTesting SQL connection: $ConnectionString" -ForegroundColor Gray
    
    try {
        # Try to connect using SqlClient
        $connection = New-Object System.Data.SqlClient.SqlConnection
        $connection.ConnectionString = $ConnectionString
        $connection.Open()
        
        $result = @{
            success = $true
            message = "Connection successful"
        }
        
        $connection.Close()
        return $result
    } catch {
        return @{
            success = $false
            message = $_.Exception.Message
        }
    }
}

# MOVEit servers
$MoveitPrimary = "BSOAUTALB001"
$MoveitSecondary = "BSOAUTALB002"

# MOVEit services
$MoveitServices = @("MOVEitCentral", "MICAdmin")

Write-Host "`n=== MOVEit SQL Server Connection Discovery ===" -ForegroundColor Cyan

$results = @{
    timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    servers = @{
        primary = @{
            hostname = $MoveitPrimary
            services = @{}
        }
        secondary = @{
            hostname = $MoveitSecondary
            services = @{}
        }
    }
}

# Enumerate SQL config on both servers
foreach ($server in @($MoveitPrimary, $MoveitSecondary)) {
    $isPrimary = ($server -eq $MoveitPrimary)
    
    Write-Host "`n=== Checking SQL config on $server ===" -ForegroundColor Yellow
    
    foreach ($service in $MoveitServices) {
        Write-Host "`nChecking service: $service" -ForegroundColor Cyan
        
        $config = Get-MoveitSqlConfig -ComputerName $server -ServiceName $service
        
        if ($config) {
            if ($isPrimary) {
                $results.servers.primary.services[$service] = $config
            } else {
                $results.servers.secondary.services[$service] = $config
            }
        }
    }
}

# Save results
$outputFile = "storage/moveit-sql-config-$(Get-Date -Format 'yyyy-MM-dd').json"
$results | ConvertTo-Json -Depth 10 | Out-File -FilePath $outputFile -Encoding utf8

Write-Host "`nResults saved to: $outputFile" -ForegroundColor Green

# Print summary
Write-Host "`n=== SQL CONFIGURATION SUMMARY ===" -ForegroundColor Cyan

Write-Host "`nPrimary Server ($MoveitPrimary):" -ForegroundColor Yellow
foreach ($serviceName in $results.servers.primary.services.Keys) {
    $config = $results.servers.primary.services[$serviceName]
    Write-Host "  ${serviceName}:" -ForegroundColor Gray
    Write-Host "    SQL Server: $($config.sqlServer)" -ForegroundColor $(if ($config.sqlServer) { 'Green' } else { 'Yellow' })
    Write-Host "    Connection String: $($config.sqlConnection)" -ForegroundColor $(if ($config.sqlConnection) { 'Green' } else { 'Yellow' })
}

Write-Host "`nSecondary Server ($MoveitSecondary):" -ForegroundColor Yellow
foreach ($serviceName in $results.servers.secondary.services.Keys) {
    $config = $results.servers.secondary.services[$serviceName]
    Write-Host "  ${serviceName}:" -ForegroundColor Gray
    Write-Host "    SQL Server: $($config.sqlServer)" -ForegroundColor $(if ($config.sqlServer) { 'Green' } else { 'Yellow' })
    Write-Host "    Connection String: $($config.sqlConnection)" -ForegroundColor $(if ($config.sqlConnection) { 'Green' } else { 'Yellow' })
}
