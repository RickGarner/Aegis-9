using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using Microsoft.Win32;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.Wpf;

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
    private UIElement? _nativeAvatarVisual;
    private WebView2? _inlineAvatarWebView;
    private bool _inlineAvatarReady;

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
            await InitializeInlineAvatarAsync();
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
        ConversationList.Items.Add($"Operator  Â·  {command}");
        CommandInput.IsEnabled = false;
        AvatarStatusText.Text = "THINKING";
        await _avatarService.SetStateAsync(AvatarVisualState.Thinking);
        await SetInlineAvatarStateAsync("thinking", "Thinking");
        try
        {
            var response = await _client.ChatAsync(_messages, _attachedFileIds, CancellationToken.None);
            _messages.Add(new ChatMessage { Role = "assistant", Content = response.Content });
            ConversationList.Items.Add($"Jarvis  Â·  {response.Content}");
            ConnectionText.Text = $"Local command center Â· {response.Model}";
            AvatarStatusText.Text = "SPEAKING";
            await _avatarService.SetStateAsync(AvatarVisualState.Speaking);
            await SetInlineAvatarStateAsync("speaking", "Speaking");

            var speechResult = await _avatarService.SpeakTextAsync(response.Content, CancellationToken.None);
            if (!speechResult.Success)
            {
                ConnectionText.Text = $"Speech unavailable Â· {speechResult.Detail}";
            }
        }
        catch (Exception error)
        {
            ConversationList.Items.Add($"Jarvis  Â·  The local assistant service is unavailable: {error.Message}");
            ConnectionText.Text = "Local command center Â· backend unavailable";
            await _avatarService.SetStateAsync(AvatarVisualState.Offline);
        }
        finally
        {
            CommandInput.IsEnabled = true;
            AvatarStatusText.Text = "READY FOR COMMANDS";
            await _avatarService.SetStateAsync(AvatarVisualState.Idle);
            await SetInlineAvatarStateAsync("ready", "Ready for commands");
        }
        ConversationList.ScrollIntoView(ConversationList.Items[^1]);
        CommandInput.Clear();
    }

    private void NewConversationButton_Click(object sender, RoutedEventArgs e)
    {
        ConversationList.Items.Clear();
        ConversationList.Items.Add("New command channel ready.");
        _messages.Clear();
        ConnectionText.Text = "Local command center Â· new conversation";
        AvatarStatusText.Text = "READY FOR COMMANDS";
    }

    private async void SettingsButton_Click(object sender, RoutedEventArgs e)
    {
        var settings = new SettingsWindow(_preferences) { Owner = this };
        var saved = settings.ShowDialog() == true;
        ApplyAvatarPreferences();
        ComposerHintText.Text = _preferences.EnterSendsMessage ? "Enter to send Â· Shift+Enter for a new line" : "Enter for a new line Â· use Issue command to send";
        if (saved)
        {
            await InitializeInlineAvatarAsync();
            ConnectionText.Text = "Settings saved Â· selected avatar applied";
        }
        else
        {
            ConnectionText.Text = "Settings closed Â· changes discarded";
        }
    }

    private void OpenAvatarHostButton_Click(object sender, RoutedEventArgs e) => OpenAvatarHostWindow();

    private async Task InitializeInlineAvatarAsync()
    {
        if (!_preferences.UseThreeDimensionalAvatar)
        {
            RestoreNativeAvatar();
            return;
        }

        var selection = new AvatarAssetCatalog().GetSelection(_preferences.AvatarProfile);
        if (!selection.IsAvailable || selection.Definition is null)
        {
            RestoreNativeAvatar();
            return;
        }

        try
        {
            _nativeAvatarVisual ??= AvatarPresence.Child as UIElement;
            if (_nativeAvatarVisual is null)
            {
                return;
            }

            if (_inlineAvatarWebView is null)
            {
                _inlineAvatarWebView = new WebView2
                {
                    DefaultBackgroundColor = System.Drawing.Color.Transparent,
                    Width = 150,
                    Height = 136,
                    HorizontalAlignment = HorizontalAlignment.Center,
                    VerticalAlignment = VerticalAlignment.Center,
                };
                AvatarPresence.Child = _inlineAvatarWebView;
            }

            _inlineAvatarWebView.Visibility = Visibility.Visible;
            await _inlineAvatarWebView.EnsureCoreWebView2Async();
            var runtimeRoot = ResolveAvatarHostRoot();
            var assetsRoot = ResolveAvatarAssetsRoot();
            var core = _inlineAvatarWebView.CoreWebView2;
            core.Settings.AreDevToolsEnabled = false;
            core.Settings.IsStatusBarEnabled = false;
            core.Settings.AreDefaultContextMenusEnabled = false;
            core.Settings.AreHostObjectsAllowed = false;
            core.SetVirtualHostNameToFolderMapping("jarvis-inline.local", runtimeRoot, CoreWebView2HostResourceAccessKind.DenyCors);
            core.SetVirtualHostNameToFolderMapping("jarvis-inline-assets.local", assetsRoot, CoreWebView2HostResourceAccessKind.Allow);
            core.WebMessageReceived -= InlineAvatarWebMessageReceived;
            core.NavigationCompleted -= InlineAvatarNavigationCompleted;
            core.WebMessageReceived += InlineAvatarWebMessageReceived;
            core.NavigationCompleted += InlineAvatarNavigationCompleted;
            _inlineAvatarReady = false;
            core.Navigate("https://jarvis-inline.local/index.html");
            _nativeAvatarVisual.Visibility = Visibility.Collapsed;
        }
        catch (Exception ex) when (ex is InvalidOperationException or WebView2RuntimeNotFoundException)
        {
            ConnectionText.Text = $"3D avatar unavailable Â· {ex.Message}";
            RestoreNativeAvatar();
        }
    }

    private async void InlineAvatarNavigationCompleted(object? sender, CoreWebView2NavigationCompletedEventArgs e)
    {
        if (!e.IsSuccess || _inlineAvatarWebView?.CoreWebView2 is null)
        {
            RestoreNativeAvatar();
            return;
        }

        _inlineAvatarReady = true;
        var activeAvatar = _avatarService.ActiveAvatar;
        if (activeAvatar is null)
        {
            RestoreNativeAvatar();
            return;
        }

        var manifestUrl = $"https://jarvis-inline-assets.local/{activeAvatar.Profile}/avatar.json";
        await SendInlineAvatarMessageAsync(AvatarProtocol.Build("avatar.load", new
        {
            manifestUrl,
            selectedAvatarId = activeAvatar.Id,
            compact = true,
            lipSyncEnabled = _preferences.EnableLipSync,
            voiceId = activeAvatar.VoiceId,
        }));
    }

    private void InlineAvatarWebMessageReceived(object? sender, CoreWebView2WebMessageReceivedEventArgs e)
    {
        try
        {
            var message = JsonSerializer.Deserialize<AvatarMessage>(e.WebMessageAsJson);
            if (message?.Type == "avatar.error")
            {
                var detail = message.Payload.TryGetProperty("message", out var messageProperty)
                    ? messageProperty.GetString()
                    : "The local avatar runtime reported an unknown error.";
                ConnectionText.Text = $"3D avatar unavailable Â· {detail}";
                RestoreNativeAvatar();
            }
        }
        catch (JsonException)
        {
            ConnectionText.Text = "3D avatar unavailable Â· invalid runtime message";
            RestoreNativeAvatar();
        }
    }

    private Task SetInlineAvatarStateAsync(string state, string detail) =>
        SendInlineAvatarMessageAsync(AvatarProtocol.Build("avatar.state", new { state, detail }));

    private Task SendInlineAvatarMessageAsync(string message)
    {
        if (!_inlineAvatarReady || _inlineAvatarWebView?.CoreWebView2 is null)
        {
            return Task.CompletedTask;
        }

        _inlineAvatarWebView.CoreWebView2.PostWebMessageAsJson(message);
        return Task.CompletedTask;
    }

    private void RestoreNativeAvatar()
    {
        _inlineAvatarReady = false;
        if (_inlineAvatarWebView is not null)
        {
            _inlineAvatarWebView.Visibility = Visibility.Collapsed;
        }
        if (_nativeAvatarVisual is not null)
        {
            AvatarPresence.Child = _nativeAvatarVisual;
            _nativeAvatarVisual.Visibility = Visibility.Visible;
        }
    }

    private static string ResolveAvatarHostRoot() => ResolveAssetRoot("AvatarHost");
    private static string ResolveAvatarAssetsRoot() => ResolveAssetRoot("Avatars");

    private static string ResolveAssetRoot(string assetFolder)
    {
        var current = new DirectoryInfo(AppDomain.CurrentDomain.BaseDirectory);
        while (current is not null)
        {
            var local = Path.Combine(current.FullName, "Assets", assetFolder);
            if (Directory.Exists(local)) return local;
            var source = Path.Combine(current.FullName, "desktop", "Jarvis.Desktop", "Assets", assetFolder);
            if (Directory.Exists(source)) return source;
            current = current.Parent;
        }
        throw new InvalidOperationException($"Avatar asset directory '{assetFolder}' was not found.");
    }

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
            ? "READY FOR COMMANDS Â· USE AVATAR HOST BUTTON"
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
                ConnectionText.Text = $"Attached context Â· {file.Name}";
            }
            catch (Exception error)
            {
                ConnectionText.Text = $"File intake failed Â· {error.Message}";
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
            ConnectionText.Text = $"Removed context Â· {file.Name}";
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
                    ConversationList.Items.Add($"{(message.Role == "assistant" ? "Jarvis" : "Operator")}  Â·  {message.Content}");
                }
            }
            _attachedFileIds.Clear();
            _stagedFiles.Clear();
            _stagedFiles.AddRange(session.Files);
            StagedFileList.ItemsSource = _stagedFiles.ToList();
            _attachedFileIds.AddRange(session.Files.Where(file => file.Id > 0).Select(file => file.Id));
            ActivityList.ItemsSource = session.Activity;
        }
        catch (Exception error) { ConnectionText.Text = $"Local command center Â· session unavailable: {error.Message}"; }
    }

    private async Task LoadMonitoringAsync()
    {
        try
        {
            var dashboard = await _client.GetDashboardAsync(CancellationToken.None);
            AlertList.ItemsSource = dashboard.Alerts;
        }
        catch (Exception error) { ConnectionText.Text = $"Local command center Â· monitoring unavailable: {error.Message}"; }
    }

    private async void ResolveAlertButton_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not FrameworkElement { Tag: MonitoringAlert alert }) return;
        try
        {
            var dashboard = await _client.ResolveAlertAsync(alert.Id, CancellationToken.None);
            AlertList.ItemsSource = dashboard.Alerts;
            ConnectionText.Text = $"Resolved alert Â· {alert.Title}";
        }
        catch (Exception error) { ConnectionText.Text = $"Alert resolution failed: {error.Message}"; }
    }

    private async Task LoadProviderHealthAsync()
    {
        try
        {
            var health = await _client.GetProviderHealthAsync(CancellationToken.None);
            ConnectionText.Text = health.Available ? $"Local command center Â· {health.Provider} Â· {health.Model}" : $"Local command center Â· provider unavailable Â· {health.Detail}";
        }
        catch (Exception error) { ConnectionText.Text = $"Local command center Â· provider health unavailable: {error.Message}"; }
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

