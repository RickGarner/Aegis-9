using System.Text.Json;
using System.IO;

namespace Jarvis.Desktop;

public sealed class AvatarService : IAvatarService
{
    private readonly UserPreferences _preferences;
    private readonly JarvisDesktopOptions _options;
    private readonly AvatarAssetCatalog _catalog;
    private readonly ISpeechService _speechService;
    private AvatarWindow? _host;
    private Func<string, CancellationToken, Task<bool>>? _primaryHostSender;
    private CancellationTokenSource? _speechCancellation;

    public AvatarService(UserPreferences preferences, JarvisDesktopOptions options, AvatarAssetCatalog catalog, ISpeechService speechService)
    {
        _preferences = preferences;
        _options = options;
        _catalog = catalog;
        _speechService = speechService;
    }

    public AvatarDefinition? ActiveAvatar { get; private set; }

    public IReadOnlyList<AvatarDefinition> AvailableAvatars => _catalog.LoadAvailableAvatars();

    public Task InitializeAsync(CancellationToken cancellationToken = default)
    {
        var preferredId = string.IsNullOrWhiteSpace(_preferences.SelectedAvatarId)
            ? _options.Avatar.SelectedAvatarId
            : _preferences.SelectedAvatarId;

        ActiveAvatar = AvailableAvatars.FirstOrDefault(item => item.Id.Equals(preferredId, StringComparison.OrdinalIgnoreCase))
            ?? AvailableAvatars.FirstOrDefault();

        if (ActiveAvatar is not null)
        {
            _preferences.SelectedAvatarId = ActiveAvatar.Id;
            _preferences.Save();
        }

        return Task.CompletedTask;
    }

    public async Task SelectAvatarAsync(string avatarId, CancellationToken cancellationToken = default)
    {
        var selected = AvailableAvatars.FirstOrDefault(item => item.Id.Equals(avatarId, StringComparison.OrdinalIgnoreCase));
        if (selected is null)
        {
            return;
        }

        await StopSpeakingAsync(cancellationToken);
        ActiveAvatar = selected;
        _preferences.SelectedAvatarId = selected.Id;
        if (selected.Profile.Equals("male", StringComparison.OrdinalIgnoreCase))
        {
            _preferences.AvatarProfile = "male";
        }
        else if (selected.Profile.Equals("female", StringComparison.OrdinalIgnoreCase))
        {
            _preferences.AvatarProfile = "female";
        }
        _preferences.Save();

        if (_host is not null)
        {
            await _host.LoadAvatarAsync(selected, cancellationToken);
        }

        await SetStateAsync(AvatarVisualState.Idle, cancellationToken);
    }

    public async Task SetStateAsync(AvatarVisualState state, CancellationToken cancellationToken = default)
    {
        var wireState = state.ToString().ToLowerInvariant();
        var payload = new
        {
            state = wireState,
        };
        await SendRuntimeMessageAsync(AvatarProtocol.Build("avatar.state", payload), cancellationToken);
    }

    public Task SetExpressionAsync(string expression, double intensity = 1.0, CancellationToken cancellationToken = default)
    {
        var payload = new
        {
            expression,
            intensity,
        };
        return SendRuntimeMessageAsync(AvatarProtocol.Build("avatar.expression", payload), cancellationToken);
    }

    public async Task SpeakAsync(SpeechPlaybackData speech, CancellationToken cancellationToken = default)
    {
        _speechCancellation?.Cancel();
        _speechCancellation?.Dispose();
        _speechCancellation = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);

