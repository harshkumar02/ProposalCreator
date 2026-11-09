import httpx
import pytest

from app.api import workflows
from tests.conftest import SECRET_HEADER


@pytest.fixture
def n8n_calls(monkeypatch):
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json})
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(workflows.httpx, "post", fake_post)
    return calls


def _start(client, headers, rfp_id):
    return client.post(
        "/api/workflows/runs", json={"workflow": "rfp-analysis", "rfp_id": rfp_id}, headers=headers
    )


def test_start_triggers_n8n_with_secret_and_callback(client, make_user, make_rfp, n8n_calls):
    headers = make_user()
    rfp_id = make_rfp(headers)

    res = _start(client, headers, rfp_id)

    assert res.status_code == 201, res.text
    run = res.json()
    assert run["status"] == "PENDING"
    [call] = n8n_calls
    assert call["url"] == "http://n8n.test/webhook/rfp-analysis"
    assert call["headers"]["X-Workflow-Secret"] == "test-secret"
    assert call["json"]["run_id"] == run["id"]
    assert call["json"]["callback_url"].endswith(f"/internal/workflows/runs/{run['id']}/status")


def test_start_rejects_unknown_workflow_and_foreign_rfp(client, make_user, make_rfp, n8n_calls):
    owner, other = make_user(), make_user()
    rfp_id = make_rfp(owner)

    res = client.post("/api/workflows/runs", json={"workflow": "nope", "rfp_id": rfp_id}, headers=owner)
    assert res.status_code == 400
    assert _start(client, other, rfp_id).status_code == 404
    assert n8n_calls == []


def test_n8n_unreachable_marks_run_failed(client, make_user, make_rfp, monkeypatch):
    def boom(*args, **kwargs):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(workflows.httpx, "post", boom)
    headers = make_user()
    rfp_id = make_rfp(headers)

    assert _start(client, headers, rfp_id).status_code == 502
    [run] = client.get(f"/api/workflows/runs?rfp_id={rfp_id}", headers=headers).json()
    assert run["status"] == "FAILED"
    assert "refused" in run["error"]


def test_internal_routes_require_secret(client, make_user, make_rfp, n8n_calls):
    headers = make_user()
    run_id = _start(client, headers, make_rfp(headers)).json()["id"]
    url = f"/internal/workflows/runs/{run_id}/status"

    assert client.post(url, json={"status": "RUNNING"}).status_code == 401
    assert client.post(url, json={"status": "RUNNING"}, headers={"X-Workflow-Secret": "wrong"}).status_code == 401
    # A user JWT is not enough either.
    assert client.post(url, json={"status": "RUNNING"}, headers=headers).status_code == 401


def test_full_run_lifecycle(client, make_user, make_rfp, n8n_calls):
    headers = make_user()
    rfp_id = make_rfp(headers)
    run_id = _start(client, headers, rfp_id).json()["id"]
    status_url = f"/internal/workflows/runs/{run_id}/status"

    res = client.post(
        status_url,
        json={"status": "RUNNING", "current_step": "extract", "n8n_execution_id": "42"},
        headers=SECRET_HEADER,
    )
    assert res.status_code == 200 and res.json()["status"] == "RUNNING"

    # No API keys in tests, so at most the local regex engine produces rows.
    res = client.post(f"/internal/rfps/{rfp_id}/extract", json={"run_id": run_id}, headers=SECRET_HEADER)
    assert res.status_code == 200, res.text
    assert set(res.json()["engines_used"]) <= {"local_regex"}
    assert isinstance(res.json()["fields_extracted"], int)

    res = client.post(status_url, json={"status": "COMPLETED", "result": res.json()}, headers=SECRET_HEADER)
    assert res.status_code == 200

    run = client.get(f"/api/workflows/runs/{run_id}", headers=headers).json()
    assert run["status"] == "COMPLETED"
    assert run["n8n_execution_id"] == "42"
    assert run["result"]["rfp_id"] == rfp_id
    assert run["finished_at"] is not None

    # Terminal runs can't be reopened or used for more work.
    assert client.post(status_url, json={"status": "RUNNING"}, headers=SECRET_HEADER).status_code == 409
    res = client.post(f"/internal/rfps/{rfp_id}/extract", json={"run_id": run_id}, headers=SECRET_HEADER)
    assert res.status_code == 409


def test_runs_are_scoped_to_owner(client, make_user, make_rfp, n8n_calls):
    owner, other = make_user(), make_user()
    run_id = _start(client, owner, make_rfp(owner)).json()["id"]

    assert client.get(f"/api/workflows/runs/{run_id}", headers=other).status_code == 404
    assert client.get("/api/workflows/runs", headers=other).json() == []


def test_internal_extract_rejects_mismatched_rfp(client, make_user, make_rfp, n8n_calls):
    headers = make_user()
    rfp_a, rfp_b = make_rfp(headers), make_rfp(headers)
    run_id = _start(client, headers, rfp_a).json()["id"]

    res = client.post(f"/internal/rfps/{rfp_b}/extract", json={"run_id": run_id}, headers=SECRET_HEADER)
    assert res.status_code == 400


