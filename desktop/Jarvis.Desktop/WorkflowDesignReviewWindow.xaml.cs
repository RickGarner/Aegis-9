using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
namespace Jarvis.Desktop;
public partial class WorkflowDesignReviewWindow : Window
{
    private readonly MonitoringClient _client = new("http://127.0.0.1:8000"); private Workflow _workflow; private readonly Dictionary<string, (Control Input, Button Submit)> _questionControls = [];
    public Workflow? UpdatedWorkflow { get; private set; }
    public WorkflowDesignReviewWindow(Workflow workflow) { InitializeComponent(); _workflow = workflow; HeadingText.Text = workflow.Title; Loaded += async (_, _) => await LoadReviewAsync(); }
    private async Task LoadReviewAsync()
    {
        ReviewStatusText.Text = "LOADING AUTHORITATIVE WORKFLOW STATE";
        PlanText.Text = "Loading the saved workflow plan from A.E.G.I.S.-9...";
        UpdateDraftButton.IsEnabled = false;
        try
        {
            _workflow = await _client.GetWorkflowAsync(_workflow.Id, CancellationToken.None);
            if (_workflow.State is "draft" or "rejected") { OperationStatusText.Text = "A.E.G.I.S.-9 is selecting a planning model and preparing the review…"; _workflow = await _client.DesignWorkflowPlanAsync(_workflow.Id, CancellationToken.None); }
            Render();
        }
        catch (Exception error) { OperationStatusText.Text = error.Message; Render(); }
    }
    private void Render()
    {
        PlanText.Text = _workflow.PlanText; ModelText.Text = string.IsNullOrWhiteSpace(_workflow.PlanModel) ? "Planning model selection pending" : $"{_workflow.PlanProvider} / {_workflow.PlanModel}";
        QuestionsPanel.Children.Clear(); _questionControls.Clear();
        if (string.IsNullOrWhiteSpace(_workflow.PlanText))
        {
            QuestionsPanel.Children.Add(new TextBlock { Text = "No usable workflow plan was returned. Close this review, reopen the workflow, and retry planning. Approval and final submission remain locked.", Foreground = new SolidColorBrush(Color.FromRgb(255, 184, 77)), TextWrapping = TextWrapping.Wrap });
            ReviewStatusText.Text = "PLAN GENERATION INCOMPLETE Â· RETRY REQUIRED";
            UpdateDraftButton.IsEnabled = false;
            UpdateDraftButton.Content = "FINAL SUBMIT LOCKED";
            return;
        }
        if (_workflow.ClarificationQuestions.Count == 0)
        {
            QuestionsPanel.Children.Add(new TextBlock { Text = "No additional questions were identified. Submit this tentative plan for final A.E.G.I.S.-9 refinement before approval or rejection becomes available.", Foreground = new SolidColorBrush(Color.FromRgb(77, 231, 255)), TextWrapping = TextWrapping.Wrap });
            ReviewStatusText.Text = "TENTATIVE PLAN REVIEW · READY FOR FINAL SUBMISSION"; UpdateDraftButton.IsEnabled = true; UpdateDraftButton.Content = "FINAL SUBMIT / UPDATE DRAFT"; return;
        }
        foreach (var question in _workflow.ClarificationQuestions) AddQuestion(question);
        RefreshCompletionState();
    }
    private void AddQuestion(WorkflowClarificationQuestion question)
    {
        var card = new Border { BorderBrush = new SolidColorBrush(Color.FromArgb(75, 56, 201, 234)), BorderThickness = new Thickness(0, 0, 0, 1), Padding = new Thickness(0, 0, 0, 15), Margin = new Thickness(0, 0, 0, 15) }; var stack = new StackPanel();
        stack.Children.Add(new TextBlock { Text = question.Prompt + (question.Required ? "  *" : ""), TextWrapping = TextWrapping.Wrap, FontSize = 13 });
        Control input = question.Options.Count > 0 ? new ComboBox { ItemsSource = question.Options, Margin = new Thickness(0, 8, 0, 7), Padding = new Thickness(7) } : new TextBox { MinHeight = 64, AcceptsReturn = true, TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 8, 0, 7) };
        var submit = new Button { Content = "SUBMIT THIS ANSWER", Tag = question, HorizontalAlignment = HorizontalAlignment.Left };
        submit.Click += SubmitAnswer_Click; stack.Children.Add(input); stack.Children.Add(submit); card.Child = stack; QuestionsPanel.Children.Add(card); _questionControls[question.Id] = (input, submit);
        if (_workflow.ClarificationAnswers.TryGetValue(question.Id, out var answer) && !string.IsNullOrWhiteSpace(answer)) { if (input is TextBox text) text.Text = answer; else if (input is ComboBox combo) combo.SelectedItem = answer; input.IsEnabled = false; submit.Content = "ANSWER SUBMITTED"; submit.IsEnabled = false; }
    }
    private async void SubmitAnswer_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button { Tag: WorkflowClarificationQuestion question } submit || !_questionControls.TryGetValue(question.Id, out var controls)) return;
        var answer = controls.Input is TextBox text ? text.Text.Trim() : (controls.Input as ComboBox)?.SelectedItem?.ToString()?.Trim() ?? ""; if (string.IsNullOrWhiteSpace(answer)) { OperationStatusText.Text = "Enter or select an answer before submitting this question."; return; }
        submit.IsEnabled = false; OperationStatusText.Text = "Submitting this answer…";
        try { _workflow = await _client.AnswerWorkflowQuestionAsync(_workflow.Id, question.Id, answer, CancellationToken.None); controls.Input.IsEnabled = false; submit.Content = "ANSWER SUBMITTED"; OperationStatusText.Text = "Answer recorded. Continue with the remaining questions."; RefreshCompletionState(); }
        catch (Exception error) { OperationStatusText.Text = error.Message; submit.IsEnabled = true; }
    }
    private void RefreshCompletionState()
    {
        var required = _workflow.ClarificationQuestions.Where(question => question.Required).ToList(); var remaining = required.Count(question => !_workflow.ClarificationAnswers.TryGetValue(question.Id, out var answer) || string.IsNullOrWhiteSpace(answer));
        ReviewStatusText.Text = remaining == 0 ? "ALL REQUIRED ANSWERS SUBMITTED · UPDATE DRAFT AVAILABLE" : $"REVIEW REQUIRED · {remaining} REQUIRED ANSWER(S) REMAIN"; UpdateDraftButton.IsEnabled = remaining == 0; UpdateDraftButton.Content = "UPDATE DRAFT";
    }
    private async void UpdateDraftButton_Click(object sender, RoutedEventArgs e)
    {
        UpdateDraftButton.IsEnabled = false; OperationStatusText.Text = "Updating the draft and asking A.E.G.I.S.-9 to re-evaluate the complete plan…";
        try { UpdatedWorkflow = await _client.CompleteWorkflowDesignReviewAsync(_workflow.Id, CancellationToken.None); DialogResult = true; }
        catch (Exception error) { OperationStatusText.Text = error.Message; RefreshCompletionState(); }
    }
    private void CloseButton_Click(object sender, RoutedEventArgs e) => DialogResult = false;
}
