using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using Microsoft.Win32;

namespace Jarvis.Desktop;

public partial class MainWindow : Window
{
    private readonly MonitoringClient _client = new("http://127.0.0.1:8000");
    private readonly List<ChatMessage> _messages = [];
    private readonly List<int> _attachedFileIds = [];
    private readonly List<FileEntry> _stagedFiles = [];
    private readonly UserPreferences _preferences = UserPreferences.Load();
    private readonly JarvisDesktopOptions _desktopOptions = JarvisDesktopOptions.Load();
    private readonly IAvatarService _avatarService;
    private int _avatarMood;
    private AvatarWindow? _avatarWindow;

    public MainWindow()
    {
        _avatarService = new AvatarService(
            _preferences,
            _desktopOptions,
            new AvatarAssetCatalog(),
            new KokoroSpeechService(_desktopOptions.Speech));

        InitializeComponent();
        ApplyAvatarPreferences();
        ConversationList.Items.Add("Jarvis is ready. Issue a command or ask a question.");
        ConversationList.Items.Add("Monitoring and workflow surfaces are available from the workspace rail.");
        Loaded += async (_, _) =>
        {
            await _avatarService.InitializeAsync();
            await LoadProviderHealthAsync();
            await LoadSystemHealthAsync();
            await LoadSessionAsync();
            await LoadMonitoringAsync();
            await LoadWorkflowsAsync();
        };
    }

    private async void IssueCommandButton_Click(object sender, RoutedEventArgs e) => await IssueCommandAsync();

    private async void CommandInput_PreviewKeyDown(object sender, KeyEventArgs e)
    {
        if (_preferences.EnterSendsMessage && e.Key == Key.Enter && Keyboard.Modifiers != ModifierKeys.Shift)
        {
            e.Handled = true;
            await IssueCommandAsync();
        }
    }

    private async Task IssueCommandAsync()
    {
        var command = CommandInput.Text.Trim();
        if (command.Length == 0) return;
        _messages.Add(new ChatMessage { Role = "user", Content = command });
        ConversationList.Items.Add($"Operator  ·  {command}");
        CommandInput.IsEnabled = false;
        AvatarStatusText.Text = "THINKING";
        await _avatarService.SetStateAsync(AvatarVisualState.Thinking);
        try
        {
            var response = await _client.ChatAsync(_messages, _attachedFileIds, CancellationToken.None);
            _messages.Add(new ChatMessage { Role = "assistant", Content = response.Content });
            ConversationList.Items.Add($"Jarvis  ·  {response.Content}");
            ConnectionText.Text = $"Local command center · {response.Model}";
            AvatarStatusText.Text = "SPEAKING";
            await _avatarService.SetStateAsync(AvatarVisualState.Speaking);

            var speechResult = await _avatarService.SpeakTextAsync(response.Content, CancellationToken.None);
            if (!speechResult.Success)
            {
                ConnectionText.Text = $"Speech unavailable · {speechResult.Detail}";
            }
        }
        catch (Exception error)
        {
            ConversationList.Items.Add($"Jarvis  ·  The local assistant service is unavailable: {error.Message}");
            ConnectionText.Text = "Local command center · backend unavailable";
            await _avatarService.SetStateAsync(AvatarVisualState.Offline);
        }
        finally
        {
            CommandInput.IsEnabled = true;
            AvatarStatusText.Text = "READY FOR COMMANDS";
            await _avatarService.SetStateAsync(AvatarVisualState.Idle);
        }
        ConversationList.ScrollIntoView(ConversationList.Items[^1]);
        CommandInput.Clear();
    }

    private void NewConversationButton_Click(object sender, RoutedEventArgs e)
    {
        ConversationList.Items.Clear();
        ConversationList.Items.Add("New command channel ready.");
        _messages.Clear();
        ConnectionText.Text = "Local command center · new conversation";
        AvatarStatusText.Text = "READY FOR COMMANDS";
    }

    private void SettingsButton_Click(object sender, RoutedEventArgs e)
    {
        var settings = new SettingsWindow(_preferences) { Owner = this };
        settings.ShowDialog();
        ApplyAvatarPreferences();
        ComposerHintText.Text = _preferences.EnterSendsMessage ? "Enter to send · Shift+Enter for a new line" : "Enter for a new line · use Issue command to send";
        ConnectionText.Text = "Settings closed · restart Jarvis to apply configuration changes";
    }

    private void OpenAvatarHostButton_Click(object sender, RoutedEventArgs e) => OpenAvatarHostWindow();

