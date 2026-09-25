# Discover MOVEit service account credentials for PowerShell remoting
# This script enumerates services and checks for service account information

function Get-ServiceAccountInfo {
    param(
        [string]$ComputerName,
        [string]$ServiceName
    )
    
    Write-Host "`nChecking service: $ServiceName on $ComputerName" -ForegroundColor Gray
    
    try {
        $service = Get-Service -Name $ServiceName -ComputerName $ComputerName -ErrorAction Stop
        
        $accountInfo = @{
            serviceName = $ServiceName
            displayName = $service.DisplayName
            status = $service.Status
            startType = $service.StartType
            serviceAccount = $null
        }
        
        # Try to get service account using WMI (requires admin privileges)
        try {
            $wmiService = Get-WmiObject -Class Win32_Service -ComputerName $ComputerName -Filter "Name='$ServiceName'" -ErrorAction Stop
            if ($wmiService) {
                $accountInfo.serviceAccount = $wmiService.StartName
            }
        } catch {
            Write-Host "  Could not retrieve service account via WMI (may require admin)" -ForegroundColor Yellow
        }
        
        return $accountInfo
    } catch {
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

function Test-PowerShellRemoting {
    param(
        [string]$ComputerName,
        [string]$Credential
    )
    
    Write-Host "`nTesting PowerShell Remoting to $ComputerName" -ForegroundColor Gray
    
    try {
        if ($Credential) {
            $session = New-PSSession -ComputerName $ComputerName -Credential $Credential -ErrorAction Stop
        } else {
            $session = New-PSSession -ComputerName $ComputerName -ErrorAction Stop
        }
        
        $result = @{
            reachable = $true
            message = "PowerShell remoting successful"
        }
        
        Remove-PSSession -Session $session -ErrorAction SilentlyContinue
        return $result
    } catch {
        return @{
            reachable = $false
            message = $_.Exception.Message
        }
    }
}

# MOVEit servers
$MoveitPrimary = "BSOAUTALB001"
$MoveitSecondary = "BSOAUTALB002"

# Common MOVEit service names
$MoveitServices = @(
    "MOVEitCentral",
    "MOVEitDM",
    "MOVEitScheduler",
    "MOVEitTransfer"
)

Write-Host "`n=== MOVEit Service Account Discovery ===" -ForegroundColor Cyan

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

# Enumerate services on both servers
foreach ($server in @($MoveitPrimary, $MoveitSecondary)) {
    $isPrimary = ($server -eq $MoveitPrimary)
    
    Write-Host "`n=== Enumerating services on $server ===" -ForegroundColor Yellow
    
    # Get all services
    try {
        $allServices = Get-Service -ComputerName $server -ErrorAction Stop
        
        foreach ($service in $allServices) {
            # Check if it's a MOVEit-related service
            if ($service.Name -like "*MOVEit*" -or $service.DisplayName -like "*MOVEit*") {
                Write-Host "`n  Found MOVEit service: $($service.Name)" -ForegroundColor Cyan
                
                $accountInfo = Get-ServiceAccountInfo -ComputerName $server -ServiceName $service.Name
                
                if ($accountInfo) {
                    if ($isPrimary) {
                        $results.servers.primary.services[$service.Name] = $accountInfo
                    } else {
                        $results.servers.secondary.services[$service.Name] = $accountInfo
                    }
                }
            }
        }
    } catch {
        Write-Host "  Error enumerating services: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Save results
$outputFile = "storage/moveit-service-accounts-$(Get-Date -Format 'yyyy-MM-dd').json"
$results | ConvertTo-Json -Depth 10 | Out-File -FilePath $outputFile -Encoding utf8

Write-Host "`nResults saved to: $outputFile" -ForegroundColor Green

# Print summary
Write-Host "`n=== SERVICE ACCOUNT SUMMARY ===" -ForegroundColor Cyan

Write-Host "`nPrimary Server ($MoveitPrimary):" -ForegroundColor Yellow
foreach ($serviceName in $results.servers.primary.services.Keys) {
    $service = $results.servers.primary.services[$serviceName]
    Write-Host "  ${serviceName}:" -ForegroundColor Gray
    Write-Host "    Display Name: $($service.displayName)" -ForegroundColor Gray
    Write-Host "    Status: $($service.status)" -ForegroundColor Gray
    Write-Host "    Start Type: $($service.startType)" -ForegroundColor Gray
    if ($service.serviceAccount) {
        Write-Host "    Service Account: $($service.serviceAccount)" -ForegroundColor Green
    } else {
        Write-Host "    Service Account: Not discovered (may require admin access)" -ForegroundColor Yellow
    }
}

Write-Host "`nSecondary Server ($MoveitSecondary):" -ForegroundColor Yellow
foreach ($serviceName in $results.servers.secondary.services.Keys) {
    $service = $results.servers.secondary.services[$serviceName]
    Write-Host "  ${serviceName}:" -ForegroundColor Gray
    Write-Host "    Display Name: $($service.displayName)" -ForegroundColor Gray
    Write-Host "    Status: $($service.status)" -ForegroundColor Gray
    Write-Host "    Start Type: $($service.startType)" -ForegroundColor Gray
    if ($service.serviceAccount) {
        Write-Host "    Service Account: $($service.serviceAccount)" -ForegroundColor Green
    } else {
        Write-Host "    Service Account: Not discovered (may require admin access)" -ForegroundColor Yellow
    }
}
