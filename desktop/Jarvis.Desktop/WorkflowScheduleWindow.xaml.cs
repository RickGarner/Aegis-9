using System.Globalization;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;

namespace Jarvis.Desktop;

public partial class WorkflowScheduleWindow : Window
{
    private readonly Workflow _workflow;
    private readonly MonitoringClient _client = new("http://127.0.0.1:8000");

    public WorkflowScheduleWindow(Workflow workflow)
    {
        InitializeComponent();
        _workflow = workflow;
        HeadingText.Text = workflow.Title;
        StartDateInput.SelectedDate = DateTime.Today;
        LoadExistingSchedule();
        UpdateFieldVisibility();
    }

    private void LoadExistingSchedule()
    {
        if (_workflow.Schedule.Count == 0) return;
        SelectByTag(TriggerInput, ReadString("trigger", "recurring"));
        SelectByTag(IntervalUnitInput, ReadString("interval_unit", "days"));
        StartDateInput.SelectedDate = ReadDate("start_date") ?? DateTime.Today;
        EndDateInput.SelectedDate = ReadDate("end_date");
        StartTimeInput.Text = ReadString("start_time", "00:00");
        EndTimeInput.Text = ReadString("end_time", "23:59");
        IntervalValueInput.Text = ReadInt("interval_value", 1).ToString(CultureInfo.InvariantCulture);
        TimezoneInput.Text = ReadString("timezone", "America/New_York");
        ReasonInput.Text = ReadString("reason", "");
        StartInput.Text = ReadString("start_conditions", "");
        StopInput.Text = ReadString("stop_conditions", "");
    }

    private string ReadString(string key, string fallback) => _workflow.Schedule.TryGetValue(key, out var value) && value.ValueKind == JsonValueKind.String ? value.GetString() ?? fallback : fallback;
    private int ReadInt(string key, int fallback) => _workflow.Schedule.TryGetValue(key, out var value) && value.TryGetInt32(out var result) ? result : fallback;
    private DateTime? ReadDate(string key) => DateTime.TryParseExact(ReadString(key, ""), "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var value) ? value : null;
    private static void SelectByTag(ComboBox box, string tag) { foreach (var item in box.Items.OfType<ComboBoxItem>()) if (string.Equals(item.Tag?.ToString(), tag, StringComparison.OrdinalIgnoreCase)) { box.SelectedItem = item; return; } }
    private void TriggerInput_SelectionChanged(object sender, SelectionChangedEventArgs e) => UpdateFieldVisibility();
    private void UpdateFieldVisibility() { if (CalendarFields is null || RecurrenceFields is null) return; var trigger = (TriggerInput.SelectedItem as ComboBoxItem)?.Tag?.ToString() ?? "recurring"; CalendarFields.Visibility = trigger == "manual" ? Visibility.Collapsed : Visibility.Visible; RecurrenceFields.Visibility = trigger == "recurring" ? Visibility.Visible : Visibility.Collapsed; }

    private async void SaveButton_Click(object sender, RoutedEventArgs e)
    {
        var trigger = (TriggerInput.SelectedItem as ComboBoxItem)?.Tag?.ToString() ?? "recurring";
        if (!int.TryParse(IntervalValueInput.Text.Trim(), out var intervalValue) || intervalValue < 1) { StatusText.Text = "Run Every must be a whole number greater than zero."; return; }
        var schedule = new WorkflowSchedule {
            Trigger = trigger, Timezone = TimezoneInput.Text.Trim(), Reason = ReasonInput.Text.Trim(), StartConditions = StartInput.Text.Trim(), StopConditions = StopInput.Text.Trim(),
            StartDate = trigger == "manual" ? "" : StartDateInput.SelectedDate?.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) ?? "",
            EndDate = trigger == "manual" ? "" : EndDateInput.SelectedDate?.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) ?? "",
            StartTime = StartTimeInput.Text.Trim(), EndTime = EndTimeInput.Text.Trim(), IntervalValue = intervalValue,
            IntervalUnit = (IntervalUnitInput.SelectedItem as ComboBoxItem)?.Tag?.ToString() ?? "days"
        };
        try { await _client.ScheduleWorkflowAsync(_workflow.Id, schedule, CancellationToken.None); DialogResult = true; }
        catch (Exception error) { StatusText.Text = error.Message; }
    }
    private void CancelButton_Click(object sender, RoutedEventArgs e) => DialogResult = false;
}
