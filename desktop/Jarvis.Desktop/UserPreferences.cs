using System.IO;
using System.Text.Json;

namespace Jarvis.Desktop;

public sealed class UserPreferences
{
    public bool EnterSendsMessage { get; set; } = true;
    public string AvatarName { get; set; } = "A.E.G.I.S.-9";
    public string AvatarTheme { get; set; } = "Emerald";
    public string AvatarProfile { get; set; } = "male";
    public bool UseThreeDimensionalAvatar { get; set; } = true;
    public string SelectedAvatarId { get; set; } = "jarvis-male-dev";
    public string MaleVoiceId { get; set; } = "am_fenrir";
    public string FemaleVoiceId { get; set; } = "af_heart";
    public bool EnableLipSync { get; set; } = true;
    public bool EnableWakePhrase { get; set; }
    public bool AutoSubmitVoiceCommands { get; set; } = true;
    public string WakePhrase { get; set; } = "AEGIS-9";
    public bool EnableStartupNotifications { get; set; } = true;
    public bool EnableVoiceResponses { get; set; } = true;

    private static string PreferencesPath => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Jarvis", "settings.json");

    public static UserPreferences Load()
    {
        try
        {
            if (File.Exists(PreferencesPath))
            {
                var preferences = JsonSerializer.Deserialize<UserPreferences>(File.ReadAllText(PreferencesPath)) ?? new UserPreferences();
                if (preferences.AvatarName.Equals("Jarvis", StringComparison.OrdinalIgnoreCase)) preferences.AvatarName = "A.E.G.I.S.-9";
                if (preferences.WakePhrase.Equals("Jarvis", StringComparison.OrdinalIgnoreCase)) preferences.WakePhrase = "AEGIS-9";
                return preferences;
            }
        }
        catch (JsonException) { }
        catch (IOException) { }
        return new UserPreferences();
    }

    public void Save()
    {
        var directory = Path.GetDirectoryName(PreferencesPath)!;
        Directory.CreateDirectory(directory);
        File.WriteAllText(PreferencesPath, JsonSerializer.Serialize(this, new JsonSerializerOptions { WriteIndented = true }));
    }
}
