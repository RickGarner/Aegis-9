using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;

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
        try
        {
            using var response = await _httpClient.PostAsJsonAsync("synthesize", new
            {
                text = request.Text,
                voiceId = request.VoiceId,
                speed = request.Speed,
                outputFormat = request.OutputFormat,
                correlationId = request.CorrelationId,
            }, cancellationToken);

            if (!response.IsSuccessStatusCode)
            {
                return new SpeechResult
                {
                    Success = false,
                    Detail = $"Kokoro runtime returned HTTP {(int)response.StatusCode}.",
                };
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
        catch (OperationCanceledException)
        {
            return new SpeechResult
            {
                Success = false,
                Detail = "Speech synthesis was cancelled.",
            };
        }
        catch (HttpRequestException ex)
        {
            return new SpeechResult
            {
                Success = false,
                Detail = $"Kokoro runtime is unavailable: {ex.Message}",
            };
        }
        catch (JsonException ex)
        {
            return new SpeechResult
            {
                Success = false,
                Detail = $"Kokoro runtime returned invalid JSON: {ex.Message}",
            };
        }
    }
}
