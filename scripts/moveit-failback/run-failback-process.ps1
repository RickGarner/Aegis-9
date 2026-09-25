# MOVEit HA Automated Fail-Back Process
# Main orchestration script for automated fail-back

param(
    [string]$Password = $env:AEGIS_MOVEIT_PASSWORD,
    [string]$OriginalPrimary = "bsoautalb001",
    [string]$CurrentPrimary = "bsoautalb002",
    [switch]$DryRun,
    [switch]$AutoApprove
)

if ([string]::IsNullOrWhiteSpace($Password)) { throw 'Set AEGIS_MOVEIT_PASSWORD or supply -Password before running this script.' }

$securePassword = $Password | ConvertTo-SecureString -AsPlainText -Force

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MOVEit HA Automated Fail-Back Process" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Original Primary: $OriginalPrimary" -ForegroundColor Yellow
Write-Host "Current Primary: $CurrentPrimary" -ForegroundColor Yellow
Write-Host "Mode: $(if($DryRun){"DRY RUN"}else{"PRODUCTION"})" -ForegroundColor Yellow
Write-Host ""

# Step 1: Detect current primary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Step 1: Detect Current Primary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$detectScript = Join-Path $PSScriptRoot "detect-primary.ps1"
$primaryInfo = & $detectScript -Password $Password -OriginalPrimary $OriginalPrimary -CurrentPrimary $CurrentPrimary

$currentPrimary = $primaryInfo.CurrentPrimary
Write-Host "Detected Current Primary: $currentPrimary" -ForegroundColor $(if($currentPrimary -eq $CurrentPrimary){"Green"}else{"Yellow"})
Write-Host ""

# Step 2: Check original primary availability
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Step 2: Check Original Primary Availability" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$availabilityScript = Join-Path $PSScriptRoot "check-primary-availability.ps1"
$availability = & $availabilityScript -Password $Password -OriginalPrimary $OriginalPrimary -SecondaryServer $CurrentPrimary

if (-not $availability.Available) {
    Write-Host ""
    Write-Host "ERROR: Original primary ($OriginalPrimary) is not available for fail-back" -ForegroundColor Red
    Write-Host "Cannot proceed with fail-back until original primary is accessible" -ForegroundColor Red
    Write-Host ""
    $availability | ConvertTo-Json -Depth 10
    exit 1
}

Write-Host "Original primary ($OriginalPrimary) is available for fail-back" -ForegroundColor Green
Write-Host ""

# Step 3: Validate prerequisites
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Step 3: Validate Prerequisites" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$prereqsScript = Join-Path $PSScriptRoot "validate-failback-prereqs.ps1"
$validation = & $prereqsScript -Password $Password -OriginalPrimary $OriginalPrimary -CurrentPrimary $CurrentPrimary

if (-not $validation.Valid) {
    Write-Host ""
    Write-Host "ERROR: Prerequisites not met for fail-back" -ForegroundColor Red
    Write-Host "Cannot proceed until all prerequisites are satisfied" -ForegroundColor Red
    Write-Host ""
    $validation | ConvertTo-Json -Depth 10
    exit 1
}

Write-Host "All prerequisites validated successfully" -ForegroundColor Green
Write-Host ""

# Step 4: Get approval (unless auto-approve)
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Step 4: Approval" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
    Write-Host "[DRY RUN] Skipping approval in dry run mode" -ForegroundColor Yellow
    Write-Host ""
} elseif ($AutoApprove) {
    Write-Host "[AUTO-APPROVE] Proceeding without manual approval" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "WARNING: This operation will initiate a fail-back from $CurrentPrimary to $OriginalPrimary" -ForegroundColor Red
    Write-Host "This may cause brief service interruption during the fail-back process" -ForegroundColor Red
    Write-Host ""
    $response = Read-Host "Do you want to proceed with fail-back? (yes/no)"
    
    if ($response -ne "yes") {
        Write-Host "Fail-back cancelled by user" -ForegroundColor Yellow
        exit 0
    }
    Write-Host ""
}

