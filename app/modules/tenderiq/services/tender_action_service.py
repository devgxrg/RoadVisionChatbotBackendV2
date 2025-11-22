"""
Service for performing actions on tenders.
"""
import uuid
import logging
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import threading

from app.modules.tenderiq.db.tenderiq_repository import TenderIQRepository
from app.modules.tenderiq.db.repository import TenderRepository
from app.modules.tenderiq.models.pydantic_models import TenderActionRequest, TenderActionType
from app.modules.tenderiq.db.schema import Tender, TenderActionEnum
from app.modules.analyze.scripts.analyze_tender import analyze_tender
from app.db.database import SessionLocal

logger = logging.getLogger(__name__)

class TenderActionService:
    def __init__(self, db: Session):
        self.db = db
        self.tender_repo = TenderRepository(db)
        self.scraped_tender_repo = TenderIQRepository(db)

    def perform_action(self, tender_id: uuid.UUID, user_id: uuid.UUID, request: TenderActionRequest) -> Tender:
        scraped_tender = self.scraped_tender_repo.get_tender_by_id(tender_id)
        if not scraped_tender:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tender not found")

        tender = self.tender_repo.get_or_create_by_id(scraped_tender)

        updates = {}
        action_to_log: Optional[TenderActionEnum] = None
        notes = request.payload.notes if request.payload else None

        if request.action == TenderActionType.TOGGLE_WISHLIST:
            updates['is_wishlisted'] = not tender.is_wishlisted
            action_to_log = TenderActionEnum.wishlisted if updates['is_wishlisted'] else TenderActionEnum.unwishlisted

            # If tender is being wishlisted, trigger analysis in background
            if updates['is_wishlisted']:
                tender_ref = scraped_tender.tender_id_str
                logger.info(f"Triggering analysis for wishlisted tender: {tender_ref}")

                # Run analysis in background thread to avoid blocking the request
                def run_analysis():
                    analysis_db = SessionLocal()
                    try:
                        analyze_tender(analysis_db, tender_ref)
                        logger.info(f"Analysis completed for tender: {tender_ref}")
                    except Exception as e:
                        logger.error(f"Background analysis failed for {tender_ref}: {e}")
                    finally:
                        analysis_db.close()

                thread = threading.Thread(target=run_analysis, daemon=True)
                thread.start()
                logger.info(f"Analysis triggered in background for tender: {tender_ref}")

        elif request.action == TenderActionType.TOGGLE_FAVORITE:
            updates['is_favorite'] = not tender.is_favorite

        elif request.action == TenderActionType.TOGGLE_ARCHIVE:
            updates['is_archived'] = not tender.is_archived

        elif request.action == TenderActionType.UPDATE_STATUS:
            if not request.payload or not request.payload.status:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status payload is required for this action")
            updates['status'] = request.payload.status.value
            if request.payload.status.value == "Shortlisted":
                action_to_log = TenderActionEnum.shortlisted
            
        elif request.action == TenderActionType.UPDATE_REVIEW_STATUS:
            if not request.payload or not request.payload.review_status:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Review status payload is required for this action")
            updates['review_status'] = request.payload.review_status.value
            if request.payload.review_status.value == "Shortlisted" and tender.status != "Shortlisted":
                 action_to_log = TenderActionEnum.shortlisted

        if updates:
            updated_tender = self.tender_repo.update(tender, updates)
        else:
            updated_tender = tender

        if action_to_log:
            try:
                self.tender_repo.log_action(updated_tender.id, user_id, action_to_log, notes)
            except Exception as e:
                # Log the error but don't fail the action
                # This handles cases where user_id doesn't exist or other logging issues
                logger.warning(
                    f"Failed to log action {action_to_log} for tender {updated_tender.id} "
                    f"by user {user_id}: {str(e)}"
                )

        return updated_tender
