from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from app.core.database import get_db
from app.models.models import BlockLibrary, ProposalBlock, BlockVariable, ProposalType, User
from app.schemas.schemas import (
    BlockLibraryCreate, BlockLibraryResponse,
    BlockCreate, BlockUpdate, BlockResponse, BlockDetailResponse,
    BlockVariableResponse
)
from app.api.auth import get_current_user


router = APIRouter()


@router.get("/libraries", response_model=List[BlockLibraryResponse])
def list_block_libraries(
    include_system: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all block libraries with block counts."""
    query = db.query(BlockLibrary)
    if not include_system:
        query = query.filter(BlockLibrary.is_system == False)

    libraries = query.all()

    result = []
    for lib in libraries:
        block_count = db.query(func.count(ProposalBlock.id)).filter(
            ProposalBlock.library_id == lib.id,
            ProposalBlock.is_active == True
        ).scalar()

        result.append(BlockLibraryResponse(
            id=lib.id,
            name=lib.name,
            display_name=lib.display_name,
            description=lib.description,
            is_system=lib.is_system,
            block_count=block_count
        ))

    return result


@router.post("/libraries", response_model=BlockLibraryResponse)
def create_block_library(
    data: BlockLibraryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new block library."""
    existing = db.query(BlockLibrary).filter(BlockLibrary.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Library already exists")

    library = BlockLibrary(
        name=data.name,
        display_name=data.display_name or data.name.replace("_", " ").title(),
        description=data.description,
        is_system=data.is_system
    )
    db.add(library)
    db.commit()
    db.refresh(library)

    return BlockLibraryResponse(
        id=library.id,
        name=library.name,
        display_name=library.display_name,
        description=library.description,
        is_system=library.is_system,
        block_count=0
    )


@router.get("/", response_model=List[BlockResponse])
def list_blocks(
    library_id: Optional[int] = None,
    proposal_type_id: Optional[int] = None,
    block_type: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all proposal blocks, optionally filtered."""
    query = db.query(ProposalBlock).join(
        BlockLibrary, ProposalBlock.library_id == BlockLibrary.id
    ).outerjoin(
        ProposalType, ProposalBlock.proposal_type_id == ProposalType.id
    )

    if library_id:
        query = query.filter(ProposalBlock.library_id == library_id)
    if proposal_type_id:
        from sqlalchemy import or_
        query = query.filter(or_(
            ProposalBlock.proposal_type_id == proposal_type_id,
            ProposalBlock.proposal_type_id == None
        ))
    if block_type:
        query = query.filter(ProposalBlock.block_type == block_type)
    if active_only:
        query = query.filter(ProposalBlock.is_active == True)

    query = query.order_by(ProposalBlock.section_order, ProposalBlock.subsection_order)
    blocks = query.all()

    return [
        BlockResponse(
            id=b.id,
            library_id=b.library_id,
            library_name=b.library.name if b.library else "",
            proposal_type_id=b.proposal_type_id,
            proposal_type_name=b.proposal_type.name if b.proposal_type else None,
            name=b.name,
            block_key=b.block_key,
            block_type=b.block_type,
            required_variables=b.required_variables or [],
            section_order=b.section_order,
            is_active=b.is_active,
            created_at=b.created_at
        )
        for b in blocks
    ]


@router.get("/{block_id}", response_model=BlockDetailResponse)
def get_block(
    block_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get block details including content."""
    block = db.query(ProposalBlock).filter(ProposalBlock.id == block_id).first()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    variables = db.query(BlockVariable).filter(BlockVariable.block_id == block_id).all()

    return BlockDetailResponse(
        id=block.id,
        library_id=block.library_id,
        library_name=block.library.name if block.library else "",
        proposal_type_id=block.proposal_type_id,
        proposal_type_name=block.proposal_type.name if block.proposal_type else None,
        name=block.name,
        block_key=block.block_key,
        block_type=block.block_type,
        required_variables=block.required_variables or [],
        section_order=block.section_order,
        is_active=block.is_active,
        created_at=block.created_at,
        content=block.content,
        default_variables=block.default_variables or {},
        condition_expression=block.condition_expression,
        variables=[
            BlockVariableResponse(
                id=v.id,
                variable_name=v.variable_name,
                display_name=v.display_name,
                data_type=v.data_type,
                default_value=v.default_value,
                is_required=v.is_required
            )
            for v in variables
        ]
    )


@router.post("/", response_model=BlockResponse)
def create_block(
    data: BlockCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new block."""
    # Verify library exists
    library = db.query(BlockLibrary).filter(BlockLibrary.id == data.library_id).first()
    if not library:
        raise HTTPException(status_code=400, detail="Library not found")

    # Verify type exists if specified
    if data.proposal_type_id:
        ptype = db.query(ProposalType).filter(ProposalType.id == data.proposal_type_id).first()
        if not ptype:
            raise HTTPException(status_code=400, detail="Proposal type not found")

    block = ProposalBlock(
        library_id=data.library_id,
        proposal_type_id=data.proposal_type_id,
        name=data.name,
        block_key=data.block_key,
        content=data.content,
        block_type=data.block_type,
        required_variables=data.required_variables,
        default_variables=data.default_variables,
        section_order=data.section_order,
        subsection_order=data.subsection_order,
        condition_expression=data.condition_expression
    )
    db.add(block)
    db.commit()
    db.refresh(block)

    return BlockResponse(
        id=block.id,
        library_id=block.library_id,
        library_name=library.name,
        proposal_type_id=block.proposal_type_id,
        proposal_type_name=ptype.name if data.proposal_type_id and 'ptype' in locals() else None,
        name=block.name,
        block_key=block.block_key,
        block_type=block.block_type,
        required_variables=block.required_variables or [],
        section_order=block.section_order,
        is_active=block.is_active,
        created_at=block.created_at
    )


@router.put("/{block_id}", response_model=BlockResponse)
def update_block(
    block_id: int,
    data: BlockUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a block."""
    block = db.query(ProposalBlock).filter(ProposalBlock.id == block_id).first()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(block, key, value)

    db.commit()
    db.refresh(block)

    return BlockResponse(
        id=block.id,
        library_id=block.library_id,
        library_name=block.library.name if block.library else "",
        proposal_type_id=block.proposal_type_id,
        proposal_type_name=block.proposal_type.name if block.proposal_type else None,
        name=block.name,
        block_key=block.block_key,
        block_type=block.block_type,
        required_variables=block.required_variables or [],
        section_order=block.section_order,
        is_active=block.is_active,
        created_at=block.created_at
    )


@router.delete("/{block_id}")
def delete_block(
    block_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete (deactivate) a block."""
    block = db.query(ProposalBlock).filter(ProposalBlock.id == block_id).first()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    block.is_active = False
    db.commit()
    return {"message": "Block deactivated"}


@router.post("/preview")
def preview_block(
    block_id: int,
    variables: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Preview a block with sample variables."""
    block = db.query(ProposalBlock).filter(ProposalBlock.id == block_id).first()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    from app.services.block_composer import BlockComposer
    composer = BlockComposer(db)
    rendered = composer._render_block(
        {
            'content': block.content,
            'default_variables': block.default_variables or {}
        },
        variables
    )

    return {
        "block_name": block.name,
        "rendered_content": rendered.get('rendered_content', '')
    }