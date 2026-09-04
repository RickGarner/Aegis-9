using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace Aegis.Desktop;

public partial class OperationsMonitoringCenterWindow : Window
{
    private readonly MonitoringClient _client = new("http://127.0.0.1:8000");
    private readonly UserPreferences _preferences;
    private CancellationTokenSource? _refreshCancellation;
    private bool _refreshing;
    private bool _layoutReady;
    private string? _selectedMonitorId;

    public event EventHandler<MonitorWindowKind>? OpenMonitorRequested;

    public OperationsMonitoringCenterWindow(UserPreferences preferences)
    {
        _preferences = preferences;
        InitializeComponent();
        RestoreLayout();
        Loaded += async (_, _) =>
        {
            _layoutReady = true;
            await RefreshAsync();
        };
        Closing += (_, _) => SaveLayout();
        Closed += (_, _) => _refreshCancellation?.Cancel();
    }

    private void RestoreLayout()
    {
        Width = Math.Max(MinWidth, _preferences.OperationsCenterWidth);
        Height = Math.Max(MinHeight, _preferences.OperationsCenterHeight);

        if (_preferences.OperationsCenterLeft is double left && _preferences.OperationsCenterTop is double top
            && IsVisibleOnCurrentDesktop(left, top, Width, Height))
        {
            Left = left;
            Top = top;
        }
        else
        {
            Left = SystemParameters.WorkArea.Left + Math.Max(0, (SystemParameters.WorkArea.Width - Width) / 2);
            Top = SystemParameters.WorkArea.Top + Math.Max(0, (SystemParameters.WorkArea.Height - Height) / 2);
        }

        var mode = NormalizeLayoutMode(_preferences.OperationsCenterLayoutMode);
        LayoutModeComboBox.SelectedIndex = mode switch { "Compact" => 0, "Wallboard" => 2, _ => 1 };
        ApplyLayoutMode(mode);
        if (_preferences.OperationsCenterMaximized) WindowState = WindowState.Maximized;
    }

    private static bool IsVisibleOnCurrentDesktop(double left, double top, double width, double height)
    {
        var bounds = new Rect(left, top, width, height);
        var desktop = new Rect(SystemParameters.VirtualScreenLeft, SystemParameters.VirtualScreenTop, SystemParameters.VirtualScreenWidth, SystemParameters.VirtualScreenHeight);
        var visible = Rect.Intersect(bounds, desktop);
        return visible.Width >= 120 && visible.Height >= 80;
    }

    private void SaveLayout()
    {
        var bounds = RestoreBounds;
        _preferences.OperationsCenterLeft = bounds.Left;
        _preferences.OperationsCenterTop = bounds.Top;
        _preferences.OperationsCenterWidth = bounds.Width;
        _preferences.OperationsCenterHeight = bounds.Height;
        _preferences.OperationsCenterMaximized = WindowState == WindowState.Maximized;
        _preferences.OperationsCenterLayoutMode = SelectedLayoutMode();
        _preferences.Save();
    }

    private async Task RefreshAsync()
    {
        if (_refreshing) return;
        _refreshing = true;
        _refreshCancellation?.Cancel();
        _refreshCancellation = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        try
        {
            ConnectionStateText.Text = "REFRESHING";
            var snapshot = await _client.GetOperationsMonitoringAsync(_refreshCancellation.Token);
            AlertsList.ItemsSource = snapshot.Alerts;
            UpdateSummary(snapshot.Summary);
            var resources = snapshot.Monitors.Select(monitor => OperationsResourceCard.Create(
                monitor,
                snapshot.Observations.FirstOrDefault(observation => observation.MonitorId == monitor.MonitorId),
                snapshot.Alerts.Count(alert => alert.MonitorId == monitor.MonitorId))).ToList();
            SystemsList.ItemsSource = resources;
            SystemsList.SelectedItem = resources.FirstOrDefault(resource => resource.MonitorId == _selectedMonitorId)
                ?? resources.FirstOrDefault();
            LastRefreshText.Text = DateTime.Now.ToString("HH:mm:ss");
            ConnectionStateText.Text = "CONNECTED";
            ConnectionStateText.Foreground = (Brush)FindResource("Cyan");
        }
        catch (OperationCanceledException)
        {
            ConnectionStateText.Text = "TIMED OUT";
            ConnectionStateText.Foreground = (Brush)FindResource("Amber");
            DetailText.Text = "The refresh timed out. The previous snapshot remains visible and must not be interpreted as current.";
        }
        catch (Exception error)
        {
            ConnectionStateText.Text = "UNAVAILABLE";
            ConnectionStateText.Foreground = (Brush)FindResource("Amber");
            DetailText.Text = $"Monitoring data is unavailable. The previous snapshot remains visible. {error.Message}";
        }
        finally
        {
            _refreshing = false;
        }
    }

    private void UpdateSummary(OperationsSummary summary)
    {
        CriticalCountText.Text = summary.Counts.Critical.ToString();
        DegradedCountText.Text = summary.Counts.Degraded.ToString();
        HealthyCountText.Text = summary.Counts.Healthy.ToString();
        UnknownCountText.Text = (summary.Counts.Unknown + summary.Counts.Unreachable + summary.Counts.Unauthorized + summary.Counts.Misconfigured).ToString();
        OverallStateText.Text = summary.OverallState.ToUpperInvariant();
        OverallStateText.Foreground = summary.OverallState.Equals("healthy", StringComparison.OrdinalIgnoreCase)
            ? (Brush)FindResource("Cyan")
            : (Brush)FindResource("Amber");
    }

