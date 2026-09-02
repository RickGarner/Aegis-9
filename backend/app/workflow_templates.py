AD_ACCOUNT_LOCKOUT_IMPLEMENTATION = r'''A.E.G.I.S.-9 managed implementation for the approved AD Account Lockouts plan.

The artifact is intentionally read-only and performs one bounded collection pass. A.E.G.I.S.-9 owns repetition, cancellation, retained output, and presentation. Service-account exclusions must be supplied by configuration rather than inferred from an `admin` suffix.

```powershell
[CmdletBinding()]
param(
    [string]$Domain = 'bsoc.local',
    [ValidateRange(1, 168)]
    [int]$EventLookbackHours = 24,
    [string[]]$ServiceAccountNamePatterns = @('^svc[_-]', '^sa[_-]'),
    [string[]]$ServiceAccountGroups = @(),
    [ValidateRange(5, 120)]
    [int]$DomainControllerTimeoutSeconds = 30
)

$ErrorActionPreference = 'Stop'
Import-Module ActiveDirectory -ErrorAction Stop

function Get-EventDataMap {
    param([Parameter(Mandatory)]$EventRecord)
    $xml = [xml]$EventRecord.ToXml()
    $values = @{}
    foreach ($item in $xml.Event.EventData.Data) {
        if ($item.Name) { $values[[string]$item.Name] = [string]$item.'#text' }
    }
    return $values
}

function Test-IsExcludedServiceAccount {
    param(
        [Parameter(Mandatory)]$User,
        [string[]]$NamePatterns,
        [string[]]$ExcludedGroups
    )
    foreach ($pattern in $NamePatterns) {
        if ($pattern -and $User.SamAccountName -match $pattern) { return $true }
    }
    if ($ExcludedGroups.Count -eq 0) { return $false }
    $memberships = @($User.MemberOf | ForEach-Object { [string]$_ })
    foreach ($group in $ExcludedGroups) {
        if (-not $group) { continue }
        try {
            $groupDn = (Get-ADGroup -Identity $group -Server $Domain -ErrorAction Stop).DistinguishedName
            if ($memberships -contains $groupDn) { return $true }
        }
        catch {
            throw "Configured service-account exclusion group '$group' could not be resolved: $($_.Exception.Message)"
        }
    }
    return $false
}

$now = Get-Date
$startTime = $now.AddHours(-$EventLookbackHours)
$domainPolicy = Get-ADDefaultDomainPasswordPolicy -Server $Domain
$lockoutDuration = [TimeSpan]$domainPolicy.LockoutDuration
$domainControllers = @(Get-ADDomainController -Filter * -Server $Domain | Sort-Object HostName)
$lockedUsers = @(Search-ADAccount -LockedOut -UsersOnly -Server $Domain | ForEach-Object {
    Get-ADUser -Identity $_.DistinguishedName -Server $Domain -Properties GivenName,Surname,SamAccountName,LockedOut,lockoutTime,LastLogonDate,MemberOf,Enabled
} | Where-Object { $_.Enabled -and $_.LockedOut })

$results = foreach ($user in $lockedUsers) {
    if (Test-IsExcludedServiceAccount -User $user -NamePatterns $ServiceAccountNamePatterns -ExcludedGroups $ServiceAccountGroups) {
        continue
    }

    $lockoutEvents = @()
    $successfulLogons = @()
    $eventErrors = @()
    foreach ($controller in $domainControllers) {
        try {
            $events = @(Get-WinEvent -ComputerName $controller.HostName -FilterHashtable @{ LogName='Security'; Id=4740,4624; StartTime=$startTime } -ErrorAction Stop)
            foreach ($event in $events) {
                $data = Get-EventDataMap -EventRecord $event
                if ($data.TargetUserName -ine $user.SamAccountName) { continue }
                $record = [pscustomobject]@{
                    EventId = $event.Id
                    TimeCreated = $event.TimeCreated
                    ReportingDomainController = $controller.HostName
                    CallerComputerName = $data.CallerComputerName
                }
                if ($event.Id -eq 4740) { $lockoutEvents += $record }
                elseif ($event.Id -eq 4624) { $successfulLogons += $record }
            }
        }
        catch {
            $eventErrors += "$($controller.HostName): $($_.Exception.Message)"
        }
    }

    $latestLockout = $lockoutEvents | Sort-Object TimeCreated -Descending | Select-Object -First 1
    $latestSuccess = $successfulLogons | Sort-Object TimeCreated -Descending | Select-Object -First 1
    $lockoutTime = if ($latestLockout) { $latestLockout.TimeCreated } elseif ($user.lockoutTime) { [DateTime]::FromFileTimeUtc([Int64]$user.lockoutTime).ToLocalTime() } else { $null }
    $autoUnlockAt = if ($lockoutTime -and $lockoutDuration.TotalSeconds -gt 0) { $lockoutTime.Add($lockoutDuration) } else { $null }
    $countSinceSuccess = if ($latestSuccess) { @($lockoutEvents | Where-Object TimeCreated -gt $latestSuccess.TimeCreated).Count } else { @($lockoutEvents).Count }

    [pscustomobject]@{
        firstName = $user.GivenName
        lastName = $user.Surname
        username = $user.SamAccountName
        lockoutTime = if ($lockoutTime) { $lockoutTime.ToString('o') } else { $null }
        reportingDomainController = if ($latestLockout) { $latestLockout.ReportingDomainController } else { $null }
        originatingComputer = if ($latestLockout) { $latestLockout.CallerComputerName } else { $null }
        automaticUnlockAt = if ($autoUnlockAt) { $autoUnlockAt.ToString('o') } else { $null }
        secondsUntilAutomaticUnlock = if ($autoUnlockAt) { [Math]::Max(0, [int]($autoUnlockAt - $now).TotalSeconds) } else { $null }
        lockoutsSinceLastObservedSuccessfulLogon = $countSinceSuccess
        lastObservedSuccessfulLogon = if ($latestSuccess) { $latestSuccess.TimeCreated.ToString('o') } else { $null }
        eventLookbackHours = $EventLookbackHours
        eventQueryWarnings = $eventErrors
    }
}

[pscustomobject]@{
    schemaVersion = 1
    workflowType = 'ad-account-lockouts'
    collectedAt = $now.ToString('o')
    domain = $Domain
    lockedUserCount = @($results).Count
    users = @($results)
} | ConvertTo-Json -Depth 6 -Compress
```

Non-production validation plans:

1. Static validation: parse the extracted PowerShell artifact and verify its hash and permission manifest are retained. Pass when parsing succeeds with no syntax errors.
2. Disposable-domain functional validation: use test-only AD users and domain controllers with audited 4740/4624 events, configured service-account groups, and no production credentials. Pass when user filtering, event correlation, unlock timing, warning retention, and JSON schema match the fixtures.
'''