    private void ApplyAvatarPreferences()
    {
        AvatarNameText.Text = $"{_preferences.AvatarName.ToUpperInvariant()} PRESENCE";
        var (fill, stroke, border) = _preferences.AvatarTheme switch
        {
            "Ocean" => ("#58B8D1", "#B8EEF5", "#2D6577"),
            "Amber" => ("#E3A24C", "#FFE0A0", "#8B642C"),
            _ => ("#5FD39A", "#B5F1D2", "#35694F"),
        };
        AvatarAccent.Fill = new SolidColorBrush((Color)ColorConverter.ConvertFromString(fill));
        AvatarAccent.Stroke = new SolidColorBrush((Color)ColorConverter.ConvertFromString(stroke));
        AvatarCore.Fill = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#D9A27F"));
        AvatarCore.Stroke = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#F1C8A8"));
        AvatarPresence.BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString(border));
        AvatarStatusText.Text = _preferences.UseThreeDimensionalAvatar
            ? "READY FOR COMMANDS · USE AVATAR HOST BUTTON"
            : "READY FOR COMMANDS";
    }

    private void AvatarPresence_MouseEnter(object sender, System.Windows.Input.MouseEventArgs e)
    {
        if (AvatarStatusText.Text == "READY FOR COMMANDS") AvatarStatusText.Text = "ATTENTION ACKNOWLEDGED";
    }

    private void AvatarPresence_MouseLeave(object sender, System.Windows.Input.MouseEventArgs e)
    {
        if (AvatarStatusText.Text == "ATTENTION ACKNOWLEDGED") AvatarStatusText.Text = "READY FOR COMMANDS";
    }

    private void AvatarPresence_MouseLeftButtonUp(object sender, System.Windows.Input.MouseButtonEventArgs e)
    {
        if (_preferences.UseThreeDimensionalAvatar && Keyboard.Modifiers.HasFlag(ModifierKeys.Control))
        {
            OpenAvatarHostWindow();
            e.Handled = true;
            return;
        }

        var moods = new[] { "READY FOR COMMANDS", "LISTENING", "AT YOUR SERVICE" };
        _avatarMood = (_avatarMood + 1) % moods.Length;
        AvatarStatusText.Text = moods[_avatarMood];
        e.Handled = true;
    }

    private void OpenAvatarHostWindow()
    {
        if (!_preferences.UseThreeDimensionalAvatar)
        {
            ConnectionText.Text = "3D avatar host is disabled in settings";
            return;
        }

        if (_avatarWindow is { IsVisible: true })
        {
            _avatarWindow.Activate();
            ConnectionText.Text = "Avatar host already running";
            return;
        }

        _avatarWindow = new AvatarWindow(_preferences) { Owner = this };
        _avatarService.AttachHostWindow(_avatarWindow);
        _avatarWindow.Closed += (_, _) => _avatarWindow = null;
        _avatarWindow.Show();
        ConnectionText.Text = "Opened local 3D avatar host";
    }

    private async void ChooseFilesButton_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog { Multiselect = true, Filter = "Supported context files|*.txt;*.md;*.csv;*.json;*.log;*.pdf;*.docx|All files|*.*" };
        if (dialog.ShowDialog(this) == true) await UploadFilesAsync(dialog.FileNames);
    }

    private void ContextDropZone_DragOver(object sender, DragEventArgs e) => e.Effects = e.Data.GetDataPresent(DataFormats.FileDrop) ? DragDropEffects.Copy : DragDropEffects.None;

    private async void ContextDropZone_Drop(object sender, DragEventArgs e)
    {
        if (e.Data.GetData(DataFormats.FileDrop) is string[] files) await UploadFilesAsync(files);
    }

    private async Task UploadFilesAsync(IEnumerable<string> filePaths)
    {
        foreach (var filePath in filePaths)
        {
            try
            {
                var file = await _client.UploadFileAsync(filePath, CancellationToken.None);
                _attachedFileIds.Add(file.Id);
                _stagedFiles.Add(file);
                RefreshStagedFiles();
                ConnectionText.Text = $"Attached context · {file.Name}";
            }
            catch (Exception error)
            {
                ConnectionText.Text = $"File intake failed · {error.Message}";
            }
        }
    }

    private async void PreviewFileButton_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not FrameworkElement { Tag: FileEntry file } || file.Id <= 0) return;
        try
        {
            var content = await _client.GetFileContentAsync(file.Id, CancellationToken.None);
            MessageBox.Show(content.Length == 0 ? "No extracted text is available for this file." : content, file.Name, MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception error) { ConnectionText.Text = $"File preview failed: {error.Message}"; }
    }

    private async void RemoveFileButton_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not FrameworkElement { Tag: FileEntry file } || file.Id <= 0) return;
        try
        {
            await _client.DeleteFileAsync(file.Id, CancellationToken.None);
            _attachedFileIds.Remove(file.Id);
            _stagedFiles.RemoveAll(entry => entry.Id == file.Id);
            RefreshStagedFiles();
            ConnectionText.Text = $"Removed context · {file.Name}";
        }
        catch (Exception error) { ConnectionText.Text = $"File removal failed: {error.Message}"; }
    }

    private void RefreshStagedFiles()
    {
        StagedFileList.ItemsSource = _stagedFiles.ToList();
    }

    private async void CreateWorkflowButton_Click(object sender, RoutedEventArgs e)
    {
        var title = WorkflowTitleInput.Text.Trim();
        if (title.Length == 0) return;
        try
        {
            await _client.CreateWorkflowAsync(title, WorkflowDescriptionInput.Text.Trim(), _attachedFileIds, CancellationToken.None);
            WorkflowTitleInput.Clear();
            WorkflowDescriptionInput.Clear();
            ConnectionText.Text = $"Workflow '{title}' awaiting approval";
            await LoadWorkflowsAsync();
        }
        catch (Exception error)
        {
            ConnectionText.Text = $"Workflow creation failed: {error.Message}";
        }
    }

    private async void ApproveWorkflowButton_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not FrameworkElement { Tag: Workflow workflow } || workflow.State != "awaiting_approval") return;
        try
        {
            await _client.ApproveWorkflowAsync(workflow.Id, CancellationToken.None);
            await LoadWorkflowsAsync();
        }
        catch (Exception error) { ConnectionText.Text = $"Workflow approval failed: {error.Message}"; }
    }

    private void OpenWorkflowButton_Click(object sender, RoutedEventArgs e)
    {
        if (sender is FrameworkElement { Tag: Workflow workflow })
        {
            new WorkflowWindow(workflow.Id) { Owner = this }.Show();
        }
    }

    private void OpenMoveItWindow_Click(object sender, RoutedEventArgs e) => OpenMonitorWindow("MoveIT Automation");
    private void OpenServerWindow_Click(object sender, RoutedEventArgs e) => OpenMonitorWindow("Server Status");

    private void OpenMonitorWindow(string title)
    {
        var window = new MonitorWindow(title == "MoveIT Automation" ? MonitorWindowKind.MoveIt : MonitorWindowKind.ServerStatus) { Owner = this };
        window.Show();
    }

    private async Task LoadSessionAsync()
    {
        try
        {
            var session = await _client.GetSessionAsync(CancellationToken.None);
            _messages.Clear();
            _messages.AddRange(session.Messages);
            if (_messages.Count > 0)
            {
                ConversationList.Items.Clear();
                foreach (var message in _messages)
                {
                    ConversationList.Items.Add($"{(message.Role == "assistant" ? "Jarvis" : "Operator")}  ·  {message.Content}");
                }
            }
            _attachedFileIds.Clear();
            _stagedFiles.Clear();
            _stagedFiles.AddRange(session.Files);
            StagedFileList.ItemsSource = _stagedFiles.ToList();
            _attachedFileIds.AddRange(session.Files.Where(file => file.Id > 0).Select(file => file.Id));
            ActivityList.ItemsSource = session.Activity;
        }
        catch (Exception error) { ConnectionText.Text = $"Local command center · session unavailable: {error.Message}"; }
    }

    private async Task LoadMonitoringAsync()
    {
        try
        {
            var dashboard = await _client.GetDashboardAsync(CancellationToken.None);
            AlertList.ItemsSource = dashboard.Alerts;
        }
        catch (Exception error) { ConnectionText.Text = $"Local command center · monitoring unavailable: {error.Message}"; }
    }

    private async void ResolveAlertButton_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not FrameworkElement { Tag: MonitoringAlert alert }) return;
        try
        {
            var dashboard = await _client.ResolveAlertAsync(alert.Id, CancellationToken.None);
            AlertList.ItemsSource = dashboard.Alerts;
            ConnectionText.Text = $"Resolved alert · {alert.Title}";
        }
        catch (Exception error) { ConnectionText.Text = $"Alert resolution failed: {error.Message}"; }
    }

    private async Task LoadProviderHealthAsync()
    {
        try
        {
            var health = await _client.GetProviderHealthAsync(CancellationToken.None);
            ConnectionText.Text = health.Available ? $"Local command center · {health.Provider} · {health.Model}" : $"Local command center · provider unavailable · {health.Detail}";
        }
        catch (Exception error) { ConnectionText.Text = $"Local command center · provider health unavailable: {error.Message}"; }
    }

    private async Task LoadSystemHealthAsync()
    {
        try
        {
            var health = await _client.GetSystemHealthAsync(CancellationToken.None);
            HealthList.ItemsSource = health.Components;
        }
        catch (Exception error)
        {
            HealthList.ItemsSource = new[] { new ComponentHealth { Name = "Health service", Available = false, Detail = error.Message } };
        }
    }

    private async Task LoadWorkflowsAsync()
    {
        try { WorkflowList.ItemsSource = await _client.GetWorkflowsAsync(CancellationToken.None); }
        catch (Exception error) { ConnectionText.Text = $"Workflow supervisor unavailable: {error.Message}"; }
    }
}
