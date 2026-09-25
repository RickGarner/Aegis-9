# View redirect test results

$json = Get-Content "storage\moveit-redirect-test-2026-09-23.json" | ConvertFrom-Json

Write-Host "`n=== MOVEit Redirect Test Results ===" -ForegroundColor Cyan

Write-Host "`n--- Primary Server ($($json.moveit.primary.hostname)) ---" -ForegroundColor Yellow
foreach ($url in $json.moveit.primary.urls.PSObject.Properties.Name) {
    $result = $json.moveit.primary.urls.$url
    Write-Host "`n  Source: $url" -ForegroundColor Gray
    if ($result.redirectLocation) {
        Write-Host "  Redirect to: $($result.redirectLocation)" -ForegroundColor Cyan
    }
    if ($result.statusCode) {
        Write-Host "  Status: $($result.statusCode)" -ForegroundColor Yellow
    }
}

Write-Host "`n--- Secondary Server ($($json.moveit.secondary.hostname)) ---" -ForegroundColor Yellow
foreach ($url in $json.moveit.secondary.urls.PSObject.Properties.Name) {
    $result = $json.moveit.secondary.urls.$url
    Write-Host "`n  Source: $url" -ForegroundColor Gray
    if ($result.redirectLocation) {
        Write-Host "  Redirect to: $($result.redirectLocation)" -ForegroundColor Cyan
    }
    if ($result.statusCode) {
        Write-Host "  Status: $($result.statusCode)" -ForegroundColor Yellow
    }
}