    private void OpenMonitorButton_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button { Tag: string monitorId }) OpenMonitor(monitorId);
    }

    private void SystemsList_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (SystemsList.SelectedItem is not OperationsResourceCard resource) return;
        _selectedMonitorId = resource.MonitorId;
        SelectedResourceNameText.Text = resource.DisplayName;
        SelectedTargetStateText.Text = resource.TargetState;
        SelectedTargetStateText.Foreground = resource.TargetBrush;
        SelectedCollectorStateText.Text = resource.CollectorState;
        SelectedCollectorStateText.Foreground = resource.CollectorBrush;
        SelectedConfigurationText.Text = $"Configuration: {resource.ConfigurationState}";
        SelectedFreshnessText.Text = resource.Freshness;
        SelectedAlertText.Text = resource.AlertSummary;
        DetailText.Text = resource.Summary;
        OpenSelectedDetailsButton.IsEnabled = true;
        OpenSelectedDetailsButton.Tag = resource.MonitorId;
    }

    private void SystemsList_MouseDoubleClick(object sender, System.Windows.Input.MouseButtonEventArgs e)
    {
        if (SystemsList.SelectedItem is OperationsResourceCard resource) OpenMonitor(resource.MonitorId);
    }

    private void OpenSelectedDetailsButton_Click(object sender, RoutedEventArgs e)
    {
        if (OpenSelectedDetailsButton.Tag is string monitorId) OpenMonitor(monitorId);
    }

    private void OpenMonitor(string monitorId)
    {
        var kind = monitorId.ToLowerInvariant() switch
        {
            "moveit" => MonitorWindowKind.MoveIt,
            "freeflow" => MonitorWindowKind.FreeFlow,
            "qualys" => MonitorWindowKind.Qualys,
            _ => MonitorWindowKind.ServerStatus,
        };
        OpenMonitorRequested?.Invoke(this, kind);
    }

    private async void RefreshButton_Click(object sender, RoutedEventArgs e) => await RefreshAsync();

    private void LayoutModeComboBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!_layoutReady) return;
        var mode = SelectedLayoutMode();
        ApplyLayoutMode(mode);
        _preferences.OperationsCenterLayoutMode = mode;
        _preferences.Save();
    }

    private string SelectedLayoutMode() => NormalizeLayoutMode((LayoutModeComboBox.SelectedItem as ComboBoxItem)?.Content?.ToString());
    private static string NormalizeLayoutMode(string? mode) => mode is "Compact" or "Wallboard" ? mode : "Standard";

    private void ApplyLayoutMode(string mode)
    {
        NavigationColumn.Width = mode == "Compact" ? new GridLength(190) : mode == "Wallboard" ? new GridLength(280) : new GridLength(240);
        DetailColumn.Width = mode == "Compact" ? new GridLength(0) : mode == "Wallboard" ? new GridLength(380) : new GridLength(320);
    }
}

public sealed class OperationsResourceCard
{
    public string MonitorId { get; init; } = string.Empty;
    public string DisplayName { get; init; } = string.Empty;
    public string TargetState { get; init; } = "UNKNOWN";
    public string CollectorState { get; init; } = "UNKNOWN";
    public string ConfigurationState { get; init; } = "unknown";
    public string Freshness { get; init; } = "No observation loaded";
    public string AlertSummary { get; init; } = "No active alerts";
    public string Summary { get; init; } = "No normalized evidence loaded.";
    public Brush TargetBrush => StatusBrush(TargetState);
    public Brush CollectorBrush => StatusBrush(CollectorState);

    public static OperationsResourceCard Create(
        OperationsMonitorDescriptor monitor,
        OperationsObservation? observation,
        int alertCount)
    {
        var freshness = observation is null
            ? "No observation loaded"
            : FormatFreshness(observation);
        return new OperationsResourceCard
        {
            MonitorId = monitor.MonitorId,
            DisplayName = monitor.DisplayName,
            TargetState = (observation?.State ?? "unknown").ToUpperInvariant(),
            CollectorState = monitor.CollectorState.ToUpperInvariant(),
            ConfigurationState = monitor.ConfigurationState,
            Freshness = freshness,
            AlertSummary = alertCount == 0 ? "No active alerts" : $"{alertCount} active alert{(alertCount == 1 ? "" : "s")}",
            Summary = observation?.Summary ?? "No normalized evidence loaded.",
        };
    }

    private static string FormatFreshness(OperationsObservation observation)
    {
        if (!DateTimeOffset.TryParse(observation.CollectedAtUtc, out var collected)) return "Observation time unavailable";
        var age = DateTimeOffset.UtcNow - collected;
        var ageText = age.TotalMinutes < 1
            ? "just now"
            : age.TotalHours < 1
                ? $"{Math.Max(1, (int)age.TotalMinutes)} min ago"
                : $"{(int)age.TotalHours} hr ago";
        var validity = DateTimeOffset.TryParse(observation.ValidUntilUtc, out var validUntil) && validUntil < DateTimeOffset.UtcNow
            ? " · evidence expired"
            : " · evidence current";
        return $"Observed {ageText}{validity}";
    }

    private static Brush StatusBrush(string status) => status.ToUpperInvariant() switch
    {
        "HEALTHY" => new SolidColorBrush(Color.FromRgb(77, 231, 255)),
        "DEGRADED" or "WARNING" => new SolidColorBrush(Color.FromRgb(255, 184, 77)),
        "CRITICAL" or "FAILED" or "UNREACHABLE" => new SolidColorBrush(Color.FromRgb(255, 98, 95)),
        "MISCONFIGURED" or "UNAUTHORIZED" or "STALE" => new SolidColorBrush(Color.FromRgb(255, 184, 77)),
        _ => new SolidColorBrush(Color.FromRgb(106, 155, 169)),
    };
}
