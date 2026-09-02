using System.Windows;
using System.Windows.Media;
using System.Windows.Threading;

namespace Jarvis.Desktop;

public partial class WorkflowWindow : Window
{
    private readonly int _workflowId;
    private readonly MonitoringClient _client = new("http://127.0.0.1:8000");
    private readonly DispatcherTimer _timer;
    private CancellationTokenSource? _refreshCancellation;
    private Workflow? _workflow;
    private WorkflowRun? _latestRun;
    private bool _refreshing;

    public WorkflowWindow(int workflowId)
    {
        InitializeComponent();
        _workflowId = workflowId;
        _timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(15) };
        _timer.Tick += async (_, _) => await RefreshAsync();
        Loaded += async (_, _) => await RefreshAsync();
        Closed += (_, _) => { _timer.Stop(); _refreshCancellation?.Cancel(); };
    }

    private async Task RefreshAsync()
    {
        if (_refreshing) return;
        _refreshing = true;
        _refreshCancellation?.Cancel();
        _refreshCancellation = new CancellationTokenSource();
        try
        {
            ConnectionText.Text = "REFRESHING";
            var workflows = await _client.GetWorkflowsAsync(_refreshCancellation.Token);
            _workflow = workflows.FirstOrDefault(item => item.Id == _workflowId);
            if (_workflow is null)
            {
                TitleText.Text = "Workflow unavailable";
                StateText.Text = "MISSING";
                ResultText.Text = "This workflow no longer exists in the local supervisor.";
                return;
            }

            TitleText.Text = _workflow.Title;
            DescriptionText.Text = _workflow.Description;
            StateText.Text = _workflow.State.ToUpperInvariant();
            PlacementText.Text = _workflow.MonitorSlot is null ? "Queued or awaiting approval" : $"Assigned monitor slot {_workflow.MonitorSlot}";
            ConnectionText.Text = "CONNECTED";
            ConnectionText.Foreground = FindResource("Green") as Brush;
            UpdatedText.Text = $"Updated {DateTime.Now:HH:mm:ss}";
            var runs = await _client.GetWorkflowRunsAsync(_workflow.Id, _refreshCancellation.Token);
            _latestRun = runs.FirstOrDefault();
            if (_latestRun is null)
            {
                ResultText.Text = $"Revision {_workflow.Revision}. Test: {_workflow.LatestTestStatus}. Supervisor: {(string.IsNullOrWhiteSpace(_workflow.SupervisorApprovedBy) ? "not approved" : _workflow.SupervisorApprovedBy)}.";
            }
            else
            {
                var events = await _client.GetWorkflowRunEventsAsync(_latestRun.Id, _refreshCancellation.Token);
                var live = string.Join(Environment.NewLine, events.TakeLast(40).Select(item => $"[{item.Sequence:000}] {item.EventType}: {item.Message}"));
                ResultText.Text = $"Run {_latestRun.Id} · {_latestRun.Status.ToUpperInvariant()} · attempt {_latestRun.Attempt}{Environment.NewLine}{live}";
            }
        }
        catch (OperationCanceledException) { }
        catch (Exception error)
        {
            ConnectionText.Text = "UNAVAILABLE";
            ConnectionText.Foreground = FindResource("Amber") as Brush;
            ResultText.Text = $"The Jarvis workflow backend could not be reached: {error.Message}";
        }
        finally
        {
            _refreshing = false;
            _timer.Start();
        }
    }

    private async Task TransitionAsync(string action)
    {
        if (_workflow is null) return;
        try
        {
            var transition = await _client.TransitionWorkflowAsync(_workflow.Id, action, CancellationToken.None);
            _workflow = transition.Workflow;
            ResultText.Text = $"Workflow {action} requested. Current state: {_workflow.State}.";
            await RefreshAsync();
        }
        catch (Exception error)
        {
            ResultText.Text = $"Workflow {action} was not accepted: {error.Message}";
        }
    }

    private async void RefreshButton_Click(object sender, RoutedEventArgs e) => await RefreshAsync();
    private async void ApproveButton_Click(object sender, RoutedEventArgs e)
    {
        if (_workflow is null) return;
        new WorkflowApprovalWindow(_workflow) { Owner = this }.ShowDialog();
        await RefreshAsync();
    }
    private async void ScheduleButton_Click(object sender, RoutedEventArgs e)
    {
        if (_workflow is null) return;
        new WorkflowScheduleWindow(_workflow) { Owner = this }.ShowDialog();
        await RefreshAsync();
    }
    private async void PauseButton_Click(object sender, RoutedEventArgs e) => await TransitionAsync("pause");
    private async void ResumeButton_Click(object sender, RoutedEventArgs e) => await TransitionAsync("resume");
    private async void StopButton_Click(object sender, RoutedEventArgs e) => await TransitionAsync("stop");
    private async void RunButton_Click(object sender, RoutedEventArgs e)
    {
        if (_workflow is null) return;
        if (MessageBox.Show(this, "Run the exact supervisor-approved artifact now? Approval and action policy will be revalidated before launch.", "Confirm workflow run", MessageBoxButton.YesNo, MessageBoxImage.Warning) != MessageBoxResult.Yes) return;
        try { _latestRun = await _client.ExecuteWorkflowAsync(_workflow.Id, CancellationToken.None); await RefreshAsync(); }
        catch (Exception error) { ResultText.Text = error.Message; }
    }
    private async void CancelRunButton_Click(object sender, RoutedEventArgs e)
    {
        if (_latestRun is null) return;
        try { _latestRun = await _client.CancelWorkflowRunAsync(_latestRun.Id, CancellationToken.None); await RefreshAsync(); }
        catch (Exception error) { ResultText.Text = error.Message; }
    }
    private async void RetryRunButton_Click(object sender, RoutedEventArgs e)
    {
        if (_latestRun is null) return;
        try { _latestRun = await _client.RetryWorkflowRunAsync(_latestRun.Id, CancellationToken.None); await RefreshAsync(); }
        catch (Exception error) { ResultText.Text = error.Message; }
    }
}
