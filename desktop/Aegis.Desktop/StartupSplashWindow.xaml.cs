using System.Collections.ObjectModel;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.IO;
using System.Text.Json;
using System.Threading.Channels;
using Microsoft.Web.WebView2.Core;
using NAudio;
using NAudio.Wave;

namespace Aegis.Desktop;

public partial class StartupSplashWindow : Window
{
    private readonly StartupCoordinator _coordinator;
    private readonly StartupState _state;
    private readonly CancellationTokenSource _closing = new();
    private readonly ObservableCollection<CheckRow> _rows = [];
    private readonly Channel<string> _speechQueue = Channel.CreateUnbounded<string>(new UnboundedChannelOptions { SingleReader = true });
    private readonly Dictionary<string, StartupCheckState> _announcedStates = [];
    private readonly ISpeechService _speechService;
    private readonly SpeechOptions _speechOptions;
    private Task? _speechTask;
    private bool _avatarRuntimeReady;
    private bool _avatarLoadRequested;
    private const string SplashAvatarId = "aegis9-head-splash";
    private string _avatarRuntimeDetail = "AEGIS AO visual core initializing.";
    public bool Entered { get; private set; }
    public StartupState StartupState => _state;
    public event Action<StartupSplashWindow>? EntryRequested;

    public StartupSplashWindow(StartupCoordinator coordinator)
    {
        _coordinator = coordinator; _state = coordinator.CreateState();
        _speechOptions = AegisDesktopOptions.Load().Speech;
        _speechService = new KokoroSpeechService(_speechOptions);
        InitializeComponent(); ChecksList.ItemsSource = _rows;
        foreach (var check in _state.Checks) _rows.Add(new CheckRow(check));
        _coordinator.CheckChanged += OnCheckChanged; Loaded += OnLoaded; Closed += OnClosed;
    }

