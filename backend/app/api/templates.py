from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import List
import io

from app.core.database import get_db
from app.models.models import Template, User
from app.schemas.schemas import TemplateCreate, TemplateUpdate, TemplateResponse, TemplateDetailResponse
from app.api.auth import get_current_user
from app.services.document_generator import create_template_from_content

router = APIRouter()


@router.post("/", response_model=TemplateResponse)
async def create_template(
    template_data: TemplateCreate,
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    content = template_data.content

    # If file is uploaded, extract content from it
    if file:
        file_content = await file.read()

        if file.filename.lower().endswith(('.docx', '.doc')):
            from docx import Document
            doc = Document(io.BytesIO(file_content))
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)
            content = '\n\n'.join(paragraphs)

        elif file.filename.lower().endswith('.txt'):
            content = file_content.decode('utf-8', errors='ignore')

    # If this is set as default, unset other defaults
    if template_data.is_default:
        db.query(Template).filter(Template.user_id == current_user.id).update({"is_default": False})

    template = Template(
        user_id=current_user.id,
        name=template_data.name,
        content=content,
        is_default=template_data.is_default
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    return TemplateResponse.model_validate(template)


@router.get("/", response_model=List[TemplateResponse])
def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    templates = db.query(Template).filter(Template.user_id == current_user.id).all()
    return [TemplateResponse.model_validate(t) for t in templates]


@router.get("/{template_id}", response_model=TemplateDetailResponse)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    template = db.query(Template).filter(
        Template.id == template_id,
        Template.user_id == current_user.id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return TemplateDetailResponse.model_validate(template)


@router.put("/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: int,
    update_data: TemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    template = db.query(Template).filter(
        Template.id == template_id,
        Template.user_id == current_user.id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if update_data.name is not None:
        template.name = update_data.name
    if update_data.content is not None:
        template.content = update_data.content
    if update_data.is_default is not None:
        if update_data.is_default:
            db.query(Template).filter(Template.user_id == current_user.id).update({"is_default": False})
        template.is_default = update_data.is_default

    db.commit()
    db.refresh(template)

    return TemplateResponse.model_validate(template)


@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    template = db.query(Template).filter(
        Template.id == template_id,
        Template.user_id == current_user.id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    db.delete(template)
    db.commit()

    return {"message": "Template deleted successfully"}


@router.get("/default/")
def get_default_template(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    template = db.query(Template).filter(
        Template.user_id == current_user.id,
        Template.is_default == True
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="No default template found")

    return TemplateDetailResponse.model_validate(template)