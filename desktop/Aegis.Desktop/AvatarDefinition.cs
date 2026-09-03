using System.Text.Json.Serialization;

namespace Aegis.Desktop;

public sealed class AvatarDefinition
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("displayName")]
    public string DisplayName { get; set; } = string.Empty;

    [JsonPropertyName("version")]
    public int Version { get; set; } = 1;

    [JsonPropertyName("profile")]
    public string Profile { get; set; } = string.Empty;

    [JsonPropertyName("format")]
    public string Format { get; set; } = string.Empty;

    [JsonPropertyName("model")]
    public string Model { get; set; } = string.Empty;

    [JsonPropertyName("voiceId")]
    public string VoiceId { get; set; } = string.Empty;

    [JsonPropertyName("scale")]
    public double Scale { get; set; } = 1.0;

    [JsonPropertyName("cameraTarget")]
    public double[] CameraTarget { get; set; } = [0.0, 1.55, 0.0];

    [JsonPropertyName("cameraOrbit")]
    public string CameraOrbit { get; set; } = "0deg 82deg 1.6m";

    [JsonPropertyName("animationNames")]
    public Dictionary<string, string> AnimationNames { get; set; } = new(StringComparer.OrdinalIgnoreCase);

    [JsonPropertyName("morphTargets")]
    public Dictionary<string, string> MorphTargets { get; set; } = new(StringComparer.OrdinalIgnoreCase);

    [JsonPropertyName("visemeMap")]
    public Dictionary<string, string> VisemeMap { get; set; } = new(StringComparer.OrdinalIgnoreCase);

    [JsonPropertyName("licenseName")]
    public string LicenseName { get; set; } = string.Empty;

    [JsonPropertyName("licenseUrl")]
    public string LicenseUrl { get; set; } = string.Empty;

    [JsonPropertyName("redistributionAllowed")]
    public bool RedistributionAllowed { get; set; }

    [JsonPropertyName("localUseAllowed")]
    public bool LocalUseAllowed { get; set; }

    [JsonPropertyName("attribution")]
    public string Attribution { get; set; } = string.Empty;
}
