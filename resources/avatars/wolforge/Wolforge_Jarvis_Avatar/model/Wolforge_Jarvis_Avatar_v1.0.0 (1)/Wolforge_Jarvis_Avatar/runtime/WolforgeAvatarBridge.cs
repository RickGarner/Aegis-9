using Microsoft.Web.WebView2.Wpf;

namespace Jarvis.Avatar;

public sealed class WolforgeAvatarBridge
{
    private readonly WebView2 _webView;
    public WolforgeAvatarBridge(WebView2 webView) => _webView = webView;

    private async Task CallAsync(string method) =>
        await _webView.ExecuteScriptAsync($"window.WolforgeAvatar?.{method}();");

    public Task IdleAsync() => CallAsync("idle");
    public Task BlinkAsync() => CallAsync("blink");
    public Task ListeningAsync() => CallAsync("listen");
    public Task ThinkingAsync() => CallAsync("think");
    public Task SpeakingAsync() => CallAsync("speak");
    public Task StopSpeakingAsync() => CallAsync("stopSpeaking");
    public Task SuccessAsync() => CallAsync("success");
    public Task WarningAsync() => CallAsync("warning");
    public Task ErrorAsync() => CallAsync("error");
    public Task JawTestAsync() => CallAsync("jawTest");
}
