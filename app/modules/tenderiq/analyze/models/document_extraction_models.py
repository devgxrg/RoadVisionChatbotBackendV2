"""
Pydantic Models for Document Extraction (Phase 1).

Defines structured data models for results from the DocumentParser service.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID


class DocumentMetadata(BaseModel):
    """Metadata for the parsed document"""
    original_filename: str
    file_size: int
    file_type: str
    page_count: int
    uploaded_at: datetime


class ExtractedSection(BaseModel):
    """A single extracted section from the document"""
    section_number: str
    title: str
    text: str
    page_numbers: List[int] = []
    confidence: float = Field(..., ge=0, le=100)


class ExtractedTable(BaseModel):
    """A single extracted table from the document"""
    table_number: int
    title: str
    data: Dict[str, Any]  # Could be raw text or parsed data
    page_number: int
    location_on_page: str
    confidence: float = Field(..., ge=0, le=100)


class ExtractedFigure(BaseModel):
    """A single extracted figure or image reference"""
    figure_number: int
    description: str
    figure_type: str
    page_number: int
    confidence: float = Field(..., ge=0, le=100)


class QualityWarning(BaseModel):
    """A warning about the quality of the extraction"""
    field: str
    severity: str
    message: str
    recommendation: str


class QualityRecommendation(BaseModel):
    """A recommendation to improve extraction quality"""
    priority: str
    suggestion: str
    impact: str


class ExtractionQualityResult(BaseModel):
    """Comprehensive quality assessment of the document extraction"""
    extraction_quality: float = Field(..., ge=0, le=100)
    data_completeness: float = Field(..., ge=0, le=100)
    warnings: List[QualityWarning] = []
    recommendations: List[QualityRecommendation] = []


class DocumentExtractionResult(BaseModel):
    """Complete result of parsing a single document"""
    analysis_id: UUID
    metadata: DocumentMetadata
    raw_text: str
    sections: List[ExtractedSection] = []
    tables: List[ExtractedTable] = []
    figures: List[ExtractedFigure] = []
    extraction_quality: float = Field(..., ge=0, le=100)
    ocr_required: bool
    ocr_confidence: Optional[float] = Field(None, ge=0, le=100)
    extractable_sections: int
    extraction_started_at: datetime
    extraction_completed_at: datetime
    processing_duration_seconds: float
