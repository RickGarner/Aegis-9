namespace Aegis.Desktop;

public sealed class SpeechRequest
{
    public string Text { get; set; } = string.Empty;
    public string VoiceId { get; set; } = string.Empty;
    public double Speed { get; set; } = 1.0;
    public string OutputFormat { get; set; } = "wav";
    public string CorrelationId { get; set; } = Guid.NewGuid().ToString("D");
}
