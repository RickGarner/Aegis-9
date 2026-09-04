using System.IO;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Animation;
using Microsoft.Win32;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.Wpf;
using NAudio;
using NAudio.Wave;

namespace Aegis.Desktop;

public partial class MainWindow : Window
{
    private const string ComingOnlinePhrase = "Aegis 9 coming on line.";
    private const string SearchingProviderPhrase = "Searching for provider.";
    private const string DevelopmentPhrase = "Aegis 9 online. Neural core synchronized. Development environment secured. Let's hunt down some bugs.";
    private const string DiagnosticsPhrase = "Guardian protocols active. Beginning systems analysis. If there's a fault in the pack, I'll find it.";
    private const string ObjectiveCompletePhrase = "Objective complete. Systems stable, code secured, and the trail is clear.";
    private const string NeuralLinkInterruptedPhrase = "Neural link interrupted. Local systems remain operational while I attempt to reestablish the connection.";
    private const string IdleWakePhrase = "Aegis 9 awake. Pack link restored. What requires my attention?";
    private readonly MonitoringClient _client = new("http://127.0.0.1:8000");
    private readonly List<ChatMessage> _messages = [];
    private readonly List<int> _attachedFileIds = [];
    private readonly List<FileEntry> _stagedFiles = [];
    private readonly UserPreferences _preferences = UserPreferences.Load();
    private readonly AegisDesktopOptions _desktopOptions = AegisDesktopOptions.Load();
    private readonly DeveloperStudioService _developerStudioService;
    private readonly IAvatarService _avatarService;
    private readonly ISpeechService _speechService;
    private readonly LocalSpeechRecognitionService _speechRecognition = new();
    private int _avatarMood;
    private AvatarWindow? _avatarWindow;
    private UIElement? _nativeAvatarVisual;
    private WebView2? _inlineAvatarWebView;
    private bool _inlineAvatarReady;
    private bool _commandInProgress;
    private CancellationTokenSource? _voiceCaptureCancellation;
    private TaskCompletionSource<bool>? _providerTransitionAcknowledgement;
    private bool _alertPhraseSpoken;

    public MainWindow()
    {
        _speechService = new KokoroSpeechService(_desktopOptions.Speech);
        _developerStudioService = new DeveloperStudioService(_desktopOptions.DeveloperStudio);
        _avatarService = new AvatarService(
            _preferences,
            _desktopOptions,
            new AvatarAssetCatalog(),
            _speechService);

        InitializeComponent();
        OperationsMonitoringCenterButton.Visibility = _desktopOptions.OperationsMonitoringCenter.Enabled
            ? Visibility.Visible
            : Visibility.Collapsed;
        DeveloperStudioPanel.Initialize(_preferences, _developerStudioService);
        DeveloperStudioPanel.CloseRequested += (_, _) => CloseDeveloperStudio();
        DeveloperStudioPanel.StatusChanged += (_, status) => ConnectionText.Text = status;
        PendingWorkflowList.LayoutUpdated += (_, _) => RenameWorkflowReviewButtons(PendingWorkflowList);
        _speechRecognition.AudioLevelChanged += SpeechRecognition_AudioLevelChanged;
        _speechRecognition.StatusChanged += SpeechRecognition_StatusChanged;
        _speechRecognition.WakePhraseRecognized += SpeechRecognition_WakePhraseRecognized;
        ApplyAvatarPreferences();
        ConversationList.Items.Clear();
        ConversationList.Items.Add("New A.E.G.I.S.-9 startup command channel ready.");
        Loaded += async (_, _) =>
        {
            await _avatarService.InitializeAsync();
            await InitializeInlineAvatarAsync();
            await WaitForProviderReadyAsync();
            await LoadSystemHealthAsync();
            await LoadMonitoringAsync();
            await LoadWorkflowsAsync();
            await ConfigureWakePhraseAsync();
        };
        Closed += MainWindow_Closed;
    }

    private async void IssueCommandButton_Click(object sender, RoutedEventArgs e) => await IssueCommandAsync();

