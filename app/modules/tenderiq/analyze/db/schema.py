import uuid
import enum
from datetime import datetime
from sqlalchemy import (Column, String, DateTime, ForeignKey, Text, JSON,
                        Integer, Boolean, Enum as SQLAlchemyEnum)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.modules.tenderiq.db.schema import Tender


class AnalysisStatusEnum(str, enum.Enum):
    """Defines the processing status of a tender analysis."""
    pending = "pending"
    parsing = "parsing"
    analyzing = "analyzing"
    completed = "completed"
    failed = "failed"


class TenderAnalysis(Base):
    """
    Central table to track the analysis of a single tender.
    Maintains a one-to-one relationship with a Tender.
    """
    __tablename__ = 'tender_analysis'
    id = Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # One-to-one relationship to the Tender being analyzed
    tender_id = Column(postgresql.UUID(as_uuid=True), ForeignKey(Tender.id), nullable=False, unique=True, index=True)
    
    # Analysis metadata
    status = Column(SQLAlchemyEnum(AnalysisStatusEnum), default=AnalysisStatusEnum.pending, nullable=False, index=True)
    progress = Column(Integer, default=0, nullable=False) # Percentage, e.g., 0-100
    status_message = Column(String(255), nullable=True) # e.g., "Parsing document 1 of 3..."
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    analysis_started_at = Column(DateTime, nullable=True)
    analysis_completed_at = Column(DateTime, nullable=True)
    
    # Analysis Results (stored as JSON for flexibility with LLM outputs)
    one_pager_json = Column(JSON, nullable=True)
    scope_of_work_json = Column(JSON, nullable=True)
    data_sheet_json = Column(JSON, nullable=True)

    # Relationships
    tender = relationship("Tender", backref="analysis", uselist=False)
    rfp_sections = relationship("AnalysisRFPSection", back_populates="analysis", cascade="all, delete-orphan")
    document_templates = relationship("AnalysisDocumentTemplate", back_populates="analysis", cascade="all, delete-orphan")


class AnalysisRFPSection(Base):
    """
    Stores a detailed, section-wise analysis of the RFP.
    Each row represents one section of the tender document.
    """
    __tablename__ = 'analysis_rfp_sections'
    id = Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(postgresql.UUID(as_uuid=True), ForeignKey('tender_analysis.id'), nullable=False, index=True)
    
    section_number = Column(String(50), nullable=True) # e.g., "1.1", "2.3.a"
    section_title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    key_requirements = Column(JSON, nullable=True) # List of extracted requirements
    compliance_issues = Column(JSON, nullable=True) # List of potential compliance issues
    page_references = Column(JSON, nullable=True) # List of page numbers where this section appears

    # Relationships
    analysis = relationship("TenderAnalysis", back_populates="rfp_sections")


class AnalysisDocumentTemplate(Base):
    """
    Stores document templates extracted from the RFP (e.g., forms, declarations).
    """
    __tablename__ = 'analysis_document_templates'
    id = Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(postgresql.UUID(as_uuid=True), ForeignKey('tender_analysis.id'), nullable=False, index=True)
    
    template_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    required_format = Column(String(50), nullable=True) # e.g., "PDF", "Word Document"
    content_preview = Column(Text, nullable=True) # A snippet or summary of the template
    page_references = Column(JSON, nullable=True) # List of page numbers

    # Relationships
    analysis = relationship("TenderAnalysis", back_populates="document_templates")
