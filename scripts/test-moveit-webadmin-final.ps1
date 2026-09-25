# Test MOVEit Web Admin at the redirect destination URLs

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

Write-Host "`n=== Testing MOVEit Web Admin at Redirect Destinations ===" -ForegroundColor Cyan

$TestUrls = @(
    "https://10.30.67.105/WebAdmin",
    "https://10.30.67.106/WebAdmin",
    "https://bsoautalb001/WebAdmin",
    "https://bsoautalb002/WebAdmin"
)

$results = @()

foreach ($url in $TestUrls) {
    Write-Host "`nTesting: $url" -ForegroundColor Yellow
    $result = Test-MoveitWebAdmin -Url $url
    $results += $result
}

# Save results
$outputFile = "storage/moveit-webadmin-final-$(Get-Date -Format 'yyyy-MM-dd').json"
$results | ConvertTo-Json | Out-File -FilePath $outputFile -Encoding utf8

Write-Host "`nResults saved to: $outputFile" -ForegroundColor Green
