# View MOVEit Web Admin test results
$json = Get-Content "storage\moveit-webadmin-test-2026-09-22.json" | ConvertFrom-Json

Write-Host "`n=== MOVEit Web Admin Test Results ===" -ForegroundColor Cyan
Write-Host "Timestamp: $($json.timestamp)" -ForegroundColor Gray

Write-Host "`n--- Primary Server ($($json.moveit.primary.hostname)) ---" -ForegroundColor Yellow
Write-Host "IP: $($json.moveit.primary.ip)" -ForegroundColor Gray

foreach ($path in $json.moveit.primary.paths.PSObject.Properties.Name) {
    $result = $json.moveit.primary.paths.$path
    Write-Host "`n  Path: $path" -ForegroundColor Gray
    Write-Host "  Status: $($result.status)" -ForegroundColor $(if ($result.statusCode -eq 200) { 'Green' } else { 'Red' })
    Write-Host "  HTTP Code: $($result.statusCode)" -ForegroundColor Gray
    if ($result.error) {
        Write-Host "  Error: $($result.error)" -ForegroundColor Red
    }
}

Write-Host "`n--- Secondary Server ($($json.moveit.secondary.hostname)) ---" -ForegroundColor Yellow
Write-Host "IP: $($json.moveit.secondary.ip)" -ForegroundColor Gray

foreach ($path in $json.moveit.secondary.paths.PSObject.Properties.Name) {
    $result = $json.moveit.secondary.paths.$path
    Write-Host "`n  Path: $path" -ForegroundColor Gray
    Write-Host "  Status: $($result.status)" -ForegroundColor $(if ($result.statusCode -eq 200) { 'Green' } else { 'Red' })
    Write-Host "  HTTP Code: $($result.statusCode)" -ForegroundColor Gray
    if ($result.error) {
        Write-Host "  Error: $($result.error)" -ForegroundColor Red
    }
}
