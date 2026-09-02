using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;

namespace Jarvis.Desktop;

public sealed class DeveloperStudioService(DeveloperStudioOptions options)
{
    private const int RestoreWindow = 9;

    public string FoundationPath => Path.GetFullPath(Environment.ExpandEnvironmentVariables(options.FoundationPath));
    public string ExecutablePath => Path.GetFullPath(Path.Combine(FoundationPath, options.ExecutableRelativePath));

    public DeveloperStudioInstallation GetInstallation() => new(
        FoundationPath,
        ExecutablePath,
        Directory.Exists(FoundationPath),
        File.Exists(ExecutablePath));

    public DeveloperStudioProcessStatus GetProcessStatus()
    {
        foreach (var process in Process.GetProcessesByName(Path.GetFileNameWithoutExtension(ExecutablePath)))
        {
            try
            {
                if (process.MainModule?.FileName.Equals(ExecutablePath, StringComparison.OrdinalIgnoreCase) == true)
                {
                    return new DeveloperStudioProcessStatus(true, process.Id, process.MainWindowHandle);
                }
            }
            catch (InvalidOperationException) { }
            catch (System.ComponentModel.Win32Exception) { }
            finally { process.Dispose(); }
        }
        return new DeveloperStudioProcessStatus(false, null, IntPtr.Zero);
    }

    public DeveloperStudioLaunchResult LaunchOrFocus(string repositoryPath)
    {
        if (!Directory.Exists(repositoryPath)) return new(false, false, null, "The selected repository no longer exists.");
        if (!File.Exists(ExecutablePath)) return new(false, false, null, $"Developer Studio executable was not found at {ExecutablePath}");

        var existing = GetProcessStatus();
        if (existing.Running && existing.ProcessId is int processId)
        {
            using var process = Process.GetProcessById(processId);
            if (process.MainWindowHandle != IntPtr.Zero)
            {
                ShowWindow(process.MainWindowHandle, RestoreWindow);
                SetForegroundWindow(process.MainWindowHandle);
            }
            StartRepositoryRequest(repositoryPath, reuseWindow: true).Dispose();
            return new(true, true, processId, "Developer Studio focused and repository request sent.");
        }

        using var started = StartRepositoryRequest(repositoryPath, reuseWindow: false);
        return new(true, false, started.Id, "Developer Studio launched in a separate window.");
    }

    private Process StartRepositoryRequest(string repositoryPath, bool reuseWindow)
    {
        var startInfo = new ProcessStartInfo { FileName = ExecutablePath, WorkingDirectory = FoundationPath, UseShellExecute = false };
        startInfo.Environment.Remove("ELECTRON_RUN_AS_NODE");
        startInfo.Environment["NODE_ENV"] = "development";
        startInfo.Environment["VSCODE_DEV"] = "1";
        startInfo.Environment["VSCODE_CLI"] = "1";
        startInfo.ArgumentList.Add(FoundationPath);
        startInfo.ArgumentList.Add("--disable-extension=vscode.vscode-api-tests");
        var localAiExtension = Path.Combine(FoundationPath, ".build", "extensions", "local-ai");
        if (File.Exists(Path.Combine(localAiExtension, "package.json")))
        {
            startInfo.ArgumentList.Add($"--extensionDevelopmentPath={localAiExtension}");
        }
        startInfo.ArgumentList.Add(reuseWindow ? "--reuse-window" : "--new-window");
        startInfo.ArgumentList.Add(Path.GetFullPath(repositoryPath));
        return Process.Start(startInfo) ?? throw new InvalidOperationException("Developer Studio did not return a process handle.");
    }

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool SetForegroundWindow(IntPtr windowHandle);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool ShowWindow(IntPtr windowHandle, int command);
}

public sealed record DeveloperStudioInstallation(string FoundationPath, string ExecutablePath, bool FoundationExists, bool ExecutableExists);
public sealed record DeveloperStudioProcessStatus(bool Running, int? ProcessId, IntPtr MainWindowHandle);
public sealed record DeveloperStudioLaunchResult(bool Success, bool FocusedExisting, int? ProcessId, string Detail);
