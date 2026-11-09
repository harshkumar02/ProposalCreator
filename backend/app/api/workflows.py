"""n8n workflow orchestration.

The frontend never talks to n8n. It asks this API to start a workflow; the
backend records a ``WorkflowRun``, triggers the matching n8n webhook, and n8n
reports progress back through ``/internal/workflows/runs/{id}/status``. Work
that needs the database (extraction, and later PQ/TQ checks) stays in FastAPI
as ``/internal`` endpoints that n8n calls — n8n only sequences them.

``/internal`` routes authenticate with the ``X-Workflow-Secret`` header
(``N8N_SHARED_SECRET``), not a user JWT, and are disabled when the secret is
unset.
"""
import hmac
import json
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.api.clauses import save_extraction, summarise
from app.api.extraction import run_extraction
from app.core.config import settings
from app.core.database import get_db
from app.models.models import RFP, Proposal, User, WorkflowRun
from app.services import llm
from app.services.clause_extractor import extract_clauses
from app.schemas.schemas import (
    InternalClauseExtractRequest,
    InternalExtractRequest,
    WorkflowRunCreate,
    WorkflowRunResponse,
    WorkflowStatusUpdate,
)

router = APIRouter()
internal_router = APIRouter()

# Workflows the API may start, keyed by name (also the n8n webhook path), with
# the resource each one must be attached to.
WORKFLOWS = {
    "rfp-analysis": {"requires": "rfp"},
}

ACTIVE_STATUSES = {"PENDING", "RUNNING"}
TERMINAL_STATUSES = {"COMPLETED", "FAILED"}
REPORTABLE_STATUSES = {"RUNNING"} | TERMINAL_STATUSES
MAX_ERROR_LENGTH = 2000

# n8n's HTTP Request node reports a failed call as `<status> - <body as JSON string>`,
# e.g. `400 - "{\"detail\":\"RFP has no content to extract\"}"`.
_N8N_HTTP_ERROR = re.compile(r"^(\d{3}) - (.+)$", re.DOTALL)


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)  # SQLite drops tzinfo; values are UTC
    return value


def _expire_stale_runs(db: Session, runs: List[WorkflowRun]) -> None:
    """Mark active runs FAILED once they've gone WORKFLOW_RUN_TIMEOUT_MINUTES without a callback.

    Checked lazily whenever runs are read or a new run is started, so a run
    whose callbacks were lost can't stay "in progress" forever or block its RFP.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.WORKFLOW_RUN_TIMEOUT_MINUTES)
    expired = False
    for run in runs:
        last_seen = _as_utc(run.updated_at or run.created_at)
        if run.status in ACTIVE_STATUSES and last_seen is not None and last_seen < cutoff:
            run.status = "FAILED"
            run.error = (
                f"Timed out: no progress from n8n for {settings.WORKFLOW_RUN_TIMEOUT_MINUTES} minutes"
                + (f" (last step: {run.current_step})" if run.current_step else "")
            )
            run.finished_at = datetime.now(timezone.utc)
            expired = True
    if expired:
        db.commit()


def _clean_error(error: str) -> str:
    """Turn n8n's raw HTTP error string into the backend's own `detail` message."""
    error = error.strip()
    match = _N8N_HTTP_ERROR.match(error)
    if match:
        code, body = match.groups()
        detail = body
        for _ in range(2):  # body is a JSON string that itself contains JSON
            try:
                detail = json.loads(detail)
            except (TypeError, ValueError):
                break
            if not isinstance(detail, str):
                break
        if isinstance(detail, dict) and isinstance(detail.get("detail"), str):
            error = f"{detail['detail']} (HTTP {code})"
        elif isinstance(detail, str):
            error = f"{detail} (HTTP {code})"
    return error[:MAX_ERROR_LENGTH]


def _trigger_n8n(run: WorkflowRun) -> None:
    """POST the run to n8n's webhook. Raises httpx.HTTPError on failure."""
    base = settings.BACKEND_INTERNAL_URL.rstrip("/")
    res = httpx.post(
        f"{settings.N8N_WEBHOOK_BASE_URL.rstrip('/')}/{run.workflow}",
        headers={"X-Workflow-Secret": settings.N8N_SHARED_SECRET},
        json={
            "run_id": run.id,
            "workflow": run.workflow,
            "rfp_id": run.rfp_id,
            "proposal_id": run.proposal_id,
            "params": run.params or {},
            "api_base_url": base,
            "callback_url": f"{base}/internal/workflows/runs/{run.id}/status",
        },
        timeout=10,
    )
    res.raise_for_status()


