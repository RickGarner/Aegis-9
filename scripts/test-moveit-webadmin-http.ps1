# Test MOVEit Web Admin with HTTP (no SSL)
# Based on user-provided URLs: http://bsoautalb001/ and http://bsoautalb002/

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

function Test-HttpEndpoint {
    param(
        [string]$Url
    )
    
    Write-Host "  Testing: $Url" -ForegroundColor Gray
    
    try {
        $webRequest = [System.Net.HttpWebRequest]::Create($Url)
        $webRequest.Timeout = 5000
        $webRequest.AllowAutoRedirect = $false
        $webRequest.UserAgent = "Aegis-9-MOVEit-Discovery/1.0"
        
        $response = $webRequest.GetResponse()
        $statusCode = [int]$response.StatusCode
        $response.Close()
        
        Write-Host "  Status: $statusCode" -ForegroundColor Green
        return @{
            url = $Url
            status = "reachable"
            statusCode = $statusCode
        }
    } catch {
        $errorResponse = $_.Exception.Response
        if ($errorResponse) {
            $statusCode = [int]$errorResponse.StatusCode
            Write-Host "  Status: $statusCode" -ForegroundColor Red
            return @{
                url = $Url
                status = "http_error"
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

# Test URLs provided by user
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
        $result = Test-HttpEndpoint -Url $url
        $results.moveit.primary.urls[$url] = $result
    } else {
        $result = Test-HttpEndpoint -Url $url
        $results.moveit.secondary.urls[$url] = $result
    }
}

$outputFile = "storage/moveit-webadmin-http-$(Get-Date -Format 'yyyy-MM-dd').json"
$results | ConvertTo-Json -Depth 10 | Out-File -FilePath $outputFile -Encoding utf8

Write-Host "`nResults saved to: $outputFile" -ForegroundColor Green
