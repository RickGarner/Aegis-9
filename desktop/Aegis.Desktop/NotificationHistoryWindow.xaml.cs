using System.Windows;
using System.Windows.Controls;

namespace Aegis.Desktop;

public partial class NotificationHistoryWindow : Window
{
    private readonly MonitoringClient _client = new("http://127.0.0.1:8000");
    private bool _refreshing;

    public NotificationHistoryWindow()
    {
        InitializeComponent();
        Loaded += async (_, _) => await RefreshAsync();
    }

    private async Task RefreshAsync()
    {
        if (_refreshing) return;
        _refreshing = true;
        try
        {
            using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(30));
            var items = await _client.GetNotificationHistoryAsync(cancellation.Token);
            NotificationsList.ItemsSource = items;
            StatusText.Text = $"{items.Count} RECORD{(items.Count == 1 ? "" : "S")} · {items.Count(item => item.Status == "pending")} PENDING · {items.Count(item => item.Status == "failed")} FAILED";
        }
        catch (Exception error)
        {
            StatusText.Text = $"NOTIFICATION HISTORY UNAVAILABLE · {error.Message}";
        }
        finally
        {
            _refreshing = false;
        }
    }

    private async void RefreshButton_Click(object sender, RoutedEventArgs e) => await RefreshAsync();

    private async void RetryButton_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button { Tag: int itemId }) return;
        try
        {
            using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(30));
            await _client.RetryNotificationAsync(itemId, cancellation.Token);
            await RefreshAsync();
        }
        catch (Exception error)
        {
            MessageBox.Show(this, error.Message, "Notification retry unavailable", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }
}