        var payload = new
        {
            audioUrl = speech.AudioUrl,
            durationMs = speech.DurationMs,
            cues = speech.Cues,
        };
        await SendRuntimeMessageAsync(AvatarProtocol.Build("avatar.speech.start", payload), _speechCancellation.Token);
    }

    public Task StopSpeakingAsync(CancellationToken cancellationToken = default)
    {
        _speechCancellation?.Cancel();
        _speechCancellation?.Dispose();
        _speechCancellation = null;

        return SendRuntimeMessageAsync(AvatarProtocol.Build("avatar.speech.stop", new { }), cancellationToken);
    }

    public void AttachPrimaryHost(Func<string, CancellationToken, Task<bool>> messageSender) =>
        _primaryHostSender = messageSender;

    public void AttachHostWindow(AvatarWindow window)
    {
        _host = window;
        if (ActiveAvatar is not null)
        {
            _ = _host.LoadAvatarAsync(ActiveAvatar, CancellationToken.None);
        }
    }

    private async Task SendRuntimeMessageAsync(string message, CancellationToken cancellationToken)
    {
        if (_primaryHostSender is not null)
        {
            await _primaryHostSender(message, cancellationToken);
        }

        if (_host is not null)
        {
            await _host.SendMessageAsync(message, cancellationToken);
        }
    }

    public async Task<SpeechResult> SpeakTextAsync(string text, CancellationToken cancellationToken = default)
    {
        var voice = _preferences.AvatarProfile.Equals("female", StringComparison.OrdinalIgnoreCase)
            ? _preferences.FemaleVoiceId
            : _preferences.MaleVoiceId;

        var request = new SpeechRequest
        {
            Text = text,
            VoiceId = voice,
            Speed = _options.Speech.Speed,
        };

        var result = await _speechService.SynthesizeAsync(request, cancellationToken);
        if (!result.Success || string.IsNullOrWhiteSpace(result.AudioPath))
        {
            return result;
        }

        var audioPath = result.AudioPath;
        if (!Path.IsPathFullyQualified(audioPath))
        {
            var basePath = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            audioPath = Path.GetFullPath(Path.Combine(basePath, audioPath));
        }

        if (!File.Exists(audioPath))
        {
            return new SpeechResult
            {
                Success = false,
                Detail = "Kokoro runtime returned an audio path that does not exist.",
            };
        }

        await SpeakAsync(new SpeechPlaybackData
        {
            AudioUrl = await BuildAudioDataUrlAsync(audioPath, cancellationToken),
            DurationMs = result.DurationMs,
            Cues = BuildDevelopmentCues(text, result.DurationMs),
        }, cancellationToken);

        return result;
    }

    private static async Task<string> BuildAudioDataUrlAsync(string audioPath, CancellationToken cancellationToken)
    {
        var mediaType = Path.GetExtension(audioPath).ToLowerInvariant() switch
        {
            ".mp3" => "audio/mpeg",
            ".ogg" => "audio/ogg",
            ".flac" => "audio/flac",
            _ => "audio/wav",
        };
        var bytes = await File.ReadAllBytesAsync(audioPath, cancellationToken);
        return $"data:{mediaType};base64,{Convert.ToBase64String(bytes)}";
    }

    private static List<SpeechCue> BuildDevelopmentCues(string text, int durationMs)
    {
        var cues = new List<SpeechCue>();
        if (durationMs <= 0)
        {
            return cues;
        }

        var tokens = text.Split([' ', '\t', '\r', '\n'], StringSplitOptions.RemoveEmptyEntries);
        if (tokens.Length == 0)
        {
            return cues;
        }

        var step = Math.Max(70, durationMs / tokens.Length);
        for (var i = 0; i < tokens.Length; i++)
        {
            var viseme = (i % 5) switch
            {
                0 => "PP",
                1 => "aa",
                2 => "FF",
                3 => "O",
                _ => "sil",
            };
            cues.Add(new SpeechCue
            {
                TimeMs = Math.Min(durationMs, i * step),
                Viseme = viseme,
                Weight = viseme == "sil" ? 0.1 : 1.0,
            });
        }

        cues.Add(new SpeechCue { TimeMs = durationMs, Viseme = "sil", Weight = 0.0 });
        return cues;
    }
}
