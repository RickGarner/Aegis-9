using System.Text.Json;
using System.Text.Json.Serialization;

namespace Aegis.Desktop;

public sealed class AvatarMessage
{
    [JsonPropertyName("version")]
    public int Version { get; set; } = 1;

    [JsonPropertyName("type")]
    public string Type { get; set; } = string.Empty;

    [JsonPropertyName("requestId")]
    public string RequestId { get; set; } = Guid.NewGuid().ToString("D");

    [JsonPropertyName("payload")]
    public JsonElement Payload { get; set; }
}

public static class AvatarProtocol
{
    public static string Build<TPayload>(string type, TPayload payload)
    {
        return JsonSerializer.Serialize(new
        {
            version = 1,
            type,
            requestId = Guid.NewGuid().ToString("D"),
            payload,
        });
    }
}
