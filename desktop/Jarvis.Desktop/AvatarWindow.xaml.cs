using System.IO;
using System.Text.Json;
using System.Windows;
using Microsoft.Web.WebView2.Core;

namespace Jarvis.Desktop;

public partial class AvatarWindow : Window
{
    private readonly UserPreferences _preferences;
    private readonly AvatarAssetCatalog _catalog = new();
    private AvatarDefinition? _activeDefinition;
    private bool _runtimeReady;
    private string? _runtimeRoot;
    private string? _assetsRoot;

    public AvatarWindow(UserPreferences preferences)
    {
        _preferences = preferences;
        InitializeComponent();
        Loaded += AvatarWindow_Loaded;
        Closed += AvatarWindow_Closed;
    }

    public async Task SendMessageAsync(string messageJson, CancellationToken cancellationToken = default)
    {
        if (AvatarWebView.CoreWebView2 is null || !_runtimeReady)
        {
            return;
        }

        cancellationToken.ThrowIfCancellationRequested();
        AvatarWebView.CoreWebView2.PostWebMessageAsJson(messageJson);
        await Task.CompletedTask;
    }

    public async Task SetAvatarStateAsync(string state, string detail)
    {
        var payload = new
        {
            state,
            detail,
        };
        await SendMessageAsync(AvatarProtocol.Build("avatar.state", payload));
    }

    public async Task LoadAvatarAsync(AvatarDefinition definition, CancellationToken cancellationToken = default)
    {
        _activeDefinition = definition;
        if (AvatarWebView.CoreWebView2 is null || !_runtimeReady)
        {
            return;
        }

        cancellationToken.ThrowIfCancellationRequested();

        if (string.IsNullOrWhiteSpace(_assetsRoot))
        {
            throw new InvalidOperationException("Avatar assets root is not available.");
        }

        var manifestFile = Path.Combine(_assetsRoot, definition.Profile, "avatar.json");
        if (!File.Exists(manifestFile))
        {
            manifestFile = Path.Combine(_assetsRoot, definition.Profile, "manifest.json");
        }
        if (!File.Exists(manifestFile))
        {
            throw new InvalidOperationException($"Avatar manifest is missing for profile '{definition.Profile}'.");
        }

        var manifestUrl = $"https://jarvis-assets.local/{definition.Profile}/{Path.GetFileName(manifestFile)}";
        var payload = new
        {
            manifestUrl,
            selectedAvatarId = definition.Id,
            lipSyncEnabled = _preferences.EnableLipSync,
            voiceId = definition.VoiceId,
        };
        await SendMessageAsync(AvatarProtocol.Build("avatar.load", payload), cancellationToken);
    }

    private async void AvatarWindow_Loaded(object sender, RoutedEventArgs e)
    {
        var selection = _catalog.GetSelection(_preferences.AvatarProfile);
        if (!selection.IsAvailable || selection.Definition is null)
        {
            HeaderText.Text = "3D AVATAR HOST";
            SubHeaderText.Text = "Fallback mode";
            FallbackDetailText.Text = selection.Detail;
            LicenseText.Text = string.Empty;
            AvatarWebView.Visibility = Visibility.Collapsed;
            FallbackPanel.Visibility = Visibility.Visible;
            return;
        }

        _activeDefinition = selection.Definition;
        HeaderText.Text = $"3D AVATAR HOST · {_activeDefinition.DisplayName}";
        SubHeaderText.Text = $"Profile: {_activeDefinition.Profile} · Format: {_activeDefinition.Format}";
        LicenseText.Text = $"License: {_activeDefinition.LicenseName}";

        try
        {
            _runtimeRoot = ResolveHostRuntimeRoot();
            _assetsRoot = ResolveAvatarsRoot();
            await AvatarWebView.EnsureCoreWebView2Async();
            ConfigureWebView(AvatarWebView.CoreWebView2, _runtimeRoot, _assetsRoot);
            AvatarWebView.CoreWebView2.WebMessageReceived += CoreWebView2_WebMessageReceived;
            AvatarWebView.CoreWebView2.NavigationCompleted += CoreWebView2_NavigationCompleted;
            AvatarWebView.CoreWebView2.Navigate("https://jarvis.local/index.html");

            AvatarWebView.Visibility = Visibility.Visible;
            FallbackPanel.Visibility = Visibility.Collapsed;
            FallbackDetailText.Text = string.Empty;
        }
        catch (Exception ex) when (ex is InvalidOperationException or WebView2RuntimeNotFoundException)
        {
            AvatarWebView.Visibility = Visibility.Collapsed;
            FallbackPanel.Visibility = Visibility.Visible;
            SubHeaderText.Text = "Fallback mode";
            FallbackDetailText.Text = $"WebView2 runtime is unavailable. {ex.Message}";
        }
    }

