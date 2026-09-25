# Follow MOVEit redirects to find actual Web Admin URL

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

function Test-HttpEndpointWithRedirect {
    param(
        [string]$Url
    )
    
    Write-Host "  Testing: $Url" -ForegroundColor Gray
    
    try {
        $webRequest = [System.Net.HttpWebRequest]::Create($Url)
        $webRequest.Timeout = 5000
        $webRequest.AllowAutoRedirect = $false  # Disable auto-redirect to capture it
        $webRequest.UserAgent = "Aegis-9-MOVEit-Discovery/1.0"
        
        $response = $webRequest.GetResponse()
        $statusCode = [int]$response.StatusCode
        $location = $response.Headers.Get("Location")
        $response.Close()
        
        Write-Host "  Status: $statusCode" -ForegroundColor Yellow
        if ($location) {
            Write-Host "  Redirect to: $location" -ForegroundColor Cyan
        }
        
        return @{
            url = $Url
            statusCode = $statusCode
            redirectLocation = $location
        }
    } catch {
        $errorResponse = $_.Exception.Response
        if ($errorResponse) {
            $statusCode = [int]$errorResponse.StatusCode
            Write-Host "  Status: $statusCode" -ForegroundColor Red
            return @{
                url = $Url
                statusCode = $statusCode
                error = $_.Exception.Message
            }
        }
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
        return @{
            url = $Url
            status = "error"
            error = $_.Exception.Message
        }
    }
}

$MoveitPrimary = "BSOAUTALB001"
$MoveitSecondary = "BSOAUTALB002"

# Resolve hostnames
Write-Host "Resolving hostnames..." -ForegroundColor Cyan
$moveitPrimaryIp = Resolve-Hostname $MoveitPrimary
$moveitSecondaryIp = Resolve-Hostname $MoveitSecondary

# Test URLs
$TestUrls = @(
    "http://$MoveitPrimary/",
    "http://$MoveitSecondary/",
    "http://$moveitPrimaryIp/",
    "http://$moveitSecondaryIp/",
    "http://$MoveitPrimary/WebAdmin",
    "http://$MoveitSecondary/WebAdmin",
    "http://$moveitPrimaryIp/WebAdmin",
    "http://$moveitSecondaryIp/WebAdmin"
)

# Test both servers
$results = @{
    timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    moveit = @{
        primary = @{
            hostname = $MoveitPrimary
            ip = $moveitPrimaryIp
            urls = @{}
        }
        secondary = @{
            hostname = $MoveitSecondary
            ip = $moveitSecondaryIp
            urls = @{}
        }
    }
}

foreach ($url in $TestUrls) {
    Write-Host "`n=== Testing: $url ===" -ForegroundColor Cyan
    
    if ($url -like "*$MoveitPrimary*" -or $url -like "*$moveitPrimaryIp*") {
        $result = Test-HttpEndpointWithRedirect -Url $url
        $results.moveit.primary.urls[$url] = $result
    } else {
        $result = Test-HttpEndpointWithRedirect -Url $url
        $results.moveit.secondary.urls[$url] = $result
    }
}

# Save results
$outputFile = "storage/moveit-redirect-test-$(Get-Date -Format 'yyyy-MM-dd').json"
$results | ConvertTo-Json -Depth 10 | Out-File -FilePath $outputFile -Encoding utf8

Write-Host "`nResults saved to: $outputFile" -ForegroundColor Green

# Print summary
Write-Host "`n=== REDIRECT SUMMARY ===" -ForegroundColor Cyan
Write-Host "`nPrimary Server:" -ForegroundColor Yellow
foreach ($url in $results.moveit.primary.urls.PSObject.Properties.Name) {
    $result = $results.moveit.primary.urls.$url
    if ($result.redirectLocation) {
        Write-Host "  $url" -ForegroundColor Gray
        Write-Host "    -> $($result.redirectLocation)" -ForegroundColor Cyan
    }
}

Write-Host "`nSecondary Server:" -ForegroundColor Yellow
foreach ($url in $results.moveit.secondary.urls.PSObject.Properties.Name) {
    $result = $results.moveit.secondary.urls.$url
    if ($result.redirectLocation) {
        Write-Host "  $url" -ForegroundColor Gray
        Write-Host "    -> $($result.redirectLocation)" -ForegroundColor Cyan
    }
}
