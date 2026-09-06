from app.workflow_lifecycle import REVIEW_TRANSITIONS, resolve_review_transition


def test_review_transition_contract_has_unique_state_action_pairs() -> None:
    keys = [(rule.source, rule.action) for rule in REVIEW_TRANSITIONS]
    assert len(keys) == len(set(keys))


def test_review_transition_contract_resolves_the_governed_path() -> None:
    assert resolve_review_transition("plan_review", "approve_plan") == ("plan_approved", "plan_approved")
    assert resolve_review_transition("test_plan_review", "approve_test_plan") == ("test_plan_approved", "test_plan_approved")
    assert resolve_review_transition("implementation_review", "submit_for_test") == ("test_ready", "test_ready")
    assert resolve_review_transition("test_passed", "user_accept") == ("user_accepted", "user_accepted")
    assert resolve_review_transition("user_accepted", "request_supervisor") == ("supervisor_pending", "supervisor_pending")


def test_review_transition_contract_fails_closed() -> None:
    assert resolve_review_transition("draft", "approve_plan") is None
    assert resolve_review_transition("running", "reject") is None
    assert resolve_review_transition("plan_review", "reject") == ("rejected", "rejected")
