# Check MOVEit SQL Server Configuration - Onsite Script
# Run this locally on the MOVEit servers to discover SQL configuration

[System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}

$moveitServers = @("bsoautalb001", "bsoautalb002")
$results = @{
    timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    servers = @{
        primary = @{
            computerName = "bsoautalb001"
            sqlServer = $null
            sqlInstance = $null
            connectionStrings = @()
            installationPaths = @()
            sqlPorts = @{
                tcp = $false
                udp = $false
            }
        }
        secondary = @{
            computerName = "bsoautalb002"
            sqlServer = $null
            sqlInstance = $null
            connectionStrings = @()
            installationPaths = @()
            sqlPorts = @{
                tcp = $false
                udp = $false
            }
        }
    }
}

Write-Host "=== MOVEit SQL Server Configuration Discovery ===" -ForegroundColor Cyan
Write-Host "Running locally on: $env:COMPUTERNAME" -ForegroundColor Gray
Write-Host ""

# Function to check SQL Server services
function Get-LocalSqlServices {
    $sqlServices = Get-Service -Name "*MSSQL*" -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq "Running" }
    
    if ($sqlServices) {
        foreach ($svc in $sqlServices) {
            $instanceName = $svc.Name -replace "MSSQL$", ""
            $instanceName = if ($instanceName -eq "") { "MSSQLSERVER" } else { $instanceName }
            
            Write-Host "  SQL Service: $($svc.DisplayName)" -ForegroundColor Green
            Write-Host "    Instance: $instanceName" -ForegroundColor Gray
            Write-Host "    Start Name: $($svc.StartName)" -ForegroundColor Gray
            
            # Get SQL Server version
            try {
                $sqlConnection = New-Object System.Data.SqlClient.SqlConnection("Server=$env:COMPUTERNAME\$instanceName;Integrated Security=True;")
                $sqlConnection.Open()
                $sqlCommand = $sqlConnection.CreateCommand()
                $sqlCommand.CommandText = "SELECT @@VERSION"
                $version = $sqlCommand.ExecuteScalar()
                Write-Host "    Version: $version" -ForegroundColor Gray
                $sqlConnection.Close()
            } catch {
                Write-Host "    Version: Unable to retrieve" -ForegroundColor Yellow
            }
            
            return @{
                server = $env:COMPUTERNAME
                instance = $instanceName
                serviceName = $svc.Name
            }
        }
    } else {
        Write-Host "  No local SQL Server instances found" -ForegroundColor Yellow
    }
}

# Function to check MOVEit installation paths
function Get-MoveitInstallationPaths {
    $moveitPaths = @(
        "C:\Program Files\Progress\MOVEit Automation",
        "C:\Program Files (x86)\Progress\MOVEit Automation",
        "D:\Program Files\Progress\MOVEit Automation",
        "E:\Program Files\Progress\MOVEit Automation"
    )
    
    foreach ($path in $moveitPaths) {
        if (Test-Path $path) {
            Write-Host "  Found: $path" -ForegroundColor Green
            $results.servers.$($env:COMPUTERNAME).installationPaths += $path
            
            # Check for web.config
            $webConfig = Join-Path $path "WebAdmin\web.config"
            if (Test-Path $webConfig) {
                Write-Host "    web.config found: $webConfig" -ForegroundColor Gray
                $results.servers.$($env:COMPUTERNAME).connectionStrings += $webConfig
                
                # Read connection strings
                try {
                    $xml = [System.Xml.XmlDocument]::new()
                    $xml.Load($web.config)
                    $connStrings = $xml.configuration.connectionStrings.add | Where-Object { $_.connectionString }
                    
                    if ($connStrings) {
                        foreach ($cs in $connStrings) {
                            Write-Host "    Connection String: $($cs.name)" -ForegroundColor Cyan
                            Write-Host "      Provider: $($cs.providerName)" -ForegroundColor Gray
                            # Mask password
                            $csString = $cs.connectionString -replace "Password=.*;", "Password=***;"
                            Write-Host "      String: $csString" -ForegroundColor Gray
                        }
                    }
                } catch {
                    Write-Host "    Error reading config: $_" -ForegroundColor Yellow
                }
            }
            
            # Check for other config files
            $configFiles = Get-ChildItem -Path $path -Filter "*.config" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 5
            foreach ($configFile in $configFiles) {
                if ($configFile.FullName -ne $webConfig) {
                    Write-Host "    Config: $($configFile.FullName)" -ForegroundColor Gray
                }
            }
        }
    }
}

