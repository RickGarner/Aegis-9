using System.Windows;
namespace Jarvis.Desktop;
public partial class WorkflowApprovalWindow : Window
{
    private readonly MonitoringClient _client = new("http://127.0.0.1:8000"); private Workflow _workflow;
    public WorkflowApprovalWindow(Workflow workflow)
    {
        InitializeComponent();
        _workflow = workflow;
        Render();
        Loaded += (_, _) =>
        {
            if (_workflow.State is "draft" or "rejected")
            {
                StatusText.Text = "Starting required AI design analysis…";
                AdvanceButton.RaiseEvent(new RoutedEventArgs(System.Windows.Controls.Button.ClickEvent));
            }
        };
    }
    private (string decision, string label, string guidance)? NextGate() => _workflow.State switch
    {
        "draft" => ("design_plan", "DESIGN AI PLAN", "A reasoning model will be selected to analyze the request and documents. It will create a plan, not executable code."),
        "rejected" => ("design_plan", "REVISE AI PLAN", "The rejected plan will be analyzed again before it can return to design review."),
        "plan_review" => ("approve_plan", "APPROVE REVIEWED PLAN", "The design review is complete and has no unanswered required questions. Approving it unlocks coding-model implementation."),
        "plan_approved" => ("generate_implementation", "GENERATE IMPLEMENTATION", "A coding model will be selected independently to implement the approved plan."),
        "implementation_review" => ("submit_for_test", "SUBMIT FOR TEST", "Review the generated implementation before it enters the isolated-test queue."),
        "test_ready" => ("test_pass", "RECORD TEST PASS", "Use only after reviewing retained non-production test evidence. The actual test runner is not connected yet."),
        "test_passed" => ("user_accept", "USER ACCEPT", "User acceptance confirms the result but does not grant production authority."),
        "user_accepted" => ("request_supervisor", "REQUEST SUPERVISOR", "Submit this exact revision for independent production approval."),
        "supervisor_pending" => ("supervisor_approve", "SUPERVISOR APPROVE", "Supervisor approval unlocks scheduling; it does not immediately start the workflow."),
        _ => null
    };
    private void Render()
    {
        HeadingText.Text = _workflow.Title;
        GateText.Text = $"{_workflow.State.ToUpperInvariant()} · REVISION {_workflow.Revision}";
        DescriptionText.Text = _workflow.Description;
        ImplementationText.Text = _workflow.Language == "csharp" ? "C# / compiled artifact" : "PowerShell / constrained runner";
        var next = NextGate();
        AdvanceButton.IsEnabled = next is not null;
        AdvanceButton.Content = next?.label ?? "NO ACTION AVAILABLE";
        GuidanceText.Text = next?.guidance ?? "This workflow has no approval transition available from its current state.";
        var unanswered = _workflow.ClarificationQuestions.Count;
        QuestionStatusText.Text = _workflow.State == "needs_clarification"
            ? $"REVIEW BLOCKED · {unanswered} unanswered required or optional question(s). Select Answer Questions."
            : _workflow.State == "plan_review"
                ? "REVIEW COMPLETE · No unanswered questions. Plan approval is now available."
                : _workflow.State == "draft"
                    ? "ANALYSIS REQUIRED · A.E.G.I.S.-9 is preparing the design review."
                    : "No unresolved design questions are recorded at this stage.";
        var showingImplementation = !string.IsNullOrWhiteSpace(_workflow.ImplementationText);
        ArtifactText.Text = showingImplementation ? _workflow.ImplementationText : _workflow.PlanText;
        ModelText.Text = showingImplementation ? $"Implementation model: {_workflow.ImplementationProvider} / {_workflow.ImplementationModel}" : string.IsNullOrWhiteSpace(_workflow.PlanText) ? "Planning model selection pending." : $"Planning model: {_workflow.PlanProvider} / {_workflow.PlanModel}";
    }
    private async void AdvanceButton_Click(object sender, RoutedEventArgs e)
    {
        var next = NextGate();
        if (next is null) return;
        AdvanceButton.IsEnabled = false;
        StatusText.Text = "A.E.G.I.S.-9 is selecting the best available model…";
        try
        {
            _workflow = next.Value.decision switch
            {
                "design_plan" => await _client.DesignWorkflowPlanAsync(_workflow.Id, CancellationToken.None),
                "generate_implementation" => await _client.GenerateWorkflowImplementationAsync(_workflow.Id, CancellationToken.None),
                _ => await _client.ReviewWorkflowAsync(_workflow.Id, next.Value.decision, CancellationToken.None)
            };
            if (next.Value.decision == "approve_plan")
            {
                StatusText.Text = "Plan approved. A.E.G.I.S.-9 is selecting a coding model and creating the workflow plus test plans…";
                _workflow = await _client.GenerateWorkflowImplementationAsync(_workflow.Id, CancellationToken.None);
                StatusText.Text = "Workflow implementation and test plans are ready for review and testing.";
            }
            else StatusText.Text = "Stage completed and recorded.";
            Render();
        }
        catch (Exception error) { StatusText.Text = error.Message; Render(); }
    }

    private async void RejectButton_Click(object sender, RoutedEventArgs e) { if (MessageBox.Show(this, "Reject this workflow revision? Its audit history will be retained.", "Confirm rejection", MessageBoxButton.YesNo, MessageBoxImage.Warning) != MessageBoxResult.Yes) return; try { _workflow = await _client.ReviewWorkflowAsync(_workflow.Id, "reject", CancellationToken.None); Render(); } catch (Exception error) { StatusText.Text = error.Message; } }
}
