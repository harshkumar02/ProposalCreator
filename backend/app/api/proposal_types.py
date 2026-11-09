from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.core.database import get_db
from app.models.models import ProposalType, ProposalBlock, User
from app.schemas.schemas import (
    ProposalTypeCreate, ProposalTypeUpdate, ProposalTypeResponse,
    ProposalTypeDetection
)
from app.api.auth import get_current_user
from app.services.proposal_type_detector import detect_proposal_type, detect_industry_tags, extract_additional_metadata


router = APIRouter()


@router.get("/", response_model=List[ProposalTypeResponse])
def list_proposal_types(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all proposal types."""
    query = db.query(ProposalType)
    if active_only:
        query = query.filter(ProposalType.is_active == True)
    query = query.order_by(ProposalType.sort_order, ProposalType.name)
    return query.all()


@router.post("/", response_model=ProposalTypeResponse)
def create_proposal_type(
    data: ProposalTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new proposal type."""
    existing = db.query(ProposalType).filter(ProposalType.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Proposal type already exists")

    proposal_type = ProposalType(
        name=data.name,
        display_name=data.display_name or data.name.replace("_", " ").title(),
        description=data.description,
        keywords=data.keywords,
        industry_tags=data.industry_tags,
        sort_order=data.sort_order
    )
    db.add(proposal_type)
    db.commit()
    db.refresh(proposal_type)
    return proposal_type


@router.get("/{type_id}", response_model=ProposalTypeResponse)
def get_proposal_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific proposal type."""
    proposal_type = db.query(ProposalType).filter(ProposalType.id == type_id).first()
    if not proposal_type:
        raise HTTPException(status_code=404, detail="Proposal type not found")
    return proposal_type


@router.put("/{type_id}", response_model=ProposalTypeResponse)
def update_proposal_type(
    type_id: int,
    data: ProposalTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a proposal type."""
    proposal_type = db.query(ProposalType).filter(ProposalType.id == type_id).first()
    if not proposal_type:
        raise HTTPException(status_code=404, detail="Proposal type not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(proposal_type, key, value)

    db.commit()
    db.refresh(proposal_type)
    return proposal_type


@router.delete("/{type_id}")
def delete_proposal_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete (deactivate) a proposal type."""
    proposal_type = db.query(ProposalType).filter(ProposalType.id == type_id).first()
    if not proposal_type:
        raise HTTPException(status_code=404, detail="Proposal type not found")

    # Soft delete - just deactivate
    proposal_type.is_active = False
    db.commit()
    return {"message": "Proposal type deactivated"}


@router.post("/detect", response_model=ProposalTypeDetection)
def detect_type(
    extracted_data: dict,
    rfp_content: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Detect proposal type from extracted data or RFP content."""
    proposal_type, confidence, metadata = detect_proposal_type(extracted_data, rfp_content)

    return ProposalTypeDetection(
        proposal_type=proposal_type,
        confidence=confidence,
        source=metadata.get("source", "unknown"),
        matched_keywords=metadata.get("matched_keywords", [])
    )


@router.get("/{type_id}/blocks")
def get_type_blocks(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all blocks for a specific proposal type."""
    proposal_type = db.query(ProposalType).filter(ProposalType.id == type_id).first()
    if not proposal_type:
        raise HTTPException(status_code=404, detail="Proposal type not found")

    from sqlalchemy import or_
    from app.models.models import BlockLibrary

    blocks = db.query(ProposalBlock).join(
        BlockLibrary, ProposalBlock.library_id == BlockLibrary.id
    ).filter(
        or_(
            ProposalBlock.proposal_type_id == type_id,
            ProposalBlock.proposal_type_id == None,
            BlockLibrary.is_system == True
        ),
        ProposalBlock.is_active == True
    ).all()

    return [
        {
            "id": b.id,
            "name": b.name,
            "block_key": b.block_key,
            "block_type": b.block_type,
            "library_name": b.library.name if b.library else "",
            "section_order": b.section_order,
            "required_variables": b.required_variables or []
        }
        for b in blocks
    ]


@router.get("/metadata/analyze")
def analyze_rfp_metadata(
    extracted_data: str = None,
    rfp_content: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Extract additional metadata from RFP content."""
    import json

    data = {}
    if extracted_data:
        try:
            data = json.loads(extracted_data)
        except:
            pass

    industry_tags = detect_industry_tags(data, rfp_content)
    additional_metadata = extract_additional_metadata(data, rfp_content)

    return {
        "industry_tags": industry_tags,
        **additional_metadata
    }