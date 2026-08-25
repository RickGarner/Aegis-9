using System.IO;
using System.Text.Json;

namespace Jarvis.Desktop;

public sealed class UserPreferences
{
    public bool EnterSendsMessage { get; set; } = true;
    public string AvatarName { get; set; } = "Jarvis";
    public string AvatarTheme { get; set; } = "Emerald";
    public string AvatarProfile { get; set; } = "male";
    public bool UseThreeDimensionalAvatar { get; set; } = true;
    public string SelectedAvatarId { get; set; } = "jarvis-male-dev";
    public string MaleVoiceId { get; set; } = "am_fenrir";
    public string FemaleVoiceId { get; set; } = "af_heart";
    public bool EnableLipSync { get; set; } = true;

    private static string PreferencesPath => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Jarvis", "settings.json");

    public static UserPreferences Load()
    {
        try
        {
            if (File.Exists(PreferencesPath))
            {
                return JsonSerializer.Deserialize<UserPreferences>(File.ReadAllText(PreferencesPath)) ?? new UserPreferences();
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
