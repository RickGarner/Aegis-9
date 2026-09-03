using System.IO;
using System.Windows;
using System.Windows.Controls;
using Microsoft.Win32;

namespace Aegis.Desktop;

public partial class DeveloperStudioPanel : UserControl
{
    private UserPreferences? _preferences;
    private DeveloperStudioService? _studioService;

    public DeveloperStudioPanel()
    {
        InitializeComponent();
    }

    public event EventHandler? CloseRequested;

    public event EventHandler<string>? StatusChanged;

    public void Initialize(UserPreferences preferences, DeveloperStudioService studioService)
    {
        _preferences = preferences;
        _studioService = studioService;
        RefreshFoundationStatus();
        RefreshRepositories();
        SelectRepository(preferences.DeveloperStudioSelectedRepository, persist: false);
    }

    private void RefreshFoundationStatus()
    {
        if (_studioService is null) return;
        var installation = _studioService.GetInstallation();
        var process = _studioService.GetProcessStatus();
        FoundationPathText.Text = installation.ExecutableExists
            ? installation.ExecutablePath
            : $"Expected executable: {installation.ExecutablePath}";
        FoundationStatusText.Text = process.Running ? "RUNNING" : installation.ExecutableExists ? "READY" : "NOT FOUND";
        FoundationStatusText.Foreground = installation.ExecutableExists
            ? (System.Windows.Media.Brush)FindResource("StudioCyan")
            : System.Windows.Media.Brushes.Orange;
    }

    private void RefreshRepositories()
    {
        if (_preferences is null) return;
        RecentRepositoriesList.ItemsSource = _preferences.DeveloperStudioRecentRepositories
            .Where(Directory.Exists)
            .Select(path => new RepositoryEntry(Path.GetFileName(path.TrimEnd(Path.DirectorySeparatorChar)) is { Length: > 0 } name ? name : path, path))
            .ToList();
    }

    private void BrowseFolderButton_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFolderDialog
        {
            Title = "Select a repository for Aegis Developer Studio",
            Multiselect = false,
            InitialDirectory = Directory.Exists(_preferences?.DeveloperStudioSelectedRepository)
                ? _preferences.DeveloperStudioSelectedRepository
                : Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
        };
        if (dialog.ShowDialog() != true) return;
        SelectRepository(dialog.FolderName, persist: true);
    }

    private void RecentRepositoriesList_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (RecentRepositoriesList.SelectedItem is RepositoryEntry repository)
        {
            SelectRepository(repository.Path, persist: true);
        }
    }

    private void SelectRepository(string? path, bool persist)
    {
        if (string.IsNullOrWhiteSpace(path) || !Directory.Exists(path))
        {
            SelectedRepositoryText.Text = "No repository selected";
            RepositoryDetailText.Text = "Choose a local folder or select a recent repository.";
            OpenStudioButton.IsEnabled = false;
            return;
        }

        var normalizedPath = Path.GetFullPath(path);
        SelectedRepositoryText.Text = Path.GetFileName(normalizedPath.TrimEnd(Path.DirectorySeparatorChar));
        RepositoryDetailText.Text = normalizedPath;
        OpenStudioButton.IsEnabled = true;
        OpenStudioButton.ToolTip = "Launch Developer Studio or focus its existing window.";

        if (!persist || _preferences is null) return;
        _preferences.DeveloperStudioSelectedRepository = normalizedPath;
        _preferences.DeveloperStudioRecentRepositories.RemoveAll(item => item.Equals(normalizedPath, StringComparison.OrdinalIgnoreCase));
        _preferences.DeveloperStudioRecentRepositories.Insert(0, normalizedPath);
        if (_preferences.DeveloperStudioRecentRepositories.Count > 6)
        {
            _preferences.DeveloperStudioRecentRepositories.RemoveRange(6, _preferences.DeveloperStudioRecentRepositories.Count - 6);
        }
        _preferences.Save();
        RefreshRepositories();
        StatusChanged?.Invoke(this, $"Developer Studio repository selected · {SelectedRepositoryText.Text}");
    }

    private void OpenStudioButton_Click(object sender, RoutedEventArgs e)
    {
        if (_studioService is null || _preferences is null) return;
        try
        {
            var result = _studioService.LaunchOrFocus(_preferences.DeveloperStudioSelectedRepository);
            RefreshFoundationStatus();
            StatusChanged?.Invoke(this, result.Detail);
            if (!result.Success)
            {
                MessageBox.Show(Window.GetWindow(this), result.Detail, "Aegis Developer Studio", MessageBoxButton.OK, MessageBoxImage.Warning);
            }
        }
        catch (Exception error)
        {
            StatusChanged?.Invoke(this, $"Developer Studio launch failed · {error.Message}");
            MessageBox.Show(Window.GetWindow(this), error.Message, "Developer Studio launch failed", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void CloseButton_Click(object sender, RoutedEventArgs e) => CloseRequested?.Invoke(this, EventArgs.Empty);

    private sealed record RepositoryEntry(string Name, string Path);
}
