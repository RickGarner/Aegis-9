using System.Text.Json;
using System.IO;

namespace Jarvis.Desktop;

public sealed class AvatarAssetCatalog
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    public AvatarAssetSelection GetSelection(string preferredProfile)
    {
        var avatars = LoadAvailableAvatars();
        if (avatars.Count == 0)
        {
            return AvatarAssetSelection.Missing("Avatar assets folder was not found.");
        }

        var profile = string.IsNullOrWhiteSpace(preferredProfile) ? "male" : preferredProfile.Trim().ToLowerInvariant();
        var selected = avatars.FirstOrDefault(item => item.Profile.Equals(profile, StringComparison.OrdinalIgnoreCase));
        if (selected is not null)
        {
            return BuildSelection(selected);
        }

        selected = avatars.FirstOrDefault(item => item.Profile.Equals(profile == "male" ? "female" : "male", StringComparison.OrdinalIgnoreCase));
        if (selected is not null)
        {
            return BuildSelection(selected, $"Preferred profile '{profile}' is unavailable. Loaded fallback profile '{selected.Profile}'.");
        }

        return AvatarAssetSelection.Missing("No valid avatar manifest/model pair was found.");
    }

    public IReadOnlyList<AvatarDefinition> LoadAvailableAvatars()
    {
        var avatarsRoot = FindAvatarsRoot();
        if (avatarsRoot is null)
        {
            return [];
        }

        var avatars = new List<AvatarDefinition>();
        foreach (var profileDir in Directory.GetDirectories(avatarsRoot))
        {
            var avatar = LoadAvatarDefinition(profileDir);
            if (avatar is not null)
            {
                avatars.Add(avatar);
            }
        }

        return avatars;
    }

    private static AvatarAssetSelection BuildSelection(AvatarDefinition definition, string? detailOverride = null)
    {
        var avatarsRoot = FindAvatarsRoot();
        if (avatarsRoot is null)
        {
            return AvatarAssetSelection.Missing("Avatar assets folder was not found.");
        }

        var profileDir = Path.Combine(avatarsRoot, definition.Profile);
        var modelPath = Path.GetFullPath(Path.Combine(profileDir, definition.Model));
        if (!File.Exists(modelPath))
        {
            return AvatarAssetSelection.Missing($"Model file was not found: {modelPath}");
        }

        if (!definition.RedistributionAllowed)
        {
            return AvatarAssetSelection.Missing($"Avatar '{definition.Id}' does not permit redistribution.");
        }

        return new AvatarAssetSelection(
            true,
            definition.Profile,
            new AvatarManifest
            {
                DisplayName = definition.DisplayName,
                Profile = definition.Profile,
                Format = definition.Format,
                ModelFile = definition.Model,
                Attribution = definition.Attribution,
                LicenseName = definition.LicenseName,
                LicenseUrl = definition.LicenseUrl,
                RedistributionAllowed = definition.RedistributionAllowed,
            },
            modelPath,
            detailOverride ?? "Avatar model loaded.",
            definition);
    }

    private static AvatarDefinition? LoadAvatarDefinition(string profileDir)
    {
        var avatarJsonPath = Path.Combine(profileDir, "avatar.json");
        if (File.Exists(avatarJsonPath))
        {
            try
            {
                var definition = JsonSerializer.Deserialize<AvatarDefinition>(File.ReadAllText(avatarJsonPath), JsonOptions);
                if (definition is null)
                {
                    return null;
                }
                if (string.IsNullOrWhiteSpace(definition.Profile))
                {
                    definition.Profile = new DirectoryInfo(profileDir).Name;
                }
                return definition;
            }
            catch (JsonException)
            {
                return null;
            }
            catch (IOException)
            {
                return null;
            }
        }

        var manifestPath = Path.Combine(profileDir, "manifest.json");
        if (!File.Exists(manifestPath))
        {
            return null;
        }

        AvatarManifest? manifest;
        try
        {
            manifest = JsonSerializer.Deserialize<AvatarManifest>(File.ReadAllText(manifestPath), JsonOptions);
        }
        catch (JsonException)
        {
            return null;
        }
        catch (IOException)
        {
            return null;
        }

        if (manifest is null)
        {
            return null;
        }

        var profile = new DirectoryInfo(profileDir).Name;
        return new AvatarDefinition
        {
            Id = $"jarvis-{profile}-dev",
            DisplayName = manifest.DisplayName,
            Profile = string.IsNullOrWhiteSpace(manifest.Profile) ? profile : manifest.Profile,
            Format = manifest.Format,
            Model = manifest.ModelFile,
            VoiceId = profile.Equals("female", StringComparison.OrdinalIgnoreCase) ? "af_heart" : "am_fenrir",
            Attribution = manifest.Attribution,
            LicenseName = manifest.LicenseName,
            LicenseUrl = manifest.LicenseUrl,
            RedistributionAllowed = manifest.RedistributionAllowed,
        };
    }

    private static string? FindAvatarsRoot()
    {
        var current = new DirectoryInfo(AppDomain.CurrentDomain.BaseDirectory);
        while (current is not null)
        {
            var localAssets = Path.Combine(current.FullName, "Assets", "Avatars");
            if (Directory.Exists(localAssets))
            {
                return localAssets;
            }

            var sourceAssets = Path.Combine(current.FullName, "desktop", "Jarvis.Desktop", "Assets", "Avatars");
            if (Directory.Exists(sourceAssets))
            {
                return sourceAssets;
            }

            current = current.Parent;
        }

        return null;
    }
}

public sealed record AvatarAssetSelection(
    bool IsAvailable,
    string Profile,
    AvatarManifest? Manifest,
    string? ModelPath,
    string Detail,
    AvatarDefinition? Definition = null)
{
    public static AvatarAssetSelection Missing(string detail) => new(false, string.Empty, null, null, detail, null);
}
