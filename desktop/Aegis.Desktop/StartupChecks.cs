using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace Aegis.Desktop;

public enum StartupCheckState { Pending, Running, Passed, Warning, Failed }

public sealed class StartupCheckResult
{
    public required string Id { get; init; }
    public required string Name { get; init; }
    public StartupCheckState State { get; set; } = StartupCheckState.Pending;
    public string Detail { get; set; } = "Awaiting verification";
    public string Resolution { get; set; } = string.Empty;
    public long DurationMs { get; set; }
    public bool Critical { get; init; }
}

public sealed class StartupState
{
    public List<StartupCheckResult> Checks { get; } = [];
    public ProviderHealth? Provider { get; set; }
    public PolicyIntegrityStatus? Policy { get; set; }
    public SystemHealth? System { get; set; }
    public bool Degraded { get; set; }
    public bool CanContinue => Checks.All(x => x.State is StartupCheckState.Passed or StartupCheckState.Warning);
    public StartupCheckResult? Failure => Checks.FirstOrDefault(x => x.State == StartupCheckState.Failed);
}

public sealed class StartupCoordinator
{
    private readonly MonitoringClient _client;
    private readonly Func<CancellationToken, Task<(bool Ready, string Detail)>> _runtimeGate;

    public StartupCoordinator(MonitoringClient client, Func<CancellationToken, Task<(bool Ready, string Detail)>> runtimeGate)
    {
        _client = client;
        _runtimeGate = runtimeGate;
    }

    public event Action<StartupCheckResult>? CheckChanged;

    public StartupState CreateState()
    {
        var state = new StartupState();
        state.Checks.AddRange([
            New("runtime", "Backend runtime", true), New("api", "Command API", true),
            New("provider", "AI provider route", true), New("policy", "Security policy integrity", true),
            New("system", "System dependencies", false), New("avatar", "AEGIS AO model", false)]);
        return state;
    }

    public async Task RunAsync(StartupState state, CancellationToken token)
    {
        var runtime = await ExecuteAsync(state, "runtime", async checkToken => { var r = await _runtimeGate(checkToken); return (r.Ready, r.Detail, "Verify Python/backend files and inspect backend logs."); }, token);
        if (!runtime) return;
        if (!await ExecuteAsync(state, "api", async checkToken => (await _client.CheckHealthAsync(checkToken), "Local command API responded.", "Confirm port 8000 is available and restart A.E.G.I.S.-9."), token)) return;
        if (!await ExecuteAsync(state, "provider", async checkToken => { state.Provider = await _client.GetProviderHealthAsync(checkToken); return (state.Provider.Available && state.Provider.Status == "ready", state.Provider.Detail.Length > 0 ? state.Provider.Detail : $"{state.Provider.Provider} / {state.Provider.Model}", state.Provider.Recommendation ?? "Configure and start at least one supported AI provider."); }, token)) return;
        if (!await ExecuteAsync(state, "policy", async checkToken => { state.Policy = await _client.GetPolicyIntegrityAsync(checkToken); var known = state.Policy.Status is "verified" or "healthy" or "ok" or "local"; var valid = known && !state.Policy.DriftDetected; var detail = state.Policy.DriftDetected ? "Policy drift was detected." : !known ? "Policy service returned an unrecognized or misconfigured state." : state.Policy.SignatureRequired ? "Signed policy baseline verified." : "Unsigned local policy baseline accepted by the policy service."; return (valid, detail, "Restore or configure the approved policy baseline and restart the backend."); }, token)) return;
        await ExecuteAsync(state, "system", async checkToken => { state.System = await _client.GetSystemHealthAsync(checkToken); var unavailable = state.System.Components.Where(x => !x.Available).ToList(); return (true, unavailable.Count == 0 ? "All reported components are available." : $"{unavailable.Count} optional component(s) unavailable: {string.Join(", ", unavailable.Select(x => x.Name))}", "Review component configuration in Settings."); }, token, warningWhenDetailContains: "unavailable");
        await ExecuteAsync(state, "avatar", _ => { var a = new AvatarAssetCatalog().GetSelection(UserPreferences.Load().AvatarProfile); return Task.FromResult((true, a.IsAvailable ? $"{a.Manifest?.DisplayName ?? "Local avatar"} assets verified." : $"Native fallback active. {a.Detail}", "Install WebView2 and verify local avatar assets.")); }, token, warningWhenDetailContains: "fallback");
    }

