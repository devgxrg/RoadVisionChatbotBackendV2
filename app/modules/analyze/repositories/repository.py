"""
Repository for TenderIQ analysis data access operations.
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session, joinedload

from app.modules.tenderiq.db.schema import Tender

from ..db.schema import TenderAnalysis

def get_wishlisted_tenders(db: Session, tdr: str) -> List[Tender]:
    wishlisted = db.query(Tender).filter(Tender.is_wishlisted == True).all()
    return wishlisted

def get_by_tender_id(db: Session, tender_id: str) -> Optional[TenderAnalysis]:
    """
    Retrieves a tender analysis record by the tender_id,
    eagerly loading related data.
    tender_id is the unique tender number eg. 51655667, 51702878 etc.
    """
    return (
        db.query(TenderAnalysis)
        .filter_by(tender_id=tender_id)
        .options(
            joinedload(TenderAnalysis.rfp_sections),
            joinedload(TenderAnalysis.document_templates)
        )
        .first()
    )

def get_by_id(db: Session, analysis_id: UUID) -> Optional[TenderAnalysis]:
    """Retrieves a tender analysis record by its own ID."""
    return db.query(TenderAnalysis).filter_by(id=analysis_id).first()

def create_for_tender(db: Session, tender_id: str, user_id: Optional[UUID]) -> TenderAnalysis:
    """
    Creates a new, pending tender analysis record for a given tender.
    """
    analysis = TenderAnalysis(tender_id=tender_id, user_id=user_id)
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis

def update(db: Session, analysis: TenderAnalysis, updates: dict) -> TenderAnalysis:
    """
    Updates a TenderAnalysis instance with a dictionary of changes.
    """
    for key, value in updates.items():
        setattr(analysis, key, value)
    db.commit()
    db.refresh(analysis)
    return analysis

def tender_is_analyzed(db: Session, tender_id: str) -> Optional[TenderAnalysis]:
    """Checks if a tender has been analyzed."""
    return (
        db.query(TenderAnalysis)
        .filter_by(tender_id=tender_id)
        .options(
            joinedload(TenderAnalysis.rfp_sections),
            joinedload(TenderAnalysis.document_templates)
        )
        .first()
    )
