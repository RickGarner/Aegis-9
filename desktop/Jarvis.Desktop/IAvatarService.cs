namespace Jarvis.Desktop;

public interface IAvatarService
{
    AvatarDefinition? ActiveAvatar { get; }
    IReadOnlyList<AvatarDefinition> AvailableAvatars { get; }

    Task InitializeAsync(CancellationToken cancellationToken = default);
    Task SelectAvatarAsync(string avatarId, CancellationToken cancellationToken = default);
    Task SetStateAsync(AvatarVisualState state, CancellationToken cancellationToken = default);
    Task SetExpressionAsync(string expression, double intensity = 1.0, CancellationToken cancellationToken = default);
    Task SpeakAsync(SpeechPlaybackData speech, CancellationToken cancellationToken = default);
    Task StopSpeakingAsync(CancellationToken cancellationToken = default);
    Task<SpeechResult> SpeakTextAsync(string text, CancellationToken cancellationToken = default);
    void AttachHostWindow(AvatarWindow window);
}

public sealed class SpeechPlaybackData
{
    public string AudioUrl { get; set; } = string.Empty;
    public int DurationMs { get; set; }
    public List<SpeechCue> Cues { get; set; } = [];
}

public sealed class SpeechCue
{
    public int TimeMs { get; set; }
    public string Viseme { get; set; } = "sil";
    public double Weight { get; set; }
}