# Function to check SQL Server ports
function Test-SqlPorts {
    $ports = @(1433, 1434, 5022, 5021, 1435)
    
    foreach ($port in $ports) {
        $tcpTest = Test-NetConnection -ComputerName $env:COMPUTERNAME -Port $port -InformationLevel Quiet -ErrorAction SilentlyContinue
        $udpTest = Test-NetConnection -ComputerName $env:COMPUTERNAME -Port $port -InformationLevel Quiet -ErrorAction SilentlyContinue
        
        if ($tcpTest) {
            Write-Host "  TCP Port $port: OPEN" -ForegroundColor Green
            $results.servers.$($env:COMPUTERNAME).sqlPorts.tcp = $true
        }
        if ($udpTest) {
            Write-Host "  UDP Port $port: OPEN" -ForegroundColor Green
            $results.servers.$($env:COMPUTERNAME).sqlPorts.udp = $true
        }
    }
}

# Function to check SQL Server configuration in registry
function Get-SqlRegistryConfig {
    $registryPaths = @(
        "HKLM:\SOFTWARE\Microsoft\Microsoft SQL Server\Instance Names\SQL",
        "HKLM:\SOFTWARE\Microsoft\MSSQLServer\Setup",
        "HKLM:\SOFTWARE\Microsoft\Microsoft SQL Server\MSSQL*\MSSQLServer\SuperSocketNetLib"
    )
    
    foreach ($regPath in $registryPaths) {
        try {
            $regItems = Get-Item -Path $regPath -ErrorAction SilentlyContinue
            if ($regItems) {
                Write-Host "  Registry: $regPath" -ForegroundColor Gray
                Get-ItemProperty -Path $regPath -ErrorAction SilentlyContinue | ForEach-Object {
                    $_.PSObject.Properties | Where-Object { $_.Name -ne "PSPath" -and $_.Name -ne "PSParentPath" -and $_.Name -ne "PSChildName" -and $_.Name -ne "PSDrive" } | ForEach-Object {
                        Write-Host "    $($_.Name): $($_.Value)" -ForegroundColor Gray
                    }
                }
            }
        } catch {
            # Registry path doesn't exist or not accessible
        }
    }
}

# Main execution
Write-Host "Checking local SQL Server configuration..." -ForegroundColor Cyan
Write-Host ""

# Get local SQL services
$sqlInfo = Get-LocalSqlServices
if ($sqlInfo) {
    $results.servers.$($env:COMPUTERNAME).sqlServer = $sqlInfo.server
    $results.servers.$($env:COMPUTERNAME).sqlInstance = $sqlInfo.instance
}

Write-Host ""
Write-Host "Checking MOVEit installation paths..." -ForegroundColor Cyan
Get-MoveitInstallationPaths

Write-Host ""
Write-Host "Checking SQL Server ports..." -ForegroundColor Cyan
Test-SqlPorts

Write-Host ""
Write-Host "Checking SQL Server registry configuration..." -ForegroundColor Cyan
Get-SqlRegistryConfig

Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "Computer: $($env:COMPUTERNAME)" -ForegroundColor Gray
Write-Host "SQL Server: $($results.servers.$($env:COMPUTERNAME).sqlServer)" -ForegroundColor Gray
Write-Host "SQL Instance: $($results.servers.$($env:COMPUTERNAME).sqlInstance)" -ForegroundColor Gray
Write-Host "Installation Paths: $($results.servers.$($env:COMPUTERNAME).installationPaths.Count)" -ForegroundColor Gray
Write-Host "Config Files with Connection Strings: $($results.servers.$($env:COMPUTERNAME).connectionStrings.Count)" -ForegroundColor Gray
Write-Host "SQL TCP Port Open: $($results.servers.$($env:COMPUTERNAME).sqlPorts.tcp)" -ForegroundColor Gray
Write-Host "SQL UDP Port Open: $($results.servers.$($env:COMPUTERNAME).sqlPorts.udp)" -ForegroundColor Gray

# Save results
$outputPath = "storage\moveit-sql-onsite-$(Get-Date -Format 'yyyy-MM-dd-HHmm').json"
$results | ConvertTo-Json -Depth 10 | Out-File -FilePath $outputPath -Encoding utf8
Write-Host ""
Write-Host "Results saved to: $outputPath" -ForegroundColor Green
