"""
API endpoints for the TenderIQ analysis submodule.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.modules.auth.services.auth_service import get_current_active_user
from app.modules.auth.db.schema import User
from app.modules.tenderiq.db.tenderiq_repository import TenderIQRepository
from app.modules.tenderiq.analyze.db.repository import AnalyzeRepository

router = APIRouter()

@router.get("/{tender_id}")
def get_analysis_result(
    tender_id: UUID,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieves the analysis result for a specific tender.
    If analysis is not found, it could mean it has not been generated yet.
    """
    # 1. Find the ScrapedTender record using the UUID to get the tender_id_str
    scraped_tender_repo = TenderIQRepository(db)
    scraped_tender = scraped_tender_repo.get_tender_by_id(tender_id)
    if not scraped_tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tender with the given ID not found."
        )

    # 2. Use the tender_id_str to find the analysis record
    analyze_repo = AnalyzeRepository(db)
    analysis = analyze_repo.get_by_tender_id(scraped_tender.tender_id_str)
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis for this tender has not been generated yet or is not found."
        )

    return analysis.to_dict()
