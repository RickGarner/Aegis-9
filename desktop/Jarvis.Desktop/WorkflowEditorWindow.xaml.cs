using Microsoft.Win32;
using System.Windows;
using System.Windows.Controls;

namespace Jarvis.Desktop;

public partial class WorkflowEditorWindow : Window
{
    private readonly MonitoringClient _client = new("http://127.0.0.1:8000");
    private readonly Workflow? _workflow;
    private readonly List<FileEntry> _attachments = [];
    public bool Saved { get; private set; }
    public Workflow? SavedWorkflow { get; private set; }

    public WorkflowEditorWindow(Workflow? workflow = null)
    {
        InitializeComponent();
        _workflow = workflow;
        if (workflow is null) return;
        HeadingText.Text = $"Edit workflow · revision {workflow.Revision}";
        TitleInput.Text = workflow.Title;
        DescriptionInput.Text = workflow.Description;
        LanguageInput.SelectedIndex = workflow.Language == "csharp" ? 1 : 0;
    }

    private async void UploadButton_Click(object sender, RoutedEventArgs e)
    {
        var picker = new OpenFileDialog { Multiselect = true, Filter = "Supported documents|*.txt;*.md;*.json;*.csv;*.pdf;*.docx;*.ps1;*.cs|All files|*.*" };
        if (picker.ShowDialog(this) != true) return;
        foreach (var path in picker.FileNames)
        {
            try { _attachments.Add(await _client.UploadFileAsync(path, CancellationToken.None)); }
            catch (Exception error) { StatusText.Text = $"Could not stage {System.IO.Path.GetFileName(path)}: {error.Message}"; }
        }
        AttachmentList.ItemsSource = null;
        AttachmentList.ItemsSource = _attachments.Select(file => file.Name).ToList();
    }

    private async void SaveButton_Click(object sender, RoutedEventArgs e)
    {
        var title = TitleInput.Text.Trim();
        if (title.Length == 0) { StatusText.Text = "A workflow name is required."; return; }
        var language = (LanguageInput.SelectedItem as ComboBoxItem)?.Tag?.ToString() ?? "powershell";
        var request = new WorkflowRequest { Title = title, Description = DescriptionInput.Text.Trim(), Language = language, AttachmentIds = _attachments.Select(file => file.Id).ToList() };
        try
        {
            SavedWorkflow = _workflow is null
                ? await _client.CreateWorkflowAsync(request.Title, request.Description, request.AttachmentIds, CancellationToken.None, request.Language)
                : await _client.UpdateWorkflowAsync(_workflow.Id, request, CancellationToken.None);
            Saved = true; DialogResult = true;
        }
        catch (Exception error) { StatusText.Text = $"Draft was not saved: {error.Message}"; }
    }

    private void CancelButton_Click(object sender, RoutedEventArgs e) => DialogResult = false;
}
