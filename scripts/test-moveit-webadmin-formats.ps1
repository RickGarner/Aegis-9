# Test MOVEit Web Admin with various URL formats including hash fragments

function Test-MoveitWebAdmin {
    param(
        [string]$Url
    )
    
    Write-Host "  Testing: $Url" -ForegroundColor Gray
    
    # Bypass certificate validation (for HTTPS)
    [System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}
    
    try {
        $webRequest = [System.Net.HttpWebRequest]::Create($Url)
        $webRequest.Timeout = 5000
        $webRequest.AllowAutoRedirect = $false
        $webRequest.UserAgent = "Aegis-9-MOVEit-Discovery/1.0"
        
        $response = $webRequest.GetResponse()
        $statusCode = [int]$response.StatusCode
        $location = $response.Headers.Get("Location")
        $response.Close()
        
        Write-Host "  Status: $statusCode" -ForegroundColor Green
        if ($location) {
            Write-Host "  Redirect to: $location" -ForegroundColor Cyan
        }
        
        return @{
            url = $Url
            status = "reachable"
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

Write-Host "`n=== Testing MOVEit Web Admin URL Formats ===" -ForegroundColor Cyan

# Test various URL formats
$TestUrls = @(
    "https://bsoautalb001/",
    "https://bsoautalb002/",
    "https://10.30.67.105/",
    "https://10.30.67.106/",
    "https://bsoautalb001/WebAdmin",
    "https://bsoautalb002/WebAdmin",
    "https://10.30.67.105/WebAdmin",
    "https://10.30.67.106/WebAdmin",
    "https://bsoautalb001/MOVEitAutomation",
    "https://bsoautalb002/MOVEitAutomation",
    "https://10.30.67.105/MOVEitAutomation",
    "https://10.30.67.106/MOVEitAutomation"
)

$results = @()

foreach ($url in $TestUrls) {
    Write-Host "`nTesting: $url" -ForegroundColor Yellow
    $result = Test-MoveitWebAdmin -Url $url
    $results += $result
}

# Save results
$outputFile = "storage/moveit-webadmin-formats-$(Get-Date -Format 'yyyy-MM-dd').json"
$results | ConvertTo-Json | Out-File -FilePath $outputFile -Encoding utf8

Write-Host "`nResults saved to: $outputFile" -ForegroundColor Green
