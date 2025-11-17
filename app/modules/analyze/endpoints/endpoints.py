"""
Endpoints for the Analyze module.

Provides APIs for retrieving tender analysis results including:
- One-pager summaries
- Scope of work details
- RFP section analysis
- Data sheets
- Document templates
"""
from uuid import UUID
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.modules.analyze.db.schema import TenderAnalysis
from app.modules.analyze.models.pydantic_models import TenderAnalysisResponse
from app.modules.auth.services.auth_service import get_current_active_user
from app.modules.analyze.repositories import repository as analyze_repo
from app.modules.analyze.services import analysis_rfp_service as rfp_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/{tender_id}",
    response_model=TenderAnalysisResponse,
    summary="Get Tender Analysis",
    description="Retrieve analysis for a tender including one-pager, scope of work, RFP sections, datasheet, and templates. Returns available data regardless of completion status.",
    tags=["Analyze"],
)
def get_tender_analysis(
    tender_id: str,
    db: Session = Depends(get_db_session),
    current_user=Depends(get_current_active_user),
) -> TenderAnalysisResponse:
    """
    Retrieve the analysis for a tender, returning available data regardless of completion status.

    If analysis is still in progress, the response will include:
    - **status**: Current analysis status (pending, parsing, analyzing, completed, failed)
    - **progress**: Percentage complete (0-100)
    - **Completed fields**: Only populated once analysis reaches that stage
    - **Null fields**: Will be null if analysis hasn't reached that stage yet

    Returns:
    - **one_pager**: Executive summary with risk analysis and key highlights (available after analyzing stage)
    - **scope_of_work**: Detailed work packages, components, and deliverables (available after analyzing stage)
    - **rfp_sections**: Section-by-section RFP analysis with requirements and risks (optional, populate from AnalysisRFPSection table)
    - **data_sheet**: Key facts and figures in tabular format (available after analyzing stage)
    - **templates**: Document templates required for bidding (optional, populate from AnalysisDocumentTemplate table)

    Args:
        tender_id: The tender reference number (TDR) as string
        db: Database session
        current_user: Authenticated user

    Raises:
        HTTPException(404): If analysis not found

    Example:
        GET /api/v1/analyze/51655667

        Response while analyzing:
        {
            "id": "...",
            "tender_id": "51655667",
            "status": "analyzing",
            "progress": 45,
            "one_pager": null,
            "scope_of_work": null,
            "data_sheet": null,
            "rfp_sections": null,
            "templates": null
        }

        Response when completed:
        {
            "id": "...",
            "tender_id": "51655667",
            "status": "completed",
            "progress": 100,
            "analyzed_at": "2024-01-16T11:45:00Z",
            "one_pager": {...},
            "scope_of_work": {...},
            "data_sheet": {...},
            ...
        }
    """
    try:
        # Fetch the analysis record from database
        # Try both string and UUID to handle different input formats
        analysis = None
        try:
            analysis = analyze_repo.get_by_id(db, tender_id)
        except (ValueError, TypeError):
            # If tender_id is not a valid UUID, search by tender_id string
            analysis = db.query(TenderAnalysis).filter(
                TenderAnalysis.tender_id == tender_id
            ).first()

        if not analysis:
            logger.warning(f"Analysis not found for tender_id: {tender_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis not found for tender {tender_id}",
            )

        rfp_section = rfp_service.get_rfp_sections(db, analysis.id)

        # Build the response with whatever data is available
        # Null fields indicate the analysis hasn't reached that stage yet
        response = TenderAnalysisResponse(
            id=str(analysis.id),
            tender_id=analysis.tender_id,
            status=analysis.status.value,
            progress=analysis.progress,
            analyzed_at=analysis.analysis_completed_at,
            # Include whatever analysis results are available
            # These will be None if analysis hasn't reached that stage
            one_pager=analysis.one_pager_json,
            scope_of_work=analysis.scope_of_work_json,
            data_sheet=analysis.data_sheet_json,
            # RFP sections and templates would be fetched from related tables if needed
            # For now, returning None - can be extended to fetch from AnalysisRFPSection
            # and AnalysisDocumentTemplate tables
            rfp_sections=rfp_section,
            templates=None,
        )

        logger.info(
            f"Retrieved analysis for tender_id: {tender_id}, status: {analysis.status.value}, progress: {analysis.progress}"
        )
        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error retrieving analysis for tender_id {tender_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving tender analysis",
        )


@router.post(
    "/trigger/{tender_ref}",
    summary="Trigger Tender Analysis",
    description="Start analysis for a tender by tender reference number. Creates analysis record and starts background processing.",
    tags=["Analyze"],
)
def trigger_tender_analysis(
    tender_ref: str,
    db: Session = Depends(get_db_session),
    # current_user=Depends(get_current_active_user),  # Removed auth for testing
):
    """
    Trigger analysis for a tender.
    
    Args:
        tender_ref: Tender reference number (e.g., "51184507")
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Status message
    """
    try:
        from app.modules.analyze.scripts.analyze_tender import analyze_tender
        
        # Check if tender exists
        from app.modules.tenderiq.db.schema import Tender
        tender = db.query(Tender).filter(Tender.tender_ref_number == tender_ref).first()
        if not tender:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tender {tender_ref} not found"
            )
        
        # Check if already analyzed
        existing = db.query(TenderAnalysis).filter(TenderAnalysis.tender_id == tender_ref).first()
        if existing and existing.status == AnalysisStatusEnum.COMPLETED:
            return {
                "status": "already_analyzed",
                "message": f"Tender {tender_ref} is already analyzed",
                "analysis_id": str(existing.id)
            }
        
        # Trigger analysis
        logger.info(f"Triggering analysis for tender {tender_ref}")
        analyze_tender(db, tender_ref)
        
        return {
            "status": "success",
            "message": f"Analysis triggered for tender {tender_ref}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering analysis for {tender_ref}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering analysis: {str(e)}"
        )
