using System.Windows;
namespace Aegis.Desktop;
public partial class WorkflowDeleteWindow : Window
{
    private readonly Workflow _workflow; private readonly MonitoringClient _client = new("http://127.0.0.1:8000");
    public WorkflowDeleteWindow(Workflow workflow) { InitializeComponent(); _workflow = workflow; DetailsText.Text = $"{workflow.Title}\nRevision {workflow.Revision} · {workflow.Language} · {workflow.State}"; }
    private async void ArchiveButton_Click(object sender, RoutedEventArgs e) { if (ConfirmCheck.IsChecked != true || ConfirmationInput.Text.Trim() != "ARCHIVE") { StatusText.Text = "Check the confirmation and type ARCHIVE exactly."; return; } try { await _client.ArchiveWorkflowAsync(_workflow.Id, CancellationToken.None); DialogResult = true; } catch (Exception error) { StatusText.Text = error.Message; } }
    private void CancelButton_Click(object sender, RoutedEventArgs e) => DialogResult = false;
}