    private void WindowHeader_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ChangedButton != MouseButton.Left) return;
        if (e.ClickCount == 2)
        {
            WindowState = WindowState == WindowState.Maximized ? WindowState.Normal : WindowState.Maximized;
            return;
        }
        DragMove();
    }

    private void HideWindowButton_Click(object sender, RoutedEventArgs e) => WindowState = WindowState.Minimized;

    private void CloseWindowButton_Click(object sender, RoutedEventArgs e) => Close();

    private void DeveloperStudioButton_Click(object sender, RoutedEventArgs e)
    {
        DeveloperStudioPanel.Initialize(_preferences, _developerStudioService);
        DeveloperStudioOverlay.Visibility = Visibility.Visible;
        ((TranslateTransform)DeveloperStudioPanel.RenderTransform).BeginAnimation(
            TranslateTransform.XProperty,
            new DoubleAnimation(455, 0, TimeSpan.FromMilliseconds(220)) { EasingFunction = new QuadraticEase { EasingMode = EasingMode.EaseOut } });
        ConnectionText.Text = "Aegis Developer Studio · panel active";
    }

    private void DeveloperStudioBackdrop_MouseLeftButtonDown(object sender, MouseButtonEventArgs e) => CloseDeveloperStudio();

    private void CloseDeveloperStudio()
    {
        var animation = new DoubleAnimation(0, 455, TimeSpan.FromMilliseconds(180)) { EasingFunction = new QuadraticEase { EasingMode = EasingMode.EaseIn } };
        animation.Completed += (_, _) => DeveloperStudioOverlay.Visibility = Visibility.Collapsed;
        ((TranslateTransform)DeveloperStudioPanel.RenderTransform).BeginAnimation(TranslateTransform.XProperty, animation);
        ConnectionText.Text = "Local command center · Developer Studio panel closed";
    }

    private async void CommandInput_PreviewKeyDown(object sender, KeyEventArgs e)
    {
        if (_preferences.EnterSendsMessage && e.Key == Key.Enter && Keyboard.Modifiers != ModifierKeys.Shift)
        {
            e.Handled = true;
            await IssueCommandAsync();
        }
    }

    private async void MainWindow_PreviewKeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Space && Keyboard.Modifiers == ModifierKeys.Control)
        {
            e.Handled = true;
            await BeginVoiceCaptureAsync(false);
        }
    }

    private async Task IssueCommandAsync()
    {
        var command = CommandInput.Text.Trim();
        if (command.Length == 0 || _commandInProgress) return;
        _commandInProgress = true;
        await _speechRecognition.StopWakePhraseAsync();
        var speechDurationMs = 0;
        _messages.Add(new ChatMessage { Role = "user", Content = command });
        AddConversationMessage($"Operator  ·  {command}");
        CommandInput.IsEnabled = false;
        AvatarStatusText.Text = "THINKING";
        await _avatarService.SetStateAsync(AvatarVisualState.Thinking);
        await SetInlineAvatarStateAsync("thinking", "Thinking");
        try
        {
            if (IsCodeCreationRequest(command))
            {
                await SpeakCodeAcknowledgementAsync(command);
                AvatarStatusText.Text = "THINKING";
                await _avatarService.SetStateAsync(AvatarVisualState.Thinking);
                await SetInlineAvatarStateAsync("thinking", "Creating requested code");
            }
            else if (IsDiagnosticRequest(command))
            {
                await SpeakSystemPhraseAsync(DiagnosticsPhrase, "Guardian diagnostics active");
                AvatarStatusText.Text = "THINKING";
                await _avatarService.SetStateAsync(AvatarVisualState.Thinking);
                await SetInlineAvatarStateAsync("thinking", "Analyzing systems");
            }
            var response = await _client.ChatAsync(_messages, _attachedFileIds, CancellationToken.None);
            if (response.Failover.RequiresAcknowledgement)
            {
                await ShowProviderTransitionAsync(response.Failover);
            }
            _messages.Add(new ChatMessage { Role = "assistant", Content = response.Content });
            AddConversationMessage($"A.E.G.I.S.-9  ·  {response.Content}");
            ConnectionText.Text = $"{response.Location.ToUpperInvariant()} command center · {response.Provider} · {response.Model}";
            if (_preferences.EnableVoiceResponses)
            {
                var spokenResponse = PrepareSpokenResponse(response.Content, command);
                var voiceId = _preferences.AvatarProfile.Equals("female", StringComparison.OrdinalIgnoreCase)
                    ? _preferences.FemaleVoiceId
                    : _preferences.MaleVoiceId;
                var speechResult = await _speechService.SynthesizeAsync(new SpeechRequest
                {
                    Text = spokenResponse,
                    VoiceId = voiceId,
                    Speed = _desktopOptions.Speech.Speed,
                }, CancellationToken.None);
                if (!speechResult.Success)
                {
                    ConnectionText.Text = $"Speech unavailable · {speechResult.Detail}";
                }
                else
                {
                    speechDurationMs = speechResult.DurationMs;
                    if (speechResult.Detail.Contains("fallback", StringComparison.OrdinalIgnoreCase))
                    {
                        ConnectionText.Text = $"Speech fallback · {speechResult.Detail}";
                    }
                    AvatarStatusText.Text = "SPEAKING";
                    await _avatarService.SetStateAsync(AvatarVisualState.Speaking);
                    await SetInlineAvatarStateAsync("speaking", "Speaking");
                    var playbackError = await PlayInlineSpeechAsync(speechResult);
                    if (!string.IsNullOrWhiteSpace(playbackError))
                    {
                        ConnectionText.Text = $"Speech playback unavailable · {playbackError}";
                    }
                }
            }
        }
        catch (Exception error)
        {
            AddConversationMessage($"A.E.G.I.S.-9  ·  {NeuralLinkInterruptedPhrase}");
            AddConversationMessage($"System detail  ·  {error.Message}");
            ConnectionText.Text = "Provider request failed · controls restored for retry";
            await _avatarService.SetStateAsync(AvatarVisualState.Offline);
            await SpeakSystemPhraseAsync(NeuralLinkInterruptedPhrase, "Neural link interrupted");
        }
        finally
        {
            CommandInput.IsEnabled = true;
            VoiceInputButton.IsEnabled = true;
            AvatarStatusText.Text = "READY FOR COMMANDS";
            await _avatarService.SetStateAsync(AvatarVisualState.Idle);
            await SetInlineAvatarStateAsync("ready", "Ready for commands");
            _commandInProgress = false;
            if (speechDurationMs > 0) _ = ResumeWakePhraseAfterSpeechAsync(speechDurationMs);
            else await ConfigureWakePhraseAsync();
        }
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

    private async void SettingsButton_Click(object sender, RoutedEventArgs e)
    {
        var settings = new SettingsWindow(_preferences) { Owner = this };
        var saved = settings.ShowDialog() == true;
        ApplyAvatarPreferences();
        ComposerHintText.Text = _preferences.EnterSendsMessage
            ? "Enter to send · Shift+Enter for a new line · Ctrl+Space for microphone"
            : "Enter for a new line · use Execute to send · Ctrl+Space for microphone";
        if (saved)
        {
            await InitializeInlineAvatarAsync();
            await ConfigureWakePhraseAsync();
            ConnectionText.Text = "Settings saved · selected avatar applied";
        }
        else
        {
            ConnectionText.Text = "Settings closed · changes discarded";
        }
    }

    private async void VoiceInputButton_Click(object sender, RoutedEventArgs e) => await BeginVoiceCaptureAsync(false);

    private async Task BeginVoiceCaptureAsync(bool wakeTriggered)
    {
        if (_voiceCaptureCancellation is not null)
        {
            _speechRecognition.RequestStop();
            VoiceInputButton.Content = "PROCESSING";
            VoiceInputButton.IsEnabled = false;
            ConnectionText.Text = "Voice capture complete · transcribing locally";
            return;
        }
        if (_commandInProgress) return;

        await _avatarService.StopSpeakingAsync();
        await _speechRecognition.StopWakePhraseAsync();
        var captureCancellation = new CancellationTokenSource();
        _voiceCaptureCancellation = captureCancellation;
        VoiceInputButton.Content = "STOP";
        AvatarStatusText.Text = "LISTENING";
        ConnectionText.Text = wakeTriggered
            ? "Wake phrase acknowledged · listening locally"
            : "Microphone active · listening locally";
        await _avatarService.SetStateAsync(AvatarVisualState.Listening);
        await SetInlineAvatarStateAsync("listening", "Listening for local voice command");

        SpeechRecognitionResult? result = null;
        try
        {
            result = await _speechRecognition.ListenOnceAsync(captureCancellation.Token);
        }
        catch (OperationCanceledException)
        {
            ConnectionText.Text = "Voice capture cancelled";
        }
        finally
        {
            if (ReferenceEquals(_voiceCaptureCancellation, captureCancellation)) _voiceCaptureCancellation = null;
            captureCancellation.Dispose();
            MicrophoneLevel.Value = 0;
            VoiceInputButton.Content = "MIC";
            VoiceInputButton.IsEnabled = true;
        }

        if (result?.Success == true)
        {
            CommandInput.Text = result.Text;
            CommandInput.CaretIndex = CommandInput.Text.Length;
            ConnectionText.Text = $"Voice captured locally · {result.Confidence:P0} confidence";
            AvatarStatusText.Text = "COMMAND CAPTURED";
            // An explicit MIC/keyboard request always submits. Wake-phrase capture
            // continues to honor the user's auto-submit preference.
            if (!wakeTriggered || _preferences.AutoSubmitVoiceCommands)
            {
                await IssueCommandAsync();
                return;
            }
        }
        else if (result is not null)
        {
            ConnectionText.Text = result.Detail;
            AddConversationMessage($"Voice input  ·  {result.Detail}");
        }

        AvatarStatusText.Text = "READY FOR COMMANDS";
        await _avatarService.SetStateAsync(AvatarVisualState.Idle);
        await SetInlineAvatarStateAsync("ready", "Ready for commands");
        await ConfigureWakePhraseAsync();
    }

    private void SpeechRecognition_AudioLevelChanged(object? sender, int level) =>
        Dispatcher.BeginInvoke(() => MicrophoneLevel.Value = level);

    private void SpeechRecognition_StatusChanged(object? sender, string status) =>
        Dispatcher.BeginInvoke(() =>
        {
            ConnectionText.Text = $"Voice input · {status}";
            if (status.StartsWith("Transcribing", StringComparison.OrdinalIgnoreCase))
            {
                VoiceInputButton.Content = "TRANSCRIBING";
            }
        });

    private void SpeechRecognition_WakePhraseRecognized(object? sender, EventArgs e) =>
        Dispatcher.BeginInvoke(() => _ = HandleWakePhraseAsync());

    private async Task HandleWakePhraseAsync()
    {
        await SpeakSystemPhraseAsync(IdleWakePhrase, "Pack link restored");
        await BeginVoiceCaptureAsync(true);
    }

    private async Task ResumeWakePhraseAfterSpeechAsync(int durationMs)
    {
        await Task.Delay(Math.Max(250, durationMs) + 250);
        await ConfigureWakePhraseAsync();
    }

    private async Task<string?> PlayInlineSpeechAsync(SpeechResult speechResult)
    {
        if (string.IsNullOrWhiteSpace(speechResult.AudioPath)) return "No audio file was produced.";
        var audioPath = speechResult.AudioPath;
        if (!Path.IsPathFullyQualified(audioPath))
        {
            var localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            audioPath = Path.GetFullPath(Path.Combine(localAppData, audioPath));
        }
        if (!File.Exists(audioPath)) return $"Audio file not found: {audioPath}";

        try
        {
            using var reader = new AudioFileReader(audioPath);
            using var output = new WaveOutEvent();
            var completion = new TaskCompletionSource<Exception?>(TaskCreationOptions.RunContinuationsAsynchronously);
            output.PlaybackStopped += (_, args) => completion.TrySetResult(args.Exception);
            output.Init(reader);
            output.Play();
            var playbackException = await completion.Task;
            return playbackException?.Message;
        }
        catch (Exception error) when (error is InvalidOperationException or IOException or MmException)
        {
            return error.Message;
        }
    }

    private async Task SpeakSystemPhraseAsync(string phrase, string detail, bool startupNotification = false)
    {
        if (startupNotification ? !_preferences.EnableStartupNotifications : !_preferences.EnableVoiceResponses) return;
        try
        {
            var voiceId = _preferences.AvatarProfile.Equals("female", StringComparison.OrdinalIgnoreCase)
                ? _preferences.FemaleVoiceId
                : _preferences.MaleVoiceId;
            var result = await _speechService.SynthesizeAsync(new SpeechRequest
            {
                Text = phrase,
                VoiceId = voiceId,
                Speed = _desktopOptions.Speech.Speed,
            }, CancellationToken.None);
            if (!result.Success) return;
            AvatarStatusText.Text = "SPEAKING";
            await _avatarService.SetStateAsync(AvatarVisualState.Speaking);
            await SetInlineAvatarStateAsync("speaking", detail);
            await PlayInlineSpeechAsync(result);
        }
        catch
        {
            // Personality phrases must never block core command or recovery paths.
        }
    }

    private async Task SpeakSystemSequenceAsync(string detail, params string[] phrases)
    {
        foreach (var phrase in phrases.Where(item => !string.IsNullOrWhiteSpace(item)))
        {
            await SpeakSystemPhraseAsync(phrase, detail, startupNotification: true);
            await Task.Delay(325);
        }
    }

    private async Task SpeakCodeAcknowledgementAsync(string command)
    {
        if (!_preferences.EnableVoiceResponses) return;
        var artifact = DescribeRequestedCode(command);
        AvatarStatusText.Text = "CREATING CODE";
        await _avatarService.SetStateAsync(AvatarVisualState.Thinking);
        await SetInlineAvatarStateAsync("thinking", $"Preparing speech for {artifact}");
        var voiceId = _preferences.AvatarProfile.Equals("female", StringComparison.OrdinalIgnoreCase)
            ? _preferences.FemaleVoiceId
            : _preferences.MaleVoiceId;
        var result = await _speechService.SynthesizeAsync(new SpeechRequest
        {
            Text = DevelopmentPhrase,
            VoiceId = voiceId,
            Speed = _desktopOptions.Speech.Speed,
        }, CancellationToken.None);
        if (result.Success)
        {
            AvatarStatusText.Text = "SPEAKING";
            await _avatarService.SetStateAsync(AvatarVisualState.Speaking);
            await SetInlineAvatarStateAsync("speaking", $"Creating {artifact}");
            var playbackError = await PlayInlineSpeechAsync(result);
            if (!string.IsNullOrWhiteSpace(playbackError))
                ConnectionText.Text = $"Speech playback unavailable · {playbackError}";
        }
        else
        {
            ConnectionText.Text = $"Speech acknowledgement unavailable · {result.Detail}";
        }
    }

    private static bool IsCodeCreationRequest(string command)
    {
        var normalized = command.ToLowerInvariant();
        var creationIntent = normalized.Contains("create") || normalized.Contains("write") ||
            normalized.Contains("generate") || normalized.Contains("build") || normalized.Contains("make");
        var codeIntent = normalized.Contains("script") || normalized.Contains("code") ||
            normalized.Contains("function") || normalized.Contains("class") ||
            normalized.Contains("powershell") || normalized.Contains("python") ||
            normalized.Contains("javascript") || normalized.Contains("c#") || normalized.Contains("csharp");
        return creationIntent && codeIntent;
    }

    private static bool IsDiagnosticRequest(string command)
    {
        var normalized = command.ToLowerInvariant();
        return normalized.Contains("diagnos") || normalized.Contains("troubleshoot") ||
            normalized.Contains("health check") || normalized.Contains("system status") ||
            normalized.Contains("analyze the system") || normalized.Contains("find the fault");
    }

    private static string DescribeRequestedCode(string command)
    {
        var normalized = command.ToLowerInvariant();
        if (normalized.Contains("powershell")) return "PowerShell script";
        if (normalized.Contains("python")) return "Python code";
        if (normalized.Contains("javascript")) return "JavaScript code";
        if (normalized.Contains("c#") || normalized.Contains("csharp")) return "C sharp code";
        if (normalized.Contains("script")) return "script";
        return "code";
    }

    private static string PrepareSpokenResponse(string response, string command)
    {
        if (!response.Contains("```", StringComparison.Ordinal)) return response;

        var explanation = Regex.Replace(
            response,
            "```[\\s\\S]*?```",
            string.Empty,
            RegexOptions.CultureInvariant).Trim();
        explanation = Regex.Replace(explanation, "\\s+", " ").Trim();
        var completion = $"{ObjectiveCompletePhrase} The requested {DescribeRequestedCode(command)} is displayed in the command channel.";
        if (explanation.Length == 0) return completion;
        if (explanation.Length > 420) explanation = explanation[..420].TrimEnd() + ".";
        return $"{completion} {explanation}";
    }

    private void AddConversationMessage(string message)
    {
        ConversationList.Items.Add(message);
        Dispatcher.BeginInvoke(() =>
        {
            ConversationScrollViewer.ScrollToEnd();
        }, System.Windows.Threading.DispatcherPriority.Background);
    }

    private void CopyChatButton_Click(object sender, RoutedEventArgs e)
    {
        var transcript = string.Join(Environment.NewLine + Environment.NewLine,
            ConversationList.Items.Cast<object>().Select(item => item?.ToString() ?? string.Empty));
        if (string.IsNullOrWhiteSpace(transcript)) return;
        Clipboard.SetText(transcript);
        ConnectionText.Text = "Conversation copied to clipboard";
    }

    private void CopyConversationSelection_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not MenuItem { Parent: ContextMenu { PlacementTarget: TextBox messageBox } }) return;
        var text = string.IsNullOrEmpty(messageBox.SelectedText) ? messageBox.Text : messageBox.SelectedText;
        if (string.IsNullOrEmpty(text)) return;
        Clipboard.SetText(text);
        ConnectionText.Text = "Selected conversation text copied";
    }


    private async Task ConfigureWakePhraseAsync()
    {
        await _speechRecognition.StopWakePhraseAsync();
        await Task.CompletedTask;
    }

    private void MainWindow_Closed(object? sender, EventArgs e)
    {
        _voiceCaptureCancellation?.Cancel();
        _voiceCaptureCancellation?.Dispose();
        _speechRecognition.AudioLevelChanged -= SpeechRecognition_AudioLevelChanged;
        _speechRecognition.StatusChanged -= SpeechRecognition_StatusChanged;
        _speechRecognition.WakePhraseRecognized -= SpeechRecognition_WakePhraseRecognized;
        _speechRecognition.Dispose();
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
            ConnectionText.Text = $"3D avatar unavailable · {ex.Message}";
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
                ConnectionText.Text = $"3D avatar unavailable · {detail}";
                RestoreNativeAvatar();
            }
        }
        catch (JsonException)
        {
            ConnectionText.Text = "3D avatar unavailable · invalid runtime message";
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
            var source = Path.Combine(current.FullName, "desktop", "Aegis.Desktop", "Assets", assetFolder);
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
        var window = new WorkflowEditorWindow { Owner = this };
        if (window.ShowDialog() == true)
        {
            await LoadWorkflowsAsync();
            if (window.SavedWorkflow is not null)
            {
                var review = new WorkflowDesignReviewWindow(window.SavedWorkflow) { Owner = this };
                if (review.ShowDialog() == true) NotifyWorkflowReevaluation(review.UpdatedWorkflow);
            }
            await LoadWorkflowsAsync();
        }
    }

    private async void ExportWorkflowButton_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not FrameworkElement { Tag: Workflow workflow }) return;
        var safeTitle = Regex.Replace(workflow.Title, "[^A-Za-z0-9._-]+", "-").Trim('-');
        var dialog = new SaveFileDialog
        {
            Filter = "A.E.G.I.S.-9 workflow|*.aegisworkflow",
            FileName = $"{(string.IsNullOrWhiteSpace(safeTitle) ? "workflow" : safeTitle)}.aegisworkflow",
            AddExtension = true,
            DefaultExt = ".aegisworkflow",
        };
        if (dialog.ShowDialog(this) != true) return;
        try
        {
            var contents = await _client.ExportWorkflowAsync(workflow.Id, CancellationToken.None);
            await File.WriteAllBytesAsync(dialog.FileName, contents);
            ConnectionText.Text = $"Workflow exported · {workflow.Title}";
        }
        catch (Exception error)
        {
            MessageBox.Show(this, error.Message, "Workflow export failed", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private async void ImportWorkflowButton_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog
        {
            Filter = "A.E.G.I.S.-9 workflow|*.aegisworkflow",
            Multiselect = false,
            CheckFileExists = true,
        };
        if (dialog.ShowDialog(this) != true) return;
        try
        {
            var result = await _client.ImportWorkflowAsync(dialog.FileName, CancellationToken.None);
            await LoadWorkflowsAsync();
            MessageBox.Show(this, $"{result.Detail}\n\n{result.Workflow.Title}\nState: {result.Workflow.State}\nRevision: {result.Workflow.Revision}", "Workflow transfer", MessageBoxButton.OK, MessageBoxImage.Information);
            ConnectionText.Text = $"Workflow {result.Action} · {result.Workflow.Title}";
        }
        catch (Exception error)
        {
            MessageBox.Show(this, error.Message, "Workflow import failed", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private async void ApproveWorkflowButton_Click(object sender, RoutedEventArgs e)
    {
        if (sender is FrameworkElement { Tag: Workflow workflow })
        {
            if (workflow.State is "draft" or "rejected" or "needs_clarification" or "design_review")
            {
                var review = new WorkflowDesignReviewWindow(workflow) { Owner = this };
                if (review.ShowDialog() == true) NotifyWorkflowReevaluation(review.UpdatedWorkflow);
            }
            else
                new WorkflowApprovalWindow(workflow) { Owner = this }.ShowDialog();
            await LoadWorkflowsAsync();
        }
    }

    private async void EditWorkflowButton_Click(object sender, RoutedEventArgs e)
    {
        if (sender is FrameworkElement { Tag: Workflow workflow } && new WorkflowEditorWindow(workflow) { Owner = this }.ShowDialog() == true) await LoadWorkflowsAsync();
    }

    private async void DeleteWorkflowButton_Click(object sender, RoutedEventArgs e)
    {
        if (sender is FrameworkElement { Tag: Workflow workflow } && new WorkflowDeleteWindow(workflow) { Owner = this }.ShowDialog() == true) await LoadWorkflowsAsync();
    }

    private void OpenWorkflowButton_Click(object sender, RoutedEventArgs e)
    {
        if (sender is FrameworkElement { Tag: Workflow workflow })
        {
            new WorkflowWindow(workflow.Id) { Owner = this }.Show();
        }
    }

    private void OpenMoveItWindow_Click(object sender, RoutedEventArgs e) => OpenMonitorWindow("MoveIT Automation");
    private void OpenFreeFlowWindow_Click(object sender, RoutedEventArgs e) => OpenMonitorWindow("Xerox FreeFlow Core");
    private void OpenQualysWindow_Click(object sender, RoutedEventArgs e) => OpenMonitorWindow("Qualys Vulnerabilities");
    private void OpenServerWindow_Click(object sender, RoutedEventArgs e) => OpenMonitorWindow("Server Status");

    private void OpenOperationsMonitoringCenter_Click(object sender, RoutedEventArgs e)
    {
        var window = new OperationsMonitoringCenterWindow(_preferences) { Owner = this };
        window.OpenMonitorRequested += (_, kind) => OpenMonitorWindow(kind switch
        {
            MonitorWindowKind.MoveIt => "MoveIT Automation",
            MonitorWindowKind.FreeFlow => "Xerox FreeFlow Core",
            MonitorWindowKind.Qualys => "Qualys Vulnerabilities",
            _ => "Server Status"
        });
        window.OpenWorkflowRequested += (_, workflowId) => new WorkflowWindow(workflowId) { Owner = this }.Show();
        window.Show();
    }

    private void OpenMonitorWindow(string title)
    {
        var kind = title switch { "MoveIT Automation" => MonitorWindowKind.MoveIt, "Xerox FreeFlow Core" => MonitorWindowKind.FreeFlow, "Qualys Vulnerabilities" => MonitorWindowKind.Qualys, _ => MonitorWindowKind.ServerStatus };
        var window = new MonitorWindow(kind) { Owner = this };
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
                    AddConversationMessage($"{(message.Role == "assistant" ? "A.E.G.I.S.-9" : "Operator")}  ·  {message.Content}");
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
            SecurityAlertCountText.Text = dashboard.Alerts.Count == 0
                ? "CLEAR"
                : $"{dashboard.Alerts.Count} OPEN";
            SecurityAlertCountText.Foreground = dashboard.Alerts.Count == 0
                ? (Brush)FindResource("Cyan")
                : (Brush)FindResource("Amber");
            if (dashboard.Alerts.Count > 0 && !_alertPhraseSpoken)
            {
                _alertPhraseSpoken = true;
                var alertSummary = dashboard.Alerts.Count == 1
                    ? "One unresolved monitoring alert remains. Review when ready."
                    : $"{dashboard.Alerts.Count} unresolved monitoring alerts remain. Review when ready.";
                await SpeakSystemPhraseAsync(alertSummary, "Monitoring review available", startupNotification: true);
                await _avatarService.SetStateAsync(AvatarVisualState.Idle);
                await SetInlineAvatarStateAsync("ready", "Monitoring review available");
            }
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
            SecurityProviderRouteText.Text = health.Available
                ? health.Location.ToUpperInvariant()
                : "OFFLINE";
            SecurityProviderRouteText.Foreground = health.Available
                ? (Brush)FindResource("Cyan")
                : (Brush)FindResource("Amber");
        }
        catch (Exception error) { ConnectionText.Text = $"Local command center · provider health unavailable: {error.Message}"; }
    }

    private async Task WaitForProviderReadyAsync()
    {
        CommandInput.IsEnabled = false;
        VoiceInputButton.IsEnabled = false;
        AvatarStatusText.Text = "SCANNING AI PROVIDERS";
        AddConversationMessage($"A.E.G.I.S.-9 startup  ·  {ComingOnlinePhrase}");
        await SpeakSystemSequenceAsync(
            "Initializing guardian intelligence",
            ComingOnlinePhrase);
        AddConversationMessage($"A.E.G.I.S.-9 startup  ·  {SearchingProviderPhrase}");
        await SpeakSystemSequenceAsync(
            "Searching for provider",
            SearchingProviderPhrase);
        await _avatarService.SetStateAsync(AvatarVisualState.Thinking);
        await SetInlineAvatarStateAsync("thinking", "Searching for provider");
        for (var attempt = 0; attempt < 90; attempt++)
        {
            try
            {
                var health = await _client.GetProviderHealthAsync(CancellationToken.None);
                ConnectionText.Text = health.Detail.Length > 0 ? health.Detail : "Scanning AI providers...";
                if (health.Status == "ready" && health.Available)
                {
                    ConnectionText.Text = $"{health.Location.ToUpperInvariant()} command center · {health.Provider} · {health.Model}";
                    SecurityProviderRouteText.Text = health.Location.ToUpperInvariant();
                    SecurityProviderRouteText.Foreground = (Brush)FindResource("Cyan");
                    AddConversationMessage($"Provider verified  ·  {health.Location.ToUpperInvariant()} · {health.Provider} · {health.Model}");
                    if (!string.IsNullOrWhiteSpace(health.Recommendation))
                    {
                        AddConversationMessage($"Provider analysis  ·  {health.Recommendation}");
                    }
                    var confirmationPhrases = new[]
                    {
                        "Armor integrity confirmed.",
                        "F.E.R.A.L. neural core synchronized.",
                        "Pack link established. Ready to assist.",
                        "Aegis 9 is online."
                    };
                    foreach (var phrase in confirmationPhrases)
                    {
                        AddConversationMessage($"A.E.G.I.S.-9 startup  ·  {phrase}");
                    }
                    await SpeakSystemSequenceAsync(
                        "F.E.R.A.L. neural core synchronized",
                        confirmationPhrases);
                    await _avatarService.SetStateAsync(AvatarVisualState.Idle);
                    await SetInlineAvatarStateAsync("ready", "Pack link established");
                    CommandInput.IsEnabled = true;
                    VoiceInputButton.IsEnabled = true;
                    AvatarStatusText.Text = "READY FOR COMMANDS";
                    return;
                }
                if (health.Status == "unavailable") break;
            }
            catch (Exception error)
            {
                ConnectionText.Text = $"Waiting for provider discovery · {error.Message}";
            }
            await Task.Delay(500);
        }
        ConnectionText.Text = "AI providers unavailable · check local services and diagnostics";
        AvatarStatusText.Text = "PROVIDER OFFLINE";
    }

    private async Task ShowProviderTransitionAsync(ProviderFailover failover)
    {
        _providerTransitionAcknowledgement = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        ProviderTransitionText.Text =
            $"Previous route: {failover.PreviousLocation.ToUpperInvariant()} · {failover.PreviousProvider} · {failover.PreviousModel}\n\n" +
            $"Active fallback: {failover.ActiveLocation.ToUpperInvariant()} · {failover.ActiveProvider} · {failover.ActiveModel}\n\n" +
            failover.Reason;
        ProviderTransitionOverlay.Visibility = Visibility.Visible;
        ProviderTransitionOverlay.Focus();
        await SpeakSystemPhraseAsync(NeuralLinkInterruptedPhrase, "Remote neural link interrupted");
        await _providerTransitionAcknowledgement.Task;
    }

    private void AcknowledgeProviderTransitionButton_Click(object sender, RoutedEventArgs e)
    {
        ProviderTransitionOverlay.Visibility = Visibility.Collapsed;
        _providerTransitionAcknowledgement?.TrySetResult(true);
        _providerTransitionAcknowledgement = null;
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
        try
        {
            var workflows = await _client.GetWorkflowsAsync(CancellationToken.None);
            RecentWorkflowList.ItemsSource = workflows.Where(item => item.State is "running" or "paused" or "completed" or "failed" or "scheduled").Take(3).ToList();
            PendingWorkflowList.ItemsSource = workflows.Where(item => item.State is not ("running" or "paused" or "completed" or "failed" or "scheduled")).ToList();
            await Dispatcher.BeginInvoke(() => RenameWorkflowReviewButtons(PendingWorkflowList));
        }
        catch (Exception error) { ConnectionText.Text = $"Workflow supervisor unavailable: {error.Message}"; }
    }

    private static void RenameWorkflowReviewButtons(DependencyObject root)
    {
        for (var index = 0; index < VisualTreeHelper.GetChildrenCount(root); index++)
        {
            var child = VisualTreeHelper.GetChild(root, index);
            if (child is Button { DataContext: Workflow workflow } button)
            {
                var needsReview = workflow.State is "draft" or "rejected" or "needs_clarification" or "design_review";
                if (Equals(button.Content, "APPROVE")) button.Content = needsReview ? "REVIEW" : "APPROVE / REJECT";
                else if (needsReview && (Equals(button.Content, "EDIT") || Equals(button.Content, "DELETE"))) button.IsEnabled = false;
            }
            RenameWorkflowReviewButtons(child);
        }
    }

    private void NotifyWorkflowReevaluation(Workflow? workflow)
    {
        if (workflow is null) return;
        if (workflow.State == "plan_review")
        {
            ConnectionText.Text = $"READY FOR APPROVAL · {workflow.Title}";
            MessageBox.Show(this, $"A.E.G.I.S.-9 completed re-evaluation of '{workflow.Title}'.\n\nThe refined workflow plan is ready for your review. Select APPROVE / REJECT in the Workflow Center.", "Workflow plan ready", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        else if (workflow.State == "needs_clarification")
        {
            ConnectionText.Text = $"ADDITIONAL REVIEW REQUIRED · {workflow.Title}";
            MessageBox.Show(this, $"A.E.G.I.S.-9 completed re-evaluation of '{workflow.Title}' and identified additional required questions.\n\nSelect REVIEW to continue.", "Additional workflow information required", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }
}
