# Extract successful MOVEit paths
$json = Get-Content "storage\moveit-webadmin-test-2026-09-22.json" | ConvertFrom-Json

Write-Host "`n=== Successful Paths ===" -ForegroundColor Green

Write-Host "`nPrimary Server ($($json.moveit.primary.hostname)):" -ForegroundColor Yellow
foreach ($path in $json.moveit.primary.paths.PSObject.Properties.Name) {
    $result = $json.moveit.primary.paths.$path
    if ($result.statusCode -eq 200) {
        Write-Host "  ✓ $path" -ForegroundColor Green
    }
}

Write-Host "`nSecondary Server ($($json.moveit.secondary.hostname)):" -ForegroundColor Yellow
foreach ($path in $json.moveit.secondary.paths.PSObject.Properties.Name) {
    $result = $json.moveit.secondary.paths.$path
    if ($result.statusCode -eq 200) {
        Write-Host "  ✓ $path" -ForegroundColor Green
    }
}

Write-Host "`n=== All Results Summary ===" -ForegroundColor Cyan
Write-Host "`nPrimary Server:" -ForegroundColor Yellow
foreach ($path in $json.moveit.primary.paths.PSObject.Properties.Name) {
    $result = $json.moveit.primary.paths.$path
    $color = if ($result.statusCode -eq 200) { 'Green' } else { 'Red' }
    Write-Host "  $path -> $($result.statusCode)" -ForegroundColor $color
}

Write-Host "`nSecondary Server:" -ForegroundColor Yellow
foreach ($path in $json.moveit.secondary.paths.PSObject.Properties.Name) {
    $result = $json.moveit.secondary.paths.$path
    $color = if ($result.statusCode -eq 200) { 'Green' } else { 'Red' }
    Write-Host "  $path -> $($result.statusCode)" -ForegroundColor $color
}
