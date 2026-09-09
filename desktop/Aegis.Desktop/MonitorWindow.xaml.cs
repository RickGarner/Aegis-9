using System.Collections.ObjectModel;
using System.Windows;
using System.Windows.Media;
using System.Windows.Threading;

namespace Aegis.Desktop;

public enum MonitorWindowKind { MoveIt, ServerStatus, FreeFlow, Qualys }

public partial class MonitorWindow : Window
{
    private readonly MonitorWindowKind _kind;
    private readonly MonitoringClient _client = new("http://127.0.0.1:8000");
    private readonly DispatcherTimer _timer;
    private CancellationTokenSource? _refreshCancellation;
    private bool _refreshing;

    public MonitorWindow(MonitorWindowKind kind)
    {
        InitializeComponent();
        _kind = kind;
        _timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(kind is MonitorWindowKind.MoveIt or MonitorWindowKind.Qualys ? 300 : 60) };
        _timer.Tick += async (_, _) => await RefreshAsync();
        Loaded += async (_, _) => await RefreshAsync();
        Closed += (_, _) => { _timer.Stop(); _refreshCancellation?.Cancel(); };
        ConfigureView();
    }

    private void ConfigureView()
    {
        WindowTitleText.Text = _kind switch { MonitorWindowKind.MoveIt => "MOVEIT AUTOMATION", MonitorWindowKind.ServerStatus => "SERVER STATUS", MonitorWindowKind.FreeFlow => "XEROX FREEFLOW CORE", _ => "QUALYS VULNERABILITIES" };
        WindowSubtitleText.Text = _kind switch { MonitorWindowKind.MoveIt => "LIVE TASK CATALOG / FIVE MINUTE MONITOR", MonitorWindowKind.ServerStatus => "STARTER SERVER INVENTORY / RESOURCE AND SERVICE MONITOR", MonitorWindowKind.FreeFlow => "READ-ONLY JMF / PRIMARY AND BACKUP DISCOVERY", _ => "URGENT AND CRITICAL FINDINGS FIRST" };
        MoveItView.Visibility = _kind == MonitorWindowKind.MoveIt ? Visibility.Visible : Visibility.Collapsed;
        ServerView.Visibility = _kind == MonitorWindowKind.ServerStatus ? Visibility.Visible : Visibility.Collapsed;
        FreeFlowView.Visibility = _kind == MonitorWindowKind.FreeFlow ? Visibility.Visible : Visibility.Collapsed;
        QualysView.Visibility = _kind == MonitorWindowKind.Qualys ? Visibility.Visible : Visibility.Collapsed;
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
            var dashboardTask = _client.GetDashboardAsync(_refreshCancellation.Token);
            if (_kind == MonitorWindowKind.FreeFlow)
            {
                var discoveryTask = _client.GetFreeFlowDiscoveryAsync(_refreshCancellation.Token);
                var jobsTask = _client.GetFreeFlowJobsAsync(_refreshCancellation.Token);
                await Task.WhenAll(dashboardTask, discoveryTask, jobsTask);
                UpdateFreeFlow(await dashboardTask, await discoveryTask, await jobsTask);
            }
            else
            {
                var dashboard = await dashboardTask;
                switch (_kind) { case MonitorWindowKind.MoveIt: UpdateMoveIt(dashboard); break; case MonitorWindowKind.ServerStatus: UpdateServer(dashboard); break; case MonitorWindowKind.Qualys: UpdateQualys(dashboard); break; }
            }
            ConnectionText.Text = "CONNECTED";
            ConnectionText.Foreground = (TryFindResource("GreenBrush") as Brush) ?? Brushes.Green;
            LastUpdatedText.Text = $"Updated {DateTime.Now:HH:mm:ss}";
        }
        catch (OperationCanceledException) { }
        catch (Exception error)
        {
            ConnectionText.Text = "UNAVAILABLE";
            ConnectionText.Foreground = (TryFindResource("AmberBrush") as Brush) ?? Brushes.Orange;
            DetailText.Text = $"The A.E.G.I.S.-9 monitoring backend could not be reached: {error.Message}";
        }
        finally { _refreshing = false; _timer.Start(); }
    }

    private void UpdateMoveIt(MonitoringDashboard dashboard)
    {
        DetailText.Text = dashboard.MoveIt.Detail;
        MoveItTasksList.ItemsSource = dashboard.MoveIt.Tasks;
        MoveItLogsList.ItemsSource = dashboard.MoveIt.RecentLogs;
    }

    private void UpdateServer(MonitoringDashboard dashboard)
    {
        var server = dashboard.Server;
        DetailText.Text = $"{server.Detail} Live metrics are currently collected from the A.E.G.I.S.-9 host; remote agent feeds will populate the starter hosts when connected.";
        ServersList.ItemsSource = server.Servers;
    }

    private void UpdateFreeFlow(MonitoringDashboard dashboard, FreeFlowJmfDiscovery discovery, FreeFlowJmfJobs jobs)
    {
        var deviceRows = discovery.Servers.SelectMany(server => server.Devices.Select(device => new FreeFlowDeviceRow
        {
            Server = server.Name,
            Role = server.Role,
            Kind = device.Kind,
            DeviceId = device.DeviceId,
            DisplayName = string.IsNullOrWhiteSpace(device.DescriptiveName) ? device.DeviceId : device.DescriptiveName,
            Status = device.Status,
            Condition = device.Attributes.GetValueOrDefault("DeviceCondition", string.Empty),
            Details = device.Attributes.GetValueOrDefault("StatusDetails", device.ModelDescription)
        })).OrderBy(row => row.Kind).ThenBy(row => row.DisplayName).ThenBy(row => row.Server).ToList();
        var healthy = discovery.Servers.Count(server => server.State == "healthy");
        var workflowRows = deviceRows.Where(row => row.Kind == "workflow").ToList();
        var queueRows = deviceRows.Where(row => row.Kind == "queue").ToList();
        var printerRows = deviceRows.Where(row => row.Kind == "printer").ToList();
        var jobRows = jobs.Servers.SelectMany(server => server.Jobs.Select(job => new FreeFlowJobRow
        {
            Server = server.Name,
            Role = server.Role,
            QueueEntryId = job.QueueEntryId,
            Status = job.Status,
            StatusDetails = job.StatusDetails,
            Priority = job.Priority,
            SubmissionTime = job.SubmissionTime,
            StartTime = job.StartTime,
            EndTime = job.EndTime
        })).OrderByDescending(row => row.SubmissionTime).ThenByDescending(row => row.QueueEntryId).ToList();
        DetailText.Text = $"Read-only JMF: {healthy}/{discovery.Servers.Count} servers · {workflowRows.Count} workflows · {queueRows.Count} queues · {printerRows.Count} printers · {jobRows.Count} recent queue entries. Portal: {dashboard.FreeFlow.Status}.";
        FreeFlowJmfServersList.ItemsSource = discovery.Servers;
        FreeFlowWorkflowsList.ItemsSource = workflowRows;
        FreeFlowQueuesList.ItemsSource = queueRows;
        FreeFlowPrintersList.ItemsSource = printerRows;
        FreeFlowWorkflowCountText.Text = workflowRows.Count.ToString();
        FreeFlowQueueCountText.Text = queueRows.Count.ToString();
        FreeFlowPrinterCountText.Text = printerRows.Count.ToString();
        FreeFlowJobsList.ItemsSource = jobRows;
    }

    private void UpdateQualys(MonitoringDashboard dashboard)
    {
        DetailText.Text = $"{dashboard.Qualys.Detail} Urgent: {dashboard.Qualys.UrgentCount} · Critical: {dashboard.Qualys.CriticalCount} · Serious: {dashboard.Qualys.SeriousCount}";
        QualysFindingsList.ItemsSource = dashboard.Qualys.Findings;
    }

    private async void RefreshButton_Click(object sender, RoutedEventArgs e) => await RefreshAsync();
}