@router.post("/runs", response_model=WorkflowRunResponse, status_code=status.HTTP_201_CREATED)
def start_workflow(
    data: WorkflowRunCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    spec = WORKFLOWS.get(data.workflow)
    if spec is None:
        raise HTTPException(status_code=400, detail=f"Unknown workflow '{data.workflow}'")
    if not settings.N8N_SHARED_SECRET:
        raise HTTPException(status_code=503, detail="Workflow engine is not configured (N8N_SHARED_SECRET unset)")

    if data.rfp_id is not None:
        if not db.query(RFP).filter(RFP.id == data.rfp_id, RFP.user_id == current_user.id).first():
            raise HTTPException(status_code=404, detail="RFP not found")
    if data.proposal_id is not None:
        if not db.query(Proposal).filter(Proposal.id == data.proposal_id, Proposal.user_id == current_user.id).first():
            raise HTTPException(status_code=404, detail="Proposal not found")
    if spec["requires"] == "rfp" and data.rfp_id is None:
        raise HTTPException(status_code=400, detail=f"Workflow '{data.workflow}' requires rfp_id")

    if data.rfp_id is not None:
        active = db.query(WorkflowRun).filter(
            WorkflowRun.rfp_id == data.rfp_id, WorkflowRun.status.in_(ACTIVE_STATUSES)
        ).all()
        _expire_stale_runs(db, active)
        busy = next((r for r in active if r.status in ACTIVE_STATUSES), None)
        if busy:
            raise HTTPException(
                status_code=409,
                detail=f"Workflow run {busy.id} ({busy.workflow}) is still {busy.status} for this RFP",
            )

    run = WorkflowRun(
        user_id=current_user.id,
        workflow=data.workflow,
        rfp_id=data.rfp_id,
        proposal_id=data.proposal_id,
        params=data.params,
        status="PENDING",
    )
    db.add(run)
    try:
        db.commit()
    except IntegrityError:
        # Lost a race with a concurrent start; the partial unique index caught it.
        db.rollback()
        raise HTTPException(status_code=409, detail="Another workflow run is already active for this RFP")
    db.refresh(run)

    try:
        _trigger_n8n(run)
    except httpx.HTTPError as e:
        run.status = "FAILED"
        run.error = f"Could not start n8n workflow: {e}"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=502, detail=run.error)

    return WorkflowRunResponse.model_validate(run)


