# Test MOVEit Web Admin with SSL certificate trust bypass
# This script tests both MOVEit primary and secondary Web Admin endpoints

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

function Test-MoveitWebAdmin {
    param(
        [string]$Hostname,
        [string]$Ip,
        [string]$Path
    )
    
    Write-Host "`nTesting $Hostname ($Ip)..." -ForegroundColor Yellow
    
    $url = "https://$Ip$Path"
    Write-Host "  URL: $url" -ForegroundColor Gray
    
    # Bypass certificate validation
    [System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}
    
    try {
        $webRequest = [System.Net.HttpWebRequest]::Create($url)
        $webRequest.Timeout = 5000
        $webRequest.AllowAutoRedirect = $false
        $webRequest.UserAgent = "Aegis-9-MOVEit-Discovery/1.0"
        
        $response = $webRequest.GetResponse()
        $statusCode = [int]$response.StatusCode
        $response.Close()
        
        Write-Host "  Status: $statusCode" -ForegroundColor Green
        return @{
            hostname = $Hostname
            ip = $Ip
            url = $url
            status = "reachable"
            statusCode = $statusCode
        }
    } catch {
        $errorResponse = $_.Exception.Response
        if ($errorResponse) {
            $statusCode = [int]$errorResponse.StatusCode
            Write-Host "  Status: $statusCode (HTTP error)" -ForegroundColor Red
            return @{
                hostname = $Hostname
                ip = $Ip
                url = $url
                status = "http_error"
                statusCode = $statusCode
                error = $_.Exception.Message
            }
        }
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
        return @{
            hostname = $Hostname
            ip = $Ip
            url = $url
            status = "error"
            error = $_.Exception.Message
        }
    }
}

$MoveitPrimary = "BSOAUTALB001"
$MoveitSecondary = "BSOAUTALB002"

# Test the URLs provided by user
$WebAdminUrls = @(
    "http://$MoveitPrimary/",
    "http://$MoveitSecondary/",
    "http://$MoveitPrimary/WebAdmin",
    "http://$MoveitSecondary/WebAdmin",
    "http://$MoveitPrimary/MOVEitAutomation",
    "http://$MoveitSecondary/MOVEitAutomation"
)

# Resolve hostnames
Write-Host "Resolving hostnames..." -ForegroundColor Cyan
$moveitPrimaryIp = Resolve-Hostname $MoveitPrimary
$moveitSecondaryIp = Resolve-Hostname $MoveitSecondary

# Test both servers
$results = @{
    timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    moveit = @{
        primary = @{
            hostname = $MoveitPrimary
            ip = $moveitPrimaryIp
            paths = @{}
        }
        secondary = @{
            hostname = $MoveitSecondary
            ip = $moveitSecondaryIp
            paths = @{}
        }
    }
}

foreach ($path in $WebAdminPaths) {
    Write-Host "`n=== Testing path: $path ===" -ForegroundColor Cyan
    
    $primaryResult = Test-MoveitWebAdmin -Hostname $MoveitPrimary -Ip $moveitPrimaryIp -Path $path
    $secondaryResult = Test-MoveitWebAdmin -Hostname $MoveitSecondary -Ip $moveitSecondaryIp -Path $path
    
    $results.moveit.primary.paths[$path] = $primaryResult
    $results.moveit.secondary.paths[$path] = $secondaryResult
}

# Save results
$results = @{
    timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    moveit = @{
        primary = $primaryResult
        secondary = $secondaryResult
    }
}

$outputFile = "storage/moveit-webadmin-test-$(Get-Date -Format 'yyyy-MM-dd').json"
$results | ConvertTo-Json -Depth 10 | Out-File -FilePath $outputFile -Encoding utf8

Write-Host "`nResults saved to: $outputFile" -ForegroundColor Green
