from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.models import RFP, User, ExtractionResult
from app.schemas.schemas import ExtractionResultResponse, ExtractionResultsResponse
from app.api.auth import get_current_user
from app.services.claude_extractor import extract_with_claude, summarize_with_claude
from app.services.openai_extractor import extract_with_openai, extract_structured_data

router = APIRouter()


@router.post("/{rfp_id}/extract", response_model=ExtractionResultsResponse)
def extract_rfp(
    rfp_id: int,
    engines: List[str] = ["claude"],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rfp = db.query(RFP).filter(RFP.id == rfp_id, RFP.user_id == current_user.id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    if not rfp.content:
        raise HTTPException(status_code=400, detail="RFP has no content to extract")

    all_results = []
    used_engines = []

    # Clear previous extraction results
    db.query(ExtractionResult).filter(ExtractionResult.rfp_id == rfp_id).delete()

    # Claude extraction
    if "claude" in engines:
        results = extract_with_claude(rfp.content)
        if results:
            used_engines.append("claude")
            for r in results:
                extraction = ExtractionResult(
                    rfp_id=rfp_id,
                    engine="claude",
                    field_name=r.get("field_name", "unknown"),
                    value=r.get("value"),
                    confidence=r.get("confidence", 0.5)
                )
                db.add(extraction)
                all_results.append(r)

    # OpenAI extraction
    if "openai" in engines:
        results = extract_with_openai(rfp.content)
        if results:
            used_engines.append("openai")
            for r in results:
                extraction = ExtractionResult(
                    rfp_id=rfp_id,
                    engine="openai",
                    field_name=r.get("field_name", "unknown"),
                    value=r.get("value"),
                    confidence=r.get("confidence", 0.5)
                )
                db.add(extraction)
                all_results.append(r)

    # Local regex extraction (always available)
    results = extract_structured_data(rfp.content)
    if results:
        used_engines.append("local_regex")
        for r in results:
            extraction = ExtractionResult(
                rfp_id=rfp_id,
                engine="local_regex",
                field_name=r.get("field_name", "unknown"),
                value=r.get("value"),
                confidence=r.get("confidence", 0.5)
            )
            db.add(extraction)

    db.commit()

    # Fetch all results
    db_results = db.query(ExtractionResult).filter(ExtractionResult.rfp_id == rfp_id).all()

    return ExtractionResultsResponse(
        results=[ExtractionResultResponse.model_validate(r) for r in db_results],
        engines_used=used_engines
    )


@router.get("/{rfp_id}/summary")
def get_rfp_summary(
    rfp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rfp = db.query(RFP).filter(RFP.id == rfp_id, RFP.user_id == current_user.id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    summary = summarize_with_claude(rfp.content or "")
    return {"summary": summary}