@router.get("/runs", response_model=List[WorkflowRunResponse])
def list_workflow_runs(
    rfp_id: Optional[int] = None,
    proposal_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(WorkflowRun).filter(WorkflowRun.user_id == current_user.id)
    if rfp_id is not None:
        query = query.filter(WorkflowRun.rfp_id == rfp_id)
    if proposal_id is not None:
        query = query.filter(WorkflowRun.proposal_id == proposal_id)
    runs = query.order_by(WorkflowRun.id.desc()).limit(50).all()
    _expire_stale_runs(db, runs)
    return [WorkflowRunResponse.model_validate(r) for r in runs]


@router.get("/runs/{run_id}", response_model=WorkflowRunResponse)
def get_workflow_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id, WorkflowRun.user_id == current_user.id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    _expire_stale_runs(db, [run])
    return WorkflowRunResponse.model_validate(run)


# --- Internal API (called by n8n) -------------------------------------------

def require_workflow_secret(x_workflow_secret: str = Header(default="")) -> None:
    if not settings.N8N_SHARED_SECRET:
        raise HTTPException(status_code=503, detail="Internal API disabled (N8N_SHARED_SECRET unset)")
    if not hmac.compare_digest(x_workflow_secret.encode(), settings.N8N_SHARED_SECRET.encode()):
        raise HTTPException(status_code=401, detail="Invalid workflow secret")


def _get_active_run(db: Session, run_id: int) -> WorkflowRun:
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    _expire_stale_runs(db, [run])
    if run.status in TERMINAL_STATUSES:
        raise HTTPException(status_code=409, detail=f"Workflow run already {run.status}")
    return run


@internal_router.post(
    "/workflows/runs/{run_id}/status",
    response_model=WorkflowRunResponse,
    dependencies=[Depends(require_workflow_secret)],
)
def report_workflow_status(run_id: int, update: WorkflowStatusUpdate, db: Session = Depends(get_db)):
    new_status = update.status.upper()
    if new_status not in REPORTABLE_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(REPORTABLE_STATUSES)}")

    run = _get_active_run(db, run_id)
    run.status = new_status
    if update.current_step is not None:
        run.current_step = update.current_step
    if update.n8n_execution_id is not None:
        run.n8n_execution_id = update.n8n_execution_id
    if update.result is not None:
        run.result = update.result
    if update.error is not None:
        run.error = _clean_error(update.error)
    if new_status in TERMINAL_STATUSES:
        run.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    return WorkflowRunResponse.model_validate(run)


@internal_router.post("/rfps/{rfp_id}/extract", dependencies=[Depends(require_workflow_secret)])
def internal_extract_rfp(rfp_id: int, data: InternalExtractRequest, db: Session = Depends(get_db)):
    run = _get_active_run(db, data.run_id)
    if run.rfp_id != rfp_id:
        raise HTTPException(status_code=400, detail="Workflow run is not attached to this RFP")

    # Scope to the run's owner, preserving the per-user filtering every route applies.
    rfp = db.query(RFP).filter(RFP.id == rfp_id, RFP.user_id == run.user_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    if not rfp.content:
        raise HTTPException(status_code=400, detail="RFP has no content to extract")

    extraction = run_extraction(db, rfp, data.engines)
    return {
        "rfp_id": rfp_id,
        "engines_used": extraction.engines_used,
        "fields_extracted": len(extraction.results),
    }


@internal_router.post("/rfps/{rfp_id}/extract-clauses", dependencies=[Depends(require_workflow_secret)])
def internal_extract_clauses(rfp_id: int, data: InternalClauseExtractRequest, db: Session = Depends(get_db)):
    """WF-02 step: replace the RFP's clauses with a fresh clause-level extraction.

    Updates ``run.current_step`` as chunks finish, which also keeps the run
    from timing out during long extractions. Model failures return 502 so the
    n8n error branch marks the run FAILED.
    """
    run = _get_active_run(db, data.run_id)
    if run.rfp_id != rfp_id:
        raise HTTPException(status_code=400, detail="Workflow run is not attached to this RFP")
    rfp = db.query(RFP).filter(RFP.id == rfp_id, RFP.user_id == run.user_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    if not (rfp.content or "").strip():
        raise HTTPException(status_code=400, detail="RFP has no content to extract")

    provider = (data.provider or settings.LLM_PROVIDER).lower()
    if provider not in llm.SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"provider must be one of {list(llm.SUPPORTED_PROVIDERS)}")

    def on_progress(message: str) -> None:
        run.current_step = message
        db.commit()

    try:
        output = extract_clauses(rfp.content, provider=provider, on_progress=on_progress)
    except llm.LLMError as e:
        raise HTTPException(status_code=502, detail=f"Clause extraction failed ({provider}): {e}")

    rows = save_extraction(db, rfp, output, run_id=run.id, provider=provider)
    summary = summarise(rows)
    return {
        "rfp_id": rfp_id,
        "provider": provider,
        "chunks": output.chunks,
        "clauses": summary["total"],
        "by_category": {k: v for k, v in summary["by_category"].items() if v},
        "mandatory_pq": summary["mandatory_pq"],
        "amendments_applied": output.amendments_applied,
        "warnings": output.warnings[:20],
    }
