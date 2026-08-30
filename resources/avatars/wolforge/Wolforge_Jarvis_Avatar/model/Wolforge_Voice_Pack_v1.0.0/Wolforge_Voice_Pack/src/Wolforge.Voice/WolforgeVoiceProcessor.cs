using System.Diagnostics;
using System.Globalization;

namespace Wolforge.Voice;

public sealed class WolforgeVoiceProcessor
{
    private readonly WolforgeVoiceOptions _options;
    public WolforgeVoiceProcessor(WolforgeVoiceOptions options) => _options = options;

    public async Task ProcessAsync(string inputWav, string outputWav, string? profileName = null,
        CancellationToken cancellationToken = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(inputWav);
        ArgumentException.ThrowIfNullOrWhiteSpace(outputWav);
        if (!File.Exists(inputWav)) throw new FileNotFoundException("Kokoro WAV was not found.", inputWav);

        var p = _options.GetProfile(profileName);
        var pitch = Math.Pow(2, p.PitchSemitones / 12.0);
        string N(double v) => v.ToString("0.######", CultureInfo.InvariantCulture);

        // Shifted formants intentionally make the cyber-wolf sound physically larger.
        // Soft clipping through tanh provides controlled grit without a monster effect.
        var filter = string.Join(',', new[]
        {
            $"rubberband=pitch={N(pitch)}:tempo={N(p.Tempo)}:transients=smooth:detector=soft:formant=shifted:pitchq=quality",
            "highpass=f=55",
            "lowpass=f=10500",
            $"equalizer=f=125:t=q:w=0.8:g={N(p.BassGainDb)}",
            $"equalizer=f=2600:t=q:w=1.1:g={N(p.PresenceGainDb)}",
            $"aeval=tanh({N(p.Drive)}*val(0))/tanh({N(p.Drive)})",
            $"acompressor=threshold={N(p.CompressorThresholdDb)}dB:ratio={N(p.CompressorRatio)}:attack=12:release=140:makeup=1.15",
            $"alimiter=limit={N(Math.Pow(10, p.TargetPeakDb / 20.0))}:attack=5:release=50"
        });

        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(outputWav))!);
        var psi = new ProcessStartInfo(_options.FfmpegPath)
        {
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardError = true,
            RedirectStandardOutput = true
        };
        foreach (var arg in new[] { "-hide_banner", "-loglevel", "error", "-y", "-i", inputWav,
                     "-af", filter, "-ar", _options.OutputSampleRate.ToString(CultureInfo.InvariantCulture),
                     "-ac", "1", "-c:a", "pcm_s16le", outputWav })
            psi.ArgumentList.Add(arg);

        using var process = Process.Start(psi) ?? throw new InvalidOperationException("Unable to start FFmpeg.");
        try
        {
            var stderr = process.StandardError.ReadToEndAsync(cancellationToken);
            await process.WaitForExitAsync(cancellationToken);
            var error = await stderr;
            if (process.ExitCode != 0)
                throw new InvalidOperationException($"Wolforge voice processing failed ({process.ExitCode}): {error}");
        }
        catch (OperationCanceledException)
        {
            if (!process.HasExited) process.Kill(entireProcessTree: true);
            TryDelete(outputWav);
            throw;
        }
        if (!File.Exists(outputWav) || new FileInfo(outputWav).Length <= 44)
            throw new InvalidDataException("FFmpeg did not produce a valid output WAV.");
    }

    private static void TryDelete(string path) { try { if (File.Exists(path)) File.Delete(path); } catch { } }
}
