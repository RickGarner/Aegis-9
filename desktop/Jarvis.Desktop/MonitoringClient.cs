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
        if (!response.IsSuccessStatusCode)
        {
            var payload = await response.Content.ReadAsStringAsync(cancellationToken);
            var detail = payload;
            try
            {
                using var document = JsonDocument.Parse(payload);
                if (document.RootElement.TryGetProperty("detail", out var value)) detail = value.GetString() ?? payload;
            }
            catch (JsonException) { }
            throw new HttpRequestException($"Chat provider returned HTTP {(int)response.StatusCode}: {detail}");
        }
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

    public async Task<Workflow> GetWorkflowAsync(int workflowId, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.GetAsync($"api/workflows/{workflowId}", cancellationToken);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<Workflow>(JsonOptions, cancellationToken)
            ?? throw new InvalidOperationException("Workflow API returned an empty response.");
    }

    public async Task<byte[]> ExportWorkflowAsync(int workflowId, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.GetAsync($"api/workflows/{workflowId}/export", cancellationToken);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadAsByteArrayAsync(cancellationToken);
    }

    public async Task<WorkflowImportResult> ImportWorkflowAsync(string filePath, CancellationToken cancellationToken)
    {
        await using var stream = File.OpenRead(filePath);
        using var content = new MultipartFormDataContent();
        using var fileContent = new StreamContent(stream);
        content.Add(fileContent, "file", Path.GetFileName(filePath));
        using var response = await _httpClient.PostAsync("api/workflows/import", content, cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            var payload = await response.Content.ReadAsStringAsync(cancellationToken);
            throw new HttpRequestException($"Workflow import returned HTTP {(int)response.StatusCode}: {payload}");
        }
        return await response.Content.ReadFromJsonAsync<WorkflowImportResult>(JsonOptions, cancellationToken)
            ?? throw new InvalidOperationException("Workflow import API returned an empty response.");
    }

    public async Task<Workflow> CreateWorkflowAsync(string title, string description, IReadOnlyList<int>? attachmentIds, CancellationToken cancellationToken, string language = "powershell")
    {
        using var response = await _httpClient.PostAsJsonAsync("api/workflows", new WorkflowRequest { Title = title, Description = description, AttachmentIds = attachmentIds ?? [], Language = language }, JsonOptions, cancellationToken);
        await EnsureSuccessWithDetailAsync(response, "Workflow draft", cancellationToken);
        return await response.Content.ReadFromJsonAsync<Workflow>(JsonOptions, cancellationToken)
            ?? throw new InvalidOperationException("Workflow API returned an empty response.");
    }

    public async Task<Workflow> UpdateWorkflowAsync(int workflowId, WorkflowRequest request, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.PutAsJsonAsync($"api/workflows/{workflowId}", request, JsonOptions, cancellationToken);
        await EnsureSuccessWithDetailAsync(response, "Workflow update", cancellationToken);
        return await response.Content.ReadFromJsonAsync<Workflow>(JsonOptions, cancellationToken) ?? throw new InvalidOperationException("Workflow update returned an empty response.");
    }

    public async Task<Workflow> ReviewWorkflowAsync(int workflowId, string decision, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.PostAsJsonAsync($"api/workflows/{workflowId}/review", new { decision }, JsonOptions, cancellationToken);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<Workflow>(JsonOptions, cancellationToken) ?? throw new InvalidOperationException("Workflow review returned an empty response.");
    }

    public async Task<WorkflowTestResult> RunWorkflowTestAsync(int workflowId, string profile, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.PostAsJsonAsync($"api/workflows/{workflowId}/run-test", new { profile }, JsonOptions, cancellationToken);
        await EnsureSuccessWithDetailAsync(response, "Workflow test", cancellationToken);
        return await response.Content.ReadFromJsonAsync<WorkflowTestResult>(JsonOptions, cancellationToken)
            ?? throw new InvalidOperationException("Workflow test API returned an empty response.");
    }

    public async Task<Workflow> DesignWorkflowPlanAsync(int workflowId, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.PostAsync($"api/workflows/{workflowId}/design-plan", null, cancellationToken);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<Workflow>(JsonOptions, cancellationToken) ?? throw new InvalidOperationException("Workflow planning returned an empty response.");
    }

    public async Task<Workflow> GenerateWorkflowImplementationAsync(int workflowId, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.PostAsync($"api/workflows/{workflowId}/generate-implementation", null, cancellationToken);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<Workflow>(JsonOptions, cancellationToken) ?? throw new InvalidOperationException("Workflow implementation returned an empty response.");
    }

    public async Task<Workflow> AnswerWorkflowQuestionAsync(int workflowId, string questionId, string answer, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.PutAsJsonAsync($"api/workflows/{workflowId}/clarifications/{Uri.EscapeDataString(questionId)}", new { answer }, JsonOptions, cancellationToken);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<Workflow>(JsonOptions, cancellationToken) ?? throw new InvalidOperationException("Question submission returned an empty response.");
    }

    public async Task<Workflow> CompleteWorkflowDesignReviewAsync(int workflowId, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.PostAsync($"api/workflows/{workflowId}/complete-design-review", null, cancellationToken);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<Workflow>(JsonOptions, cancellationToken) ?? throw new InvalidOperationException("Draft re-evaluation returned an empty response.");
    }

    public async Task<Workflow> ScheduleWorkflowAsync(int workflowId, WorkflowSchedule schedule, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.PutAsJsonAsync($"api/workflows/{workflowId}/schedule", schedule, JsonOptions, cancellationToken);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<Workflow>(JsonOptions, cancellationToken) ?? throw new InvalidOperationException("Workflow schedule returned an empty response.");
    }

    public async Task<Workflow> ArchiveWorkflowAsync(int workflowId, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.DeleteAsync($"api/workflows/{workflowId}", cancellationToken);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<Workflow>(JsonOptions, cancellationToken) ?? throw new InvalidOperationException("Workflow archive returned an empty response.");
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

    public async Task<WorkflowRun> ExecuteWorkflowAsync(int workflowId, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.PostAsJsonAsync($"api/workflows/{workflowId}/execute", new { trigger = "manual" }, JsonOptions, cancellationToken);
        await EnsureSuccessWithDetailAsync(response, "Workflow execution", cancellationToken);
        return await response.Content.ReadFromJsonAsync<WorkflowRun>(JsonOptions, cancellationToken) ?? throw new InvalidOperationException("Workflow execution returned an empty response.");
    }

    public async Task<List<WorkflowRun>> GetWorkflowRunsAsync(int workflowId, CancellationToken cancellationToken)
        => await _httpClient.GetFromJsonAsync<List<WorkflowRun>>($"api/workflows/{workflowId}/runs", JsonOptions, cancellationToken) ?? [];

    public async Task<List<WorkflowRunEvent>> GetWorkflowRunEventsAsync(int runId, CancellationToken cancellationToken)
        => await _httpClient.GetFromJsonAsync<List<WorkflowRunEvent>>($"api/workflow-runs/{runId}/events", JsonOptions, cancellationToken) ?? [];

    public async Task<WorkflowRun> CancelWorkflowRunAsync(int runId, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.PostAsync($"api/workflow-runs/{runId}/cancel", null, cancellationToken);
        await EnsureSuccessWithDetailAsync(response, "Workflow cancellation", cancellationToken);
        return await response.Content.ReadFromJsonAsync<WorkflowRun>(JsonOptions, cancellationToken) ?? throw new InvalidOperationException("Workflow cancellation returned an empty response.");
    }

    public async Task<WorkflowRun> RetryWorkflowRunAsync(int runId, CancellationToken cancellationToken)
    {
        using var response = await _httpClient.PostAsync($"api/workflow-runs/{runId}/retry", null, cancellationToken);
        await EnsureSuccessWithDetailAsync(response, "Workflow retry", cancellationToken);
        return await response.Content.ReadFromJsonAsync<WorkflowRun>(JsonOptions, cancellationToken) ?? throw new InvalidOperationException("Workflow retry returned an empty response.");
    }

    private static async Task EnsureSuccessWithDetailAsync(HttpResponseMessage response, string operation, CancellationToken cancellationToken)
    {
        if (response.IsSuccessStatusCode) return;
        var payload = await response.Content.ReadAsStringAsync(cancellationToken);
        var detail = payload;
        try
        {
            using var document = JsonDocument.Parse(payload);
            if (document.RootElement.TryGetProperty("detail", out var value))
            {
                if (value.ValueKind == JsonValueKind.Array)
                {
                    detail = string.Join("; ", value.EnumerateArray().Select(item =>
                    {
                        var location = item.TryGetProperty("loc", out var loc) ? string.Join(".", loc.EnumerateArray().Select(part => part.ToString())) : "request";
                        var message = item.TryGetProperty("msg", out var msg) ? msg.GetString() : item.ToString();
                        return $"{location}: {message}";
                    }));
                }
                else detail = value.ToString();
            }
        }
        catch (JsonException) { }
        throw new HttpRequestException($"{operation} returned HTTP {(int)response.StatusCode}: {detail}");
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
    public string Location { get; set; } = string.Empty;
    public string Status { get; set; } = "initializing";
    public string Detail { get; set; } = string.Empty;
    public string? Recommendation { get; set; }
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
    public string Provider { get; set; } = string.Empty;
    public string Location { get; set; } = string.Empty;
    public ProviderFailover Failover { get; set; } = new();
}

public sealed class ProviderFailover
{
    public bool Occurred { get; set; }
    [JsonPropertyName("requires_acknowledgement")] public bool RequiresAcknowledgement { get; set; }
    [JsonPropertyName("previous_location")] public string PreviousLocation { get; set; } = string.Empty;
    [JsonPropertyName("previous_provider")] public string PreviousProvider { get; set; } = string.Empty;
    [JsonPropertyName("previous_model")] public string PreviousModel { get; set; } = string.Empty;
    [JsonPropertyName("active_location")] public string ActiveLocation { get; set; } = string.Empty;
    [JsonPropertyName("active_provider")] public string ActiveProvider { get; set; } = string.Empty;
    [JsonPropertyName("active_model")] public string ActiveModel { get; set; } = string.Empty;
    public string Reason { get; set; } = string.Empty;
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
    public string Language { get; set; } = "powershell";
}

public sealed class WorkflowActionRequest
{
    public string Action { get; set; } = string.Empty;
}

public sealed class Workflow
{
    public int Id { get; set; }
    [JsonPropertyName("transfer_id")] public string TransferId { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public string State { get; set; } = string.Empty;
    [JsonPropertyName("monitor_slot")] public int? MonitorSlot { get; set; }
    public string Language { get; set; } = "powershell";
    public int Revision { get; set; } = 1;
    [JsonPropertyName("approval_stage")] public string ApprovalStage { get; set; } = "draft";
    public Dictionary<string, JsonElement> Schedule { get; set; } = [];
    public bool Archived { get; set; }
    [JsonPropertyName("created_at")] public string CreatedAt { get; set; } = string.Empty;
    [JsonPropertyName("updated_at")] public string UpdatedAt { get; set; } = string.Empty;
    [JsonPropertyName("plan_text")] public string PlanText { get; set; } = string.Empty;
    [JsonPropertyName("plan_provider")] public string PlanProvider { get; set; } = string.Empty;
    [JsonPropertyName("plan_model")] public string PlanModel { get; set; } = string.Empty;
    [JsonPropertyName("implementation_text")] public string ImplementationText { get; set; } = string.Empty;
    [JsonPropertyName("implementation_provider")] public string ImplementationProvider { get; set; } = string.Empty;
    [JsonPropertyName("implementation_model")] public string ImplementationModel { get; set; } = string.Empty;
    [JsonPropertyName("clarification_questions")] public List<WorkflowClarificationQuestion> ClarificationQuestions { get; set; } = [];
    [JsonPropertyName("clarification_answers")] public Dictionary<string, string> ClarificationAnswers { get; set; } = [];
    [JsonPropertyName("artifact_sha256")] public string ArtifactSha256 { get; set; } = string.Empty;
    [JsonPropertyName("permission_manifest")] public Dictionary<string, JsonElement> PermissionManifest { get; set; } = [];
    [JsonPropertyName("latest_test_status")] public string LatestTestStatus { get; set; } = string.Empty;
    [JsonPropertyName("latest_test_evidence_sha256")] public string LatestTestEvidenceSha256 { get; set; } = string.Empty;
    [JsonPropertyName("latest_test_summary")] public string LatestTestSummary { get; set; } = string.Empty;
    [JsonPropertyName("supervisor_approved_by")] public string SupervisorApprovedBy { get; set; } = string.Empty;
    [JsonPropertyName("supervisor_approved_at")] public string? SupervisorApprovedAt { get; set; }
    [JsonPropertyName("supervisor_revision")] public int? SupervisorRevision { get; set; }
    [JsonPropertyName("supervisor_artifact_sha256")] public string SupervisorArtifactSha256 { get; set; } = string.Empty;
}

public sealed class WorkflowRun
{
    public int Id { get; set; }
    [JsonPropertyName("workflow_id")] public int WorkflowId { get; set; }
    public int Revision { get; set; }
    [JsonPropertyName("artifact_sha256")] public string ArtifactSha256 { get; set; } = string.Empty;
    public string Trigger { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
    public int Attempt { get; set; }
    [JsonPropertyName("requested_by")] public string RequestedBy { get; set; } = string.Empty;
    [JsonPropertyName("started_at")] public string StartedAt { get; set; } = string.Empty;
    [JsonPropertyName("completed_at")] public string? CompletedAt { get; set; }
    [JsonPropertyName("exit_code")] public int? ExitCode { get; set; }
    public string Stdout { get; set; } = string.Empty;
    public string Stderr { get; set; } = string.Empty;
    public string Error { get; set; } = string.Empty;
}

public sealed class WorkflowRunEvent
{
    public int Id { get; set; }
    [JsonPropertyName("run_id")] public int RunId { get; set; }
    public int Sequence { get; set; }
    [JsonPropertyName("event_type")] public string EventType { get; set; } = string.Empty;
    public string Message { get; set; } = string.Empty;
    [JsonPropertyName("created_at")] public string CreatedAt { get; set; } = string.Empty;
}

public sealed class WorkflowTestResult
{
    public Workflow Workflow { get; set; } = new();
    public WorkflowTestEvidence Evidence { get; set; } = new();
}

public sealed class WorkflowTestEvidence
{
    public string Profile { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
    [JsonPropertyName("artifact_sha256")] public string ArtifactSha256 { get; set; } = string.Empty;
    [JsonPropertyName("evidence_sha256")] public string EvidenceSha256 { get; set; } = string.Empty;
    public string Summary { get; set; } = string.Empty;
    public string Stdout { get; set; } = string.Empty;
    public string Stderr { get; set; } = string.Empty;
    [JsonPropertyName("duration_ms")] public int DurationMs { get; set; }
}

public sealed class WorkflowImportResult
{
    public string Action { get; set; } = string.Empty;
    public Workflow Workflow { get; set; } = new();
    public string Detail { get; set; } = string.Empty;
}

public sealed class WorkflowClarificationQuestion
{
    public string Id { get; set; } = string.Empty;
    public string Prompt { get; set; } = string.Empty;
    public bool Required { get; set; } = true;
    public List<string> Options { get; set; } = [];
}

public sealed class WorkflowSchedule
{
    public string Trigger { get; set; } = "recurring";
    public string Expression { get; set; } = string.Empty;
    public string Timezone { get; set; } = "America/New_York";
    public string Reason { get; set; } = string.Empty;
    [JsonPropertyName("start_conditions")] public string StartConditions { get; set; } = string.Empty;
    [JsonPropertyName("stop_conditions")] public string StopConditions { get; set; } = string.Empty;
    [JsonPropertyName("start_date")] public string StartDate { get; set; } = string.Empty;
    [JsonPropertyName("end_date")] public string EndDate { get; set; } = string.Empty;
    [JsonPropertyName("start_time")] public string StartTime { get; set; } = "00:00";
    [JsonPropertyName("end_time")] public string EndTime { get; set; } = "23:59";
    [JsonPropertyName("interval_value")] public int IntervalValue { get; set; } = 1;
    [JsonPropertyName("interval_unit")] public string IntervalUnit { get; set; } = "days";
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
    [JsonPropertyName("freeflow")] public FreeFlowMonitor FreeFlow { get; set; } = new();
    [JsonPropertyName("qualys")] public QualysMonitor Qualys { get; set; } = new();
    [JsonPropertyName("alerts")] public List<MonitoringAlert> Alerts { get; set; } = [];
}

public sealed class FreeFlowMonitor
{
    public string Status { get; set; } = "unavailable";
    public string Detail { get; set; } = string.Empty;
    public List<FreeFlowServer> Servers { get; set; } = [];
}

public sealed class FreeFlowServer
{
    public string Name { get; set; } = string.Empty;
    public string Role { get; set; } = string.Empty;
    [JsonPropertyName("web_url")] public string WebUrl { get; set; } = string.Empty;
    public string Status { get; set; } = "unavailable";
    [JsonPropertyName("http_status")] public int? HttpStatus { get; set; }
    [JsonPropertyName("response_ms")] public int? ResponseMs { get; set; }
    public string Detail { get; set; } = string.Empty;
}

public sealed class QualysMonitor
{
    public string Status { get; set; } = "unavailable";
    public string Detail { get; set; } = string.Empty;
    [JsonPropertyName("urgent_count")] public int UrgentCount { get; set; }
    [JsonPropertyName("critical_count")] public int CriticalCount { get; set; }
    [JsonPropertyName("serious_count")] public int SeriousCount { get; set; }
    public List<QualysFinding> Findings { get; set; } = [];
}

public sealed class QualysFinding
{
    public string Qid { get; set; } = string.Empty;
    public string Asset { get; set; } = string.Empty;
    public int Severity { get; set; }
    [JsonPropertyName("severity_label")] public string SeverityLabel { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    [JsonPropertyName("first_found_at")] public string? FirstFoundAt { get; set; }
    [JsonPropertyName("last_found_at")] public string? LastFoundAt { get; set; }
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
