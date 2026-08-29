namespace Wolforge.Voice;

public interface IKokoroSynthesizer
{
    Task SynthesizeToWavAsync(string text, string language, string voice, double speed,
        string outputWav, CancellationToken cancellationToken);
}

public interface IWolforgeAudioPlayer
{
    Task PlayAsync(string wavPath, IReadOnlyList<JawFrame> jawFrames, CancellationToken cancellationToken);
    void Stop();
}

public interface IWolforgeAvatar
{
    Task SpeakingAsync();
    Task StopSpeakingAsync();
}

public sealed class WolforgeSpeechCoordinator
{
    private readonly IKokoroSynthesizer _kokoro;
    private readonly WolforgeVoiceProcessor _processor;
    private readonly IWolforgeAudioPlayer _player;
    private readonly IWolforgeAvatar _avatar;
    private readonly WolforgeVoiceOptions _options;

    public WolforgeSpeechCoordinator(IKokoroSynthesizer kokoro, WolforgeVoiceProcessor processor,
        IWolforgeAudioPlayer player, IWolforgeAvatar avatar, WolforgeVoiceOptions options)
        => (_kokoro,_processor,_player,_avatar,_options)=(kokoro,processor,player,avatar,options);

    public async Task SpeakAsync(string text, string? profile = null, CancellationToken ct = default)
    {
        if (string.IsNullOrWhiteSpace(text)) return;
        string stem=Path.Combine(Path.GetTempPath(),"Jarvis-Wolforge",Guid.NewGuid().ToString("N"));
        string raw=stem+"-kokoro.wav", final=stem+"-wolforge.wav";
        Directory.CreateDirectory(Path.GetDirectoryName(stem)!);
        try
        {
            await _kokoro.SynthesizeToWavAsync(text,_options.Language,_options.KokoroVoice,_options.KokoroSpeed,raw,ct);
            await _processor.ProcessAsync(raw,final,profile,ct);
            var envelope=WavJawEnvelope.ReadPcm16Mono(final,_options.JawEnvelope);
            await _avatar.SpeakingAsync();
            await _player.PlayAsync(final,envelope,ct);
        }
        finally
        {
            _player.Stop();
            await _avatar.StopSpeakingAsync();
            TryDelete(raw); TryDelete(final);
        }
    }

    private static void TryDelete(string p) { try { if(File.Exists(p)) File.Delete(p); } catch { } }
}
