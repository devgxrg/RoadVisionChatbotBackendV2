"""
TenderIQ Repository Layer

Encapsulates all data access logic for TenderIQ features.
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.modules.tenderiq.db.schema import (
    TenderAnalysis,
    AnalysisResults,
    AnalysisRisk,
    AnalysisRFPSection,
    TenderExtractedContent,
    ExtractionQualityMetrics,
)


class AnalyzeRepository:
    """Repository for TenderIQ analysis data access operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_analysis(
        self, tender_id: UUID, user_id: UUID, analysis_type: str, **kwargs
    ) -> TenderAnalysis:
        """Create a new tender analysis record."""
        analysis = TenderAnalysis(
            tender_id=tender_id,
            user_id=user_id,
            analysis_type=analysis_type,
            **kwargs,
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def get_analysis_by_id(self, analysis_id: UUID) -> Optional[TenderAnalysis]:
        """Get an analysis by its ID."""
        return (
            self.db.query(TenderAnalysis)
            .filter(TenderAnalysis.id == analysis_id)
            .first()
        )

    def get_analysis_results(
        self, analysis_id: UUID
    ) -> Optional[AnalysisResults]:
        """Get analysis results by analysis ID."""
        return (
            self.db.query(AnalysisResults)
            .filter(AnalysisResults.analysis_id == analysis_id)
            .first()
        )

    def get_user_analyses(
        self, user_id: UUID, status: Optional[str], tender_id: Optional[UUID], limit: int, offset: int
    ) -> (List[TenderAnalysis], int):
        """Get all analyses for a user with optional filters."""
        query = self.db.query(TenderAnalysis).filter(TenderAnalysis.user_id == user_id)
        if status:
            query = query.filter(TenderAnalysis.status == status)
        if tender_id:
            query = query.filter(TenderAnalysis.tender_id == tender_id)
        
        total = query.count()
        analyses = query.limit(limit).offset(offset).all()
        return analyses, total

    def delete_analysis(self, analysis_id: UUID) -> bool:
        """Delete an analysis and its results."""
        analysis = self.get_analysis_by_id(analysis_id)
        if analysis:
            self.db.delete(analysis)
            self.db.commit()
            return True
        return False
