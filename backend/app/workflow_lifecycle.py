from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowTransitionRule:
    source: str
    action: str
    target: str
    approval_stage: str


REVIEW_TRANSITIONS = (
    WorkflowTransitionRule("plan_review", "approve_plan", "plan_approved", "plan_approved"),
    WorkflowTransitionRule("implementation_review", "submit_for_test", "test_ready", "test_ready"),
    WorkflowTransitionRule("test_failed", "submit_for_test", "test_ready", "test_ready"),
    WorkflowTransitionRule("test_passed", "user_accept", "user_accepted", "user_accepted"),
    WorkflowTransitionRule("user_accepted", "request_supervisor", "supervisor_pending", "supervisor_pending"),
)

REVIEW_TRANSITION_MAP = {
    (rule.source, rule.action): (rule.target, rule.approval_stage)
    for rule in REVIEW_TRANSITIONS
}

NON_REJECTABLE_STATES = frozenset({"running", "paused", "completed"})


def resolve_review_transition(state: str, action: str) -> tuple[str, str] | None:
    if action == "reject" and state not in NON_REJECTABLE_STATES:
        return "rejected", "rejected"
    return REVIEW_TRANSITION_MAP.get((state, action))
