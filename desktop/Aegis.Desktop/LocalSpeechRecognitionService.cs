using NAudio;
using System.IO;
using System.Diagnostics;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using NAudio.Wave;

namespace Aegis.Desktop;

public sealed class LocalSpeechRecognitionService : IDisposable
{
    private readonly HttpClient _client;
    private bool _disposed;
    private volatile bool _manualStopRequested;

    public LocalSpeechRecognitionService() : this("http://127.0.0.1:8000") { }

    public LocalSpeechRecognitionService(string backendBaseUrl)
    {
        _client = new HttpClient
        {
            BaseAddress = new Uri(backendBaseUrl.TrimEnd('/') + "/"),
            Timeout = TimeSpan.FromSeconds(60),
        };
    }

    public event EventHandler<int>? AudioLevelChanged;
    public event EventHandler<string>? StatusChanged;
    public event EventHandler? WakePhraseRecognized;

    public void RequestStop() => _manualStopRequested = true;

    public Task StartWakePhraseAsync(string phrase, CancellationToken cancellationToken = default) =>
        throw new InvalidOperationException("Wake phrase monitoring is temporarily disabled while Whisper push-to-talk is active.");

    public Task StopWakePhraseAsync() => Task.CompletedTask;

    public async Task<SpeechRecognitionResult> ListenOnceAsync(CancellationToken cancellationToken = default)
    {
        ObjectDisposedException.ThrowIf(_disposed, this);
        var directory = Path.Combine(Path.GetTempPath(), "Aegis-9", "VoiceInput");
        Directory.CreateDirectory(directory);
        var audioPath = Path.Combine(directory, $"voice-{Guid.NewGuid():N}.wav");
        _manualStopRequested = false;
        try
        {
            StatusChanged?.Invoke(this, "Recording locally");
            await CaptureCommandAsync(audioPath, cancellationToken);
            StatusChanged?.Invoke(this, "Transcribing locally with Whisper");
            return await TranscribeAsync(audioPath, cancellationToken);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested) { throw; }
        catch (OperationCanceledException error)
        {
            return new SpeechRecognitionResult { Detail = $"Local Whisper transcription timed out: {error.Message}" };
        }
        catch (Exception error) when (error is InvalidOperationException or HttpRequestException or IOException or MmException or JsonException)
        {
            return new SpeechRecognitionResult { Detail = $"Local Whisper transcription is unavailable: {error.Message}" };
        }
        finally
        {
            AudioLevelChanged?.Invoke(this, 0);
            StatusChanged?.Invoke(this, "Ready");
            _manualStopRequested = false;
            try { File.Delete(audioPath); } catch (IOException) { }
        }
    }

    private async Task CaptureCommandAsync(string audioPath, CancellationToken cancellationToken)
    {
        using var capture = new WaveInEvent { DeviceNumber = 0, WaveFormat = new WaveFormat(16000, 16, 1), BufferMilliseconds = 50 };
        using var writer = new WaveFileWriter(audioPath, capture.WaveFormat);
        var completion = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var stopwatch = Stopwatch.StartNew();
        var speechStarted = false;
        var lastSpeechAt = TimeSpan.Zero;
        var stopRequested = false;
        capture.DataAvailable += (_, e) =>
        {
            writer.Write(e.Buffer, 0, e.BytesRecorded);
            var sum = 0d;
            var samples = e.BytesRecorded / 2;
            for (var offset = 0; offset + 1 < e.BytesRecorded; offset += 2)
            {
                var sample = BitConverter.ToInt16(e.Buffer, offset) / 32768d;
                sum += sample * sample;
            }
            var rms = samples == 0 ? 0 : Math.Sqrt(sum / samples);
            var level = Math.Clamp((int)(rms * 500), 0, 100);
            AudioLevelChanged?.Invoke(this, level);
            if (level >= 4) { speechStarted = true; lastSpeechAt = stopwatch.Elapsed; }
        };
        capture.RecordingStopped += (_, e) =>
        {
            if (e.Exception is not null) completion.TrySetException(e.Exception);
            else completion.TrySetResult();
        };
        using var registration = cancellationToken.Register(() =>
        {
            try { capture.StopRecording(); } catch (MmException) { }
        });
        capture.StartRecording();
        while (!completion.Task.IsCompleted)
        {
            cancellationToken.ThrowIfCancellationRequested();
            await Task.Delay(100, cancellationToken);
            var elapsed = stopwatch.Elapsed;
            if (!stopRequested && (_manualStopRequested ||
                (!speechStarted && elapsed >= TimeSpan.FromSeconds(8)) ||
                (speechStarted && elapsed - lastSpeechAt >= TimeSpan.FromSeconds(1.1)) ||
                elapsed >= TimeSpan.FromSeconds(20)))
            {
                stopRequested = true;
                capture.StopRecording();
                break;
            }
        }
        var recordingFinished = await Task.WhenAny(
            completion.Task,
            Task.Delay(TimeSpan.FromSeconds(3), cancellationToken));
        if (recordingFinished != completion.Task)
            throw new InvalidOperationException("Windows did not finish the microphone recording within three seconds.");
        await completion.Task;
        cancellationToken.ThrowIfCancellationRequested();
        writer.Flush();
        // A manual STOP means "finish and transcribe", not "cancel". Whisper can
        // still recover quiet speech even when the local level threshold was not met.
        if (!speechStarted && !_manualStopRequested)
            throw new InvalidOperationException("No speech was detected. Check the selected Windows input device and microphone permission.");
    }

    private async Task<SpeechRecognitionResult> TranscribeAsync(string audioPath, CancellationToken cancellationToken)
    {
        await using var stream = File.OpenRead(audioPath);
        using var content = new MultipartFormDataContent();
        using var audio = new StreamContent(stream);
        audio.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("audio/wav");
        content.Add(audio, "file", Path.GetFileName(audioPath));
        using var response = await _client.PostAsync("api/speech/transcribe", content, cancellationToken);
        var payload = await response.Content.ReadFromJsonAsync<WhisperResponse>(cancellationToken: cancellationToken);
        if (!response.IsSuccessStatusCode)
            return new SpeechRecognitionResult { Detail = payload?.Detail ?? $"Whisper returned HTTP {(int)response.StatusCode}." };
        if (string.IsNullOrWhiteSpace(payload?.Text))
            return new SpeechRecognitionResult { Detail = "Whisper did not detect a spoken command." };
        return new SpeechRecognitionResult
        {
            Success = true,
            Text = payload.Text.Trim(),
            Confidence = payload.Confidence,
            Detail = $"Transcribed locally with Whisper ({payload.Language}).",
        };
    }

    public void Dispose()
    {
        if (_disposed) return;
        _client.Dispose();
        _disposed = true;
    }

    private sealed class WhisperResponse
    {
        public string Text { get; set; } = string.Empty;
        public string Language { get; set; } = "en";
        public float Confidence { get; set; }
        public string Detail { get; set; } = string.Empty;
    }
}

