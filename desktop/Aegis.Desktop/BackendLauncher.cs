using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
using System.Threading.Tasks;

namespace Aegis.Desktop;

public sealed class BackendLauncher : IDisposable
{
    private readonly string _backendDir;
    private readonly string _pythonExe;
    private Process? _process;

    public BackendLauncher(string backendDir, string pythonExe = "python.exe")
    {
        _backendDir = backendDir;
        _pythonExe = pythonExe;
    }

    public bool IsRunning => _process != null && !_process.HasExited;

    public Task StartAsync(CancellationToken cancellationToken)
    {
        if (IsRunning) return Task.CompletedTask;

        Directory.CreateDirectory(Path.Combine(_backendDir, "logs"));
        var stdout = Path.Combine(_backendDir, "logs", "backend.stdout.log");
        var stderr = Path.Combine(_backendDir, "logs", "backend.stderr.log");

        var psi = new ProcessStartInfo
        {
            FileName = _pythonExe,
            Arguments = "-m uvicorn app.main:app --host 127.0.0.1 --port 8000",
            WorkingDirectory = _backendDir,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
        };

        _process = new Process { StartInfo = psi, EnableRaisingEvents = true };
        _process.OutputDataReceived += (_, e) => { if (e.Data != null) File.AppendAllText(stdout, e.Data + Environment.NewLine); };
        _process.ErrorDataReceived += (_, e) => { if (e.Data != null) File.AppendAllText(stderr, e.Data + Environment.NewLine); };

        _process.Start();
        _process.BeginOutputReadLine();
        _process.BeginErrorReadLine();

        return Task.CompletedTask;
    }

    public async Task StopAsync()
    {
        if (_process == null || _process.HasExited) return;

        try
        {
            _process.CloseMainWindow();
            if (!await WaitForExitAsync(TimeSpan.FromSeconds(5)))
            {
                _process.Kill(true);
                await WaitForExitAsync(TimeSpan.FromSeconds(5));
            }
        }
        catch { }
    }

    private Task<bool> WaitForExitAsync(TimeSpan timeout)
    {
        var tcs = new TaskCompletionSource<bool>();
        if (_process == null || _process.HasExited) return Task.FromResult(true);
        _process.Exited += (_, _) => tcs.TrySetResult(true);
        _ = Task.Delay(timeout).ContinueWith(_ => tcs.TrySetResult(_process == null || _process.HasExited));
        return tcs.Task;
    }

    public void Dispose() => _process?.Dispose();
}
