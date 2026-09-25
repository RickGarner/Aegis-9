import json

import pytest

from app.storage import JarvisStore


def make_store(tmp_path):
    store = JarvisStore(tmp_path / "jobs.db")
    store.initialize()
    return store


def make_workflow(store: JarvisStore) -> int:
    return store.create_workflow("Workshop test", "Generate a script").id


def test_workshop_job_lifecycle_and_payload(tmp_path) -> None:
    store = make_store(tmp_path)
    workflow_id = make_workflow(store)

    job = store.create_workshop_job(workflow_id, "implementation", json.dumps({"revision": 1}))
    assert job is not None
    assert job.status == "queued"
    assert job.revision == 1

    claimed = store.claim_workshop_job(job.id)
    assert claimed is not None
    assert claimed.status == "running"

    completed = store.complete_workshop_job(job.id, "completed", '{"artifact":"returned"}')
    assert completed is not None
    assert completed.status == "completed"
    assert json.loads(completed.response_json)["artifact"] == "returned"


def test_workshop_job_rejects_stale_revision(tmp_path) -> None:
    store = make_store(tmp_path)
    workflow_id = make_workflow(store)
    job = store.create_workshop_job(workflow_id, "design_plan", "{}")
    assert job is not None

    updated = store.update_workflow(workflow_id, "Revised", "New request", [], "powershell")
    assert updated is not None
    assert updated.revision == 2
    assert store.claim_workshop_job(job.id) is None


def test_workshop_job_terminal_status_validation_and_recovery(tmp_path) -> None:
    store = make_store(tmp_path)
    workflow_id = make_workflow(store)
    job = store.create_workshop_job(workflow_id, "test_plans", "{}")
    assert job is not None
    assert store.claim_workshop_job(job.id) is not None

    with pytest.raises(ValueError):
        store.complete_workshop_job(job.id, "running")

    assert store.recover_interrupted_workshop_jobs() == 1
    recovered = store.get_workshop_job(job.id)
    assert recovered is not None
    assert recovered.status == "failed"
    assert "restarted" in recovered.error


def test_workshop_job_can_be_cancelled(tmp_path) -> None:
    store = make_store(tmp_path)
    workflow_id = make_workflow(store)
    job = store.create_workshop_job(workflow_id, "design_plan", "{}")
    assert job is not None
    cancelled = store.cancel_workshop_job(job.id)
    assert cancelled is not None
    assert cancelled.status == "cancelled"
    assert store.cancel_workshop_job(job.id) is None


def test_workshop_job_request_retains_transfer_context(tmp_path) -> None:
    store = make_store(tmp_path)
    workflow_id = make_workflow(store)
    request = json.dumps({"workflow_id": workflow_id, "revision": 1, "attachments": [{"name": "input.txt"}]})
    job = store.create_workshop_job(workflow_id, "implementation", request)
    assert job is not None
    payload = json.loads(job.request_json)
    assert payload["revision"] == job.revision
    assert payload["attachments"][0]["name"] == "input.txt"




def test_workshop_job_list_is_scoped_to_workflow(tmp_path) -> None:
    store = make_store(tmp_path)
    first = make_workflow(store)
    second = make_workflow(store)
    store.create_workshop_job(first, "design_plan", "{}")
    store.create_workshop_job(second, "implementation", "{}")

    jobs = store.get_workshop_jobs(first)
    assert len(jobs) == 1
    assert jobs[0].workflow_id == first
    assert store.get_workshop_job(jobs[0].id) is not None

  