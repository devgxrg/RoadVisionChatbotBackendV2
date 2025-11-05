"""
TenderIQ Analysis Tasks

Asynchronous tasks for processing tender analyses.
"""

from uuid import UUID
from app.db.database import SessionLocal
from app.modules.tenderiq.services.analysis_service import AnalysisService

def process_analysis_sync(analysis_id: UUID):
    """Synchronous wrapper for processing analysis in a background thread."""
    db = SessionLocal()
    try:
        service = AnalysisService()
        # This is a blocking call
        service.process_analysis(db, analysis_id)
    finally:
        db.close()
