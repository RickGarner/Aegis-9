using System.IO;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Speech.Synthesis;
using NAudio.Wave;

namespace Jarvis.Desktop;

public sealed class KokoroSpeechService : ISpeechService
{
    private readonly HttpClient _httpClient;
    private readonly SpeechOptions _options;

    public KokoroSpeechService(SpeechOptions options)
    {
        _options = options;
        _httpClient = new HttpClient
        {
            BaseAddress = new Uri(options.LocalEndpoint.TrimEnd('/') + "/"),
            Timeout = TimeSpan.FromSeconds(Math.Max(10, options.RequestTimeoutSeconds)),
        };
    }

    public bool IsAvailable => true;

    public async Task<SpeechResult> SynthesizeAsync(SpeechRequest request, CancellationToken cancellationToken = default)
    {
        var spokenText = PrepareTextForSpeech(request.Text);
        try
        {
            using var response = await _httpClient.PostAsJsonAsync("synthesize", new
            {
                text = spokenText,
                voiceId = request.VoiceId,
                speed = request.Speed,
                outputFormat = request.OutputFormat,
                correlationId = request.CorrelationId,
            }, cancellationToken);

            if (!response.IsSuccessStatusCode)
            {
                return await SynthesizeFallbackAsync(request, $"Kokoro returned HTTP {(int)response.StatusCode}.", cancellationToken);
            }

            using var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
            using var document = await JsonDocument.ParseAsync(stream, cancellationToken: cancellationToken);
            var root = document.RootElement;
            var audioPath = root.TryGetProperty("audioPath", out var audioPathElement) ? audioPathElement.GetString() : null;
            var durationMs = root.TryGetProperty("durationMs", out var durationElement) ? durationElement.GetInt32() : 0;
            var sampleRate = root.TryGetProperty("sampleRate", out var sampleRateElement) ? sampleRateElement.GetInt32() : 0;

            return new SpeechResult
            {
                Success = !string.IsNullOrWhiteSpace(audioPath),
                AudioPath = audioPath,
                DurationMs = durationMs,
                SampleRate = sampleRate,
                Detail = string.IsNullOrWhiteSpace(audioPath)
                    ? "Kokoro runtime response did not include audioPath."
                    : "Speech synthesis completed.",
            };
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            return new SpeechResult
            {
                Success = false,
                Detail = "Speech synthesis was cancelled.",
            };
        }
        catch (OperationCanceledException ex)
        {
            return await SynthesizeFallbackAsync(request, $"Kokoro timed out: {ex.Message}", cancellationToken);
        }
        catch (HttpRequestException ex)
        {
            return await SynthesizeFallbackAsync(request, $"Kokoro unavailable: {ex.Message}", cancellationToken);
        }
        catch (JsonException ex)
        {
            return await SynthesizeFallbackAsync(request, $"Kokoro returned invalid JSON: {ex.Message}", cancellationToken);
        }
    }

    private static async Task<SpeechResult> SynthesizeFallbackAsync(SpeechRequest request, string reason, CancellationToken cancellationToken)
    {
        try
        {
            var directory = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Jarvis", "SpeechCache");
            Directory.CreateDirectory(directory);
            var audioPath = Path.Combine(directory, $"fallback-{Guid.NewGuid():N}.wav");
            await Task.Run(() =>
            {
                cancellationToken.ThrowIfCancellationRequested();
                using var synthesizer = new SpeechSynthesizer();
                synthesizer.SelectVoiceByHints(VoiceGender.Male, VoiceAge.Adult);
                synthesizer.Rate = Math.Clamp((int)Math.Round((request.Speed - 1.0) * 5), -4, 4);
                synthesizer.SetOutputToWaveFile(audioPath);
                synthesizer.Speak(PrepareTextForSpeech(request.Text));
            }, cancellationToken);
            using var reader = new WaveFileReader(audioPath);
            return new SpeechResult
            {
                Success = true,
                AudioPath = audioPath,
                DurationMs = (int)reader.TotalTime.TotalMilliseconds,
                SampleRate = reader.WaveFormat.SampleRate,
                Detail = $"Used offline Windows voice fallback. {reason}",
            };
        }
        catch (Exception error) when (error is InvalidOperationException or IOException)
        {
            return new SpeechResult { Success = false, Detail = $"Speech synthesis unavailable: {error.Message}" };
        }
    }

    internal static string PrepareTextForSpeech(string text)
    {
        return text
            .Replace("F.E.R.A.L.", "feral", StringComparison.OrdinalIgnoreCase)
            .Replace("F.E.R.A.L", "feral", StringComparison.OrdinalIgnoreCase)
            .Replace("FERAL", "feral", StringComparison.OrdinalIgnoreCase);
    }
}

