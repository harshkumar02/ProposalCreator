from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import json

from app.core.database import get_db
from app.models.models import Proposal, RFP, User, ExtractionResult, ProposalVersion
from app.schemas.schemas import (
    ProposalCreate, ProposalUpdate, ProposalResponse, ProposalDetailResponse,
    ExtractionResultResponse
)
from app.api.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=ProposalResponse)
def create_proposal(
    proposal_data: ProposalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate RFP if provided
    if proposal_data.rfp_id:
        rfp = db.query(RFP).filter(
            RFP.id == proposal_data.rfp_id,
            RFP.user_id == current_user.id
        ).first()
        if not rfp:
            raise HTTPException(status_code=404, detail="RFP not found")

    proposal = Proposal(
        user_id=current_user.id,
        client_name=proposal_data.client_name,
        title=proposal_data.title,
        rfp_id=proposal_data.rfp_id,
        extracted_data=proposal_data.extracted_data
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)

    return ProposalResponse.model_validate(proposal)


@router.get("/", response_model=List[ProposalResponse])
def list_proposals(
    skip: int = 0,
    limit: int = 100,
    status_filter: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Proposal).filter(Proposal.user_id == current_user.id)

    if status_filter:
        query = query.filter(Proposal.status == status_filter)

    proposals = query.order_by(Proposal.updated_at.desc()).offset(skip).limit(limit).all()
    return [ProposalResponse.model_validate(p) for p in proposals]


@router.get("/{proposal_id}", response_model=ProposalDetailResponse)
def get_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    proposal = db.query(Proposal).filter(
        Proposal.id == proposal_id,
        Proposal.user_id == current_user.id
    ).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Get extraction results if RFP is linked
    extraction_results = []
    if proposal.rfp_id:
        results = db.query(ExtractionResult).filter(
            ExtractionResult.rfp_id == proposal.rfp_id
        ).all()
        extraction_results = [ExtractionResultResponse.model_validate(r) for r in results]

    return ProposalDetailResponse(
        **ProposalResponse.model_validate(proposal).model_dump(),
        extraction_results=extraction_results
    )


@router.put("/{proposal_id}", response_model=ProposalResponse)
def update_proposal(
    proposal_id: int,
    update_data: ProposalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    proposal = db.query(Proposal).filter(
        Proposal.id == proposal_id,
        Proposal.user_id == current_user.id
    ).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if update_data.client_name is not None:
        proposal.client_name = update_data.client_name
    if update_data.title is not None:
        proposal.title = update_data.title
    if update_data.status is not None:
        proposal.status = update_data.status
    if update_data.extracted_data is not None:
        proposal.extracted_data = update_data.extracted_data

    db.commit()
    db.refresh(proposal)

    return ProposalResponse.model_validate(proposal)


@router.post("/{proposal_id}/save-version")
def save_proposal_version(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    proposal = db.query(Proposal).filter(
        Proposal.id == proposal_id,
        Proposal.user_id == current_user.id
    ).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Increment version
    proposal.version += 1

    # Save current state as version
    version = ProposalVersion(
        proposal_id=proposal_id,
        version=proposal.version,
        content=proposal.extracted_data or "{}"
    )
    db.add(version)
    db.commit()

    return {"message": "Version saved", "version": proposal.version}


@router.get("/{proposal_id}/versions")
def get_proposal_versions(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    proposal = db.query(Proposal).filter(
        Proposal.id == proposal_id,
        Proposal.user_id == current_user.id
    ).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    versions = db.query(ProposalVersion).filter(
        ProposalVersion.proposal_id == proposal_id
    ).order_by(ProposalVersion.version.desc()).all()

    return [
        {
            "version": v.version,
            "created_at": v.created_at,
            "content": v.content
        }
        for v in versions
    ]


@router.delete("/{proposal_id}")
def delete_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    proposal = db.query(Proposal).filter(
        Proposal.id == proposal_id,
        Proposal.user_id == current_user.id
    ).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    db.query(ProposalVersion).filter(ProposalVersion.proposal_id == proposal_id).delete()
    db.delete(proposal)
    db.commit()

    return {"message": "Proposal deleted successfully"}


@router.post("/{proposal_id}/duplicate")
def duplicate_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    original = db.query(Proposal).filter(
        Proposal.id == proposal_id,
        Proposal.user_id == current_user.id
    ).first()
    if not original:
        raise HTTPException(status_code=404, detail="Proposal not found")

    new_proposal = Proposal(
        user_id=current_user.id,
        client_name=f"{original.client_name} (Copy)",
        title=original.title,
        rfp_id=original.rfp_id,
        extracted_data=original.extracted_data,
        status="draft"
    )
    db.add(new_proposal)
    db.commit()
    db.refresh(new_proposal)

    return ProposalResponse.model_validate(new_proposal)