    private async void OnLoaded(object sender, RoutedEventArgs e)
    {
        try
        {
            await InitializeAvatarAsync();
            _speechTask = RunSpeechQueueAsync(_closing.Token);
            QueueSpeech("Aegis guardian startup sequence initiated.");
            await _coordinator.RunAsync(_state, _closing.Token);
            ApplyAvatarResult();
            if (_state.Failure is null)
            {
                QueueSpeech("All required startup checks passed. Aegis is ready.");
                ShowSuccess();
            }
            else
            {
                ShowFailure(_state.Failure);
            }
        }
        catch (OperationCanceledException) { }
        catch (Exception ex) { DecisionText.Text = $"Startup halted: {ex.Message}"; ShowFailure(null); }
    }
    private void OnCheckChanged(StartupCheckResult check) => Dispatcher.Invoke(() =>
    {
        var i = _state.Checks.IndexOf(check);
        _rows[i] = new CheckRow(check);
        SequenceText.Text = check.State == StartupCheckState.Running ? $"VERIFYING / {check.Name.ToUpperInvariant()}" : "GUARDIAN SEQUENCE";
        if (!_announcedStates.TryGetValue(check.Id, out var announced) || announced != check.State)
        {
            _announcedStates[check.Id] = check.State;
            var announcement = check.State switch
            {
                StartupCheckState.Running => $"Checking {check.Name}.",
                StartupCheckState.Passed => $"{check.Name} verified.",
                StartupCheckState.Warning => $"{check.Name} completed with a warning.",
                StartupCheckState.Failed => $"{check.Name} failed. Startup is halted.",
                _ => null
            };
            if (announcement is not null) QueueSpeech(announcement);
        }
    });
    private void ShowSuccess() { SequenceText.Text = "ALL REQUIRED GATES PASSED"; DecisionText.Text = "Guardian systems are ready. Operator confirmation is required to enter the command center."; ContinueButton.Visibility = Visibility.Visible; ((Storyboard)FindResource("Pulse")).Begin(ContinueButton); ContinueButton.Focus(); }
    private void ShowFailure(StartupCheckResult? failure) { SequenceText.Text = "SEQUENCE HALTED"; DecisionText.Text = failure == null ? DecisionText.Text : $"{failure.Name} failed — {failure.Detail}\nResolution: {failure.Resolution}"; DegradedButton.Visibility = DiagnosticButton.Visibility = CloseButton.Visibility = Visibility.Visible; DegradedButton.Focus(); }
    private void Continue_Click(object sender, RoutedEventArgs e) => Enter(false);
    private void Degraded_Click(object sender, RoutedEventArgs e) => Enter(true);
    private void Enter(bool degraded) { Entered = true; _state.Degraded = degraded; EntryRequested?.Invoke(this); }
    private void Diagnostic_Click(object sender, RoutedEventArgs e) { try { var app = (App)Application.Current; var path = StartupDiagnosticWriter.Write(_state, app.BackendDirectory, app.PythonExecutable); DecisionText.Text = $"Diagnostic report written to {path}"; } catch (Exception ex) { DecisionText.Text = $"Diagnostic report could not be written: {StartupCoordinator.Sanitize(ex.Message)}. Verify write access to the local application data folder."; } }
    private async void Close_Click(object sender, RoutedEventArgs e) { CloseButton.IsEnabled = false; DecisionText.Text = "Stopping owned services…"; _closing.Cancel(); await ((App)Application.Current).ShutdownOwnedBackendAsync(); }
    private void Root_MouseLeftButtonDown(object sender, MouseButtonEventArgs e) { if (e.ChangedButton == MouseButton.Left) DragMove(); }
    private async Task InitializeAvatarAsync()
    {
        try
        {
            var host = ResolveAsset("AvatarHost"); var assets = ResolveAsset("Avatars");
            await AvatarWebView.EnsureCoreWebView2Async().WaitAsync(TimeSpan.FromSeconds(15), _closing.Token);
            AvatarWebView.DefaultBackgroundColor = System.Drawing.Color.Transparent;
            var core = AvatarWebView.CoreWebView2; core.Settings.AreDevToolsEnabled = false; core.Settings.AreDefaultContextMenusEnabled = false; core.Settings.IsStatusBarEnabled = false;
            core.SetVirtualHostNameToFolderMapping("jarvis.local", host, CoreWebView2HostResourceAccessKind.DenyCors); core.SetVirtualHostNameToFolderMapping("jarvis-assets.local", assets, CoreWebView2HostResourceAccessKind.Allow);
            var ready = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
            core.WebMessageReceived += (_, e) =>
            {
                try
                {
                    var message = JsonSerializer.Deserialize<AvatarMessage>(e.WebMessageAsJson);
                    if (message?.Type == "avatar.ready" && message.Payload.TryGetProperty("avatarId", out var id))
                    {
                        var avatarId = id.GetString();
                        if (avatarId == "unloaded")
                        {
                            Dispatcher.BeginInvoke(RequestAvatarLoad);
                        }
                        else if (avatarId == SplashAvatarId)
                        {
                            ready.TrySetResult(true);
                            Dispatcher.BeginInvoke(ShowLoadedAvatar);
                        }
                    }
                    else if (message?.Type == "avatar.error")
                    {
                        ready.TrySetResult(false);
                        Dispatcher.BeginInvoke(() => ShowAvatarFallback("3D VISUAL CORE UNAVAILABLE", "3D visual core unavailable; branded guardian telemetry remains active."));
                    }
                }
                catch (Exception ex)
                {
                    ready.TrySetResult(false);
                    Dispatcher.BeginInvoke(() => ShowAvatarFallback("3D VISUAL CORE UNAVAILABLE", $"3D visual core message failed. {StartupCoordinator.Sanitize(ex.Message)}"));
                }
            };
            core.NavigationCompleted += (_, e) => { if (!e.IsSuccess) ready.TrySetResult(false); };
            AvatarWebView.Visibility = Visibility.Visible;
            core.Navigate("https://jarvis.local/index.html");
            try
            {
                _avatarRuntimeReady = await ready.Task.WaitAsync(TimeSpan.FromSeconds(30), _closing.Token);
            }
            catch (TimeoutException)
            {
                _avatarRuntimeReady = false;
                _avatarRuntimeDetail = "AEGIS animated avatar visual core is still loading and will appear when ready.";
                AvatarFallbackDetail.Text = "VISUAL CORE STILL INITIALIZING";
                return;
            }
            if (_avatarRuntimeReady) ShowLoadedAvatar();
            else ShowAvatarFallback("3D VISUAL CORE UNAVAILABLE", "3D visual core unavailable; branded guardian telemetry remains active.");
        }
        catch (OperationCanceledException) when (_closing.IsCancellationRequested) { }
        catch (Exception ex) { ShowAvatarFallback("3D VISUAL CORE UNAVAILABLE", $"3D visual core unavailable. {StartupCoordinator.Sanitize(ex.Message)}"); }
    }
    private void RequestAvatarLoad()
    {
        if (_avatarLoadRequested || _closing.IsCancellationRequested || AvatarWebView.CoreWebView2 is null) return;
        _avatarLoadRequested = true;
        AvatarWebView.CoreWebView2.PostWebMessageAsJson(AvatarProtocol.Build("avatar.load", new
        {
            manifestUrl = "https://jarvis-assets.local/shared/splash-avatar.json",
            selectedAvatarId = SplashAvatarId,
            compact = true,
            presentation = "splash"
        }));
    }
    private void QueueSpeech(string text)
    {
        if (!_closing.IsCancellationRequested) _speechQueue.Writer.TryWrite(text);
    }
    private async Task RunSpeechQueueAsync(CancellationToken token)
    {
        try
        {
            await foreach (var text in _speechQueue.Reader.ReadAllAsync(token))
            {
                var result = await _speechService.SynthesizeAsync(new SpeechRequest
                {
                    Text = text,
                    VoiceId = _speechOptions.MaleVoiceId,
                    Speed = _speechOptions.Speed,
                    CorrelationId = $"startup-{Guid.NewGuid():N}"
                }, token);
                if (!result.Success || string.IsNullOrWhiteSpace(result.AudioPath)) continue;

                var audioPath = Path.IsPathFullyQualified(result.AudioPath)
                    ? result.AudioPath
                    : Path.GetFullPath(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), result.AudioPath));
                if (!File.Exists(audioPath) || AvatarWebView.CoreWebView2 is null) continue;

                await Dispatcher.InvokeAsync(() => AvatarWebView.CoreWebView2?.PostWebMessageAsJson(
                    AvatarProtocol.Build("avatar.state", new { state = "speaking", detail = text })));
                try
                {
                    using var reader = new AudioFileReader(audioPath);
                    using var output = new WaveOutEvent();
                    var completion = new TaskCompletionSource<Exception?>(TaskCreationOptions.RunContinuationsAsynchronously);
                    output.PlaybackStopped += (_, args) => completion.TrySetResult(args.Exception);
                    output.Init(reader);
                    output.Play();
                    await completion.Task.WaitAsync(token);
                }
                catch (Exception error) when (error is InvalidOperationException or IOException or MmException)
                {
                    // A missing audio device must not stop the readiness sequence.
                }
                finally
                {
                    if (!token.IsCancellationRequested)
                    {
                        await Dispatcher.InvokeAsync(() => AvatarWebView.CoreWebView2?.PostWebMessageAsJson(
                            AvatarProtocol.Build("avatar.state", new { state = "idle", detail = "Guardian startup sequence" })));
                    }
                }
            }
        }
        catch (OperationCanceledException) when (token.IsCancellationRequested) { }
        catch { /* Speech is optional and must never block the startup gate. */ }
    }
    private void ShowLoadedAvatar()
    {
        if (_closing.IsCancellationRequested || !IsLoaded || AvatarWebView.CoreWebView2 is null) return;
        _avatarRuntimeReady = true;
        _avatarRuntimeDetail = "A.E.G.I.S.-9 animated avatar head visual core ready.";
        AvatarWebView.Visibility = Visibility.Visible;
        AvatarFallback.Visibility = Visibility.Collapsed;
        AvatarWebView.CoreWebView2.PostWebMessageAsJson(AvatarProtocol.Build("avatar.state", new { state = "idle", detail = "Guardian startup sequence" }));
        ApplyAvatarResult();
    }
    private void ShowAvatarFallback(string label, string detail)
    {
        if (_closing.IsCancellationRequested || !IsLoaded) return;
        _avatarRuntimeReady = false;
        _avatarRuntimeDetail = detail;
        AvatarWebView.Visibility = Visibility.Collapsed;
        AvatarFallback.Visibility = Visibility.Visible;
        AvatarFallbackDetail.Text = label;
        ApplyAvatarResult();
    }
    private void ApplyAvatarResult() { var check = _state.Checks.Single(x => x.Id == "avatar"); check.State = _avatarRuntimeReady ? StartupCheckState.Passed : StartupCheckState.Warning; check.Detail = _avatarRuntimeDetail; OnCheckChanged(check); }
    private static string ResolveAsset(string name) { for (var d = new DirectoryInfo(AppDomain.CurrentDomain.BaseDirectory); d != null; d = d.Parent) { var a = Path.Combine(d.FullName, "Assets", name); if (Directory.Exists(a)) return a; var s = Path.Combine(d.FullName, "desktop", "Aegis.Desktop", "Assets", name); if (Directory.Exists(s)) return s; } throw new DirectoryNotFoundException($"{name} assets were not found."); }
    private void OnClosed(object? sender, EventArgs e) { _speechQueue.Writer.TryComplete(); _closing.Cancel(); _coordinator.CheckChanged -= OnCheckChanged; ((Storyboard)FindResource("Orbit")).Remove(this); ((Storyboard)FindResource("Pulse")).Remove(ContinueButton); AvatarWebView.Dispose(); _closing.Dispose(); }
    private sealed record CheckRow(string Name, string Status, string Detail, string Timing, string Symbol, Brush Brush)
    {
        public CheckRow(StartupCheckResult x) : this(x.Name, x.State.ToString().ToUpperInvariant(), x.Detail, x.DurationMs > 0 ? $"{x.DurationMs} ms" : "—", x.State switch { StartupCheckState.Passed => "✓", StartupCheckState.Warning => "!", StartupCheckState.Failed => "×", StartupCheckState.Running => "◆", _ => "○" }, new SolidColorBrush((Color)ColorConverter.ConvertFromString(x.State switch { StartupCheckState.Passed => "#4DE7FF", StartupCheckState.Warning or StartupCheckState.Failed => "#FFB74D", StartupCheckState.Running => "#B7F8FF", _ => "#527A86" }))) { }
    }
}
