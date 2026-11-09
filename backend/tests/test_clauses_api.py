import httpx
import pytest

from app.api import workflows
from app.services import clause_extractor as ce
from app.services.llm import LLMError
from tests.conftest import SECRET_HEADER


@pytest.fixture(autouse=True)
def no_n8n(monkeypatch):
    monkeypatch.setattr(
        workflows.httpx, "post", lambda url, **kw: httpx.Response(200, request=httpx.Request("POST", url))
    )


def _clause(category, requirement, page, **extra):
    data = {
        "category": category, "criterion_type": None, "requirement": requirement, "source_text": requirement,
        "mandatory": True, "threshold_value": None, "threshold_unit": None, "operator": None, "period": None,
        "min_count": None, "max_marks": None, "scoring_rule": None, "evidence_required": [], "page_number": page,
        "section_ref": None, "confidence": 0.9,
    }
    data.update(extra)
    return data


def _fake_output():
    clauses = [
        _clause("PQ", "Average turnover >= INR 25 crore", 3, criterion_type="turnover", threshold_value=250000000,
                threshold_unit="INR", operator=">="),
        _clause("PQ", "CERT-In empanelment", 3, criterion_type="empanelment", mandatory=False),
        _clause("TQ", "SOC contracts", 5, mandatory=None, max_marks=10, scoring_rule="2.5 marks per contract"),
    ]
    clauses[0]["amended_by"] = "Corrigendum-1"
    clauses[0]["original"] = {"threshold_value": 300000000}
    ce.assign_codes(clauses)
    return ce.ExtractionOutput(
        clauses=clauses, tender_details={"tender_id": "KVB/2026/07", "emd_amount_inr": 1000000},
        warnings=["Clause 7 is ambiguous"], chunks=2, amendments_applied=1,
    )


