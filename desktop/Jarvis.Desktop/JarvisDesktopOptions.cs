using System.Text.Json;
using System.IO;

namespace Jarvis.Desktop;

public sealed class JarvisDesktopOptions
{
    public AvatarOptions Avatar { get; set; } = new();
    public SpeechOptions Speech { get; set; } = new();

    public static JarvisDesktopOptions Load()
    {
        var path = ResolveSettingsPath();
        if (!File.Exists(path))
        {
            return new JarvisDesktopOptions();
        }

        try
        {
            using var stream = File.OpenRead(path);
            using var document = JsonDocument.Parse(stream);
            var root = document.RootElement;
            var options = new JarvisDesktopOptions();

            if (root.TryGetProperty("avatar", out var avatar))
            {
                options.Avatar.Enabled = avatar.TryGetProperty("enabled", out var enabled) ? enabled.GetBoolean() : true;
                options.Avatar.UseNativeFallback = avatar.TryGetProperty("useNativeFallback", out var fallback) ? fallback.GetBoolean() : true;
                options.Avatar.EnableLipSync = avatar.TryGetProperty("enableLipSync", out var lipSync) ? lipSync.GetBoolean() : true;
                options.Avatar.EnableBlinking = avatar.TryGetProperty("enableBlinking", out var blinking) ? blinking.GetBoolean() : true;
                options.Avatar.SelectedAvatarId = avatar.TryGetProperty("selectedAvatarId", out var selectedAvatarId) ? selectedAvatarId.GetString() ?? options.Avatar.SelectedAvatarId : options.Avatar.SelectedAvatarId;
            }

            if (root.TryGetProperty("speech", out var speech))
            {
                options.Speech.Provider = speech.TryGetProperty("provider", out var provider) ? provider.GetString() ?? options.Speech.Provider : options.Speech.Provider;
                options.Speech.MaleVoiceId = speech.TryGetProperty("maleVoiceId", out var maleVoiceId) ? maleVoiceId.GetString() ?? options.Speech.MaleVoiceId : options.Speech.MaleVoiceId;
                options.Speech.FemaleVoiceId = speech.TryGetProperty("femaleVoiceId", out var femaleVoiceId) ? femaleVoiceId.GetString() ?? options.Speech.FemaleVoiceId : options.Speech.FemaleVoiceId;
                options.Speech.Speed = speech.TryGetProperty("speed", out var speed) ? speed.GetDouble() : options.Speech.Speed;
                options.Speech.StartupTimeoutSeconds = speech.TryGetProperty("startupTimeoutSeconds", out var startupTimeout) ? startupTimeout.GetInt32() : options.Speech.StartupTimeoutSeconds;
                options.Speech.RequestTimeoutSeconds = speech.TryGetProperty("requestTimeoutSeconds", out var requestTimeout) ? requestTimeout.GetInt32() : options.Speech.RequestTimeoutSeconds;
                options.Speech.LocalEndpoint = speech.TryGetProperty("localEndpoint", out var localEndpoint) ? localEndpoint.GetString() ?? options.Speech.LocalEndpoint : options.Speech.LocalEndpoint;
            }

            return options;
        }
        catch
        {
            return new JarvisDesktopOptions();
        }
    }

    private static string ResolveSettingsPath()
    {
        var current = new DirectoryInfo(AppDomain.CurrentDomain.BaseDirectory);
        while (current is not null)
        {
            var local = Path.Combine(current.FullName, "appsettings.json");
            if (File.Exists(local))
            {
                return local;
            }

            var source = Path.Combine(current.FullName, "desktop", "Jarvis.Desktop", "appsettings.json");
            if (File.Exists(source))
            {
                return source;
            }

            current = current.Parent;
        }

        return "appsettings.json";
    }
}

public sealed class AvatarOptions
{
    public bool Enabled { get; set; } = true;
    public string SelectedAvatarId { get; set; } = "jarvis-male-dev";
    public bool UseNativeFallback { get; set; } = true;
    public bool EnableLipSync { get; set; } = true;
    public bool EnableBlinking { get; set; } = true;
}

public sealed class SpeechOptions
{
    public string Provider { get; set; } = "kokoro-local";
    public string MaleVoiceId { get; set; } = "am_fenrir";
    public string FemaleVoiceId { get; set; } = "af_heart";
    public double Speed { get; set; } = 1.0;
    public int StartupTimeoutSeconds { get; set; } = 30;
    public int RequestTimeoutSeconds { get; set; } = 120;
    public string LocalEndpoint { get; set; } = "http://127.0.0.1:5050";
}
