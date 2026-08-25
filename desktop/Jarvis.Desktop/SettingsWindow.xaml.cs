using System.Diagnostics;
using System.IO;
using System.Windows;
using System.Windows.Media;

namespace Jarvis.Desktop;

public partial class SettingsWindow : Window
{
    private readonly UserPreferences _preferences;
    private readonly JarvisDesktopOptions _options = JarvisDesktopOptions.Load();

    public SettingsWindow(UserPreferences preferences)
    {
        _preferences = preferences;
        InitializeComponent();
        EnterSendsMessageCheckBox.IsChecked = _preferences.EnterSendsMessage;
        AvatarNameInput.Text = _preferences.AvatarName;
        AvatarThemeInput.SelectedValue = _preferences.AvatarTheme;
        AvatarProfileInput.SelectedValue = _preferences.AvatarProfile;
        AvatarChoiceInput.SelectedValue = _preferences.SelectedAvatarId;
        MaleVoiceInput.Text = _preferences.MaleVoiceId;
        FemaleVoiceInput.Text = _preferences.FemaleVoiceId;
        UseThreeDAvatarCheckBox.IsChecked = _preferences.UseThreeDimensionalAvatar;
        EnableLipSyncCheckBox.IsChecked = _preferences.EnableLipSync;
    }

    private void OpenServerListButton_Click(object sender, RoutedEventArgs e)
    {
        var path = FindWorkspaceFile(Path.Combine("config", "monitored-servers.json"));
        OpenInEditor(path);
        StatusText.Text = path == null ? "Server inventory file was not found." : "Opened monitored server inventory.";
    }

    private void OpenEnvironmentButton_Click(object sender, RoutedEventArgs e)
    {
        var path = FindWorkspaceFile(".env");
        if (path == null)
        {
            var example = FindWorkspaceFile(".env.example");
            if (example != null)
            {
                path = Path.Combine(Path.GetDirectoryName(example)!, ".env");
                File.Copy(example, path);
            }
        }
        OpenInEditor(path);
        StatusText.Text = path == null ? "Local .env file could not be created." : "Opened local credentials configuration.";
    }

    private static string? FindWorkspaceFile(string relativePath)
    {
        for (var directory = new DirectoryInfo(AppDomain.CurrentDomain.BaseDirectory); directory != null; directory = directory.Parent)
        {
            var path = Path.Combine(directory.FullName, relativePath);
            if (File.Exists(path)) return path;
        }
        return null;
    }

    private static void OpenInEditor(string? path)
    {
        if (path != null) Process.Start(new ProcessStartInfo("notepad.exe", $"\"{path}\"") { UseShellExecute = false });
    }

    private void CloseButton_Click(object sender, RoutedEventArgs e) => Close();

    private async void PreviewVoiceButton_Click(object sender, RoutedEventArgs e)
    {
        var profile = AvatarProfileInput.SelectedValue as string ?? "male";
        var voice = profile.Equals("female", StringComparison.OrdinalIgnoreCase)
            ? (string.IsNullOrWhiteSpace(FemaleVoiceInput.Text) ? "af_heart" : FemaleVoiceInput.Text.Trim())
            : (string.IsNullOrWhiteSpace(MaleVoiceInput.Text) ? "am_fenrir" : MaleVoiceInput.Text.Trim());

        var speechService = new KokoroSpeechService(_options.Speech);
        var result = await speechService.SynthesizeAsync(new SpeechRequest
        {
            Text = "Jarvis voice preview is ready.",
            VoiceId = voice,
            Speed = _options.Speech.Speed,
        }, CancellationToken.None);

        if (!result.Success || string.IsNullOrWhiteSpace(result.AudioPath) || !File.Exists(result.AudioPath))
        {
            StatusText.Text = $"Voice preview unavailable: {result.Detail}";
            return;
        }

        var player = new MediaPlayer();
        player.Open(new Uri(result.AudioPath));
        player.Play();
        StatusText.Text = $"Playing preview voice '{voice}'.";
    }

    protected override void OnClosed(EventArgs e)
    {
        _preferences.EnterSendsMessage = EnterSendsMessageCheckBox.IsChecked == true;
        _preferences.AvatarName = string.IsNullOrWhiteSpace(AvatarNameInput.Text) ? "Jarvis" : AvatarNameInput.Text.Trim();
        _preferences.AvatarTheme = AvatarThemeInput.SelectedValue as string ?? "Emerald";
        _preferences.AvatarProfile = AvatarProfileInput.SelectedValue as string ?? "male";
        _preferences.SelectedAvatarId = AvatarChoiceInput.SelectedValue as string ?? "jarvis-male-dev";
        _preferences.MaleVoiceId = string.IsNullOrWhiteSpace(MaleVoiceInput.Text) ? "am_fenrir" : MaleVoiceInput.Text.Trim();
        _preferences.FemaleVoiceId = string.IsNullOrWhiteSpace(FemaleVoiceInput.Text) ? "af_heart" : FemaleVoiceInput.Text.Trim();
        _preferences.UseThreeDimensionalAvatar = UseThreeDAvatarCheckBox.IsChecked == true;
        _preferences.EnableLipSync = EnableLipSyncCheckBox.IsChecked == true;
        _preferences.Save();
        base.OnClosed(e);
    }
}
