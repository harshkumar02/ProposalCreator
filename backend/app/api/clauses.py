"""Review API for extracted tender clauses (``/api/rfps/{rfp_id}/clauses``).

Clauses are produced by the ``rfp-analysis`` workflow (see api/workflows.py).
Reviewers verify, reject, correct or add clauses here; the corrected typed
columns are what qualification (Phase 3) will evaluate, while ``ai_data``
keeps the model's original output for audit.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.models import RFP, RFPClause, User
from app.schemas.schemas import (
    RFPClauseCreate,
    RFPClauseListResponse,
    RFPClauseResponse,
    RFPClauseUpdate,
)
from app.services.clause_extractor import CATEGORIES, CODE_PREFIX, OPERATORS, ExtractionOutput

router = APIRouter()

REVIEW_STATUSES = ("PENDING", "VERIFIED", "REJECTED")
# Typed columns a reviewer may correct; compared against ai_data to flag edits.
EDITABLE_FIELDS = (
    "category", "criterion_type", "requirement", "mandatory", "threshold_value", "threshold_unit",
    "operator", "period", "min_count", "max_marks", "scoring_rule", "evidence_required",
    "page_number", "section_ref",
)


def _to_response(clause: RFPClause) -> RFPClauseResponse:
    response = RFPClauseResponse.model_validate(clause)
    ai = clause.ai_data or {}
    response.edited = clause.provider != "manual" and any(
        field in ai and getattr(clause, field) != ai[field] for field in EDITABLE_FIELDS
    )
    if response.reviewed_at is not None and response.reviewed_at.tzinfo is None:
        response.reviewed_at = response.reviewed_at.replace(tzinfo=timezone.utc)
    return response


def _get_rfp(db: Session, rfp_id: int, user: User) -> RFP:
    rfp = db.query(RFP).filter(RFP.id == rfp_id, RFP.user_id == user.id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    return rfp


def _validate(data: Dict[str, Any]) -> None:
    if "category" in data and data["category"] not in CATEGORIES:
        raise HTTPException(status_code=400, detail=f"category must be one of {list(CATEGORIES)}")
    if data.get("operator") is not None and data["operator"] not in OPERATORS:
        raise HTTPException(status_code=400, detail=f"operator must be one of {list(OPERATORS)}")
    if "review_status" in data and data["review_status"] not in REVIEW_STATUSES:
        raise HTTPException(status_code=400, detail=f"review_status must be one of {list(REVIEW_STATUSES)}")
    if "requirement" in data and not (data["requirement"] or "").strip():
        raise HTTPException(status_code=400, detail="requirement cannot be empty")


def summarise(clauses: List[RFPClause]) -> Dict[str, Any]:
    by_category = {c: 0 for c in CATEGORIES}
    by_status = {s: 0 for s in REVIEW_STATUSES}
    for clause in clauses:
        by_category[clause.category] = by_category.get(clause.category, 0) + 1
        by_status[clause.review_status] = by_status.get(clause.review_status, 0) + 1
    return {
        "total": len(clauses),
        "by_category": by_category,
        "by_review_status": by_status,
        "mandatory_pq": sum(1 for c in clauses if c.category == "PQ" and c.mandatory),
        "tq_total_marks": sum(c.max_marks or 0 for c in clauses if c.category == "TQ" and c.review_status != "REJECTED"),
    }


def save_extraction(db: Session, rfp: RFP, output: ExtractionOutput, *, run_id: Optional[int], provider: str) -> List[RFPClause]:
    """Replace the RFP's clauses and tender details with a fresh extraction."""
    db.query(RFPClause).filter(RFPClause.rfp_id == rfp.id).delete()
    rows = []
    for data in output.clauses:
        original = data.get("original")
        ai_data = {k: v for k, v in data.items() if k not in ("original", "clause_code", "amended_by")}
        if original:
            ai_data["before_corrigendum"] = original
        row = RFPClause(
            rfp_id=rfp.id,
            run_id=run_id,
            clause_code=data["clause_code"],
            amended_by=data.get("amended_by"),
            provider=provider,
            ai_data=ai_data,
            review_status="PENDING",
            **{k: data.get(k) for k in EDITABLE_FIELDS + ("source_text", "confidence")},
        )
        db.add(row)
        rows.append(row)
    rfp.tender_details = output.tender_details
    db.commit()
    return rows


@router.get("/{rfp_id}/clauses", response_model=RFPClauseListResponse)
def list_clauses(
    rfp_id: int,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rfp = _get_rfp(db, rfp_id, current_user)
    clauses = db.query(RFPClause).filter(RFPClause.rfp_id == rfp.id).order_by(RFPClause.id).all()
    summary = summarise(clauses)
    if category:
        clauses = [c for c in clauses if c.category == category.upper()]
    return RFPClauseListResponse(
        clauses=[_to_response(c) for c in clauses],
        tender_details=rfp.tender_details,
        summary=summary,
    )


@router.put("/{rfp_id}/clauses/{clause_id}", response_model=RFPClauseResponse)
def update_clause(
    rfp_id: int,
    clause_id: int,
    update: RFPClauseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rfp = _get_rfp(db, rfp_id, current_user)
    clause = db.query(RFPClause).filter(RFPClause.id == clause_id, RFPClause.rfp_id == rfp.id).first()
    if not clause:
        raise HTTPException(status_code=404, detail="Clause not found")

    data = update.model_dump(exclude_unset=True)
    if "category" in data and data["category"]:
        data["category"] = data["category"].upper()
    _validate(data)
    for key, value in data.items():
        setattr(clause, key, value)
    if "review_status" in data:
        clause.reviewed_at = None if data["review_status"] == "PENDING" else datetime.now(timezone.utc)
    db.commit()
    db.refresh(clause)
    return _to_response(clause)


@router.post("/{rfp_id}/clauses", response_model=RFPClauseResponse, status_code=status.HTTP_201_CREATED)
def create_clause(
    rfp_id: int,
    data: RFPClauseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a requirement the extractor missed. Manual clauses count as verified."""
    rfp = _get_rfp(db, rfp_id, current_user)
    values = data.model_dump(exclude_unset=True)
    values["category"] = values["category"].upper()
    _validate(values)

    prefix = CODE_PREFIX[values["category"]]
    existing = db.query(RFPClause.clause_code).filter(
        RFPClause.rfp_id == rfp.id, RFPClause.clause_code.like(f"{prefix}-%")
    ).all()
    next_number = max((int(code.split("-")[1]) for (code,) in existing if code.split("-")[1].isdigit()), default=0) + 1

    clause = RFPClause(
        rfp_id=rfp.id,
        clause_code=f"{prefix}-{next_number:03d}",
        provider="manual",
        review_status=values.pop("review_status", None) or "VERIFIED",
        reviewed_at=datetime.now(timezone.utc),
        **values,
    )
    db.add(clause)
    db.commit()
    db.refresh(clause)
    return _to_response(clause)
