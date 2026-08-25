using System.Net.Http;
using System.Net.Http.Json;
using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Jarvis.Desktop;

public sealed class MonitoringClient
{
    private readonly HttpClient _httpClient;
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
    };

    public MonitoringClient(string baseUrl)
    {
        _httpClient = new HttpClient { BaseAddress = new Uri(baseUrl.TrimEnd('/') + "/"), Timeout = TimeSpan.FromMinutes(3) };
    }

    public async Task<MonitoringDashboard> GetDashboardAsync(CancellationToken cancellationToken)
    {
        using var response = await _httpClient.GetAsync("api/monitoring", cancellationToken);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<MonitoringDashboard>(JsonOptions, cancellationToken)
            ?? throw new InvalidOperationException("Monitoring API returned an empty response.");
    }

    public async Task<bool> CheckHealthAsync(CancellationToken cancellationToken)
    {
        try
        {
            using var response = await _httpClient.GetAsync("health", cancellationToken);
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }

    public async Task<ProviderHealth> GetProviderHealthAsync(CancellationToken cancellationToken)
    {
        using var response = await _httpClient.GetAsync("api/provider/health", cancellationToken);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<ProviderHealth>(JsonOptions, cancellationToken)
            ?? throw new InvalidOperationException("Provider health API returned an empty response.");
    }

    public async Task<SystemHealth> GetSystemHealthAsync(CancellationToken cancellationToken)
    {
        using var response = await _httpClient.GetAsync("api/system/health", cancellationToken);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<SystemHealth>(JsonOptions, cancellationToken)
            ?? throw new InvalidOperationException("System health API returned an empty response.");
    }

    public async Task<SessionState> GetSessionAsync(CancellationToken cancellationToken)
    {
        using var response = await _httpClient.GetAsync("api/session", cancellationToken);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<SessionState>(JsonOptions, cancellationToken)
            ?? throw new InvalidOperationException("Session API returned an empty response.");
    }

    public async Task<ChatResponse> ChatAsync(IReadOnlyList<ChatMessage> messages, IReadOnlyList<int>? attachmentIds, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.PostAsJsonAsync("api/chat", new ChatRequest { Messages = messages, AttachmentIds = attachmentIds ?? [] }, JsonOptions, cancellationToken);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<ChatResponse>(JsonOptions, cancellationToken)
            ?? throw new InvalidOperationException("Chat API returned an empty response.");
    }

    public async Task<FileEntry> UploadFileAsync(string filePath, CancellationToken cancellationToken)
    {
        await using var stream = File.OpenRead(filePath);
        using var content = new MultipartFormDataContent();
        using var fileContent = new StreamContent(stream);
        content.Add(fileContent, "file", Path.GetFileName(filePath));
        using var response = await _httpClient.PostAsync("api/files/upload", content, cancellationToken);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<FileEntry>(JsonOptions, cancellationToken)
            ?? throw new InvalidOperationException("File upload API returned an empty response.");
    }

    public async Task<string> GetFileContentAsync(int fileId, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.GetAsync($"api/files/{fileId}/content", cancellationToken);
        response.EnsureSuccessStatusCode();
        var result = await response.Content.ReadFromJsonAsync<FileContent>(JsonOptions, cancellationToken);
        return result?.Content ?? string.Empty;
    }

    public async Task DeleteFileAsync(int fileId, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.DeleteAsync($"api/files/{fileId}", cancellationToken);
        response.EnsureSuccessStatusCode();
    }

    public async Task<MonitoringDashboard> ResolveAlertAsync(int alertId, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.PostAsync($"api/monitoring/alerts/{alertId}/resolve", null, cancellationToken);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<MonitoringDashboard>(JsonOptions, cancellationToken)
            ?? throw new InvalidOperationException("Alert resolution API returned an empty response.");
    }

    public async Task<List<Workflow>> GetWorkflowsAsync(CancellationToken cancellationToken)
    {
        using var response = await _httpClient.GetAsync("api/workflows", cancellationToken);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<List<Workflow>>(JsonOptions, cancellationToken) ?? [];
    }

    public async Task<Workflow> CreateWorkflowAsync(string title, string description, IReadOnlyList<int>? attachmentIds, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.PostAsJsonAsync("api/workflows", new WorkflowRequest { Title = title, Description = description, AttachmentIds = attachmentIds ?? [] }, JsonOptions, cancellationToken);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<Workflow>(JsonOptions, cancellationToken)
            ?? throw new InvalidOperationException("Workflow API returned an empty response.");
    }

    public async Task<Workflow> ApproveWorkflowAsync(int workflowId, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.PostAsync($"api/workflows/{workflowId}/approve", null, cancellationToken);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<Workflow>(JsonOptions, cancellationToken)
            ?? throw new InvalidOperationException("Workflow approval API returned an empty response.");
    }

    public async Task<WorkflowTransition> TransitionWorkflowAsync(int workflowId, string action, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.PostAsJsonAsync($"api/workflows/{workflowId}/actions", new WorkflowActionRequest { Action = action }, JsonOptions, cancellationToken);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<WorkflowTransition>(JsonOptions, cancellationToken)
            ?? throw new InvalidOperationException("Workflow action API returned an empty response.");
    }
}

public sealed class ChatMessage
{
    public string Role { get; set; } = string.Empty;
    public string Content { get; set; } = string.Empty;
}

public sealed class ChatRequest
{
    public IReadOnlyList<ChatMessage> Messages { get; set; } = [];
    [JsonPropertyName("attachment_ids")] public IReadOnlyList<int> AttachmentIds { get; set; } = [];
}

public sealed class ProviderHealth
{
    public bool Available { get; set; }
    public string Provider { get; set; } = string.Empty;
    public string Model { get; set; } = string.Empty;
    public string Detail { get; set; } = string.Empty;
}

