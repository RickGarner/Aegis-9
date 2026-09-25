# Test more MOVEit Web Admin URL variations

function Test-MoveitWebAdmin {
    param(
        [string]$Url
    )
    
    Write-Host "  Testing: $Url" -ForegroundColor Gray
    
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
        
        Write-Host "  Status: $statusCode" -ForegroundColor $(if ($statusCode -eq 200) { 'Green' } else { 'Red' })
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

Write-Host "`n=== Testing Additional MOVEit Web Admin URLs ===" -ForegroundColor Cyan

$TestUrls = @(
    "https://bsoautalb001/MOVEitAutomation/WebAdmin",
    "https://bsoautalb002/MOVEitAutomation/WebAdmin",
    "https://10.30.67.105/MOVEitAutomation/WebAdmin",
    "https://10.30.67.106/MOVEitAutomation/WebAdmin",
    "https://bsoautalb001/MOVEitAutomation/WebAdmin/",
    "https://bsoautalb002/MOVEitAutomation/WebAdmin/",
    "https://10.30.67.105/MOVEitAutomation/WebAdmin/",
    "https://10.30.67.106/MOVEitAutomation/WebAdmin/",
    "https://bsoautalb001/MOVEitAutomation/WebAdmin/default.aspx",
    "https://bsoautalb002/MOVEitAutomation/WebAdmin/default.aspx",
    "https://10.30.67.105/MOVEitAutomation/WebAdmin/default.aspx",
    "https://10.30.67.106/MOVEitAutomation/WebAdmin/default.aspx"
)

$results = @()

foreach ($url in $TestUrls) {
    Write-Host "`nTesting: $url" -ForegroundColor Yellow
    $result = Test-MoveitWebAdmin -Url $url
    $results += $result
}

$outputFile = "storage/moveit-webadmin-additional-$(Get-Date -Format 'yyyy-MM-dd').json"
$results | ConvertTo-Json | Out-File -FilePath $outputFile -Encoding utf8

Write-Host "`nResults saved to: $outputFile" -ForegroundColor Green
