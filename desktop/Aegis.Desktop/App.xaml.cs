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
    private readonly MonitoringClient _monitoringClient = new(Environment.GetEnvironmentVariable("JARVIS_MONITORING_URL") ?? "http://127.0.0.1:8000");

    protected override async void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        try
        {
            var ready = await WaitForBackendReadyAsync(TimeSpan.FromSeconds(1));
            if (!ready)
            {
                var (backendDir, pythonExe) = ResolveBackendRuntime();
                _backendLauncher = new BackendLauncher(backendDir, pythonExe);
                await _backendLauncher.StartAsync(CancellationToken.None);

                ready = await WaitForBackendReadyAsync(TimeSpan.FromSeconds(30));
                if (!ready)
                {
                    MessageBox.Show("A.E.G.I.S.-9 could not start the local backend within the timeout. See backend/logs for details.", "A.E.G.I.S.-9", MessageBoxButton.OK, MessageBoxImage.Warning);
                }
            }
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Failed to start the local backend: {ex.Message}", "A.E.G.I.S.-9", MessageBoxButton.OK, MessageBoxImage.Error);
        }

        var mainWindow = new MainWindow();
        MainWindow = mainWindow;
        mainWindow.Show();
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

    private async Task<bool> WaitForBackendReadyAsync(TimeSpan timeout)
    {
        var sw = Stopwatch.StartNew();
        while (sw.Elapsed < timeout)
        {
            if (await _monitoringClient.CheckHealthAsync(CancellationToken.None)) return true;
            await Task.Delay(500);
        }
        return false;
    }

    protected override async void OnExit(ExitEventArgs e)
    {
        base.OnExit(e);
        if (_backendLauncher != null)
        {
            await _backendLauncher.StopAsync();
            _backendLauncher.Dispose();
        }
    }
}

