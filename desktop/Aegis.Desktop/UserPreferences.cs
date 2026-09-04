using System.IO;
using System.Text.Json;

namespace Aegis.Desktop;

public sealed class UserPreferences
{
    public bool EnterSendsMessage { get; set; } = true;
    public string AvatarName { get; set; } = "A.E.G.I.S.-9";
    public string AvatarTheme { get; set; } = "Emerald";
    public string AvatarProfile { get; set; } = "male";
    public bool UseThreeDimensionalAvatar { get; set; } = true;
    public string SelectedAvatarId { get; set; } = "aegis9-male";
    public string MaleVoiceId { get; set; } = "am_fenrir";
    public string FemaleVoiceId { get; set; } = "af_heart";
    public bool EnableLipSync { get; set; } = true;
    public bool EnableWakePhrase { get; set; }
    public bool AutoSubmitVoiceCommands { get; set; } = true;
    public string WakePhrase { get; set; } = "AEGIS-9";
    public bool EnableStartupNotifications { get; set; } = true;
    public bool EnableVoiceResponses { get; set; } = true;
    public string DeveloperStudioSelectedRepository { get; set; } = "";
    public List<string> DeveloperStudioRecentRepositories { get; set; } = [];
    public double? OperationsCenterLeft { get; set; }
    public double? OperationsCenterTop { get; set; }
    public double OperationsCenterWidth { get; set; } = 1320;
    public double OperationsCenterHeight { get; set; } = 780;
    public bool OperationsCenterMaximized { get; set; }
    public string OperationsCenterLayoutMode { get; set; } = "Standard";

    private static string PreferencesPath => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Aegis-9", "settings.json");

    private static string LegacyPreferencesPath => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Jarvis", "settings.json");

    public static UserPreferences Load()
    {
        try
        {
            var loadPath = File.Exists(PreferencesPath) ? PreferencesPath : LegacyPreferencesPath;
            if (File.Exists(loadPath))
            {
                var preferences = JsonSerializer.Deserialize<UserPreferences>(File.ReadAllText(loadPath)) ?? new UserPreferences();
                if (preferences.AvatarName.Equals("Jarvis", StringComparison.OrdinalIgnoreCase)) preferences.AvatarName = "A.E.G.I.S.-9";
                if (preferences.WakePhrase.Equals("Jarvis", StringComparison.OrdinalIgnoreCase)) preferences.WakePhrase = "AEGIS-9";
                if (preferences.SelectedAvatarId.Equals("jarvis-male-dev", StringComparison.OrdinalIgnoreCase)) preferences.SelectedAvatarId = "aegis9-male";
                if (preferences.SelectedAvatarId.Equals("jarvis-female-dev", StringComparison.OrdinalIgnoreCase)) preferences.SelectedAvatarId = "aegis9-female";
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
