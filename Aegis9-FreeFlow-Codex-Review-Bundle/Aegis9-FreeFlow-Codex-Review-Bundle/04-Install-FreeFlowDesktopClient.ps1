[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$RepoPath,
    [switch]$Apply,
    [switch]$ForceReplace
)

. (Join-Path $PSScriptRoot "Aegis9-FreeFlow.Common.ps1")

$repo = Resolve-AegisRepoPath -RepoPath $RepoPath
$project = Get-AegisDesktopProject -RepoPath $repo

if (-not $project) {
    throw "Could not uniquely identify the active WPF desktop project. Codex must identify it before this script is applied."
}

$projectDir = Split-Path -Parent $project
$ns = Get-AegisRootNamespace -ProjectFile $project
$target = Join-Path $projectDir "Integrations\FreeFlow"

$models = @"
// AEGIS_FREEFLOW_GENERATED_V1
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace $ns.Integrations.FreeFlow;

public sealed class FreeFlowStatus
{
    [JsonPropertyName("enabled")] public bool Enabled { get; set; }
    [JsonPropertyName("healthy")] public bool Healthy { get; set; }
    [JsonPropertyName("state")] public string? State { get; set; }
    [JsonPropertyName("base_url")] public string? BaseUrl { get; set; }
    [JsonPropertyName("latency_ms")] public double? LatencyMs { get; set; }
    [JsonPropertyName("device_count")] public int? DeviceCount { get; set; }
    [JsonPropertyName("status_query_enabled")] public bool StatusQueryEnabled { get; set; }
    [JsonPropertyName("mutations_enabled")] public bool MutationsEnabled { get; set; }
    [JsonPropertyName("error")] public string? Error { get; set; }
}

public sealed class FreeFlowDevice
{
    [JsonPropertyName("device_id")] public string? DeviceId { get; set; }
    [JsonPropertyName("descriptive_name")] public string? DescriptiveName { get; set; }
    [JsonPropertyName("device_type")] public string? DeviceType { get; set; }
    [JsonPropertyName("device_class")] public string? DeviceClass { get; set; }
    [JsonPropertyName("status")] public string? Status { get; set; }
    [JsonPropertyName("attributes")] public Dictionary<string, string> Attributes { get; set; } = new();
}

public sealed class FreeFlowDeviceList
{
    [JsonPropertyName("devices")] public List<FreeFlowDevice> Devices { get; set; } = new();
}

public sealed class FreeFlowWorkflowList
{
    [JsonPropertyName("workflows")] public List<FreeFlowDevice> Workflows { get; set; } = new();
}

public sealed class FreeFlowQueueList
{
    [JsonPropertyName("queues")] public List<FreeFlowDevice> Queues { get; set; } = new();
}

public sealed class FreeFlowJob
{
    [JsonPropertyName("queue_entry_id")] public string? QueueEntryId { get; set; }
    [JsonPropertyName("job_id")] public string? JobId { get; set; }
    [JsonPropertyName("job_name")] public string? JobName { get; set; }
    [JsonPropertyName("status")] public string? Status { get; set; }
    [JsonPropertyName("device_id")] public string? DeviceId { get; set; }
    [JsonPropertyName("attributes")] public Dictionary<string, string> Attributes { get; set; } = new();
}

public sealed class FreeFlowJobList
{
    [JsonPropertyName("supported")] public bool Supported { get; set; }
    [JsonPropertyName("reason")] public string? Reason { get; set; }
    [JsonPropertyName("jobs")] public List<FreeFlowJob> Jobs { get; set; } = new();
}
"@

$client = @"
// AEGIS_FREEFLOW_GENERATED_V1
using System;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading;
using System.Threading.Tasks;

namespace $ns.Integrations.FreeFlow;

/// <summary>
/// Read-only client for the AEGIS backend FreeFlow Core integration.
/// It intentionally does not expose job mutation methods.
/// </summary>
public sealed class FreeFlowClient
{
    private readonly HttpClient _http;

    public FreeFlowClient(HttpClient http)
    {
        _http = http ?? throw new ArgumentNullException(nameof(http));
    }

    public async Task<FreeFlowStatus?> GetStatusAsync(CancellationToken cancellationToken = default) =>
        await _http.GetFromJsonAsync<FreeFlowStatus>(
            "/api/integrations/freeflow/status", cancellationToken);

    public async Task<FreeFlowDeviceList?> GetDevicesAsync(CancellationToken cancellationToken = default) =>
        await _http.GetFromJsonAsync<FreeFlowDeviceList>(
            "/api/integrations/freeflow/devices", cancellationToken);

    public async Task<FreeFlowWorkflowList?> GetWorkflowsAsync(CancellationToken cancellationToken = default) =>
        await _http.GetFromJsonAsync<FreeFlowWorkflowList>(
            "/api/integrations/freeflow/workflows", cancellationToken);

    public async Task<FreeFlowQueueList?> GetQueuesAsync(CancellationToken cancellationToken = default) =>
        await _http.GetFromJsonAsync<FreeFlowQueueList>(
            "/api/integrations/freeflow/queues", cancellationToken);

    public async Task<FreeFlowJobList?> GetJobsAsync(CancellationToken cancellationToken = default) =>
        await _http.GetFromJsonAsync<FreeFlowJobList>(
            "/api/integrations/freeflow/jobs", cancellationToken);
}
"@

$readme = @"
# AEGIS FreeFlow Desktop Wiring

Generated for Codex review.

This folder contains only a self-contained API client and DTOs. The installer
does **not** edit MonitorWindow, view models, dependency injection, navigation,
or startup code because the current AEGIS desktop architecture is unavailable
to this bundle.

Codex should wire ``FreeFlowClient`` into the existing HTTP/client abstraction
rather than creating a second unrelated networking stack if AEGIS already has
one (for example ``MonitoringClient.cs``).

Recommended first UI:
- Integration status/health
- JMF latency
- discovered workflows
- discovered queues
- job panel only when backend ``supported=true``
- no mutation buttons in v1
"@

Write-AegisGeneratedFile -RepoPath $repo -Path (Join-Path $target "FreeFlowModels.cs") -Content $models -Apply:$Apply -ForceReplace:$ForceReplace
Write-AegisGeneratedFile -RepoPath $repo -Path (Join-Path $target "FreeFlowClient.cs") -Content $client -Apply:$Apply -ForceReplace:$ForceReplace
Write-AegisGeneratedFile -RepoPath $repo -Path (Join-Path $target "README-FreeFlow-Wiring.md") -Content $readme -Apply:$Apply -ForceReplace:$ForceReplace

if (-not $Apply) {
    Write-AegisWarn "Dry-run only. No desktop files were modified."
} else {
    Write-AegisOk "Desktop client scaffold installed. Codex must wire it into the current AEGIS UI/client conventions."
}
