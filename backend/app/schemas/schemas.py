from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone


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
    proposal_type_id: Optional[int] = None
    template_id: Optional[int] = None
    extracted_data: Optional[str] = None


class ProposalUpdate(BaseModel):
    client_name: Optional[str] = None
    title: Optional[str] = None
    status: Optional[str] = None
    proposal_type_id: Optional[int] = None
    template_id: Optional[int] = None
    block_assignments: Optional[Dict[str, Any]] = None
    extracted_data: Optional[str] = None


class ProposalResponse(BaseModel):
    id: int
    user_id: int
    rfp_id: Optional[int]
    proposal_type_id: Optional[int]
    template_id: Optional[int]
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
    proposal_type_name: Optional[str] = None


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


# ============================================================
# Proposal Engine Schemas
# ============================================================

# Proposal Type Schemas
class ProposalTypeCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    keywords: List[str] = []
    industry_tags: List[str] = []
    sort_order: int = 0


class ProposalTypeUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    industry_tags: Optional[List[str]] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class ProposalTypeResponse(BaseModel):
    id: int
    name: str
    display_name: Optional[str]
    description: Optional[str]
    keywords: List[str]
    industry_tags: List[str]
    is_active: bool
    sort_order: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProposalTypeDetection(BaseModel):
    proposal_type: str
    confidence: float
    source: str
    matched_keywords: List[str] = []


# Block Library Schemas
class BlockLibraryCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_system: bool = False


class BlockLibraryResponse(BaseModel):
    id: int
    name: str
    display_name: Optional[str]
    description: Optional[str]
    is_system: bool
    block_count: int = 0

    class Config:
        from_attributes = True


# Block Schemas
class BlockCreate(BaseModel):
    library_id: int
    proposal_type_id: Optional[int] = None
    name: str
    block_key: str
    content: str
    block_type: str = "section"
    required_variables: List[str] = []
    default_variables: Dict[str, Any] = {}
    section_order: int = 0
    subsection_order: int = 0
    condition_expression: Optional[str] = None


class BlockUpdate(BaseModel):
    library_id: Optional[int] = None
    proposal_type_id: Optional[int] = None
    name: Optional[str] = None
    content: Optional[str] = None
    block_type: Optional[str] = None
    required_variables: Optional[List[str]] = None
    default_variables: Optional[Dict[str, Any]] = None
    section_order: Optional[int] = None
    subsection_order: Optional[int] = None
    condition_expression: Optional[str] = None
    is_active: Optional[bool] = None


class BlockResponse(BaseModel):
    id: int
    library_id: int
    library_name: str
    proposal_type_id: Optional[int]
    proposal_type_name: Optional[str]
    name: str
    block_key: str
    block_type: str
    required_variables: List[str]
    section_order: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class BlockDetailResponse(BlockResponse):
    content: str
    default_variables: Dict[str, Any]
    condition_expression: Optional[str]
    variables: List["BlockVariableResponse"] = []


class BlockVariableResponse(BaseModel):
    id: int
    variable_name: str
    display_name: Optional[str]
    data_type: str
    default_value: Optional[str]
    is_required: bool

    class Config:
        from_attributes = True


# Block Composition Schemas
class CompositionConfig(BaseModel):
    proposal_type_id: Optional[int] = None
    template_id: Optional[int] = None
    custom_block_order: Optional[List[str]] = None
    include_optional: bool = True


class ComposedBlock(BaseModel):
    block_id: int
    name: str
    block_key: str
    block_type: str
    rendered_content: str
    section_order: int


class CompositionResponse(BaseModel):
    proposal_id: int
    proposal_type: Optional[str]
    blocks: List[ComposedBlock]
    total_blocks: int
    missing_variables: List[str] = []


# Export Schemas
class ExportRequest(BaseModel):
    format: str = "docx"
    proposal_type_id: Optional[int] = None
    template_id: Optional[int] = None
    include_cover: bool = True
    include_toc: bool = False

# Workflow (n8n) Schemas
class WorkflowRunCreate(BaseModel):
    workflow: str
    rfp_id: Optional[int] = None
    proposal_id: Optional[int] = None
    params: Optional[Dict[str, Any]] = None


class WorkflowRunResponse(BaseModel):
    id: int
    workflow: str
    rfp_id: Optional[int] = None
    proposal_id: Optional[int] = None
    status: str
    current_step: Optional[str] = None
    n8n_execution_id: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    @field_validator("created_at", "updated_at", "finished_at")
    @classmethod
    def _assume_utc(cls, value: Optional[datetime]) -> Optional[datetime]:
        # SQLite drops tzinfo; timestamps are stored in UTC, so say so in the
        # response instead of letting the browser read them as local time.
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    class Config:
        from_attributes = True


class WorkflowStatusUpdate(BaseModel):
    status: str
    current_step: Optional[str] = None
    n8n_execution_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class InternalExtractRequest(BaseModel):
    run_id: int
    engines: List[str] = ["claude"]


# Clause (tender requirement) Schemas
class RFPClauseResponse(BaseModel):
    id: int
    rfp_id: int
    run_id: Optional[int] = None
    clause_code: str
    category: str
    criterion_type: Optional[str] = None
    requirement: str
    source_text: Optional[str] = None
    mandatory: Optional[bool] = None
    threshold_value: Optional[float] = None
    threshold_unit: Optional[str] = None
    operator: Optional[str] = None
    period: Optional[str] = None
    min_count: Optional[int] = None
    max_marks: Optional[float] = None
    scoring_rule: Optional[str] = None
    evidence_required: Optional[List[str]] = None
    page_number: Optional[int] = None
    section_ref: Optional[str] = None
    amended_by: Optional[str] = None
    confidence: Optional[float] = None
    provider: Optional[str] = None
    review_status: str
    reviewer_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    edited: bool = False

    class Config:
        from_attributes = True


class RFPClauseUpdate(BaseModel):
    category: Optional[str] = None
    criterion_type: Optional[str] = None
    requirement: Optional[str] = None
    mandatory: Optional[bool] = None
    threshold_value: Optional[float] = None
    threshold_unit: Optional[str] = None
    operator: Optional[str] = None
    period: Optional[str] = None
    min_count: Optional[int] = None
    max_marks: Optional[float] = None
    scoring_rule: Optional[str] = None
    evidence_required: Optional[List[str]] = None
    page_number: Optional[int] = None
    section_ref: Optional[str] = None
    review_status: Optional[str] = None
    reviewer_notes: Optional[str] = None


class RFPClauseCreate(RFPClauseUpdate):
    category: str
    requirement: str
    source_text: Optional[str] = None


class RFPClauseListResponse(BaseModel):
    clauses: List[RFPClauseResponse]
    tender_details: Optional[Dict[str, Any]] = None
    summary: Dict[str, Any]


class InternalClauseExtractRequest(BaseModel):
    run_id: int
    provider: Optional[str] = None
