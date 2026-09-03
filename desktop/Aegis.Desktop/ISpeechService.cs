namespace Aegis.Desktop;

public interface ISpeechService
{
    bool IsAvailable { get; }
    Task<SpeechResult> SynthesizeAsync(SpeechRequest request, CancellationToken cancellationToken = default);
}
