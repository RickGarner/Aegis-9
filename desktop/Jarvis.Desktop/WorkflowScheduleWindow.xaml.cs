using System.Windows;
using System.Windows.Controls;
namespace Jarvis.Desktop;
public partial class WorkflowScheduleWindow : Window
{
    private readonly Workflow _workflow; private readonly MonitoringClient _client = new("http://127.0.0.1:8000");
    public WorkflowScheduleWindow(Workflow workflow) { InitializeComponent(); _workflow = workflow; HeadingText.Text = workflow.Title; }
    private async void SaveButton_Click(object sender, RoutedEventArgs e) { var schedule = new WorkflowSchedule { Trigger = (TriggerInput.SelectedItem as ComboBoxItem)?.Tag?.ToString() ?? "daily", Expression = ExpressionInput.Text.Trim(), Timezone = TimezoneInput.Text.Trim(), Reason = ReasonInput.Text.Trim(), StartConditions = StartInput.Text.Trim(), StopConditions = StopInput.Text.Trim() }; try { await _client.ScheduleWorkflowAsync(_workflow.Id, schedule, CancellationToken.None); DialogResult = true; } catch (Exception error) { StatusText.Text = error.Message; } }
    private void CancelButton_Click(object sender, RoutedEventArgs e) => DialogResult = false;
}