    private async Task<bool> ExecuteAsync(StartupState state, string id, Func<CancellationToken, Task<(bool Ok, string Detail, string Resolution)>> action, CancellationToken token, string? warningWhenDetailContains = null)
    {
        var check = state.Checks.Single(x => x.Id == id); check.State = StartupCheckState.Running; check.Detail = "Verification in progress…"; CheckChanged?.Invoke(check);
        var watch = Stopwatch.StartNew();
        try
        {
            using var deadline = CancellationTokenSource.CreateLinkedTokenSource(token); deadline.CancelAfter(TimeSpan.FromSeconds(check.Id == "runtime" ? 35 : 15));
            var result = await action(deadline.Token).WaitAsync(deadline.Token);
            check.Detail = Sanitize(result.Detail); check.Resolution = result.Resolution;
            check.State = !result.Ok ? StartupCheckState.Failed : warningWhenDetailContains != null && check.Detail.Contains(warningWhenDetailContains, StringComparison.OrdinalIgnoreCase) ? StartupCheckState.Warning : StartupCheckState.Passed;
        }
        catch (OperationCanceledException) when (!token.IsCancellationRequested) { check.State = check.Critical ? StartupCheckState.Failed : StartupCheckState.Warning; check.Detail = "Verification timed out before a trusted result was returned."; check.Resolution = "Confirm the local service is responsive, review its logs, and retry startup."; }
        catch (OperationCanceledException) { check.State = check.Critical ? StartupCheckState.Failed : StartupCheckState.Warning; check.Detail = "Verification was cancelled by the operator."; check.Resolution = "Restart A.E.G.I.S.-9 to run the readiness sequence again."; }
        catch (Exception ex) { check.State = check.Critical ? StartupCheckState.Failed : StartupCheckState.Warning; check.Detail = Sanitize(ex.Message); check.Resolution = "Review the diagnostic report and relevant local service logs."; }
        finally { check.DurationMs = watch.ElapsedMilliseconds; CheckChanged?.Invoke(check); }
        return check.State != StartupCheckState.Failed;
    }

    private static StartupCheckResult New(string id, string name, bool critical) => new() { Id = id, Name = name, Critical = critical };
    internal static string Sanitize(string value)
    {
        if (string.IsNullOrWhiteSpace(value)) return "No detail was returned.";
        var safe = value.Replace(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "%USERPROFILE%", StringComparison.OrdinalIgnoreCase);
        safe = Regex.Replace(safe, @"(?im)(authorization\s*[:=]\s*)[^\r\n]+", "$1[REDACTED]");
        safe = Regex.Replace(safe, @"(?i)bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [REDACTED]");
        safe = Regex.Replace(safe, @"(?i)\b(token|api[_-]?key|secret|password|credential)\s*[:=]\s*([^\s,;]+)", "$1=[REDACTED]");
        safe = Regex.Replace(safe, "(?i)\\\"(token|api[_-]?key|secret|password|credential)\\\"\\s*:\\s*\\\"[^\\\"]*\\\"", "\"$1\":\"[REDACTED]\"");
        return safe.Length > 500 ? safe[..500] + "…" : safe;
    }
}

public static class StartupDiagnosticWriter
{
    public static string Write(StartupState state, string? backendDirectory, string? pythonExecutable)
    {
        var directory = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Aegis-9", "logs");
        Directory.CreateDirectory(directory);
        var path = Path.Combine(directory, $"startup-diagnostic-{DateTime.Now:yyyyMMdd-HHmmss}.json");
        var payload = new { generatedUtc = DateTime.UtcNow, degraded = state.Degraded, runtime = new { backendDirectory = StartupCoordinator.Sanitize(backendDirectory ?? "external"), pythonExecutable = Path.GetFileName(pythonExecutable), framework = Environment.Version.ToString() }, checks = state.Checks.Select(x => new { x.Id, x.Name, state = x.State.ToString(), detail = StartupCoordinator.Sanitize(x.Detail), resolution = StartupCoordinator.Sanitize(x.Resolution), x.DurationMs, x.Critical }), backendLogs = backendDirectory == null ? null : new { stdout = Path.Combine(backendDirectory, "logs", "backend.stdout.log"), stderr = Path.Combine(backendDirectory, "logs", "backend.stderr.log") } };
        File.WriteAllText(path, JsonSerializer.Serialize(payload, new JsonSerializerOptions { WriteIndented = true }));
        return path;
    }
}
