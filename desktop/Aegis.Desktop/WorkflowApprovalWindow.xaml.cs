using System.Windows;
using System.Text.Json;
using System.Windows.Controls;
namespace Aegis.Desktop;
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
        "plan_review" => ("approve_plan", "APPROVE WORKFLOW PLAN", "Approve the workflow design before A.E.G.I.S.-9 creates detailed non-production test plans. No code is built at this gate."),
        "plan_approved" => ("generate_test_plans", "DESIGN TEST PLANS", "A qualified reasoning model will design detailed isolated test plans for user review."),
        "test_plan_review" => ("approve_test_plan", "APPROVE TEST PLANS + AUTHORIZE BUILD", "Approve the proposed test procedures before a coding model builds the workflow and corresponding test artifacts."),
        "test_plan_approved" => ("generate_implementation", "BUILD WORKFLOW + TESTS", "A coding model will implement only the approved workflow and approved test plans."),
        "implementation_review" => ("submit_for_test", "SUBMIT FOR TEST", "Review the generated implementation before it enters the isolated-test queue."),
        "test_ready" => ("run_test", "RUN SAFE TEST", "Run the selected bounded non-production profile and retain hashed evidence."),
        "test_failed" => ("run_test", "RETRY SAFE TEST", "Review the permission findings or build errors, revise when necessary, and run validation again."),
        "test_passed" => ("user_accept", "USER ACCEPT", "User acceptance confirms the result but does not grant production authority."),
        "user_accepted" => ("request_supervisor", "REQUEST SUPERVISOR", "Submit this exact revision for independent production approval."),
        "supervisor_pending" when _workflow.Schedule.Count == 0 => ("set_schedule", "SET SCHEDULE / CONDITIONS", "Record the production trigger, timezone, purpose, and declarative prerequisites before requesting final supervisor authorization."),
        "supervisor_pending" => ("supervisor_approve", "SUPERVISOR APPROVE", "Approval binds this exact revision, artifact, permission manifest, and saved schedule to the configured Windows supervisor identity."),
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
        var showingTestPlan = !showingImplementation && !string.IsNullOrWhiteSpace(_workflow.TestPlanText) && _workflow.State is "test_plan_review" or "test_plan_approved";
        var evidence = string.IsNullOrWhiteSpace(_workflow.LatestTestStatus) ? "" : $"\n\n--- RETAINED TEST EVIDENCE ---\nStatus: {_workflow.LatestTestStatus}\nArtifact SHA-256: {_workflow.ArtifactSha256}\nEvidence SHA-256: {_workflow.LatestTestEvidenceSha256}\nSummary: {_workflow.LatestTestSummary}\nPermission manifest:\n{JsonSerializer.Serialize(_workflow.PermissionManifest, new JsonSerializerOptions { WriteIndented = true })}";
        ArtifactText.Text = (showingImplementation ? _workflow.ImplementationText : showingTestPlan ? _workflow.TestPlanText : _workflow.PlanText) + evidence;
        ModelText.Text = showingImplementation ? $"Implementation model: {_workflow.ImplementationProvider} / {_workflow.ImplementationModel}" : showingTestPlan ? $"Test-plan model: {_workflow.TestPlanProvider} / {_workflow.TestPlanModel}" : string.IsNullOrWhiteSpace(_workflow.PlanText) ? "Planning model selection pending." : $"Planning model: {_workflow.PlanProvider} / {_workflow.PlanModel}";
    }
    private async void AdvanceButton_Click(object sender, RoutedEventArgs e)
    {
        var next = NextGate();
        if (next is null) return;
        if (next.Value.decision == "approve_plan" && MessageBox.Show(
            this,
            "Approve this reviewed plan and authorize A.E.G.I.S.-9 to build its PowerShell/C# implementation and non-production test plans? This does not authorize testing or production use.",
            "Approve Plan and Authorize Build",
            MessageBoxButton.YesNo,
            MessageBoxImage.Question) != MessageBoxResult.Yes) return;
        if (next.Value.decision == "approve_test_plan" && MessageBox.Show(
            this,
            "Approve these non-production test plans and authorize A.E.G.I.S.-9 to build the workflow and test artifacts? Testing and production still require later approvals.",
            "Approve Test Plans and Authorize Build",
            MessageBoxButton.YesNo,
            MessageBoxImage.Question) != MessageBoxResult.Yes) return;
        if (next.Value.decision == "set_schedule")
        {
            StatusText.Text = "Record the production schedule and conditions before supervisor approval.";
            new WorkflowScheduleWindow(_workflow) { Owner = this }.ShowDialog();
            _workflow = (await _client.GetWorkflowsAsync(CancellationToken.None)).First(item => item.Id == _workflow.Id);
            StatusText.Text = _workflow.Schedule.Count == 0 ? "Schedule was not saved." : "Schedule saved. Final supervisor approval is now available.";
            Render();
            return;
        }
        AdvanceButton.IsEnabled = false;
        StatusText.Text = "A.E.G.I.S.-9 is selecting the best available model…";
        try
        {
            _workflow = next.Value.decision switch
            {
                "design_plan" => await _client.DesignWorkflowPlanAsync(_workflow.Id, CancellationToken.None),
                "generate_test_plans" => await _client.GenerateWorkflowTestPlansAsync(_workflow.Id, CancellationToken.None),
                "generate_implementation" => await _client.GenerateWorkflowImplementationAsync(_workflow.Id, CancellationToken.None),
                "run_test" => (await _client.RunWorkflowTestAsync(_workflow.Id, (TestProfileInput.SelectedItem as ComboBoxItem)?.Tag?.ToString() ?? "static", CancellationToken.None)).Workflow,
                _ => await _client.ReviewWorkflowAsync(_workflow.Id, next.Value.decision, CancellationToken.None)
            };
            if (next.Value.decision == "approve_plan")
            {
                StatusText.Text = "Workflow plan approved. A.E.G.I.S.-9 is designing detailed non-production test plans…";
                _workflow = await _client.GenerateWorkflowTestPlansAsync(_workflow.Id, CancellationToken.None);
                StatusText.Text = "Test plans are ready for your review and approval.";
            }
            else if (next.Value.decision == "approve_test_plan")
            {
                StatusText.Text = "Test plans approved. A.E.G.I.S.-9 is building the workflow and corresponding test artifacts…";
                _workflow = await _client.GenerateWorkflowImplementationAsync(_workflow.Id, CancellationToken.None);
                StatusText.Text = "Workflow and test implementation are ready for review.";
            }
            else StatusText.Text = "Stage completed and recorded.";
            Render();
        }
        catch (Exception error) { StatusText.Text = error.Message; Render(); }
    }

    private async void RejectButton_Click(object sender, RoutedEventArgs e) { if (MessageBox.Show(this, "Reject this workflow revision? Its audit history will be retained.", "Confirm rejection", MessageBoxButton.YesNo, MessageBoxImage.Warning) != MessageBoxResult.Yes) return; try { _workflow = await _client.ReviewWorkflowAsync(_workflow.Id, "reject", CancellationToken.None); Render(); } catch (Exception error) { StatusText.Text = error.Message; } }
}
