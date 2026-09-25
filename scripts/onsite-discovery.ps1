# Onsite Discovery Script for MOVEit HA and FreeFlow Core
param(
    [string]$MoveitPrimary = "BSOAUTALB001",
    [string]$MoveitSecondary = "BSOAUTALB002",
    [string]$FreeflowPrimary = "BSOXERALB001",
    [string]$FreeflowSecondary = "BSOXERALB002"
)

$ErrorActionPreference = "Continue"
$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffffffzzz"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "ON-SITE DISCOVERY - $timestamp" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Helper function to resolve hostname
function Resolve-Hostname {
    param([string]$Hostname)
    try {
        $ip = [System.Net.Dns]::GetHostEntry($Hostname).AddressList[0].IPAddressToString
        Write-Host "  Resolved $Hostname to $ip" -ForegroundColor Gray
        return $ip
    } catch {
        Write-Host "  DNS resolution failed for $Hostname" -ForegroundColor Yellow
        return $Hostname
    }
}

# Helper function to check TCP port
function Test-TcpPort {
    param([string]$Hostname, [int]$Port, [int]$Timeout = 3000)
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $asyncResult = $tcpClient.BeginConnect($Hostname, $Port, $null, $null)
        $completed = $asyncResult.AsyncWaitHandle.WaitOne($Timeout, $false)
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

# Helper function to check HTTP endpoint
function Test-HttpEndpoint {
    param([string]$Url, [int]$Timeout = 5000)
    try {
        $webRequest = [System.Net.HttpWebRequest]::Create($Url)
        $webRequest.Timeout = $Timeout
        $webRequest.AllowAutoRedirect = $false
        $webRequest.UserAgent = "Aegis-9-Onsite-Discovery/1.0"
        
        $response = $webRequest.GetResponse()
        $statusCode = [int]$response.StatusCode
        $response.Close()
        
        return @{ statusCode=$statusCode; success=$true }
    } catch {
        $errorResponse = $_.Exception.Response
        if ($errorResponse) {
            $statusCode = [int]$errorResponse.StatusCode
            return @{ statusCode=$statusCode; success=$false; error=$_.Exception.Message }
        }
        return @{ success=$false; error=$_.Exception.Message }
    }
}

# Check MOVEit
Write-Host "Checking MOVEit Web Admin endpoints..." -ForegroundColor Cyan

$moveitPrimaryIp = Resolve-Hostname $MoveitPrimary
$moveitSecondaryIp = Resolve-Hostname $MoveitSecondary

$moveitPrimaryWebAdmin = $null
$moveitSecondaryWebAdmin = $null

# Check primary
$portOpen = Test-TcpPort $moveitPrimaryIp 443 3000
if ($portOpen) {
    Write-Host "  ${MoveitPrimary}: Port 443 OPEN" -ForegroundColor Green
    $webAdminUrl = "https://$moveitPrimaryIp/WebAdmin/"
    $webAdminResult = Test-HttpEndpoint $webAdminUrl 5000
    $moveitPrimaryWebAdmin = @{
        url = $webAdminUrl
        portOpen = $portOpen
        httpStatus = $webAdminResult.statusCode
        reachable = $webAdminResult.success
        detail = if ($webAdminResult.success) { "HTTP $($webAdminResult.statusCode)" } else { $webAdminResult.error }
    }
    if ($webAdminResult.success -and $webAdminResult.statusCode -eq 200) {
        Write-Host "    Web Admin: REACHABLE (HTTP 200)" -ForegroundColor Green
    } else {
        Write-Host "    Web Admin: $($webAdminResult.error)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ${MoveitPrimary}: Port 443 CLOSED" -ForegroundColor Red
    $moveitPrimaryWebAdmin = @{
        url = "https://$moveitPrimaryIp/WebAdmin/"
        portOpen = $false
        httpStatus = $null
        reachable = $false
        detail = "Port 443 closed"
    }
}

# Check secondary
$portOpen = Test-TcpPort $moveitSecondaryIp 443 3000
if ($portOpen) {
    Write-Host "  ${MoveitSecondary}: Port 443 OPEN" -ForegroundColor Green
    $webAdminUrl = "https://$moveitSecondaryIp/WebAdmin/"
    $webAdminResult = Test-HttpEndpoint $webAdminUrl 5000
    $moveitSecondaryWebAdmin = @{
        url = $webAdminUrl
        portOpen = $portOpen
        httpStatus = $webAdminResult.statusCode
        reachable = $webAdminResult.success
        detail = if ($webAdminResult.success) { "HTTP $($webAdminResult.statusCode)" } else { $webAdminResult.error }
    }
    if ($webAdminResult.success -and $webAdminResult.statusCode -eq 200) {
        Write-Host "    Web Admin: REACHABLE (HTTP 200)" -ForegroundColor Green
    } else {
        Write-Host "    Web Admin: $($webAdminResult.error)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ${MoveitSecondary}: Port 443 CLOSED" -ForegroundColor Red
    $moveitSecondaryWebAdmin = @{
        url = "https://$moveitSecondaryIp/WebAdmin/"
        portOpen = $false
        httpStatus = $null
        reachable = $false
        detail = "Port 443 closed"
    }
}

# Check FreeFlow
Write-Host ""
Write-Host "Checking FreeFlow JMF endpoints..." -ForegroundColor Cyan

$freeflowPrimaryIp = Resolve-Hostname $FreeflowPrimary
$freeflowSecondaryIp = Resolve-Hostname $FreeflowSecondary

$freeflowPrimaryJmf = $null
$freeflowSecondaryJmf = $null

# Check primary
$portOpen = Test-TcpPort $freeflowPrimaryIp 7751 3000
if ($portOpen) {
    Write-Host "  ${FreeflowPrimary}: Port 7751 OPEN" -ForegroundColor Green
    $jmfUrl = "http://$freeflowPrimaryIp:7751/FreeFlowCore/"
    $jmfResult = Test-HttpEndpoint $jmfUrl 5000
    $freeflowPrimaryJmf = @{
        url = $jmfUrl
        portOpen = $portOpen
        httpStatus = $jmfResult.statusCode
        reachable = $jmfResult.success
        detail = if ($jmfResult.success) { "HTTP $($jmfResult.statusCode)" } else { $jmfResult.error }
    }
    if ($jmfResult.success) {
        Write-Host "    JMF: REACHABLE (HTTP $($jmfResult.statusCode))" -ForegroundColor Green
    } else {
        Write-Host "    JMF: $($jmfResult.error)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ${FreeflowPrimary}: Port 7751 CLOSED" -ForegroundColor Red
    $freeflowPrimaryJmf = @{
        url = "http://$freeflowPrimaryIp:7751/FreeFlowCore/"
        portOpen = $false
        httpStatus = $null
        reachable = $false
        detail = "Port 7751 closed"
    }
}

# Check secondary
$portOpen = Test-TcpPort $freeflowSecondaryIp 7751 3000
if ($portOpen) {
    Write-Host "  ${FreeflowSecondary}: Port 7751 OPEN" -ForegroundColor Green
    $jmfUrl = "http://$freeflowSecondaryIp:7751/FreeFlowCore/"
    $jmfResult = Test-HttpEndpoint $jmfUrl 5000
    $freeflowSecondaryJmf = @{
        url = $jmfUrl
        portOpen = $portOpen
        httpStatus = $jmfResult.statusCode
        reachable = $jmfResult.success
        detail = if ($jmfResult.success) { "HTTP $($jmfResult.statusCode)" } else { $jmfResult.error }
    }
    if ($jmfResult.success) {
        Write-Host "    JMF: REACHABLE (HTTP $($jmfResult.statusCode))" -ForegroundColor Green
    } else {
        Write-Host "    JMF: $($jmfResult.error)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ${FreeflowSecondary}: Port 7751 CLOSED" -ForegroundColor Red
    $freeflowSecondaryJmf = @{
        url = "http://$freeflowSecondaryIp:7751/FreeFlowCore/"
        portOpen = $false
        httpStatus = $null
        reachable = $false
        detail = "Port 7751 closed"
    }
}

# Check Windows services
Write-Host ""
Write-Host "Checking Windows services..." -ForegroundColor Cyan

$allServices = @{}

foreach ($server in @($MoveitPrimary, $MoveitSecondary)) {
    if ($server -eq $MoveitPrimary) {
        $serverIp = $moveitPrimaryIp
    } else {
        $serverIp = $moveitSecondaryIp
    }
    
    try {
        $services = Get-Service -ComputerName $serverIp -Name "MoveIt*" -ErrorAction SilentlyContinue
        if ($services) {
            foreach ($svc in $services) {
                $allServices["${server}/${svc.Name}"] = @{
                    hostname = $server
                    service_name = $svc.Name
                    display_name = $svc.DisplayName
                    service_running = ($svc.Status -eq "Running")
                    detail = "Status: $($svc.Status)"
                }
                $statusColor = if ($svc.Status -eq "Running") { "Green" } else { "Yellow" }
                Write-Host "  ${server}/${svc.Name}: $($svc.Status)" -ForegroundColor $statusColor
            }
        }
    } catch {
        Write-Host "  ${server}: Service enumeration failed - $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

foreach ($server in @($FreeflowPrimary, $FreeflowSecondary)) {
    if ($server -eq $FreeflowPrimary) {
        $serverIp = $freeflowPrimaryIp
    } else {
        $serverIp = $freeflowSecondaryIp
    }
    
    try {
        $services = Get-Service -ComputerName $serverIp -Name "*FreeFlow*" -ErrorAction SilentlyContinue
        if ($services) {
            foreach ($svc in $services) {
                $allServices["${server}/${svc.Name}"] = @{
                    hostname = $server
                    service_name = $svc.Name
                    display_name = $svc.DisplayName
                    service_running = ($svc.Status -eq "Running")
                    detail = "Status: $($svc.Status)"
                }
                $statusColor = if ($svc.Status -eq "Running") { "Green" } else { "Yellow" }
                Write-Host "  ${server}/${svc.Name}: $($svc.Status)" -ForegroundColor $statusColor
            }
        }
    } catch {
        Write-Host "  ${server}: Service enumeration failed - $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Save results
$outputFile = "storage\onsite-discovery-$(Get-Date -Format 'yyyy-MM-dd').json"
$outputDir = Split-Path $outputFile -Parent
if ($outputDir -and $outputDir -ne ".") {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

$results = @{
    timestamp = $timestamp
    moveit = @{
        primary = @{
            hostname = $MoveitPrimary
            ip = $moveitPrimaryIp
            webAdmin = $moveitPrimaryWebAdmin
        }
        secondary = @{
            hostname = $MoveitSecondary
            ip = $moveitSecondaryIp
            webAdmin = $moveitSecondaryWebAdmin
        }
    }
    freeflow = @{
        primary = @{
            hostname = $FreeflowPrimary
            ip = $freeflowPrimaryIp
            jmf = $freeflowPrimaryJmf
        }
        secondary = @{
            hostname = $FreeflowSecondary
            ip = $freeflowSecondaryIp
            jmf = $freeflowSecondaryJmf
        }
    }
    services = $allServices
}

$outputPath = Join-Path (Get-Location) $outputFile
$outputPath = $outputPath -replace '\\', '/'

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Discovery results saved to: $outputPath" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Save to JSON
$results | ConvertTo-Json -Depth 10 | Set-Content -Path $outputPath -Encoding UTF8

# Also save to storage directory
$storageDir = Join-Path (Split-Path (Get-Location) -Parent) "storage"
if (-not (Test-Path $storageDir)) {
    New-Item -ItemType Directory -Path $storageDir -Force | Out-Null
}

$storageOutput = Join-Path $storageDir (Split-Path $outputPath -Leaf)
Copy-Item $outputPath $storageOutput -Force

Write-Host "Also saved to: $storageOutput" -ForegroundColor Gray