public sealed class SystemHealth
{
    public List<ComponentHealth> Components { get; set; } = [];
}

public sealed class ComponentHealth
{
    public string Name { get; set; } = string.Empty;
    public bool Available { get; set; }
    public bool Configured { get; set; }
    public string Detail { get; set; } = string.Empty;
    public List<string> Models { get; set; } = [];
    public string Status => Available ? "UP" : "DOWN";
}

public sealed class FileEntry
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
    [JsonPropertyName("extracted_preview")] public string? ExtractedPreview { get; set; }
}

public sealed class FileContent
{
    public string? Content { get; set; }
}

public sealed class ChatResponse
{
    public string Model { get; set; } = string.Empty;
    public string Content { get; set; } = string.Empty;
}

public sealed class SessionState
{
    public List<ChatMessage> Messages { get; set; } = [];
    public List<ActivityLog> Activity { get; set; } = [];
    public List<FileEntry> Files { get; set; } = [];
    public ApprovalState Approval { get; set; } = new();
}

public sealed class ActivityLog
{
    [JsonPropertyName("created_at")] public string CreatedAt { get; set; } = string.Empty;
    [JsonPropertyName("event_type")] public string EventType { get; set; } = string.Empty;
    public string Message { get; set; } = string.Empty;
    public string Tone { get; set; } = "info";
}

public sealed class ApprovalState
{
    public string Decision { get; set; } = "pending";
}

public sealed class WorkflowRequest
{
    public string Title { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    [JsonPropertyName("attachment_ids")] public IReadOnlyList<int> AttachmentIds { get; set; } = [];
}

public sealed class WorkflowActionRequest
{
    public string Action { get; set; } = string.Empty;
}

public sealed class Workflow
{
    public int Id { get; set; }
    public string Title { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public string State { get; set; } = string.Empty;
    [JsonPropertyName("monitor_slot")] public int? MonitorSlot { get; set; }
}

public sealed class WorkflowTransition
{
    public Workflow Workflow { get; set; } = new();
    [JsonPropertyName("promoted_workflow")] public Workflow? PromotedWorkflow { get; set; }
}

public sealed class MonitoringDashboard
{
    [JsonPropertyName("generated_at")] public string GeneratedAt { get; set; } = string.Empty;
    [JsonPropertyName("moveit")] public MoveItMonitor MoveIt { get; set; } = new();
    [JsonPropertyName("server")] public ServerMonitor Server { get; set; } = new();
    [JsonPropertyName("alerts")] public List<MonitoringAlert> Alerts { get; set; } = [];
}

public sealed class MoveItMonitor
{
    public string Status { get; set; } = "unavailable";
    public string Adapter { get; set; } = string.Empty;
    public string Detail { get; set; } = string.Empty;
    public List<MoveItTask> Tasks { get; set; } = [];
    [JsonPropertyName("recent_logs")] public List<MoveItLogEntry> RecentLogs { get; set; } = [];
}

public sealed class MoveItTask
{
    public string Name { get; set; } = string.Empty;
    [JsonPropertyName("task_id")] public string TaskId { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    [JsonPropertyName("schedule_status")] public string ScheduleStatus { get; set; } = "Unknown";
    [JsonPropertyName("last_run_status")] public string LastRunStatus { get; set; } = "Unavailable";
    public string Status { get; set; } = string.Empty;
    public string Detail { get; set; } = string.Empty;
    [JsonPropertyName("last_run_at")] public string? LastRunAt { get; set; }
    [JsonPropertyName("log_url")] public string? LogUrl { get; set; }
}

public sealed class MoveItLogEntry
{
    [JsonPropertyName("task_name")] public string TaskName { get; set; } = string.Empty;
    [JsonPropertyName("captured_at")] public string CapturedAt { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
    [JsonPropertyName("log_url")] public string? LogUrl { get; set; }
    public string Detail { get; set; } = string.Empty;
}

public sealed class ServerMonitor
{
    public string Status { get; set; } = "unavailable";
    public string Detail { get; set; } = string.Empty;
    public List<ServerMetric> Metrics { get; set; } = [];
    [JsonPropertyName("stopped_automatic_services")] public List<ServerService> StoppedAutomaticServices { get; set; } = [];
    public List<ServerInventory> Servers { get; set; } = [];
    [JsonPropertyName("total_disk")] public string TotalDisk { get; set; } = "Unavailable";
    [JsonPropertyName("free_disk")] public string FreeDisk { get; set; } = "Unavailable";
}

public sealed class ServerInventory
{
    public string Name { get; set; } = string.Empty;
    public string Address { get; set; } = string.Empty;
    public string Role { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
    [JsonPropertyName("total_disk")] public string TotalDisk { get; set; } = "Unavailable";
    [JsonPropertyName("free_disk")] public string FreeDisk { get; set; } = "Unavailable";
    [JsonPropertyName("threshold_status")] public string ThresholdStatus { get; set; } = "Unavailable";
    public string Cpu { get; set; } = "Unavailable";
    public string Memory { get; set; } = "Unavailable";
    [JsonPropertyName("automatic_services")] public string AutomaticServices { get; set; } = "Unavailable";
    public string Data => "CPU, memory, disk, automatic services, filesystem audit";
}

public sealed class ServerMetric
{
    public string Key { get; set; } = string.Empty;
    public string Label { get; set; } = string.Empty;
    [JsonPropertyName("display_value")] public string DisplayValue { get; set; } = string.Empty;
}

public sealed class ServerService
{
    public string Name { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
    public string Detail { get; set; } = string.Empty;
}

public sealed class MonitoringAlert
{
    public int Id { get; set; }
    public string Source { get; set; } = string.Empty;
    public string Severity { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public string Detail { get; set; } = string.Empty;
}