def _start_run(client, headers, rfp_id):
    res = client.post("/api/workflows/runs", json={"workflow": "rfp-analysis", "rfp_id": rfp_id}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()["id"]


@pytest.fixture
def extracted(client, make_user, make_rfp, monkeypatch):
    """An RFP whose clauses were produced by the internal workflow step."""
    seen = {}

    def fake_extract(content, provider=None, on_progress=None):
        seen["provider"] = provider
        on_progress("Extracting clauses: 1/2 parts")
        return _fake_output()

    monkeypatch.setattr(workflows, "extract_clauses", fake_extract)
    headers = make_user()
    rfp_id = make_rfp(headers)
    run_id = _start_run(client, headers, rfp_id)
    res = client.post(f"/internal/rfps/{rfp_id}/extract-clauses", json={"run_id": run_id, "provider": "gemini"},
                      headers=SECRET_HEADER)
    assert res.status_code == 200, res.text
    return {"headers": headers, "rfp_id": rfp_id, "run_id": run_id, "step": res.json(), "seen": seen}


def test_internal_step_saves_clauses_and_reports_summary(client, extracted):
    step = extracted["step"]
    assert step["clauses"] == 3
    assert step["by_category"] == {"PQ": 2, "TQ": 1}
    assert step["mandatory_pq"] == 1
    assert step["amendments_applied"] == 1
    assert extracted["seen"]["provider"] == "gemini"

    run = client.get(f"/api/workflows/runs/{extracted['run_id']}", headers=extracted["headers"]).json()
    assert run["current_step"] == "Extracting clauses: 1/2 parts"


def test_list_clauses_returns_typed_rows_tender_details_and_summary(client, extracted):
    res = client.get(f"/api/rfps/{extracted['rfp_id']}/clauses", headers=extracted["headers"]).json()

    assert [c["clause_code"] for c in res["clauses"]] == ["PQ-001", "PQ-002", "TQ-001"]
    turnover = res["clauses"][0]
    assert turnover["threshold_value"] == 250000000 and turnover["amended_by"] == "Corrigendum-1"
    assert turnover["review_status"] == "PENDING" and turnover["edited"] is False
    assert res["tender_details"]["tender_id"] == "KVB/2026/07"
    assert res["summary"]["by_category"]["PQ"] == 2 and res["summary"]["tq_total_marks"] == 10

    only_tq = client.get(f"/api/rfps/{extracted['rfp_id']}/clauses?category=tq", headers=extracted["headers"]).json()
    assert [c["clause_code"] for c in only_tq["clauses"]] == ["TQ-001"]
    assert only_tq["summary"]["total"] == 3  # summary always covers the whole RFP


def test_review_edit_marks_clause_edited_and_keeps_ai_original(client, extracted):
    from app.core.database import SessionLocal
    from app.models.models import RFPClause

    base = f"/api/rfps/{extracted['rfp_id']}/clauses"
    clause = client.get(base, headers=extracted["headers"]).json()["clauses"][0]

    res = client.put(f"{base}/{clause['id']}", json={"threshold_value": 200000000, "review_status": "VERIFIED",
                                                       "reviewer_notes": "Checked against corrigendum"},
                     headers=extracted["headers"])
    assert res.status_code == 200
    body = res.json()
    assert body["threshold_value"] == 200000000 and body["edited"] is True
    assert body["review_status"] == "VERIFIED" and body["reviewed_at"].endswith(("+00:00", "Z"))

    db = SessionLocal()
    try:
        row = db.get(RFPClause, clause["id"])
        assert row.ai_data["threshold_value"] == 250000000
        assert row.ai_data["before_corrigendum"] == {"threshold_value": 300000000}
    finally:
        db.close()

    back = client.put(f"{base}/{clause['id']}", json={"review_status": "PENDING"}, headers=extracted["headers"]).json()
    assert back["reviewed_at"] is None


@pytest.mark.parametrize("payload", [{"category": "BOGUS"}, {"operator": "~"}, {"review_status": "DONE"}, {"requirement": " "}])
def test_review_rejects_invalid_values(client, extracted, payload):
    base = f"/api/rfps/{extracted['rfp_id']}/clauses"
    clause_id = client.get(base, headers=extracted["headers"]).json()["clauses"][0]["id"]
    assert client.put(f"{base}/{clause_id}", json=payload, headers=extracted["headers"]).status_code == 400


def test_manual_clause_gets_next_code_and_is_verified(client, extracted):
    res = client.post(f"/api/rfps/{extracted['rfp_id']}/clauses",
                      json={"category": "pq", "requirement": "Valid GST registration", "mandatory": True},
                      headers=extracted["headers"])
    assert res.status_code == 201
    body = res.json()
    assert body["clause_code"] == "PQ-003"
    assert body["provider"] == "manual" and body["review_status"] == "VERIFIED" and body["edited"] is False


def test_clauses_are_scoped_to_owner(client, extracted, make_user):
    other = make_user()
    base = f"/api/rfps/{extracted['rfp_id']}/clauses"
    clause_id = client.get(base, headers=extracted["headers"]).json()["clauses"][0]["id"]

    assert client.get(base, headers=other).status_code == 404
    assert client.put(f"{base}/{clause_id}", json={"review_status": "VERIFIED"}, headers=other).status_code == 404
    assert client.post(base, json={"category": "PQ", "requirement": "x"}, headers=other).status_code == 404


def test_reextraction_replaces_previous_clauses(client, extracted, monkeypatch):
    run_id = extracted["run_id"]
    client.post(f"/internal/workflows/runs/{run_id}/status", json={"status": "COMPLETED"}, headers=SECRET_HEADER)
    output = _fake_output()
    output.clauses = output.clauses[:1]
    monkeypatch.setattr(workflows, "extract_clauses", lambda content, provider=None, on_progress=None: output)

    new_run = _start_run(client, extracted["headers"], extracted["rfp_id"])
    client.post(f"/internal/rfps/{extracted['rfp_id']}/extract-clauses", json={"run_id": new_run}, headers=SECRET_HEADER)

    clauses = client.get(f"/api/rfps/{extracted['rfp_id']}/clauses", headers=extracted["headers"]).json()["clauses"]
    assert len(clauses) == 1


def test_model_failure_returns_502_with_reason(client, make_user, make_rfp, monkeypatch):
    def boom(content, provider=None, on_progress=None):
        raise LLMError("Part 2/3 failed: Gemini API error 429: quota")

    monkeypatch.setattr(workflows, "extract_clauses", boom)
    headers = make_user()
    rfp_id = make_rfp(headers)
    run_id = _start_run(client, headers, rfp_id)

    res = client.post(f"/internal/rfps/{rfp_id}/extract-clauses", json={"run_id": run_id, "provider": "gemini"},
                      headers=SECRET_HEADER)
    assert res.status_code == 502
    assert "Gemini API error 429" in res.json()["detail"]


def test_unknown_provider_is_rejected(client, make_user, make_rfp):
    headers = make_user()
    rfp_id = make_rfp(headers)
    run_id = _start_run(client, headers, rfp_id)
    res = client.post(f"/internal/rfps/{rfp_id}/extract-clauses", json={"run_id": run_id, "provider": "gpt"},
                      headers=SECRET_HEADER)
    assert res.status_code == 400
