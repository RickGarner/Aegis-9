namespace Aegis.Desktop;

public sealed class SpeechResult
{
    public bool Success { get; set; }
    public string? AudioPath { get; set; }
    public int SampleRate { get; set; }
    public int DurationMs { get; set; }
    public string Detail { get; set; } = string.Empty;
}
