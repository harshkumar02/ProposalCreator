from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Float, JSON, Index, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    rfps = relationship("RFP", back_populates="user")
    proposals = relationship("Proposal", back_populates="user")
    templates = relationship("Template", back_populates="user")
    proposal_templates = relationship("ProposalTemplate", back_populates="user")


class RFP(Base):
    __tablename__ = "rfps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(500), nullable=True)
    file_type = Column(String(50), nullable=False)
    content = Column(Text, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    # Tender-level facts from clause extraction (tender id, deadline, EMD, ...)
    tender_details = Column(JSON, nullable=True)

    user = relationship("User", back_populates="rfps")
    extraction_results = relationship("ExtractionResult", back_populates="rfp")
    clauses = relationship("RFPClause", back_populates="rfp", cascade="all, delete-orphan")
    proposals = relationship("Proposal", back_populates="rfp")


class ExtractionResult(Base):
    __tablename__ = "extraction_results"

    id = Column(Integer, primary_key=True, index=True)
    rfp_id = Column(Integer, ForeignKey("rfps.id"), nullable=False)
    engine = Column(String(100), nullable=False)
    field_name = Column(String(255), nullable=False)
    value = Column(Text, nullable=True)
    confidence = Column(Float, default=0.0)
    is_reviewed = Column(Boolean, default=False)

    rfp = relationship("RFP", back_populates="extraction_results")


class Proposal(Base):
    __tablename__ = "proposals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rfp_id = Column(Integer, ForeignKey("rfps.id"), nullable=True)
    proposal_type_id = Column(Integer, ForeignKey("proposal_types.id"), nullable=True)
    template_id = Column(Integer, ForeignKey("proposal_templates.id"), nullable=True)
    client_name = Column(String(255), nullable=False)
    title = Column(String(500), nullable=True)
    status = Column(String(50), default="draft")
    version = Column(Integer, default=1)
    extracted_data = Column(Text, nullable=True)
    block_assignments = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="proposals")
    rfp = relationship("RFP", back_populates="proposals")
    versions = relationship("ProposalVersion", back_populates="proposal")
    proposal_type = relationship("ProposalType", back_populates="proposals")
    proposal_template = relationship("ProposalTemplate", back_populates="proposals")


class ProposalVersion(Base):
    __tablename__ = "proposal_versions"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(Integer, ForeignKey("proposals.id"), nullable=False)
    version = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    proposal = relationship("Proposal", back_populates="versions")


class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="templates")


# ============================================================
# Modular Proposal Engine Models
# ============================================================

class ProposalType(Base):
    __tablename__ = "proposal_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    keywords = Column(JSON, default=[])
    industry_tags = Column(JSON, default=[])
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    proposals = relationship("Proposal", back_populates="proposal_type")
    blocks = relationship("ProposalBlock", back_populates="proposal_type")
    templates = relationship("ProposalTemplate", back_populates="proposal_type")


class BlockLibrary(Base):
    __tablename__ = "block_libraries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    blocks = relationship("ProposalBlock", back_populates="library")


class ProposalBlock(Base):
    __tablename__ = "proposal_blocks"

    id = Column(Integer, primary_key=True, index=True)
    library_id = Column(Integer, ForeignKey("block_libraries.id"), nullable=False)
    proposal_type_id = Column(Integer, ForeignKey("proposal_types.id"), nullable=True)
    name = Column(String(255), nullable=False)
    block_key = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    block_type = Column(String(50), default="section")
    required_variables = Column(JSON, default=[])
    default_variables = Column(JSON, default={})
    section_order = Column(Integer, default=0)
    subsection_order = Column(Integer, default=0)
    condition_expression = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    library = relationship("BlockLibrary", back_populates="blocks")
    proposal_type = relationship("ProposalType", back_populates="blocks")
    variables = relationship("BlockVariable", back_populates="block")


