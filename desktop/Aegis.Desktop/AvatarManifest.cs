using System.Text.Json.Serialization;

namespace Aegis.Desktop;

public sealed class AvatarManifest
{
    [JsonPropertyName("displayName")]
    public string DisplayName { get; set; } = string.Empty;

    [JsonPropertyName("profile")]
    public string Profile { get; set; } = string.Empty;

    [JsonPropertyName("modelFile")]
    public string ModelFile { get; set; } = string.Empty;

    [JsonPropertyName("format")]
    public string Format { get; set; } = string.Empty;

    [JsonPropertyName("licenseName")]
    public string LicenseName { get; set; } = string.Empty;

    [JsonPropertyName("licenseUrl")]
    public string LicenseUrl { get; set; } = string.Empty;

    [JsonPropertyName("redistributionAllowed")]
    public bool RedistributionAllowed { get; set; }

    [JsonPropertyName("attribution")]
    public string Attribution { get; set; } = string.Empty;
}
