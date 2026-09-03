namespace Aegis.Desktop;

public sealed class SpeechRecognitionResult
{
    public bool Success { get; init; }
    public string Text { get; init; } = string.Empty;
    public float Confidence { get; init; }
    public string Detail { get; init; } = string.Empty;
}
