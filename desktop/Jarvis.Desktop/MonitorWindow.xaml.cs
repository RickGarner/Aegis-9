using System.Collections.ObjectModel;
using System.Windows;
using System.Windows.Media;
using System.Windows.Threading;

namespace Jarvis.Desktop;

public enum MonitorWindowKind { MoveIt, ServerStatus }

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
        _timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(kind == MonitorWindowKind.MoveIt ? 300 : 60) };
        _timer.Tick += async (_, _) => await RefreshAsync();
        Loaded += async (_, _) => await RefreshAsync();
        Closed += (_, _) => { _timer.Stop(); _refreshCancellation?.Cancel(); };
        ConfigureView();
    }

    private void ConfigureView()
    {
        var moveIt = _kind == MonitorWindowKind.MoveIt;
        WindowTitleText.Text = moveIt ? "MOVEIT AUTOMATION" : "SERVER STATUS";
        WindowSubtitleText.Text = moveIt ? "LIVE TASK CATALOG / FIVE MINUTE MONITOR" : "STARTER SERVER INVENTORY / RESOURCE AND SERVICE MONITOR";
        MoveItView.Visibility = moveIt ? Visibility.Visible : Visibility.Collapsed;
        ServerView.Visibility = moveIt ? Visibility.Collapsed : Visibility.Visible;
        if (!moveIt)
        {
            ServersList.ItemsSource = new ObservableCollection<ServerInventory>();
        }
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
            var dashboard = await _client.GetDashboardAsync(_refreshCancellation.Token);
            if (_kind == MonitorWindowKind.MoveIt) UpdateMoveIt(dashboard); else UpdateServer(dashboard);
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

    private async void RefreshButton_Click(object sender, RoutedEventArgs e) => await RefreshAsync();
}
