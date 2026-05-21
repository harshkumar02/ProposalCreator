from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime


# Auth Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# RFP Schemas
class RFPCreate(BaseModel):
    content: Optional[str] = None


class RFPResponse(BaseModel):
    id: int
    user_id: int
    filename: Optional[str]
    file_type: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


# Extraction Schemas - Fields matching 63SATS proposal format
EXTRACTION_FIELDS = [
    "client_name",
    "project_title",
    "current_challenges",
    "objectives",
    "assets",
    "key_services",
    "solution_proposed",
    "implementation_approach",
    "implementation_methodology",
    "timeline",
    "assumptions",
    "expected_outcomes",
    "contact_information",
    "compliance_requirements",
    "security_requirements",
    "pricing_information",
    "qualifications",
    "deliverables",
    "terms_and_conditions",
]


class ExtractionResultResponse(BaseModel):
    id: int
    rfp_id: int
    engine: str
    field_name: str
    value: Optional[str]
    confidence: float
    is_reviewed: bool

    class Config:
        from_attributes = True


class ExtractionResultUpdate(BaseModel):
    field_name: Optional[str] = None
    value: Optional[str] = None
    is_reviewed: Optional[bool] = None


class ExtractionResultsResponse(BaseModel):
    results: List[ExtractionResultResponse]
    engines_used: List[str]


# Proposal Schemas
class ProposalCreate(BaseModel):
    client_name: str
    title: Optional[str] = None
    rfp_id: Optional[int] = None
    extracted_data: Optional[str] = None


class ProposalUpdate(BaseModel):
    client_name: Optional[str] = None
    title: Optional[str] = None
    status: Optional[str] = None
    extracted_data: Optional[str] = None


class ProposalResponse(BaseModel):
    id: int
    user_id: int
    rfp_id: Optional[int]
    client_name: str
    title: Optional[str]
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProposalDetailResponse(ProposalResponse):
    extraction_results: List[ExtractionResultResponse] = []
    extracted_data_dict: Optional[Dict[str, str]] = {}


class ExtractedDataResponse(BaseModel):
    """Structured extracted data matching 63SATS proposal format"""
    client_name: Optional[str] = None
    project_title: Optional[str] = None
    current_challenges: Optional[str] = None
    objectives: Optional[str] = None
    assets: Optional[str] = None
    key_services: Optional[str] = None
    solution_proposed: Optional[str] = None
    implementation_approach: Optional[str] = None
    implementation_methodology: Optional[str] = None
    timeline: Optional[str] = None
    assumptions: Optional[str] = None
    expected_outcomes: Optional[str] = None
    contact_information: Optional[str] = None
    compliance_requirements: Optional[str] = None
    security_requirements: Optional[str] = None
    pricing_information: Optional[str] = None
    qualifications: Optional[str] = None
    deliverables: Optional[str] = None
    terms_and_conditions: Optional[str] = None


# Template Schemas
class TemplateCreate(BaseModel):
    name: str
    content: Optional[str] = None
    is_default: bool = False


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    is_default: Optional[bool] = None


class TemplateResponse(BaseModel):
    id: int
    user_id: int
    name: str
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TemplateDetailResponse(TemplateResponse):
    content: Optional[str]