    private void ConfigureWebView(CoreWebView2 core, string runtimeRoot, string assetsRoot)
    {
        core.Settings.AreDevToolsEnabled = false;
        core.Settings.IsStatusBarEnabled = false;
        core.Settings.AreDefaultContextMenusEnabled = false;
        core.Settings.AreHostObjectsAllowed = false;
        core.SetVirtualHostNameToFolderMapping("jarvis.local", runtimeRoot, CoreWebView2HostResourceAccessKind.DenyCors);
        core.SetVirtualHostNameToFolderMapping("jarvis-assets.local", assetsRoot, CoreWebView2HostResourceAccessKind.DenyCors);
    }

    private async void CoreWebView2_NavigationCompleted(object? sender, CoreWebView2NavigationCompletedEventArgs e)
    {
        if (!e.IsSuccess)
        {
            _runtimeReady = false;
            FallbackPanel.Visibility = Visibility.Visible;
            AvatarWebView.Visibility = Visibility.Collapsed;
            FallbackDetailText.Text = "Avatar runtime page failed to load.";
            return;
        }

        _runtimeReady = true;
        if (_activeDefinition is not null)
        {
            await LoadAvatarAsync(_activeDefinition);
        }
    }

    private async void CoreWebView2_WebMessageReceived(object? sender, CoreWebView2WebMessageReceivedEventArgs e)
    {
        try
        {
            var message = JsonSerializer.Deserialize<AvatarMessage>(e.WebMessageAsJson);
            if (message is null || message.Version != 1 || string.IsNullOrWhiteSpace(message.Type))
            {
                return;
            }

            switch (message.Type)
            {
                case "avatar.ready":
                    SubHeaderText.Text = "Runtime ready";
                    break;
                case "avatar.error":
                    AvatarWebView.Visibility = Visibility.Collapsed;
                    FallbackPanel.Visibility = Visibility.Visible;
                    SubHeaderText.Text = "Fallback mode";
                    FallbackDetailText.Text = message.Payload.TryGetProperty("message", out var detail)
                        ? detail.GetString() ?? "Unknown runtime error."
                        : "Unknown runtime error.";
                    break;
            }
        }
        catch (JsonException)
        {
            await Task.CompletedTask;
        }
    }

    private static string ResolveHostRuntimeRoot()
    {
        var current = new DirectoryInfo(AppDomain.CurrentDomain.BaseDirectory);
        while (current is not null)
        {
            var local = Path.Combine(current.FullName, "Assets", "AvatarHost");
            if (Directory.Exists(local))
            {
                return local;
            }

            var source = Path.Combine(current.FullName, "desktop", "Jarvis.Desktop", "Assets", "AvatarHost");
            if (Directory.Exists(source))
            {
                return source;
            }

            current = current.Parent;
        }

        throw new InvalidOperationException("Avatar host runtime directory was not found.");
    }

    private static string ResolveAvatarsRoot()
    {
        var current = new DirectoryInfo(AppDomain.CurrentDomain.BaseDirectory);
        while (current is not null)
        {
            var local = Path.Combine(current.FullName, "Assets", "Avatars");
            if (Directory.Exists(local))
            {
                return local;
            }

            var source = Path.Combine(current.FullName, "desktop", "Jarvis.Desktop", "Assets", "Avatars");
            if (Directory.Exists(source))
            {
                return source;
            }

            current = current.Parent;
        }

        throw new InvalidOperationException("Avatar assets directory was not found.");
    }

    private void AvatarWindow_Closed(object? sender, EventArgs e)
    {
        if (AvatarWebView.CoreWebView2 is not null)
        {
            AvatarWebView.CoreWebView2.WebMessageReceived -= CoreWebView2_WebMessageReceived;
            AvatarWebView.CoreWebView2.NavigationCompleted -= CoreWebView2_NavigationCompleted;
        }

        _runtimeReady = false;
    }

    private void CloseButton_Click(object sender, RoutedEventArgs e) => Close();
}