class BlockVariable(Base):
    __tablename__ = "block_variables"

    id = Column(Integer, primary_key=True, index=True)
    block_id = Column(Integer, ForeignKey("proposal_blocks.id"), nullable=False)
    variable_name = Column(String(100), nullable=False)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    data_type = Column(String(50), default="string")
    default_value = Column(Text, nullable=True)
    is_required = Column(Boolean, default=True)

    block = relationship("ProposalBlock", back_populates="variables")


class ProposalTemplate(Base):
    __tablename__ = "proposal_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    proposal_type_id = Column(Integer, ForeignKey("proposal_types.id"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    block_order = Column(JSON, default=[])
    content = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="proposal_templates")
    proposal_type = relationship("ProposalType", back_populates="templates")
    proposals = relationship("Proposal", back_populates="proposal_template")

class WorkflowRun(Base):
    """One execution of an n8n workflow, tracked from the backend's side.

    The backend creates the row and triggers n8n; n8n reports progress back
    through the /internal callback, so the frontend polls this row rather than
    n8n itself.
    """
    __tablename__ = "workflow_runs"
    __table_args__ = (
        # At most one active run per RFP: concurrent runs would each delete and
        # rewrite the same extraction rows. Partial index, so finished runs don't count.
        Index(
            "uq_workflow_runs_active_rfp",
            "rfp_id",
            unique=True,
            sqlite_where=text("status IN ('PENDING', 'RUNNING') AND rfp_id IS NOT NULL"),
            postgresql_where=text("status IN ('PENDING', 'RUNNING') AND rfp_id IS NOT NULL"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    rfp_id = Column(Integer, ForeignKey("rfps.id"), nullable=True, index=True)
    proposal_id = Column(Integer, ForeignKey("proposals.id"), nullable=True, index=True)
    workflow = Column(String(100), nullable=False)
    # PENDING -> RUNNING -> COMPLETED | FAILED
    status = Column(String(30), nullable=False, default="PENDING")
    current_step = Column(String(255), nullable=True)
    n8n_execution_id = Column(String(100), nullable=True)
    params = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)


class RFPClause(Base):
    """One requirement extracted from a tender (PQ, TQ, scope, commercial, ...).

    The typed columns are what reviewers edit and later phases evaluate;
    ``ai_data`` keeps the extractor's original output untouched, so human
    corrections stay distinguishable from what the model claimed.
    """
    __tablename__ = "rfp_clauses"

    id = Column(Integer, primary_key=True, index=True)
    rfp_id = Column(Integer, ForeignKey("rfps.id"), nullable=False, index=True)
    run_id = Column(Integer, ForeignKey("workflow_runs.id"), nullable=True)
    clause_code = Column(String(30), nullable=False)          # PQ-001, TQ-004, ...
    category = Column(String(30), nullable=False, index=True)  # see clause_extractor.CATEGORIES
    criterion_type = Column(String(50), nullable=True)         # turnover, certification, experience, ...
    requirement = Column(Text, nullable=False)                 # normalised one-line statement
    source_text = Column(Text, nullable=True)                  # verbatim excerpt from the tender
    mandatory = Column(Boolean, nullable=True)                 # None = document doesn't say
    threshold_value = Column(Float, nullable=True)
    threshold_unit = Column(String(30), nullable=True)         # INR, count, years, percent, ...
    operator = Column(String(10), nullable=True)               # >=, >, <=, <, =
    period = Column(String(255), nullable=True)                # "last 3 FYs (FY24-FY26)"
    min_count = Column(Integer, nullable=True)
    max_marks = Column(Float, nullable=True)                   # TQ only
    scoring_rule = Column(Text, nullable=True)                 # TQ only
    evidence_required = Column(JSON, nullable=True)
    page_number = Column(Integer, nullable=True)
    section_ref = Column(String(100), nullable=True)
    amended_by = Column(String(255), nullable=True)            # corrigendum that changed this clause
    confidence = Column(Float, nullable=True)
    provider = Column(String(30), nullable=True)               # claude | gemini | manual
    ai_data = Column(JSON, nullable=True)
    review_status = Column(String(20), nullable=False, default="PENDING")  # PENDING | VERIFIED | REJECTED
    reviewer_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    rfp = relationship("RFP", back_populates="clauses")
