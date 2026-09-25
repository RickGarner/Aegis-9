# Extract successful MOVEit paths
$json = Get-Content "storage\moveit-webadmin-http-2026-09-23.json" | ConvertFrom-Json

Write-Host "`n=== MOVEit HTTP Test Results ===" -ForegroundColor Cyan

Write-Host "`n--- Primary Server ($($json.moveit.primary.hostname)) ---" -ForegroundColor Yellow
Write-Host "IP: $($json.moveit.primary.ip)" -ForegroundColor Gray

foreach ($url in $json.moveit.primary.urls.PSObject.Properties.Name) {
    $result = $json.moveit.primary.urls.$url
    $color = if ($result.statusCode -eq 200) { 'Green' } elseif ($result.statusCode -eq 302) { 'Yellow' } else { 'Red' }
    Write-Host "  $url -> $($result.statusCode)" -ForegroundColor $color
}

Write-Host "`n--- Secondary Server ($($json.moveit.secondary.hostname)) ---" -ForegroundColor Yellow
Write-Host "IP: $($json.moveit.secondary.ip)" -ForegroundColor Gray

foreach ($url in $json.moveit.secondary.urls.PSObject.Properties.Name) {
    $result = $json.moveit.secondary.urls.$url
    $color = if ($result.statusCode -eq 200) { 'Green' } elseif ($result.statusCode -eq 302) { 'Yellow' } else { 'Red' }
    Write-Host "  $url -> $($result.statusCode)" -ForegroundColor $color
}
