using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Windows;
using Microsoft.Win32;

namespace Aegis.Desktop;

public partial class TestLabWindow : Window
{
    private readonly MonitoringClient _client;
    private readonly Dictionary<string, string> _files = [];
    private TestLabPlan? _plan;
    private TestLabPackage? _package;

    public TestLabWindow(MonitoringClient client) { _client = client; InitializeComponent(); }

    private void SelectSource_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog { Filter = "Supported source (*.ps1;*.psm1;*.cs;*.csproj)|*.ps1;*.psm1;*.cs;*.csproj|All files (*.*)|*.*" };
        if (dialog.ShowDialog(this) != true) return;
        var info = new FileInfo(dialog.FileName);
        if (info.Length > 500_000) { MessageBox.Show(this, "The selected file exceeds the 500 KB Test Lab limit.", "Test Lab", MessageBoxButton.OK, MessageBoxImage.Warning); return; }
        _files.Clear(); _files[info.Name] = File.ReadAllText(info.FullName); SourcePathText.Text = info.FullName; SourceText.Text = _files[info.Name];
        _plan = null; _package = null; PlanText.Clear(); ApproveButton.IsEnabled = false; LaunchButton.IsEnabled = false; EvidenceButton.IsEnabled = false; StatusText.Text = "Source copied for review. Create a plan before approval.";
    }

    private async void CreatePlan_Click(object sender, RoutedEventArgs e)
    {
        if (_files.Count == 0) { MessageBox.Show(this, "Select a source file first."); return; }
        try {
            StatusText.Text = "A.E.G.I.S. is reviewing source and generating synthetic tests locally…";
            _plan = await _client.CreateTestLabPlanAsync(_files, UseAiCheckBox.IsChecked == true, CancellationToken.None);
            PlanText.Text = FormatPlan(_plan); ApproveButton.IsEnabled = true; LaunchButton.IsEnabled = false; StatusText.Text = "Plan ready. Review every finding and synthetic case before approval.";
        } catch (Exception error) { StatusText.Text = $"Plan failed: {error.Message}"; }
    }

    private async void ApprovePackage_Click(object sender, RoutedEventArgs e)
    {
        if (_plan is null) return;
        if (MessageBox.Show(this, $"Approve plan {_plan.Id} with {_plan.Risk.ToUpperInvariant()} assessed risk? This creates a package but does not run it.", "Approve Test Lab Plan", MessageBoxButton.YesNo, MessageBoxImage.Warning) != MessageBoxResult.Yes) return;
        try { _package = await _client.CreateTestLabPackageAsync(_files, _plan, CancellationToken.None); LaunchButton.IsEnabled = true; EvidenceButton.IsEnabled = true; ApproveButton.IsEnabled = false; StatusText.Text = $"Package ready: {_package.PackagePath}"; }
        catch (Exception error) { StatusText.Text = $"Package failed: {error.Message}"; }
    }

    private void LaunchSandbox_Click(object sender, RoutedEventArgs e)
    {
        if (_package is null) return;
        var executable = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "System32", "WindowsSandbox.exe");
        if (!File.Exists(executable)) { MessageBox.Show(this, "Windows Sandbox is not installed or enabled. The package was retained without executing code.", "Test Lab", MessageBoxButton.OK, MessageBoxImage.Error); return; }
        if (MessageBox.Show(this, "Launch the disposable sandbox now? Network, clipboard, writable host source, and production credentials remain disabled.", "Final Test Lab Approval", MessageBoxButton.YesNo, MessageBoxImage.Warning) != MessageBoxResult.Yes) return;
        try { Process.Start(new ProcessStartInfo(executable, $"\"{_package.ConfigurationPath}\"") { UseShellExecute = true }); StatusText.Text = $"Sandbox launched. When it finishes, review the signed-input evidence file."; LaunchButton.IsEnabled = false; }
        catch (Exception error) { StatusText.Text = $"Sandbox launch failed safely: {error.Message}"; }
    }

    private void ReviewEvidence_Click(object sender, RoutedEventArgs e)
    {
        if (_package is null) return;
        var evidencePath = Path.Combine(_package.PackagePath, "output", "evidence.json");
        if (!File.Exists(evidencePath)) { MessageBox.Show(this, "Evidence is not available yet. Finish and close the sandbox, then try again.", "Test Lab Evidence", MessageBoxButton.OK, MessageBoxImage.Information); return; }
        try {
            using var parsed = JsonDocument.Parse(File.ReadAllText(evidencePath));
            PlanText.Text = JsonSerializer.Serialize(parsed.RootElement, new JsonSerializerOptions { WriteIndented = true });
            StatusText.Text = $"Evidence loaded from {evidencePath}";
        } catch (Exception error) { StatusText.Text = $"Evidence could not be validated: {error.Message}"; }
    }

    private static string FormatPlan(TestLabPlan plan)
    {
        var findings = plan.Findings.Count == 0 ? "No deterministic high-risk pattern found (not a safety guarantee)." : string.Join("\n", plan.Findings.Select(item => $"[{item.Risk.ToUpperInvariant()}] {item.Category}\n  {item.Evidence}\n  CONTROL: {item.Control}"));
        var cases = string.Join("\n\n", plan.TestCases.Select(item => $"{item.Name}: {item.Purpose}\nINPUT: {JsonSerializer.Serialize(item.SyntheticInput)}\nEXPECTED: {item.Expected}"));
        return $"PLAN {plan.Id}\nLANGUAGE: {plan.Language}\nRISK: {plan.Risk.ToUpperInvariant()}\nAI: {plan.AiStatus}\n\nENFORCED: network=false, clipboard=false, hostWrite=false, credentials=false\n\nFINDINGS\n{findings}\n\nSYNTHETIC TESTS\n{cases}";
    }
}
