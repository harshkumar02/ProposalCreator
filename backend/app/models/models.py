from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Float
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


class RFP(Base):
    __tablename__ = "rfps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(500), nullable=True)
    file_type = Column(String(50), nullable=False)
    content = Column(Text, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="rfps")
    extraction_results = relationship("ExtractionResult", back_populates="rfp")
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
    client_name = Column(String(255), nullable=False)
    title = Column(String(500), nullable=True)
    status = Column(String(50), default="draft")
    version = Column(Integer, default=1)
    extracted_data = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="proposals")
    rfp = relationship("RFP", back_populates="proposals")
    versions = relationship("ProposalVersion", back_populates="proposal")


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