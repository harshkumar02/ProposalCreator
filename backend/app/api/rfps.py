from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
import fitz
import mammoth
import io
from typing import List, Optional

from app.core.database import get_db
from app.models.models import RFP, User, ExtractionResult
from app.schemas.schemas import RFPResponse, ExtractionResultResponse, ExtractionResultUpdate, ExtractionResultsResponse
from app.api.auth import get_current_user

router = APIRouter()


def extract_text_from_pdf(file_content: bytes) -> str:
    try:
        doc = fitz.open(stream=file_content, filetype="pdf")
        # Page markers let clause extraction cite the page each requirement is on
        # (see services/clause_extractor.split_pages).
        text = "".join(
            f"--- Page {number} ---\n{page.get_text()}\n"
            for number, page in enumerate(doc, start=1)
        )
        doc.close()
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract PDF text: {str(e)}")


def extract_text_from_docx(file_content: bytes) -> str:
    try:
        result = mammoth.extract_raw_text({"stream": file_content, "filename": "document.docx"})
        return result.value
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract DOCX text: {str(e)}")


@router.post("/upload", response_model=RFPResponse)
async def upload_rfp(
    file: Optional[UploadFile] = File(None),
    content: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    filename = None
    file_type = "text"
    extracted_text = None

    if file:
        filename = file.filename
        file_content = await file.read()

        if filename.lower().endswith('.pdf'):
            file_type = "pdf"
            extracted_text = extract_text_from_pdf(file_content)
        elif filename.lower().endswith(('.doc', '.docx')):
            file_type = "docx"
            extracted_text = extract_text_from_docx(file_content)
        elif filename.lower().endswith('.txt'):
            file_type = "txt"
            extracted_text = file_content.decode('utf-8', errors='ignore')
        else:
            file_type = "unknown"
            extracted_text = file_content.decode('utf-8', errors='ignore')
    elif content:
        file_type = "text"
        extracted_text = content
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either file or content must be provided"
        )

    rfp = RFP(
        user_id=current_user.id,
        filename=filename,
        file_type=file_type,
        content=extracted_text
    )
    db.add(rfp)
    db.commit()
    db.refresh(rfp)

    return RFPResponse.model_validate(rfp)


@router.get("/", response_model=List[RFPResponse])
def list_rfps(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rfps = db.query(RFP).filter(RFP.user_id == current_user.id).offset(skip).limit(limit).all()
    return [RFPResponse.model_validate(rfp) for rfp in rfps]


@router.get("/{rfp_id}", response_model=RFPResponse)
def get_rfp(
    rfp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rfp = db.query(RFP).filter(RFP.id == rfp_id, RFP.user_id == current_user.id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    return RFPResponse.model_validate(rfp)


@router.get("/{rfp_id}/content")
def get_rfp_content(
    rfp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rfp = db.query(RFP).filter(RFP.id == rfp_id, RFP.user_id == current_user.id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    return {"content": rfp.content}


@router.delete("/{rfp_id}")
def delete_rfp(
    rfp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rfp = db.query(RFP).filter(RFP.id == rfp_id, RFP.user_id == current_user.id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    db.query(ExtractionResult).filter(ExtractionResult.rfp_id == rfp_id).delete()
    db.delete(rfp)
    db.commit()

    return {"message": "RFP deleted successfully"}


@router.get("/{rfp_id}/extraction-results", response_model=ExtractionResultsResponse)
def get_extraction_results(
    rfp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rfp = db.query(RFP).filter(RFP.id == rfp_id, RFP.user_id == current_user.id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    results = db.query(ExtractionResult).filter(ExtractionResult.rfp_id == rfp_id).all()
    engines = list(set(r.engine for r in results))

    return ExtractionResultsResponse(
        results=[ExtractionResultResponse.model_validate(r) for r in results],
        engines_used=engines
    )


@router.put("/{rfp_id}/extraction-results/{result_id}", response_model=ExtractionResultResponse)
def update_extraction_result(
    rfp_id: int,
    result_id: int,
    update_data: ExtractionResultUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rfp = db.query(RFP).filter(RFP.id == rfp_id, RFP.user_id == current_user.id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    result = db.query(ExtractionResult).filter(
        ExtractionResult.id == result_id,
        ExtractionResult.rfp_id == rfp_id
    ).first()
    if not result:
        raise HTTPException(status_code=404, detail="Extraction result not found")

    if update_data.field_name is not None:
        result.field_name = update_data.field_name
    if update_data.value is not None:
        result.value = update_data.value
    if update_data.is_reviewed is not None:
        result.is_reviewed = update_data.is_reviewed

    db.commit()
    db.refresh(result)

    return ExtractionResultResponse.model_validate(result)