using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;

namespace Aegis.Desktop;

/// <summary>
/// Interaction logic for App.xaml
/// </summary>
public partial class App : Application
{
    private BackendLauncher? _backendLauncher;
    private Task? _shutdownTask;
    private readonly MonitoringClient _monitoringClient = new(Environment.GetEnvironmentVariable("JARVIS_MONITORING_URL") ?? "http://127.0.0.1:8000");
    public string? BackendDirectory { get; private set; }
    public string? PythonExecutable { get; private set; }

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        ShutdownMode = ShutdownMode.OnExplicitShutdown;
        var coordinator = new StartupCoordinator(_monitoringClient, EnsureBackendAsync);
        var splash = new StartupSplashWindow(coordinator);
        MainWindow = splash;
        splash.EntryRequested += window =>
        {
            var main = new MainWindow(window.StartupState);
            MainWindow = main;
            ShutdownMode = ShutdownMode.OnExplicitShutdown;
            main.Closing += async (_, args) => { if (_shutdownTask is not null) return; args.Cancel = true; await ShutdownOwnedBackendAsync(); };
            main.Show();
            window.Close();
        };
        splash.Closed += async (_, _) => { if (!splash.Entered) await ShutdownOwnedBackendAsync(); };
        splash.Show();
    }

    public async Task ShutdownOwnedBackendAsync()
    {
        _shutdownTask ??= ShutdownCoreAsync();
        await _shutdownTask;
    }

    private async Task ShutdownCoreAsync()
    {
        var launcher = _backendLauncher; _backendLauncher = null;
        if (launcher != null) { await launcher.StopAsync(); launcher.Dispose(); }
        Shutdown();
    }

    private async Task<(bool Ready, string Detail)> EnsureBackendAsync(CancellationToken token)
    {
        if (await WaitForBackendReadyAsync(TimeSpan.FromSeconds(1), token)) return (true, "Existing backend recognized on the local command channel.");
        var runtime = ResolveBackendRuntime(); BackendDirectory = runtime.BackendDirectory; PythonExecutable = runtime.PythonExecutable;
        _backendLauncher = new BackendLauncher(runtime.BackendDirectory, runtime.PythonExecutable);
        await _backendLauncher.StartAsync(token);
        var ready = await WaitForBackendReadyAsync(TimeSpan.FromSeconds(30), token);
        return (ready, ready ? $"Owned backend started with {Path.GetFileName(runtime.PythonExecutable)}." : "Backend did not become ready within 30 seconds.");
    }

    private static (string BackendDirectory, string PythonExecutable) ResolveBackendRuntime()
    {
        var exeDir = new DirectoryInfo(AppDomain.CurrentDomain.BaseDirectory);
        for (var directory = exeDir; directory != null; directory = directory.Parent)
        {
            var backendDir = Path.Combine(directory.FullName, "backend");
            if (!Directory.Exists(Path.Combine(backendDir, "app"))) continue;

            var bundledPython = Path.Combine(backendDir, "python", "python.exe");
            if (File.Exists(bundledPython)) return (backendDir, bundledPython);

            var repositoryPython = Path.Combine(directory.FullName, ".venv", "Scripts", "python.exe");
            if (File.Exists(repositoryPython)) return (backendDir, repositoryPython);

            return (backendDir, "python.exe");
        }

        throw new DirectoryNotFoundException("Could not locate the A.E.G.I.S.-9 backend directory.");
    }

    private async Task<bool> WaitForBackendReadyAsync(TimeSpan timeout, CancellationToken token)
    {
        var sw = Stopwatch.StartNew();
        while (sw.Elapsed < timeout)
        {
            token.ThrowIfCancellationRequested();
            if (await _monitoringClient.CheckHealthAsync(token)) return true;
            await Task.Delay(500, token);
        }
        return false;
    }

    protected override void OnExit(ExitEventArgs e)
    {
        base.OnExit(e);
        _backendLauncher?.Dispose();
    }
}

