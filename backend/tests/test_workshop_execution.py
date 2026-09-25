"""Revision, approval, cancellation and persistence checks using temporary state."""
import asyncio
import json

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute

from app import main
from app.config import Settings
from app.providers import ProviderFailover, ProviderRoute, RoutedChatResult
from app.storage import JarvisStore, SessionState


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def store(tmp_path):
    result = JarvisStore(tmp_path / "state.db")
    result.initialize()
    return result


def prepare(store, operation):
    workflow = store.create_workflow("Synthetic workflow", "Return a harmless message")
    if operation != "design_plan":
        store.save_workflow_plan(workflow.id, "Approved plan", "fixture", "fixture", finalizing=True)
        store.review_workflow(workflow.id, "approve_plan")
    if operation == "implementation":
        store.save_workflow_test_plan(workflow.id, "Approved test plan", "fixture", "fixture")
        store.review_workflow(workflow.id, "approve_test_plan")
    return store.get_workflow(workflow.id)


def create_job(store, workflow, operation):
    return store.create_workshop_job(workflow.id, operation, json.dumps({"workflow": workflow.model_dump(mode="json")}))


def save(scoped, workflow_id, operation):
    if operation == "design_plan":
        return scoped.save_workflow_plan(workflow_id, "Generated plan", "workshop", "actual-model")
    if operation == "test_plans":
        return scoped.save_workflow_test_plan(workflow_id, "Generated tests", "workshop", "actual-model")
    return scoped.save_workflow_implementation(workflow_id, "Generated code", "workshop", "actual-model")


@pytest.mark.parametrize("operation", ["design_plan", "test_plans", "implementation"])
@pytest.mark.parametrize("change", ["cancel", "revision", "approval", "none"])
def test_generation_commit_is_atomic_and_rejects_changed_inputs(store, operation, change):
    workflow = prepare(store, operation)
    job = create_job(store, workflow, operation)
    assert store.claim_workshop_job(job.id)
    scoped = store.for_workshop_job(job.id)
    if change == "cancel":
        store.cancel_workshop_job(job.id)
    elif change == "revision":
        store.update_workflow(workflow.id, "Revised", "Different request", [], "powershell")
    elif change == "approval":
        store.review_workflow(workflow.id, "reject")
    before = store.get_workflow(workflow.id)
    result = save(scoped, workflow.id, operation)
    if change != "none":
        assert result is None
        assert store.get_workflow(workflow.id) == before
    else:
        job = store.get_workshop_job(job.id)
        assert job.status == "completed"
        assert job.provider == "workshop" and job.model == "actual-model"
        assert json.loads(job.response_json)["id"] == result.id
        assert store.cancel_workshop_job(job.id) is None
        assert result.state in {"design_review", "test_plan_review", "implementation_review"}


def test_duplicate_jobs_and_queued_restart_recovery(store):
    workflow = prepare(store, "design_plan")
    job = create_job(store, workflow, "design_plan")
    assert create_job(store, workflow, "design_plan") is None
    assert store.recover_interrupted_workshop_jobs() == 1
    assert store.get_workshop_job(job.id).status == "failed"
    retried = store.retry_workshop_job(job.id)
    assert retried and store.retry_workshop_job(job.id) is None


class DelayedProvider:
    def __init__(self):
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def chat_for_task_with_tools(self, *args, **kwargs):
        self.started.set()
        await self.release.wait()
        return RoutedChatResult(json.dumps({"plan": "Synthetic completed plan", "questions": []}),
            ProviderRoute("local", "workshop", "actual-model", "http://127.0.0.1:12345/v1/chat/completions"), ProviderFailover())


@pytest.mark.anyio
@pytest.mark.parametrize("change", ["cancel", "revision", "none"])
async def test_background_generation_handles_delayed_results(store, tmp_path, monkeypatch, change):
    monkeypatch.setattr(main, "document_workflow", lambda workflow, *args: workflow)
    workflow = prepare(store, "design_plan")
    provider = DelayedProvider()
    settings = Settings(_env_file=None, JARVIS_ENVIRONMENT="home", JARVIS_WORKFLOW_ARTIFACT_ROOT=tmp_path / "artifacts")
    response = await main._queue_workshop_job(workflow.id, main.WorkshopJobRequest(operation="design_plan"), provider, store, settings)
    task = main._workshop_tasks[response.job.id]
    await asyncio.wait_for(provider.started.wait(), 3)
    if change == "cancel":
        await main.cancel_workshop_job(response.job.id, store)
    elif change == "revision":
        store.update_workflow(workflow.id, "Revised", "New request", [], "powershell")
    provider.release.set()
    await asyncio.gather(task, return_exceptions=True)
    job = store.get_workshop_job(response.job.id)
    assert job.status == {"cancel": "cancelled", "revision": "failed", "none": "completed"}[change]
    saved = store.get_workflow(workflow.id)
    assert saved.plan_text == ("Synthetic completed plan" if change == "none" else "")
    assert saved.state != "approved"


@pytest.mark.anyio
async def test_implementation_cannot_be_queued_before_approvals(store, tmp_path):
    workflow = prepare(store, "design_plan")
    with pytest.raises(HTTPException) as error:
        await main._queue_workshop_job(workflow.id, main.WorkshopJobRequest(operation="implementation"), None, store,
            Settings(_env_file=None, JARVIS_ENVIRONMENT="home"))
    assert error.value.status_code == 409
    assert store.get_workshop_jobs(workflow.id) == []


def test_session_route_is_restored_and_monitoring_is_unique():
    routes = [route for route in main.app.routes if isinstance(route, APIRoute)]
    session = next(route for route in routes if route.path == "/api/session")
    assert session.response_model is SessionState
    assert len([route for route in routes if route.path == "/api/operations/monitoring"]) == 1