def test_second_run_on_same_rfp_is_rejected_while_one_is_active(client, make_user, make_rfp, n8n_calls):
    headers = make_user()
    rfp_id = make_rfp(headers)
    first = _start(client, headers, rfp_id).json()["id"]

    res = _start(client, headers, rfp_id)
    assert res.status_code == 409
    assert f"run {first}" in res.json()["detail"]
    assert len(n8n_calls) == 1  # n8n was not triggered for the rejected run

    client.post(f"/internal/workflows/runs/{first}/status", json={"status": "COMPLETED"}, headers=SECRET_HEADER)
    assert _start(client, headers, rfp_id).status_code == 201


def test_database_rejects_two_active_runs_for_one_rfp(make_user, make_rfp, client):
    # Guards the race the API-level check can't: two starts committing together.
    from sqlalchemy.exc import IntegrityError
    from app.core.database import SessionLocal
    from app.models.models import RFP, WorkflowRun

    headers = make_user()
    rfp_id = make_rfp(headers)
    db = SessionLocal()
    try:
        user_id = db.get(RFP, rfp_id).user_id
        db.add(WorkflowRun(user_id=user_id, rfp_id=rfp_id, workflow="rfp-analysis", status="PENDING"))
        db.commit()
        db.add(WorkflowRun(user_id=user_id, rfp_id=rfp_id, workflow="rfp-analysis", status="RUNNING"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        # Finished runs don't count toward the limit.
        db.add(WorkflowRun(user_id=user_id, rfp_id=rfp_id, workflow="rfp-analysis", status="FAILED"))
        db.commit()
    finally:
        db.close()


def _age_run(run_id, minutes):
    from datetime import datetime, timedelta, timezone
    from app.core.database import SessionLocal
    from app.models.models import WorkflowRun

    db = SessionLocal()
    try:
        stale = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        db.query(WorkflowRun).filter(WorkflowRun.id == run_id).update({"updated_at": stale})
        db.commit()
    finally:
        db.close()


def test_run_without_progress_times_out(client, make_user, make_rfp, n8n_calls):
    headers = make_user()
    rfp_id = make_rfp(headers)
    run_id = _start(client, headers, rfp_id).json()["id"]
    client.post(f"/internal/workflows/runs/{run_id}/status", json={"status": "RUNNING", "current_step": "extract"}, headers=SECRET_HEADER)

    _age_run(run_id, minutes=29)
    assert client.get(f"/api/workflows/runs/{run_id}", headers=headers).json()["status"] == "RUNNING"

    _age_run(run_id, minutes=31)
    run = client.get(f"/api/workflows/runs/{run_id}", headers=headers).json()
    assert run["status"] == "FAILED"
    assert "Timed out" in run["error"] and "last step: extract" in run["error"]
    assert run["finished_at"] is not None

    # A late callback from n8n can't resurrect it, and the RFP is free again.
    late = client.post(f"/internal/workflows/runs/{run_id}/status", json={"status": "COMPLETED"}, headers=SECRET_HEADER)
    assert late.status_code == 409
    assert _start(client, headers, rfp_id).status_code == 201


def test_stale_run_does_not_block_a_new_start(client, make_user, make_rfp, n8n_calls):
    headers = make_user()
    rfp_id = make_rfp(headers)
    stuck = _start(client, headers, rfp_id).json()["id"]  # first callback "lost": stays PENDING
    _age_run(stuck, minutes=31)

    assert _start(client, headers, rfp_id).status_code == 201
    assert client.get(f"/api/workflows/runs/{stuck}", headers=headers).json()["status"] == "FAILED"


@pytest.mark.parametrize(
    "raw, expected",
    [
        ('400 - "{\\"detail\\":\\"RFP has no content to extract\\"}"', "RFP has no content to extract (HTTP 400)"),
        ('502 - "Bad Gateway"', "Bad Gateway (HTTP 502)"),
        ("ECONNREFUSED 127.0.0.1:8000", "ECONNREFUSED 127.0.0.1:8000"),
    ],
)
def test_n8n_error_text_is_cleaned(client, make_user, make_rfp, n8n_calls, raw, expected):
    headers = make_user()
    run_id = _start(client, headers, make_rfp(headers)).json()["id"]

    res = client.post(
        f"/internal/workflows/runs/{run_id}/status", json={"status": "FAILED", "error": raw}, headers=SECRET_HEADER
    )
    assert res.json()["error"] == expected


def test_timestamps_are_returned_as_utc(client, make_user, make_rfp, n8n_calls):
    headers = make_user()
    run_id = _start(client, headers, make_rfp(headers)).json()["id"]
    client.post(f"/internal/workflows/runs/{run_id}/status", json={"status": "COMPLETED"}, headers=SECRET_HEADER)

    run = client.get(f"/api/workflows/runs/{run_id}", headers=headers).json()
    for field in ("created_at", "updated_at", "finished_at"):
        assert run[field].endswith(("+00:00", "Z")), (field, run[field])