# Step 5: Execute fail-back
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Step 5: Execute Fail-Back" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
    Write-Host "[DRY RUN] Would execute fail-back command on $CurrentPrimary" -ForegroundColor Yellow
    Write-Host "[DRY RUN] Command: Invoke-RestMethod -Uri 'https://$CurrentPrimary/api/v1/ha/failback' -Method Post" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "[DRY RUN] Fail-back would be initiated" -ForegroundColor Yellow
} else {
    Write-Host "Initiating fail-back from $CurrentPrimary to $OriginalPrimary..." -ForegroundColor Yellow
    
    try {
        # Note: The actual fail-back command depends on MOVEit HA API
        # This is a placeholder - you'll need to insert the actual MOVEit HA fail-back command
        # Common approaches:
        # 1. MOVEit HA API endpoint (if available)
        # 2. PowerShell command on current primary
        # 3. SQL command on database server
        
        # Example using MOVEit HA API (if available):
        # $failbackResponse = Invoke-RestMethod -Uri "https://$CurrentPrimary/api/v1/ha/failback" -Method Post -Credential $cred
        
        # Example using PowerShell on current primary:
        # Invoke-Command -ComputerName $CurrentPrimary -Credential $currentCred -ScriptBlock {
        #     # MOVEit HA fail-back command (placeholder - replace with actual command)
        #     Start-Sleep -Seconds 5  # Wait for any pending operations to complete
        #     # Add actual fail-back command here
        # }
        
        Write-Host "  ⚠ FAIL-BACK COMMAND NOT IMPLEMENTED" -ForegroundColor Yellow
        Write-Host "  The actual fail-back command needs to be inserted based on your MOVEit HA configuration" -ForegroundColor Yellow
        Write-Host "  Common options:" -ForegroundColor Yellow
        Write-Host "    1. MOVEit HA API endpoint (if available)" -ForegroundColor Yellow
        Write-Host "    2. PowerShell command on current primary" -ForegroundColor Yellow
        Write-Host "    3. SQL command on database server" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  Please update this script with the appropriate fail-back command" -ForegroundColor Yellow
    } catch {
        Write-Host "ERROR: Failed to initiate fail-back: $($_.Exception.Message)" -ForegroundColor Red
        $validation | ConvertTo-Json -Depth 10
        exit 1
    }
}

Write-Host ""

# Step 6: Validate fail-back success
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Step 6: Validate Fail-Back Success" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
    Write-Host "[DRY RUN] Would validate fail-back by:" -ForegroundColor Yellow
    Write-Host "  1. Detecting new primary server" -ForegroundColor Yellow
    Write-Host "  2. Verifying Web Admin accessible on $OriginalPrimary" -ForegroundColor Yellow
    Write-Host "  3. Checking MOVEit services on $OriginalPrimary" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "Waiting for fail-back to complete..." -ForegroundColor Yellow
    Write-Host "(In production, add wait logic and polling here)" -ForegroundColor Yellow
    Write-Host ""
    
    # Re-detect primary after fail-back
    Write-Host "Re-detecting primary server..." -ForegroundColor Yellow
    $postFailbackInfo = & $detectScript -Password $Password -OriginalPrimary $OriginalPrimary -CurrentPrimary $CurrentPrimary
    
    if ($postFailbackInfo.CurrentPrimary -eq $OriginalPrimary) {
        Write-Host "✓ Fail-back successful! $OriginalPrimary is now the acting primary" -ForegroundColor Green
    } else {
        Write-Host "✗ Fail-back may have failed. Current primary is still: $($postFailbackInfo.CurrentPrimary)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fail-Back Process Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Output summary
$summary = @{
    Status = "COMPLETED"
    OriginalPrimary = $OriginalPrimary
    CurrentPrimary = $CurrentPrimary
    NewPrimary = if($DryRun) { $OriginalPrimary } else { $postFailbackInfo.CurrentPrimary }
    DryRun = $DryRun.IsPresent
    Timestamp = Get-Date -Format "o"
}

$summary | ConvertTo-Json -Depth 5
