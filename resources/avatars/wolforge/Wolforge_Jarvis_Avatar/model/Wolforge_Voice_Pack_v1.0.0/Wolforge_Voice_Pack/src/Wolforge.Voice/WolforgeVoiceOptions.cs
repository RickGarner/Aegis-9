using System.Text.Json;
using System.Text.Json.Serialization;

namespace Wolforge.Voice;

public sealed class WolforgeVoiceOptions
{
    public int SchemaVersion { get; init; } = 1;
    public string VoiceId { get; init; } = "wolforge";
    public string DisplayName { get; init; } = "Wolforge";
    public string Language { get; init; } = "en-us";
    public string Engine { get; init; } = "kokoro";
    public string KokoroVoice { get; init; } = "am_fenrir";
    public double KokoroSpeed { get; init; } = 0.94;
    public string FfmpegPath { get; init; } = "ffmpeg.exe";
    public int OutputSampleRate { get; init; } = 24000;
    public string DefaultProfile { get; init; } = "normal";
    public Dictionary<string, VoiceProfile> Profiles { get; init; } = new(StringComparer.OrdinalIgnoreCase);
    public JawEnvelopeOptions JawEnvelope { get; init; } = new();

    public VoiceProfile GetProfile(string? name) =>
        Profiles.TryGetValue(name ?? DefaultProfile, out var profile)
            ? profile
            : Profiles.TryGetValue(DefaultProfile, out var fallback)
                ? fallback
                : throw new InvalidOperationException("No Wolforge voice profile is configured.");

    public static async Task<WolforgeVoiceOptions> LoadAsync(string path, CancellationToken ct = default)
    {
        await using var stream = File.OpenRead(path);
        return await JsonSerializer.DeserializeAsync<WolforgeVoiceOptions>(stream,
            new JsonSerializerOptions { PropertyNameCaseInsensitive = true }, ct)
            ?? throw new InvalidDataException($"Invalid voice configuration: {path}");
    }
}

public sealed class VoiceProfile
{
    public double PitchSemitones { get; init; } = -2;
    public double Tempo { get; init; } = .97;
    public double BassGainDb { get; init; } = 2.5;
    public double PresenceGainDb { get; init; } = 1;
    public double Drive { get; init; } = 1.06;
    public double CompressorThresholdDb { get; init; } = -20;
    public double CompressorRatio { get; init; } = 3;
    public double TargetPeakDb { get; init; } = -1;
}

public sealed class JawEnvelopeOptions
{
    public int FrameMilliseconds { get; init; } = 20;
    public double NoiseFloorDb { get; init; } = -48;
    public double OpenThresholdDb { get; init; } = -31;
    public double MaximumDb { get; init; } = -9;
    public double Attack { get; init; } = .58;
    public double Release { get; init; } = .24;
}
